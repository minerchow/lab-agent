from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from models.equipment import Equipment
from schemas.equipment import EquipmentCreateRequest, EquipmentUpdateRequest


async def get_equipment_by_id(db: AsyncSession, equipment_id: int) -> Equipment | None:
    result = await db.execute(
        select(Equipment)
        .options(joinedload(Equipment.lab))
        .where(Equipment.id == equipment_id, Equipment.is_deleted == False)
    )
    return result.scalars().unique().one_or_none()


async def get_equipment_page_list(
    db: AsyncSession, page: int, page_size: int, keywords: str | None = None, lab_id: int | None = None
) -> tuple[list[Equipment], int]:
    offset = (page - 1) * page_size

    conditions = [Equipment.is_deleted == False]
    if keywords:
        conditions.append(
            or_(
                Equipment.name.like(f"%{keywords}%"),
                Equipment.spec.like(f"%{keywords}%"),
                Equipment.description.like(f"%{keywords}%"),
            )
        )
    if lab_id is not None:
        conditions.append(Equipment.lab_id == lab_id)

    count_query = select(func.count(Equipment.id)).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = (
        select(Equipment)
        .options(joinedload(Equipment.lab))
        .where(*conditions)
        .order_by(Equipment.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    equipments = list(result.scalars().unique().all())

    return equipments, total


async def create_equipment(db: AsyncSession, data: EquipmentCreateRequest) -> Equipment:
    equipment = Equipment(**data.model_dump())
    db.add(equipment)
    await db.flush()
    await db.refresh(equipment)
    return equipment


async def update_equipment(db: AsyncSession, equipment_id: int, data: EquipmentUpdateRequest) -> Equipment:
    equipment = await get_equipment_by_id(db, equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="设备不存在")

    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(equipment, field, value)
    await db.flush()
    await db.refresh(equipment)
    return equipment


async def delete_equipment(db: AsyncSession, equipment_id: int) -> Equipment:
    equipment = await get_equipment_by_id(db, equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="设备不存在")

    equipment.is_deleted = True
    await db.flush()
    await db.refresh(equipment)
    return equipment
