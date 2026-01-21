import asyncio
import networkx as nx
import logging
from typing import Any, Dict, List, Tuple, Type, Set
from collections import defaultdict

from flow.block import Block

class ComputeEngine:
    def __init__(self):
        self.block_registry: Dict[str, Type[Block]] = {}
        self.instances: Dict[str, Block] = {}
        self._graph = nx.MultiDiGraph()
        self.on_log = print
        
        # 运行时状态
        self.running_tasks: List[asyncio.Task] = []
        self._node_locks: Dict[str, asyncio.Lock] = {}
        # 记录每个节点当前等待了多少个前驱节点的信号
        self._ready_counts: Dict[str, int] = defaultdict(int)

    def log(self, msg: str):
        if self.on_log: self.on_log(f"[Engine] {msg}")

    def set_blocks(self, block_classes: List[Type[Block]]):
        for cls in block_classes:
            self.block_registry[cls.NAME] = cls
            self.log(f"已注册: {cls.NAME}")

    def set_flow(self, flow: Dict[str, Any]):
        self.log("🛠️ 正在编译计算图...")
        self._graph.clear()
        self.instances = {}
        port_to_node = {}

        # 1. 实例化
        for node_data in flow["nodes"]:
            n_id = node_data["id"]
            block_cls = self.block_registry.get(node_data["type"])
            if not block_cls: continue
            
            instance = block_cls()
            instance.instance_id = n_id
            self.instances[n_id] = instance
            self._node_locks[n_id] = asyncio.Lock()
            self._graph.add_node(n_id)

            for key, info in node_data.get("inputs", {}).items():
                if key in instance._options:
                    instance.set_option(key, info.get("value"))
                else:
                    port_to_node[info["id"]] = (n_id, key)
            for key, info in node_data.get("outputs", {}).items():
                port_to_node[info["id"]] = (n_id, key)

        # 2. 建立连接
        for conn in flow["connections"]:
            src = port_to_node.get(conn["from"])
            dst = port_to_node.get(conn["to"])
            if src and dst:
                self._graph.add_edge(src[0], dst[0], out_p=src[1], in_p=dst[1])
        
        self.log(f"✅ 图构建完成，节点数: {len(self.instances)}")

    async def _execute_single_node(self, n_id: str, execution_id: str):
        """执行单个节点并尝试触发下游"""
        block = self.instances[n_id]
        
        # 1. 执行计算
        try:# 1. 搬运数据
            for pred_id in self._graph.predecessors(n_id):
                pred_block = self.instances[pred_id]
                
                # 获取 pred_id 到 n_id 之间的所有边数据
                edges_dict = self._graph.get_edge_data(pred_id, n_id)
                if edges_dict:
                    for edge_data in edges_dict.values():
                        # edge_data 实际上就是我们 add_edge 时传入的字典
                        src_port = edge_data.get("out_p")
                        dst_port = edge_data.get("in_p")
                        
                        # 执行数据传递
                        block._inputs[dst_port] = pred_block._outputs.get(src_port)

            # 2. 执行计算
            await block.async_on_compute(execution_id)
            # self.log(f"DEBUG: 节点 {block.NAME}({n_id}) 执行完毕")
        except Exception as e:
            self.log(f"💥 节点 {n_id} 执行出错: {e}")
            return

        # 2. 通知下游节点
        for succ_id in self._graph.successors(n_id):
            asyncio.create_task(self._notify_node(succ_id, n_id, execution_id))

    async def _notify_node(self, n_id: str, from_id: str, execution_id: str):
        """
        下游节点被前驱通知：
        只有当所有前驱都 ready，才触发执行
        """
        async with self._node_locks[n_id]:
            self._ready_counts[n_id] += 1
            expected = self._graph.in_degree(n_id)
            
            if self._ready_counts[n_id] >= expected:
                self._ready_counts[n_id] = 0 # 重置计数器
                # 触发下游执行（不持有锁以允许并发）
                asyncio.create_task(self._execute_single_node(n_id, execution_id))

    async def _source_loop(self, n_id: str, execution_id: str):
        """源节点（入度为0）的常驻循环"""
        block = self.instances[n_id]
        self.log(f"📡 源节点启动: {block.NAME}")
        while True:
            try:
                # 阻塞直到源节点产生新数据（例如 MQTT 收到消息）
                await block.async_on_compute(execution_id)
                
                # 源节点完成后，立即通知其所有下游
                for succ_id in self._graph.successors(n_id):
                    asyncio.create_task(self._notify_node(succ_id, n_id, execution_id))
                
                # 防止非阻塞节点过快消耗 CPU
                await asyncio.sleep(0.001)
            except Exception as e:
                self.log(f"⚠️ 源节点 {n_id} 异常: {e}")
                await asyncio.sleep(1)

    async def start(self, execution_id: str = "stream_001"):
        """正式启动引擎"""
        self.log("🚀 事件驱动引擎启动中...")
        source_nodes = [n for n, d in self._graph.in_degree() if d == 0]
        
        if not source_nodes:
            self.log("❌ 流程中没有源节点(入度为0)，无法启动")
            return

        for n_id in source_nodes:
            task = asyncio.create_task(self._source_loop(n_id, execution_id))
            self.running_tasks.append(task)

        try:
            await asyncio.gather(*self.running_tasks)
        except asyncio.CancelledError:
            self.log("🛑 引擎已停止")


