# 多邮箱管理系统 — 技术设计文档

## 1. 概述

集中管理多个 Outlook 邮箱账号的内部运维工具。支持批量导入、状态监控、凭证提取、邮件在线查看，实现自动化的邮箱资产管理。

**核心决策：**
- 前端：React 18 + TypeScript + Ant Design 5 + Vite
- 后端：Python 3.12 + FastAPI + SQLAlchemy + Uvicorn
- 数据库：PostgreSQL 16
- 任务队列：ARQ + Redis 7
- 邮件API：Microsoft Graph API（通过 MSAL + httpx）
- 部署：Docker Compose（5 个服务）
- UI 语言：中文
- 系统认证：无（内部/本地工具）

## 2. 系统架构

### 2.1 服务拓扑

```
┌──────────────────────────────────────────────────────────┐
│                   Docker Compose                         │
│                                                          │
│  ┌──────────┐   HTTP /api/*   ┌──────────┐              │
│  │ frontend │ ───────────────→│   api    │              │
│  │ (Nginx)  │                 │(FastAPI) │              │
│  │ :3000    │                 │ :8000    │              │
│  └──────────┘                 └────┬─────┘              │
│                                    │                     │
│                          ┌─────────┴──────────┐         │
│                          │                    │          │
│                    ┌─────▼────┐         ┌─────▼────┐    │
│                    │ postgres │         │  redis   │    │
│                    │  :5432   │         │  :6379   │    │
│                    └─────▲────┘         └─────▲────┘    │
│                          │                    │          │
│                    ┌─────┴────────────────────┘         │
│                    │                                     │
│                 ┌──▼─────┐                              │
│                 │ worker  │                              │
│                 │ (ARQ)   │                              │
│                 └─────────┘                              │
└──────────────────────────────────────────────────────────┘
```

### 2.2 容器职责

| 服务 | 镜像 | 端口 | 职责 |
|------|------|------|------|
| frontend | node:20 → nginx:alpine | 3000:80 | Vite 多阶段构建，Nginx 静态服务 + API 反向代理 |
| api | python:3.12-slim | 8000:8000 | FastAPI REST API，加密服务，Graph API 客户端 |
| worker | python:3.12-slim | — | ARQ 后台任务：令牌心跳检测 |
| postgres | postgres:16-alpine | 5432:5432 | 核心数据存储，持久化 volume |
| redis | redis:7-alpine | 6379:6379 | ARQ 任务队列 + Access Token 短期缓存 |

### 2.3 关键数据流

**导入流程：**
用户输入 → 前端逐行解析校验（4 字段） → POST /api/mailboxes/import → 后端 AES-256-GCM 加密凭证 → 写入 PostgreSQL

**令牌心跳：**
Worker 定时扫描 → 标记 "checking" → 解密 refresh_token → MSAL 刷新 → 成功：status="normal" + 缓存 access_token 到 Redis；失败：status="expired" → 前端 30 秒轮询展示

**邮件查看：**
点击"查看" → GET /api/mailboxes/{id}/emails → 后端解密 token → 调用 Graph API → 懒加载分页返回 → 前端 HTML 安全渲染（sandbox iframe）

## 3. 数据模型

### 3.1 mailboxes（核心表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | gen_random_uuid() |
| email | VARCHAR(255) | 唯一索引，支持模糊搜索 |
| password_encrypted | BYTEA | AES-256-GCM 密文 |
| client_id_encrypted | BYTEA | Azure AD Client ID 密文 |
| refresh_token_encrypted | BYTEA | OAuth2.0 Refresh Token 密文 |
| group_id | UUID (FK → groups.id) | 可为 NULL（= 默认分组） |
| token_status | VARCHAR(20) | normal / checking / expired |
| channel | VARCHAR(20) | 默认 "O2"（OAuth2.0） |
| token_checked_at | TIMESTAMPTZ | 最后心跳检查时间 |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| updated_at | TIMESTAMPTZ | 触发器自动更新 |

