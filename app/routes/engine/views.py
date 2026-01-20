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
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
import time
from datetime import datetime

from .schema import ExecuteRequest, ExecuteResponse, ExecuteSavedRequest
from node.run import make_dynamic_engine, get_json_blocks, run_flow
from services import list_dir, read_file, normalize_path
from routes.flow.service import get_flow
from uuid import UUID
from node.output_manager import output_file_manager
from node.file_collector import file_collector
from node.settings import settings


logger = logging.getLogger(__name__)

USER_ID = "default"


router = APIRouter(prefix="/api/engine", tags=["engine"])


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
    """
    执行图计算（直接执行）

    执行流程：
    1. 验证请求参数
    2. 加载自定义脚本
    3. 解析图结构
    4. 创建执行记录
    5. 执行计算
    6. 收集输出文件并保存到数据库
    7. 更新执行状态
    8. 返回结果
    """

    try:
        if not request.flow or not request.flow.graph:
            raise HTTPException(400, "flow.graph is required")

        flow = request.flow.graph

        # 1. 加载自定义脚本
        scripts = request.scripts or []
        scripts_db = await load_scripts_from_db("/")
        scripts.extend(scripts_db)

        # 2. 计算脚本哈希
        from utils.helpers import calculate_scripts_hash
        scripts_hash = calculate_scripts_hash(scripts)

        # 3. 创建执行ID
        execution_id = output_file_manager.create_execution_id()

        # 4. 根据配置决定是否创建 Execution 记录
        execution = None
        if settings.ENABLE_DB_WRITE:
            from db import Execution
            execution = await Execution.create(
                execution_id=execution_id,
                user_id=USER_ID,
                source="direct",
                scripts_path="/",
                scripts_hash=scripts_hash,
                status="running",
                start_time=datetime.now(),
                total_nodes=len(flow.nodes),
            )

        # 5. 记录执行开始时间
        start_time = time.time()

        # 6. 执行 flow（传递 execution_id）
        try:
            result = await run_flow(scripts, flow.model_dump(by_alias=True), execution_id)

            # 收集输出文件
            # 根据配置决定从数据库还是收集器获取
            if settings.ENABLE_DB_WRITE:
                output_files = await output_file_manager.get_execution_files(execution_id)
            else:
                # 从文件收集器获取（轻量化模式）
                output_files = file_collector.get_files(execution_id)

            # 更新 Execution 状态为完成
            if execution:
                execution.status = "completed"
                execution.end_time = datetime.now()
                execution.execution_time = time.time() - start_time
                execution.executed_nodes = execution.total_nodes
                execution.result = str(result)[:1000] if result else None
                await execution.save()

            # 构建响应
            response = {
                "ok": True,
                "result": result,
                "output_files": output_files,
                "execution_id": execution_id,
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
                "stats": {
                    "total_nodes": len(flow.nodes),
                    "executed_nodes": len(flow.nodes),
                    "failed_nodes": 0,
                    "total_connections": len(flow.connections),
                    "execution_time": time.time() - start_time,
                }
            }
            logger.info(
                f"执行完成，耗时: {response['execution_time']:.3f}s，输出文件: {len(output_files)}"
            )

            return response

        except Exception as e:
            # 更新 Execution 状态为失败
            if execution:
                execution.status = "failed"
                execution.end_time = datetime.now()
                execution.execution_time = time.time() - start_time
                execution.result = f"Error: {str(e)}"[:1000]
                await execution.save()
            raise

    except ValueError as e:
        logger.error(f"参数验证失败: {str(e)}")
        raise HTTPException(400, detail=f"参数错误: {str(e)}")
    except Exception as e:
        logger.error(f"执行失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Execution failed: {str(e)}")


