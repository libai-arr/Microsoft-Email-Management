from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MailboxResponse(BaseModel):
    id: UUID
    email: str
    group_id: UUID | None
    group_name: str | None = None
    token_status: str
    channel: str
    token_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MailboxImportItem(BaseModel):
    email: str
    password: str
    client_id: str
    refresh_token: str


class MailboxImportRequest(BaseModel):
    items: list[MailboxImportItem]
    mode: str = "append"  # "append" | "overwrite"


class MailboxImportResponse(BaseModel):
    imported: int
    skipped: int
    total: int


class MailboxExportRequest(BaseModel):
    ids: list[UUID] | None = None
    format: str = "csv"  # "csv" | "xlsx"
    include_all: bool = False


class BatchCopyRequest(BaseModel):
    ids: list[UUID]
    type: str  # "email" | "password" | "combined"


class BatchCopyResponse(BaseModel):
    text: str


class BatchGroupRequest(BaseModel):
    ids: list[UUID]
    group_id: UUID | None
