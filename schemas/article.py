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
