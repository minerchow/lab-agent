import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
from fastapi import Header, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from config.jwt_config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE,
    REFRESH_TOKEN_EXPIRE
)

logger = logging.getLogger(__name__)


# ── Token 生成（每个 token 带唯一 jti） ──────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    to_encode["type"] = "access"
    to_encode["jti"] = str(uuid.uuid4())
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE
    to_encode["exp"] = int(expire.timestamp())
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    to_encode["type"] = "refresh"
    to_encode["jti"] = str(uuid.uuid4())
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + REFRESH_TOKEN_EXPIRE
    to_encode["exp"] = int(expire.timestamp())
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_tokens(user_id: int) -> Dict[str, Any]:
    token_data = {"sub": str(user_id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(ACCESS_TOKEN_EXPIRE.total_seconds())
    }


# ── Redis 黑名单 / 会话管理 ──────────────────────────────────────────
#
# Key 设计（统一用字符串类型，避免 SET/STRING 混用导致 WRONGTYPE）：
#   token:blacklist:{user_id}            -> 已撤销的 jti 列表（逗号分隔字符串）
#   token:active_access:{user_id}        -> 当前有效 access jti（单个字符串）
#   token:active_refresh:{user_id}       -> 当前有效 refresh jti（单个字符串）
#
# 刷新时：旧 refresh jti + 旧 access jti 全部写入 blacklist，再写入新的 active 值。

TOKEN_BLACKLIST_PREFIX = "token:blacklist"
TOKEN_ACTIVE_ACCESS_PREFIX = "token:active_access"
TOKEN_ACTIVE_REFRESH_PREFIX = "token:active_refresh"


async def _add_to_blacklist(user_id: int, *jti_list: Optional[str]) -> None:
    """把若干 jti 追加到黑名单（逗号分隔字符串）"""
    from config.cache_config import redis_client
    jti_list = [j for j in jti_list if j]
    if not jti_list:
        return
    key = f"{TOKEN_BLACKLIST_PREFIX}:{user_id}"
    try:
        existing = await redis_client.get(key)
        parts = ([existing] if existing else []) + jti_list
        await redis_client.setex(key, int(REFRESH_TOKEN_EXPIRE.total_seconds()), ",".join(parts))
    except Exception:
        logger.exception("黑名单写入失败 user_id=%s", user_id)


async def _in_blacklist(user_id: int, jti: Optional[str]) -> bool:
    if not jti:
        return False
    from config.cache_config import redis_client
    key = f"{TOKEN_BLACKLIST_PREFIX}:{user_id}"
    try:
        val = await redis_client.get(key)
        if not val:
            return False
        return jti in val.split(",")
    except Exception:
        logger.exception("黑名单查询失败 user_id=%s", user_id)
        return False


async def _set_active(user_id: int, token_type: str, jti: str) -> None:
    from config.cache_config import redis_client
    key = f"{TOKEN_ACTIVE_ACCESS_PREFIX if token_type == 'access' else TOKEN_ACTIVE_REFRESH_PREFIX}:{user_id}"
    try:
        await redis_client.setex(key, int(REFRESH_TOKEN_EXPIRE.total_seconds()), jti)
    except Exception:
        logger.exception("active token 写入失败 user_id=%s type=%s", user_id, token_type)


async def _get_active(user_id: int, token_type: str) -> Optional[str]:
    from config.cache_config import redis_client
    key = f"{TOKEN_ACTIVE_ACCESS_PREFIX if token_type == 'access' else TOKEN_ACTIVE_REFRESH_PREFIX}:{user_id}"
    try:
        return await redis_client.get(key)
    except Exception:
        logger.exception("active token 读取失败 user_id=%s type=%s", user_id, token_type)
        return None


# ── 登录 / 刷新 ──────────────────────────────────────────────────────

async def create_login_tokens(user_id: int) -> Dict[str, Any]:
    """登录：生成新 token 并登记 active jti（覆盖旧会话）"""
    tokens = create_tokens(user_id)
    access_jti = jwt.decode(tokens["access_token"], JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])["jti"]
    refresh_jti = jwt.decode(tokens["refresh_token"], JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])["jti"]
    await _set_active(user_id, "access", access_jti)
    await _set_active(user_id, "refresh", refresh_jti)
    return tokens


async def rotate_tokens(user_id: int, old_refresh_token: str) -> Dict[str, Any]:
    """刷新：作废旧 access + 旧 refresh，签发新的一对（单会话策略）"""
    old_payload = jwt.decode(old_refresh_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    old_refresh_jti = old_payload.get("jti")

    old_access_jti = await _get_active(user_id, "access")

    # 作废旧的一对
    await _add_to_blacklist(user_id, old_access_jti, old_refresh_jti)

    # 签发新的一对并登记
    tokens = create_tokens(user_id)
    access_jti = jwt.decode(tokens["access_token"], JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])["jti"]
    refresh_jti = jwt.decode(tokens["refresh_token"], JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])["jti"]
    await _set_active(user_id, "access", access_jti)
    await _set_active(user_id, "refresh", refresh_jti)
    return tokens


# ── 撤销（改密码 / 删除用户） ────────────────────────────────────────

async def revoke_user_tokens(user_id: int) -> None:
    """撤销该用户当前所有 access + refresh token"""
    from config.cache_config import redis_client
    old_access_jti = await _get_active(user_id, "access")
    old_refresh_jti = await _get_active(user_id, "refresh")
    await _add_to_blacklist(user_id, old_access_jti, old_refresh_jti)
    try:
        await redis_client.delete(
            f"{TOKEN_ACTIVE_ACCESS_PREFIX}:{user_id}",
            f"{TOKEN_ACTIVE_REFRESH_PREFIX}:{user_id}",
        )
    except Exception:
        logger.exception("删除 active token 键失败 user_id=%s", user_id)


# ── 校验 ──────────────────────────────────────────────────────────────

def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _resolve_user_id(payload: Dict[str, Any]) -> int:
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        return int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token")


async def check_token_valid(user_id: int, payload: dict) -> None:
    """
    校验规则：
    1. jti 在黑名单中 -> 已撤销
    2. 该类型的 active jti 与 payload.jti 不一致 -> 已被轮换顶替
    两条命中任意一条即 401。
    """
    jti = payload.get("jti")
    token_type = payload.get("type")

    if await _in_blacklist(user_id, jti):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    active_jti = await _get_active(user_id, token_type)
    if active_jti is not None and jti != active_jti:
        raise HTTPException(status_code=401, detail="Token has been replaced by a new token")


async def get_current_user(
    authorization: str = Header(default=None),
    db: AsyncSession = Depends(get_db)
):
    from crud.user import get_user_by_id

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split(" ")
    token = parts[1] if len(parts) > 1 else parts[0]

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type, please use access token")

    user_id = _resolve_user_id(payload)
    await check_token_valid(user_id, payload)

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def verify_refresh_token(token: str, db: AsyncSession) -> Any:
    from crud.user import get_user_by_id

    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type, please use refresh token")

    user_id = _resolve_user_id(payload)
    await check_token_valid(user_id, payload)

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user
