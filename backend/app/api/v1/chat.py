from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.api.dependencies.permissions import require_permissions
from app.models.user import User
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages", response_model=ChatMessageResponse)
async def send_message(
    payload: ChatMessageRequest,
    current_user: User = Depends(require_permissions("chat.use")),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    result = await chat_service.send_chat_message(
        db,
        actor=current_user,
        content=payload.content,
        conversation_id=payload.conversation_id,
    )
    return ChatMessageResponse(**result)
