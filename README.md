# 多邮箱管理系统

批量管理 Microsoft 365 邮箱的 Web 应用，支持邮箱导入、分组管理、令牌健康检查和邮件查看。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design 5 + Vite |
| 后端 | FastAPI + SQLAlchemy 2 (async) + Pydantic |
| 数据库 | PostgreSQL 16 |
| 缓存/队列 | Redis 7 + ARQ |
| 邮件接口 | Microsoft Graph API (MSAL) |
| 部署 | Docker Compose |

## 功能

- **邮箱导入** — 支持 Excel/CSV 批量导入，自动解析多种格式
- **分组管理** — 按分组组织邮箱，支持批量设置
- **令牌检查** — 后台定时检测 refresh token 有效性，状态实时展示
- **邮件查看** — 收件箱 / 垃圾邮件 / 全部邮件三栏浏览，HTML 内容安全渲染
- **批量操作** — 批量复制（邮箱、密码、Token）、批量删除、导出 CSV
- **凭据加密** — 密码、Client ID、Refresh Token 使用 AES 加密存储

## 快速开始

### 前置要求

- Docker & Docker Compose

### 启动

```bash
# 1. 复制环境变量
cp .env.example .env

# 2. 生成加密密钥并填入 .env 的 ENCRYPTION_KEY
python3 -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"

# 3. 设置访问密码（必填）
# APP_SHARED_PASSWORD=your-password

# 4. 启动所有服务
docker compose up -d --build
```

启动后访问 http://localhost:3000。

### 服务端口

| 服务 | 端口 |
|------|------|
| Web 应用 | 3000 |
| PostgreSQL | Compose 内网 |
| Redis | Compose 内网 |

## 项目结构

```
├── frontend/                # React 前端
│   └── src/
│       ├── components/      # UI 组件（EmailViewer, ImportModal 等）
│       ├── hooks/           # 自定义 Hooks
│       ├── pages/           # 页面（MailboxList）
│       ├── services/        # API 调用
│       ├── types/           # TypeScript 类型定义
│       └── utils/           # 工具函数
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # 路由（mailboxes, emails, groups, tokens, batch）
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── schemas/         # Pydantic 校验模型
│   │   ├── services/        # 业务逻辑（加密、Graph 客户端、邮件清洗）
│   │   └── worker/          # ARQ 后台任务（令牌检查）
│   ├── migrations/          # Alembic 数据库迁移
│   └── tests/               # pytest 测试
└── docker-compose.yml
```

## API 概览

| 模块 | 路径 | 说明 |
|------|------|------|
| 邮箱 | `POST /api/mailboxes/import` | 导入邮箱 |
| 邮箱 | `GET /api/mailboxes` | 分页查询（支持搜索、分组过滤） |
| 邮箱 | `DELETE /api/mailboxes/{id}` | 删除邮箱 |
| 邮件 | `GET /api/mailboxes/{id}/emails` | 获取邮件列表 |
| 分组 | `GET/POST/DELETE /api/groups` | 分组 CRUD |
| 令牌 | `GET /api/tokens/status` | 查询令牌状态 |
| 批量 | `POST /api/mailboxes/batch/copy` | 批量复制信息 |
| 批量 | `POST /api/mailboxes/batch/delete` | 批量删除 |

API 文档：容器内 API 由 nginx 代理提供，对外统一走 http://localhost:3000/api。

## 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev

# 测试
cd backend
pytest
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ENCRYPTION_KEY` | AES 加密密钥（必填） | — |
| `APP_SHARED_PASSWORD` | 访问系统时输入的共享密码（必填） | — |
| `APP_SHARED_PASSWORD_SESSION_TTL` | 访问会话有效期（秒） | `43200` |
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://mailbox:mailbox_pass@postgres:5432/mailbox_db` |
| `REDIS_URL` | Redis 连接地址 | `redis://redis:6379/0` |
| `TOKEN_CHECK_INTERVAL` | 令牌检查间隔（秒） | `300` |
| `TOKEN_CHECK_CONCURRENCY` | 令牌检查并发数 | `10` |
| `ACCESS_TOKEN_CACHE_TTL` | Access Token 缓存时间（秒） | `3000` |

## 上传 GitHub 前检查

- 不要提交真实 `.env`、`backend/.env`
- 不要提交本地数据库文件：`*.db`、`*.sqlite*`
- 不要提交 Office 临时文件：`~$*`
- 检查是否存在不该公开的本地工具产物（如 `.superpowers/`）
- 推送前先运行 `git status --short` 确认工作区内容符合预期

## 服务器部署（Docker Compose）

1. 将仓库上传到 GitHub 后，在服务器上拉取代码。
2. 复制环境变量模板：
   ```bash
   cp .env.example .env
   ```
3. 填写以下生产配置：
   - `ENCRYPTION_KEY`：使用随机生成的 32 字节 base64 密钥
   - `APP_SHARED_PASSWORD`：设置强密码
   - `POSTGRES_PASSWORD`：不要使用默认值
   - 如有需要，再调整 `DATABASE_URL`、`REDIS_URL`
4. 启动服务：
   ```bash
   docker compose up -d --build
   ```
5. 验证：
   - 打开 `http://<服务器IP或域名>:3000`
   - 应先看到访问密码页
   - 输入正确共享密码后进入系统
   - 未授权直接访问 `/api/*` 应返回 401
