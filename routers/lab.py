import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from models.user import User
from schemas.lab import LabCreateRequest, LabUpdateRequest, LabResponse, LabListResponse
from crud.lab import get_lab_page_list, get_lab_by_id, create_lab, update_lab, delete_lab
from utils.response import success_response
from utils.auth import get_current_user

router = APIRouter(prefix="/api/labs", tags=["labs"])


@router.get("/list")
async def list_labs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keywords: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[int] = Query(None, description="实验室状态"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    labs, total = await get_lab_page_list(db, page, page_size, keywords, status)
    total_pages = math.ceil(total / page_size) if total else 0
    return success_response(
        message="获取实验室列表成功",
        data=LabListResponse(
            items=[LabResponse.model_validate(l) for l in labs],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ).model_dump(),
    )


@router.get("/detail/{lab_id}")
async def get_lab_detail(
    lab_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lab = await get_lab_by_id(db, lab_id)
    if not lab:
        raise HTTPException(status_code=404, detail="实验室不存在")
    return success_response(message="获取实验室信息成功", data=LabResponse.model_validate(lab).model_dump())


@router.post("/create")
async def create_new_lab(
    data: LabCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lab = await create_lab(db, data, user.id)
    return success_response(message="创建实验室成功", data=LabResponse.model_validate(lab).model_dump())


@router.post("/update/{lab_id}")
async def update_existing_lab(
    lab_id: int,
    data: LabUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lab = await update_lab(db, lab_id, data)
    return success_response(message="更新实验室成功", data=LabResponse.model_validate(lab).model_dump())


@router.delete("/{lab_id}")
async def delete_existing_lab(
    lab_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lab = await delete_lab(db, lab_id)
    return success_response(message="删除实验室成功", data=LabResponse.model_validate(lab).model_dump())
