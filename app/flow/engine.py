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


class Execution:
    def __init__(self, exec_id: str, engine: "ComputeEngine"):
        self.id = exec_id
        self.engine = engine
        self.status = EngineStatus.IDLE
        self.shutdown_event = asyncio.Event()
        self.running_tasks: Set[asyncio.Task] = set()
        self.start_time: Optional[float] = None
        self.ready_ports = defaultdict(set)  # key: node_id (str)
        # Per-execution instances to isolate state (instantiate here)
        self.instances: Dict[str, "Block"] = {}
        self._node_locks: Dict[str, asyncio.Lock] = {}
        port_map = {}  # Temporary for setup
        for n_data in self.engine.flow_data.get("nodes", []):
            n_id = n_data["id"]
            cls = self.engine.block_registry.get(n_data["type"])
            if not cls:
                raise ValueError(f"Unknown block type: {n_data['type']}")
            inst = cls()
            inst.instance_id = n_id
            self.instances[n_id] = inst
            self._node_locks[n_id] = asyncio.Lock()
            # Configure static options
            for k, v in n_data.get("inputs", {}).items():
                if k in inst._options:
                    inst.set_option(k, v.get("value"))
                else:
                    port_map[v["id"]] = (n_id, k)
            for k, v in n_data.get("outputs", {}).items():
                port_map[v["id"]] = (n_id, k)
        # No need to rebuild connections; use shared _graph

    async def _execute_node(self, n_id: str):
        if self.shutdown_event.is_set():
            return
        block = self.instances[n_id]
        try:
            await block.async_on_compute(self.id)
            await self.engine.event_bus.emit(
                RuntimeEvent(
                    self.id, RuntimeEventType.LOG, block.NAME, f"Node {n_id} completed"
                )
            )
            await self._trigger_successors(n_id)
        except asyncio.CancelledError:
            await self.engine.event_bus.emit(
                RuntimeEvent(
                    self.id, RuntimeEventType.ERROR, block.NAME, f"Node {n_id} cancelled"
                )
            )
            raise
        except Exception as e:
            self.engine.logger.error(
                f"Node {n_id} [{block.NAME}] execution failed: {e}", exc_info=True
            )
            await self.engine.event_bus.emit(
                RuntimeEvent(
                    self.id,
                    RuntimeEventType.ERROR,
                    block.NAME,
                    f"Node {n_id} failed: {str(e)}",
                )
            )

    async def _trigger_successors(self, n_id: str):
        if self.shutdown_event.is_set():
            return
        block = self.instances[n_id]
        output_snapshot = {k: copy.copy(v) for k, v in block._outputs.items()}
        for succ_id in list(self.engine._graph.successors(n_id)):
            succ_block = self.instances[succ_id]
            async with self._node_locks[succ_id]:
                slot_key = succ_id
                edges = self.engine._graph.get_edge_data(n_id, succ_id)
                for edge in edges.values():
                    in_port = edge["in_p"]
                    out_port = edge["out_p"]
                    succ_block._inputs[in_port] = output_snapshot.get(out_port)
                    self.ready_ports[slot_key].add(in_port)
                if len(self.ready_ports[slot_key]) >= self.engine._graph.in_degree(
                    succ_id
                ):
                    del self.ready_ports[slot_key]
                    task = asyncio.create_task(self._execute_node(succ_id))
                    self.running_tasks.add(task)
                    task.add_done_callback(self._task_done)

    async def _source_worker(self, n_id: str):
        block = self.instances[n_id]
        is_streaming = getattr(block, "STREAMING", False)
        while not self.shutdown_event.is_set():
            try:
                await block.async_on_compute(self.id)
                trigger_task = asyncio.create_task(self._trigger_successors(n_id))
                self.running_tasks.add(trigger_task)
                trigger_task.add_done_callback(self._task_done)
                if not is_streaming:
                    break
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.engine.logger.error(f"Source {n_id} error: {e}")
                await asyncio.sleep(1)

    def _task_done(self, task: asyncio.Task):
        # callback不能await，用loop.create_task(self.engine._complete_execution(...))
        self.running_tasks.discard(task)
        if not self.running_tasks:
            asyncio.create_task(self.engine._complete_execution(self.id, self.shutdown_event.is_set()))

    async def run(self):
        if self.status != EngineStatus.IDLE:
            self.engine.logger.warning(f"Execution {self.id} is already running.")
            await self.engine.event_bus.emit(
                RuntimeEvent(
                    self.id,
                    RuntimeEventType.EXECUTION_FAILED,
                    "engine",
                    "Execution is already running.",
                )
            )
            return
        self.status = EngineStatus.RUNNING
        self.start_time = time.time()
        await self.engine.event_bus.emit(
            RuntimeEvent(
                self.id,
                RuntimeEventType.STATUS,
                "engine",
                "Execution started",
                payload={"status": "running"},
            )
        )
        sources = [n for n, d in self.engine._graph.in_degree() if d == 0]
        if not sources:
            self.engine.logger.error("No source nodes found in flow!")
            await self.engine.event_bus.emit(
                RuntimeEvent(
                    self.id,
                    RuntimeEventType.EXECUTION_FAILED,
                    "engine",
                    "No source nodes found in flow!",
                )
            )
            self.engine.executions.pop(self.id, None)
            return
        for n_id in sources:
            task = asyncio.create_task(self._source_worker(n_id))
            self.running_tasks.add(task)
            task.add_done_callback(self._task_done)

    async def stop(self):
        if self.status != EngineStatus.RUNNING:
            return
        await self.engine._complete_execution(self.id, is_stopped=True)


