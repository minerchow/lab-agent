from datetime import datetime
from typing import Optional
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from sqlalchemy.orm import selectinload

from models.reservation import Reservation
from schemas.reservation import ReservationCreateRequest, ReservationUpdateRequest, ReservationListQuery
from models.lab import Lab
from models.equipment import Equipment
from models.user import User


async def get_reservation_by_id(db: AsyncSession, reservation_id: int) -> Reservation | None:
    """根据 ID 获取预约记录（包含关联的 lab、equipment、user 信息）"""
    query = (
        select(Reservation)
        .options(selectinload(Reservation.lab), selectinload(Reservation.equipment), selectinload(Reservation.user))
        .where(Reservation.id == reservation_id, Reservation.is_deleted == False)
    )
    result = await db.execute(query)
    return result.scalars().unique().one_or_none()


async def get_reservations(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    user_id: Optional[int] = None,
    lab_id: Optional[int] = None,
    status: Optional[int] = None,
    keywords: Optional[str] = None
) -> tuple[list[Reservation], int]:
    """获取预约列表（分页）"""
    offset = (page - 1) * page_size
    
    conditions = [Reservation.is_deleted == False]
    if user_id is not None:
        conditions.append(Reservation.user_id == user_id)
    if lab_id is not None:
        conditions.append(Reservation.lab_id == lab_id)
    if status is not None:
        conditions.append(Reservation.status == status)
    
    # 关键字搜索：实验室名称、备注
    if keywords:
        conditions.append(
            or_(
                Lab.name.like(f"%{keywords}%"),
                Reservation.remark.like(f"%{keywords}%")
            )
        )
    
    # 统计总数
    count_query = select(func.count(Reservation.id)).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 获取数据
    query = (
        select(Reservation)
        .options(selectinload(Reservation.lab), selectinload(Reservation.equipment), selectinload(Reservation.user))
        .where(*conditions)
        .order_by(Reservation.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    reservations = list(result.scalars().unique().all())
    
    return reservations, total


async def create_reservation(
    db: AsyncSession,
    user_id: int,
    data: ReservationCreateRequest
) -> Reservation:
    """创建预约记录"""
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    
    # 验证日期和时间
    if data.date < current_date:
        raise HTTPException(status_code=400, detail="预约日期不能小于当前的日期")
    if data.end_time < data.start_time:
        raise HTTPException(status_code=400, detail="预约的结束时间不能小于开始时间")
    if data.date == current_date and data.start_time < current_time:
        raise HTTPException(status_code=400, detail="预约开始时间不能小于当前的时间")
    
    # 验证实验室是否存在且可用
    lab_query = select(Lab).where(Lab.id == data.lab_id, Lab.is_deleted == False)
    lab_result = await db.execute(lab_query)
    lab = lab_result.scalars().one_or_none()
    
    if not lab:
        raise HTTPException(status_code=404, detail="实验室不存在")
    if lab.status != 1:
        raise HTTPException(status_code=400, detail="实验室已关闭")
    if lab.open_time and data.start_time < lab.open_time:
        raise HTTPException(status_code=400, detail="预约时间不能早于实验室的开放时间")
    if lab.close_time and data.end_time > lab.close_time:
        raise HTTPException(status_code=400, detail="预约时间不能晚于实验室的关闭时间")
    
    # 如果指定了设备，验证设备是否存在且可用
    if data.equipment_id:
        equipment_query = select(Equipment).where(
            Equipment.id == data.equipment_id,
            Equipment.is_deleted == False
        )
        equipment_result = await db.execute(equipment_query)
        equipment = equipment_result.scalars().one_or_none()
        
        if not equipment:
            raise HTTPException(status_code=404, detail="实验室设备不存在")
        if equipment.status != 1:
            raise HTTPException(status_code=400, detail="实验室设备正在维修")
        # 验证设备属于该实验室
        if equipment.lab_id != data.lab_id:
            raise HTTPException(status_code=400, detail="设备不属于指定的实验室")
    
    # 检查时间段冲突
    conflict_query = select(Reservation).where(
        Reservation.lab_id == data.lab_id,
        Reservation.date == data.date,
        Reservation.status.in_([0, 1]),  # 0 表示待审核，1 已通过
        Reservation.start_time < data.end_time,
        Reservation.end_time > data.start_time,
        Reservation.is_deleted == False
    )
    
    if data.equipment_id:
        conflict_query = conflict_query.filter(Reservation.equipment_id == data.equipment_id)
    else:
        conflict_query = conflict_query.filter(Reservation.equipment_id.is_(None))
    
    conflict_result = await db.execute(conflict_query)
    if conflict_result.scalars().first():
        raise HTTPException(status_code=400, detail="该时段已预约")
    
    # 创建预约记录
    reservation_model = Reservation(
        user_id=user_id,
        lab_id=data.lab_id,
        equipment_id=data.equipment_id,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        remark=data.remark,
        status=0,  # 待审核
    )
    db.add(reservation_model)
    await db.flush()
    await db.refresh(reservation_model)
    
    return reservation_model


async def update_reservation(
    db: AsyncSession,
    reservation_id: int,
    data: ReservationUpdateRequest
) -> Reservation:
    """更新预约记录"""
    reservation = await get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    
    # 如果修改了时间，需要重新检查冲突
    if "start_time" in update_data or "end_time" in update_data or "date" in update_data:
        new_start = update_data.get("start_time", reservation.start_time)
        new_end = update_data.get("end_time", reservation.end_time)
        new_date = update_data.get("date", reservation.date)
        
        # 验证时间逻辑
        if new_end < new_start:
            raise HTTPException(status_code=400, detail="结束时间不能小于开始时间")
        
        # 检查时间段冲突（排除自己）
        conflict_query = select(Reservation).where(
            Reservation.lab_id == reservation.lab_id,
            Reservation.date == new_date,
            Reservation.id != reservation_id,
            Reservation.status.in_([0, 1]),
            Reservation.start_time < new_end,
            Reservation.end_time > new_start,
            Reservation.is_deleted == False
        )
        
        if reservation.equipment_id:
            conflict_query = conflict_query.filter(Reservation.equipment_id == reservation.equipment_id)
        else:
            conflict_query = conflict_query.filter(Reservation.equipment_id.is_(None))
        
        conflict_result = await db.execute(conflict_query)
        if conflict_result.scalars().first():
            raise HTTPException(status_code=400, detail="该时段已被其他预约占用")
    
    for field, value in update_data.items():
        setattr(reservation, field, value)
    
    await db.flush()
    await db.refresh(reservation)
    return reservation


async def delete_reservation(db: AsyncSession, reservation_id: int) -> Reservation:
    """软删除预约记录"""
    reservation = await get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    
    reservation.is_deleted = True
    await db.flush()
    await db.refresh(reservation)
    return reservation


async def approve_reservation(
    db: AsyncSession,
    reservation_id: int,
    approved: bool
) -> Reservation:
    """审核预约（通过/拒绝）"""
    reservation = await get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    
    if reservation.status != 0:  # 0 表示待审核
        raise HTTPException(status_code=400, detail="只能审核待审核状态的预约")
    
    reservation.status = 1 if approved else 2  # 1 已通过，2 已拒绝
    await db.flush()
    await db.refresh(reservation)
    return reservation


async def cancel_reservation(
    db: AsyncSession,
    reservation_id: int
) -> Reservation:
    """取消预约"""
    reservation = await get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    
    if reservation.status == 0:  # 待审核状态可以取消
        reservation.status = 3  # 3 已取消
    elif reservation.status == 1:  # 已通过状态也可以取消
        reservation.status = 3
    else:
        raise HTTPException(status_code=400, detail="只有待审核或已通过状态的预约可以取消")
    
    await db.flush()
    await db.refresh(reservation)
    return reservation
