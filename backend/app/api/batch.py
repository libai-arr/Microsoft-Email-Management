from fastapi import APIRouter, Depends
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_crypto, get_client_ip
from app.models.mailbox import Mailbox
from app.schemas.common import BatchIdsRequest
from app.schemas.mailbox import BatchCopyRequest, BatchCopyResponse, BatchGroupRequest
from app.services.audit import log_audit
from app.services.crypto import CryptoService

router = APIRouter()


@router.delete("/batch")
async def batch_delete(
    body: BatchIdsRequest,
    db: AsyncSession = Depends(get_db),
    ip: str = Depends(get_client_ip),
):
    stmt = delete(Mailbox).where(Mailbox.id.in_(body.ids))
    result = await db.execute(stmt)
    await log_audit(
        db, "batch_delete", result.rowcount,
        detail={"ids": [str(i) for i in body.ids]},
        ip_address=ip,
    )
    await db.commit()
    return {"deleted": result.rowcount}


@router.patch("/batch/group")
async def batch_set_group(
    body: BatchGroupRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = update(Mailbox).where(Mailbox.id.in_(body.ids)).values(group_id=body.group_id)
    result = await db.execute(stmt)
    await db.commit()
    return {"updated": result.rowcount}


@router.post("/batch/copy", response_model=BatchCopyResponse)
async def batch_copy(
    body: BatchCopyRequest,
    db: AsyncSession = Depends(get_db),
    crypto: CryptoService = Depends(get_crypto),
    ip: str = Depends(get_client_ip),
):
    stmt = select(Mailbox).where(Mailbox.id.in_(body.ids)).order_by(Mailbox.created_at)
    rows = (await db.execute(stmt)).scalars().all()

    lines: list[str] = []
    for m in rows:
        if body.type == "email":
            lines.append(m.email)
        elif body.type == "password":
            lines.append(crypto.decrypt(m.password_encrypted))
        elif body.type == "combined":
            pwd = crypto.decrypt(m.password_encrypted)
            lines.append(f"{m.email}----{pwd}")

    await log_audit(
        db, "batch_copy", len(rows),
        detail={"type": body.type, "ids": [str(i) for i in body.ids]},
        ip_address=ip,
    )
    await db.commit()

    return BatchCopyResponse(text="\n".join(lines))
