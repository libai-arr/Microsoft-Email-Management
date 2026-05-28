import base64
import hashlib
import hmac
import secrets
import time
from typing import AsyncGenerator

from fastapi import Cookie, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.services.crypto import CryptoService

_crypto: CryptoService | None = None
_redis: Redis | None = None
_ACCESS_COOKIE_NAME = "app_access"


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


def get_crypto() -> CryptoService:
    global _crypto
    if _crypto is None:
        _crypto = CryptoService(settings.ENCRYPTION_KEY)
    return _crypto


async def get_redis() -> Redis | None:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    try:
        await _redis.ping()
        return _redis
    except Exception:
        return None


def _sign_access_payload(payload: str) -> str:
    key = base64.b64decode(settings.ENCRYPTION_KEY)
    signature = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")


def create_access_cookie_value() -> str:
    expires_at = int(time.time()) + settings.APP_SHARED_PASSWORD_SESSION_TTL
    payload = str(expires_at)
    signature = _sign_access_payload(payload)
    return f"{payload}.{signature}"


def verify_access_cookie_value(value: str | None) -> bool:
    if not value or "." not in value:
        return False
    payload, signature = value.rsplit(".", 1)
    expected = _sign_access_payload(payload)
    if not secrets.compare_digest(signature, expected):
        return False
    try:
        expires_at = int(payload)
    except ValueError:
        return False
    return expires_at > int(time.time())


def get_access_cookie_name() -> str:
    return _ACCESS_COOKIE_NAME


def require_shared_access(access_cookie: str | None = Cookie(default=None, alias=_ACCESS_COOKIE_NAME)) -> None:
    if not verify_access_cookie_value(access_cookie):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先输入访问密码",
        )


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
