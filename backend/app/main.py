from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.batch import router as batch_router
from app.api.groups import router as groups_router
from app.api.mailboxes import router as mailboxes_router

app = FastAPI(title="多邮箱管理系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(groups_router, prefix="/api/groups", tags=["groups"])
app.include_router(batch_router, prefix="/api/mailboxes", tags=["batch"])
app.include_router(mailboxes_router, prefix="/api/mailboxes", tags=["mailboxes"])
