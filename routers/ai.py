from fastapi import APIRouter, Depends

from models.user import User
from schemas.ai import ChatMessage, ChatRequest
from crud.ai import chat
from utils.response import success_response
from utils.auth import get_current_user

router = APIRouter(prefix="/api/ai", tags=["AI相关的API"])


@router.post("/chat")
def chat_endpoint(data: ChatRequest, current_user: User = Depends(get_current_user)):
    content = chat(data)
    return success_response(
        message="对话成功",
        data=ChatMessage(role="assistant", content=content).model_dump(),
    )
