import math
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from models.user import User
from models.article import Article
from schemas.article import ArticleCreate, ArticleUpdate, ArticleResponse, ArticleListResponse
from crud.article import get_article_by_id, get_articles, create_article, update_article, delete_article
from crud.user import get_user_by_id
from utils.response import success_response
from utils.permissions import require_role, require_any_role

router = APIRouter(prefix="/api/articles", tags=["articles"])


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
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        ).model_dump()
    )


@router.get("/{article_id}")
async def get_article_detail(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_any_role("user", "author", "admin"))
):
    article = await get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    return success_response(
        message="获取文章详情成功",
        data=ArticleResponse.model_validate(article)
    )


@router.post("")
async def create_new_article(
    article_data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_any_role("author", "admin"))
):
    db_user = await get_user_by_id(db, user.id)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    article = await create_article(db, article_data, user.id)
    return success_response(
        message="创建文章成功",
        data=ArticleResponse.model_validate(article)
    )


@router.put("/{article_id}")
async def update_existing_article(
    article_id: int,
    article_data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_any_role("author", "admin"))
):
    article = await get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )

    if article.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能修改自己的文章"
        )
    
    updated_article = await update_article(db, article, article_data)
    return success_response(
        message="更新文章成功",
        data=ArticleResponse.model_validate(updated_article)
    )


@router.delete("/{article_id}")
async def delete_existing_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin"))
):
    article = await get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )

    deleted_article = await delete_article(db, article)
    return success_response(
        message="删除文章成功",
        data=ArticleResponse.model_validate(deleted_article)
    )
