from datetime import datetime
from typing import Optional, List

from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.role import user_role


class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 多对多：用户-角色
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=user_role,
        primaryjoin="User.id == user_role.c.user_id",
        secondaryjoin="Role.id == user_role.c.role_id",
        backref="users",
        lazy="selectin",
    )

    def has_role(self, role_name: str) -> bool:
        """检查用户是否拥有指定角色"""
        return any(r.name == role_name for r in self.roles)

    def has_permission(self, permission_code: str) -> bool:
        """检查用户是否拥有指定权限"""
        for role in self.roles:
            for perm in role.permissions:
                if perm.code == permission_code:
                    return True
        return False

    def get_role_names(self) -> list[str]:
        """获取用户所有角色名"""
        return [r.name for r in self.roles]

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', roles={[r.name for r in self.roles]})>"
