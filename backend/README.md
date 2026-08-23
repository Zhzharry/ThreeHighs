# 后端说明

这里放 Flask 后端代码，负责 RESTful API、数据库读写、OCR、预测模型、大模型问答和管理员数据维护。

## 目录

```text
backend/
├── app/
│   ├── api/          # Flask-RESTful 接口资源，按页面功能拆分
│   │   ├── auth/     # 登录接口
│   │   ├── daily/    # 每日记录页面接口
│   │   ├── reports/  # 体检报告上传和 OCR 接口
│   │   ├── ai/       # AI 对话页面接口
│   │   ├── mine/     # 我的页面接口
│   │   └── admin/    # 管理员端接口
│   ├── models/       # SQLAlchemy 数据模型，对应 docs/数据库设计.md
│   ├── services/     # 演示数据、OCR、预测、大模型、向量库等服务
│   ├── config.py
│   └── extensions.py
├── tests/            # pytest 测试
├── requirements.txt
├── Dockerfile
└── run.py
```

## 本地运行

```powershell
cd "D:\study\vscode\大作业\backend"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:AUTO_CREATE_TABLES = "false"
flask --app run.py db upgrade
python run.py
```

数据库结构由 `backend/migrations` 中的 Flask-Migrate/Alembic 版本管理。执行
迁移命令时必须关闭兼容自动建表，否则空数据库会在 Alembic 执行前被提前建表。
当前课程本地运行仍保留 `AUTO_CREATE_TABLES=true` 兼容模式；Docker 入口固定先执行
`db upgrade`，并默认关闭自动建表。

模型调整后的开发流程：

```powershell
$env:AUTO_CREATE_TABLES = "false"
flask --app run.py db migrate -m "说明本次结构变化"
flask --app run.py db upgrade
flask --app run.py db check
```

迁移文件生成后必须人工审查并提交，不能只依赖 `db.create_all()`。不要对结构未知的
旧数据库直接执行 `stamp`；`stamp` 只记录版本，不会实际修改表结构。

测试接口：

```text
http://localhost:5000/api/v1/health
```

常用接口：

```text
GET  /api/v1/daily-records/today
GET  /api/v1/me/profile
GET  /api/v1/ai/conversations
GET  /api/v1/reports/history
GET  /api/v1/admin/users
GET  /api/v1/admin/users/{user_id}
PUT  /api/v1/admin/users/{user_id}
PATCH /api/v1/admin/reports/batch-review
POST /api/v1/admin/foods/batch-delete
PATCH /api/v1/admin/announcements/batch-publish
```

管理后台登录：

```text
POST /api/v1/auth/admin-login
```

本地开发账号为 `admin / admin123`。生产环境必须配置 `ADMIN_USERNAME` 和
`ADMIN_PASSWORD_HASH`，明文 `ADMIN_PASSWORD` 只用于本地开发。所有
`/api/v1/admin/*` 接口始终要求管理员 Token，不受 `AUTH_REQUIRED` 开关影响。

## 当前实现说明

- 第一版接口按 `docs/api.md` 实现，返回格式统一为 `{ code, message, data }`。
- 全部业务接口已拆分到正式 SQLAlchemy Repository，直接读写领域表；`app_state` 仅保留跨版本升级所需的6个迁移完成标记，不再保存业务数据或自增计数器。
- `app/models` 已按 `docs/数据库设计.md` 建立 SQLAlchemy 模型，`migrations` 已包含初始结构和七次后续迁移，当前版本头为 `9c2f7e8a1b34`。确认所有已部署旧环境完成升级后，可在后续独立版本删除空兼容表。
- 待办事项已按“模板版本 + 每日快照”实现：修改待办后，只影响修改日期及之后的记录，历史日期不被覆盖。
- 健康检查会执行数据库 `SELECT 1`，只有依赖可用时才返回 `status=ready`。
- API 返回请求追踪 ID、禁止缓存和常用安全响应头；登录接口与普通接口使用 Redis 共享限流。
- 微信登录支持本地 mock 与生产 `code2session` 两种显式模式；正式模式按 openid/unionid 建立用户、记录登录审计，并通过令牌版本实现退出及管理员停用后的即时撤销。
- `APP_ENV=production` 时会检查密钥、鉴权、数据库账号、CORS、管理员密码哈希、微信 AppID/AppSecret、令牌版本和限流存储，发现演示配置会拒绝启动。
- Gunicorn worker/线程/超时均通过环境变量配置，上传目录由 Docker 持久卷保存。

接口说明见：`docs/api.md`。

本地未设置 `DATABASE_URL` 时使用 `backend/storage/three_high_health.db`；Docker 环境使用 MySQL。`DOMAIN_REPOSITORIES_ENABLED=true` 启用已经完成的领域 Repository 和旧数据一次性导入。设置 `AUTH_REQUIRED=true` 后，除健康检查和登录外的普通业务接口都必须携带 Bearer Token；管理员接口始终强制鉴权并校验管理员角色。

生产部署的完整变量、密码哈希生成方式、HTTPS/域名和微信平台配置见 `docs/上线部署清单.md`。
