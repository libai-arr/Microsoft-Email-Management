from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_crypto, get_redis
from app.models.mailbox import Mailbox
from app.schemas.email import EmailSummary, EmailDetail
from app.services.crypto import CryptoService
from app.services.graph_client import GraphClient
from app.services.mail_sanitizer import sanitize_html

router = APIRouter()


async def _get_mailbox_creds(
    mailbox_id: UUID, db: AsyncSession, crypto: CryptoService
) -> tuple[Mailbox, str, str]:
    mailbox = await db.get(Mailbox, mailbox_id)
    if not mailbox:
        raise HTTPException(status_code=404, detail="邮箱不存在")
    client_id = crypto.decrypt(mailbox.client_id_encrypted)
    refresh_token = crypto.decrypt(mailbox.refresh_token_encrypted)
    return mailbox, client_id, refresh_token


@router.get("/{mailbox_id}/emails", response_model=list[EmailSummary])
async def list_emails(
    mailbox_id: UUID,
    folder: str = Query("inbox"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    crypto: CryptoService = Depends(get_crypto),
    redis=Depends(get_redis),
):
    mailbox, client_id, refresh_token = await _get_mailbox_creds(mailbox_id, db, crypto)
    graph = GraphClient(redis)

    try:
        data = await graph.list_emails(
            client_id, refresh_token, str(mailbox_id),
            folder=folder, page=page, page_size=page_size, search=search,
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Graph API 调用失败")

    emails = []
    for msg in data.get("value", []):
        sender = msg.get("from", {}).get("emailAddress", {})
        emails.append(EmailSummary(
            id=msg["id"],
            subject=msg.get("subject", ""),
            sender_name=sender.get("name", ""),
            sender_email=sender.get("address", ""),
            preview=msg.get("bodyPreview", ""),
            received_at=msg["receivedDateTime"],
            is_read=msg.get("isRead", False),
        ))

    return emails


@router.get("/{mailbox_id}/emails/{message_id}", response_model=EmailDetail)
async def get_email_detail(
    mailbox_id: UUID,
    message_id: str,
    db: AsyncSession = Depends(get_db),
    crypto: CryptoService = Depends(get_crypto),
    redis=Depends(get_redis),
):
    mailbox, client_id, refresh_token = await _get_mailbox_creds(mailbox_id, db, crypto)
    graph = GraphClient(redis)

    try:
        data = await graph.get_email_body(
            client_id, refresh_token, str(mailbox_id), message_id
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Graph API 调用失败")

    sender = data.get("from", {}).get("emailAddress", {})
    body_html = data.get("body", {}).get("content", "")

    return EmailDetail(
        id=data["id"],
        subject=data.get("subject", ""),
        sender_name=sender.get("name", ""),
        sender_email=sender.get("address", ""),
        received_at=data["receivedDateTime"],
        body_html=sanitize_html(body_html),
    )
