from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from fastapi import Depends, HTTPException, status

from utils.auth import get_current_user

if TYPE_CHECKING:
    from models.user import User


# ==================== 基于角色的检查 ====================

def require_role(role_name: str):
    """
    基于角色的依赖注入（RBAC 新方案）

    使用方式:
        @router.get("/items")
        async def get_items(user = Depends(require_role("admin"))):
            ...
    """
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.has_role(role_name):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"需要 {role_name} 角色"
        )
    return role_checker


def require_permission(permission_code: str):
    """
    基于权限的依赖注入（RBAC 新方案）

    使用方式:
        @router.post("/articles")
        async def create_article(user = Depends(require_permission("article:create"))):
            ...
    """
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        if user.has_permission(permission_code):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"需要 {permission_code} 权限"
        )
    return permission_checker


def require_any_role(*role_names: str):
    """
    需要拥有任意一个指定角色

    使用方式:
        @router.delete("/items/{id}")
        async def delete_item(user = Depends(require_any_role("admin", "editor"))):
            ...
    """
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if any(user.has_role(name) for name in role_names):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"需要以下角色之一: {', '.join(role_names)}"
        )
    return role_checker


def require_any_permission(*permission_codes: str):
    """
    需要拥有任意一个指定权限

    使用方式:
        @router.delete("/items/{id}")
        async def delete_item(user = Depends(require_any_permission("article:delete", "admin:all"))):
            ...
    """
    def permission_checker(user: User = Depends(get_current_user)) -> User:
        if any(user.has_permission(code) for code in permission_codes):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"需要以下权限之一: {', '.join(permission_codes)}"
        )
    return permission_checker


# ==================== 可选认证 ====================

async def get_current_user_optional(
    user: Optional[User] = Depends(get_current_user)
) -> Optional[User]:
    return user
