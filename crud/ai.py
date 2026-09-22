from fastapi import HTTPException, status
from openai import OpenAI

from config.llm_config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT,
)
from schemas.ai import ChatMessage, ChatRequest

SYSTEM_PROMPT = "你是一个乐于助人的AI助手，请用简洁、准确的中文回答用户的问题。"


def get_client() -> OpenAI:
    """创建OPENAI的客户端"""
    if not LLM_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="未获取到大模型的API Key"
        )
    return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=LLM_TIMEOUT)


def chat(data: ChatRequest) -> str:
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

    client = get_client()

    try:
        res = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                ChatMessage(role="assistant", content=SYSTEM_PROMPT).model_dump(),
                *history,
            ],
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
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
