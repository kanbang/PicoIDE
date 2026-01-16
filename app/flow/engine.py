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
        self._compiled_sequence: List[Tuple[Block, List[Tuple[Block, str, str]]]] = []

    def log(self, msg: str):
        if self.on_log: self.on_log(f"[Engine] {msg}")

    def register_blocks(self, blocks: List[Block]):
        for b in blocks: self.block_templates[b.name] = b

    def export_all_blocks(self) -> List[Dict]:
        """导出所有注册节点的配置描述"""
        return [b.export_config() for b in self.block_templates.values()]


    def set_schema(self, schema: Dict[str, Any]):
        self.log("🛠️  正在修复预编译逻辑以支持多重连接...")
        
        # --- 使用 MultiDiGraph 而不是 DiGraph ---
        temp_graph = nx.MultiDiGraph() 
        self.instances = {}
        port_to_node = {} 

        # 1. 节点实例化
        for node_data in schema["nodes"]:
            t_name = node_data["type"]
            n_id = node_data["id"]
            template = self.block_templates.get(t_name)
            
            if not template:
                continue

            instance = copy.deepcopy(template)
            instance.instance_id = n_id
            self.instances[n_id] = instance
            temp_graph.add_node(n_id)

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
                # --- 核心修改 2: MultiDiGraph 的 add_edge 不会覆盖旧边 ---
                temp_graph.add_edge(src[0], dst[0], out_p=src[1], in_p=dst[1])

        # 3. 环路检测 (MultiDiGraph 同样支持)
        try:
            nx.find_cycle(temp_graph, orientation="original")
            raise ValueError("Flowchart contains cycles")
        except nx.NetworkXNoCycle:
            pass

        # 4. 生成指令序列
        self._compiled_sequence = []
        # 注意：topological_sort 在 MultiDiGraph 上工作正常
        execution_order = list(nx.topological_sort(temp_graph))
        
        for n_id in execution_order:
            current_instance = self.instances[n_id]
            transfers = []
            
            # --- 核心修改 3: 遍历所有入边 (in_edges)，处理多重连接 ---
            # data=True 会返回我们存储在 edge 中的属性字典
            for pred_id, _, edge_data in temp_graph.in_edges(n_id, data=True):
                out_p = edge_data["out_p"]
                in_p = edge_data["in_p"]
                transfers.append((self.instances[pred_id], out_p, in_p))
            
            self._compiled_sequence.append((current_instance, transfers))

        self.log(f"✅ 编译完成。执行序列中包含多重数据流转指令。")

    def run(self, execution_id: str = None):
        """
        同步执行：针对工业主循环优化，达到 O(1) 调度性能
        
        Args:
            execution_id: 执行ID，用于追踪输出文件
        """
        self.log("🚀 开始同步执行流程...")
        try:
            for block, transfers in self._compiled_sequence:
                # 1. 极致高效的数据流转（纯内存指针访问）
                for src_block, src_port, dst_port in transfers:
                    block._inputs[dst_port] = src_block._outputs.get(src_port)
                
                # 2. 执行计算
                try:
                    block.on_compute(execution_id)
                    self.log(f"✅ 节点 {block.name} [{block.instance_id}] 执行完成")
                except Exception as e:
                    self.log(f"💥 节点 {block.name} [{block.instance_id}] 执行出错: {e}")
                    raise e
            self.log("✨ 流程全部同步执行完毕")
        except Exception as e:
            self.log(f"🛑 流程运行异常终止")

    async def async_run(self, execution_id: str = None):
        """
        异步执行：基于 Event 驱动的最大化并行调度
        
        Args:
            execution_id: 执行ID，用于追踪输出文件
        """
        self.log("🚀 开始异步并行执行...")
        
        # 1. 准备所有节点的事件
        done_events = {n_id: asyncio.Event() for n_id in self.instances}

        async def execute_node(n_id: str, block: Block, transfers: List[Tuple[Block, str, str]]):
            # 2. 等待当前节点的所有前驱节点完成
            # 我们通过 transfers 列表直接获取依赖的源 Block
            if transfers:
                # 提取所有源 Block 的 instance_id
                dependency_ids = [src_b.instance_id for src_b, _, _ in transfers]
                # 并行等待这些 ID 对应的 Event
                await asyncio.gather(*(done_events[dep_id].wait() for dep_id in dependency_ids))

            # 3. 静态数据搬运（此时前驱节点已确保 outputs 就绪）
            for src_block, src_port, dst_port in transfers:
                block._inputs[dst_port] = src_block._outputs.get(src_port)

            # 4. 执行异步计算逻辑
            try:
                # 调用 Block 的异步执行接口
                await block.async_on_compute(execution_id)
                self.log(f"✅ 节点 {block.name} [{block.instance_id}] 执行完成")
            except Exception as e:
                self.log(f"💥 节点 {block.name} [{block.instance_id}] 执行出错: {e}")
                raise e # 向上抛出以触发 gather 的异常终止
            finally:
                # 无论成功失败都必须 set，防止下游节点永久死锁
                done_events[n_id].set()

        # 5. 启动所有任务
        try:
            # 直接从预编译序列创建任务，保证数据一致性
            async_tasks = [
                execute_node(block.instance_id, block, transfers)
                for block, transfers in self._compiled_sequence
            ]
            
            await asyncio.gather(*async_tasks)
            self.log("✨ 异步流程全部执行完毕")
        except Exception as e:
            self.log(f"🛑 异步运行中断: {e}")