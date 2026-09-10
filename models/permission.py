from typing import Optional
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base


class Permission(Base):
    __tablename__ = "permission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self):
        return f"<Permission(id={self.id}, code='{self.code}')>"
