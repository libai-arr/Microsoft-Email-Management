from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.mailbox import Mailbox

router = APIRouter()


@router.get("/status")
async def get_token_status(
    ids: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    id_list = [UUID(i.strip()) for i in ids.split(",") if i.strip()]
    stmt = select(Mailbox.id, Mailbox.token_status, Mailbox.token_checked_at).where(
        Mailbox.id.in_(id_list)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {"id": str(r.id), "status": r.token_status, "checked_at": r.token_checked_at}
        for r in rows
    ]


@router.post("/check")
async def trigger_token_check(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    ids = [UUID(i) for i in body.get("ids", [])]
    stmt = update(Mailbox).where(Mailbox.id.in_(ids)).values(token_status="checking")
    result = await db.execute(stmt)
    await db.commit()
    return {"queued": result.rowcount}
