import asyncio
import copy
from typing import Any, Dict, List
from node.block import Block
import networkx as nx


class ComputeEngine:
    def __init__(self):
        self.block_templates: Dict[str, Block] = {}
        self.instances: Dict[str, Block] = {}
        self.graph = nx.DiGraph()
        self.on_log = print

    def log(self, msg: str):
        if self.on_log:
            self.on_log(msg)

    def register_blocks(self, blocks: List[Block]):
        for b in blocks:
            self.block_templates[b.name] = b

    def export_all_blocks(self):
        """对应需求 3：导出所有注册节点的 JSON 描述"""
        return [b.export_config() for b in self.block_templates.values()]

    def set_schema(self, schema: Dict[str, Any]):
        """对应需求 4：解析复杂的 Scheme"""
        self.log("🛠️  正在构建计算流图...")
        self.instances = {}
        self.graph.clear()

        # 建立 ID 映射表，用于解析连接
        # interface_id -> (node_instance, port_name, type['in'|'out'])
        port_map = {}

        # 1. 创建实例并填充配置
        for node_data in schema["nodes"]:
            t_name = node_data["type"]
            n_id = node_data["id"]
            template = self.block_templates.get(t_name)

            if not template:
                self.log(f"⚠️  警告: 未知节点类型 {t_name}")
                continue

            # 使用 deepcopy 确保状态隔离
            instance = copy.deepcopy(template)
            instance.instance_id = n_id  # 记录实例ID

            # 处理配置项 (Options) 和 接口映射 (Interfaces)
            for key, info in node_data.get("inputs", {}).items():
                p_id = info["id"]
                val = info.get("value")

                if key in instance._options:
                    instance.set_option(key, val)
                else:
                    # 这是一个输入端口
                    port_map[p_id] = (n_id, key, "in")

            for key, info in node_data.get("outputs", {}).items():
                port_map[info["id"]] = (n_id, key, "out")

            self.instances[n_id] = instance
            self.graph.add_node(n_id)

        # 2. 建立连线
        for conn in schema["connections"]:
            source = port_map.get(conn["from"])
            target = port_map.get(conn["to"])
            if source and target:
                self.graph.add_edge(source[0], target[0], link=(source[1], target[1]))

        self.log(f"✅ 完成：构建了 {len(self.instances)} 个节点")

    def _transfer_data(self, target_id):
        """通用数据传递逻辑"""
        for pred_id in self.graph.predecessors(target_id):
            edge = self.graph.get_edge_data(pred_id, target_id)
            out_port, in_port = edge["link"]
            val = self.instances[pred_id]._outputs.get(out_port)
            self.instances[target_id]._inputs[in_port] = val

    def run(self):
        """同步执行：严格按拓扑顺序跑 on_compute"""
        self.log("🚀 开始同步执行流程...")
        try:
            order = list(nx.topological_sort(self.graph))
            for n_id in order:
                self._transfer_data(n_id)
                block = self.instances[n_id]
                try:
                    block.on_compute()  # <--- 执行同步方法
                    self.log(f"✅ 节点 {block.name} 执行完成")
                except Exception as e:
                    self.log(f"❌ 节点 {block.name} 执行出错: {e}")
                    raise e
            self.log("✨ 流程全部执行完毕")
        except nx.NetworkXUnfeasible:
            self.log("❌ 错误: 检测到循环依赖")

    async def async_run(self):
        """异步执行：利用 asyncio.Event 实现最大化并行执行 async_on_compute"""
        self.log("🚀 开始异步并行执行...")
        # 为每个节点创建一个完成事件
        done_events = {n_id: asyncio.Event() for n_id in self.instances}

        async def execute_node(n_id):
            block = self.instances[n_id]

            # 1. 等待所有前置依赖节点完成
            predecessors = list(self.graph.predecessors(n_id))
            if predecessors:
                await asyncio.gather(*(done_events[p].wait() for p in predecessors))

            # 2. 准备数据
            self._transfer_data(n_id)

            # 3. 执行异步计算
            try:
                await block.async_on_compute()  # <--- 执行异步方法
                self.log(f"✅ 节点 {block.name} 执行完成")
            except Exception as e:
                self.log(f"❌ 节点 {block.name} 执行出错: {e}")
                raise e
            finally:
                done_events[n_id].set()

        # 启动所有节点的协程，它们会根据依赖关系自动阻塞/运行
        tasks = [asyncio.create_task(execute_node(nid)) for nid in self.instances]
        await asyncio.gather(*tasks)
        self.log("✨ 异步流程全部执行完毕")
