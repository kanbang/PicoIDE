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
from pydantic import BaseModel
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

# 输出目录配置
OUTPUT_DIR = Path("./output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 文件类型映射
FILE_TYPE_MAP = {
    ".html": "html",
    ".csv": "csv",
    ".json": "json",
    ".txt": "text",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".pdf": "pdf",
    ".xlsx": "excel",
    ".xls": "excel",
}

# 浏览器可打开的文件类型
BROWSER_OPENABLE = {"html", "json", "txt"}

router = APIRouter(prefix="/api/flow", tags=["blocks"])


class ExecuteRequest(BaseModel):
    scripts: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None


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
                    if name.endswith('.py'):
                        # 读取 .py 文件内容
                        content = await read_file(USER_ID, full_path)
                        if content:
                            scripts.append(content.decode('utf-8'))
                            logger.info(f"Loaded block script: {full_path}")
                elif file_type == 2:  # 目录
                    # 递归处理子目录
                    await _load_recursive(full_path)
        except Exception as e:
            logger.error(f"Error loading blocks from {path}: {str(e)}")
    
    await _load_recursive(directory)
    return scripts


def collect_output_files(start_time: float) -> List[Dict[str, Any]]:
    """
    收集执行期间创建的输出文件
    
    Args:
        start_time: 执行开始时间戳
        
    Returns:
        输出文件列表
    """
    files = []
    
    if not OUTPUT_DIR.exists():
        return files
    
    for file_path in OUTPUT_DIR.iterdir():
        if file_path.is_file():
            # 检查文件是否在执行期间创建
            file_mtime = file_path.stat().st_mtime
            
            if file_mtime >= start_time:
                suffix = file_path.suffix.lower()
                file_type = FILE_TYPE_MAP.get(suffix, "unknown")
                
                # 跳过未知类型
                if file_type == "unknown":
                    continue
                
                files.append({
                    "file_id": f"file_{file_path.name}",
                    "filename": file_path.name,
                    "file_path": str(file_path),
                    "file_type": file_type,
                    "file_size": file_path.stat().st_size,
                    "created_at": datetime.fromtimestamp(file_mtime).isoformat(),
                    "can_open": file_type in BROWSER_OPENABLE,
                    "can_download": True,
                })
    
    return files




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


@router.post("/execute")
async def execute(request: ExecuteRequest):
    """
    执行 block 计算
    """
    try:
        scripts = request.scripts or []

        # 从数据库加载自定义 blocks
        scripts_db = await load_scripts_from_db("/")
        scripts.extend(scripts_db)

        # 记录执行开始时间
        start_time = time.time()
        
        # 执行 schema
        result = await run_schema(scripts, request.data["graph"] or {})
        
        # 收集输出文件
        output_files = collect_output_files(start_time)
        
        # 构建响应
        response = {
            "ok": True,
            "result": result,
            "output_files": output_files,
            "execution_time": time.time() - start_time,
            "timestamp": datetime.now().isoformat()
        }

        logger.info(f"执行完成，耗时: {response['execution_time']:.3f}s，输出文件: {len(output_files)}")
        
        return response
    except Exception as e:
        logger.error(f"执行失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Execution failed: {str(e)}")


@router.get("/output-files")
async def get_output_files() -> List[Dict[str, Any]]:
    """
    获取所有输出文件列表
    """
    try:
        files = []
        
        if OUTPUT_DIR.exists():
            for file_path in OUTPUT_DIR.iterdir():
                if file_path.is_file():
                    suffix = file_path.suffix.lower()
                    file_type = FILE_TYPE_MAP.get(suffix, "unknown")
                    
                    files.append({
                        "file_id": f"file_{file_path.name}",
                        "filename": file_path.name,
                        "file_type": file_type,
                        "file_size": file_path.stat().st_size,
                        "created_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "can_open": file_type in BROWSER_OPENABLE,
                        "can_download": True,
                    })
        
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
        # 从 file_id 提取文件名
        filename = file_id.replace("file_", "")
        file_path = OUTPUT_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(404, f"文件不存在: {filename}")
        
        return FileResponse(
            file_path,
            filename=filename,
            media_type="application/octet-stream"
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
        # 从 file_id 提取文件名
        filename = file_id.replace("file_", "")
        file_path = OUTPUT_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(404, f"文件不存在: {filename}")
        
        file_path.unlink()
        
        logger.info(f"已删除文件: {filename}")
        
        return {
            "file_id": file_id,
            "status": "deleted",
            "message": "文件已删除"
        }
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
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        if OUTPUT_DIR.exists():
            for file_path in OUTPUT_DIR.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    
                    if file_age > max_age_seconds:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                            logger.info(f"已清理旧文件: {file_path.name}")
                        except Exception as e:
                            logger.error(f"清理文件失败: {file_path.name}, {e}")
        
        return {
            "status": "success",
            "message": f"已清理 {deleted_count} 个超过 {max_age_hours} 小时的旧文件"
        }
    except Exception as e:
        logger.error(f"清理文件失败: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to cleanup files: {str(e)}")
