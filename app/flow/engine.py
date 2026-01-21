import asyncio
import networkx as nx
import logging
from enum import Enum, auto
from typing import Any, Dict, List, Type, Optional, Set, Tuple
from collections import defaultdict

# 假设 Block 基类已在外部定义
# from flow.block import Block

class EngineStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    STOPPING = auto()

class ComputeEngine:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("ComputeEngine")
        
        # 结构定义
        self.block_registry: Dict[str, Type['Block']] = {}
        self.instances: Dict[str, 'Block'] = {}
        self._graph = nx.MultiDiGraph()
        
        # 运行时状态管理
        self.status = EngineStatus.IDLE
        self._node_locks: Dict[str, asyncio.Lock] = {}
        self._ready_counts: Dict[str, int] = defaultdict(int)
        self._running_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()

    # --- 1. 配置与编译阶段 ---

    def set_blocks(self, block_classes: List[Type['Block']]):
        """注册可用的 Block 类"""
        for cls in block_classes:
            if hasattr(cls, "NAME"):
                self.block_registry[cls.NAME] = cls
        self.logger.info(f"Registered {len(block_classes)} block types.")

    def set_flow(self, flow: Dict[str, Any]):
        """编译计算图"""
        if self.status != EngineStatus.IDLE:
            raise RuntimeError("Cannot recompile flow while engine is running.")

        self._graph.clear()
        self.instances = {}
        self._node_locks = {}
        self._ready_counts.clear()
        
        port_map = {} 

        # 实例化节点
        for n_data in flow["nodes"]:
            n_id = n_data["id"]
            cls = self.block_registry.get(n_data["type"])
            if not cls:
                self.logger.warning(f"Unknown block type: {n_data['type']}")
                continue
            
            inst = cls()
            inst.instance_id = n_id
            self.instances[n_id] = inst
            self._node_locks[n_id] = asyncio.Lock()
            self._graph.add_node(n_id)

            # 配置端口映射
            for k, v in n_data.get("inputs", {}).items():
                if k in inst._options:
                    inst.set_option(k, v.get("value"))
                else:
                    port_map[v["id"]] = (n_id, k)
            for k, v in n_data.get("outputs", {}).items():
                port_map[v["id"]] = (n_id, k)

        # 建立拓扑连接
        for conn in flow["connections"]:
            src = port_map.get(conn["from"])
            dst = port_map.get(conn["to"])
            if src and dst:
                self._graph.add_edge(src[0], dst[0], out_p=src[1], in_p=dst[1])
        
        self.logger.info(f"Flow compiled: {len(self.instances)} nodes, {self._graph.number_of_edges()} connections.")

    # --- 2. 核心调度逻辑 ---

    async def _execute_node(self, n_id: str, exec_id: str):
        """执行普通节点的计算并触发其下游"""
        block = self.instances[n_id]
        try:
            # 执行节点的业务逻辑
            await block.async_on_compute(exec_id)
            # 递归触发下游
            await self._trigger_successors(n_id, exec_id)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.logger.error(f"Node execution error {n_id} ({block.NAME}): {e}", exc_info=True)

    async def _trigger_successors(self, n_id: str, exec_id: str):
        """核心：数据搬运与屏障同步(Barrier Synchronization)"""
        block = self.instances[n_id]
        successors = list(self._graph.successors(n_id))
        
        for succ_id in successors:
            succ_block = self.instances[succ_id]
            
            # 1. 数据物理搬运 (Data Marshalling)
            edges = self._graph.get_edge_data(n_id, succ_id)
            for edge in edges.values():
                succ_block._inputs[edge["in_p"]] = block._outputs.get(edge["out_p"])

            # 2. 屏障同步：确保多入度节点集齐所有输入
            async with self._node_locks[succ_id]:
                self._ready_counts[succ_id] += 1
                # 信号量满足入度要求
                if self._ready_counts[succ_id] >= self._graph.in_degree(succ_id):
                    self._ready_counts[succ_id] = 0
                    
                    # 启动下游任务
                    task = asyncio.create_task(self._execute_node(succ_id, exec_id))
                    self._running_tasks.add(task)
                    task.add_done_callback(self._running_tasks.discard)

    async def _source_worker(self, n_id: str, exec_id: str):
        """源节点(Source)专用 Worker，负责生产数据泵"""
        block = self.instances[n_id]
        
        while not self._shutdown_event.is_set():
            try:
                # 阻塞直到源节点产出新数据
                await block.async_on_compute(exec_id)
                
                # 源节点产出数据后，异步抛出下游分支
                asyncio.create_task(self._trigger_successors(n_id, exec_id))
                
                # 根据 Block 属性判断是流式源还是单次源
                if not getattr(block, "STREAMING", False):
                    self.logger.info(f"Once-style source {n_id} finished.")
                    break
                
                await asyncio.sleep(0.001) # 微小让权
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Source worker {n_id} error: {e}")
                await asyncio.sleep(1) # 故障避让

    # --- 3. 外部控制接口 ---

    async def run(self, execution_id: str = "exec_default"):
        """启动引擎的主入口"""
        if self.status != EngineStatus.IDLE:
            return

        self.status = EngineStatus.RUNNING
        self._shutdown_event.clear()
        self.logger.info(f"Engine started (ExecID: {execution_id}).")

        # 识别入度为 0 的拓扑源
        sources = [n for n, d in self._graph.in_degree() if d == 0]
        
        # 启动所有源 Worker
        for n_id in sources:
            task = asyncio.create_task(self._source_worker(n_id, execution_id))
            self._running_tasks.add(task)
            task.add_done_callback(self._running_tasks.discard)

        try:
            # 持续运行，直到手动停止或所有任务运行完毕
            while not self._shutdown_event.is_set():
                if not self._running_tasks:
                    self.logger.info("All tasks completed. Engine exiting.")
                    break
                await asyncio.sleep(0.5)
        finally:
            await self.stop()

    async def stop(self):
        """优雅停止引擎"""
        if self.status == EngineStatus.STOPPING:
            return
            
        self.status = EngineStatus.STOPPING
        self._shutdown_event.set()
        
        if self._running_tasks:
            self.logger.info(f"Stopping {len(self._running_tasks)} active tasks...")
            for task in list(self._running_tasks):
                if not task.done():
                    task.cancel()
            
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
            self._running_tasks.clear()

        self.status = EngineStatus.IDLE
        self.logger.info("Engine stopped safely.")