import math
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from models.user import User
from schemas.role import RoleCreate, RoleUpdate, RoleResponse, RoleListResponse
from schemas.permission import PermissionCreate, PermissionUpdate, PermissionResponse, PermissionListResponse
from crud.role import (
    get_role_by_id, get_role_by_name, get_roles, get_all_roles,
    create_role, update_role, delete_role,
    get_permission_by_id, get_permission_by_code, get_permissions, get_all_permissions,
    create_permission, update_permission, delete_permission,
)
from utils.response import success_response
from utils.permissions import require_role

router = APIRouter(prefix="/api", tags=["rbac"])


# ==================== 角色管理 ====================

@router.get("/roles")
async def list_roles(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    roles, total = await get_roles(db, page, page_size)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return success_response(
        message="获取角色列表成功",
        data=RoleListResponse(
            items=[RoleResponse.model_validate(r) for r in roles],
            total=total, page=page, page_size=page_size, total_pages=total_pages,
        ).model_dump(),
    )


@router.get("/roles/all")
async def list_all_roles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    roles = await get_all_roles(db)
    return success_response(
        message="获取所有角色成功",
        data=[RoleResponse.model_validate(r).model_dump() for r in roles],
    )


@router.get("/roles/{role_id}")
async def get_role_detail(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    role = await get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    return success_response(
        message="获取角色详情成功",
        data=RoleResponse.model_validate(role).model_dump(),
    )


@router.post("/roles")
async def create_new_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    existing = await get_role_by_name(db, role_data.name)
    if existing:
        raise HTTPException(status_code=400, detail="角色名已存在")
    role = await create_role(db, role_data)
    return success_response(
        message="创建角色成功",
        data=RoleResponse.model_validate(role).model_dump(),
    )


@router.put("/roles/{role_id}")
async def update_existing_role(
    role_id: int,
    role_data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    role = await get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role_data.name and role_data.name != role.name:
        existing = await get_role_by_name(db, role_data.name)
        if existing:
            raise HTTPException(status_code=400, detail="角色名已存在")
    updated_role = await update_role(db, role, role_data)
    return success_response(
        message="更新角色成功",
        data=RoleResponse.model_validate(updated_role).model_dump(),
    )


@router.delete("/roles/{role_id}")
async def delete_existing_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    role = await get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    deleted_role = await delete_role(db, role)
    return success_response(
        message="删除角色成功",
        data=RoleResponse.model_validate(deleted_role).model_dump(),
    )


# ==================== 权限管理 ====================

@router.get("/permissions")
async def list_permissions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    permissions, total = await get_permissions(db, page, page_size)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return success_response(
        message="获取权限列表成功",
        data=PermissionListResponse(
            items=[PermissionResponse.model_validate(p) for p in permissions],
            total=total, page=page, page_size=page_size, total_pages=total_pages,
        ).model_dump(),
    )


@router.get("/permissions/all")
async def list_all_permissions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    permissions = await get_all_permissions(db)
    return success_response(
        message="获取所有权限成功",
        data=[PermissionResponse.model_validate(p).model_dump() for p in permissions],
    )


@router.get("/permissions/{permission_id}")
async def get_permission_detail(
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    permission = await get_permission_by_id(db, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="权限不存在")
    return success_response(
        message="获取权限详情成功",
        data=PermissionResponse.model_validate(permission).model_dump(),
    )


@router.post("/permissions")
async def create_new_permission(
    permission_data: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    existing = await get_permission_by_code(db, permission_data.code)
    if existing:
        raise HTTPException(status_code=400, detail="权限编码已存在")
    permission = await create_permission(db, permission_data)
    return success_response(
        message="创建权限成功",
        data=PermissionResponse.model_validate(permission).model_dump(),
    )


@router.put("/permissions/{permission_id}")
async def update_existing_permission(
    permission_id: int,
    permission_data: PermissionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    permission = await get_permission_by_id(db, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="权限不存在")
    if permission_data.code and permission_data.code != permission.code:
        existing = await get_permission_by_code(db, permission_data.code)
        if existing:
            raise HTTPException(status_code=400, detail="权限编码已存在")
    updated_permission = await update_permission(db, permission, permission_data)
    return success_response(
        message="更新权限成功",
        data=PermissionResponse.model_validate(updated_permission).model_dump(),
    )


@router.delete("/permissions/{permission_id}")
async def delete_existing_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    permission = await get_permission_by_id(db, permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="权限不存在")
    deleted_permission = await delete_permission(db, permission)
    return success_response(
        message="删除权限成功",
        data=PermissionResponse.model_validate(deleted_permission).model_dump(),
    )
