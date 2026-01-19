"""
Schemas 路由
"""
from pydantic import BaseModel
from typing import List, Optional


# Flow 数据模型
class FlowItem(BaseModel):
    id: str
    name: str
    flow: Optional[dict] = None
    hasUnsavedChanges: bool = False


class CreateFlowRequest(BaseModel):
    name: str
    flow: Optional[dict] = None


class UpdateFlowRequest(BaseModel):
    name: Optional[str] = None
    flow: Optional[dict] = None


class DuplicateFlowRequest(BaseModel):
    name: str
