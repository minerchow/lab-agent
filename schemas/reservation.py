from datetime import datetime

from pydantic import BaseModel, Field
from typing import Optional


class ReservationCreateRequest(BaseModel):
    """创建预约请求"""
    lab_id: int = Field(..., description="实验室 ID")
    equipment_id: Optional[int] = Field(None, description="设备 ID，空表示只预约实验室")
    date: str = Field(..., description="预约日期 (YYYY-MM-DD)")
    start_time: str = Field(..., description="开始时间 (HH:MM)")
    end_time: str = Field(..., description="结束时间 (HH:MM)")
    remark: Optional[str] = Field(None, description="备注")


class ReservationUpdateRequest(BaseModel):
    """更新预约请求"""
    start_time: Optional[str] = Field(None, description="开始时间 (HH:MM)")
    end_time: Optional[str] = Field(None, description="结束时间 (HH:MM)")
    date: Optional[str] = Field(None, description="预约日期 (YYYY-MM-DD)")
    remark: Optional[str] = Field(None, description="备注")


class ReservationListQuery(BaseModel):
    """预约列表查询参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")
    user_id: Optional[int] = Field(None, description="用户 ID 筛选")
    lab_id: Optional[int] = Field(None, description="实验室 ID 筛选")
    status: Optional[int] = Field(None, description="状态筛选：0 待审核，1 已通过，2 已拒绝，3 已取消")
    keywords: Optional[str] = Field(None, description="关键字搜索（实验室名称、备注）")


class ReservationResponse(BaseModel):
    """预约响应"""
    id: int
    user_id: int
    lab_id: int
    equipment_id: Optional[int]
    date: str
    start_time: str
    end_time: str
    remark: Optional[str]
    status: int
    type: str | None = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AuditReservationRequest(BaseModel):
    status: int  #  1 | 2
class ReservationDetailResponse(ReservationResponse):
    """预约详情响应（包含关联信息）"""
    user_name: Optional[str] = None
    lab_name: Optional[str] = None
    equipment_name: Optional[str] = None


class ReservationListResponse(BaseModel):
    """预约列表响应"""
    items: list[ReservationDetailResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
