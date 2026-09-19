from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from models.lab import Lab
from schemas.lab import LabCreateRequest, LabUpdateRequest


async def get_lab_by_id(db: AsyncSession, lab_id: int) -> Lab | None:
    result = await db.execute(
        select(Lab)
        .options(joinedload(Lab.user))
        .where(Lab.id == lab_id, Lab.is_deleted == False)
    )
    return result.scalars().unique().one_or_none()


async def get_lab_by_name(db: AsyncSession, name: str) -> Lab | None:
    result = await db.execute(
        select(Lab).where(Lab.name == name, Lab.is_deleted == False)
    )
    return result.scalars().one_or_none()


async def get_lab_page_list(
    db: AsyncSession, page: int, page_size: int, keywords: str | None = None, status: int | None = None
) -> tuple[list[Lab], int]:
    offset = (page - 1) * page_size

    conditions = [Lab.is_deleted == False]
    if keywords:
        conditions.append(
            or_(
                Lab.name.like(f"%{keywords}%"),
                Lab.location.like(f"%{keywords}%"),
                Lab.description.like(f"%{keywords}%"),
            )
        )
    if status is not None:
        conditions.append(Lab.status == status)

    count_query = select(func.count(Lab.id)).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = (
        select(Lab)
        .options(joinedload(Lab.user))
        .where(*conditions)
        .order_by(Lab.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    labs = list(result.scalars().unique().all())

    return labs, total


async def create_lab(db: AsyncSession, data: LabCreateRequest, user_id: int) -> Lab:
    exists = await get_lab_by_name(db, data.name)
    if exists:
        raise HTTPException(status_code=400, detail="实验室名称已存在")

    lab = Lab(**data.model_dump(), user_id=user_id)
    db.add(lab)
    await db.flush()
    await db.refresh(lab)
    return lab


async def update_lab(db: AsyncSession, lab_id: int, data: LabUpdateRequest) -> Lab:
    lab = await get_lab_by_id(db, lab_id)
    if not lab:
        raise HTTPException(status_code=404, detail="实验室不存在")

    payload = data.model_dump(exclude_unset=True)
    if "name" in payload and payload["name"] != lab.name:
        exists = await get_lab_by_name(db, payload["name"])
        if exists:
            raise HTTPException(status_code=400, detail="实验室名称已存在")

    for field, value in payload.items():
        setattr(lab, field, value)
    await db.flush()
    await db.refresh(lab)
    return lab


async def delete_lab(db: AsyncSession, lab_id: int) -> Lab:
    lab = await get_lab_by_id(db, lab_id)
    if not lab:
        raise HTTPException(status_code=404, detail="实验室不存在")

    lab.is_deleted = True
    await db.flush()
    await db.refresh(lab)
    return lab
