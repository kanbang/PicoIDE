import hashlib
import json
import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Any, Optional, Type
from cachetools import LRUCache
from flow.block import Block
from flow.engine import ComputeEngine
from utils.singleton import singleton


@singleton
class EngineManager:
    """
    引擎管理器：负责业务块注册、流预编译、执行管理和停止。
    使用LRU缓存预编译引擎，避免重复编译。
    支持异步操作，确保线程安全。
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
        """注册业务的块库。如果已存在，则覆盖。"""
        async with self._lock:
            if business_id in self._block_libraries:
                self.logger.warning(f"业务 {business_id} 已注册。正在覆盖。")
            self._block_libraries[business_id] = blocks
            self.logger.info(f"为业务 {business_id} 注册了 {len(blocks)} 个块。")

    def _get_hash(self, business_id: str, flow: Dict) -> str:
        """计算业务ID和流的MD5哈希，用于缓存键。"""
        if not flow:
            raise ValueError("Flow 不能为空。")
        flow_str = json.dumps(flow, sort_keys=True)
        return hashlib.md5(f"{business_id}:{flow_str}".encode()).hexdigest()

    async def _ensure_precompiled(self, business_id: str, flow: Dict, s_hash: str):
        """确保哈希对应的引擎已预编译。如果不存在，则创建。"""
        async with self._lock:
            if s_hash not in self._precompiled_engines:
                self._create_precompiled_internal(business_id, flow, s_hash)

    def _create_precompiled_internal(self, business_id: str, flow: Dict, s_hash: str):
        """内部创建预编译引擎。"""
        if business_id not in self._block_libraries:
            raise ValueError(f"业务 {business_id} 未注册。")
        engine = ComputeEngine(logger=self.logger)
        engine.set_blocks(self._block_libraries[business_id])
        try:
            engine.set_flow(flow)
        except Exception as e:
            self.logger.error(f"为 {business_id} 设置flow失败：{e}", exc_info=True)
            raise
        self._precompiled_engines[s_hash] = engine
        self.logger.info(f"为哈希 {s_hash} 预编译了引擎（业务：{business_id}）。")

    async def acquire(self, business_id: str, flow: Dict) -> ComputeEngine:
        """获取预编译的引擎。如果不存在，则预编译。"""
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
        """移除执行记录。"""
        self.logger.info(f"移除执行 {execution_id}。")
        async with self._lock:
            if execution_id in self._running_executions:
                del self._running_executions[execution_id]
                self.logger.info(f"移除了执行 {execution_id}。")

    async def get_running_executions(self, business: Optional[str] = None) -> List[str]:
        """获取运行中的执行ID列表。可按业务过滤。"""
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
        """停止指定执行。返回是否成功。"""
        async with self._lock:
            if execution_id not in self._running_executions:
                self.logger.warning(f"执行 {execution_id} 未找到。")
                return False
            info = self._running_executions[execution_id]
            if business and info["business"].upper() != business.upper():
                self.logger.warning(f"执行 {execution_id} 的业务不匹配。")
                return False
        # 在等待前释放锁，避免潜在死锁
        try:
            await info["engine"].stop_execution(execution_id)
            info["task"].cancel()
            await asyncio.sleep(0)  # 让出控制权，允许回调运行
            self.logger.info(f"停止了执行 {execution_id}。")
            return True
        except Exception as e:
            self.logger.error(f"停止执行 {execution_id} 失败：{e}", exc_info=True)
            return False

    async def _start_execution_internal(
        self,
        engine: ComputeEngine,
        business_id: str,
        execution_id: str,
        user_id: str,
        on_done: Optional[Callable[[Any], Awaitable[None]]] = None,
    ):
        """内部启动执行逻辑，提取公共部分以避免重复。"""
        await engine.run(execution_id)
        execution = engine.executions.get(execution_id)
        if not execution:
            raise RuntimeError(f"启动执行 {execution_id} 失败。")
        wait_task = asyncio.create_task(execution.shutdown_event.wait())
        await self.register_execution(
            execution_id, wait_task, engine, business_id, user_id
        )

        def done_callback(t):
            asyncio.create_task(self.remove_execution(execution_id))
            if on_done:
                # 目前传递None作为结果；未来可扩展为实际结果
                asyncio.create_task(on_done(None))

        wait_task.add_done_callback(done_callback)

    async def start_execution(
        self,
        business_id: str,
        flow: Dict,
        execution_id: str,
        user_id: str,
        on_done: Optional[Callable[[Any], Awaitable[None]]] = None,
    ):
        """启动新执行，使用预编译引擎。"""
        engine = await self.acquire(business_id, flow)
        await self._start_execution_internal(engine, business_id, execution_id, user_id, on_done)

    async def run_existing(
        self,
        engine: ComputeEngine,
        business_id: str,
        execution_id: str,
        user_id: str,
        on_done: Optional[Callable[[Any], Awaitable[None]]] = None,
    ):
        """在现有引擎上启动执行。"""
        if not hasattr(engine, "run"):
            raise ValueError("无效的引擎实例。")
        await self._start_execution_internal(engine, business_id, execution_id, user_id, on_done)


# 全局辅助函数，便于使用（仅异步版本）
def get_engine_manager() -> EngineManager:
    """获取引擎管理器单例实例。"""
    return EngineManager()


async def async_acquire_flow(business_id: str, flow: Dict) -> ComputeEngine:
    """异步获取预编译的流引擎。"""
    manager = get_engine_manager()
    return await manager.acquire(business_id, flow)


async def async_run_existing_engine(
    engine: ComputeEngine,
    business_id: str,
    execution_id: str,
    user_id: str,
    on_done: Optional[Callable[[Any], Awaitable[None]]] = None,
):
    """异步在现有引擎上运行执行。"""
    manager = get_engine_manager()
    await manager.run_existing(engine, business_id, execution_id, user_id, on_done)


async def async_start_flow(
    business_id: str,
    flow: Dict,
    execution_id: str,
    user_id: str,
    on_done: Optional[Callable[[Any], Awaitable[None]]] = None,
):
    """异步启动流执行。"""
    manager = get_engine_manager()
    await manager.start_execution(business_id, flow, execution_id, user_id, on_done)


async def async_stop_flow(execution_id: str, business: Optional[str] = None) -> bool:
    """异步停止流执行。"""
    manager = get_engine_manager()
    return await manager.stop_execution(execution_id, business)


async def register_business_blocks(business_id: str, blocks: List[Type[Block]]):
    """注册业务的块。"""
    manager = get_engine_manager()
    await manager.register_business(business_id, blocks)


async def get_running_flows(business: Optional[str] = None) -> List[str]:
    """获取运行中的流ID列表。"""
    manager = get_engine_manager()
    return await manager.get_running_executions(business)