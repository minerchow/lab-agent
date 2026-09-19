import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from models.user import User
from schemas.equipment import EquipmentCreateRequest, EquipmentUpdateRequest, EquipmentResponse, EquipmentListResponse
from crud.equipment import get_equipment_page_list, create_equipment, update_equipment, delete_equipment
from crud.lab import get_lab_by_id
from utils.response import success_response
from utils.permissions import require_role
from utils.auth import get_current_user

router = APIRouter(prefix="/api/equipments", tags=["equipments"])


@router.get("/list")
async def list_equipments(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keywords: Optional[str] = Query(None, description="搜索关键词"),
    lab_id: Optional[int] = Query(None, description="按实验室筛选"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    equipments, total = await get_equipment_page_list(db, page, page_size, keywords, lab_id)
    total_pages = math.ceil(total / page_size) if total else 0
    return success_response(
        message="获取设备列表成功",
        data=EquipmentListResponse(
            items=[EquipmentResponse.model_validate(e) for e in equipments],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ).model_dump(),
    )


@router.post("/create")
async def create_new_equipment(
    data: EquipmentCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    # 验证实验室是否存在
    lab = await get_lab_by_id(db, data.lab_id)
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="实验室不存在")
    
    equipment = await create_equipment(db, data)
    return success_response(message="创建设备成功", data=EquipmentResponse.model_validate(equipment).model_dump())


@router.post("/update/{equipment_id}")
async def update_existing_equipment(
    equipment_id: int,
    data: EquipmentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    # 如果请求中包含 lab_id，需要验证实验室是否存在
    if data.lab_id is not None:
        lab = await get_lab_by_id(db, data.lab_id)
        if not lab:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="实验室不存在")
    
    equipment = await update_equipment(db, equipment_id, data)
    return success_response(message="更新设备成功", data=EquipmentResponse.model_validate(equipment).model_dump())


@router.post("/delete/{equipment_id}")
async def delete_existing_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    equipment = await delete_equipment(db, equipment_id)
    return success_response(message="删除设备成功", data=EquipmentResponse.model_validate(equipment).model_dump())
