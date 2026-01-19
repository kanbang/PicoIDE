'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-12 20:03:57
LastEditors: zhai
LastEditTime: 2026-01-19 19:11:28
'''
"""
Flow 业务逻辑
"""
import time
import uuid
from typing import List, Optional
from db import Flow


async def get_flows(user_id: str) -> List[Flow]:
    """获取用户的所有 flows"""
    return await Flow.filter(user_id=user_id).all()


async def get_flow(user_id: str, flow_id: uuid.UUID) -> Optional[Flow]:
    """获取单个 flow"""
    return await Flow.filter(id=flow_id, user_id=user_id).first()


async def create_flow(user_id: str, name: str, flow: dict = None) -> Flow:
    """创建新 flow"""
    now = int(time.time() * 1000)
    return await Flow.create(
        user_id=user_id,
        name=name,
        flow=flow,
        mtime=now,
    )


async def update_flow(user_id: str, flow_id: uuid.UUID, name: str = None, flow: dict = None) -> bool:
    """更新 flow"""
    now = int(time.time() * 1000)
    update_data = {"mtime": now}
    if name is not None:
        update_data["name"] = name
    if flow is not None:
        update_data["flow"] = flow

    updated = await Flow.filter(id=flow_id, user_id=user_id).update(**update_data)
    return updated > 0


async def delete_flow(user_id: str, flow_id: uuid.UUID) -> bool:
    """删除 flow"""
    deleted = await Flow.filter(id=flow_id, user_id=user_id).delete()
    return deleted > 0


async def duplicate_flow(user_id: str, flow_id: uuid.UUID, new_name: str) -> Optional[Flow]:
    """复制 flow"""
    original = await get_flow(user_id, flow_id)
    if not original:
        return None
    return await create_flow(user_id, new_name, original.flow)