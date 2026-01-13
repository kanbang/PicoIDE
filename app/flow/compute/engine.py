import copy
import time
import uuid
import asyncio
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Callable, Optional
from collections import defaultdict

class ComputeEngine:
    def __init__(self, block_registry: List[Any] = None):
        """
        Args:
            block_registry: Block 原型列表，自动解析 name 注册
        """
        
        # 1. 拓扑与映射存储
        self.schema: Optional[Dict] = None
        self.nodes: Dict[str, Any] = {}          # node_id -> Block Instance
        self.port_map: Dict[str, tuple] = {}     # port_id -> (node_id, port_name, port_type)
        self.connections_map = defaultdict(list) # from_port_id -> [to_port_id]
        self.adjacency = defaultdict(list)       # node_id -> [downstream_node_ids]
        self.initial_in_degree = defaultdict(int)# node_id -> input_connection_count
        self._output_port_cache = {}             # (node_id, port_name) -> port_id

        # 2. 外部反馈与同步
        self.event_handler: Optional[Callable[[Dict], None]] = None
        self._sync_lock = threading.Lock()
        
        # 3. 注册表初始化 (支持 List 输入并转为 Dict 以提高查找效率)
        self.registry: Dict[str, Any] = {}
        if block_registry:
            self.update_blocks(block_registry)

    def update_blocks(self, blocks: List[Any]):
        """友好提示：动态更新 Block 库"""
        self.registry.clear()
        for b in blocks:
            self.registry[b.name] = b
        self._emit("registry_updated", {"types": list(self.registry.keys())})

    def set_handler(self, handler: Callable[[Dict], None]):
        """设置反馈处理器，用于 UI 更新或日志记录"""
        self.event_handler = handler

    def _emit(self, event_type: str, data: Dict):
        """统一的信息反馈口"""
        if self.event_handler:
            self.event_handler({"timestamp": time.time(), "event": event_type, "data": data})

    def set_schema(self, schema: Dict):
        """外部接口：设置新的 Schema 并立即构建计算图"""
        self.schema = schema
        self._build_graph()

    def _build_graph(self):
        """逻辑参考：解析 JSON 建立节点实例与端口映射"""
        if not self.schema: return
        
        print("🛠️  正在构建计算图...")
        self.nodes.clear()
        self.port_map.clear()
        self.connections_map.clear()
        self.adjacency.clear()
        self.initial_in_degree.clear()
        self._output_port_cache.clear()

        try:
            # 1. 实例化节点
            for node_data in self.schema["nodes"]:
                node_id = node_data["id"]
                node_type = node_data["type"]
                node_title = node_data.get("title", node_type)
                
                if node_type not in self.registry:
                    self._emit("error", {"msg": f"未知的 Block 类型: {node_type}"})
                    raise ValueError(f"未知的 Block 类型: {node_type}")
                
                # 使用 deepcopy 确保实例独立
                instance = copy.deepcopy(self.registry[node_type])
                instance.name = f"{node_title}_{node_id[:4]}"
                self.nodes[node_id] = instance
                self.initial_in_degree[node_id] = 0

                # 2. 处理 Inputs/Options (友好区分参数与连接端口)
                for key, info in node_data.get("inputs", {}).items():
                    p_id, val = info["id"], info["value"]
                    if key in instance._options:
                        if val is not None: instance.set_option(key, val)
                    elif key in instance._inputs:
                        self.port_map[p_id] = (node_id, key, "input")

                # 3. 处理 Outputs
                for key, info in node_data.get("outputs", {}).items():
                    p_id = info["id"]
                    self.port_map[p_id] = (node_id, key, "output")
                    self._output_port_cache[(node_id, key)] = p_id

            # 4. 构建连接关系
            for conn in self.schema["connections"]:
                f_id, t_id = conn["from"], conn["to"]
                if f_id not in self.port_map or t_id not in self.port_map:
                    print(f"⚠️  警告: 发现悬空连接 {conn.get('id', 'unknown')}，跳过。")
                    continue
                
                f_node, _, _ = self.port_map[f_id]
                t_node, _, _ = self.port_map[t_id]
                self.connections_map[f_id].append(t_id)
                self.adjacency[f_node].append(t_node)
                self.initial_in_degree[t_node] += 1
            
            print(f"✅ 图构建完成: {len(self.nodes)} 个节点, {len(self.schema['connections'])} 条连接")
            self._emit("graph_ready", {"nodes": len(self.nodes)})

        except Exception as e:
            self._emit("error", {"stage": "build", "msg": str(e)})
            traceback.print_exc()

    # --- 公共逻辑：数据传播 ---
    def _propagate_data(self, node_id: str):
        block = self.nodes[node_id]
        for out_name, out_interface in block._outputs.items():
            src_p_id = self._output_port_cache.get((node_id, out_name))
            if src_p_id in self.connections_map:
                val = out_interface.value
                for target_p_id in self.connections_map[src_p_id]:
                    t_node_id, t_p_name, _ = self.port_map[target_p_id]
                    self.nodes[t_node_id].set_interface(t_p_name, val)

    # ==========================================
    # 模式一：异步并行 (asyncio)
    # ==========================================
    async def async_run(self):
        if not self.nodes: return
        print("🚀 [Async] 开始执行计算流程...")
        
        ctx = {
            'in_degree': self.initial_in_degree.copy(),
            'finished_count': 0,
            'event': asyncio.Event(),
            'failed': False
        }

        seeds = [nid for nid, deg in ctx['in_degree'].items() if deg == 0]
        for nid in seeds:
            asyncio.create_task(self._async_execute_task(nid, ctx))

        await ctx['event'].wait()
        print(f"🏁 [Async] 执行结束。共执行 {ctx['finished_count']} 个节点。")

    async def _async_execute_task(self, node_id: str, ctx: Dict):
        if ctx['failed']: return
        block = self.nodes[node_id]
        try:
            # 执行计算
            if hasattr(block, '_on_compute'):
                res = block._on_compute()
                if asyncio.iscoroutine(res): await res
            
            self._propagate_data(node_id)
            
            # 拓扑触发下游
            for next_id in set(self.adjacency[node_id]):
                ctx['in_degree'][next_id] -= 1
                if ctx['in_degree'][next_id] == 0:
                    asyncio.create_task(self._async_execute_task(next_id, ctx))
        except Exception as e:
            ctx['failed'] = True
            self._emit("node_error", {"node": block.name, "msg": str(e)})
            print(f"❌ 节点 {block.name} 执行出错: {e}")
            traceback.print_exc()
            ctx['event'].set() # 发生严重错误时提前终止等待
        finally:
            ctx['finished_count'] += 1
            if ctx['finished_count'] == len(self.nodes):
                ctx['event'].set()

    # ==========================================
    # 模式二：同步并行 (线程池)
    # ==========================================
    def run(self, max_workers: int = 4):
        if not self.nodes: return
        print("🚀 [Sync] 开始线程并行执行...")
        
        done_event = threading.Event()
        ctx = {
            'in_degree': self.initial_in_degree.copy(),
            'finished_count': 0,
            'done_event': done_event,
            'failed': False
        }

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            seeds = [nid for nid, deg in ctx['in_degree'].items() if deg == 0]
            for nid in seeds:
                executor.submit(self._sync_execute_task, nid, ctx, executor)
            
            done_event.wait()

        print(f"🏁 [Sync] 执行结束。共执行 {ctx['finished_count']} 个节点。")

    def _sync_execute_task(self, node_id: str, ctx: Dict, executor: ThreadPoolExecutor):
        if ctx['failed']: return
        block = self.nodes[node_id]
        try:
            self._emit("node_started", {"name": block.name})
            
            if hasattr(block, '_on_compute'):
                block._on_compute()
            
            self._propagate_data(node_id)
            
            with self._sync_lock:
                for next_id in set(self.adjacency[node_id]):
                    ctx['in_degree'][next_id] -= 1
                    if ctx['in_degree'][next_id] == 0:
                        executor.submit(self._sync_execute_task, next_id, ctx, executor)
        except Exception as e:
            ctx['failed'] = True
            self._emit("node_error", {"node": block.name, "msg": str(e)})
            print(f"❌ 节点 {block.name} 执行出错: {e}")
            traceback.print_exc()
            ctx['done_event'].set()
        finally:
            with self._sync_lock:
                ctx['finished_count'] += 1
                if ctx['finished_count'] == len(self.nodes):
                    ctx['done_event'].set()