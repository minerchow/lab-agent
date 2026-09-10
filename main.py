from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import user_router, health_router, article_router, role_router
from utils.exception_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from config.db_conf import async_engine
    from config.cache_config import redis_client
    await async_engine.dispose()
    await redis_client.aclose()


app = FastAPI(
    title="FastAPI Scaffold",
    description="A FastAPI scaffold project with SQLAlchemy, Redis, and more",
    version="0.1.0",
    lifespan=lifespan
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(user_router)
app.include_router(article_router)
app.include_router(role_router)


@app.get("/")
async def root():
    return {"msg": "Hello FastAPI Scaffold"}
