import hashlib
import json
import asyncio
import threading
from typing import Dict, List, Any, Optional, Type
from cachetools import LRUCache
from flow.block import Block  # 假设这是你的自定义模块
from flow.engine import ComputeEngine  # 假设这是你的自定义模块
from utils.singleton import singleton  # 假设这是你的单例工具

@singleton
class EngineManager:
    def __init__(self, precompiled_size: int = 100):
        self._block_libraries: Dict[str, list[Type[Block]]] = {}
        self._precompiled_engines = LRUCache(maxsize=precompiled_size)
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        self._running_executions: Dict[str, Dict[str, Any]] = {}

    def register_business(self, business_id: str, blocks: list[Type[Block]]):
        with self._lock:
            self._block_libraries[business_id] = blocks

    def _get_hash(self, business_id: str, flow: Dict) -> str:
        if not flow:
            raise ValueError("Flow cannot be empty.")
        s_str = json.dumps(flow, sort_keys=True)
        return hashlib.md5(f"{business_id}:{s_str}".encode()).hexdigest()

    async def _ensure_precompiled_async(self, business_id: str, flow: Dict, s_hash: str):
        if s_hash not in self._precompiled_engines:
            async with self._async_lock:
                if s_hash not in self._precompiled_engines:
                    self._create_precompiled_internal(business_id, flow, s_hash)

    def _ensure_precompiled_sync(self, business_id: str, flow: Dict, s_hash: str):
        if s_hash not in self._precompiled_engines:
            with self._lock:
                if s_hash not in self._precompiled_engines:
                    self._create_precompiled_internal(business_id, flow, s_hash)

    async def acquire(self, business_id: str, flow: Dict) -> ComputeEngine:
        s_hash = self._get_hash(business_id, flow)
        await self._ensure_precompiled_async(business_id, flow, s_hash)
        return self._precompiled_engines[s_hash]

    def acquire_sync(self, business_id: str, flow: Dict) -> ComputeEngine:
        s_hash = self._get_hash(business_id, flow)
        self._ensure_precompiled_sync(business_id, flow, s_hash)
        return self._precompiled_engines[s_hash]

    def register_execution(self, execution_id: str, task: asyncio.Task, engine: ComputeEngine, business: str, user_id: str):
        with self._lock:
            self._running_executions[execution_id] = {
                "task": task,
                "engine": engine,
                "business": business,
                "user_id": user_id,
            }

    def remove_execution(self, execution_id: str):
        with self._lock:
            if execution_id in self._running_executions:
                del self._running_executions[execution_id]

    def get_running_executions(self, business: Optional[str] = None) -> List[str]:
        with self._lock:
            if business:
                return [ex_id for ex_id, info in self._running_executions.items() if info["business"].upper() == business.upper()]
            return list(self._running_executions.keys())

    async def stop_execution(self, execution_id: str, business: Optional[str] = None) -> bool:
        with self._lock:
            if execution_id not in self._running_executions:
                return False
            info = self._running_executions[execution_id]
            if business and info["business"].upper() != business.upper():
                return False
            await info["engine"].stop_execution(execution_id)
            info["task"].cancel()
            return True

    def _create_precompiled_internal(self, biz_id: str, flow: Dict, s_hash: str):
        if biz_id not in self._block_libraries:
            raise ValueError(f"Business {biz_id} not registered.")
        engine = ComputeEngine()
        engine.set_blocks(self._block_libraries[biz_id])
        engine.set_flow(flow)
        self._precompiled_engines[s_hash] = engine

    async def start_execution(self, business_id: str, flow: Dict, execution_id: str, user_id: str):
        engine = await self.acquire(business_id, flow)
        await engine.run(execution_id)
        execution = engine.executions.get(execution_id)
        if execution:
            wait_task = asyncio.create_task(execution.shutdown_event.wait())
            self.register_execution(execution_id, wait_task, engine, business_id, user_id)
            wait_task.add_done_callback(lambda t: self.remove_execution(execution_id))

    def start_execution_sync(self, business_id: str, flow: Dict, execution_id: str, user_id: str):
        engine = self.acquire_sync(business_id, flow)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(engine.run(execution_id))
        execution = engine.executions.get(execution_id)
        if execution:
            wait_task = loop.create_task(execution.shutdown_event.wait())
            self.register_execution(execution_id, wait_task, engine, business_id, user_id)
            wait_task.add_done_callback(lambda t: self.remove_execution(execution_id))

    async def run_existing(self, engine: ComputeEngine, business_id: str, execution_id: str, user_id: str):
        if not hasattr(engine, 'run'):
            raise ValueError("Invalid engine instance.")
        await engine.run(execution_id)
        execution = engine.executions.get(execution_id)
        if execution:
            wait_task = asyncio.create_task(execution.shutdown_event.wait())
            self.register_execution(execution_id, wait_task, engine, business_id, user_id)
            wait_task.add_done_callback(lambda t: self.remove_execution(execution_id))

    def run_existing_sync(self, engine: ComputeEngine, business_id: str, execution_id: str, user_id: str):
        if not hasattr(engine, 'run'):
            raise ValueError("Invalid engine instance.")
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(engine.run(execution_id))
        execution = engine.executions.get(execution_id)
        if execution:
            wait_task = loop.create_task(execution.shutdown_event.wait())
            self.register_execution(execution_id, wait_task, engine, business_id, user_id)
            wait_task.add_done_callback(lambda t: self.remove_execution(execution_id))

    # 新增简便函数：异步启动执行（简化接口，直接启动，无需手动获取 engine）
    async def simple_start_execution(self, business_id: str, flow: Dict, execution_id: str = "default_exec", user_id: str = "default_user"):
        await self.start_execution(business_id, flow, execution_id, user_id)

    # 新增简便函数：同步启动执行（简化接口，直接启动，无需手动获取 engine）
    def simple_start_execution_sync(self, business_id: str, flow: Dict, execution_id: str = "default_exec", user_id: str = "default_user"):
        self.start_execution_sync(business_id, flow, execution_id, user_id)

# 使用示例（假设 engine_manager 是 EngineManager 实例）
# 1. 注册业务
# engine_manager.register_business("vibration_analysis", [BlockType1, BlockType2])  # 替换为实际 Block 类型

# 2. 预编译并获取 engine（可选，如果使用 start_execution 会自动预编译）
# engine = await engine_manager.acquire("vibration_analysis", {"key": "flow_data"})

# 3. 使用简便函数启动执行（异步）
# await engine_manager.simple_start_execution("vibration_analysis", {"key": "flow_data"}, "exec_001", "user_001")

# 4. 使用简便函数启动执行（同步）
# engine_manager.simple_start_execution_sync("vibration_analysis", {"key": "flow_data"}, "exec_002", "user_002")

# 5. 运行现有 engine（异步）
# await engine_manager.run_existing(engine, "vibration_analysis", "new_exec_003", "user_003")

# 6. 运行现有 engine（同步）
# engine_manager.run_existing_sync(engine, "vibration_analysis", "new_exec_004", "user_004")

# 7. 停止执行
# await engine_manager.stop_execution("exec_001")

# 8. 获取运行中执行
# running = engine_manager.get_running_executions("vibration_analysis")
# print(running)