### 3.2 groups（分组表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | gen_random_uuid() |
| name | VARCHAR(100) | 唯一 |
| description | TEXT | 可选 |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### 3.3 audit_logs（审计日志表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL (PK) | 自增 |
| action | VARCHAR(50) | batch_copy / batch_export / batch_delete / import_overwrite |
| target_count | INTEGER | 操作涉及的记录数 |
| detail | JSONB | 受影响的邮箱 ID 列表等 |
| ip_address | INET | 操作来源 IP |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### 3.4 设计决策

- 邮件数据不存储在数据库中 — 每次通过 Graph API 实时拉取
- Access Token 缓存在 Redis（TTL 50 分钟），避免重复刷新
- 加密密钥通过环境变量 ENCRYPTION_KEY 注入，不存储在数据库或代码中
- audit_logs 与 mailboxes 松耦合（JSONB detail，无 FK），邮箱删除后审计记录保留
- email 字段唯一索引，导入时遇到已存在的邮箱地址则跳过该行（不覆盖已有记录），并在导入结果中报告跳过数量

## 4. API 设计

### 4.1 邮箱管理 `/api/mailboxes`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/mailboxes | 分页查询列表。Query: page, page_size, search, group_id |
| POST | /api/mailboxes/import | 批量导入。Body: { items: [...], mode: "append" \| "overwrite" } |
| POST | /api/mailboxes/export | 导出 CSV/Excel。Body: { ids?, format, include_all? } |
| DELETE | /api/mailboxes/batch | 批量删除。Body: { ids: uuid[] } |
| PATCH | /api/mailboxes/batch/group | 批量设置分组。Body: { ids, group_id } |
| POST | /api/mailboxes/batch/copy | 批量获取复制数据。Body: { ids, type: "email" \| "password" \| "combined" } |
| DELETE | /api/mailboxes/{id} | 删除单个邮箱 |

### 4.2 分组管理 `/api/groups`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/groups | 获取所有分组（含邮箱计数） |
| POST | /api/groups | 创建分组。Body: { name, description? } |
| PUT | /api/groups/{id} | 更新分组 |
| DELETE | /api/groups/{id} | 删除分组（邮箱回归默认分组） |

### 4.3 邮件查看 `/api/mailboxes/{id}/emails`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/mailboxes/{id}/emails | 邮件列表（懒加载）。Query: folder=inbox\|junk, page, page_size, search |
| GET | /api/mailboxes/{id}/emails/{message_id} | 单封邮件 HTML 正文（已 sanitize） |

### 4.4 令牌状态 `/api/tokens`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/tokens/status | 批量获取状态。Query: ids=uuid1,uuid2,... |
| POST | /api/tokens/check | 手动触发检查（异步入队）。Body: { ids } |

### 4.5 API 设计决策

- batch/copy 返回拼接文本 — 密码解密在后端完成，前端仅写入剪贴板
- export 使用 POST — 需要传递可能很长的 ID 列表
- 邮件接口不做缓存 — 每次实时调用 Graph API 确保最新
- 令牌状态前端轮询间隔 30 秒
- 所有敏感操作自动记录 audit_logs
- 邮件正文返回前 HTML sanitize（移除 script/iframe/事件处理器）

## 5. 前端设计

### 5.1 技术栈

- React 18 + TypeScript
- Ant Design 5（ProTable, Modal, Tabs, Tag, Badge, Dropdown, Popconfirm）
- Vite 构建
- axios HTTP 客户端

### 5.2 页面结构

单页应用，一个主页面 `MailboxList`，功能通过模态框承载。

### 5.3 邮箱管理主列表

核心工作台页面，包含：

**工具栏：** 导入邮箱（primary 按钮）、导出备份、批量复制（Dropdown 级联菜单：复制账号/复制密码/复制账号----密码）、批量设置分组、批量删除（danger 按钮）。右侧：分组下拉筛选 + 邮箱地址模糊搜索框。

**数据网格（ProTable）：**

