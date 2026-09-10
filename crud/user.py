from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload
from fastapi import HTTPException
from models.article import Article
from models.user import User
from models.role import Role
from schemas.user import UserCreate
from utils.security import get_hash_password


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    query = select(User).options(joinedload(User.roles)).where(
        User.username == username, User.is_deleted == False
    )
    result = await db.execute(query)
    return result.scalars().unique().one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    query = select(User).options(joinedload(User.roles)).where(
        User.id == user_id, User.is_deleted == False
    )
    result = await db.execute(query)
    return result.scalars().unique().one_or_none()


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    hashed_password = get_hash_password(user_data.password)
    user = User(username=user_data.username, password=hashed_password)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_user_roles(db: AsyncSession, user: User, role_ids: list[int]) -> User:
    """更新用户的角色关联"""
    roles = []
    if role_ids:
        query = select(Role).where(Role.id.in_(role_ids), Role.is_deleted == False)
        result = await db.execute(query)
        roles = list(result.scalars().all())
        if len(roles) != len(role_ids):
            found_ids = {r.id for r in roles}
            missing = [rid for rid in role_ids if rid not in found_ids]
            raise HTTPException(
                status_code=400,
                detail=f"以下角色不存在: {missing}"
            )
    user.roles = roles
    await db.flush()
    await db.refresh(user)
    return user


async def soft_delete_user(db: AsyncSession, user: User) -> User:
    user.is_deleted = True
    await db.execute(
        update(Article)
        .where(Article.user_id == user.id, Article.is_deleted == False)
        .values(is_deleted=True)
    )
    await db.flush()
    await db.refresh(user)
    return user
