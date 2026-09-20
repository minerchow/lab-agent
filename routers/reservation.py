import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from models.user import User
from schemas.reservation import (
    ReservationCreateRequest,
    ReservationUpdateRequest,
    ReservationResponse,
    ReservationDetailResponse,
    ReservationListResponse,
)
from crud.reservation import (
    get_reservation_by_id,
    get_reservations,
    create_reservation,
    update_reservation,
    delete_reservation,
    approve_reservation,
    cancel_reservation,
)
from utils.response import success_response
from utils.auth import get_current_user
from utils.permissions import require_role

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


@router.get("/list")
async def list_reservations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    user_id: Optional[int] = Query(None, description="按用户筛选"),
    lab_id: Optional[int] = Query(None, description="按实验室筛选"),
    status: Optional[int] = Query(None, description="状态筛选：0 待审核，1 已通过，2 已拒绝，3 已取消"),
    keywords: Optional[str] = Query(None, description="关键字搜索（实验室名称、备注）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reservations, total = await get_reservations(
        db, page, page_size, user_id, lab_id, status, keywords
    )
    total_pages = math.ceil(total / page_size) if total else 0
    return success_response(
        message="获取预约列表成功",
        data=ReservationListResponse(
            items=[ReservationDetailResponse.model_validate(r) for r in reservations],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ).model_dump(),
    )


@router.get("/my")
async def list_my_reservations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reservations, total = await get_reservations(db, page, page_size, user.id)
    total_pages = math.ceil(total / page_size) if total else 0
    return success_response(
        message="获取我的预约列表成功",
        data=ReservationListResponse(
            items=[ReservationDetailResponse.model_validate(r) for r in reservations],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ).model_dump(),
    )


@router.get("/detail/{reservation_id}")
async def get_reservation_detail(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reservation = await get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    return success_response(
        message="获取预约详情成功",
        data=ReservationDetailResponse.model_validate(reservation).model_dump(),
    )


@router.post("/create")
async def create_new_reservation(
    data: ReservationCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reservation = await create_reservation(db, user.id, data)
    return success_response(
        message="创建预约成功",
        data=ReservationResponse.model_validate(reservation).model_dump(),
    )


@router.post("/update/{reservation_id}")
async def update_existing_reservation(
    reservation_id: int,
    data: ReservationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reservation = await get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if reservation.user_id != user.id and not user.has_role("admin"):
        raise HTTPException(status_code=403, detail="只能修改自己的预约")
    reservation = await update_reservation(db, reservation_id, data)
    return success_response(
        message="更新预约成功",
        data=ReservationResponse.model_validate(reservation).model_dump(),
    )


@router.post("/delete/{reservation_id}")
async def delete_existing_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reservation = await get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if reservation.user_id != user.id and not user.has_role("admin"):
        raise HTTPException(status_code=403, detail="只能删除自己的预约")
    reservation = await delete_reservation(db, reservation_id)
    return success_response(
        message="删除预约成功",
        data=ReservationResponse.model_validate(reservation).model_dump(),
    )


@router.post("/approve/{reservation_id}")
async def approve_existing_reservation(
    reservation_id: int,
    approved: bool = Query(..., description="是否通过审核"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    reservation = await approve_reservation(db, reservation_id, approved)
    return success_response(
        message="审核预约成功",
        data=ReservationResponse.model_validate(reservation).model_dump(),
    )


@router.post("/cancel/{reservation_id}")
async def cancel_existing_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reservation = await get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if reservation.user_id != user.id and not user.has_role("admin"):
        raise HTTPException(status_code=403, detail="只能取消自己的预约")
    reservation = await cancel_reservation(db, reservation_id)
    return success_response(
        message="取消预约成功",
        data=ReservationResponse.model_validate(reservation).model_dump(),
    )
