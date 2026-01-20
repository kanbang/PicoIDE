import asyncio
import networkx as nx
from typing import Any, Dict, List, Tuple, Type, Optional
from flow.block import Block

class ComputeEngine:
    def __init__(self):
        # 存储类对象 Type[Block]
        self.block_registry: Dict[str, Type[Block]] = {}
        self.instances: Dict[str, Block] = {}
        self.on_log = print
        self._compiled_sequence: List[Tuple[Block, List[Tuple[Block, str, str]]]] = []

    def log(self, msg: str):
        if self.on_log: self.on_log(f"[Engine] {msg}")

    def register_blocks(self, block_classes: List[Type[Block]]):
        """
        核心优化：直接读取类属性 NAME 进行注册，无需实例化
        """
        for cls in block_classes:
            if not hasattr(cls, 'NAME') or cls.NAME is None:
                self.log(f"⚠️ 跳过无效注册：类 {cls.__name__} 未定义 NAME 属性")
                continue
            
            self.block_registry[cls.NAME] = cls
            self.log(f"已注册组件类: {cls.NAME} (Category: {getattr(cls, 'CATEGORY', 'Unknown')})")

    def export_all_blocks(self) -> List[Dict]:
        """
        导出所有注册节点的配置描述
        注意：options 等动态属性仍需一次临时实例化来解析 add_option 逻辑
        """
        configs = []
        for cls in self.block_registry.values():
            # 这里的实例化仅用于获取 export_config 产生的 UI 描述
            configs.append(cls().export_config())
        return configs

    def set_flow(self, flow: Dict[str, Any]):
        self.log("🛠️  正在构建计算图...")
        
        temp_graph = nx.MultiDiGraph() 
        self.instances = {}
        port_to_node = {} 

        # 1. 节点实例化
        for node_data in flow["nodes"]:
            t_name = node_data["type"]
            n_id = node_data["id"]
            
            block_cls = self.block_registry.get(t_name)
            if not block_cls:
                self.log(f"⚠️ 找不到类型为 {t_name} 的注册组件")
                continue

            # 直接实例化
            instance = block_cls()
            instance.instance_id = n_id
            self.instances[n_id] = instance
            temp_graph.add_node(n_id)

            # 配置选项处理
            for key, info in node_data.get("inputs", {}).items():
                p_id = info["id"]
                if key in instance._options:
                    instance.set_option(key, info.get("value"))
                else:
                    port_to_node[p_id] = (n_id, key)

            for key, info in node_data.get("outputs", {}).items():
                port_to_node[info["id"]] = (n_id, key)

        # 2. 建立逻辑连接
        for conn in flow["connections"]:
            src = port_to_node.get(conn["from"])
            dst = port_to_node.get(conn["to"])
            if src and dst:
                temp_graph.add_edge(src[0], dst[0], out_p=src[1], in_p=dst[1])

        # 3. 环路检测
        try:
            nx.find_cycle(temp_graph, orientation="original")
            raise ValueError("Flowchart contains cycles")
        except nx.NetworkXNoCycle:
            pass

        # 4. 生成指令序列 (拓扑排序)
        self._compiled_sequence = []
        execution_order = list(nx.topological_sort(temp_graph))
        
        for n_id in execution_order:
            current_instance = self.instances[n_id]
            transfers = []
            
            for pred_id, _, edge_data in temp_graph.in_edges(n_id, data=True):
                out_p = edge_data["out_p"]
                in_p = edge_data["in_p"]
                transfers.append((self.instances[pred_id], out_p, in_p))
            
            self._compiled_sequence.append((current_instance, transfers))

        self.log(f"✅ 编译完成。")

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
                # 提取所有源 Block 的 instance_id，去重
                dependency_ids = list({src_b.instance_id for src_b, _, _ in transfers})

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


# TODO
# 多条线 → 同一个 input

# 👉 建议明确三种输入策略（至少设计层面）：

# 策略	行为
# single	后写覆盖前写
# list	append
# dict	按 src_id 存