"""Shared response schemas."""
from typing import Generic, TypeVar, Any
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseSchema, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class ErrorResponse(BaseSchema):
    error: str
    detail: str | None = None
    code: str | None = None


class SuccessResponse(BaseSchema):
    message: str
    data: Any = None
