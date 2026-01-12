"""
Schema 业务逻辑
"""
import time
import uuid
from typing import List, Optional
from db import Schema


async def get_schemas(user_id: str) -> List[Schema]:
    """获取用户的所有 schemas"""
    return await Schema.filter(user_id=user_id).all()


async def get_schema(user_id: str, schema_id: uuid.UUID) -> Optional[Schema]:
    """获取单个 schema"""
    return await Schema.filter(id=schema_id, user_id=user_id).first()


async def create_schema(user_id: str, name: str, schema_data: dict = None) -> Schema:
    """创建新 schema"""
    now = int(time.time() * 1000)
    return await Schema.create(
        user_id=user_id,
        name=name,
        schema_data=schema_data,
        mtime=now,
    )


async def update_schema(user_id: str, schema_id: uuid.UUID, name: str = None, schema_data: dict = None) -> bool:
    """更新 schema"""
    now = int(time.time() * 1000)
    update_data = {"mtime": now}
    if name is not None:
        update_data["name"] = name
    if schema_data is not None:
        update_data["schema_data"] = schema_data

    updated = await Schema.filter(id=schema_id, user_id=user_id).update(**update_data)
    return updated > 0


async def delete_schema(user_id: str, schema_id: uuid.UUID) -> bool:
    """删除 schema"""
    deleted = await Schema.filter(id=schema_id, user_id=user_id).delete()
    return deleted > 0


async def duplicate_schema(user_id: str, schema_id: uuid.UUID, new_name: str) -> Optional[Schema]:
    """复制 schema"""
    original = await get_schema(user_id, schema_id)
    if not original:
        return None
    return await create_schema(user_id, new_name, original.schema_data)