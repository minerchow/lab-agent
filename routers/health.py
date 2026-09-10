from fastapi import APIRouter
from utils.response import success_response

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return success_response(message="服务正常运行")
