from datetime import datetime

from pydantic import BaseModel


class EmailSummary(BaseModel):
    id: str
    subject: str
    sender_name: str
    sender_email: str
    preview: str
    received_at: datetime
    is_read: bool
    folder: str | None = None


class EmailDetail(BaseModel):
    id: str
    subject: str
    sender_name: str
    sender_email: str
    received_at: datetime
    body_html: str
