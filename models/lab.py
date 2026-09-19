from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean, String, Integer
from models.base import Base


class Lab(Base):
    __tablename__ = "labs"
    __table_args__ = {"comment": "实验室信息表"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), comment="实验室名称", nullable=False)
    location: Mapped[str | None] = mapped_column(String(100), comment="位置")
    capacity: Mapped[int] = mapped_column(Integer, comment="容纳人数", default=0)
    open_time: Mapped[str | None] = mapped_column(String(20), comment="开放开始时间")
    close_time: Mapped[str | None] = mapped_column(String(20), comment="开放结束时间")
    description: Mapped[str | None] = mapped_column(String(500), comment="简介")
    img: Mapped[str | None] = mapped_column(String(200), comment="封面图")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态：0-关闭，1-开放")
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, comment="创建人", nullable=True, index=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否删除")

    # 关联关系仅通过 ORM 维护，不建数据库层外键
    user: Mapped[Optional["User"]] = relationship(
        "User",
        backref="labs",
        foreign_keys=[user_id],
        primaryjoin="Lab.user_id == User.id",
    )

    @property
    def user_name(self) -> Optional[str]:
        return self.user.username if self.user else None

    def __repr__(self):
        return f"<Lab(id={self.id}, name='{self.name}', status={self.status})>"