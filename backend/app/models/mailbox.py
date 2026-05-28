import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, LargeBinary, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Mailbox(Base):
    __tablename__ = "mailboxes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    client_id_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    token_status: Mapped[str] = mapped_column(String(20), default="normal")
    channel: Mapped[str] = mapped_column(String(20), default="O2")
    token_checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    group: Mapped[Optional["Group"]] = relationship(back_populates="mailboxes")

    __table_args__ = (
        Index("ix_mailboxes_token_status", "token_status"),
    )
