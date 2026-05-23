from uuid import UUID

from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 10


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list


class BatchIdsRequest(BaseModel):
    ids: list[UUID]