@router.post("/execute-saved", response_model=ExecuteResponse)
async def execute_saved(request: ExecuteSavedRequest):
    """
    执行已保存的图

    支持两种模式：
    1. 默认模式：每次生成新的 execution_id（不提供 tag）
    2. Tag 模式：使用 tag 覆盖旧数据（提供 tag）

    执行流程：
    1. 从存储加载 graph
    2. 从存储加载脚本
    3. 如果是 tag 模式，清理旧数据
    4. 创建执行记录
    5. 执行计算
    6. 收集输出文件并保存到数据库
    7. 更新执行状态
    8. 返回结果
    """
    try:
        logger.info(f"Execute From DB Request - Flow ID: {request.flow_id}, Scripts Path: {request.scripts_path}, Tag: {request.tag}")

        # 1. 从数据库加载 graph
        flow_db = await get_flow(USER_ID, UUID(request.flow_id))
        if not flow_db:
            raise HTTPException(404, f"Flow not found: {request.flow_id}")

        # 获取 flow 数据
        flow_data = flow_db.flow
        if not flow_data or "graph" not in flow_data:
            raise HTTPException(400, "Flow data is invalid or missing graph")

        graph = flow_data["graph"]

        # 2. 从数据库加载脚本
        scripts = await load_scripts_from_db(request.scripts_path)
        logger.info(f"从数据库加载了 {len(scripts)} 个脚本")

        # 3. 计算脚本哈希
        from utils.helpers import calculate_scripts_hash
        scripts_hash = calculate_scripts_hash(scripts)

        # 4. 确定 execution_id 和清理策略
        if request.tag:
            # Tag 模式：清理旧数据
            if settings.ENABLE_DB_WRITE:
                await cleanup_tag_execution(USER_ID, request.tag)
            execution_id = f"{request.tag}_{int(time.time())}"
            source = "tag"
        else:
            # 默认模式：生成新 ID
            execution_id = output_file_manager.create_execution_id()
            source = "saved"

        # 5. 根据配置决定是否创建 Execution 记录
        execution = None
        if settings.ENABLE_DB_WRITE:
            from db import Execution
            execution = await Execution.create(
                execution_id=execution_id,
                user_id=USER_ID,
                source=source,
                flow_id=UUID(request.flow_id),
                tag=request.tag,
                scripts_path=request.scripts_path,
                scripts_hash=scripts_hash,
                status="running",
                start_time=datetime.now(),
                total_nodes=len(graph.get("nodes", [])),
            )

        # 6. 记录执行开始时间
        start_time = time.time()

        # 7. 执行 flow（传递 execution_id）
        try:
            result = await run_flow(scripts, graph, execution_id)

            # 收集输出文件
            # 根据配置决定从数据库还是收集器获取
            if settings.ENABLE_DB_WRITE:
                output_files = await output_file_manager.get_execution_files(execution_id)
            else:
                # 从文件收集器获取（轻量化模式）
                output_files = file_collector.get_files(execution_id)
         
            # 更新 Execution 状态为完成
            if execution:
                execution.status = "completed"
                execution.end_time = datetime.now()
                execution.execution_time = time.time() - start_time
                execution.executed_nodes = execution.total_nodes
                execution.result = str(result)[:1000] if result else None
                await execution.save()

            # 8. 构建响应
            response = {
                "ok": True,
                "result": result,
                "output_files": output_files,
                "execution_id": execution_id,
                "execution_time": time.time() - start_time,
                "timestamp": execution.start_time.isoformat() if execution else datetime.now().isoformat(),
                "stats": {
                    "total_nodes": len(graph.get("nodes", [])),
                    "executed_nodes": len(graph.get("nodes", [])),
                    "failed_nodes": 0,
                    "total_connections": len(graph.get("connections", [])),
                    "execution_time": time.time() - start_time,
                }
            }
            logger.info(
                f"从数据库执行完成，耗时: {response['execution_time']:.3f}s，输出文件: {len(output_files)}"
            )

            return response

        except Exception as e:
            # 更新 Execution 状态为失败
            if execution:
                execution.status = "failed"
                execution.end_time = datetime.now()
                execution.execution_time = time.time() - start_time
                execution.result = f"Error: {str(e)}"[:1000]
                await execution.save()
            raise

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从数据库执行失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Execution from DB failed: {str(e)}")


async def cleanup_tag_execution(user_id: str, tag: str):
    """
    清理指定 tag 的旧执行记录和输出文件

    Args:
        user_id: 用户ID
        tag: 标签
    """
    # 只在启用数据库时才执行清理
    if not settings.ENABLE_DB_WRITE:
        logger.info(f"数据库写入已禁用，跳过 tag '{tag}' 的清理")
        return
    
    from db import Execution, Output

    # 1. 查找同一 tag 的旧执行记录
    old_executions = await Execution.filter(
        user_id=user_id,
        tag=tag
    ).all()

    for old_exec in old_executions:
        # 2. 软删除关联的 Output 记录
        await Output.filter(
            execution_id=old_exec.execution_id
        ).update(is_deleted=True, deleted_at=datetime.now())

        # 3. 删除旧的 Execution 记录
        await old_exec.delete()

        logger.info(f"已清理 tag '{tag}' 的旧执行: {old_exec.execution_id}")


