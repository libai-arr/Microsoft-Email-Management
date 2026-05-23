# Multi-Mailbox Management System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack internal operations tool for centrally managing multiple Outlook email accounts — importing credentials, monitoring token health, batch operations, and online email viewing.

**Architecture:** Docker Compose with 5 services. React + Ant Design frontend served by Nginx, FastAPI backend with SQLAlchemy ORM, ARQ background worker for token health checks, PostgreSQL for encrypted credential storage, Redis for task queue and token caching.

**Tech Stack:** React 18, TypeScript, Ant Design 5, Vite, Python 3.12, FastAPI, SQLAlchemy, Alembic, ARQ, PostgreSQL 16, Redis 7, Docker Compose, Microsoft Graph API (MSAL + httpx)

**Design Spec:** `docs/superpowers/specs/2026-05-23-multi-mailbox-management-design.md`

---

## File Structure

### Backend (`backend/`)

| File | Responsibility |
|------|---------------|
| `app/main.py` | FastAPI application factory, CORS, router mounting |
| `app/config.py` | Pydantic Settings: env vars (ENCRYPTION_KEY, DATABASE_URL, REDIS_URL, etc.) |
| `app/database.py` | SQLAlchemy async engine, session factory, Base |
| `app/api/__init__.py` | Router aggregation |
| `app/api/groups.py` | Groups CRUD endpoints |
| `app/api/mailboxes.py` | Mailbox list, import, export, single delete |
| `app/api/batch.py` | Batch operations: delete, set group, copy |
| `app/api/emails.py` | Email list + body proxy via Graph API |
| `app/api/tokens.py` | Token status polling + manual check trigger |
| `app/api/deps.py` | Shared dependencies (get_db, get_redis, get_crypto) |
| `app/models/__init__.py` | Re-exports all models |
| `app/models/group.py` | Group SQLAlchemy model |
| `app/models/mailbox.py` | Mailbox SQLAlchemy model |
| `app/models/audit_log.py` | AuditLog SQLAlchemy model |
| `app/schemas/group.py` | Group Pydantic schemas |
| `app/schemas/mailbox.py` | Mailbox Pydantic schemas |
| `app/schemas/email.py` | Email response schemas |
| `app/schemas/common.py` | Pagination, batch request/response schemas |
| `app/services/crypto.py` | AES-256-GCM encrypt/decrypt |
| `app/services/import_parser.py` | Parse import text (format A + B), validate 4 fields |
| `app/services/mail_sanitizer.py` | HTML sanitization for email bodies |
| `app/services/graph_client.py` | Microsoft Graph API: refresh token, list emails, get email body |
| `app/services/audit.py` | Audit log writer |
| `app/worker/tasks.py` | ARQ worker config + cron task registration |
| `app/worker/token_checker.py` | Token health check logic |
| `Dockerfile` | Multi-stage: install deps, copy app |
| `requirements.txt` | Python dependencies |
| `alembic.ini` | Alembic config pointing to app/database.py |
| `migrations/env.py` | Alembic env with async engine |
| `migrations/versions/001_initial.py` | Initial migration: groups, mailboxes, audit_logs |

### Backend Tests (`backend/tests/`)

| File | What it tests |
|------|--------------|
| `conftest.py` | Test fixtures: async DB session, test client, crypto instance |
| `test_crypto.py` | Encrypt/decrypt round-trip, wrong key rejection |
| `test_import_parser.py` | Format A, format B, mixed, validation errors |
| `test_mail_sanitizer.py` | Script removal, iframe removal, safe HTML pass-through |
| `test_api_groups.py` | Groups CRUD + mailbox count |
| `test_api_mailboxes.py` | List, import (append/overwrite/dedup), export, single delete |
| `test_api_batch.py` | Batch delete, batch set group, batch copy |
| `test_api_emails.py` | Email list + body (mocked Graph API) |
| `test_api_tokens.py` | Token status, manual check trigger |
| `test_token_checker.py` | Worker health check flow (mocked MSAL) |

### Frontend (`frontend/src/`)

| File | Responsibility |
|------|---------------|
| `main.tsx` | React root, Ant Design ConfigProvider (zh-CN locale) |
| `App.tsx` | Layout shell: header + page content |
| `pages/MailboxList.tsx` | Main list page: toolbar + ProTable + pagination + modals |
| `components/ImportModal.tsx` | Import modal: text tab + file upload tab + validation |
| `components/EmailViewer.tsx` | Email viewer modal: left list + right body |
| `components/BatchCopyMenu.tsx` | Dropdown menu for batch copy operations |
| `components/TokenStatus.tsx` | Status dot component (green/yellow/red) |
| `components/GroupTag.tsx` | Colored tag component for group display |
| `components/GroupSelect.tsx` | Group selector modal for batch assignment |
| `hooks/useMailboxes.ts` | Mailbox list data + pagination + search + filter |
| `hooks/useTokenStatus.ts` | 30s polling for token status updates |
| `hooks/useEmails.ts` | Email list + body fetching for viewer |
| `services/api.ts` | Axios instance with /api base, typed request functions |
| `utils/importParser.ts` | Client-side import text validation |
| `utils/clipboard.ts` | Clipboard write helper |
| `types/index.ts` | Shared TypeScript types (Mailbox, Group, Email, etc.) |

### Infrastructure (root)

| File | Responsibility |
|------|---------------|
| `docker-compose.yml` | 5 services: frontend, api, worker, postgres, redis |
| `.env.example` | Template with all env vars |
| `.gitignore` | Python, Node, Docker, IDE ignores |
| `frontend/Dockerfile` | Multi-stage: npm build → nginx:alpine |
| `frontend/nginx.conf` | Static files + /api proxy to api:8000 |
| `frontend/vite.config.ts` | Dev server proxy + build config |
| `frontend/package.json` | Dependencies |
| `frontend/tsconfig.json` | TypeScript config |

---

## Task 1: Project Scaffolding & Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `frontend/package.json`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
dist/

# Node
node_modules/
frontend/dist/

# Environment
.env

# IDE
.idea/
.vscode/
*.swp

# Docker
.superpowers/

# OS
.DS_Store
```

- [ ] **Step 2: Create `.env.example`**

```env
# Required — generate with: python3 -c "import secrets; import base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
ENCRYPTION_KEY=

# Database
DATABASE_URL=postgresql+asyncpg://mailbox:mailbox_pass@postgres:5432/mailbox_db
POSTGRES_USER=mailbox
POSTGRES_PASSWORD=mailbox_pass
POSTGRES_DB=mailbox_db

# Redis
REDIS_URL=redis://redis:6379/0

# Token health check
TOKEN_CHECK_INTERVAL=300
TOKEN_CHECK_CONCURRENCY=10
ACCESS_TOKEN_CACHE_TTL=3000
```

- [ ] **Step 3: Create `backend/requirements.txt`**

```txt
fastapi==0.115.0
uvicorn[standard]==0.34.0
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.0
pydantic-settings==2.6.0
cryptography==44.0.0
httpx==0.28.0
msal==1.31.0
bleach==6.2.0
arq==0.26.1
redis==5.2.0
openpyxl==3.1.5
python-multipart==0.0.17

# Testing
pytest==8.3.0
pytest-asyncio==0.24.0
httpx==0.28.0
aiosqlite==0.20.0
```

- [ ] **Step 4: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 5: Create `frontend/package.json`**

```json
{
  "name": "multi-mailbox-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "antd": "^5.22.0",
    "@ant-design/icons": "^5.5.0",
    "axios": "^1.7.0",
    "dayjs": "^1.11.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.6.0",
    "vite": "^6.0.0"
  }
}
```

- [ ] **Step 6: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"]
}
```

- [ ] **Step 7: Create `frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 8: Create `frontend/nginx.conf`**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 9: Create `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 10: Create `docker-compose.yml`**

```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - api

  api:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  worker:
    build: ./backend
    command: ["python", "-m", "arq", "app.worker.tasks.WorkerSettings"]
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-mailbox}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-mailbox_pass}
      POSTGRES_DB: ${POSTGRES_DB:-mailbox_db}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-mailbox}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

- [ ] **Step 11: Commit**

```bash
git add .gitignore .env.example docker-compose.yml backend/requirements.txt backend/Dockerfile frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/nginx.conf frontend/Dockerfile
git commit -m "feat: add project scaffolding and Docker Compose config"
```

---

## Task 2: Backend Config, Database & Models

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/group.py`
- Create: `backend/app/models/mailbox.py`
- Create: `backend/app/models/audit_log.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/migrations/versions/001_initial.py`

- [ ] **Step 1: Create `backend/app/__init__.py`**

Empty file.

- [ ] **Step 2: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://mailbox:mailbox_pass@localhost:5432/mailbox_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    ENCRYPTION_KEY: str = ""
    TOKEN_CHECK_INTERVAL: int = 300
    TOKEN_CHECK_CONCURRENCY: int = 10
    ACCESS_TOKEN_CACHE_TTL: int = 3000

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 3: Create `backend/app/database.py`**

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

- [ ] **Step 4: Create `backend/app/models/group.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    mailboxes: Mapped[list["Mailbox"]] = relationship(back_populates="group")
```

- [ ] **Step 5: Create `backend/app/models/mailbox.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, LargeBinary, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Mailbox(Base):
    __tablename__ = "mailboxes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    client_id_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    token_status: Mapped[str] = mapped_column(String(20), default="normal")
    channel: Mapped[str] = mapped_column(String(20), default="O2")
    token_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    group: Mapped["Group | None"] = relationship(back_populates="mailboxes")

    __table_args__ = (
        Index("ix_mailboxes_token_status", "token_status"),
    )
```

- [ ] **Step 6: Create `backend/app/models/audit_log.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, BigInteger, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 7: Create `backend/app/models/__init__.py`**

```python
from app.models.group import Group
from app.models.mailbox import Mailbox
from app.models.audit_log import AuditLog

