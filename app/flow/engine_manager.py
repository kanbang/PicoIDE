import hashlib
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Type
from cachetools import LRUCache
from flow.block import Block
from flow.engine import ComputeEngine
from utils.singleton import singleton


@singleton
class EngineManager:
    """
    优化的EngineManager类，仅支持异步操作以精炼代码。

    关键优化：
    - 统一锁机制：使用单一的asyncio.Lock处理所有关键部分。
    - 移除所有同步方法，仅提供异步接口。
    - 改进错误处理：添加更具体的异常和日志记录。
    - 预编译：确保预编译始终异步进行。
    - 执行管理：添加更好的清理和状态检查。
    - 哈希：对JSON键排序以确保一致的哈希。
    - 通用清理：移除冗余代码，聚焦异步逻辑。

    注意：假设有一个全局日志器可用；如果没有，请集成一个。
    """

    def __init__(
        self, precompiled_size: int = 100, logger: Optional[logging.Logger] = None
    ):
        self._block_libraries: Dict[str, List[Type[Block]]] = {}
        self._precompiled_engines = LRUCache(maxsize=precompiled_size)
        self._lock = asyncio.Lock()
        self._running_executions: Dict[str, Dict[str, Any]] = {}
        self.logger = logger or logging.getLogger("EngineManager")

    async def register_business(self, business_id: str, blocks: List[Type[Block]]):
        """为业务ID注册块。"""
        async with self._lock:
            if business_id in self._block_libraries:
                self.logger.warning(f"业务 {business_id} 已注册。正在覆盖。")
            self._block_libraries[business_id] = blocks
            self.logger.info(f"为业务 {business_id} 注册了 {len(blocks)} 个块。")

    def _get_hash(self, business_id: str, flow: Dict) -> str:
        """为business_id和flow生成一致的哈希。"""
        if not flow:
            raise ValueError("Flow 不能为空。")
        flow_str = json.dumps(flow, sort_keys=True)
        return hashlib.md5(f"{business_id}:{flow_str}".encode()).hexdigest()

    async def _ensure_precompiled(self, business_id: str, flow: Dict, s_hash: str):
        """确保引擎已预编译，如果必要则创建它。"""
        async with self._lock:
            if s_hash not in self._precompiled_engines:
                self._create_precompiled_internal(business_id, flow, s_hash)

    def _create_precompiled_internal(self, business_id: str, flow: Dict, s_hash: str):
        """内部方法，用于创建和缓存预编译的引擎。"""
        if business_id not in self._block_libraries:
            raise ValueError(f"业务 {business_id} 未注册。")
        engine = ComputeEngine(logger=self.logger)
        engine.set_blocks(self._block_libraries[business_id])
        try:
            engine.set_flow(flow)
        except Exception as e:
            self.logger.error(f"为 {business_id} 设置flow失败：{e}")
            raise
        self._precompiled_engines[s_hash] = engine
        self.logger.info(f"为哈希 {s_hash} 预编译了引擎（业务：{business_id}）。")

    async def acquire(self, business_id: str, flow: Dict) -> ComputeEngine:
        """异步获取预编译的引擎。"""
        s_hash = self._get_hash(business_id, flow)
        await self._ensure_precompiled(business_id, flow, s_hash)
        return self._precompiled_engines[s_hash]

    async def register_execution(
        self,
        execution_id: str,
        task: asyncio.Task,
        engine: ComputeEngine,
        business: str,
        user_id: str,
    ):
        """注册正在运行的执行。"""
        async with self._lock:
            if execution_id in self._running_executions:
                self.logger.warning(f"执行 {execution_id} 已注册。正在覆盖。")
            self._running_executions[execution_id] = {
                "task": task,
                "engine": engine,
                "business": business,
                "user_id": user_id,
            }
            self.logger.info(
                f"为业务 {business} 注册了执行 {execution_id}（用户：{user_id}）。"
            )

    async def remove_execution(self, execution_id: str):
        """移除已完成或停止的执行。"""
        async with self._lock:
            if execution_id in self._running_executions:
                del self._running_executions[execution_id]
                self.logger.info(f"移除了执行 {execution_id}。")

    async def get_running_executions(self, business: Optional[str] = None) -> List[str]:
        """获取正在运行的执行ID列表，可选地按业务过滤。"""
        async with self._lock:
            if business:
                return [
                    ex_id
                    for ex_id, info in self._running_executions.items()
                    if info["business"].upper() == business.upper()
                ]
            return list(self._running_executions.keys())

    async def stop_execution(
        self, execution_id: str, business: Optional[str] = None
    ) -> bool:
        """停止特定执行，如果它匹配业务过滤器。"""
        async with self._lock:
            if execution_id not in self._running_executions:
                self.logger.warning(f"执行 {execution_id} 未找到。")
                return False
            info = self._running_executions[execution_id]
            if business and info["business"].upper() != business.upper():
                self.logger.warning(f"执行 {execution_id} 的业务不匹配。")
                return False
            try:
                await info["engine"].stop_execution(execution_id)
                info["task"].cancel()
                self.logger.info(f"停止了执行 {execution_id}。")
                return True
            except Exception as e:
                self.logger.error(f"停止执行 {execution_id} 失败：{e}")
                return False

    async def start_execution(
        self, business_id: str, flow: Dict, execution_id: str, user_id: str
    ):
        """异步启动新执行。"""
        engine = await self.acquire(business_id, flow)
        await engine.run(execution_id)
        execution = engine.executions.get(execution_id)
        if not execution:
            raise RuntimeError(f"启动执行 {execution_id} 失败。")
        wait_task = asyncio.create_task(execution.shutdown_event.wait())
        await self.register_execution(
            execution_id, wait_task, engine, business_id, user_id
        )
        wait_task.add_done_callback(
            lambda t: asyncio.create_task(self.remove_execution(execution_id))
        )

    async def run_existing(
        self, engine: ComputeEngine, business_id: str, execution_id: str, user_id: str
    ):
        """异步运行现有引擎实例。"""
        if not hasattr(engine, "run"):
            raise ValueError("无效的引擎实例。")
        await engine.run(execution_id)
        execution = engine.executions.get(execution_id)
        if not execution:
            raise RuntimeError(f"在现有引擎上启动执行 {execution_id} 失败。")
        wait_task = asyncio.create_task(execution.shutdown_event.wait())
        await self.register_execution(
            execution_id, wait_task, engine, business_id, user_id
        )
        wait_task.add_done_callback(
            lambda t: asyncio.create_task(self.remove_execution(execution_id))
        )


