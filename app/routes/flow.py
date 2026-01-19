"""
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-12 19:36:16
LastEditors: zhai
LastEditTime: 2026-01-13 08:26:48
"""

"""
Blocks 路由
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
import json
import time
from datetime import datetime

from node.run import make_dynamic_engine, get_json_blocks, run_schema
from services import list_dir, read_file, normalize_path


logger = logging.getLogger(__name__)

USER_ID = "default"

# 导入输出文件管理器配置
from node.output_manager import OutputConfig, output_file_manager

# 使用统一的输出目录配置
OUTPUT_DIR = OutputConfig.OUTPUT_DIR

router = APIRouter(prefix="/api/flow", tags=["blocks"])


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


class SchemaData(BaseModel):
    """图容器模型"""

    graph: GraphData
    graphTemplates: Optional[List[Dict[str, Any]]] = None

    model_config = ConfigDict(extra="ignore")


class ExecuteRequest(BaseModel):
    """执行请求模型"""

    scripts: Optional[List[str]] = None
    graph_schema: Optional[SchemaData] = Field(None, alias="schema")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


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


async def load_scripts_from_db(directory: str = "/blocks") -> List[str]:
    """从数据库指定目录递归加载所有 .py 文件内容"""
    scripts = []

    async def _load_recursive(path: str):
        """递归加载目录"""
        try:
            # 列出目录下的所有文件和子目录
            files = await list_dir(USER_ID, normalize_path(path))

            for file_info in files:
                name, file_type = file_info
                full_path = normalize_path(f"{path}/{name}")

                if file_type == 1:  # 文件
                    if name.endswith(".py"):
                        # 读取 .py 文件内容
                        content = await read_file(USER_ID, full_path)
                        if content:
                            scripts.append(content.decode("utf-8"))
                            logger.info(f"Loaded block script: {full_path}")
                elif file_type == 2:  # 目录
                    # 递归处理子目录
                    await _load_recursive(full_path)
        except Exception as e:
            logger.error(f"Error loading blocks from {path}: {str(e)}")

    await _load_recursive(directory)
    return scripts


def collect_output_files(execution_id: str) -> List[Dict[str, Any]]:
    """
    收集执行期间创建的输出文件（使用 execution_id 追踪）

    Args:
        execution_id: 执行ID

    Returns:
        输出文件列表
    """
    # 使用 OutputFileManager 获取执行关联的文件
    return output_file_manager.get_execution_files(execution_id)


@router.get("/blocks")
async def get_blocks():
    """
    获取所有可用的 blocks 定义
    """
    try:
        # 从数据库加载自定义 blocks
        scripts = await load_scripts_from_db("/")
        blocks = get_json_blocks(scripts)
        return {"blocks": blocks}
    except Exception as e:
        raise HTTPException(500, f"Failed to get blocks: {str(e)}")


@router.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest):

    try:
        if not request.graph_schema or not request.graph_schema.graph:
            raise HTTPException(400, "schema.graph is required")

        schema = request.graph_schema.graph

        # 2. 加载自定义脚本
        scripts = request.scripts or []

        scripts_db = await load_scripts_from_db("/")
        scripts.extend(scripts_db)

        # 3. 创建执行ID
        execution_id = output_file_manager.create_execution_id()

        # 4. 记录执行开始时间
        start_time = time.time()

        # 6. 执行 schema（传递 execution_id）
        result = await run_schema(scripts, schema.model_dump(by_alias=True), execution_id)

        # 收集输出文件（使用 execution_id）
        output_files = collect_output_files(execution_id)

        # 构建响应
        response = {
            "ok": True,
            "result": result,
            "output_files": output_files,
            "execution_id": execution_id,
            "execution_time": time.time() - start_time,
            "timestamp": datetime.now().isoformat(),
        }
        logger.info(
            f"执行完成，耗时: {response['execution_time']:.3f}s，输出文件: {len(output_files)}"
        )

        return response

    except ValueError as e:
        logger.error(f"参数验证失败: {str(e)}")
        raise HTTPException(400, detail=f"参数错误: {str(e)}")
    except Exception as e:
        logger.error(f"执行失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Execution failed: {str(e)}")

@router.get("/output-files")
async def get_output_files() -> List[Dict[str, Any]]:
    """
    获取所有输出文件列表
    """
    try:
        # 使用 OutputFileManager 获取所有文件
        files = output_file_manager.get_all_files()

        # 按创建时间倒序排序
        return sorted(files, key=lambda x: x["created_at"], reverse=True)
    except Exception as e:
        logger.error(f"获取输出文件失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to get output files: {str(e)}")


@router.get("/output-files/{file_id}")
async def get_output_file(file_id: str):
    """
    获取输出文件内容
    """
    try:
        # 使用 OutputFileManager 获取文件路径
        file_path = output_file_manager.get_file_path(file_id)

        if file_path is None or not file_path.exists():
            raise HTTPException(404, f"文件不存在: {file_id}")

        # 获取文件信息
        file_info = output_file_manager.get_file_info(file_id)
        filename = file_info["filename"] if file_info else file_id
        file_type = file_info["file_type"] if file_info else "unknown"

        # 根据文件类型设置正确的 MIME 类型
        mime_type_map = {
            "html": "text/html",
            "csv": "text/csv",
            "json": "application/json",
            "txt": "text/plain",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "pdf": "application/pdf",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xls": "application/vnd.ms-excel",
        }

        media_type = mime_type_map.get(file_type, "application/octet-stream")

        # 对于 HTML 文件，使用 inline 以便浏览器直接打开
        # 对于其他文件，使用 attachment 以便下载
        content_disposition = (
            "inline" if file_type == "html" else f'attachment; filename="{filename}"'
        )

        return FileResponse(
            file_path,
            filename=filename,
            media_type=media_type,
            headers={"Content-Disposition": content_disposition},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to get file: {str(e)}")


@router.delete("/output-files/{file_id}")
async def delete_output_file(file_id: str) -> Dict[str, Any]:
    """
    删除输出文件
    """
    try:
        # 使用 OutputFileManager 删除文件
        success = output_file_manager.delete_file(file_id)

        if not success:
            raise HTTPException(404, f"文件不存在: {file_id}")

        logger.info(f"已删除文件: {file_id}")

        return {"file_id": file_id, "status": "deleted", "message": "文件已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to delete file: {str(e)}")


@router.delete("/output-files/cleanup")
async def cleanup_output_files(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    清理旧输出文件
    """
    try:
        # 使用 OutputFileManager 清理旧文件
        result = output_file_manager.cleanup_old_files(max_age_hours)

        return {
            "status": "success",
            "message": f"已清理 {result['deleted_count']} 个超过 {max_age_hours} 小时的旧文件",
        }
    except Exception as e:
        logger.error(f"清理文件失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to cleanup files: {str(e)}")
