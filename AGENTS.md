# fastapi-init — Project Architecture & Module Development Guide

> This document is for AI agents. When asked to create a new module (e.g. `tag`, `category`, `comment`), **always reference the `articles` module as the canonical example** and follow its patterns exactly.

---

## 1. Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (async, MySQL via aiomysql) |
| DB Migration | Alembic |
| Auth | JWT (access + refresh token) |
| Password | bcrypt via passlib |
| Cache | Redis (async, optional per module) |
| Env Config | python-dotenv (`.env`, `.env.test`, `.env.production`) |
| Package Manager | uv |

---

## 2. Project Directory Structure

```
fastapi-init/
├── main.py                  # App entry: create FastAPI with lifespan, register middleware & routers
├── pyproject.toml           # Dependencies & project metadata
├── alembic/                 # DB migrations (Alembic)
│   └── versions/
├── config/                  # Configuration layer
│   ├── db_conf.py           #   DB engine & AsyncSession factory
│   ├── jwt_config.py        #   JWT secret / algorithm / expiry
│   └── cache_config.py      #   Redis client & helpers
├── models/                  # SQLAlchemy ORM models (layer 1)
│   ├── __init__.py          #   Re-exports all models + Base
│   ├── base.py              #   Base (DeclarativeBase, UTC timestamps via _utcnow())
│   ├── user.py              #   User model
│   └── article.py           #   Article model
├── schemas/                 # Pydantic request/response schemas (layer 2)
│   ├── __init__.py          #   Re-exports schemas (optional)
│   ├── user.py              #   User schemas + auth schemas
│   └── article.py           #   Article schemas
├── crud/                    # Data-access functions (layer 3)
│   ├── __init__.py          #   Re-exports CRUD functions (optional)
│   ├── user.py              #   User DB operations
│   └── article.py           #   Article DB operations
├── routers/                 # FastAPI route handlers (layer 4)
│   ├── __init__.py          #   Re-exports routers
│   ├── health.py            #   /health endpoint
│   ├── user.py              #   /api/users/* endpoints
│   └── article.py           #   /api/articles/* endpoints
└── utils/                   # Shared utilities
    ├── auth.py              #   JWT creation & current-user dependency
    ├── security.py          #   bcrypt hash / verify
    ├── permissions.py       #   RBAC 依赖注入 (require_role / require_any_role / require_permission)
    ├── response.py          #   success_response() / error_response() helpers
    ├── exception.py         #   Exception handler implementations (DEBUG_MODE from ENV)
    └── exception_handlers.py#   register_exception_handlers(app)
```

---

## 3. Module Architecture (4-Layer Pattern)

Every feature module follows **exactly 4 layers**. Data flows: **Router → CRUD → Model**, and back via **Schema**.

```
┌─────────────────────────────────────────┐
│  routers/<module>.py   (Route handlers) │  ← FastAPI endpoints, Depends(), HTTPException
├─────────────────────────────────────────┤
│  crud/<module>.py      (DB operations)  │  ← Async queries, no HTTP logic
├─────────────────────────────────────────┤
│  schemas/<module>.py   (Pydantic models)│  ← Request validation & response serialization
├─────────────────────────────────────────┤
│  models/<module>.py    (SQLAlchemy ORM)  │  ← Table mapping, relationships
└─────────────────────────────────────────┘
```

**Rules:**
- **Routers** depend on (import from) `crud.*`, `schemas.*`, `models.*`, `utils.*`
- **CRUD** depends on `models.*` and `schemas.*`
- **Schemas** depend on nothing (standalone Pydantic models)
- **Models** depend on nothing project-internal (SQLAlchemy only)
- **Never** import a router from CRUD or a schema from a model.

---

## 4. Role & Permission System (RBAC)

项目采用标准 RBAC（基于角色的访问控制）模型，定义在 `utils/permissions.py` 中：

```
用户(User) -- N:N --> 角色(Role) -- N:N --> 权限(Permission)
```

### 权限依赖注入

| Dependency | 说明 | 典型用法 |
|------------|------|---------|
| `require_role("admin")` | 需要指定角色 | `Depends(require_role("admin"))` |
| `require_any_role("author", "admin")` | 需要任意一个角色 | `Depends(require_any_role("author", "admin"))` |
| `require_permission("article:create")` | 需要指定权限 | `Depends(require_permission("article:create"))` |
| `require_any_permission("a", "b")` | 需要任意一个权限 | `Depends(require_any_permission("article:delete", "admin:all"))` |

