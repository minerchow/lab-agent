from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class LabResponse(BaseModel):
    id: int
    name: str
    location: Optional[str] = None
    capacity: int
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    description: Optional[str] = None
    img: Optional[str] = None
    status: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class LabCreateRequest(BaseModel):
    name: str
    location: Optional[str] = None
    capacity: int = 0
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    description: Optional[str] = None
    img: Optional[str] = None
    status: int = 1

class LabUpdateRequest(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    capacity: Optional[int] = None
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    description: Optional[str] = None
    img: Optional[str] = None
    status: Optional[int] = None

class LabListResponse(BaseModel):
    items: list[LabResponse]
    total: int
    page: int
    page_size: int
    total_pages: int