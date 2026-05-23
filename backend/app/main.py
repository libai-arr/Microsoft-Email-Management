from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.groups import router as groups_router

app = FastAPI(title="多邮箱管理系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(groups_router, prefix="/api/groups", tags=["groups"])
