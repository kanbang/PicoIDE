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


USER_ID = "default"

router = APIRouter(prefix="/api/flow", tags=["blocks"])


class ExecuteRequest(BaseModel):
    scripts: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None


@router.get("/blocks")
async def get_blocks():
    """
    获取所有可用的 blocks 定义
    """
    try:
        # 从文件系统读取所有 .py 脚本文件
        blocks = get_json_blocks([])
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

        result = await run_schema(scripts, request.data["graph"] or {})
        # BlockEngine.make_engine(scripts)
        # BlockEngine.init_schemas(request.data["graph"] or {})

        # # 执行计算
        # result = BlockEngine.execute()

        return {"ok": True, "result": result}
    except Exception as e:
        raise HTTPException(500, f"Execution failed: {str(e)}")
