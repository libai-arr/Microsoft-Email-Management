from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.batch import router as batch_router
from app.api.deps import require_shared_access
from app.api.emails import router as emails_router
from app.api.groups import router as groups_router
from app.api.mailboxes import router as mailboxes_router
from app.api.tokens import router as tokens_router

app = FastAPI(title="多邮箱管理系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

protected = [Depends(require_shared_access)]

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(groups_router, prefix="/api/groups", tags=["groups"], dependencies=protected)
app.include_router(batch_router, prefix="/api/mailboxes", tags=["batch"], dependencies=protected)
app.include_router(emails_router, prefix="/api/mailboxes", tags=["emails"], dependencies=protected)
app.include_router(mailboxes_router, prefix="/api/mailboxes", tags=["mailboxes"], dependencies=protected)
app.include_router(tokens_router, prefix="/api/tokens", tags=["tokens"], dependencies=protected)
