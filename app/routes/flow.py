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
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from node.run import make_dynamic_engine, get_json_blocks, run_schema
from services import list_dir, read_file, normalize_path


USER_ID = "default"

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
                            print(f"Loaded block script: {full_path}")
                elif file_type == 2:  # 目录
                    # 递归处理子目录
                    await _load_recursive(full_path)
        except Exception as e:
            print(f"Error loading blocks from {path}: {str(e)}")
    
    await _load_recursive(directory)
    return scripts




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

        result = await run_schema(scripts, request.data["graph"] or {})

        return {"ok": True, "result": result}
    except Exception as e:
        raise HTTPException(500, f"Execution failed: {str(e)}")
