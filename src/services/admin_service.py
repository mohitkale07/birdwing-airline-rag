from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.models.conversation import Conversation
from src.models.message import Message
from src.models.user import User


def list_users(
    db: Session,
    *,
    limit: int,
    offset: int,
    search: str | None,
) -> tuple[list[dict[str, object]], int]:
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                User.email.ilike(pattern),
                User.name.ilike(pattern),
            )
        )

    conversation_count = (
        select(func.count(Conversation.id))
        .where(Conversation.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )
    message_count = (
        select(func.count(Message.id))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )
    rows = db.execute(
        select(
            User,
            conversation_count.label("conversation_count"),
            message_count.label("message_count"),
        )
        .where(*filters)
        .order_by(User.created_at.desc(), User.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    total = db.scalar(select(func.count(User.id)).where(*filters)) or 0

    items = [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "is_restricted": user.is_restricted,
            "created_at": user.created_at,
            "conversation_count": conversations,
            "message_count": messages,
        }
        for user, conversations, messages in rows
    ]
    return items, total


def set_user_restriction(
    db: Session,
    *,
    actor_id: UUID,
    user_id: UUID,
    is_restricted: bool,
) -> User:
    if actor_id == user_id and is_restricted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot restrict your own admin account.",
        )

    active_admin_ids: list[UUID] = []
    if is_restricted:
        active_admin_ids = list(
            db.scalars(
                select(User.id)
                .where(
                    User.role == User.ROLE_ADMIN,
                    User.is_active.is_(True),
                    User.is_restricted.is_(False),
                )
                .order_by(User.id)
                .with_for_update()
            )
        )

    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if (
        is_restricted
        and user.role == User.ROLE_ADMIN
        and user.is_active
        and not user.is_restricted
    ):
        if len(active_admin_ids) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot restrict the last active admin account.",
            )

    user.is_restricted = is_restricted
    db.commit()
    db.refresh(user)
    return user


def get_dashboard_metrics(db: Session) -> dict[str, int]:
    total_users = db.scalar(select(func.count(User.id))) or 0
    active_users = db.scalar(
        select(func.count(User.id)).where(
            User.is_active.is_(True),
            User.is_restricted.is_(False),
        )
    ) or 0
    restricted_users = db.scalar(
        select(func.count(User.id)).where(User.is_restricted.is_(True))
    ) or 0
    total_conversations = db.scalar(
        select(func.count(Conversation.id))
    ) or 0
    total_messages = db.scalar(select(func.count(Message.id))) or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "restricted_users": restricted_users,
        "total_conversations": total_conversations,
        "total_messages": total_messages,
    }
