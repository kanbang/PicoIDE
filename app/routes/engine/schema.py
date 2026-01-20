


from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

# ==================== 执行请求数据模型 ====================

class NodePort(BaseModel):
    """节点端口定义"""

    id: str
    value: Any = ""

    model_config = ConfigDict(extra="ignore")


class NodePosition(BaseModel):
    """节点位置信息"""

    x: float
    y: float

    model_config = ConfigDict(extra="ignore")


class NodeData(BaseModel):
    """节点数据定义"""

    type: str  # 节点类型名称
    id: str  # 节点唯一ID
    title: str  # 节点显示标题
    inputs: Dict[str, NodePort]  # 输入端口配置
    outputs: Dict[str, NodePort]  # 输出端口
    position: NodePosition  # 画布位置
    width: int = 200  # 节点宽度
    twoColumn: bool = False  # 是否双列显示

    model_config = ConfigDict(extra="ignore")


class Connection(BaseModel):
    """节点连接定义"""

    id: str  # 连接唯一ID
    from_port: str = Field(..., alias="from")  # 源端口ID
    to: str  # 目标端口ID

    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    
  

class GraphData(BaseModel):
    """图数据定义"""

    id: str  # 图唯一ID
    nodes: List[NodeData]  # 节点列表
    connections: List[Connection]  # 连接列表
    inputs: List[Any] = []  # 图输入（预留）
    outputs: List[Any] = []  # 图输出（预留）
    panning: Optional[Dict[str, float]] = (
        None  # 注意：你的JSON中是平级字段，不是嵌套对象
    )
    scaling: Optional[float] = None  # 缩放比例

    model_config = ConfigDict(extra="ignore")


class FlowData(BaseModel):
    """图容器模型"""

    graph: GraphData
    graphTemplates: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(extra="ignore")


class ExecuteRequest(BaseModel):
    """执行请求模型"""
    business: Optional[str] = None
    scripts: Optional[List[str]] = None
    flow: Optional[FlowData] = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class ExecuteSavedRequest(BaseModel):
    """
    执行已保存的请求
    
    从存储中加载脚本和 flow 来执行
    
    支持两种模式：
    1. 默认模式：每次生成新的 execution_id（不提供 tag）
    2. Tag 模式：使用 tag 覆盖旧数据（提供 tag）
    
    Attributes:
        scripts_path: 脚本路径（如 "/blocks"）
        flow_id: Flow ID
        tag: 可选的标签（用于覆盖模式）
    """
    scripts_path: str = "/"  # 默认从根目录加载脚本
    flow_id: str  # Flow ID
    tag: Optional[str] = None  # 可选的标签


# ==================== 响应模型 ====================

class OutputFileInfo(BaseModel):
    """输出文件信息"""

    file_id: str
    execution_id: str
    filename: str
    file_path: str
    file_type: str
    file_size: Optional[int] = None
    created_at: str
    block_name: Optional[str] = None
    block_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    can_open: bool = True
    can_download: bool = True

    model_config = ConfigDict(extra="ignore")


class ExecutionStats(BaseModel):
    """执行统计信息"""

    total_nodes: int
    executed_nodes: int
    failed_nodes: int = 0
    skipped_nodes: int = 0
    total_connections: int
    execution_time: float
    peak_memory_mb: Optional[float] = None
    cache_hits: int = 0
    cache_misses: int = 0

    model_config = ConfigDict(extra="ignore")


class ExecuteResponse(BaseModel):
    """执行响应模型"""

    ok: bool
    result: str
    output_files: List[OutputFileInfo] = []
    execution_id: str
    execution_time: float
    timestamp: str
    stats: Optional[ExecutionStats] = None
    warnings: List[str] = []
    errors: List[str] = []

    model_config = ConfigDict(extra="ignore")
