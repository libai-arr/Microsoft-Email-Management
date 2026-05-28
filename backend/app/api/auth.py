import secrets

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from pydantic import BaseModel

from app.api.deps import (
    create_access_cookie_value,
    get_access_cookie_name,
    verify_access_cookie_value,
)
from app.config import settings

router = APIRouter()


class UnlockRequest(BaseModel):
    password: str


COOKIE_NAME = get_access_cookie_name()
COOKIE_MAX_AGE = settings.APP_SHARED_PASSWORD_SESSION_TTL
COOKIE_SECURE = False


def _set_access_cookie(response: Response) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_access_cookie_value(),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )


def _clear_access_cookie(response: Response) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )


@router.post("/unlock")
def unlock(body: UnlockRequest, response: Response):
    if not secrets.compare_digest(body.password, settings.APP_SHARED_PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="访问密码错误",
        )
    _set_access_cookie(response)
    return {"ok": True}


@router.get("/status")
def access_status(
    response: Response,
    access_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
):
    unlocked = verify_access_cookie_value(access_cookie)
    if not unlocked:
        _clear_access_cookie(response)
    return {"unlocked": unlocked}


@router.post("/logout")
def logout(response: Response):
    _clear_access_cookie(response)
    return {"ok": True}
