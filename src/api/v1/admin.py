from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies.auth import require_roles
from src.db.database import get_db
from src.models.user import User
from src.schemas.admin import (
    AdminDashboardMetrics,
    AdminUserListResponse,
    AdminUserSummary,
    UserRestrictionRequest,
    UserRestrictionResponse,
)
from src.services.admin_service import (
    get_dashboard_metrics,
    list_users,
    set_user_restriction,
)

router = APIRouter()


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    dependencies=[Depends(require_roles(User.ROLE_ADMIN))],
)
def get_users(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db),
) -> AdminUserListResponse:
    items, total = list_users(
        db,
        limit=limit,
        offset=offset,
        search=search,
    )
    return AdminUserListResponse(
        items=[AdminUserSummary.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/users/{user_id}/restriction",
    response_model=UserRestrictionResponse,
)
def update_user_restriction(
    user_id: UUID,
    payload: UserRestrictionRequest,
    current_user: User = Depends(require_roles(User.ROLE_ADMIN)),
    db: Session = Depends(get_db),
) -> UserRestrictionResponse:
    user = set_user_restriction(
        db,
        actor_id=current_user.id,
        user_id=user_id,
        is_restricted=payload.is_restricted,
    )
    return UserRestrictionResponse(
        user_id=user.id,
        is_restricted=user.is_restricted,
    )


@router.get(
    "/metrics",
    response_model=AdminDashboardMetrics,
    dependencies=[Depends(require_roles(User.ROLE_ADMIN))],
)
def get_admin_metrics(
    db: Session = Depends(get_db),
) -> AdminDashboardMetrics:
    return AdminDashboardMetrics(**get_dashboard_metrics(db))
