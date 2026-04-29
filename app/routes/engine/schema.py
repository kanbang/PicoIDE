from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class ExecuteSavedRequest(BaseModel):
    """
    执行已保存流程的请求。

    Attributes:
        scripts_path: 动态脚本目录，默认从根目录加载。
        flow_id: 已保存的流程 ID。
        tag: 可选标签；提供时会先清理同标签旧执行记录。
    """

    scripts_path: str = "/"
    flow_id: str
    tag: Optional[str] = None


class OutputFileInfo(BaseModel):
    """输出文件信息。"""

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
    """执行统计信息。"""

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


class StartExecutionResponse(BaseModel):
    """启动执行接口的响应。"""

    ok: bool = True
    execution_id: str
    status: str = "running"
    timestamp: str

    model_config = ConfigDict(extra="ignore")
