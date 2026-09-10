import os
import json
from typing import Any
from dotenv import load_dotenv

# 根据 APP_ENV 加载对应的 .env 文件
app_env = os.getenv("APP_ENV", "development")
env_file = f".env.{app_env}" if app_env != "development" else ".env"
load_dotenv(env_file)

ENV = os.getenv("ENV", app_env)

REDIS_CONFIG = {
    "development": {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", 6379)),
        "db": int(os.getenv("REDIS_DB", 0)),
        "password": os.getenv("REDIS_PASSWORD", ""),
    },
    "test": {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", 6379)),
        "db": int(os.getenv("REDIS_DB", 1)),
        "password": os.getenv("REDIS_PASSWORD", ""),
    },
    "production": {
        "host": os.getenv("REDIS_HOST", ""),
        "port": int(os.getenv("REDIS_PORT", 6379)),
        "db": int(os.getenv("REDIS_DB", 0)),
        "password": os.getenv("REDIS_PASSWORD", ""),
    },
}

redis_config = REDIS_CONFIG.get(ENV, REDIS_CONFIG["development"])

import redis.asyncio as redis

redis_client = redis.Redis(
    host=redis_config["host"],
    port=redis_config["port"],
    db=redis_config["db"],
    password=redis_config["password"] if redis_config["password"] else None,
    decode_responses=True,
)


async def get_cache(key: str):
    try:
        return await redis_client.get(key)
    except Exception as e:
        print(f"获取缓存失败：{e}")
        return None


async def get_json_cache(key: str):
    try:
        data = await redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"获取 JSON 缓存失败：{e}")
        return None


async def set_cache(key: str, value: Any, expire: int = 3600):
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        await redis_client.setex(key, expire, value)
        return True
    except Exception as e:
        print(f"设置缓存失败：{e}")
        return False


async def delete_cache(key: str):
    try:
        await redis_client.delete(key)
        return True
    except Exception as e:
        print(f"删除缓存失败：{e}")
        return False
