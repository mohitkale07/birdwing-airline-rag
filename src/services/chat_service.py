from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select

from src.db.database import SessionLocal
from src.models.conversation import Conversation
from src.models.message import Message
from src.schemas.chat import ChatRequest

HISTORY_MESSAGE_LIMIT = 6


@dataclass(frozen=True)
class SavedUserMessage:
    conversation_id: UUID
    message_id: UUID
    history: list[tuple[str, str]]


def save_user_message(
    user_id: UUID,
    request: ChatRequest,
) -> SavedUserMessage:
    with SessionLocal() as db:
        try:
            if request.conversation_id is None:
                conversation = Conversation(
                    user_id=user_id,
                    title=request.text[:200],
                )
                db.add(conversation)
                db.flush()
            else:
                conversation = db.scalar(
                    select(Conversation)
                    .where(
                        Conversation.id == request.conversation_id,
                        Conversation.user_id == user_id,
                    )
                    .with_for_update()
                )
                if conversation is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Conversation not found.",
                    )
                if conversation.is_archived:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Archived conversations cannot be continued.",
                    )

            previous_messages = list(
                db.scalars(
                    select(Message)
                    .where(Message.conversation_id == conversation.id)
                    .order_by(Message.created_at.desc(), Message.id.desc())
                    .limit(HISTORY_MESSAGE_LIMIT)
                )
            )
            previous_messages.reverse()
            history = [
                (message.role, message.content)
                for message in previous_messages
            ]

            user_message = Message(
                conversation_id=conversation.id,
                role="user",
                content=request.text,
            )
            db.add(user_message)
            conversation.updated_at = func.now()
            db.flush()

            saved_message = SavedUserMessage(
                conversation_id=conversation.id,
                message_id=user_message.id,
                history=history,
            )
            db.commit()
            return saved_message
        except Exception:
            db.rollback()
            raise


def save_assistant_message(
    conversation_id: UUID,
    content: str,
    sources: list[dict[str, Any]],
    retrieval_role: str,
) -> UUID:
    with SessionLocal() as db:
        try:
            conversation = db.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                )
            )
            if conversation is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found.",
                )

            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                sources=sources,
                message_metadata={"retrieval_role": retrieval_role},
            )
            db.add(assistant_message)
            conversation.updated_at = func.now()
            db.flush()
            message_id = assistant_message.id
            db.commit()
            return message_id
        except Exception:
            db.rollback()
            raise
