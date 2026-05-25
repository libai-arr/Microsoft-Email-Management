# Unified Docker Image Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate three Docker images (frontend, api, worker) into one unified image using multi-stage build and supervisord.

**Architecture:** A single multi-stage Dockerfile builds the frontend (Node) in stage 1, then copies the static assets into a Python-based runtime image that runs nginx, uvicorn, and arq worker via supervisord. PostgreSQL and Redis remain as separate containers.

**Tech Stack:** Docker multi-stage build, supervisord, nginx, Python 3.12, Node 20

**Spec:** `docs/superpowers/specs/2026-05-25-unified-docker-image-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `nginx.conf` (root) | Create | nginx config for unified container — proxies `/api/` to `127.0.0.1:8000` |
| `supervisord.conf` (root) | Create | Manages nginx, uvicorn, arq worker processes |
| `Dockerfile` (root) | Create | Multi-stage build: frontend assets + Python runtime + nginx + supervisor |
| `.dockerignore` (root) | Modify | Adapt exclusions for root-level build context |
| `docker-compose.yml` (root) | Modify | Replace frontend/api/worker services with single `app` service |

Existing `backend/Dockerfile` and `frontend/Dockerfile` are retained untouched for standalone dev use.

---

### Task 1: Create root nginx.conf

**Files:**
- Create: `nginx.conf`

This is a copy of `frontend/nginx.conf` with `proxy_pass` changed from Docker service name to localhost.

- [ ] **Step 1: Create `nginx.conf` at project root**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Only difference from `frontend/nginx.conf`: `http://api:8000` → `http://127.0.0.1:8000`.

- [ ] **Step 2: Commit**

```bash
git add nginx.conf
git commit -m "feat: add root nginx.conf for unified container"
```

---

### Task 2: Create supervisord.conf

**Files:**
- Create: `supervisord.conf`

- [ ] **Step 1: Create `supervisord.conf` at project root**

```ini
[supervisord]
nodaemon=true
logfile=/var/log/supervisord.log
pidfile=/var/run/supervisord.pid

[program:nginx]
command=nginx -g "daemon off;"
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:api]
command=uvicorn app.main:app --host 127.0.0.1 --port 8000
directory=/app
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:worker]
command=python -m arq app.worker.tasks.WorkerSettings
directory=/app
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

Key details:
- `nodaemon=true` keeps supervisord in foreground (required for Docker)
- All three programs set `autorestart=true` for crash recovery
- `stdout_logfile_maxbytes=0` disables log rotation (required when redirecting to `/dev/stdout`)
- `directory=/app` for api and worker so Python finds the `app` package

- [ ] **Step 2: Commit**

```bash
git add supervisord.conf
git commit -m "feat: add supervisord config for unified container"
```

---

### Task 3: Create unified Dockerfile

**Files:**
- Create: `Dockerfile`

- [ ] **Step 1: Create `Dockerfile` at project root**

```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Runtime
FROM python:3.12-slim

# Install nginx and supervisor
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx supervisor && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/nginx/sites-enabled/default

# Install Python dependencies
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Copy frontend build output
COPY --from=frontend-build /app/dist /usr/share/nginx/html

# Copy nginx and supervisor configs
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

Key details:
- Stage 1 copies `frontend/package.json` first for Docker layer caching, then copies source and builds
- Stage 2 uses `python:3.12-slim` (Debian-based, so `apt-get` works for nginx/supervisor)
- `rm -f /etc/nginx/sites-enabled/default` removes the default nginx welcome page that would conflict with our config
- `WORKDIR /app` matches what the current `backend/Dockerfile` uses
- Backend source is copied directly into `/app/` (not `/app/backend/`) so `app.main:app` and `app.worker.tasks.WorkerSettings` resolve correctly

- [ ] **Step 2: Commit**

```bash
git add Dockerfile
git commit -m "feat: add unified multi-stage Dockerfile"
```

---

### Task 4: Update .dockerignore

**Files:**
- Modify: `.dockerignore`

- [ ] **Step 1: Update `.dockerignore` for root-level build context**

Replace the current contents with:

```
.git/
.gitignore

__pycache__/
*.py[cod]
.venv/
*.egg-info/

node_modules/
frontend/node_modules/

.env

.idea/
.vscode/
*.swp

.superpowers/
.claude/

.DS_Store

*.db
docs/
```

Changes from original:
- Removed `dist/` and `frontend/dist/` exclusions — `dist/` at root doesn't exist, and `frontend/dist/` is rebuilt inside Docker so excluding it is fine, but the build copies `frontend/` source into the container where `npm run build` produces the dist. The exclusion of `frontend/dist/` avoids copying any stale local build artifacts.
- Added `*.db` to exclude `backend/test.db`
- Added `docs/` to exclude documentation from the image

- [ ] **Step 2: Commit**

```bash
git add .dockerignore
git commit -m "chore: update .dockerignore for unified build context"
```

---

### Task 5: Update docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Replace docker-compose.yml contents**

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

Changes:
- Removed `frontend`, `api`, `worker` services
- Added single `app` service that builds from root Dockerfile
- Only exposes port `3000:80` (no more `8000:8000`)
- `env_file` and `environment` (proxy settings) carried over from the old `api` service
- `depends_on` for postgres (healthy) and redis (started) carried over

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: consolidate to single app service in docker-compose"
```

---

### Task 6: Build and verify

- [ ] **Step 1: Build the unified image**

```bash
docker compose build
```

Expected: Build completes successfully. Stage 1 builds frontend, Stage 2 installs nginx/supervisor/Python deps, copies everything.

- [ ] **Step 2: Start all services**

```bash
docker compose up -d
```

Expected: Three containers start — `app`, `postgres`, `redis`.

- [ ] **Step 3: Verify container is running with all processes**

```bash
docker compose exec app supervisorctl status
```

Expected output (all three RUNNING):
```
api                              RUNNING   pid XX, uptime X:XX:XX
nginx                            RUNNING   pid XX, uptime X:XX:XX
worker                           RUNNING   pid XX, uptime X:XX:XX
```

- [ ] **Step 4: Verify frontend is served**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/
```

Expected: `200`

- [ ] **Step 5: Verify API proxy works**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/docs
```

Expected: `200` (FastAPI's built-in docs endpoint). A `502` would indicate nginx cannot reach uvicorn.

- [ ] **Step 6: Verify only one custom image was built**

```bash
docker images | grep multi-mailbox-management
```

Expected: Only one image listed (e.g., `multi-mailbox-management-app`).

- [ ] **Step 7: Stop services**

```bash
docker compose down
```

- [ ] **Step 8: Final commit (if any adjustments were needed)**

```bash
git add -A
git commit -m "feat: unified Docker image with supervisord"
```
