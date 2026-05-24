import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.crypto import CryptoService
from app.services.graph_client import GraphClient

logger = logging.getLogger(__name__)


async def check_tokens(
    session_factory: async_sessionmaker[AsyncSession],
    crypto: CryptoService,
    redis,
    interval: int = 300,
    concurrency: int = 10,
):
    from app.models.mailbox import Mailbox

    async with session_factory() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=interval)
        stale_stmt = (
            select(Mailbox)
            .where(
                (Mailbox.token_checked_at < cutoff) | (Mailbox.token_checked_at.is_(None))
            )
        )
        rows = (await db.execute(stale_stmt)).scalars().all()

        if not rows:
            return

        ids = [m.id for m in rows]
        await db.execute(
            update(Mailbox).where(Mailbox.id.in_(ids)).values(token_status="checking")
        )
        await db.commit()

    graph = GraphClient(redis)
    semaphore = asyncio.Semaphore(concurrency)

    async def check_one(mailbox_id, client_id_enc, refresh_token_enc):
        async with semaphore:
            try:
                client_id = crypto.decrypt(client_id_enc)
                refresh_token = crypto.decrypt(refresh_token_enc)
                valid = await graph.validate_token(client_id, refresh_token)
                new_status = "normal" if valid else "expired"
            except Exception:
                new_status = "expired"
                logger.exception(f"Token check failed for {mailbox_id}")

            async with session_factory() as db:
                await db.execute(
                    update(Mailbox)
                    .where(Mailbox.id == mailbox_id)
                    .values(
                        token_status=new_status,
                        token_checked_at=datetime.now(timezone.utc),
                    )
                )
                await db.commit()

    tasks = [
        check_one(m.id, m.client_id_encrypted, m.refresh_token_encrypted)
        for m in rows
    ]
    await asyncio.gather(*tasks)
