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
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10
) -> tuple[list[Article], int]:
    offset = (page - 1) * page_size
    
    count_query = select(func.count(Article.id)).where(Article.is_deleted == False)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = select(Article).options(joinedload(Article.user)).where(
        Article.is_deleted == False
    ).order_by(Article.created_at.desc()).offset(offset).limit(page_size)
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
    db: AsyncSession,
    article: Article,
    article_data: ArticleUpdate
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