| 列 | 组件 | 交互 |
|----|------|------|
| 多选框 | Checkbox | 全选/单选 |
| # | 自动序号 | 基于分页自动生成 |
| 邮箱地址 | 文本 + 复制图标 | 点击图标复制到剪贴板 |
| 密码 | 密文 + 显隐切换 + 复制图标 | 默认 •••••• 显示 |
| 分组 | Tag | 不同分组不同颜色 |
| 令牌状态 | 自定义 StatusDot | 绿=正常，黄=检测中，红=失效 |
| 通道 | Badge | 显示 "O2" 标识 |
| 操作 | Button Group | 查看、删除（Popconfirm）、更多(... → 编辑分组、手动检测令牌) |

**分页：** 底部显示总条数、已选条数。支持每页 10/20/50 条切换、上下页跳转、直接输入页码。

### 5.4 导入模态框

Ant Design Modal，内含两个 Tab：

**文本录入 Tab：**
- 格式提示区：展示格式 A（空格/Tab 分隔）和格式 B（四连减号分隔）
- 带行号的 TextArea，monospace 字体
- 提交时前端逐行解析校验，检查每行是否包含 4 个必要字段
- 校验失败：红色 Alert 显示错误行号和原因，阻断提交
- 支持混合格式 A 和 B

**文件上传 Tab：**
- Upload.Dragger 拖拽上传区
- 支持 .txt / .csv 文件
- 上传后同样执行前端校验

**底部按钮：** 取消 / 追加导入（primary）/ 覆盖导入（warning，触发 Popconfirm 高危确认）

### 5.5 邮件在线查看器

大号 Modal（宽度 90vw, 高度 80vh），左右分栏布局：

**左侧（340px 固定宽度）：**
- 顶部显示当前邮箱：`邮件列表 — [email]`
- Tabs：收件箱（Inbox）/ 垃圾箱（Junk），各带邮件数量 badge
- 搜索框：按发件人、主题即时过滤
- 刷新按钮：异步调用 Graph API 拉取最新邮件
- 邮件卡片列表：发件人、主题、首行摘要、时间戳，active/unread 状态样式

**右侧（自适应宽度）：**
- 缺省状态：居中浅灰色提示 "请从左侧选择一封邮件查看"
- 激活状态：邮件主题、发件人头像/名称/地址、时间、HTML 正文渲染
- 验证码自动识别：匹配 4-8 位数字验证码，高亮显示 + "一键复制"按钮
- 链接安全跳转：target="_blank" + rel="noopener noreferrer"

**安全渲染：** 后端使用 bleach 库过滤 HTML（移除 script/iframe/on* 事件处理器）。前端通过 sandbox iframe 二次隔离渲染。

### 5.6 前端组件清单

| 组件 | 文件 | 职责 |
|------|------|------|
| MailboxList | pages/MailboxList.tsx | 主列表页（工具栏 + ProTable + 分页） |
| ImportModal | components/ImportModal.tsx | 导入模态框（文本录入 + 文件上传） |
| EmailViewer | components/EmailViewer.tsx | 邮件查看大号模态框 |
| BatchCopyMenu | components/BatchCopyMenu.tsx | 批量复制下拉菜单 |
| TokenStatus | components/TokenStatus.tsx | 令牌状态灯组件 |
| GroupTag | components/GroupTag.tsx | 分组标签（颜色映射） |

### 5.7 自定义 Hooks

| Hook | 文件 | 职责 |
|------|------|------|
| useMailboxes | hooks/useMailboxes.ts | 列表数据获取 + 分页 + 搜索 + 筛选 |
| useTokenStatus | hooks/useTokenStatus.ts | 30 秒轮询令牌状态 |
| useEmails | hooks/useEmails.ts | 邮件列表 + 正文获取 |

## 6. 后台服务

### 6.1 令牌心跳检测流程

ARQ Worker 定时任务，每 5 分钟一轮：

