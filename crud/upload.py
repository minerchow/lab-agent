import os
import time
import uuid
import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile

from config.upload_config import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    UPLOAD_DIR,
    get_upload_file_url,
)
from schemas.upload import UploadResponse


def save_upload_file(file: UploadFile) -> UploadResponse:
    """保存上传文件到磁盘，并返回文件信息"""
    if not file.filename:
        raise HTTPException(status_code=404, message="文件名不能为空")

    # 原始的文件名  用户头像.jpg
    orignal_name = os.path.basename(file.filename)
    # 文件后缀 .jpg
    ext = Path(orignal_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=404, message=f"不自持的文件后缀：{ext}")
    # 文件大小校验
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=404,
            message=f"文件不能超过 {MAX_FILE_SIZE // 1024 // 1024}MB",
        )
    # 设置唯一的文件名称   199323213213_ddadaqwerq.jpg
    disk_name = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}{ext}"
    # 文件存储的实际路径
    save_path = UPLOAD_DIR / disk_name

    # 流式写文件
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return UploadResponse(
        original_name=orignal_name,
        disk_name=disk_name,
        size=file.size,
        url=get_upload_file_url(disk_name),
    )