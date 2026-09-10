from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from models.user import User
from schemas.user import UserCreate, UserResponse, UserLogin, LoginResponse, TokenData, RefreshTokenRequest, UserRoleUpdate
from crud.user import get_user_by_username, create_user, get_user_by_id, update_user_roles, soft_delete_user
from utils.response import success_response
from utils.auth import get_current_user, create_tokens, verify_refresh_token
from utils.security import verify_password
from utils.permissions import require_role

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register")
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="两次密码输入不一致"
        )

    existing_user = await get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    new_user = await create_user(db, user_data)
    return success_response(
        message="注册成功",
        data=UserResponse.model_validate(new_user)
    )


@router.post("/login")
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(db, login_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    if not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    tokens = create_tokens(user.id)

    return success_response(
        message="登录成功",
        data=LoginResponse(
            user=UserResponse.model_validate(user),
            token=TokenData(**tokens)
        )
    )


@router.post("/refresh")
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    user = await verify_refresh_token(request.refresh_token, db)
    tokens = create_tokens(user.id)

    return success_response(
        message="Token刷新成功",
        data=TokenData(**tokens)
    )


@router.get("/info")
async def get_user_info(user: User = Depends(get_current_user)):
    return success_response(
        message="获取用户信息成功",
        data=UserResponse.model_validate(user)
    )


@router.get("/{user_id}")
async def get_user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin"))
):
    target_user = await get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return success_response(
        message="获取用户信息成功",
        data=UserResponse.model_validate(target_user)
    )


@router.put("/{user_id}/roles")
async def change_user_roles(
    user_id: int,
    role_data: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin"))
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    updated_user = await update_user_roles(db, user, role_data.role_ids)
    return success_response(
        message="修改用户角色成功",
        data=UserResponse.model_validate(updated_user)
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin"))
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    await soft_delete_user(db, user)
    return success_response(message="删除用户成功")
