from typing import Optional
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    original_name: str = Field(..., description="原始文件名")
    disk_name: str = Field(..., description="磁盘存储文件名")
    size: Optional[int] = Field(None, description="文件大小(字节)")
    url: str = Field(..., description="文件访问 URL")