class ComputeEngine:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.event_bus = RuntimeEventBus()
        self.logger = logger or logging.getLogger("ComputeEngine")
        file_collector.set_event_callback(self._on_file_generated)
        self.block_registry: Dict[str, Type["Block"]] = {}
        self._graph = nx.MultiDiGraph()
        self.flow_data: Dict[str, Any] = (
            {}
        )  # Store raw flow for per-execution instantiation
        self.executions: Dict[str, Execution] = {}

    def set_blocks(self, block_classes: List[Type["Block"]]):
        if self.executions:
            raise RuntimeError("Cannot set blocks while executions are running.")
        for cls in block_classes:
            if hasattr(cls, "NAME"):
                self.block_registry[cls.NAME] = cls
        self.logger.info(f"Registered {len(block_classes)} block types.")

    def set_flow(self, flow: Dict[str, Any]):
        if self.executions:
            raise RuntimeError("Cannot recompile flow while executions are running.")
        self._graph.clear()
        self.flow_data = copy.deepcopy(flow)  # Store for reuse
        port_map = {}
        # Temp instantiation for validation and graph building
        temp_instances = {}
        for n_data in flow["nodes"]:
            n_id = n_data["id"]
            cls = self.block_registry.get(n_data["type"])
            if not cls:
                raise ValueError(f"Unknown block type: {n_data['type']}")
            inst = cls()  # Temp for validation
            temp_instances[n_id] = inst
            self._graph.add_node(n_id)
            for k, v in n_data.get("inputs", {}).items():
                if k in inst._options:
                    pass  # Validate only
                else:
                    port_map[v["id"]] = (n_id, k)
            for k, v in n_data.get("outputs", {}).items():
                port_map[v["id"]] = (n_id, k)
        for conn in flow["connections"]:
            src = port_map.get(conn["from"])
            dst = port_map.get(conn["to"])
            if src and dst:
                self._graph.add_edge(src[0], dst[0], out_p=src[1], in_p=dst[1])
        if not nx.is_directed_acyclic_graph(self._graph):
            self.logger.warning(
                "Graph contains cycles. Ensure blocks handle feedback loops properly."
            )
        self.logger.info(f"Flow compiled: {len(flow['nodes'])} nodes.")

    def _on_file_generated(self, execution_id: str, node_type: str, file_info: Dict[str, Any]):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        file_event = RuntimeEvent(
            execution_id=execution_id,
            type=RuntimeEventType.FILE,
            source=node_type,
            message=f"Generated file: {file_info['filename']}",
            payload={"file": file_info},
            ts=time.time(),
        )
        if loop.is_running():
            asyncio.create_task(self.event_bus.emit(file_event))
        else:
            loop.run_until_complete(self.event_bus.emit(file_event))

    async def run(self, execution_id: str = "exec_001"):
        if execution_id in self.executions:
            self.logger.warning(f"Execution {execution_id} is already running.")
            await self.event_bus.emit(
                RuntimeEvent(
                    execution_id,
                    RuntimeEventType.EXECUTION_FAILED,
                    "engine",
                    "Execution is already running.",
                )
            )
            return
        execution = Execution(execution_id, self)
        self.executions[execution_id] = execution
        await execution.run()

    async def stop_execution(self, execution_id: str):
        execution = self.executions.get(execution_id)
        if execution:
            await execution.stop()

    async def stop_all(self):
        for exec_id in list(self.executions.keys()):
            await self.stop_execution(exec_id)

    async def _complete_execution(self, exec_id: str, is_stopped: bool):
        execution = self.executions.get(exec_id)
        if not execution:
            return
        
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

        duration = time.time() - execution.start_time if execution.start_time else 0
        event_type = (
            RuntimeEventType.EXECUTION_STOPPED
            if is_stopped
            else RuntimeEventType.EXECUTION_COMPLETED
        )
        message = "Execution stopped by user" if is_stopped else "Execution completed"
        await self.event_bus.emit(
            RuntimeEvent(
                exec_id, event_type, "engine", message, payload={"duration": duration}
            )
        )
        if is_stopped:
            execution.shutdown_event.set()
            execution.status = EngineStatus.STOPPING
            if execution.running_tasks:
                self.logger.info(
                    f"Cancelling {len(execution.running_tasks)} tasks for {exec_id}..."
                )
                for task in list(execution.running_tasks):
                    task.cancel()
                asyncio.gather(*execution.running_tasks, return_exceptions=True)
        else:
            execution.shutdown_event.set()
        execution.running_tasks.clear()
        execution.ready_ports.clear()
        execution.status = EngineStatus.IDLE
        del self.executions[exec_id]
        self.logger.info(
            f"Execution {exec_id} {'stopped' if is_stopped else 'completed'}."
        )