### 在路由中使用

```python
from utils.permissions import require_role, require_any_role, require_permission

# 需要指定角色
@router.get("/admin-only")
async def admin_only(user: User = Depends(require_role("admin"))):
    ...

# 需要任意一个角色
@router.post("/articles")
async def create_article(user: User = Depends(require_any_role("author", "admin"))):
    ...

# 需要指定权限
@router.delete("/items/{id}")
async def delete_item(user: User = Depends(require_permission("article:delete"))):
    ...
```

### 预置角色

| 角色 | 说明 | 典型权限 |
|------|------|---------|
| `admin` | 管理员 | 全部权限 |
| `author` | 作者 | 文章创建/编辑 |
| `user` | 普通用户 | 文章查看 |
| `reader` | 读者 | 仅查看 |

> **注意**：不要使用旧的 `allow_user` / `allow_author` / `allow_admin`，已废弃。统一使用 `require_role` / `require_any_role`。

---

## 5. Response Convention

Always use `success_response()` or `error_response()` from `utils/response.py`.

```python
from utils.response import success_response

# Success — standard format
return success_response(
    message="操作成功",
    data={...}            # Serialized dict / Pydantic.model_dump()
)

# Error — raises HTTPException (caught by global handler)
raise HTTPException(status_code=404, detail="资源不存在")
```

Response JSON shape:
```json
{
  "code": 200,
  "message": "操作成功",
  "data": { ... }
}
```

---

## 6. Articles Module — Canonical CRUD Example

This is the **reference implementation** for all new modules.

### 6.1 Model (`models/article.py`)

```python
from typing import Optional
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base

class Article(Base):
    __tablename__ = 'article'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Optional relationship (no DB-level FK, use ORM relationship only)
    user: Mapped[Optional["User"]] = relationship(
        "User", backref="articles"
    )

    @property
    def user_name(self) -> Optional[str]:
        return self.user.username if self.user else None

    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title}', user_id={self.user_id})>"
```

**Key conventions:**
- Inherit from `Base` (declared in `models/base.py` — provides `created_at`, `updated_at` using UTC via `_utcnow()`)
- Soft-delete via `is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)`
- Foreign key fields use `Integer` without FK constraint at DB level — **禁止在数据库层面添加外键约束**（不要使用 `ForeignKey`、`ForeignKeyConstraint` 或任何 DB-level FK），关联关系仅通过 ORM `relationship()` 维护
- Relationships and `@property` for computed fields
- `__repr__` for debugging

### 6.2 Schemas (`schemas/article.py`)

```python
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class ArticleBase(BaseModel):
    title: str = Field(..., max_length=255, description="文章标题")
    content: Optional[str] = Field(None, description="文章内容")

class ArticleCreate(ArticleBase):
    pass

class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="文章标题")
    content: Optional[str] = Field(None, description="文章内容")

class ArticleResponse(ArticleBase):
    id: int
    user_id: Optional[int]
    user_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ArticleListResponse(BaseModel):
    items: list[ArticleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
```

**Key conventions:**
- `*Create` — inherits from `*Base`, all required fields
- `*Update` — flat `BaseModel`, **all fields Optional** (partial update via `exclude_unset=True`)
- `*Response` — inherits from `*Base`, adds `id` / timestamps / computed fields, sets `model_config = ConfigDict(from_attributes=True)`
- `*ListResponse` — always wraps paginated results
- Use `description=` in Chinese for Field (optional but conventional)

### 6.3 CRUD (`crud/article.py`)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from models.article import Article
from schemas.article import ArticleCreate, ArticleUpdate

async def get_article_by_id(db: AsyncSession, article_id: int) -> Article | None:
    query = select(Article).options(joinedload(Article.user)).where(
        Article.id == article_id, Article.is_deleted == False
    )
    result = await db.execute(query)
    return result.scalars().unique().one_or_none()

