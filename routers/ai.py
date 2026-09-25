from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAI

from models.user import User
from schemas.ai import ChatMessage, ChatRequest
from config.llm_config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from crud.kb import build_context
from utils.response import success_response
from utils.auth import get_current_user

router = APIRouter(prefix="/api/ai", tags=["AI相关的API"])

SYSTEM_PROMPT = """你是智能实验室预约系统的助手，回答要简洁。
如果下面提供了实验室资料，请依据资料回答，不要编造资料里没有的时间、规则、设备。
你目前查不到真实的实验室空闲、设备库存、预约记录。
如果用户问现在哪些实验室能约、某台设备此刻有没有空，请说明去「实验室列表」查看。
除了实验室相关的问题之外，不要回复无关的问题。
"""


def get_client() -> OpenAI:
    """创建OPENAI的客户端"""
    if not LLM_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="未获取到大模型的API Key"
        )
    return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)


def chat(data: ChatRequest):
    """大模型对话"""
    if not data.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="对话内容为空"
        )
    history = []
    for message in data.messages:
        if message.role in ("user", "assistant") and message.content.strip():
            history.append(message.model_dump())
    if not history:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请输入您要对话的内容"
        )

    # 取出用户最新的一条提问内容
    question = next(
        (item["content"] for item in reversed(history) if item["role"] == "user"), ""
    )

    knowledge = build_context(query=question)

    print(f"检索到的向量库的内容：{knowledge}")

    system_prompt = SYSTEM_PROMPT
    if knowledge:
        system_prompt += "\n\n以下是检索到的实验室的资料：\n" + knowledge

    client = get_client()

    try:
        res = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *history,
            ],
        )
        content = res.choices[0].message.content
        if not content or not content.strip():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="大模型没有返回内容"
            )
        return content
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="大模型调用失败，请稍后重试"
        )


@router.post("/chat")
def chat_endpoint(data: ChatRequest, current_user: User = Depends(get_current_user)):
    content = chat(data)
    return success_response(
        message="对话成功",
        data=ChatMessage(role="assistant", content=content).model_dump(),
    )
