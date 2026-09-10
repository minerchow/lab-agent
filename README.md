# FastAPI Init

一个基于 FastAPI 的项目脚手架，集成了 SQLAlchemy 2.0 异步 ORM、Redis 缓存、JWT 认证、RBAC 权限管理等功能。

## 技术栈

| 层级 | 技术 |
|------|------|
| 框架 | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (async, MySQL via aiomysql) |
| 迁移 | Alembic |
| 认证 | JWT (access + refresh token) |
| 密码 | bcrypt via passlib |
| 缓存 | Redis (async) |
| 权限 | RBAC (角色-权限模型) |
| 包管理 | uv |

## 快速启动

```bash
# 1. 安装依赖
uv sync

# 2. 配置环境变量（见 .env 文件）

# 3. 初始化数据库
mysql -u root -p < app_db.sql

# 4. 启动服务
uv run python -m uvicorn main:app --reload
```

启动后访问：
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## 权限模型

项目采用 RBAC（基于角色的访问控制）模型：

```
用户(User) -- N:N --> 角色(Role) -- N:N --> 权限(Permission)
```

### 预置角色

| 角色 | 说明 |
|------|------|
| `admin` | 管理员，可管理所有资源和用户 |
| `author` | 作者，可创建/编辑自己的文章 |
| `user` | 普通用户，可查看文章 |
| `reader` | 读者，仅可查看文章 |

### 权限控制方式

路由层使用以下依赖注入进行权限检查：

```python
from utils.permissions import require_role, require_any_role, require_permission

# 需要指定角色
@router.get("/admin-only")
async def admin_only(user = Depends(require_role("admin"))):
    ...

# 需要任意一个角色
@router.post("/articles")
async def create_article(user = Depends(require_any_role("author", "admin"))):
    ...

# 需要指定权限
@router.delete("/items/{id}")
async def delete_item(user = Depends(require_permission("article:delete"))):
    ...
```

---

## 接口文档

### 统一响应格式

```json
{
  "code": 200,
  "message": "操作成功",
  "data": { ... }
}
```

### 认证方式

需要认证的接口在请求头中携带 JWT Token：

```
Authorization: Bearer <access_token>
```

---

### 1. 健康检查

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/health` | 无 | 服务健康检查 |

---

### 2. 用户模块 (`/api/users`)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | `/api/users/register` | 无 | 用户注册 |
| POST | `/api/users/login` | 无 | 用户登录 |
| POST | `/api/users/refresh` | 无 | 刷新 Token |
| GET | `/api/users/info` | 登录用户 | 获取当前用户信息 |
| GET | `/api/users/{user_id}` | admin | 查看指定用户信息 |
| PUT | `/api/users/{user_id}/roles` | admin | 修改用户角色 |
| DELETE | `/api/users/{user_id}` | admin | 删除用户（软删除） |

#### POST `/api/users/register` — 用户注册

**请求体：**
```json
{
  "username": "string (必填, max 50)",
  "password": "string (必填, min 6)"
}
```

**响应：**
```json
{
  "code": 200,
  "message": "注册成功",
  "data": {
    "id": 1,
    "username": "xiaoming",
    "nickname": null,
    "avatar": null,
    "roles": []
  }
}
```

#### POST `/api/users/login` — 用户登录

**请求体：**
```json
{
  "username": "string (必填)",
  "password": "string (必填)"
}
```

**响应：**
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "user": {
      "id": 1,
      "username": "xiaoming",
      "nickname": null,
      "avatar": null,
      "roles": [{"id": 1, "name": "admin"}]
    },
    "token": {
      "access_token": "eyJ...",
      "refresh_token": "eyJ...",
      "token_type": "bearer",
      "expires_in": 1800
    }
  }
}
```

#### POST `/api/users/refresh` — 刷新 Token

**请求头：** 无需 Authorization

**请求体：**
```json
{
  "refresh_token": "string (必填)"
}
```

