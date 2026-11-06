from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.conversation import Conversation
from src.models.message import Message
from src.schemas.chat import ConversationUpdateRequest


def list_conversations(
    db: Session,
    user_id: UUID,
    *,
    limit: int,
    offset: int,
    include_archived: bool,
) -> tuple[list[dict[str, object]], int]:
    filters = [Conversation.user_id == user_id]
    if not include_archived:
        filters.append(Conversation.is_archived.is_(False))

    message_count = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )
    last_message = (
        select(Message.content)
        .where(Message.conversation_id == Conversation.id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(1)
        .correlate(Conversation)
        .scalar_subquery()
    )
    rows = db.execute(
        select(
            Conversation,
            message_count.label("message_count"),
            last_message.label("last_message"),
        )
        .where(*filters)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    total = db.scalar(
        select(func.count(Conversation.id)).where(*filters)
    ) or 0

    items = [
        {
            "id": conversation.id,
            "title": conversation.title,
            "is_archived": conversation.is_archived,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "message_count": count,
            "last_message": preview[:200] if preview else None,
        }
        for conversation, count, preview in rows
    ]
    return items, total


def get_conversation(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[Conversation, list[Message], int]:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    messages = list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, Message.id)
            .offset(offset)
            .limit(limit)
        )
    )
    total = db.scalar(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id,
        )
    ) or 0
    return conversation, messages, total


def update_conversation(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
    payload: ConversationUpdateRequest,
) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one conversation field must be provided.",
        )
    if "title" in changes:
        if changes["title"] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Conversation title cannot be null.",
            )
        conversation.title = changes["title"]
    if "is_archived" in changes:
        if changes["is_archived"] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="is_archived cannot be null.",
            )
        conversation.is_archived = changes["is_archived"]

    db.commit()
    db.refresh(conversation)
    return conversation


def delete_conversation(
    db: Session,
    user_id: UUID,
    conversation_id: UUID,
) -> None:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )
    db.delete(conversation)
    db.commit()