async def get_articles(
    db: AsyncSession, page: int = 1, page_size: int = 10
) -> tuple[list[Article], int]:
    offset = (page - 1) * page_size
    count_query = select(func.count(Article.id)).where(Article.is_deleted == False)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = (
        select(Article)
        .options(joinedload(Article.user))
        .where(Article.is_deleted == False)
        .order_by(Article.created_at.desc())
        .offset(offset).limit(page_size)
    )
    result = await db.execute(query)
    articles = list(result.scalars().unique().all())
    return articles, total

async def create_article(db: AsyncSession, article_data: ArticleCreate, user_id: int) -> Article:
    article = Article(**article_data.model_dump(), user_id=user_id)
    db.add(article)
    await db.flush()
    await db.refresh(article)
    return article

async def update_article(
    db: AsyncSession, article: Article, article_data: ArticleUpdate
) -> Article:
    update_data = article_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(article, field, value)
    await db.flush()
    await db.refresh(article)
    return article

async def delete_article(db: AsyncSession, article: Article) -> Article:
    article.is_deleted = True
    await db.flush()
    await db.refresh(article)
    return article
```

**Key conventions:**
- All functions are `async` and accept `db: AsyncSession` as first parameter
- **Soft delete**: never hard-delete — set `is_deleted = True`
- **Paginated list**: return `tuple[list[Model], int]` (items + total), compute offset manually
- **Get by ID**: `result.scalars().unique().one_or_none()`
- **Create**: `db.add()` → `flush()` → `refresh()` — accept `**model_dump()` for scalar fields; user-existence validation is done in the router layer, not CRUD
- **Update**: `model_dump(exclude_unset=True)` → iter `setattr()` → `flush()` → `refresh()` — accept the ORM object (not ID), so ownership check is caller's responsibility
- **Delete**: set `is_deleted = True` → `flush()` → `refresh()`
- Use `joinedload()` for eager-loading relationships when needed
- Use `flush()` instead of `commit()` — `get_db` dependency auto-commits on yield success

### 6.4 Router (`routers/article.py`)

```python
import math
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from models.user import User
from schemas.article import ArticleCreate, ArticleUpdate, ArticleResponse, ArticleListResponse
from crud.article import get_article_by_id, get_articles, create_article, update_article, delete_article
from crud.user import get_user_by_id
from utils.response import success_response
from utils.permissions import require_role, require_any_role

router = APIRouter(prefix="/api/articles", tags=["articles"])

# --- Public list (no auth required) ---
@router.get("")
async def list_articles(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    articles, total = await get_articles(db, page, page_size)
    total_pages = math.ceil(total / page_size)
    return success_response(
        message="获取文章列表成功",
        data=ArticleListResponse(
            items=[ArticleResponse.model_validate(a) for a in articles],
            total=total, page=page, page_size=page_size, total_pages=total_pages
        ).model_dump()
    )

# --- Detail (authenticated user) ---
@router.get("/{article_id}")
async def get_article_detail(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_any_role("user", "author", "admin"))
):
    article = await get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文章不存在")
    return success_response(message="获取文章详情成功", data=ArticleResponse.model_validate(article))

# --- Create (author/admin) ---
@router.post("")
async def create_new_article(
    article_data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_any_role("author", "admin"))
):
    db_user = await get_user_by_id(db, user.id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    article = await create_article(db, article_data, user.id)
    return success_response(message="创建文章成功", data=ArticleResponse.model_validate(article))

# --- Update (author/admin, ownership check) ---
@router.put("/{article_id}")
async def update_existing_article(
    article_id: int,
    article_data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_any_role("author", "admin"))
):
    article = await get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.user_id != user.id:
        raise HTTPException(status_code=403, detail="只能修改自己的文章")
    updated_article = await update_article(db, article, article_data)
    return success_response(message="更新文章成功", data=ArticleResponse.model_validate(updated_article))

# --- Delete (admin only) ---
@router.delete("/{article_id}")
async def delete_existing_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin"))
):
    article = await get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    deleted_article = await delete_article(db, article)
    return success_response(message="删除文章成功", data=ArticleResponse.model_validate(deleted_article))
