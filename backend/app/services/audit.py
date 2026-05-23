from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_audit(
    db: AsyncSession,
    action: str,
    target_count: int,
    detail: dict | None = None,
    ip_address: str | None = None,
) -> None:
    entry = AuditLog(
        action=action,
        target_count=target_count,
        detail=detail or {},
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