1. **扫描目标** — 查询 token_checked_at 超过 5 分钟或 token_status="expired" 的邮箱批次
2. **标记检测中** — 批量更新 token_status="checking"，前端轮询立即展示黄灯
3. **解密 & 刷新** — 解密 refresh_token，调用 MSAL 换取新 access_token。并发限制 10 个/秒，防止 Graph API 限流
4. **更新状态** — 成功：status="normal" + 缓存 access_token 到 Redis（TTL 50min）；失败：status="expired"

### 6.2 加密方案

- 算法：AES-256-GCM（认证加密，防篡改）
- 实现：Python `cryptography` 库
- 密钥管理：ENCRYPTION_KEY 环境变量注入，base64 编码 32 字节
- 加密字段：password、client_id、refresh_token
- 每次加密生成随机 nonce，存储格式：nonce + ciphertext + tag

## 7. 环境配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| ENCRYPTION_KEY | （必填） | AES-256 加密主密钥，base64 编码 32 字节 |
| DATABASE_URL | postgresql://user:pass@postgres:5432/mailbox_db | PostgreSQL 连接字符串 |
| REDIS_URL | redis://redis:6379/0 | Redis 连接 |
| TOKEN_CHECK_INTERVAL | 300 | 令牌心跳检测间隔（秒） |
| TOKEN_CHECK_CONCURRENCY | 10 | 令牌刷新并发数上限 |
| ACCESS_TOKEN_CACHE_TTL | 3000 | Access Token Redis 缓存 TTL（秒） |
| FRONTEND_POLL_INTERVAL | 30 | 前端令牌状态轮询间隔（秒） |

## 8. 项目目录结构

```
multi-mailbox-management/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── migrations/
│   └── app/
│       ├── main.py                  # FastAPI 入口
│       ├── config.py                # 环境变量配置
│       ├── api/
│       │   ├── mailboxes.py         # 邮箱 CRUD + 批量操作
│       │   ├── groups.py            # 分组管理
│       │   ├── emails.py            # 邮件查看代理
│       │   └── tokens.py            # 令牌状态接口
│       ├── models/
│       │   ├── mailbox.py           # SQLAlchemy 模型
│       │   ├── group.py
│       │   └── audit_log.py
│       ├── services/
│       │   ├── crypto.py            # AES-256 加解密
│       │   ├── graph_client.py      # Microsoft Graph API
│       │   ├── mail_sanitizer.py    # HTML 净化
│       │   └── import_parser.py     # 导入数据解析
│       └── worker/
│           ├── tasks.py             # ARQ 后台任务
│           └── token_checker.py     # 心跳检测逻辑
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── vite.config.ts
    ├── package.json
    └── src/
        ├── App.tsx
        ├── main.tsx
        ├── pages/
        │   └── MailboxList.tsx
        ├── components/
        │   ├── ImportModal.tsx
        │   ├── EmailViewer.tsx
        │   ├── BatchCopyMenu.tsx
        │   ├── TokenStatus.tsx
        │   └── GroupTag.tsx
        ├── hooks/
        │   ├── useMailboxes.ts
        │   ├── useTokenStatus.ts
        │   └── useEmails.ts
        ├── services/
        │   └── api.ts               # axios 封装
        └── utils/
            ├── importParser.ts      # 前端导入校验
            └── clipboard.ts         # 剪贴板操作
```

## 9. 安全措施

- **凭证加密：** 密码、Client_ID、Refresh Token 使用 AES-256-GCM 密文存储，严禁明文落库
- **密钥隔离：** 加密密钥仅通过环境变量注入，不进入代码仓库或数据库
- **审计日志：** 批量复制、导出、删除、覆盖导入等敏感操作全程记录（action + target_count + detail + IP）
- **邮件渲染安全：** 后端 bleach 过滤 + 前端 sandbox iframe 双重隔离，防止 XSS
- **链接安全：** 邮件内链接统一添加 target="_blank" + rel="noopener noreferrer"
- **导入校验：** 前端逐行解析校验 4 字段完整性，后端二次校验，防止非法数据入库
