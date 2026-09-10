import os
from datetime import timedelta
from dotenv import load_dotenv

# 根据 APP_ENV 加载对应的 .env 文件
app_env = os.getenv("APP_ENV", "development")
env_file = f".env.{app_env}" if app_env != "development" else ".env"
load_dotenv(env_file)

ENV = os.getenv("ENV", app_env)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-secret-key-please-change")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

ACCESS_TOKEN_EXPIRE = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
REFRESH_TOKEN_EXPIRE = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