```

**Key conventions:**
- `APIRouter(prefix="/api/<plural>", tags=["<plural>"])`
- `get_db` dependency from `config.db_conf`
- HTTPException for error cases (caught by global handler, formatted as unified JSON)
- `ArticleResponse.model_validate(obj)` for serialization
- `ArticleListResponse(…).model_dump()` for paginated list responses
- Ownership check: `article.user_id != user.id` before update
- User-existence check in router (not CRUD) before create
- Role-based access via `require_role` / `require_any_role` / `require_permission`

---

## 7. User Module — Key Differences

The `user` module is special because it handles auth, but its structure matches the 4-layer pattern:

| Aspect | User Module | Article Module (Canonical) |
|--------|------------|---------------------------|
| Model | `User` + `Base` (DeclarativeBase) | `Article(Base)` |
| Auth schemas | `UserLogin`, `TokenData`, `LoginResponse`, `RefreshTokenRequest`, `UserRoleUpdate` | None |
| CRUD extras | Password hashing, cascade soft-delete of user's articles | None |
| Router extras | `/register`, `/login`, `/refresh`, `/info`, `/{id}/role` | Standard CRUD |

**Do NOT use User as a template for new business modules.** Use **Article** as the template.

---

## 8. Creating a New Module — Step-by-Step Checklist

When asked to create a new module (e.g. `tag`, `category`, `comment`, `setting`):

```
Step 1: models/<module>.py      ← Define ORM model (inherit Base)
Step 2: schemas/<module>.py     ← Define Pydantic schemas (*Base, *Create, *Update, *Response, *ListResponse)
Step 3: crud/<module>.py        ← Implement CRUD functions (get_by_id, get_list, create, update, delete)
Step 4: routers/<module>.py     ← Implement endpoints (list, detail, create, update, delete)
Step 5: Alembic migration       ← `uv run alembic revision --autogenerate -m "add_<module>"`
Step 6: Register router         ← In routers/__init__.py + main.py
```

**Rules to follow:**
- Follow **Article module** code exactly — same import patterns, same function signatures, same response format
- Soft-delete always (`is_deleted` boolean) — never hard-delete
- **Never use DB-level foreign keys** — do NOT use `ForeignKey`, `ForeignKeyConstraint`, or any database-level FK constraint. Foreign key columns should be plain `Integer` (with optional `index=True`). All table relationships are maintained only via ORM `relationship()`.
- Paginated list always returns `(items, total)` tuple from CRUD
- Use `joinedload()` for relationships in read queries
- Use `model_dump(exclude_unset=True)` for partial updates
- Use `model_config = ConfigDict(from_attributes=True)` on `*Response` schemas
- Use `*ListResponse` wrapper for list endpoints
- Role-check all endpoints appropriately (use `require_role` / `require_any_role` / `require_permission`)
- User-existence validation in router layer, not CRUD
- Use `flush()` instead of `commit()` in CRUD — `get_db` dependency auto-commits on yield success
- Chinese `description=` in Field is acceptable but optional

---

## 9. DB Session & Migration

**Session dependency** (`config/db_conf.py`):
```python
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**Application lifespan** (`main.py`) — closes DB engine and Redis on shutdown:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from config.db_conf import async_engine
    from config.cache_config import redis_client
    await async_engine.dispose()
    await redis_client.aclose()
```

**Alembic migration:**
```bash
# Auto-generate from model changes
uv run alembic revision --autogenerate -m "description"

# Apply
uv run alembic upgrade head
```

---

## 10. Authentication Flow

| Endpoint | Description |
|----------|-------------|
| `POST /api/users/register` | Create user (bcrypt-hashed password) |
| `POST /api/users/login` | Returns `access_token` (30min) + `refresh_token` (7d) |
| `POST /api/users/refresh` | Exchange refresh_token for new token pair |
| `GET /api/users/info` | Get current user info (`Authorization: Bearer <token>`) |

Token is passed as `Authorization: Bearer <token>` header. The `get_current_user` dependency (in `utils/auth.py`) decodes the JWT and returns the `User` ORM object.

---

## 11. Cache Layer (Optional)

Available via `cache/base_cache.py` (Redis-backed). Use for read-heavy endpoints:

```python
from cache.base_cache import BaseCache

article_cache = BaseCache(prefix="article", default_expire=300)

# In CRUD / Router
cached = await article_cache.get_json(f"detail:{id}")
if cached:
    return cached
# ... fetch from DB, then:
await article_cache.set(f"detail:{id}", serialized_data)
```

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
