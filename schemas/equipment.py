from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class EquipmentResponse(BaseModel):
    id: int
    lab_id: int
    lab_name: str | None = None
    name: str
    description: str | None = None
    img: str | None = None
    spec: str | None = None
    quantity: int
    status: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
class EquipmentCreateRequest(BaseModel):
    lab_id: int
    name: str
    description: str | None = None
    img: str | None = None
    spec: str | None = None
    quantity: int = 1
    status: int = 1

class EquipmentUpdateRequest(BaseModel):
    lab_id: int | None = None
    name: str | None = None
    description: str | None = None
    img: str | None = None
    spec: str | None = None
    quantity: int | None = None
    status: int | None = None

class EquipmentListResponse(BaseModel):
    items: list[EquipmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
