from fastapi import APIRouter, File, UploadFile

from crud.upload import save_upload_file
from schemas.upload import UploadResponse
from utils.response import success_response

router = APIRouter(prefix="/api/files", tags=["文件管理"])

@router.post("/upload")
def upload(file: UploadFile = File(...)):
    """文件上传的接口"""
    result = save_upload_file(file)
    return success_response(message="上传成功", data=UploadResponse.model_validate(result).model_dump())
