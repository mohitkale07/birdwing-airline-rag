from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, StringConstraints


ChatText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000),
]


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    text: ChatText


class ChatSource(BaseModel):
    document_name: str
    source: str
    start_page: int
    end_page: int


class ChatStartedEvent(BaseModel):
    type: Literal["start"] = "start"
    conversation_id: UUID | None
    user_message_id: UUID | None


class ChatTokenEvent(BaseModel):
    type: Literal["token"] = "token"
    content: str


class ChatCompletedEvent(BaseModel):
    type: Literal["done"] = "done"
    conversation_id: UUID | None
    user_message_id: UUID | None
    assistant_message_id: UUID | None
    sources: list[ChatSource]


class ChatErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message: str | None


class ConversationListResponse(BaseModel):
    items: list[ConversationSummary]
    total: int
    limit: int
    offset: int


class StoredChatMessage(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    sources: list[ChatSource] | None
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    id: UUID
    title: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    messages: list[StoredChatMessage]
    total_messages: int
    limit: int
    offset: int


class ConversationUpdateRequest(BaseModel):
    title: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    ] | None = None
    is_archived: bool | None = None


class ConversationActionResponse(BaseModel):
    id: UUID
    title: str
    is_archived: bool
    updated_at: datetime
