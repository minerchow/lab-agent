from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from schemas.permission import PermissionResponse


class RoleBase(BaseModel):
    name: str = Field(..., max_length=50, description="角色名称")
    description: Optional[str] = Field(None, max_length=200, description="角色描述")


class RoleCreate(RoleBase):
    permission_ids: List[int] = Field(default=[], description="权限ID列表")


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, max_length=200, description="角色描述")
    permission_ids: Optional[List[int]] = Field(None, description="权限ID列表")


class RoleResponse(RoleBase):
    id: int
    permissions: List[PermissionResponse] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RoleListResponse(BaseModel):
    items: List[RoleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
