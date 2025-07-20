from typing import List, Optional

from fastapi import APIRouter
from openai import AsyncOpenAI
from pydantic import BaseModel

from .session import create as basic_create


class BaseSession(BaseModel):
    key: str
    input: str
    system: Optional[str] = None
    history: Optional[List[str]] = None


class Session(BaseSession):
    url: str
    model: str


router = APIRouter()


@router.post("/create")
async def create_session(session: Session):
    """
    创建助手会话

    Args:
        session (Session): 会话参数

    Returns:
        助手的纯文本回复
    """
    try:
        r = await basic_create(
            input=session.input,
            model=session.model,
            system=session.system,
            history=session.history,
            client=AsyncOpenAI(api_key=session.key, base_url=session.url),
        )
        return {"code": 0, "msg": r}
    except Exception as e:
        msg = type(e).__name__
        if str(e) != "":
            msg += f": {str(e)}"
        return {"code": 1, "msg": msg}


@router.post("/deepseek_chat")
async def deepseek_chat(session: BaseSession):
    """
    创建 deepseek-chat 助手会话

    Args:
        session (BaseSession): 会话参数

    Returns:
        助手的纯文本回复
    """
    return await create_session(
        Session(
            key=session.key,
            input=session.input,
            system=session.system,
            history=session.history,
            url="https://api.deepseek.com",
            model="deepseek-chat",
        )
    )


@router.post("/deepseek_reasoner")
async def deepseek_reasoner(session: BaseSession):
    """
    创建 deepseek-reasoner 助手会话

    Args:
        session (BaseSession): 会话参数

    Returns:
        助手的纯文本回复
    """
    return await create_session(
        Session(
            key=session.key,
            input=session.input,
            system=session.system,
            history=session.history,
            url="https://api.deepseek.com",
            model="deepseek-reasoner",
        )
    )
