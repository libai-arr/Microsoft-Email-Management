from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_crypto, get_client_ip
from app.models.mailbox import Mailbox
from app.models.group import Group
from app.schemas.mailbox import (
    MailboxResponse,
    MailboxImportRequest,
    MailboxImportResponse,
    MailboxExportRequest,
)
from app.services.audit import log_audit
from app.services.crypto import CryptoService

router = APIRouter()


@router.get("")
async def list_mailboxes(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    search: str | None = None,
    group_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Mailbox).outerjoin(Group, Mailbox.group_id == Group.id)
    count_stmt = select(func.count(Mailbox.id))

    if search:
        stmt = stmt.where(Mailbox.email.ilike(f"%{search}%"))
        count_stmt = count_stmt.where(Mailbox.email.ilike(f"%{search}%"))
    if group_id:
        stmt = stmt.where(Mailbox.group_id == group_id)
        count_stmt = count_stmt.where(Mailbox.group_id == group_id)

    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(Mailbox.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    items = []
    for m in rows:
        group_name = None
        if m.group_id:
            g = await db.get(Group, m.group_id)
            group_name = g.name if g else None
        items.append(
            MailboxResponse(
                id=m.id,
                email=m.email,
                group_id=m.group_id,
                group_name=group_name,
                token_status=m.token_status,
                channel=m.channel,
                token_checked_at=m.token_checked_at,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
        )

    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.post("/import", response_model=MailboxImportResponse)
async def import_mailboxes(
    body: MailboxImportRequest,
    db: AsyncSession = Depends(get_db),
    crypto: CryptoService = Depends(get_crypto),
    ip: str = Depends(get_client_ip),
):
    if body.mode == "overwrite":
        await db.execute(delete(Mailbox))
        await log_audit(db, "import_overwrite", len(body.items), ip_address=ip)

    imported = 0
    skipped = 0

    for item in body.items:
        existing = await db.execute(select(Mailbox).where(Mailbox.email == item.email))
        if existing.scalar_one_or_none():
            skipped += 1
            continue

        mailbox = Mailbox(
            email=item.email,
            password_encrypted=crypto.encrypt(item.password),
            client_id_encrypted=crypto.encrypt(item.client_id),
            refresh_token_encrypted=crypto.encrypt(item.refresh_token),
        )
        db.add(mailbox)
        imported += 1

    await db.commit()
    return MailboxImportResponse(imported=imported, skipped=skipped, total=len(body.items))


@router.post("/export")
async def export_mailboxes(
    body: MailboxExportRequest,
    db: AsyncSession = Depends(get_db),
    crypto: CryptoService = Depends(get_crypto),
    ip: str = Depends(get_client_ip),
):
    stmt = select(Mailbox)
    if not body.include_all and body.ids:
        stmt = stmt.where(Mailbox.id.in_(body.ids))
    stmt = stmt.order_by(Mailbox.created_at)

    rows = (await db.execute(stmt)).scalars().all()

    await log_audit(
        db, "batch_export", len(rows),
        detail={"format": "txt"},
        ip_address=ip,
    )
    await db.commit()

    lines = []
    for m in rows:
        email = m.email
        password = crypto.decrypt(m.password_encrypted)
        client_id = crypto.decrypt(m.client_id_encrypted)
        refresh_token = crypto.decrypt(m.refresh_token_encrypted)
        lines.append(f"{email}----{password}----{client_id}----{refresh_token}")

    content = "\n".join(lines)
    return StreamingResponse(
        iter([content]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=mailboxes.txt"},
    )


@router.delete("/{mailbox_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mailbox(mailbox_id: UUID, db: AsyncSession = Depends(get_db)):
    mailbox = await db.get(Mailbox, mailbox_id)
    if not mailbox:
        raise HTTPException(status_code=404, detail="邮箱不存在")
    await db.delete(mailbox)
    await db.commit()