# 全局辅助函数，便于使用（仅异步版本）
def get_engine_manager() -> EngineManager:
    """获取单例EngineManager实例。"""
    return EngineManager()


async def async_acquire_flow(business_id: str, flow: Dict) -> ComputeEngine:
    """全局异步辅助函数，用于获取预编译的引擎。"""
    manager = get_engine_manager()
    return await manager.acquire(business_id, flow)


async def async_run_existing_engine(
    engine: ComputeEngine, business_id: str, execution_id: str, user_id: str
):
    """全局异步辅助函数，用于运行现有引擎实例。"""
    manager = get_engine_manager()
    await manager.run_existing(engine, business_id, execution_id, user_id)


async def async_start_flow(
    business_id: str, flow: Dict, execution_id: str, user_id: str
):
    """全局异步辅助函数，用于启动flow执行。"""
    manager = get_engine_manager()
    await manager.start_execution(business_id, flow, execution_id, user_id)


async def async_stop_flow(execution_id: str, business: Optional[str] = None) -> bool:
    """全局异步辅助函数，用于停止执行。"""
    manager = get_engine_manager()
    return await manager.stop_execution(execution_id, business)


async def register_business_blocks(business_id: str, blocks: List[Type[Block]]):
    """全局异步辅助函数，用于注册业务块。"""
    manager = get_engine_manager()
    await manager.register_business(business_id, blocks)


async def get_running_flows(business: Optional[str] = None) -> List[str]:
    """全局异步辅助函数，用于获取正在运行的执行ID。"""
    manager = get_engine_manager()
    return await manager.get_running_executions(business)