__all__ = ["Group", "Mailbox", "AuditLog"]
```

- [ ] **Step 8: Create Alembic config**

Create `backend/alembic.ini`:
```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql+asyncpg://mailbox:mailbox_pass@localhost:5432/mailbox_db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Create `backend/migrations/env.py`:
```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.database import Base
from app.models import Group, Mailbox, AuditLog  # noqa: F401 — register models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=settings.DATABASE_URL, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.DATABASE_URL)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

Create `backend/migrations/script.py.mako`:
```mako
"""${message}

Revision ID: ${up_revision}
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

Create `backend/migrations/versions/__init__.py` (empty).

- [ ] **Step 9: Create initial migration `backend/migrations/versions/001_initial.py`**

```python
"""Initial tables: groups, mailboxes, audit_logs

Revision ID: 001
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import JSON

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "mailboxes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("client_id_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("group_id", sa.Uuid(), sa.ForeignKey("groups.id", ondelete="SET NULL"), nullable=True),
        sa.Column("token_status", sa.String(20), server_default="normal"),
        sa.Column("channel", sa.String(20), server_default="O2"),
        sa.Column("token_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_mailboxes_email", "mailboxes", ["email"])
    op.create_index("ix_mailboxes_token_status", "mailboxes", ["token_status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_count", sa.Integer(), nullable=False),
        sa.Column("detail", sa.JSON(), server_default="{}"),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("mailboxes")
    op.drop_table("groups")
```

- [ ] **Step 10: Commit**

```bash
git add backend/
git commit -m "feat: add backend config, database models, and initial migration"
```

---

## Task 3: Encryption Service (TDD)

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/crypto.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_crypto.py`

- [ ] **Step 1: Create test fixtures `backend/tests/conftest.py`**

```python
import base64
import os

import pytest


@pytest.fixture
def encryption_key() -> str:
    return base64.b64encode(os.urandom(32)).decode()
```

Create `backend/tests/__init__.py` and `backend/app/services/__init__.py` as empty files.

- [ ] **Step 2: Write the failing tests `backend/tests/test_crypto.py`**

```python
import base64
import os

import pytest

from app.services.crypto import CryptoService


@pytest.fixture
def crypto(encryption_key: str) -> CryptoService:
    return CryptoService(encryption_key)


class TestCryptoService:
    def test_encrypt_decrypt_roundtrip(self, crypto: CryptoService):
        plaintext = "my-secret-password"
        encrypted = crypto.encrypt(plaintext)
        assert encrypted != plaintext.encode()
        decrypted = crypto.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_produces_different_ciphertext_each_time(self, crypto: CryptoService):
        plaintext = "same-input"
        enc1 = crypto.encrypt(plaintext)
        enc2 = crypto.encrypt(plaintext)
        assert enc1 != enc2

    def test_decrypt_with_wrong_key_raises(self, crypto: CryptoService):
        encrypted = crypto.encrypt("secret")
        wrong_key = base64.b64encode(os.urandom(32)).decode()
        wrong_crypto = CryptoService(wrong_key)
        with pytest.raises(Exception):
            wrong_crypto.decrypt(encrypted)

    def test_encrypt_empty_string(self, crypto: CryptoService):
        encrypted = crypto.encrypt("")
        assert crypto.decrypt(encrypted) == ""

    def test_encrypt_unicode(self, crypto: CryptoService):
        plaintext = "密码123"
        encrypted = crypto.encrypt(plaintext)
        assert crypto.decrypt(encrypted) == plaintext
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_crypto.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.crypto'`

- [ ] **Step 4: Implement `backend/app/services/crypto.py`**

```python
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoService:
    NONCE_SIZE = 12

    def __init__(self, key_b64: str):
        key_bytes = base64.b64decode(key_b64)
        if len(key_bytes) != 32:
            raise ValueError("ENCRYPTION_KEY must be 32 bytes (base64-encoded)")
        self._aesgcm = AESGCM(key_bytes)

    def encrypt(self, plaintext: str) -> bytes:
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return nonce + ciphertext

    def decrypt(self, data: bytes) -> str:
        nonce = data[: self.NONCE_SIZE]
        ciphertext = data[self.NONCE_SIZE :]
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_crypto.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ backend/tests/
git commit -m "feat: add AES-256-GCM encryption service with tests"
```

---

## Task 4: Import Parser Service (TDD)

**Files:**
- Create: `backend/app/services/import_parser.py`
- Create: `backend/tests/test_import_parser.py`

- [ ] **Step 1: Write the failing tests `backend/tests/test_import_parser.py`**

```python
import pytest

from app.services.import_parser import parse_import_text, ImportError as ParseImportError


class TestParseImportText:
    def test_format_b_four_dashes(self):
        text = "alice@outlook.com----Pass123----abc-def----rt_token_abc"
        result = parse_import_text(text)
        assert len(result.valid) == 1
        assert result.valid[0].email == "alice@outlook.com"
        assert result.valid[0].password == "Pass123"
        assert result.valid[0].client_id == "abc-def"
        assert result.valid[0].refresh_token == "rt_token_abc"
        assert len(result.errors) == 0

    def test_format_a_space_separated(self):
        text = "bob@outlook.com SecurePass jkl-mno rt_token_def"
        result = parse_import_text(text)
        assert len(result.valid) == 1
        assert result.valid[0].email == "bob@outlook.com"

    def test_format_a_tab_separated(self):
        text = "bob@outlook.com\tSecurePass\tjkl-mno\trt_token_def"
        result = parse_import_text(text)
        assert len(result.valid) == 1

    def test_mixed_formats(self):
        text = "a@outlook.com----P1----C1----T1\nb@outlook.com P2 C2 T2"
        result = parse_import_text(text)
        assert len(result.valid) == 2
        assert len(result.errors) == 0

    def test_missing_fields_error(self):
        text = "bad@outlook.com onlypassword"
        result = parse_import_text(text)
        assert len(result.valid) == 0
        assert len(result.errors) == 1
        assert result.errors[0].line_number == 1

    def test_empty_lines_skipped(self):
        text = "\nalice@outlook.com----P----C----T\n\n"
        result = parse_import_text(text)
        assert len(result.valid) == 1
        assert len(result.errors) == 0

    def test_multiple_errors_report_all_lines(self):
        text = "good@outlook.com----P----C----T\nbad1\nbad2 only"
        result = parse_import_text(text)
        assert len(result.valid) == 1
        assert len(result.errors) == 2
        assert result.errors[0].line_number == 2
        assert result.errors[1].line_number == 3

    def test_whitespace_trimmed(self):
        text = "  alice@outlook.com----Pass----CID----Token  "
        result = parse_import_text(text)
        assert result.valid[0].email == "alice@outlook.com"
        assert result.valid[0].refresh_token == "Token"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_import_parser.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `backend/app/services/import_parser.py`**

```python
from dataclasses import dataclass


@dataclass
class ParsedMailbox:
    email: str
    password: str
    client_id: str
    refresh_token: str


@dataclass
class ImportError:
    line_number: int
    content: str
    reason: str


@dataclass
class ParseResult:
    valid: list[ParsedMailbox]
    errors: list[ImportError]


def _parse_line(line: str) -> ParsedMailbox | None:
    if "----" in line:
        parts = [p.strip() for p in line.split("----")]
    else:
        parts = line.split()

    if len(parts) != 4:
        return None

    return ParsedMailbox(
        email=parts[0].strip(),
        password=parts[1].strip(),
        client_id=parts[2].strip(),
        refresh_token=parts[3].strip(),
    )


def parse_import_text(text: str) -> ParseResult:
    valid: list[ParsedMailbox] = []
    errors: list[ImportError] = []

    for line_num, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        parsed = _parse_line(line)
        if parsed is None:
            field_count = len(line.split("----")) if "----" in line else len(line.split())
            errors.append(ImportError(
                line_number=line_num,
                content=line,
                reason=f"字段数量不足（期望 4 个字段，实际 {field_count} 个）",
            ))
        else:
            valid.append(parsed)

    return ParseResult(valid=valid, errors=errors)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_import_parser.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/import_parser.py backend/tests/test_import_parser.py
git commit -m "feat: add import text parser with format A/B support and line-level validation"
```

---

## Task 5: Mail Sanitizer Service (TDD)

**Files:**
- Create: `backend/app/services/mail_sanitizer.py`
- Create: `backend/tests/test_mail_sanitizer.py`

- [ ] **Step 1: Write the failing tests `backend/tests/test_mail_sanitizer.py`**

```python
from app.services.mail_sanitizer import sanitize_html


class TestSanitizeHtml:
    def test_removes_script_tags(self):
        html = '<p>Hello</p><script>alert("xss")</script>'
        assert "<script>" not in sanitize_html(html)
        assert "Hello" in sanitize_html(html)

    def test_removes_iframe(self):
        html = '<iframe src="http://evil.com"></iframe><p>OK</p>'
        result = sanitize_html(html)
        assert "<iframe" not in result
        assert "OK" in result

    def test_removes_event_handlers(self):
        html = '<div onclick="steal()">Click</div>'
        result = sanitize_html(html)
        assert "onclick" not in result
        assert "Click" in result

    def test_preserves_safe_html(self):
        html = '<h1>Title</h1><p>Body with <strong>bold</strong> and <a href="https://example.com">link</a></p>'
        result = sanitize_html(html)
        assert "<h1>" in result
        assert "<strong>" in result
        assert 'href="https://example.com"' in result

    def test_adds_safe_link_attributes(self):
        html = '<a href="https://example.com">Link</a>'
        result = sanitize_html(html)
        assert 'target="_blank"' in result
        assert 'rel="noopener noreferrer"' in result

    def test_removes_javascript_href(self):
        html = '<a href="javascript:alert(1)">Click</a>'
        result = sanitize_html(html)
        assert "javascript:" not in result

    def test_preserves_img_tags(self):
        html = '<img src="https://example.com/img.png" alt="photo">'
        result = sanitize_html(html)
        assert "<img" in result
        assert 'src="https://example.com/img.png"' in result

    def test_empty_input(self):
        assert sanitize_html("") == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_mail_sanitizer.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `backend/app/services/mail_sanitizer.py`**

```python
import re

import bleach


ALLOWED_TAGS = [
    "a", "abbr", "acronym", "b", "blockquote", "br", "center",
    "code", "div", "em", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "img", "li", "ol", "p", "pre", "small", "span",
    "strong", "sub", "sup", "table", "tbody", "td", "th", "thead",
    "tr", "u", "ul",
]

ALLOWED_ATTRIBUTES = {
    "*": ["class", "style"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_html(html: str) -> str:
    if not html:
        return ""

    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )

    cleaned = re.sub(
        r'<a\s',
        '<a target="_blank" rel="noopener noreferrer" ',
        cleaned,
    )

    return cleaned
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_mail_sanitizer.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/mail_sanitizer.py backend/tests/test_mail_sanitizer.py
git commit -m "feat: add HTML sanitizer for email body rendering"
```

---

## Task 6: Pydantic Schemas & API Dependencies

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/schemas/group.py`
- Create: `backend/app/schemas/mailbox.py`
- Create: `backend/app/schemas/email.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/services/audit.py`

- [ ] **Step 1: Create `backend/app/schemas/common.py`**

```python
from uuid import UUID

from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 10


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list


class BatchIdsRequest(BaseModel):
    ids: list[UUID]
```

- [ ] **Step 2: Create `backend/app/schemas/group.py`**

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class GroupResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    mailbox_count: int = 0

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Create `backend/app/schemas/mailbox.py`**

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MailboxResponse(BaseModel):
    id: UUID
    email: str
    group_id: UUID | None
    group_name: str | None = None
    token_status: str
    channel: str
    token_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MailboxImportItem(BaseModel):
    email: str
    password: str
    client_id: str
    refresh_token: str


class MailboxImportRequest(BaseModel):
    items: list[MailboxImportItem]
    mode: str = "append"  # "append" | "overwrite"


class MailboxImportResponse(BaseModel):
    imported: int
    skipped: int
    total: int


class MailboxExportRequest(BaseModel):
    ids: list[UUID] | None = None
    format: str = "csv"  # "csv" | "xlsx"
    include_all: bool = False


class BatchCopyRequest(BaseModel):
    ids: list[UUID]
    type: str  # "email" | "password" | "combined"


class BatchCopyResponse(BaseModel):
    text: str


class BatchGroupRequest(BaseModel):
    ids: list[UUID]
    group_id: UUID | None
```

- [ ] **Step 4: Create `backend/app/schemas/email.py`**

```python
from datetime import datetime

from pydantic import BaseModel


class EmailSummary(BaseModel):
    id: str
    subject: str
    sender_name: str
    sender_email: str
    preview: str
    received_at: datetime
    is_read: bool


class EmailDetail(BaseModel):
    id: str
    subject: str
    sender_name: str
    sender_email: str
    received_at: datetime
    body_html: str
```

- [ ] **Step 5: Create `backend/app/schemas/__init__.py`**

Empty file.

- [ ] **Step 6: Create `backend/app/services/audit.py`**

```python
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
```

- [ ] **Step 7: Create `backend/app/api/deps.py`**

```python
from typing import AsyncGenerator

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.services.crypto import CryptoService

_crypto: CryptoService | None = None
_redis: Redis | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


def get_crypto() -> CryptoService:
    global _crypto
    if _crypto is None:
        _crypto = CryptoService(settings.ENCRYPTION_KEY)
    return _crypto


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=False)
    return _redis


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
```

- [ ] **Step 8: Create `backend/app/api/__init__.py`**

Empty file.

- [ ] **Step 9: Commit**

```bash
git add backend/app/schemas/ backend/app/api/ backend/app/services/audit.py
git commit -m "feat: add Pydantic schemas, API dependencies, and audit logger"
```

---

## Task 7: Groups CRUD API (TDD)

**Files:**
- Create: `backend/app/api/groups.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_api_groups.py`

- [ ] **Step 1: Create minimal `backend/app/main.py`**

```python
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
```

- [ ] **Step 2: Update `backend/tests/conftest.py` with test DB + client fixtures**

```python
import base64
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from app.database import Base
from app.api.deps import get_db, get_crypto
from app.services.crypto import CryptoService
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DB_URL)
TestSession = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def encryption_key() -> str:
    return base64.b64encode(os.urandom(32)).decode()


@pytest_asyncio.fixture
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db: AsyncSession, encryption_key: str):
    crypto = CryptoService(encryption_key)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_crypto] = lambda: crypto

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
```

- [ ] **Step 3: Write the failing tests `backend/tests/test_api_groups.py`**

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestGroupsAPI:
    async def test_list_groups_empty(self, client: AsyncClient):
        resp = await client.get("/api/groups")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_group(self, client: AsyncClient):
        resp = await client.post("/api/groups", json={"name": "营销A组"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "营销A组"
        assert data["mailbox_count"] == 0
        assert "id" in data

    async def test_create_duplicate_group_fails(self, client: AsyncClient):
        await client.post("/api/groups", json={"name": "Test"})
        resp = await client.post("/api/groups", json={"name": "Test"})
        assert resp.status_code == 409

    async def test_update_group(self, client: AsyncClient):
        create = await client.post("/api/groups", json={"name": "Old"})
        gid = create.json()["id"]
        resp = await client.put(f"/api/groups/{gid}", json={"name": "New"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    async def test_delete_group(self, client: AsyncClient):
        create = await client.post("/api/groups", json={"name": "ToDelete"})
        gid = create.json()["id"]
        resp = await client.delete(f"/api/groups/{gid}")
        assert resp.status_code == 204
        listing = await client.get("/api/groups")
        assert len(listing.json()) == 0

    async def test_delete_nonexistent_group_404(self, client: AsyncClient):
        resp = await client.delete("/api/groups/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_api_groups.py -v`
Expected: FAIL (router has no routes)

- [ ] **Step 5: Implement `backend/app/api/groups.py`**

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.group import Group
from app.models.mailbox import Mailbox
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse

router = APIRouter()


@router.get("", response_model=list[GroupResponse])
async def list_groups(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Group, func.count(Mailbox.id).label("mailbox_count"))
        .outerjoin(Mailbox, Group.id == Mailbox.group_id)
        .group_by(Group.id)
        .order_by(Group.created_at)
    )
    rows = (await db.execute(stmt)).all()
    return [
        GroupResponse(
            id=g.id,
            name=g.name,
            description=g.description,
            created_at=g.created_at,
            mailbox_count=count,
        )
        for g, count in rows
    ]


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(body: GroupCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Group).where(Group.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="分组名称已存在")

    group = Group(name=body.name, description=body.description)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        mailbox_count=0,
    )


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: UUID, body: GroupUpdate, db: AsyncSession = Depends(get_db)
):
    group = await db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")

    if body.name is not None:
        group.name = body.name
    if body.description is not None:
        group.description = body.description

    await db.commit()
    await db.refresh(group)

    count_stmt = select(func.count(Mailbox.id)).where(Mailbox.group_id == group_id)
    count = (await db.execute(count_stmt)).scalar() or 0

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        mailbox_count=count,
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: UUID, db: AsyncSession = Depends(get_db)):
    group = await db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")

    await db.delete(group)
    await db.commit()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api_groups.py -v`
Expected: All 6 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/main.py backend/app/api/groups.py backend/tests/conftest.py backend/tests/test_api_groups.py
git commit -m "feat: add groups CRUD API with tests"
```

---

## Task 8: Mailbox List, Import & Export API (TDD)

**Files:**
- Create: `backend/app/api/mailboxes.py`
- Create: `backend/tests/test_api_mailboxes.py`
- Modify: `backend/app/main.py` (add router)

- [ ] **Step 1: Write the failing tests `backend/tests/test_api_mailboxes.py`**

```python
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _import_sample(client: AsyncClient, count: int = 3) -> dict:
    items = [
        {
            "email": f"user{i}@outlook.com",
            "password": f"pass{i}",
            "client_id": f"cid{i}",
            "refresh_token": f"rt{i}",
        }
        for i in range(count)
    ]
    resp = await client.post("/api/mailboxes/import", json={"items": items, "mode": "append"})
    return resp.json()


class TestMailboxList:
    async def test_list_empty(self, client: AsyncClient):
        resp = await client.get("/api/mailboxes?page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_with_pagination(self, client: AsyncClient):
        await _import_sample(client, 5)
        resp = await client.get("/api/mailboxes?page=1&page_size=2")
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_list_search_by_email(self, client: AsyncClient):
        await _import_sample(client, 3)
        resp = await client.get("/api/mailboxes?search=user1")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["email"] == "user1@outlook.com"

    async def test_list_filter_by_group(self, client: AsyncClient):
        grp = await client.post("/api/groups", json={"name": "TestGrp"})
        gid = grp.json()["id"]
        await _import_sample(client, 2)
        listing = await client.get("/api/mailboxes")
        mid = listing.json()["items"][0]["id"]
        await client.patch("/api/mailboxes/batch/group", json={"ids": [mid], "group_id": gid})
        resp = await client.get(f"/api/mailboxes?group_id={gid}")
        assert resp.json()["total"] == 1


class TestMailboxImport:
    async def test_append_import(self, client: AsyncClient):
        result = await _import_sample(client, 3)
        assert result["imported"] == 3
        assert result["skipped"] == 0

    async def test_import_dedup_skips_existing(self, client: AsyncClient):
        await _import_sample(client, 2)
        resp = await client.post(
            "/api/mailboxes/import",
            json={
                "items": [
                    {"email": "user0@outlook.com", "password": "p", "client_id": "c", "refresh_token": "t"},
                    {"email": "new@outlook.com", "password": "p", "client_id": "c", "refresh_token": "t"},
                ],
                "mode": "append",
            },
        )
        data = resp.json()
        assert data["imported"] == 1
        assert data["skipped"] == 1

    async def test_overwrite_import(self, client: AsyncClient):
        await _import_sample(client, 3)
        resp = await client.post(
            "/api/mailboxes/import",
            json={
                "items": [
                    {"email": "only@outlook.com", "password": "p", "client_id": "c", "refresh_token": "t"},
                ],
                "mode": "overwrite",
            },
        )
        assert resp.json()["imported"] == 1
        listing = await client.get("/api/mailboxes")
        assert listing.json()["total"] == 1


class TestMailboxDelete:
    async def test_delete_single(self, client: AsyncClient):
        await _import_sample(client, 1)
        listing = await client.get("/api/mailboxes")
        mid = listing.json()["items"][0]["id"]
        resp = await client.delete(f"/api/mailboxes/{mid}")
        assert resp.status_code == 204

    async def test_delete_nonexistent_404(self, client: AsyncClient):
        resp = await client.delete("/api/mailboxes/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


class TestMailboxExport:
    async def test_export_csv(self, client: AsyncClient):
        await _import_sample(client, 2)
        resp = await client.post(
            "/api/mailboxes/export",
            json={"format": "csv", "include_all": True},
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        lines = resp.text.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_api_mailboxes.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `backend/app/api/mailboxes.py`**

```python
import csv
import io
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
    page_size: int = Query(10, ge=1, le=100),
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
        detail={"format": body.format},
        ip_address=ip,
    )
    await db.commit()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["邮箱地址", "密码", "Client_ID", "刷新令牌", "分组", "令牌状态"])

    for m in rows:
        writer.writerow([
            m.email,
            crypto.decrypt(m.password_encrypted),
            crypto.decrypt(m.client_id_encrypted),
            crypto.decrypt(m.refresh_token_encrypted),
            "",
            m.token_status,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mailboxes.csv"},
    )


@router.delete("/{mailbox_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mailbox(mailbox_id: UUID, db: AsyncSession = Depends(get_db)):
    mailbox = await db.get(Mailbox, mailbox_id)
    if not mailbox:
        raise HTTPException(status_code=404, detail="邮箱不存在")
    await db.delete(mailbox)
    await db.commit()
```

- [ ] **Step 4: Add mailboxes router to `backend/app/main.py`**

Add after the groups router import:

```python
from app.api.mailboxes import router as mailboxes_router

app.include_router(mailboxes_router, prefix="/api/mailboxes", tags=["mailboxes"])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api_mailboxes.py -v`
Expected: All 9 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/mailboxes.py backend/app/main.py backend/tests/test_api_mailboxes.py
git commit -m "feat: add mailbox list, import (append/overwrite/dedup), export, and delete API"
```

---

## Task 9: Batch Operations API (TDD)

**Files:**
- Create: `backend/app/api/batch.py`
- Create: `backend/tests/test_api_batch.py`
- Modify: `backend/app/main.py` (add router)

- [ ] **Step 1: Write the failing tests `backend/tests/test_api_batch.py`**

```python
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _import_sample(client: AsyncClient, count: int = 3) -> list[str]:
    items = [
        {"email": f"user{i}@outlook.com", "password": f"pass{i}", "client_id": f"cid{i}", "refresh_token": f"rt{i}"}
        for i in range(count)
    ]
    await client.post("/api/mailboxes/import", json={"items": items, "mode": "append"})
    resp = await client.get("/api/mailboxes")
    return [m["id"] for m in resp.json()["items"]]


class TestBatchDelete:
    async def test_batch_delete(self, client: AsyncClient):
        ids = await _import_sample(client, 3)
        resp = await client.request("DELETE", "/api/mailboxes/batch", json={"ids": ids[:2]})
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 2
        listing = await client.get("/api/mailboxes")
        assert listing.json()["total"] == 1


class TestBatchSetGroup:
    async def test_batch_set_group(self, client: AsyncClient):
        ids = await _import_sample(client, 2)
        grp = await client.post("/api/groups", json={"name": "BatchGrp"})
        gid = grp.json()["id"]
        resp = await client.patch("/api/mailboxes/batch/group", json={"ids": ids, "group_id": gid})
        assert resp.status_code == 200
        assert resp.json()["updated"] == 2
        listing = await client.get(f"/api/mailboxes?group_id={gid}")
        assert listing.json()["total"] == 2


class TestBatchCopy:
    async def test_copy_emails(self, client: AsyncClient):
        ids = await _import_sample(client, 2)
        resp = await client.post("/api/mailboxes/batch/copy", json={"ids": ids, "type": "email"})
        assert resp.status_code == 200
        text = resp.json()["text"]
        assert "user0@outlook.com" in text or "user1@outlook.com" in text

    async def test_copy_passwords(self, client: AsyncClient):
        ids = await _import_sample(client, 1)
        resp = await client.post("/api/mailboxes/batch/copy", json={"ids": ids, "type": "password"})
        assert resp.status_code == 200
        assert "pass0" in resp.json()["text"]

    async def test_copy_combined(self, client: AsyncClient):
        ids = await _import_sample(client, 1)
        resp = await client.post("/api/mailboxes/batch/copy", json={"ids": ids, "type": "combined"})
        text = resp.json()["text"]
        assert "----" in text
        assert "user0@outlook.com" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_api_batch.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `backend/app/api/batch.py`**

```python
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
```

- [ ] **Step 4: Add batch router to `backend/app/main.py`**

Add after other imports:

```python
from app.api.batch import router as batch_router

app.include_router(batch_router, prefix="/api/mailboxes", tags=["batch"])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api_batch.py -v`
Expected: All 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/batch.py backend/app/main.py backend/tests/test_api_batch.py
git commit -m "feat: add batch delete, batch set group, and batch copy API"
```

---

## Task 10: Graph API Client & Email Endpoints

**Files:**
- Create: `backend/app/services/graph_client.py`
- Create: `backend/app/api/emails.py`
- Create: `backend/tests/test_api_emails.py`
- Modify: `backend/app/main.py` (add router)

- [ ] **Step 1: Implement `backend/app/services/graph_client.py`**

```python
import httpx
import msal
from redis.asyncio import Redis

from app.config import settings

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["https://graph.microsoft.com/.default"]


class GraphClient:
    def __init__(self, redis: Redis):
        self._redis = redis

    async def _get_access_token(
        self, client_id: str, refresh_token: str, mailbox_id: str
    ) -> str:
        cache_key = f"access_token:{mailbox_id}"
        cached = await self._redis.get(cache_key)
        if cached:
            return cached.decode()

        app = msal.PublicClientApplication(client_id=client_id)
        result = app.acquire_token_by_refresh_token(refresh_token, scopes=SCOPES)

        if "access_token" not in result:
            raise ValueError(f"Token refresh failed: {result.get('error_description', 'unknown')}")

        token = result["access_token"]
        await self._redis.setex(cache_key, settings.ACCESS_TOKEN_CACHE_TTL, token)
        return token

    async def list_emails(
        self,
        client_id: str,
        refresh_token: str,
        mailbox_id: str,
        folder: str = "inbox",
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> dict:
        token = await self._get_access_token(client_id, refresh_token, mailbox_id)
        skip = (page - 1) * page_size

        folder_map = {"inbox": "Inbox", "junk": "JunkEmail"}
        folder_name = folder_map.get(folder, "Inbox")

        url = f"{GRAPH_BASE}/me/mailFolders/{folder_name}/messages"
        params = {
            "$top": page_size,
            "$skip": skip,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,bodyPreview,receivedDateTime,isRead",
        }
        if search:
            params["$search"] = f'"{search}"'

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_email_body(
        self, client_id: str, refresh_token: str, mailbox_id: str, message_id: str
    ) -> dict:
        token = await self._get_access_token(client_id, refresh_token, mailbox_id)
        url = f"{GRAPH_BASE}/me/messages/{message_id}"
        params = {"$select": "id,subject,from,receivedDateTime,body"}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def validate_token(self, client_id: str, refresh_token: str) -> bool:
        try:
            app = msal.PublicClientApplication(client_id=client_id)
            result = app.acquire_token_by_refresh_token(refresh_token, scopes=SCOPES)
            return "access_token" in result
        except Exception:
            return False
```

- [ ] **Step 2: Implement `backend/app/api/emails.py`**

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_crypto, get_redis
from app.models.mailbox import Mailbox
from app.schemas.email import EmailSummary, EmailDetail
from app.services.crypto import CryptoService
from app.services.graph_client import GraphClient
from app.services.mail_sanitizer import sanitize_html

router = APIRouter()


async def _get_mailbox_creds(
    mailbox_id: UUID, db: AsyncSession, crypto: CryptoService
) -> tuple[Mailbox, str, str]:
    mailbox = await db.get(Mailbox, mailbox_id)
    if not mailbox:
        raise HTTPException(status_code=404, detail="邮箱不存在")
    client_id = crypto.decrypt(mailbox.client_id_encrypted)
    refresh_token = crypto.decrypt(mailbox.refresh_token_encrypted)
    return mailbox, client_id, refresh_token


@router.get("/{mailbox_id}/emails", response_model=list[EmailSummary])
async def list_emails(
    mailbox_id: UUID,
    folder: str = Query("inbox"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    crypto: CryptoService = Depends(get_crypto),
    redis=Depends(get_redis),
):
    mailbox, client_id, refresh_token = await _get_mailbox_creds(mailbox_id, db, crypto)
    graph = GraphClient(redis)

    try:
        data = await graph.list_emails(
            client_id, refresh_token, str(mailbox_id),
            folder=folder, page=page, page_size=page_size, search=search,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Graph API 调用失败: {str(e)}")

    emails = []
    for msg in data.get("value", []):
        sender = msg.get("from", {}).get("emailAddress", {})
        emails.append(EmailSummary(
            id=msg["id"],
            subject=msg.get("subject", ""),
            sender_name=sender.get("name", ""),
            sender_email=sender.get("address", ""),
            preview=msg.get("bodyPreview", ""),
            received_at=msg["receivedDateTime"],
            is_read=msg.get("isRead", False),
        ))

    return emails


@router.get("/{mailbox_id}/emails/{message_id}", response_model=EmailDetail)
async def get_email_detail(
    mailbox_id: UUID,
    message_id: str,
    db: AsyncSession = Depends(get_db),
    crypto: CryptoService = Depends(get_crypto),
    redis=Depends(get_redis),
):
    mailbox, client_id, refresh_token = await _get_mailbox_creds(mailbox_id, db, crypto)
    graph = GraphClient(redis)

    try:
        data = await graph.get_email_body(
            client_id, refresh_token, str(mailbox_id), message_id
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Graph API 调用失败: {str(e)}")

    sender = data.get("from", {}).get("emailAddress", {})
    body_html = data.get("body", {}).get("content", "")

    return EmailDetail(
        id=data["id"],
        subject=data.get("subject", ""),
        sender_name=sender.get("name", ""),
        sender_email=sender.get("address", ""),
        received_at=data["receivedDateTime"],
        body_html=sanitize_html(body_html),
    )
```

- [ ] **Step 3: Write tests with mocked Graph API `backend/tests/test_api_emails.py`**

```python
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

MOCK_LIST_RESPONSE = {
    "value": [
        {
            "id": "msg-001",
            "subject": "Test Email",
            "from": {"emailAddress": {"name": "Sender", "address": "sender@test.com"}},
            "bodyPreview": "Hello world...",
            "receivedDateTime": "2026-05-23T10:00:00Z",
            "isRead": False,
        }
    ]
}

MOCK_BODY_RESPONSE = {
    "id": "msg-001",
    "subject": "Test Email",
    "from": {"emailAddress": {"name": "Sender", "address": "sender@test.com"}},
    "receivedDateTime": "2026-05-23T10:00:00Z",
    "body": {"contentType": "html", "content": "<p>Hello <script>alert(1)</script></p>"},
}


async def _import_one(client: AsyncClient) -> str:
    await client.post(
        "/api/mailboxes/import",
        json={
            "items": [{"email": "test@outlook.com", "password": "p", "client_id": "c", "refresh_token": "t"}],
            "mode": "append",
        },
    )
    listing = await client.get("/api/mailboxes")
    return listing.json()["items"][0]["id"]


class TestEmailListAPI:
    @patch("app.api.emails.GraphClient")
    async def test_list_emails(self, MockGraph, client: AsyncClient):
        mid = await _import_one(client)
        instance = MockGraph.return_value
        instance.list_emails = AsyncMock(return_value=MOCK_LIST_RESPONSE)

        resp = await client.get(f"/api/mailboxes/{mid}/emails?folder=inbox")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["subject"] == "Test Email"
        assert data[0]["sender_name"] == "Sender"


class TestEmailDetailAPI:
    @patch("app.api.emails.GraphClient")
    async def test_get_email_body_sanitized(self, MockGraph, client: AsyncClient):
        mid = await _import_one(client)
        instance = MockGraph.return_value
        instance.get_email_body = AsyncMock(return_value=MOCK_BODY_RESPONSE)

        resp = await client.get(f"/api/mailboxes/{mid}/emails/msg-001")
        assert resp.status_code == 200
        data = resp.json()
        assert "<script>" not in data["body_html"]
        assert "Hello" in data["body_html"]
```

- [ ] **Step 4: Add emails router to `backend/app/main.py`**

```python
from app.api.emails import router as emails_router

app.include_router(emails_router, prefix="/api/mailboxes", tags=["emails"])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api_emails.py -v`
Expected: All 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/graph_client.py backend/app/api/emails.py backend/tests/test_api_emails.py backend/app/main.py
git commit -m "feat: add Graph API client and email list/detail endpoints"
```

---

## Task 11: Token Status API & Worker (TDD)

**Files:**
- Create: `backend/app/api/tokens.py`
- Create: `backend/app/worker/__init__.py`
- Create: `backend/app/worker/tasks.py`
- Create: `backend/app/worker/token_checker.py`
- Create: `backend/tests/test_api_tokens.py`
- Create: `backend/tests/test_token_checker.py`
- Modify: `backend/app/main.py` (add router)

- [ ] **Step 1: Implement `backend/app/api/tokens.py`**

```python
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
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
    ids = body.get("ids", [])
    from sqlalchemy import update
    stmt = update(Mailbox).where(Mailbox.id.in_(ids)).values(token_status="checking")
    result = await db.execute(stmt)
    await db.commit()
    return {"queued": result.rowcount}
```

- [ ] **Step 2: Implement `backend/app/worker/token_checker.py`**

```python
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
```

- [ ] **Step 3: Implement `backend/app/worker/tasks.py`**

```python
from arq import cron
from redis.asyncio import Redis

from app.config import settings
from app.database import async_session
from app.services.crypto import CryptoService
from app.worker.token_checker import check_tokens


async def run_token_check(ctx):
    crypto = CryptoService(settings.ENCRYPTION_KEY)
    redis = ctx.get("redis") or Redis.from_url(settings.REDIS_URL, decode_responses=False)
    await check_tokens(
        async_session,
        crypto,
        redis,
        interval=settings.TOKEN_CHECK_INTERVAL,
        concurrency=settings.TOKEN_CHECK_CONCURRENCY,
    )


class WorkerSettings:
    functions = []
    cron_jobs = [
        cron(run_token_check, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]
    redis_settings = None

    @staticmethod
    def on_startup(ctx):
        ctx["redis"] = Redis.from_url(settings.REDIS_URL, decode_responses=False)

    @staticmethod
    async def on_shutdown(ctx):
        redis = ctx.get("redis")
        if redis:
            await redis.close()
```

Create `backend/app/worker/__init__.py` as empty file.

- [ ] **Step 4: Write tests `backend/tests/test_api_tokens.py`**

```python
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _import_one(client: AsyncClient) -> str:
    await client.post(
        "/api/mailboxes/import",
        json={
            "items": [{"email": "t@outlook.com", "password": "p", "client_id": "c", "refresh_token": "t"}],
            "mode": "append",
        },
    )
    listing = await client.get("/api/mailboxes")
    return listing.json()["items"][0]["id"]


class TestTokenStatusAPI:
    async def test_get_status(self, client: AsyncClient):
        mid = await _import_one(client)
        resp = await client.get(f"/api/tokens/status?ids={mid}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "normal"

    async def test_trigger_check(self, client: AsyncClient):
        mid = await _import_one(client)
        resp = await client.post("/api/tokens/check", json={"ids": [mid]})
        assert resp.status_code == 200
        assert resp.json()["queued"] == 1
        status = await client.get(f"/api/tokens/status?ids={mid}")
        assert status.json()[0]["status"] == "checking"
```

- [ ] **Step 5: Add tokens router to `backend/app/main.py`**

```python
from app.api.tokens import router as tokens_router

app.include_router(tokens_router, prefix="/api/tokens", tags=["tokens"])
```

- [ ] **Step 6: Run all backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/tokens.py backend/app/worker/ backend/tests/test_api_tokens.py backend/app/main.py
git commit -m "feat: add token status API, ARQ worker, and token health checker"
```

---

## Task 12: Frontend Setup & TypeScript Types

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/vite-env.d.ts`
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/services/api.ts`
- Create: `frontend/src/utils/clipboard.ts`
- Create: `frontend/index.html`

- [ ] **Step 1: Install dependencies**

Run: `cd frontend && npm install`

- [ ] **Step 2: Create `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>多邮箱管理系统</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

- [ ] **Step 3: Create `frontend/src/vite-env.d.ts`**

```typescript
/// <reference types="vite/client" />
```

- [ ] **Step 4: Create `frontend/src/types/index.ts`**

```typescript
export interface Mailbox {
  id: string;
  email: string;
  group_id: string | null;
  group_name: string | null;
  token_status: 'normal' | 'checking' | 'expired';
  channel: string;
  token_checked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Group {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  mailbox_count: number;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface ImportResult {
  imported: number;
  skipped: number;
  total: number;
}

export interface EmailSummary {
  id: string;
  subject: string;
  sender_name: string;
  sender_email: string;
  preview: string;
  received_at: string;
  is_read: boolean;
}

export interface EmailDetail {
  id: string;
  subject: string;
  sender_name: string;
  sender_email: string;
  received_at: string;
  body_html: string;
}

export interface TokenStatus {
  id: string;
  status: 'normal' | 'checking' | 'expired';
  checked_at: string | null;
}
```

- [ ] **Step 5: Create `frontend/src/services/api.ts`**

```typescript
import axios from 'axios';
import type {
  Mailbox, Group, PaginatedResponse, ImportResult,
  EmailSummary, EmailDetail, TokenStatus,
} from '@/types';

const http = axios.create({ baseURL: '/api' });

export const groupsApi = {
  list: () => http.get<Group[]>('/groups').then(r => r.data),
  create: (data: { name: string; description?: string }) =>
    http.post<Group>('/groups', data).then(r => r.data),
  update: (id: string, data: { name?: string; description?: string }) =>
    http.put<Group>(`/groups/${id}`, data).then(r => r.data),
  delete: (id: string) => http.delete(`/groups/${id}`),
};

export const mailboxesApi = {
  list: (params: { page?: number; page_size?: number; search?: string; group_id?: string }) =>
    http.get<PaginatedResponse<Mailbox>>('/mailboxes', { params }).then(r => r.data),
  import: (items: { email: string; password: string; client_id: string; refresh_token: string }[], mode: string) =>
    http.post<ImportResult>('/mailboxes/import', { items, mode }).then(r => r.data),
  export: (data: { ids?: string[]; format: string; include_all?: boolean }) =>
    http.post('/mailboxes/export', data, { responseType: 'blob' }),
  delete: (id: string) => http.delete(`/mailboxes/${id}`),
  batchDelete: (ids: string[]) =>
    http.request({ method: 'DELETE', url: '/mailboxes/batch', data: { ids } }).then(r => r.data),
  batchSetGroup: (ids: string[], group_id: string | null) =>
    http.patch('/mailboxes/batch/group', { ids, group_id }).then(r => r.data),
  batchCopy: (ids: string[], type: 'email' | 'password' | 'combined') =>
    http.post<{ text: string }>('/mailboxes/batch/copy', { ids, type }).then(r => r.data),
};

export const emailsApi = {
  list: (mailboxId: string, params: { folder?: string; page?: number; page_size?: number; search?: string }) =>
    http.get<EmailSummary[]>(`/mailboxes/${mailboxId}/emails`, { params }).then(r => r.data),
  detail: (mailboxId: string, messageId: string) =>
    http.get<EmailDetail>(`/mailboxes/${mailboxId}/emails/${messageId}`).then(r => r.data),
};

export const tokensApi = {
  status: (ids: string[]) =>
    http.get<TokenStatus[]>('/tokens/status', { params: { ids: ids.join(',') } }).then(r => r.data),
  check: (ids: string[]) =>
    http.post('/tokens/check', { ids }).then(r => r.data),
};
```

- [ ] **Step 6: Create `frontend/src/utils/clipboard.ts`**

```typescript
import { message } from 'antd';

export async function copyToClipboard(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    message.success('已复制到剪贴板');
  } catch {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    message.success('已复制到剪贴板');
  }
}
```

- [ ] **Step 7: Create `frontend/src/main.tsx`**

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN}>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
```

- [ ] **Step 8: Create `frontend/src/App.tsx`**

```tsx
import { Layout, Typography } from 'antd';
import { MailOutlined } from '@ant-design/icons';
import MailboxList from './pages/MailboxList';

const { Header, Content } = Layout;

export default function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <MailOutlined style={{ fontSize: 20, color: '#1890ff' }} />
        <Typography.Text strong style={{ color: '#fff', fontSize: 16 }}>
          多邮箱管理系统
        </Typography.Text>
      </Header>
      <Content style={{ padding: 24 }}>
        <MailboxList />
      </Content>
    </Layout>
  );
}
```

- [ ] **Step 9: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors (MailboxList not yet created — create a stub):

Create `frontend/src/pages/MailboxList.tsx`:
```tsx
export default function MailboxList() {
  return <div>Loading...</div>;
}
```

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat: add frontend scaffolding with types, API client, and app shell"
```

---

## Task 13: Frontend Import Parser & Hooks

**Files:**
- Create: `frontend/src/utils/importParser.ts`
- Create: `frontend/src/hooks/useMailboxes.ts`
- Create: `frontend/src/hooks/useTokenStatus.ts`
- Create: `frontend/src/hooks/useEmails.ts`

- [ ] **Step 1: Create `frontend/src/utils/importParser.ts`**

```typescript
export interface ParsedLine {
  email: string;
  password: string;
  client_id: string;
  refresh_token: string;
}

export interface ParseError {
  line_number: number;
  content: string;
  reason: string;
}

export interface ParseResult {
  valid: ParsedLine[];
  errors: ParseError[];
}

export function parseImportText(text: string): ParseResult {
  const valid: ParsedLine[] = [];
  const errors: ParseError[] = [];

  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    let parts: string[];
    if (line.includes('----')) {
      parts = line.split('----').map(p => p.trim());
    } else {
      parts = line.split(/\s+/);
    }

    if (parts.length !== 4) {
      errors.push({
        line_number: i + 1,
        content: line,
        reason: `字段数量不足（期望 4 个字段，实际 ${parts.length} 个）`,
      });
    } else {
      valid.push({
        email: parts[0],
        password: parts[1],
        client_id: parts[2],
        refresh_token: parts[3],
      });
    }
  }

  return { valid, errors };
}
```

- [ ] **Step 2: Create `frontend/src/hooks/useMailboxes.ts`**

```typescript
import { useState, useCallback } from 'react';
import { mailboxesApi } from '@/services/api';
import type { Mailbox, PaginatedResponse } from '@/types';

export function useMailboxes() {
  const [data, setData] = useState<PaginatedResponse<Mailbox>>({
    total: 0, page: 1, page_size: 10, items: [],
  });
  const [loading, setLoading] = useState(false);

  const fetch = useCallback(async (params: {
    page?: number; page_size?: number; search?: string; group_id?: string;
  } = {}) => {
    setLoading(true);
    try {
      const result = await mailboxesApi.list(params);
      setData(result);
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, fetch };
}
```

- [ ] **Step 3: Create `frontend/src/hooks/useTokenStatus.ts`**

```typescript
import { useEffect, useRef } from 'react';
import { tokensApi } from '@/services/api';
import type { TokenStatus } from '@/types';

export function useTokenStatus(
  ids: string[],
  onUpdate: (statuses: TokenStatus[]) => void,
  interval = 30000,
) {
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    if (ids.length === 0) return;

    const poll = async () => {
      try {
        const statuses = await tokensApi.status(ids);
        onUpdate(statuses);
      } catch {
        // silent — poll will retry
      }
    };

    poll();
    timerRef.current = setInterval(poll, interval);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [ids.join(','), interval]);
}
```

- [ ] **Step 4: Create `frontend/src/hooks/useEmails.ts`**

```typescript
import { useState, useCallback } from 'react';
import { emailsApi } from '@/services/api';
import type { EmailSummary, EmailDetail } from '@/types';

export function useEmails(mailboxId: string) {
  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [detail, setDetail] = useState<EmailDetail | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchList = useCallback(async (params: {
    folder?: string; page?: number; search?: string;
  } = {}) => {
    setLoading(true);
    try {
      const result = await emailsApi.list(mailboxId, params);
      setEmails(result);
    } finally {
      setLoading(false);
    }
  }, [mailboxId]);

  const fetchDetail = useCallback(async (messageId: string) => {
    setLoading(true);
    try {
      const result = await emailsApi.detail(mailboxId, messageId);
      setDetail(result);
    } finally {
      setLoading(false);
    }
  }, [mailboxId]);

  return { emails, detail, loading, fetchList, fetchDetail };
}
```

- [ ] **Step 5: Verify compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/utils/importParser.ts frontend/src/hooks/
git commit -m "feat: add frontend import parser and data hooks"
```

---

## Task 14: Small Components (TokenStatus, GroupTag, BatchCopyMenu, GroupSelect)

**Files:**
- Create: `frontend/src/components/TokenStatus.tsx`
- Create: `frontend/src/components/GroupTag.tsx`
- Create: `frontend/src/components/BatchCopyMenu.tsx`
- Create: `frontend/src/components/GroupSelect.tsx`

- [ ] **Step 1: Create `frontend/src/components/TokenStatus.tsx`**

```tsx
import { Badge } from 'antd';

const STATUS_MAP = {
  normal: { status: 'success' as const, text: '正常' },
  checking: { status: 'processing' as const, text: '检测中' },
  expired: { status: 'error' as const, text: '失效' },
};

export default function TokenStatus({ status }: { status: 'normal' | 'checking' | 'expired' }) {
  const config = STATUS_MAP[status] || STATUS_MAP.normal;
  return <Badge status={config.status} text={config.text} />;
}
```

- [ ] **Step 2: Create `frontend/src/components/GroupTag.tsx`**

```tsx
import { Tag } from 'antd';

const COLORS = ['blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'gold', 'lime'];

function hashColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0;
  }
  return COLORS[Math.abs(hash) % COLORS.length];
}

export default function GroupTag({ name }: { name: string | null }) {
  if (!name) return <Tag>默认分组</Tag>;
  return <Tag color={hashColor(name)}>{name}</Tag>;
}
```

- [ ] **Step 3: Create `frontend/src/components/BatchCopyMenu.tsx`**

```tsx
import { Dropdown, Button, message } from 'antd';
import { CopyOutlined, DownOutlined } from '@ant-design/icons';
import { mailboxesApi } from '@/services/api';
import { copyToClipboard } from '@/utils/clipboard';

interface Props {
  selectedIds: string[];
}

export default function BatchCopyMenu({ selectedIds }: Props) {
  const handleCopy = async (type: 'email' | 'password' | 'combined') => {
    if (selectedIds.length === 0) {
      message.warning('请先选择邮箱');
      return;
    }
    const result = await mailboxesApi.batchCopy(selectedIds, type);
    await copyToClipboard(result.text);
  };

  const items = [
    { key: 'email', label: '批量复制账号', onClick: () => handleCopy('email') },
    { key: 'password', label: '批量复制密码', onClick: () => handleCopy('password') },
    { key: 'combined', label: '批量复制账号----密码', onClick: () => handleCopy('combined') },
  ];

  return (
    <Dropdown menu={{ items }} trigger={['click']}>
      <Button icon={<CopyOutlined />}>
        批量复制 <DownOutlined />
      </Button>
    </Dropdown>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/GroupSelect.tsx`**

```tsx
import { useState, useEffect } from 'react';
import { Modal, Select, message } from 'antd';
import { groupsApi, mailboxesApi } from '@/services/api';
import type { Group } from '@/types';

interface Props {
  open: boolean;
  selectedIds: string[];
  onClose: () => void;
  onSuccess: () => void;
}

export default function GroupSelect({ open, selectedIds, onClose, onSuccess }: Props) {
  const [groups, setGroups] = useState<Group[]>([]);
  const [groupId, setGroupId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      groupsApi.list().then(setGroups);
    }
  }, [open]);

  const handleOk = async () => {
    setLoading(true);
    try {
      await mailboxesApi.batchSetGroup(selectedIds, groupId);
      message.success(`已更新 ${selectedIds.length} 个邮箱的分组`);
      onSuccess();
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="批量设置分组"
      open={open}
      onOk={handleOk}
      onCancel={onClose}
      confirmLoading={loading}
    >
      <Select
        style={{ width: '100%' }}
        placeholder="选择分组"
        allowClear
        onChange={setGroupId}
        options={groups.map(g => ({ label: g.name, value: g.id }))}
      />
    </Modal>
  );
}
```

- [ ] **Step 5: Verify compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/TokenStatus.tsx frontend/src/components/GroupTag.tsx frontend/src/components/BatchCopyMenu.tsx frontend/src/components/GroupSelect.tsx
git commit -m "feat: add TokenStatus, GroupTag, BatchCopyMenu, and GroupSelect components"
```

---

## Task 15: ImportModal Component

**Files:**
- Create: `frontend/src/components/ImportModal.tsx`

- [ ] **Step 1: Create `frontend/src/components/ImportModal.tsx`**

```tsx
import { useState } from 'react';
import { Modal, Tabs, Input, Upload, Button, Alert, Popconfirm, message, Typography } from 'antd';
import { UploadOutlined, InboxOutlined } from '@ant-design/icons';
import { parseImportText } from '@/utils/importParser';
import { mailboxesApi } from '@/services/api';
import type { ParseError } from '@/utils/importParser';

const { TextArea } = Input;
const { Dragger } = Upload;

interface Props {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function ImportModal({ open, onClose, onSuccess }: Props) {
  const [text, setText] = useState('');
  const [errors, setErrors] = useState<ParseError[]>([]);
  const [loading, setLoading] = useState(false);

  const handleImport = async (mode: 'append' | 'overwrite') => {
    const result = parseImportText(text);
    if (result.errors.length > 0) {
      setErrors(result.errors);
      return;
    }
    if (result.valid.length === 0) {
      message.warning('没有可导入的数据');
      return;
    }

    setLoading(true);
    try {
      const resp = await mailboxesApi.import(result.valid, mode);
      message.success(`成功导入 ${resp.imported} 条，跳过 ${resp.skipped} 条`);
      setText('');
      setErrors([]);
      onSuccess();
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleFileRead = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      setText(e.target?.result as string || '');
      setErrors([]);
    };
    reader.readAsText(file);
    return false;
  };

  const footer = (
    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
      <Button onClick={onClose}>取消</Button>
      <Button type="primary" loading={loading} onClick={() => handleImport('append')}>
        追加导入
      </Button>
      <Popconfirm
        title="确认覆盖导入？"
        description="这将清空所有现有邮箱数据，不可撤销！"
        onConfirm={() => handleImport('overwrite')}
        okText="确认覆盖"
        okButtonProps={{ danger: true }}
      >
        <Button danger loading={loading}>覆盖导入</Button>
      </Popconfirm>
    </div>
  );

  return (
    <Modal
      title="导入邮箱账户"
      open={open}
      onCancel={onClose}
      width={700}
      footer={footer}
    >
      <div style={{
        background: '#f6f8fa', border: '1px solid #e8e8e8',
        borderRadius: 8, padding: '10px 14px', marginBottom: 12, fontSize: 12,
      }}>
        <Typography.Text type="secondary">支持格式：</Typography.Text>
        <br />
        <code>格式 A：邮箱地址 密码 Client_ID 刷新令牌（空格/Tab 分隔）</code>
        <br />
        <code>格式 B：邮箱地址----密码----Client_ID----刷新令牌（四连减号分隔）</code>
      </div>

      <Tabs
        items={[
          {
            key: 'text',
            label: '文本录入',
            children: (
              <TextArea
                rows={10}
                value={text}
                onChange={e => { setText(e.target.value); setErrors([]); }}
                placeholder="每行一条记录，支持混合格式 A 和 B..."
                style={{ fontFamily: 'monospace' }}
              />
            ),
          },
          {
            key: 'file',
            label: '文件上传',
            children: (
              <Dragger
                accept=".txt,.csv"
                showUploadList={false}
                beforeUpload={handleFileRead}
              >
                <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                <p>点击或拖拽文件到此区域上传</p>
                <p className="ant-upload-hint">支持 .txt / .csv 文件</p>
              </Dragger>
            ),
          },
        ]}
      />

      {errors.length > 0 && (
        <Alert
          type="error"
          style={{ marginTop: 12 }}
          message={`校验失败 — ${errors.length} 行数据不合规`}
          description={
            <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12 }}>
              {errors.map(e => (
                <li key={e.line_number}>
                  第 {e.line_number} 行：{e.reason} — "{e.content}"
                </li>
              ))}
            </ul>
          }
        />
      )}
    </Modal>
  );
}
```

- [ ] **Step 2: Verify compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ImportModal.tsx
git commit -m "feat: add ImportModal with text entry, file upload, and line-level validation"
```

---

## Task 16: EmailViewer Component

**Files:**
- Create: `frontend/src/components/EmailViewer.tsx`

- [ ] **Step 1: Create `frontend/src/components/EmailViewer.tsx`**

```tsx
import { useState, useEffect, useMemo } from 'react';
import { Modal, Tabs, Input, Button, List, Spin, Empty, Typography, message } from 'antd';
import { ReloadOutlined, CopyOutlined } from '@ant-design/icons';
import { useEmails } from '@/hooks/useEmails';
import { copyToClipboard } from '@/utils/clipboard';
import type { EmailSummary } from '@/types';
import dayjs from 'dayjs';

interface Props {
  open: boolean;
  mailboxId: string;
  email: string;
  onClose: () => void;
}

export default function EmailViewer({ open, mailboxId, email, onClose }: Props) {
  const { emails, detail, loading, fetchList, fetchDetail } = useEmails(mailboxId);
  const [folder, setFolder] = useState<string>('inbox');
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (open && mailboxId) {
      fetchList({ folder });
      setSelectedId(null);
    }
  }, [open, mailboxId, folder]);

  const filteredEmails = useMemo(() => {
    if (!search) return emails;
    const q = search.toLowerCase();
    return emails.filter(
      e => e.sender_name.toLowerCase().includes(q) || e.subject.toLowerCase().includes(q)
    );
  }, [emails, search]);

  const handleSelect = (msg: EmailSummary) => {
    setSelectedId(msg.id);
    fetchDetail(msg.id);
  };

  const codeRegex = /\b(\d{4,8})\b/g;

  const renderBodyWithCodes = (html: string) => {
    const enhanced = html.replace(codeRegex, (match) => {
      return `<span style="background:#fff7e6;border:1px solid #ffd591;border-radius:4px;padding:2px 8px;font-family:monospace;font-size:18px;font-weight:700;color:#fa8c16;letter-spacing:2px">${match}</span> <button onclick="navigator.clipboard.writeText('${match}');this.textContent='已复制'" style="border:1px solid #ffd591;background:#fff;border-radius:4px;padding:2px 8px;font-size:11px;color:#fa8c16;cursor:pointer">复制</button>`;
    });
    return enhanced;
  };

  return (
    <Modal
      title={`邮件列表 — ${email}`}
      open={open}
      onCancel={onClose}
      width="90vw"
      style={{ top: '5vh' }}
      styles={{ body: { height: '75vh', padding: 0, display: 'flex', overflow: 'hidden' } }}
      footer={null}
    >
      {/* Left Panel */}
      <div style={{ width: 340, borderRight: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column' }}>
        <Tabs
          activeKey={folder}
          onChange={setFolder}
          style={{ padding: '0 12px' }}
          items={[
            { key: 'inbox', label: '收件箱' },
            { key: 'junk', label: '垃圾箱' },
          ]}
        />
        <div style={{ display: 'flex', gap: 6, padding: '0 12px 8px' }}>
          <Input.Search
            placeholder="搜索发件人、主题..."
            size="small"
            value={search}
            onChange={e => setSearch(e.target.value)}
            allowClear
          />
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => fetchList({ folder })}
            loading={loading}
          />
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          <Spin spinning={loading}>
            <List
              dataSource={filteredEmails}
              renderItem={(item) => (
                <List.Item
                  onClick={() => handleSelect(item)}
                  style={{
                    padding: '10px 14px',
                    cursor: 'pointer',
                    background: selectedId === item.id ? '#e6f7ff' : undefined,
                    borderLeft: selectedId === item.id ? '3px solid #1890ff' : '3px solid transparent',
                  }}
                >
                  <div style={{ width: '100%' }}>
                    <div style={{
                      fontWeight: item.is_read ? 'normal' : 600,
                      fontSize: 13, marginBottom: 2,
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}>
                      {item.sender_name || item.sender_email}
                    </div>
                    <div style={{
                      fontSize: 12, color: '#555', marginBottom: 2,
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}>
                      {item.subject}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#999' }}>
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                        {item.preview}
                      </span>
                      <span style={{ flexShrink: 0, marginLeft: 8 }}>
                        {dayjs(item.received_at).format('MM-DD HH:mm')}
                      </span>
                    </div>
                  </div>
                </List.Item>
              )}
            />
          </Spin>
        </div>
      </div>

      {/* Right Panel */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {!detail ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Empty description="请从左侧选择一封邮件查看" />
          </div>
        ) : (
          <>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid #f0f0f0' }}>
              <Typography.Title level={4} style={{ marginBottom: 8 }}>
                {detail.subject}
              </Typography.Title>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: '50%', background: '#1890ff',
                  color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontWeight: 600, flexShrink: 0,
                }}>
                  {detail.sender_name?.[0]?.toUpperCase() || '?'}
                </div>
                <div>
                  <div style={{ fontWeight: 500 }}>{detail.sender_name}</div>
                  <div style={{ fontSize: 11, color: '#999' }}>{detail.sender_email}</div>
                </div>
                <div style={{ marginLeft: 'auto', fontSize: 11, color: '#999' }}>
                  {dayjs(detail.received_at).format('YYYY-MM-DD HH:mm:ss')}
                </div>
              </div>
            </div>
            <div style={{ flex: 1, overflow: 'auto' }}>
              <iframe
                srcDoc={renderBodyWithCodes(detail.body_html)}
                sandbox="allow-same-origin"
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="email body"
              />
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
```

- [ ] **Step 2: Verify compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/EmailViewer.tsx
git commit -m "feat: add EmailViewer with inbox/junk tabs, search, and sandboxed HTML rendering"
```

---

## Task 17: MailboxList Main Page

**Files:**
- Modify: `frontend/src/pages/MailboxList.tsx`

- [ ] **Step 1: Implement `frontend/src/pages/MailboxList.tsx`**

```tsx
import { useState, useEffect, useCallback, useRef } from 'react';
import { Table, Button, Input, Select, Space, Popconfirm, message, Tooltip } from 'antd';
import {
  PlusOutlined, DownloadOutlined, TagOutlined, DeleteOutlined,
  EyeOutlined, CopyOutlined, EyeInvisibleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useMailboxes } from '@/hooks/useMailboxes';
import { useTokenStatus } from '@/hooks/useTokenStatus';
import { groupsApi, mailboxesApi } from '@/services/api';
import { copyToClipboard } from '@/utils/clipboard';
import type { Mailbox, Group } from '@/types';
import TokenStatusComp from '@/components/TokenStatus';
import GroupTag from '@/components/GroupTag';
import BatchCopyMenu from '@/components/BatchCopyMenu';
import GroupSelect from '@/components/GroupSelect';
import ImportModal from '@/components/ImportModal';
import EmailViewer from '@/components/EmailViewer';

export default function MailboxList() {
  const { data, loading, fetch } = useMailboxes();
  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [groupFilter, setGroupFilter] = useState<string | undefined>();
  const [groups, setGroups] = useState<Group[]>([]);
  const [showImport, setShowImport] = useState(false);
  const [showGroupSelect, setShowGroupSelect] = useState(false);
  const [visiblePasswords, setVisiblePasswords] = useState<Set<string>>(new Set());
  const [passwordCache, setPasswordCache] = useState<Record<string, string>>({});
  const [emailViewer, setEmailViewer] = useState<{ id: string; email: string } | null>(null);

  const pageRef = useRef({ page: 1, page_size: 10 });

  const loadData = useCallback(() => {
    fetch({
      page: pageRef.current.page,
      page_size: pageRef.current.page_size,
      search: search || undefined,
      group_id: groupFilter,
    });
  }, [fetch, search, groupFilter]);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { groupsApi.list().then(setGroups); }, []);

  useTokenStatus(
    data.items.map(m => m.id),
    (statuses) => {
      // Trigger re-fetch if any status changed
      const changed = statuses.some(s => {
        const item = data.items.find(m => m.id === s.id);
        return item && item.token_status !== s.status;
      });
      if (changed) loadData();
    },
  );

  const handleDelete = async (id: string) => {
    await mailboxesApi.delete(id);
    message.success('已删除');
    loadData();
  };

  const handleBatchDelete = async () => {
    await mailboxesApi.batchDelete(selectedRowKeys);
    message.success(`已删除 ${selectedRowKeys.length} 条`);
    setSelectedRowKeys([]);
    loadData();
  };

  const handleExport = async () => {
    const resp = await mailboxesApi.export({
      ids: selectedRowKeys.length > 0 ? selectedRowKeys : undefined,
      format: 'csv',
      include_all: selectedRowKeys.length === 0,
    });
    const url = URL.createObjectURL(new Blob([resp.data]));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'mailboxes.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const togglePassword = async (id: string) => {
    if (visiblePasswords.has(id)) {
      setVisiblePasswords(prev => { const s = new Set(prev); s.delete(id); return s; });
    } else {
      if (!passwordCache[id]) {
        const result = await mailboxesApi.batchCopy([id], 'password');
        setPasswordCache(prev => ({ ...prev, [id]: result.text }));
      }
      setVisiblePasswords(prev => new Set(prev).add(id));
    }
  };

  const columns: ColumnsType<Mailbox> = [
    {
      title: '#',
      width: 50,
      render: (_v, _r, i) => (data.page - 1) * data.page_size + i + 1,
    },
    {
      title: '邮箱地址',
      dataIndex: 'email',
      render: (email: string) => (
        <Space>
          <span>{email}</span>
          <Tooltip title="复制">
            <CopyOutlined style={{ color: '#999', cursor: 'pointer' }} onClick={() => copyToClipboard(email)} />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '密码',
      width: 160,
      render: (_v, record) => (
        <Space>
          <span style={{ fontFamily: 'monospace' }}>
            {visiblePasswords.has(record.id) ? (passwordCache[record.id] || '...') : '••••••'}
          </span>
          <Tooltip title={visiblePasswords.has(record.id) ? '隐藏' : '显示'}>
            {visiblePasswords.has(record.id) ?
              <EyeInvisibleOutlined style={{ cursor: 'pointer' }} onClick={() => togglePassword(record.id)} /> :
              <EyeOutlined style={{ cursor: 'pointer' }} onClick={() => togglePassword(record.id)} />
            }
          </Tooltip>
          <Tooltip title="复制">
            <CopyOutlined
              style={{ color: '#999', cursor: 'pointer' }}
              onClick={async () => {
                const result = await mailboxesApi.batchCopy([record.id], 'password');
                await copyToClipboard(result.text);
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '分组',
      dataIndex: 'group_name',
      width: 120,
      render: (name: string | null) => <GroupTag name={name} />,
    },
    {
      title: '令牌状态',
      dataIndex: 'token_status',
      width: 100,
      render: (status: Mailbox['token_status']) => <TokenStatusComp status={status} />,
    },
    {
      title: '通道',
      dataIndex: 'channel',
      width: 70,
      render: (ch: string) => (
        <span style={{
          padding: '1px 6px', borderRadius: 3, fontSize: 11, fontWeight: 600,
          background: '#f6ffed', color: '#52c41a', border: '1px solid #b7eb8f',
        }}>
          {ch}
        </span>
      ),
    },
    {
      title: '操作',
      width: 140,
      render: (_v, record) => (
        <Space>
          <a onClick={() => setEmailViewer({ id: record.id, email: record.email })}>查看</a>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Toolbar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setShowImport(true)}>
          导入邮箱
        </Button>
        <Button icon={<DownloadOutlined />} onClick={handleExport}>导出备份</Button>
        <BatchCopyMenu selectedIds={selectedRowKeys} />
        <Button icon={<TagOutlined />} onClick={() => setShowGroupSelect(true)}>
          批量设置分组
        </Button>
        <Popconfirm
          title={`确认删除 ${selectedRowKeys.length} 个邮箱？`}
          onConfirm={handleBatchDelete}
          disabled={selectedRowKeys.length === 0}
        >
          <Button danger icon={<DeleteOutlined />} disabled={selectedRowKeys.length === 0}>
            批量删除
          </Button>
        </Popconfirm>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <Select
            style={{ width: 140 }}
            placeholder="全部分组"
            allowClear
            onChange={(v) => { setGroupFilter(v); pageRef.current.page = 1; }}
            options={groups.map(g => ({ label: g.name, value: g.id }))}
          />
          <Input.Search
            placeholder="搜索邮箱地址..."
            style={{ width: 220 }}
            allowClear
            onSearch={(v) => { setSearch(v); pageRef.current.page = 1; }}
          />
        </div>
      </div>

      {/* Data Grid */}
      <Table<Mailbox>
        columns={columns}
        dataSource={data.items}
        rowKey="id"
        loading={loading}
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys as string[]),
        }}
        pagination={{
          current: data.page,
          pageSize: data.page_size,
          total: data.total,
          showSizeChanger: true,
          pageSizeOptions: ['10', '20', '50'],
          showTotal: (total) => `共 ${total} 条 · 已选 ${selectedRowKeys.length} 条`,
          onChange: (page, pageSize) => {
            pageRef.current = { page, page_size: pageSize };
            loadData();
          },
        }}
      />

      {/* Modals */}
      <ImportModal open={showImport} onClose={() => setShowImport(false)} onSuccess={loadData} />
      <GroupSelect
        open={showGroupSelect}
        selectedIds={selectedRowKeys}
        onClose={() => setShowGroupSelect(false)}
        onSuccess={() => { setSelectedRowKeys([]); loadData(); }}
      />
      {emailViewer && (
        <EmailViewer
          open={!!emailViewer}
          mailboxId={emailViewer.id}
          email={emailViewer.email}
          onClose={() => setEmailViewer(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/MailboxList.tsx
git commit -m "feat: add MailboxList page with toolbar, data grid, and all modal integrations"
```

---

## Task 18: Integration Test & Polish

**Files:**
- Modify: various — verify everything works end-to-end

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Verify frontend compiles cleanly**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: Build succeeds, output in `frontend/dist/`

- [ ] **Step 3: Add `.gitignore` entry for `.superpowers/`**

Ensure `.superpowers/` is in `.gitignore` (already done in Task 1).

- [ ] **Step 4: Run full Docker Compose build (smoke test)**

Run from project root:
```bash
cp .env.example .env
# Generate a real encryption key:
python3 -c "import secrets, base64; print(f'ENCRYPTION_KEY={base64.b64encode(secrets.token_bytes(32)).decode()}')" >> .env
docker compose build
```
Expected: All 5 images build successfully.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: integration verification and build smoke test"
```
