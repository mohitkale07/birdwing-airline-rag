import logging
from collections.abc import Iterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.dependencies.auth import get_optional_current_user
from src.db.database import get_db
from src.generation.answer_question import PreparedAnswer, prepare_answer_prompt
from src.generation.llm_client import stream_answer
from src.models.user import User
from src.schemas.chat import (
    ChatCompletedEvent,
    ChatErrorEvent,
    ChatRequest,
    ChatSource,
    ChatStartedEvent,
    ChatTokenEvent,
    ConversationActionResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummary,
    ConversationUpdateRequest,
    StoredChatMessage,
)
from src.services.chat_service import (
    SavedUserMessage,
    save_assistant_message,
    save_user_message,
)
from src.services.conversation_service import (
    delete_conversation,
    get_conversation,
    list_conversations,
    update_conversation,
)

router = APIRouter()
logger = logging.getLogger(__name__)
NO_CONTEXT_ANSWER = "The information is not available in the provided policy context."


@router.get("/conversations", response_model=ConversationListResponse)
def get_my_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_archived: bool = False,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> ConversationListResponse:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )

    items, total = list_conversations(
        db,
        current_user.id,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
    )
    return ConversationListResponse(
        items=[ConversationSummary.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_my_conversation(
    conversation_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )

    conversation, messages, total = get_conversation(
        db,
        current_user.id,
        conversation_id,
        limit=limit,
        offset=offset,
    )
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        is_archived=conversation.is_archived,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            StoredChatMessage(
                id=message.id,
                role=message.role,
                content=message.content,
                sources=(
                    [
                        ChatSource.model_validate(source)
                        for source in message.sources
                    ]
                    if message.sources is not None
                    else None
                ),
                created_at=message.created_at,
            )
            for message in messages
        ],
        total_messages=total,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationActionResponse,
)
def patch_my_conversation(
    conversation_id: UUID,
    payload: ConversationUpdateRequest,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> ConversationActionResponse:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )

    conversation = update_conversation(
        db,
        current_user.id,
        conversation_id,
        payload,
    )
    return ConversationActionResponse(
        id=conversation.id,
        title=conversation.title,
        is_archived=conversation.is_archived,
        updated_at=conversation.updated_at,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_my_conversation(
    conversation_id: UUID,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> Response:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )

    delete_conversation(db, current_user.id, conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _sse(event: BaseModel) -> str:
    return f"data: {event.model_dump_json()}\n\n"


def _start_event(saved_message: SavedUserMessage | None) -> str:
    return _sse(
        ChatStartedEvent(
            conversation_id=(
                saved_message.conversation_id if saved_message else None
            ),
            user_message_id=saved_message.message_id if saved_message else None,
        )
    )


def _error_stream(
    message: str,
    saved_message: SavedUserMessage | None,
) -> Iterator[str]:
    yield _start_event(saved_message)
    yield _sse(ChatErrorEvent(message=message))


def _answer_stream(
    prepared: PreparedAnswer,
    saved_message: SavedUserMessage | None,
    retrieval_role: str,
) -> Iterator[str]:
    yield _start_event(saved_message)

    answer_parts: list[str] = []
    try:
        if prepared.prompt is None:
            answer_parts.append(NO_CONTEXT_ANSWER)
            yield _sse(ChatTokenEvent(content=NO_CONTEXT_ANSWER))
        else:
            for token in stream_answer(prepared.prompt):
                answer_parts.append(token)
                yield _sse(ChatTokenEvent(content=token))
        if not "".join(answer_parts).strip():
            raise RuntimeError("The LLM returned an empty answer.")
    except Exception:
        logger.exception("Chat answer generation failed")
        yield _sse(ChatErrorEvent(message="Answer generation failed."))
        return

    assistant_message_id = None
    if saved_message is not None:
        try:
            assistant_message_id = save_assistant_message(
                conversation_id=saved_message.conversation_id,
                content="".join(answer_parts),
                sources=prepared.sources,
                retrieval_role=retrieval_role,
            )
        except Exception:
            logger.exception("Failed to save the generated chat response")
            yield _sse(ChatErrorEvent(message="Failed to save the chat response."))
            return

    yield _sse(
        ChatCompletedEvent(
            conversation_id=(
                saved_message.conversation_id if saved_message else None
            ),
            user_message_id=saved_message.message_id if saved_message else None,
            assistant_message_id=assistant_message_id,
            sources=[
                ChatSource.model_validate(source)
                for source in prepared.sources
            ],
        )
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User | None = Depends(get_optional_current_user),
) -> StreamingResponse:
    if current_user is None:
        if request.conversation_id is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Log in to continue a saved conversation.",
            )
        retrieval_role = "public"
        saved_message = None
        history: list[tuple[str, str]] = []
    else:
        retrieval_role = (
            "hr" if current_user.role == User.ROLE_ADMIN else "employee"
        )
        saved_message = await run_in_threadpool(
            save_user_message,
            current_user.id,
            request,
        )
        history = saved_message.history

    try:
        prepared = await run_in_threadpool(
            prepare_answer_prompt,
            request.text,
            retrieval_role,
            history,
        )
    except ValueError as error:
        return StreamingResponse(
            _error_stream(str(error), saved_message),
            media_type="text/event-stream",
        )
    except Exception:
        logger.exception("Chat answer preparation failed")
        return StreamingResponse(
            _error_stream("Unable to prepare an answer.", saved_message),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        _answer_stream(prepared, saved_message, retrieval_role),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
