from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: T | None = None


class APIErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: list[dict[str, str]] | None = None