**响应：**
```json
{
  "code": 200,
  "message": "Token刷新成功",
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

#### GET `/api/users/info` — 获取当前用户信息

**请求头：** `Authorization: Bearer <access_token>`

**响应：**
```json
{
  "code": 200,
  "message": "获取用户信息成功",
  "data": {
    "id": 1,
    "username": "xiaoming",
    "nickname": null,
    "avatar": null,
    "roles": [{"id": 1, "name": "admin"}]
  }
}
```

#### GET `/api/users/{user_id}` — 查看指定用户（admin）

**请求头：** `Authorization: Bearer <admin_token>`

**路径参数：** `user_id` — 用户ID

**响应：** 同上 `UserResponse` 格式

#### PUT `/api/users/{user_id}/roles` — 修改用户角色（admin）

**请求头：** `Authorization: Bearer <admin_token>`

**路径参数：** `user_id` — 用户ID

**请求体：**
```json
{
  "role_ids": [1, 2, 3]
}
```

**响应：**
```json
{
  "code": 200,
  "message": "修改用户角色成功",
  "data": {
    "id": 2,
    "username": "xiaoming2",
    "nickname": null,
    "avatar": null,
    "roles": [{"id": 1, "name": "admin"}, {"id": 3, "name": "reader"}]
  }
}
```

#### DELETE `/api/users/{user_id}` — 删除用户（admin）

**请求头：** `Authorization: Bearer <admin_token>`

**路径参数：** `user_id` — 用户ID

**响应：**
```json
{
  "code": 200,
  "message": "删除用户成功"
}
```

---

### 3. 文章模块 (`/api/articles`)

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/articles` | 无 | 文章列表（公开） |
| GET | `/api/articles/{article_id}` | user/author/admin | 文章详情 |
| POST | `/api/articles` | author/admin | 创建文章 |
| PUT | `/api/articles/{article_id}` | author/admin | 更新文章（仅作者） |
| DELETE | `/api/articles/{article_id}` | admin | 删除文章 |

#### GET `/api/articles` — 文章列表（公开）

**查询参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 (≥1) |
| `page_size` | int | 10 | 每页数量 (1-100) |

**响应：**
```json
{
  "code": 200,
  "message": "获取文章列表成功",
  "data": {
    "items": [
      {
        "id": 1,
        "title": "文章标题",
        "content": "文章内容",
        "user_id": 1,
        "user_name": "xiaoming",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
      }
    ],
    "total": 25,
    "page": 1,
    "page_size": 10,
    "total_pages": 3
  }
}
```

#### GET `/api/articles/{article_id}` — 文章详情

**请求头：** `Authorization: Bearer <token>`

**路径参数：** `article_id` — 文章ID

**响应：**
```json
{
  "code": 200,
  "message": "获取文章详情成功",
  "data": {
    "id": 1,
    "title": "文章标题",
    "content": "文章内容",
    "user_id": 1,
    "user_name": "xiaoming",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

#### POST `/api/articles` — 创建文章

**请求头：** `Authorization: Bearer <author/admin_token>`

**请求体：**
```json
{
  "title": "string (必填, max 255)",
  "content": "string (可选)"
}
```

**响应：** 返回创建后的 `ArticleResponse`

#### PUT `/api/articles/{article_id}` — 更新文章

**请求头：** `Authorization: Bearer <author/admin_token>`

**路径参数：** `article_id` — 文章ID

**请求体（部分更新）：**
```json
{
  "title": "新的标题 (可选)",
  "content": "新的内容 (可选)"
}
```

**注意：** 只能更新自己的文章，否则返回 `403`

**响应：** 返回更新后的 `ArticleResponse`

#### DELETE `/api/articles/{article_id}` — 删除文章

**请求头：** `Authorization: Bearer <admin_token>`

**路径参数：** `article_id` — 文章ID

**响应：**
```json
{
  "code": 200,
  "message": "删除文章成功"
}
```

---

### 4. 角色管理 (`/api/roles`)

> 所有角色管理接口均需要 admin 权限

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/roles` | admin | 角色列表（分页） |
| GET | `/api/roles/all` | admin | 所有角色（不分页） |
| GET | `/api/roles/{role_id}` | admin | 角色详情 |
| POST | `/api/roles` | admin | 创建角色 |
| PUT | `/api/roles/{role_id}` | admin | 更新角色 |
| DELETE | `/api/roles/{role_id}` | admin | 删除角色 |

#### GET `/api/roles` — 角色列表

**查询参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 10 | 每页数量 |

**响应：**
```json
{
  "code": 200,
  "message": "获取角色列表成功",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "admin",
        "description": "管理员",
        "permissions": [{"id": 1, "code": "user:manage", "name": "用户管理"}]
      }
    ],
    "total": 4,
    "page": 1,
    "page_size": 10,
    "total_pages": 1
  }
}
```

#### POST `/api/roles` — 创建角色

**请求体：**
```json
{
  "name": "string (必填)",
  "description": "string (可选)"
}
```

**响应：** 返回创建后的 `RoleResponse`

#### PUT `/api/roles/{role_id}` — 更新角色

**请求体（部分更新）：**
```json
{
  "name": "string (可选)",
  "description": "string (可选)"
}
```

