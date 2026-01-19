"""
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-19 20:25:18
LastEditors: zhai
LastEditTime: 2026-01-19 20:25:35
"""

from routes.flow.service import (
    create_flow,
    delete_flow,
    duplicate_flow,
    get_flow,
    get_flows,
    update_flow,
)
from db import Flow
from routes.flow.schema import (
    CreateFlowRequest,
    DuplicateFlowRequest,
    FlowItem,
    UpdateFlowRequest,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


USER_ID = "default"

router = APIRouter(prefix="/api/flows", tags=["flows"])


def to_flow_item(db_flow: Flow) -> FlowItem:
    """将数据库模型转换为 FlowItem"""
    return FlowItem(
        id=str(db_flow.id),
        name=db_flow.name,
        flow=db_flow.flow,
        hasUnsavedChanges=False,
    )


@router.get("", response_model=List[FlowItem])
async def list_flows():
    """
    获取所有 flows
    """
    try:
        flows = await get_flows(USER_ID)
        return [to_flow_item(f) for f in flows]
    except Exception as e:
        raise HTTPException(500, f"Failed to list flows: {str(e)}")


@router.post("", response_model=FlowItem)
async def create_new_flow(request: CreateFlowRequest):
    """
    创建新 flow
    """
    try:
        flow = await create_flow(USER_ID, request.name, request.flow)
        return to_flow_item(flow)
    except Exception as e:
        raise HTTPException(500, f"Failed to create flow: {str(e)}")


@router.get("/{flow_id}", response_model=FlowItem)
async def get_flow_by_id(flow_id: UUID):
    """
    获取单个 flow
    """
    try:
        flow = await get_flow(USER_ID, flow_id)
        if not flow:
            raise HTTPException(404, "Flow not found")
        return to_flow_item(flow)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get flow: {str(e)}")


@router.put("/{flow_id}", response_model=FlowItem)
async def update_flow_by_id(flow_id: UUID, request: UpdateFlowRequest):
    """
    更新 flow
    """
    try:
        success = await update_flow(USER_ID, flow_id, request.name, request.flow)
        if not success:
            raise HTTPException(404, "Flow not found")
        flow = await get_flow(USER_ID, flow_id)
        return to_flow_item(flow)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update flow: {str(e)}")


@router.delete("/{flow_id}")
async def delete_flow_by_id(flow_id: UUID):
    """
    删除 flow
    """
    try:
        success = await delete_flow(USER_ID, flow_id)
        if not success:
            raise HTTPException(404, "Flow not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to delete flow: {str(e)}")


@router.post("/{flow_id}/duplicate", response_model=FlowItem)
async def duplicate_flow_by_id(flow_id: UUID, request: DuplicateFlowRequest):
    """
    复制 flow
    """
    try:
        flow = await duplicate_flow(USER_ID, flow_id, request.name)
        if not flow:
            raise HTTPException(404, "Flow not found")
        return to_flow_item(flow)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to duplicate flow: {str(e)}")
