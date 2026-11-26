import uuid

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=6000)
    conversation_id: uuid.UUID | None = None


class ChatCitationResponse(BaseModel):
    order: int
    document_id: uuid.UUID
    document_title: str
    location: str | None
    page_number: int | None
    excerpt: str
    similarity: float


class ChatMessageResponse(BaseModel):
    conversation_id: uuid.UUID
    user_message_id: uuid.UUID
    assistant_message_id: uuid.UUID
    answer: str
    model: str
    grounded: bool
    notice: str | None
    citations: list[ChatCitationResponse]
