from typing import Generic, TypeVar, List, Optional, Any
from pydantic import BaseModel, Field

T = TypeVar("T")

class PaginationMeta(BaseModel):
    total_count: int
    current_page: int
    limit: int
    total_pages: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    meta: PaginationMeta

class ErrorDetails(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None

class ErrorResponse(BaseModel):
    error: ErrorDetails
