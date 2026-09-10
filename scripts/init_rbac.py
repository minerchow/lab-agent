"""
RBAC 基础数据初始化脚本
运行方式: PYTHONPATH=. uv run python scripts/init_rbac.py
"""
import asyncio
from config.db_conf import AsyncSessionLocal
from models.role import Role, role_permission
from models.permission import Permission
from sqlalchemy import select, insert


# 预设权限
PERMISSIONS = [
    # 文章权限
    {"code": "article:read", "name": "查看文章", "description": "查看文章列表和详情"},
    {"code": "article:create", "name": "创建文章", "description": "创建新文章"},
    {"code": "article:update", "name": "更新文章", "description": "修改文章内容"},
    {"code": "article:update:own", "name": "更新自己的文章", "description": "仅修改自己创建的文章"},
    {"code": "article:delete", "name": "删除文章", "description": "删除任意文章"},
    {"code": "article:delete:own", "name": "删除自己的文章", "description": "仅删除自己创建的文章"},

    # 用户权限
    {"code": "user:read", "name": "查看用户", "description": "查看用户列表"},
    {"code": "user:create", "name": "创建用户", "description": "注册新用户"},
    {"code": "user:update", "name": "修改用户", "description": "修改用户信息"},
    {"code": "user:delete", "name": "删除用户", "description": "删除用户"},
    {"code": "user:assign_role", "name": "分配角色", "description": "给用户分配角色"},

    # 角色权限
    {"code": "role:read", "name": "查看角色", "description": "查看角色列表"},
    {"code": "role:create", "name": "创建角色", "description": "创建新角色"},
    {"code": "role:update", "name": "修改角色", "description": "修改角色信息和权限"},
    {"code": "role:delete", "name": "删除角色", "description": "删除角色"},
]

# 预设角色及权限编码
ROLES = [
    {
        "name": "admin",
        "description": "管理员，拥有所有权限",
        "permission_codes": [p["code"] for p in PERMISSIONS],
    },
    {
        "name": "author",
        "description": "作者，可以创建和管理自己的文章",
        "permission_codes": [
            "article:read", "article:create", "article:update:own", "article:delete:own",
        ],
    },
    {
        "name": "user",
        "description": "普通用户，仅能查看文章",
        "permission_codes": ["article:read"],
    },
]


async def init_rbac():
    async with AsyncSessionLocal() as db:
        try:
            # 1. 初始化权限
            print("正在初始化权限...")
            permission_map = {}  # code -> id

            for perm_data in PERMISSIONS:
                query = select(Permission).where(Permission.code == perm_data["code"])
                result = await db.execute(query)
                existing = result.scalars().one_or_none()

                if existing:
                    permission_map[perm_data["code"]] = existing.id
                    print(f"  权限已存在: {perm_data['code']}")
                else:
                    perm = Permission(**perm_data)
                    db.add(perm)
                    await db.flush()
                    permission_map[perm_data["code"]] = perm.id
                    print(f"  创建权限: {perm_data['code']} - {perm_data['name']}")

            # 2. 初始化角色
            print("\n正在初始化角色...")
            for role_data in ROLES:
                query = select(Role).where(Role.name == role_data["name"])
                result = await db.execute(query)
                existing = result.scalars().one_or_none()

                if existing:
                    role_id = existing.id
                    print(f"  角色已存在: {role_data['name']} (id={role_id})")
                    # 先删除旧关联
                    await db.execute(
                        role_permission.delete().where(role_permission.c.role_id == role_id)
                    )
                else:
                    role = Role(name=role_data["name"], description=role_data["description"])
                    db.add(role)
                    await db.flush()
                    role_id = role.id
                    print(f"  创建角色: {role_data['name']} - {role_data['description']} (id={role_id})")

                # 3. 插入角色-权限关联
                perm_ids = [permission_map[code] for code in role_data["permission_codes"]]
                if perm_ids:
                    for pid in perm_ids:
                        await db.execute(
                            insert(role_permission).values(role_id=role_id, permission_id=pid)
                        )
                    print(f"    分配权限: {len(perm_ids)} 个")

            await db.commit()
            print("\n✅ RBAC 基础数据初始化完成!")

        except Exception as e:
            await db.rollback()
            raise e


if __name__ == "__main__":
    asyncio.run(init_rbac())
