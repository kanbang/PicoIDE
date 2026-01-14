import hashlib
import json
import asyncio
import copy
import threading
from collections import deque
from typing import Dict, List, Any, Optional
from cachetools import LRUCache
from flow.engine import ComputeEngine
from utils.singleton import singleton

@singleton
class EngineManager:
    def __init__(self, pool_size: int = 10, blueprint_size: int = 100):
        # 1. 静态资源：业务对应的 Block 模板类
        self._block_libraries: Dict[str, List[Any]] = {}
        
        # 2. 核心缓存：预编译蓝图 (LRU)
        self._blueprints = LRUCache(maxsize=blueprint_size)
        
        # 3. 实例池：{ schema_hash: deque([ComputeEngine]) }
        self._instance_pools: Dict[str, deque] = {}
        self._pool_max = pool_size
        
        # 4. 双重锁机制
        # 线程锁保护同步操作（线程安全）
        self._lock = threading.Lock()
        # 异步锁保护蓝图初始化逻辑（协程安全，防止惊群效应）
        self._async_lock = asyncio.Lock()

    def register_business(self, business_id: str, blocks: List[Any]):
        with self._lock:
            self._block_libraries[business_id] = blocks

    def _get_hash(self, business_id: str, schema: Dict) -> str:
        # 进行排序序列化
        s_str = json.dumps(schema, sort_keys=True)
        return hashlib.md5(f"{business_id}:{s_str}".encode()).hexdigest()

    # --- 异步接口层 ---
    async def acquire(self, business_id: str, schema: Dict) -> "ScopedEngine":
        s_hash = self._get_hash(business_id, schema)
        
        # 1. 异步检查蓝图是否存在（非阻塞快速路径）
        if s_hash not in self._blueprints:
            async with self._async_lock:
                # Double-Check 避免并发请求重复编译
                if s_hash not in self._blueprints:
                    self._create_blueprint_internal(business_id, schema, s_hash)
        
        return ScopedEngine(self, business_id, schema, s_hash)

    # --- 同步接口层 ---
    def acquire_sync(self, business_id: str, schema: Dict) -> "ScopedEngineSync":
        s_hash = self._get_hash(business_id, schema)
        
        # 同步环境下直接检查并创建蓝图
        if s_hash not in self._blueprints:
            with self._lock:
                if s_hash not in self._blueprints:
                    self._create_blueprint_internal(business_id, schema, s_hash)
        
        return ScopedEngineSync(self, business_id, schema, s_hash)

    # --- 核心逻辑私有化 ---
    def _create_blueprint_internal(self, biz_id: str, schema: Dict, s_hash: str):
        """严谨的编译流程：创建蓝图并初始化池"""
        if biz_id not in self._block_libraries:
            raise ValueError(f"Business {biz_id} not registered.")
        
        bp = ComputeEngine()
        bp.register_blocks(self._block_libraries[biz_id])
        # 拓扑排序与环路检测在此处一次性完成
        bp.set_schema(schema)
        
        self._blueprints[s_hash] = bp
        self._instance_pools[s_hash] = deque()

    def _get_instance(self, s_hash: str) -> "ComputeEngine":
        """从池中弹出实例或从蓝图克隆"""
        with self._lock:
            pool = self._instance_pools[s_hash]
            if pool:
                return pool.popleft()
            # 池空时执行克隆，此操作依然在锁内以保证蓝图对象不被竞争访问
            return copy.deepcopy(self._blueprints[s_hash])

    def _return_instance(self, s_hash: str, engine: "ComputeEngine"):
        """归还实例前重置数据，并入池"""
        for inst in engine.instances.values():
            inst.reset()
        
        with self._lock:
            pool = self._instance_pools.get(s_hash)
            if pool is not None and len(pool) < self._pool_max:
                pool.append(engine)

# ==========================================
# 5. 上下文管理器封装（严谨资源回收）
# ==========================================

class ScopedEngine:
    """异步上下文管理器"""
    def __init__(self, mgr: EngineManager, biz_id: str, schema: Dict, s_hash: str):
        self.mgr, self.biz_id, self.schema, self.s_hash = mgr, biz_id, schema, s_hash
        self.engine: Optional[ComputeEngine] = None

    async def __aenter__(self) -> "ComputeEngine":
        self.engine = self.mgr._get_instance(self.s_hash)
        return self.engine

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.mgr._return_instance(self.s_hash, self.engine)

class ScopedEngineSync:
    """同步上下文管理器"""
    def __init__(self, mgr: EngineManager, biz_id: str, schema: Dict, s_hash: str):
        self.mgr, self.biz_id, self.schema, self.s_hash = mgr, biz_id, schema, s_hash
        self.engine: Optional[ComputeEngine] = None

    def __enter__(self) -> "ComputeEngine":
        self.engine = self.mgr._get_instance(self.s_hash)
        return self.engine

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.mgr._return_instance(self.s_hash, self.engine)


# # 示例使用场景

    # async def analyze_vibration(schema: dict = Body(...)):
    #     """
    #     在高并发下，相同的 schema 会从 Object Pool 中 O(1) 获取实例。
    #     """
     
    #     # 1. 异步获取引擎（内置蓝图编译检查、惊群保护、对象池复用）
    #     async with await engine_manager.acquire("vibration_analysis", schema) as engine:
    #         # 2. 执行高性能计算
    #         # 虽然 compute 是同步的，但管理器支持在协程中安全运行
    #         await engine.async_run()

                
    # def worker_task(schema_data):
    #     """
    #     同步 Worker 任务。
    #     使用 acquire_sync 确保在多线程环境下对池的访问是原子性的。
    #     """
    #     # 1. 同步方式借出引擎
    #     with engine_manager.acquire_sync("vibration_analysis", schema_data) as engine:
    #         # 2. 执行计算
    #         engine.run()