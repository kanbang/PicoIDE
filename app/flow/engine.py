import asyncio
import networkx as nx
import logging
import copy
import time
from enum import Enum, auto
from typing import Any, Dict, List, Type, Optional, Set, Tuple
from collections import defaultdict
from flow.runtime_bus import RuntimeEventBus, RuntimeEvent, RuntimeEventType
from flow.collector import file_collector


class EngineStatus(Enum):
    IDLE = auto()
    RUNNING = auto()
    STOPPING = auto()


class ComputeEngine:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.event_bus = RuntimeEventBus()  # 使用单例
        self.logger = logger or logging.getLogger("ComputeEngine")

        # 设置文件收集器的即时推送回调
        file_collector.set_event_callback(self._on_file_generated)

        # 结构定义
        self.block_registry: Dict[str, Type["Block"]] = {}
        self.instances: Dict[str, "Block"] = {}
        self._graph = nx.MultiDiGraph()

        # 运行时状态管理
        self.status = EngineStatus.IDLE
        self._node_locks: Dict[str, asyncio.Lock] = {}
        # 使用 (node_id, exec_id) 组合作为计数 Key，防止批次污染
        self._ready_ports = defaultdict(set)
        self._running_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        # 记录执行开始时间，用于计算 duration
        self._execution_start_time: Optional[float] = None
        # 当前执行的ID，用于发送停止事件
        self._current_execution_id: Optional[str] = None

    # --- 1. 配置与编译阶段 ---

    def set_blocks(self, block_classes: List[Type["Block"]]):
        """注册可用的 Block 类"""
        for cls in block_classes:
            if hasattr(cls, "NAME"):
                self.block_registry[cls.NAME] = cls
        self.logger.info(f"Registered {len(block_classes)} block types.")

    def set_flow(self, flow: Dict[str, Any]):
        """编译计算图并进行拓扑检查"""
        if self.status != EngineStatus.IDLE:
            raise RuntimeError("Cannot recompile flow while engine is running.")

        self._graph.clear()
        self.instances = {}
        self._node_locks = {}
        self._ready_ports.clear()

        port_map = {}

        # 1. 实例化节点
        for n_data in flow["nodes"]:
            n_id = n_data["id"]
            cls = self.block_registry.get(n_data["type"])
            if not cls:
                raise ValueError(f"Unknown block type: {n_data['type']}")

            inst = cls()
            inst.instance_id = n_id
            self.instances[n_id] = inst
            self._node_locks[n_id] = asyncio.Lock()
            self._graph.add_node(n_id)

            # 配置端口映射与静态 Option
            for k, v in n_data.get("inputs", {}).items():
                if k in inst._options:
                    inst.set_option(k, v.get("value"))
                else:
                    port_map[v["id"]] = (n_id, k)
            for k, v in n_data.get("outputs", {}).items():
                port_map[v["id"]] = (n_id, k)

        # 2. 建立拓扑连接
        for conn in flow["connections"]:
            src = port_map.get(conn["from"])
            dst = port_map.get(conn["to"])
            if src and dst:
                self._graph.add_edge(src[0], dst[0], out_p=src[1], in_p=dst[1])

        # 3. 拓扑合法性检查
        if not nx.is_directed_acyclic_graph(self._graph):
            self.logger.warning(
                "Graph contains cycles. Ensure blocks handle feedback loops properly."
            )

        self.logger.info(f"Flow compiled: {len(self.instances)} nodes.")

    # --- 2. 核心调度逻辑 ---

    async def _execute_node(self, n_id: str, exec_id: str):
        """执行节点计算"""
        block = self.instances[n_id]
        try:
            # 执行业务逻辑
            await block.async_on_compute(exec_id)
            await self.event_bus.emit(
                RuntimeEvent(
                    exec_id, RuntimeEventType.LOG, n_id, f"Node {n_id} completed"
                )
            )
            # 成功后触发下游
            await self._trigger_successors(n_id, exec_id)
        except asyncio.CancelledError:
            await self.event_bus.emit(
                RuntimeEvent(
                    exec_id, RuntimeEventType.ERROR, n_id, f"Node {n_id} cancelled"
                )
            )
            raise
        except Exception as e:
            self.logger.error(
                f"Node {n_id} [{block.NAME}] execution failed: {e}", exc_info=True
            )
            await self.event_bus.emit(
                RuntimeEvent(
                    exec_id,
                    RuntimeEventType.ERROR,
                    n_id,
                    f"Node {n_id} failed: {str(e)}",
                )
            )
            # 注意：此处可扩展错误传播逻辑，清理 _ready_ports 或通知下游失败

    async def _trigger_successors(self, n_id: str, exec_id: str):
        """数据搬运与屏障同步"""
        block = self.instances[n_id]
        # 关键：获取输出快照，实现数据隔离
        output_snapshot = {k: copy.copy(v) for k, v in block._outputs.items()}

        for succ_id in list(self._graph.successors(n_id)):
            succ_block = self.instances[succ_id]

            async with self._node_locks[succ_id]:

                # 记录是哪个"来源节点"送达了数据
                slot_key = (succ_id, exec_id)

                # 1. 物理搬运数据
                edges = self._graph.get_edge_data(n_id, succ_id)
                for edge in edges.values():
                    in_port = edge["in_p"]
                    out_port = edge["out_p"]

                    # 物理搬运数据
                    succ_block._inputs[in_port] = output_snapshot.get(out_port)
                    self._ready_ports[slot_key].add(in_port)

                # 只有当 set 的长度等于入度时，才说明每个上游都到齐了
                if len(self._ready_ports[slot_key]) >= self._graph.in_degree(succ_id):
                    # 重置槽位
                    del self._ready_ports[slot_key]

                    # 启动任务
                    task = asyncio.create_task(self._execute_node(succ_id, exec_id))
                    self._running_tasks.add(task)
                    task.add_done_callback(self._running_tasks.discard)

    async def _source_worker(self, n_id: str, exec_id: str):
        """源节点驱动器"""
        block = self.instances[n_id]
        is_streaming = getattr(block, "STREAMING", False)

        while not self._shutdown_event.is_set():
            try:
                # 生产数据
                await block.async_on_compute(exec_id)

                # 触发下游（不等待下游执行完，实现流水线并行）
                trigger_task = asyncio.create_task(
                    self._trigger_successors(n_id, exec_id)
                )
                self._running_tasks.add(trigger_task)
                trigger_task.add_done_callback(self._running_tasks.discard)

                if not is_streaming:
                    break

                # 这里的频率控制应由 Block 内部的 async_on_compute 实现（如 await sleep）
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Source {n_id} error: {e}")
                await asyncio.sleep(1)  # 故障退避

    def _on_file_generated(self, execution_id: str, file_info: Dict[str, Any]):
        """
        文件生成时的回调函数，立即通过 SSE 发送给前端

        Args:
            execution_id: 执行ID
            file_info: 文件信息字典
        """
        # 由于这是同步回调，需要在事件循环中调度异步任务
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # 统一使用 "file" 格式，与前端处理逻辑一致
        file_event = RuntimeEvent(
            execution_id=execution_id,
            type=RuntimeEventType.DATA,
            source="output_file",
            message=f"Generated file: {file_info['filename']}",
            payload={"file": file_info},
            ts=time.time()
        )

        if loop.is_running():
            # 使用 ensure_future 在当前运行的事件循环中调度
            loop.create_task(self.event_bus.emit(file_event))
        else:
            # 如果没有运行中的事件循环，使用 asyncio.run_until_complete
            loop.run_until_complete(self.event_bus.emit(file_event))

    # --- 3. 运行控制 ---

    async def run(self, execution_id: str = "exec_001"):
        """启动引擎"""
        if self.status != EngineStatus.IDLE:
            self.logger.warning("Engine is already running.")
            await self.event_bus.emit(
                RuntimeEvent(
                    execution_id,
                    RuntimeEventType.EXECUTION_FAILED,
                    "engine",
                    "Engine is already running.",
                )
            )
            return

        self.status = EngineStatus.RUNNING
        self._current_execution_id = execution_id
        self._execution_start_time = time.time()
        self._shutdown_event.clear()

        # 发送 running 状态事件
        await self.event_bus.emit(
            RuntimeEvent(
                execution_id,
                RuntimeEventType.STATUS,
                "engine",
                "Execution started",
                payload={"status": "running"},
            )
        )

        # 识别入度为 0 的源节点
        sources = [n for n, d in self._graph.in_degree() if d == 0]
        if not sources:
            self.logger.error("No source nodes found in flow!")
            self.status = EngineStatus.IDLE
            self._execution_start_time = None
            self._current_execution_id = None
            await self.event_bus.emit(
                RuntimeEvent(
                    execution_id,
                    RuntimeEventType.EXECUTION_FAILED,
                    "engine",
                    "No source nodes found in flow!",
                )
            )
            return

        for n_id in sources:
            task = asyncio.create_task(self._source_worker(n_id, execution_id))
            self._running_tasks.add(task)
            task.add_done_callback(self._running_tasks.discard)

        # 维持运行直到主动停止或任务清空
        try:
            while not self._shutdown_event.is_set():
                if not self._running_tasks:
                    self.logger.info("Pipeline idle. All tasks finished.")
                    break
                await asyncio.sleep(0.1)
        finally:
            await self.stop()


          
        # # 从文件收集器获取，整体返回运行结果，作为备选方案，不要删
        # output_files = file_collector.get_files(execution_id)

        # # 通过 SSE 发送输出文件列表给前端
        # if output_files:
        #     await self.event_bus.emit(
        #         RuntimeEvent(
        #             execution_id=execution_id,
        #             type=RuntimeEventType.DATA,
        #             source="output_files",
        #             message=f"Generated {len(output_files)} output file(s)",
        #             payload={"files": output_files},
        #         )
        #     )       


        # 计算执行耗时
        duration = time.time() - self._execution_start_time if self._execution_start_time else 0
        self._execution_start_time = None

        await self.event_bus.emit(
            RuntimeEvent(
                execution_id,
                RuntimeEventType.EXECUTION_COMPLETED,
                "engine",
                "Execution completed",
                payload={"duration": duration},
            )
        )

    async def stop(self):
        """安全停止"""
        if self.status != EngineStatus.RUNNING:
            return

        self.status = EngineStatus.STOPPING
        self._shutdown_event.set()

        # 发送停止事件
        if self._current_execution_id:
            duration = None
            if self._execution_start_time:
                duration = time.time() - self._execution_start_time
            await self.event_bus.emit(
                RuntimeEvent(
                    self._current_execution_id,
                    RuntimeEventType.EXECUTION_STOPPED,
                    "engine",
                    "Execution stopped by user",
                    payload={"duration": duration} if duration is not None else None
                )
            )

        if self._running_tasks:
            self.logger.info(f"Cancelling {len(self._running_tasks)} tasks...")
            for task in list(self._running_tasks):
                task.cancel()

            # 等待所有任务收尾
            await asyncio.gather(*self._running_tasks, return_exceptions=True)
            self._running_tasks.clear()

        self._ready_ports.clear()
        self.status = EngineStatus.IDLE
        # 清空执行相关状态
        self._current_execution_id = None
        self._execution_start_time = None
        self.logger.info("Engine stopped.")