@router.get("/output-files")
async def get_output_files(
    execution_id: Optional[str] = None,
    file_type: Optional[str] = None,
    is_deleted: bool = False,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    获取输出文件列表（支持过滤和分页）

    支持过滤：
    - execution_id: 按执行ID过滤
    - file_type: 按文件类型过滤
    - is_deleted: 是否包含已删除文件
    - limit: 返回数量限制
    - offset: 偏移量
    """
    try:
        files = []
        
        if settings.ENABLE_DB_WRITE:
            # 从数据库获取
            files = await output_file_manager.get_all_files(
                execution_id=execution_id,
                file_type=file_type,
                is_deleted=is_deleted,
                limit=limit,
                offset=offset
            )
        else:
            # 从收集器获取（轻量化模式）
            if execution_id:
                files = file_collector.get_files(execution_id)
            else:
                # 如果没有指定 execution_id，获取所有执行的文件
                # 注意：收集器不支持跨执行查询，这里只返回空列表
                files = []
            
            # 应用过滤
            if file_type:
                files = [f for f in files if f.get("file_type") == file_type]
            
            # 应用分页
            files = files[offset:offset + limit]

        return {
            "files": files,
            "count": len(files),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"获取输出文件失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to get output files: {str(e)}")


@router.get("/output-files/{file_id}")
async def get_output_file(file_id: str):
    """
    获取输出文件内容
    """
    try:
        # 先尝试从数据库获取文件信息
        file_info = await output_file_manager.get_file_info(file_id)
        
        # 如果数据库中没有，尝试从收集器获取（轻量化模式）
        if not file_info and not settings.ENABLE_DB_WRITE:
            # 从 file_id 提取 execution_id
            # file_id 格式: {execution_id}_{random}
            parts = file_id.rsplit('_', 1)
            if len(parts) == 2:
                execution_id = parts[0]
                files = file_collector.get_files(execution_id)
                for f in files:
                    if f["file_id"] == file_id:
                        file_info = f
                        break

        if not file_info:
            raise HTTPException(404, f"文件不存在: {file_id}")

        file_path = Path(file_info["file_path"])

        if not file_path.exists():
            raise HTTPException(404, f"文件不存在: {file_id}")

        filename = file_info["filename"]
        file_type = file_info["file_type"]

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
    删除输出文件（软删除）
    """
    try:
        # 先尝试从数据库删除
        success = await output_file_manager.delete_file(file_id, soft_delete=True)
        
        # 如果数据库中没有且处于轻量化模式，从收集器中删除
        if not success and not settings.ENABLE_DB_WRITE:
            # 从 file_id 提取 execution_id
            parts = file_id.rsplit('_', 1)
            if len(parts) == 2:
                execution_id = parts[0]
                files = file_collector.get_files(execution_id)
                # 从收集器中移除该文件
                file_collector._files[execution_id] = [f for f in files if f["file_id"] != file_id]
                success = True

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
        result = await output_file_manager.cleanup_old_files(max_age_hours)

        return {
            "status": "success",
            "message": f"已清理 {result['deleted_count']} 个超过 {max_age_hours} 小时的旧文件",
        }
    except Exception as e:
        logger.error(f"清理文件失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to cleanup files: {str(e)}")


# ==================== 执行历史查询接口 ====================


@router.get("/executions")
async def get_executions(
    status: Optional[str] = None,
    source: Optional[str] = None,
    tag: Optional[str] = None,
    flow_id: Optional[str] = None,
    scripts_hash: Optional[str] = None,
    include_outputs: bool = False,
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """
    获取执行历史列表

    支持过滤和分页：
    - status: 按状态过滤 (running, completed, failed)
    - source: 按来源过滤 (direct, saved, tag)
    - tag: 按 tag 过滤
    - flow_id: 按 flow ID 过滤
    - scripts_hash: 按脚本哈希过滤
    - include_outputs: 是否包含输出文件列表（当 flow_id 指定时）
    - limit: 返回数量限制
    - offset: 偏移量
    """
    try:
        from db import Execution

        query = Execution.filter(user_id=USER_ID)

        if status:
            query = query.filter(status=status)

        if source:
            query = query.filter(source=source)

        if tag:
            query = query.filter(tag=tag)

        if flow_id:
            query = query.filter(flow_id=UUID(flow_id))

        if scripts_hash:
            query = query.filter(scripts_hash=scripts_hash)

        executions = await query.order_by("-start_time").limit(limit).offset(offset).all()

        # 如果需要包含输出文件且指定了 flow_id
        if include_outputs and flow_id:
            # 获取所有相关的 execution_id
            execution_ids = [e.execution_id for e in executions]
            
            # 批量获取所有输出文件
            from db import Output
            outputs = await Output.filter(
                execution_id__in=execution_ids,
                is_deleted=False
            ).all()
            
            # 按 execution_id 分组
            outputs_by_execution = {}
            for o in outputs:
                if o.execution_id not in outputs_by_execution:
                    outputs_by_execution[o.execution_id] = []
                outputs_by_execution[o.execution_id].append({
                    "file_id": o.file_id,
                    "execution_id": o.execution_id,
                    "filename": o.filename,
                    "file_path": o.file_path,
                    "file_type": o.file_type,
                    "file_size": o.file_size,
                    "created_at": o.created_at.isoformat(),
                    "block_name": o.block_name,
                    "block_id": o.block_id,
                    "description": o.description,
                    "metadata": o.metadata,
                    "can_open": o.file_type in output_file_manager.settings.BROWSER_OPENABLE,
                    "can_download": True,
                })
            
            # 构建响应，包含输出文件
            executions_data = []
            for e in executions:
                exec_data = {
                    "execution_id": e.execution_id,
                    "user_id": e.user_id,
                    "source": e.source,
                    "flow_id": str(e.flow_id) if e.flow_id else None,
                    "tag": e.tag,
                    "scripts_path": e.scripts_path,
                    "scripts_hash": e.scripts_hash,
                    "status": e.status,
                    "result": e.result,
                    "total_nodes": e.total_nodes,
                    "executed_nodes": e.executed_nodes,
                    "failed_nodes": e.failed_nodes,
                    "execution_time": e.execution_time,
                    "start_time": e.start_time.isoformat(),
                    "end_time": e.end_time.isoformat() if e.end_time else None,
                    "metadata": e.metadata,
                    "output_files": outputs_by_execution.get(e.execution_id, []),
                    "output_files_count": len(outputs_by_execution.get(e.execution_id, [])),
                }
                executions_data.append(exec_data)
        else:
            # 不包含输出文件
            executions_data = [
                {
                    "execution_id": e.execution_id,
                    "user_id": e.user_id,
                    "source": e.source,
                    "flow_id": str(e.flow_id) if e.flow_id else None,
                    "tag": e.tag,
                    "scripts_path": e.scripts_path,
                    "scripts_hash": e.scripts_hash,
                    "status": e.status,
                    "result": e.result,
                    "total_nodes": e.total_nodes,
                    "executed_nodes": e.executed_nodes,
                    "failed_nodes": e.failed_nodes,
                    "execution_time": e.execution_time,
                    "start_time": e.start_time.isoformat(),
                    "end_time": e.end_time.isoformat() if e.end_time else None,
                    "metadata": e.metadata,
                }
                for e in executions
            ]

        return {
            "executions": executions_data,
            "count": len(executions),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        logger.error(f"获取执行历史失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to get executions: {str(e)}")


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str) -> Dict[str, Any]:
    """
    获取单个执行详情
    """
    try:
        from db import Execution

        execution = await Execution.filter(
            user_id=USER_ID,
            execution_id=execution_id
        ).first()

        if not execution:
            raise HTTPException(404, f"Execution not found: {execution_id}")

        return {
            "execution_id": execution.execution_id,
            "user_id": execution.user_id,
            "source": execution.source,
            "flow_id": str(execution.flow_id) if execution.flow_id else None,
            "tag": execution.tag,
            "scripts_path": execution.scripts_path,
            "scripts_hash": execution.scripts_hash,
            "status": execution.status,
            "result": execution.result,
            "total_nodes": execution.total_nodes,
            "executed_nodes": execution.executed_nodes,
            "failed_nodes": execution.failed_nodes,
            "execution_time": execution.execution_time,
            "start_time": execution.start_time.isoformat(),
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "metadata": execution.metadata,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行详情失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to get execution: {str(e)}")


@router.get("/executions/{execution_id}/outputs")
async def get_execution_outputs(
    execution_id: str,
    file_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    获取执行的所有输出文件
    """
    try:
        # 验证执行是否存在
        from db import Execution

        logger.info(f"get_execution_outputs - 查询执行ID: {execution_id}")

        execution = await Execution.filter(
            user_id=USER_ID,
            execution_id=execution_id
        ).first()

        if not execution:
            logger.warning(f"get_execution_outputs - 执行不存在: {execution_id}")
            raise HTTPException(404, f"Execution not found: {execution_id}")

        # 获取输出文件
        output_files = await output_file_manager.get_all_files(
            execution_id=execution_id,
            file_type=file_type,
            is_deleted=False,
            limit=limit,
            offset=offset
        )

        logger.info(f"get_execution_outputs - 找到 {len(output_files)} 个输出文件")

        return {
            "execution_id": execution_id,
            "outputs": output_files,
            "count": len(output_files),
            "limit": limit,
            "offset": offset,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行输出文件失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to get execution outputs: {str(e)}")


@router.delete("/executions/{execution_id}")
async def delete_execution(execution_id: str) -> Dict[str, Any]:
    """
    删除执行记录及关联的输出文件（软删除）
    """
    try:
        from db import Execution, Output

        # 获取执行记录
        execution = await Execution.filter(
            user_id=USER_ID,
            execution_id=execution_id
        ).first()

        if not execution:
            raise HTTPException(404, f"Execution not found: {execution_id}")

        # 软删除关联的 Output 记录
        output_count = await Output.filter(
            execution_id=execution_id
        ).update(is_deleted=True, deleted_at=datetime.now())

        # 删除 Execution 记录
        await execution.delete()

        logger.info(f"已删除执行: {execution_id}（关联 {output_count} 个输出文件）")

        return {
            "execution_id": execution_id,
            "status": "deleted",
            "output_count": output_count,
            "message": "执行记录及关联输出文件已删除"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除执行失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to delete execution: {str(e)}")


@router.get("/executions/tags")
async def get_execution_tags() -> Dict[str, Any]:
    """
    获取用户的所有 tag 列表
    """
    try:
        from db import Execution

        # 获取所有不重复的 tag
        tags = await Execution.filter(
            user_id=USER_ID,
            tag__not_isnull=True
        ).distinct().values_list("tag", flat=True)

        # 为每个 tag 获取最新的执行记录
        tag_info = []
        for tag in tags:
            latest_exec = await Execution.filter(
                user_id=USER_ID,
                tag=tag
            ).order_by("-start_time").first()

            if latest_exec:
                tag_info.append({
                    "tag": tag,
                    "latest_execution_id": latest_exec.execution_id,
                    "status": latest_exec.status,
                    "start_time": latest_exec.start_time.isoformat(),
                })

        return {
            "tags": tag_info,
            "count": len(tag_info),
        }
    except Exception as e:
        logger.error(f"获取 tag 列表失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to get tags: {str(e)}")


@router.get("/executions/tags/{tag}")
async def get_tag_execution(tag: str) -> Dict[str, Any]:
    """
    获取指定 tag 的最新执行记录
    """
    try:
        from db import Execution

        execution = await Execution.filter(
            user_id=USER_ID,
            tag=tag
        ).order_by("-start_time").first()

        if not execution:
            raise HTTPException(404, f"Tag not found: {tag}")

        return {
            "execution_id": execution.execution_id,
            "user_id": execution.user_id,
            "source": execution.source,
            "flow_id": str(execution.flow_id) if execution.flow_id else None,
            "tag": execution.tag,
            "scripts_path": execution.scripts_path,
            "scripts_hash": execution.scripts_hash,
            "status": execution.status,
            "result": execution.result,
            "total_nodes": execution.total_nodes,
            "executed_nodes": execution.executed_nodes,
            "failed_nodes": execution.failed_nodes,
            "execution_time": execution.execution_time,
            "start_time": execution.start_time.isoformat(),
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "metadata": execution.metadata,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 tag 执行记录失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to get tag execution: {str(e)}")


@router.delete("/executions/tags/{tag}")
async def delete_tag_execution(tag: str) -> Dict[str, Any]:
    """
    删除指定 tag 的所有执行记录
    """
    try:
        from db import Execution, Output

        # 查找该 tag 的所有执行记录
        executions = await Execution.filter(
            user_id=USER_ID,
            tag=tag
        ).all()

        if not executions:
            raise HTTPException(404, f"Tag not found: {tag}")

        total_outputs = 0
        for execution in executions:
            # 软删除关联的 Output 记录
            output_count = await Output.filter(
                execution_id=execution.execution_id
            ).update(is_deleted=True, deleted_at=datetime.now())
            total_outputs += output_count

            # 删除 Execution 记录
            await execution.delete()

        logger.info(f"已删除 tag '{tag}' 的 {len(executions)} 个执行记录（共 {total_outputs} 个输出文件）")

        return {
            "tag": tag,
            "status": "deleted",
            "execution_count": len(executions),
            "output_count": total_outputs,
            "message": f"已删除 tag '{tag}' 的所有执行记录"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除 tag 执行记录失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to delete tag execution: {str(e)}")
