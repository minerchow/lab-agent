from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


class PermissionBase(BaseModel):
    code: str = Field(..., max_length=100, description="权限编码")
    name: str = Field(..., max_length=100, description="权限名称")
    description: Optional[str] = Field(None, max_length=200, description="权限描述")


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=100, description="权限编码")
    name: Optional[str] = Field(None, max_length=100, description="权限名称")
    description: Optional[str] = Field(None, max_length=200, description="权限描述")


class PermissionResponse(PermissionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PermissionListResponse(BaseModel):
    items: List[PermissionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
