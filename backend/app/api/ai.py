"""IA juridique : chat RAG, traduction anti-jargon."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, AuditLog
from ..core.security import get_current_user
from ..services import ai as ai_service

router = APIRouter()


class ChatIn(BaseModel):
    question: str
    falc: bool = False
    context: str | None = None


class TranslateIn(BaseModel):
    text: str


@router.post("/chat")
async def chat(
    data: ChatIn,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    response = await ai_service.chat(data.question, data.context, falc=data.falc)
    db.add(AuditLog(action="ai.chat", actor_id=current.id, payload={"len": len(data.question)}))
    return response


@router.post("/translate")
async def translate(
    data: TranslateIn,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    response = await ai_service.translate_jargon(data.text)
    db.add(AuditLog(action="ai.translate", actor_id=current.id, payload={"len": len(data.text)}))
    return response
