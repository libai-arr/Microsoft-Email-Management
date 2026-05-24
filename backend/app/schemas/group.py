from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class GroupResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    mailbox_count: int = 0

    model_config = {"from_attributes": True}