#### DELETE `/api/roles/{role_id}` — 删除角色

**响应：**
```json
{
  "code": 200,
  "message": "删除角色成功"
}
```

---

### 5. 权限管理 (`/api/permissions`)

> 所有权限管理接口均需要 admin 权限

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/permissions` | admin | 权限列表（分页） |
| GET | `/api/permissions/all` | admin | 所有权限（不分页） |
| GET | `/api/permissions/{permission_id}` | admin | 权限详情 |
| POST | `/api/permissions` | admin | 创建权限 |
| PUT | `/api/permissions/{permission_id}` | admin | 更新权限 |
| DELETE | `/api/permissions/{permission_id}` | admin | 删除权限 |

#### GET `/api/permissions` — 权限列表

**查询参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码 |
| `page_size` | int | 10 | 每页数量 |

**响应：**
```json
{
  "code": 200,
  "message": "获取权限列表成功",
  "data": {
    "items": [
      {
        "id": 1,
        "code": "user:manage",
        "name": "用户管理",
        "description": "管理用户账号和角色"
      }
    ],
    "total": 10,
    "page": 1,
    "page_size": 10,
    "total_pages": 1
  }
}
```

#### POST `/api/permissions` — 创建权限

**请求体：**
```json
{
  "code": "string (必填, 如 article:create)",
  "name": "string (必填, 如 创建文章)",
  "description": "string (可选)"
}
```

#### PUT `/api/permissions/{permission_id}` — 更新权限

**请求体（部分更新）：**
```json
{
  "code": "string (可选)",
  "name": "string (可选)",
  "description": "string (可选)"
}
```

#### DELETE `/api/permissions/{permission_id}` — 删除权限

**响应：**
```json
{
  "code": 200,
  "message": "删除权限成功"
}
```

---

## 项目结构

```
fastapi-init/
├── main.py                  # 应用入口
├── config/                  # 配置层
│   ├── db_conf.py           #   数据库引擎 & 会话工厂
│   ├── jwt_config.py        #   JWT 配置
│   └── cache_config.py      #   Redis 客户端
├── models/                  # ORM 模型层
│   ├── base.py              #   Base 基类 (UTC 时间戳)
│   ├── user.py              #   User 模型 (多对多 Role)
│   ├── article.py           #   Article 模型
│   ├── role.py              #   Role 模型 & 关联表
│   └── permission.py        #   Permission 模型
├── schemas/                 # Pydantic 序列化层
│   ├── user.py              #   用户请求/响应模型
│   ├── article.py           #   文章请求/响应模型
│   ├── role.py              #   角色请求/响应模型
│   └── permission.py        #   权限请求/响应模型
├── crud/                    # 数据操作层
│   ├── user.py              #   用户 CRUD
│   ├── article.py           #   文章 CRUD
│   └── role.py              #   角色/权限 CRUD
├── routers/                 # API 路由层
│   ├── health.py            #   健康检查
│   ├── user.py              #   用户接口
│   ├── article.py           #   文章接口
│   └── role.py              #   角色/权限管理接口
├── utils/                   # 工具层
│   ├── auth.py              #   JWT 创建 & 解码
│   ├── security.py          #   密码哈希
│   ├── permissions.py       #   RBAC 权限依赖注入
│   ├── enums.py             #   枚举定义
│   ├── response.py          #   统一响应格式
│   └── exception_handlers.py#   全局异常处理
├── cache/                   # 缓存层
│   └── base_cache.py        #   Redis 缓存基类
├── alembic/                 # 数据库迁移
│   └── versions/            #   迁移脚本
├── .env                     # 开发环境变量
├── .env.test                # 测试环境变量
├── .env.production          # 生产环境变量
├── pyproject.toml           # 依赖配置
├── alembic.ini              # Alembic 配置
└── README.md                # 本文档
```

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| xiaoming | 需要自行设置 | admin |
| xiaoming2 | 需要自行设置 | author |

## 多环境配置

| 环境 | 配置文件 | 启动命令 |
|------|----------|----------|
| 开发 | `.env` | `APP_ENV=development uv run fastapi dev main.py` |
| 测试 | `.env.test` | `APP_ENV=test uv run fastapi dev main.py` |
| 生产 | `.env.production` | `APP_ENV=production uv run fastapi run main.py` |

## 数据库迁移

```bash
# 自动生成迁移脚本
uv run alembic revision --autogenerate -m "描述"

# 应用迁移
uv run alembic upgrade head

# 回滚一步
uv run alembic downgrade -1
```
