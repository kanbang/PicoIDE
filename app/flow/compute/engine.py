import asyncio
import networkx as nx
import traceback
from typing import Dict, List, Any, Callable, Optional
from dataclasses import asdict

class ComputeEngine:
    def __init__(self):
        self.registry: Dict[str, Any] = {} # 注册的 Block 模板
        self.instances: Dict[str, Any] = {}       # Schema 实例化的节点容器
        self.graph = nx.DiGraph()
        self.schema: Dict[str, Any] = {}
        # 默认日志处理器，可以被外部覆盖以对接到 UI 或 WebSocket
        self.on_log: Callable[[str], None] = print

    def log(self, message: str):
        """统一日志输出入口"""
        if self.on_log:
            self.on_log(message)

    def register_blocks(self, blocks: List[Any]):
        """注册可用的 Block 类型"""
        for block in blocks:
            # 使用 block 的 name 作为注册 key
            self.registry[block.name] = block
        self.log(f"✅ 已成功注册 {len(blocks)} 个节点类型。")

    def set_schema(self, schema: Dict[str, Any]):
        """根据 Schema 结构构建执行图并初始化节点实例"""
        self.log("🛠️  正在构建计算流图...")
        self.schema = schema
        self.instances = {}
        self.graph.clear()

        try:
            # 1. 实例化节点
            for node_data in schema["nodes"]:
                node_type = node_data["type"]
                node_id = node_data["id"]
                
                template = self.registry.get(node_type)
                if not template:
                    self.log(f"⚠️  警告: 找不到类型为 {node_type} 的模板，跳过节点 {node_id}")
                    continue

                # 创建实例：克隆模板的配置和 compute 函数
                import copy
                from types import MethodType
                
                # 简单模拟实例化过程，确保每个节点有独立的状态
                instance = copy.deepcopy(template)
                instance.name = node_data.get("title", template.name)
                
                # 设置选项值
                for opt_name, opt_meta in node_data.get("inputs", {}).items():
                    if opt_name in instance._options:
                        instance.set_option(opt_name, value=opt_meta["value"])

                self.instances[node_id] = instance
                self.graph.add_node(node_id)

            # 2. 建立连接关系 (用于数据传递和拓扑排序)
            # 建立 ID 到 (节点ID, 接口名) 的映射表
            interface_map = {}
            for node in schema["nodes"]:
                nid = node["id"]
                for name, meta in node["inputs"].items(): interface_map[meta["id"]] = (nid, name)
                for name, meta in node["outputs"].items(): interface_map[meta["id"]] = (nid, name)

            for conn in schema["connections"]:
                from_nid, from_port = interface_map.get(conn["from"], (None, None))
                to_nid, to_port = interface_map.get(conn["to"], (None, None))
                
                if from_nid and to_nid:
                    self.graph.add_edge(from_nid, to_nid, link=(from_port, to_port))

            self.log(f"✅ 计算流构建完成：{len(self.instances)} 个节点，{len(schema['connections'])} 条连线。")
        except Exception as e:
            self.log(f"❌ 构建过程中出现错误: {e}")

    def _transfer_data(self, target_node_id: str):
        """执行节点前，从上游输出端口拉取数据到下游输入端口"""
        for pred_id in self.graph.predecessors(target_node_id):
            edge_data = self.graph.get_edge_data(pred_id, target_node_id)
            out_name, in_name = edge_data["link"]
            
            val = self.instances[pred_id].get_interface(out_name)
            self.instances[target_node_id].set_interface(in_name, val)

    def run(self):
        """同步执行"""
        self.log("🚀 开始同步执行流程...")
        try:
            # 拓扑排序确保顺序
            order = list(nx.topological_sort(self.graph))
            for node_id in order:
                self._transfer_data(node_id)
                block = self.instances[node_id]
                try:
                    block._on_compute()
                    self.log(f"✅ 节点 {block.name} 执行完成")
                except Exception as e:
                    self.log(f"❌ 节点 {block.name} 执行出错: {e}")
                    raise e
            self.log("✨ 流程全部执行完毕")
        except nx.NetworkXUnfeasible:
            self.log("❌ 错误: 检测到循环依赖，无法执行")

    async def async_run(self):
        """异步执行 (支持并行运算)"""
        self.log("🚀 开始异步并行执行流程...")
        
        # 记录每个节点的 Future 对象
        node_tasks = {}
        
        async def execute_node_task(node_id):
            block = self.instances[node_id]
            
            # 1. 等待所有前置依赖节点完成
            predecessors = list(self.graph.predecessors(node_id))
            if predecessors:
                await asyncio.gather(*(node_tasks[p] for p in predecessors))
            
            # 2. 准备数据
            self._transfer_data(node_id)
            
            # 3. 执行计算
            try:
                if asyncio.iscoroutinefunction(block._on_compute):
                    await block._on_compute()
                else:
                    # 如果是同步函数，放入线程池避免阻塞
                    await asyncio.to_thread(block._on_compute)
                self.log(f"✅ 节点 {block.name} 执行完成")
            except Exception as e:
                self.log(f"❌ 节点 {block.name} 执行出错: {e}")
                # 打印详细堆栈方便调试
                # traceback.print_exc() 
                raise e

        # 创建所有节点的协程任务
        for node_id in self.instances:
            node_tasks[node_id] = asyncio.create_task(execute_node_task(node_id))

        try:
            await asyncio.gather(*node_tasks.values())
            self.log("✨ 异步流程全部执行完毕")
        except Exception:
            self.log("⚠️  由于某个节点执行失败，流程已中断")