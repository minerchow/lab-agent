from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from models.role import Role, role_permission
from models.permission import Permission
from schemas.role import RoleCreate, RoleUpdate


async def get_role_by_id(db: AsyncSession, role_id: int) -> Role | None:
    query = select(Role).options(joinedload(Role.permissions)).where(
        Role.id == role_id, Role.is_deleted == False
    )
    result = await db.execute(query)
    return result.scalars().unique().one_or_none()


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    query = select(Role).options(joinedload(Role.permissions)).where(
        Role.name == name, Role.is_deleted == False
    )
    result = await db.execute(query)
    return result.scalars().unique().one_or_none()


async def get_roles(
    db: AsyncSession, page: int = 1, page_size: int = 10
) -> tuple[list[Role], int]:
    offset = (page - 1) * page_size
    count_query = select(func.count(Role.id)).where(Role.is_deleted == False)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = (
        select(Role)
        .options(joinedload(Role.permissions))
        .where(Role.is_deleted == False)
        .order_by(Role.created_at.desc())
        .offset(offset).limit(page_size)
    )
    result = await db.execute(query)
    roles = list(result.scalars().unique().all())
    return roles, total


async def get_all_roles(db: AsyncSession) -> list[Role]:
    query = select(Role).options(joinedload(Role.permissions)).where(
        Role.is_deleted == False
    ).order_by(Role.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().unique().all())


async def create_role(db: AsyncSession, role_data: RoleCreate) -> Role:
    role = Role(name=role_data.name, description=role_data.description)
    db.add(role)
    await db.flush()

    # 关联权限
    if role_data.permission_ids:
        permissions = await get_permissions_by_ids(db, role_data.permission_ids)
        if len(permissions) != len(role_data.permission_ids):
            found_ids = {p.id for p in permissions}
            missing = [pid for pid in role_data.permission_ids if pid not in found_ids]
            raise HTTPException(status_code=400, detail=f"以下权限不存在: {missing}")
        role.permissions = permissions
        await db.flush()

    await db.refresh(role)
    return role


async def update_role(db: AsyncSession, role: Role, role_data: RoleUpdate) -> Role:
    update_data = role_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field != "permission_ids":
            setattr(role, field, value)

    # 更新权限关联
    if role_data.permission_ids is not None:
        permissions = await get_permissions_by_ids(db, role_data.permission_ids)
        if len(permissions) != len(role_data.permission_ids):
            found_ids = {p.id for p in permissions}
            missing = [pid for pid in role_data.permission_ids if pid not in found_ids]
            raise HTTPException(status_code=400, detail=f"以下权限不存在: {missing}")
        role.permissions = permissions

    await db.flush()
    await db.refresh(role)
    return role


async def delete_role(db: AsyncSession, role: Role) -> Role:
    role.is_deleted = True
    await db.flush()
    await db.refresh(role)
    return role


# --- Permission CRUD ---

async def get_permission_by_id(db: AsyncSession, permission_id: int) -> Permission | None:
    query = select(Permission).where(
        Permission.id == permission_id, Permission.is_deleted == False
    )
    result = await db.execute(query)
    return result.scalars().one_or_none()


async def get_permission_by_code(db: AsyncSession, code: str) -> Permission | None:
    query = select(Permission).where(
        Permission.code == code, Permission.is_deleted == False
    )
    result = await db.execute(query)
    return result.scalars().one_or_none()


async def get_permissions_by_ids(db: AsyncSession, ids: list[int]) -> list[Permission]:
    query = select(Permission).where(
        Permission.id.in_(ids), Permission.is_deleted == False
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_permissions(
    db: AsyncSession, page: int = 1, page_size: int = 10
) -> tuple[list[Permission], int]:
    offset = (page - 1) * page_size
    count_query = select(func.count(Permission.id)).where(Permission.is_deleted == False)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = (
        select(Permission)
        .where(Permission.is_deleted == False)
        .order_by(Permission.created_at.desc())
        .offset(offset).limit(page_size)
    )
    result = await db.execute(query)
    permissions = list(result.scalars().all())
    return permissions, total


async def get_all_permissions(db: AsyncSession) -> list[Permission]:
    query = select(Permission).where(
        Permission.is_deleted == False
    ).order_by(Permission.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_permission(db: AsyncSession, permission_data: "PermissionCreate") -> Permission:
    permission = Permission(
        code=permission_data.code,
        name=permission_data.name,
        description=permission_data.description,
    )
    db.add(permission)
    await db.flush()
    await db.refresh(permission)
    return permission


async def update_permission(db: AsyncSession, permission: Permission, permission_data: "PermissionUpdate") -> Permission:
    update_data = permission_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(permission, field, value)
    await db.flush()
    await db.refresh(permission)
    return permission


async def delete_permission(db: AsyncSession, permission: Permission) -> Permission:
    permission.is_deleted = True
    await db.flush()
    await db.refresh(permission)
    return permission
