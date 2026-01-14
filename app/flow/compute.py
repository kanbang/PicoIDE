import asyncio
import copy
import networkx as nx
from typing import Any, Dict, List, Tuple
from flow.block import Block

class ComputeEngine:
    def __init__(self):
        self.block_templates: Dict[str, Block] = {}
        self.instances: Dict[str, Block] = {}
        self.on_log = print
        
        # 预编译生成的执行指令集：[(当前节点, [(源节点, 源端口, 目标端口), ...]), ...]
        # 这种结构在 run 时完全避开了字典查找，直接操作对象指针
        self._compiled_sequence: List[Tuple[Block, List[Tuple[Block, str, str]]]] = []

    def log(self, msg: str):
        if self.on_log:
            self.on_log(f"[Engine] {msg}")

    def register_blocks(self, blocks: List[Block]):
        """注册 Block 模板库"""
        for b in blocks:
            self.block_templates[b.name] = b

    def export_all_blocks(self) -> List[Dict]:
        """导出所有注册节点的配置描述"""
        return [b.export_config() for b in self.block_templates.values()]

    def set_schema(self, schema: Dict[str, Any]):
        """
        静态编译阶段：解析、校验、排序并生成高性能执行指令
        """
        self.log("🛠️  正在预编译流图并进行静态安全检查...")
        
        temp_graph = nx.DiGraph()
        self.instances = {}
        port_to_node = {} # 临时映射：port_id -> (node_id, port_name)

        # 1. 节点实例化与配置解析
        for node_data in schema["nodes"]:
            t_name = node_data["type"]
            n_id = node_data["id"]
            template = self.block_templates.get(t_name)
            
            if not template:
                self.log(f"⚠️  警告: 找不到类型为 {t_name} 的 Block 模板")
                continue

            # 使用 deepcopy 实现状态隔离，每个实例独立运行
            instance = copy.deepcopy(template)
            instance.instance_id = n_id  # 关键：注入 ID 用于日志寻址
            self.instances[n_id] = instance
            temp_graph.add_node(n_id)

            # 解析端口与配置项
            for key, info in node_data.get("inputs", {}).items():
                p_id = info["id"]
                if key in instance._options:
                    instance.set_option(key, info.get("value"))
                else:
                    port_to_node[p_id] = (n_id, key)

            for key, info in node_data.get("outputs", {}).items():
                port_to_node[info["id"]] = (n_id, key)

        # 2. 建立逻辑连接
        for conn in schema["connections"]:
            src = port_to_node.get(conn["from"])
            dst = port_to_node.get(conn["to"])
            if src and dst:
                # src[0] 是 node_id, src[1] 是端口名
                temp_graph.add_edge(src[0], dst[0], link=(src[1], dst[1]))

        # 3. 工业级安全校验：环路检测
        try:
            cycle = list(nx.find_cycle(temp_graph, orientation="original"))
            self.log(f"❌ 关键错误: 检测到环路依赖 {cycle}。编译终止。")
            raise ValueError("Flowchart contains cycles")
        except nx.NetworkXNoCycle:
            pass

        # 4. 极致性能编译：生成指令序列
        self._compiled_sequence = []
        execution_order = list(nx.topological_sort(temp_graph))
        
        for n_id in execution_order:
            current_instance = self.instances[n_id]
            transfers = []
            
            # 找到所有前驱节点，预存其引用
            for pred_id in temp_graph.predecessors(n_id):
                edge = temp_graph.get_edge_data(pred_id, n_id)
                out_p, in_p = edge["link"]
                transfers.append((self.instances[pred_id], out_p, in_p))
            
            self._compiled_sequence.append((current_instance, transfers))

        self.log(f"✅ 完成：构建了 {len(self.instances)} 个节点，执行序列已就绪")

    def run(self):
        """
        同步执行：针对工业主循环优化，达到 O(1) 调度性能
        """
        self.log("🚀 开始同步执行流程...")
        try:
            for block, transfers in self._compiled_sequence:
                # 1. 极致高效的数据流转（纯内存指针访问）
                for src_block, src_port, dst_port in transfers:
                    block._inputs[dst_port] = src_block._outputs.get(src_port)
                
                # 2. 执行计算
                try:
                    block.on_compute()
                    self.log(f"✅ 节点 {block.name} [{block.instance_id}] 执行完成")
                except Exception as e:
                    self.log(f"💥 节点 {block.name} [{block.instance_id}] 执行出错: {e}")
                    raise e
            self.log("✨ 流程全部同步执行完毕")
        except Exception as e:
            self.log(f"🛑 流程运行异常终止")

    async def async_run(self):
        """
        异步执行：基于 Event 驱动的最大化并行调度
        """
        self.log("🚀 开始异步并行执行...")
        done_events = {n_id: asyncio.Event() for n_id in self.instances}

        async def execute_node(n_id: str, block: Block, transfers: List[Tuple[Block, str, str]]):
            # 1. 等待所有父节点完成（并行监听）
            parent_ids = [nid for nid, b in self.instances.items() if any(t[0] == b for t in transfers)]
            if parent_ids:
                await asyncio.gather(*(done_events[pid].wait() for pid in parent_ids))

            # 2. 准备数据流
            for src_block, src_port, dst_port in transfers:
                block._inputs[dst_port] = src_block._outputs.get(src_port)

            # 3. 异步计算
            try:
                await block.async_on_compute()
                self.log(f"✅ 节点 {block.name} [{block.instance_id}] 执行完成")
            except Exception as e:
                self.log(f"💥 节点 {block.name} [{block.instance_id}] 执行出错: {e}")
                raise e
            finally:
                done_events[n_id].set()

        # 并发启动所有节点
        try:
            tasks = [
                execute_node(nid, block, trans) 
                for nid, (block, trans) in zip(self.instances.keys(), [s[1] for s in self._compiled_sequence])
            ]
            # 修正：我们需要按实例查找 transfers，这里通过预编译序列更安全
            async_tasks = []
            for n_id, inst in self.instances.items():
                # 找到该实例对应的 transfers
                _, trans = next(item for item in self._compiled_sequence if item[0] == inst)
                async_tasks.append(execute_node(n_id, inst, trans))

            await asyncio.gather(*async_tasks)
            self.log("✨ 异步流程全部执行完毕")
        except Exception as e:
            self.log(f"🛑 异步运行中断: {e}")