"""
Schemas 路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from schema_service import (
    get_schemas,
    get_schema,
    create_schema,
    update_schema,
    delete_schema,
    duplicate_schema,
)

USER_ID = "default"

router = APIRouter(prefix="/api/schemas", tags=["schemas"])


# Schema 数据模型
class SchemaItem(BaseModel):
    id: int
    name: str
    schema: Optional[dict] = None
    hasUnsavedChanges: bool = False


class CreateSchemaRequest(BaseModel):
    name: str
    schema: Optional[dict] = None


class UpdateSchemaRequest(BaseModel):
    name: Optional[str] = None
    schema: Optional[dict] = None


class DuplicateSchemaRequest(BaseModel):
    name: str


def to_schema_item(db_schema) -> SchemaItem:
    """将数据库模型转换为 SchemaItem"""
    return SchemaItem(
        id=db_schema.id,
        name=db_schema.name,
        schema=db_schema.schema_data,
        hasUnsavedChanges=False,
    )


@router.get("", response_model=List[SchemaItem])
async def list_schemas():
    """
    获取所有 schemas
    """
    try:
        schemas = await get_schemas(USER_ID)
        return [to_schema_item(s) for s in schemas]
    except Exception as e:
        raise HTTPException(500, f"Failed to list schemas: {str(e)}")


@router.post("", response_model=SchemaItem)
async def create_new_schema(request: CreateSchemaRequest):
    """
    创建新 schema
    """
    try:
        schema = await create_schema(USER_ID, request.name, request.schema)
        return to_schema_item(schema)
    except Exception as e:
        raise HTTPException(500, f"Failed to create schema: {str(e)}")


@router.get("/{schema_id}", response_model=SchemaItem)
async def get_schema_by_id(schema_id: int):
    """
    获取单个 schema
    """
    try:
        schema = await get_schema(USER_ID, schema_id)
        if not schema:
            raise HTTPException(404, "Schema not found")
        return to_schema_item(schema)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to get schema: {str(e)}")


@router.put("/{schema_id}", response_model=SchemaItem)
async def update_schema_by_id(schema_id: int, request: UpdateSchemaRequest):
    """
    更新 schema
    """
    try:
        success = await update_schema(USER_ID, schema_id, request.name, request.schema)
        if not success:
            raise HTTPException(404, "Schema not found")
        schema = await get_schema(USER_ID, schema_id)
        return to_schema_item(schema)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to update schema: {str(e)}")


@router.delete("/{schema_id}")
async def delete_schema_by_id(schema_id: int):
    """
    删除 schema
    """
    try:
        success = await delete_schema(USER_ID, schema_id)
        if not success:
            raise HTTPException(404, "Schema not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to delete schema: {str(e)}")


@router.post("/{schema_id}/duplicate", response_model=SchemaItem)
async def duplicate_schema_by_id(schema_id: int, request: DuplicateSchemaRequest):
    """
    复制 schema
    """
    try:
        schema = await duplicate_schema(USER_ID, schema_id, request.name)
        if not schema:
            raise HTTPException(404, "Schema not found")
        return to_schema_item(schema)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to duplicate schema: {str(e)}")