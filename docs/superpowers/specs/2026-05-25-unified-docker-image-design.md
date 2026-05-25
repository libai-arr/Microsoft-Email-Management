# Unified Docker Image Design

## Goal

Consolidate three separate Docker images (`multi-mailbox-management-api`, `multi-mailbox-management-frontend`, `multi-mailbox-management-worker`) into a single unified image (`multi-mailbox-management`). PostgreSQL and Redis remain as separate containers.

## Architecture

### Current State

```
docker-compose.yml → 5 services
├── frontend   (nginx:alpine — serves static files, proxies /api/ to api service)
├── api        (python:3.12-slim — FastAPI/Uvicorn on port 8000)
├── worker     (python:3.12-slim — arq worker, same image as api)
├── postgres   (postgres:16-alpine)
└── redis      (redis:7-alpine)
```

Three custom images built: frontend, api (shared by api+worker).

### Target State

```
docker-compose.yml → 3 services
├── app        (unified image — nginx + uvicorn + arq worker via supervisord)
├── postgres   (postgres:16-alpine — unchanged)
└── redis      (redis:7-alpine — unchanged)
```

One custom image built. Externally exposes only port 80 (mapped to host 3000).

## Unified Dockerfile (Multi-Stage Build)

Location: project root `/Dockerfile`

### Stage 1: frontend-build

- Base: `node:20-alpine`
- Copy `frontend/package.json`, `frontend/package-lock.json`
- Run `npm install`
- Copy `frontend/` source
- Run `npm run build`
- Output: `/app/dist/` (static files)

### Stage 2: runtime

- Base: `python:3.12-slim`
- Install system packages: `nginx`, `supervisor` (via apt-get)
- Copy `backend/requirements.txt`, run `pip install --no-cache-dir`
- Copy `backend/` source to `/app/`
- Copy static files from Stage 1 (`/app/dist/`) to `/usr/share/nginx/html/`
- Copy `nginx.conf` to `/etc/nginx/conf.d/default.conf`
- Copy `supervisord.conf` to `/etc/supervisor/conf.d/supervisord.conf`
- Remove default nginx site config
- Expose port 80
- CMD: `supervisord -c /etc/supervisor/conf.d/supervisord.conf`

## supervisord Configuration

File: project root `/supervisord.conf`

Manages three processes:

| Program | Command | Notes |
|---------|---------|-------|
| nginx | `nginx -g "daemon off;"` | Serves static files, reverse proxies `/api/` |
| api | `uvicorn app.main:app --host 127.0.0.1 --port 8000` | Internal only, not exposed externally |
| worker | `python -m arq app.worker.tasks.WorkerSettings` | Background task processing |

All processes:
- `autorestart=true` — auto-recover from crashes
- `stdout_logfile=/dev/stdout`, `stderr_logfile=/dev/stderr` — logs visible via `docker logs`
- `stdout_logfile_maxbytes=0`, `stderr_logfile_maxbytes=0` — disable log rotation (required for `/dev/stdout` redirect)
- `nodaemon=true` on supervisord — runs in foreground for Docker

## nginx Configuration Changes

Current (`frontend/nginx.conf`):
```nginx
location /api/ {
    proxy_pass http://api:8000;
}
```

New (`nginx.conf` at project root):
```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
}
```

Only change: `api` → `127.0.0.1` (same container, no Docker network resolution needed). All other directives (headers, try_files) remain unchanged.

## docker-compose.yml Changes

Replace `frontend`, `api`, `worker` services with single `app` service:

```yaml
services:
  app:
    build: .
    ports:
      - "3000:80"
    env_file: .env
    environment:
      HTTPS_PROXY: http://host.docker.internal:7897
      HTTP_PROXY: http://host.docker.internal:7897
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
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-mailbox} -d ${POSTGRES_DB:-mailbox_db}"]
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

## .dockerignore Update

Updated for root-level build context:

```
.git
.env
*.db
node_modules
frontend/node_modules
__pycache__
*.pyc
.DS_Store
docs
.claude
.superpowers
```

## Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `Dockerfile` | Create | Root-level multi-stage unified Dockerfile |
| `supervisord.conf` | Create | Process manager configuration |
| `nginx.conf` | Create | Copy from frontend/nginx.conf, change proxy_pass to 127.0.0.1 |
| `docker-compose.yml` | Modify | Replace 3 app services with 1 `app` service |
| `.dockerignore` | Modify | Adapt for root-level build context |
| `backend/Dockerfile` | Keep | Retained for standalone backend dev use |
| `frontend/Dockerfile` | Keep | Retained for standalone frontend dev use |

## Startup Behavior

Container always starts all three processes (nginx, api, worker) simultaneously via supervisord. No per-role mode switching.

## Port Mapping

| Before | After |
|--------|-------|
| `3000:80` (frontend/nginx) | `3000:80` (unified app) |
| `8000:8000` (api/uvicorn) | Not exposed externally |
| `5432:5432` (postgres) | `5432:5432` (unchanged) |
| `6379:6379` (redis) | `6379:6379` (unchanged) |
