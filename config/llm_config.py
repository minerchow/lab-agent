import os
from dotenv import load_dotenv

# 根据 APP_ENV 加载对应的 .env 文件
app_env = os.getenv("APP_ENV", "development")
env_file = f".env.{app_env}" if app_env != "development" else ".env"
load_dotenv(env_file)

ENV = os.getenv("ENV", app_env)

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.7))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 4096))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", 60))
