from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminUserSummary(BaseModel):
    id: UUID
    name: str | None
    email: str
    role: str
    is_verified: bool
    is_active: bool
    is_restricted: bool
    created_at: datetime
    conversation_count: int
    message_count: int


class AdminUserListResponse(BaseModel):
    items: list[AdminUserSummary]
    total: int
    limit: int
    offset: int


class UserRestrictionRequest(BaseModel):
    is_restricted: bool


class UserRestrictionResponse(BaseModel):
    user_id: UUID
    is_restricted: bool


class AdminDashboardMetrics(BaseModel):
    total_users: int
    active_users: int
    restricted_users: int
    total_conversations: int
    total_messages: int
