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
    
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys="Article.user_id", primaryjoin="Article.user_id == User.id", backref="articles")
    
    @property
    def user_name(self) -> Optional[str]:
        return self.user.username if self.user else None

    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title}', user_id={self.user_id})>"
