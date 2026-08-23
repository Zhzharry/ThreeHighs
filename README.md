# 三高健康管理小程序

这是一个前后端分离的三高健康管理微信小程序。小程序页面已接入 Flask RESTful API、MySQL、Redis 限流和正式领域 Repository；文档集中放在 `docs` 目录，便于开发、验收和上线交接。

## 一眼看懂目录

```text
大作业/
├── frontend/                 # 前端代码
│   ├── miniprogram/          # 微信小程序源码
│   │   ├── pages/            # 小程序页面
│   │   ├── services/         # wx.request API 封装
│   │   └── assets/           # 图片、图标、公共样式等前端资源
│   └── preview/              # 历史浏览器预览源码，默认不再启动或作为验收入口
├── backend/                  # 后端代码
│   ├── app/
│   │   ├── api/              # Flask-RESTful 接口
│   │   ├── models/           # SQLAlchemy 数据模型
│   │   └── services/         # OCR、预测、大模型、向量库服务
│   ├── tests/                # pytest 测试
│   └── requirements.txt
├── docs/                     # 文档
│   ├── api.md                # API 接口文档
│   ├── 需求分析.md
│   └── 项目结构说明.md
├── docker-compose.yml
└── project.config.json       # 微信开发者工具配置
```

## 前端代码在哪里

```text
frontend/miniprogram
```

页面代码：

- 每日记录：`frontend/miniprogram/pages/daily`
- AI：`frontend/miniprogram/pages/ai`
- 我的：`frontend/miniprogram/pages/mine`

旧的模块页面文件仍保留在 `frontend/miniprogram/pages` 中，后续可以继续拆分复用，但当前小程序主入口只展示这三个底部导航页面。

前端 API 封装：

```text
frontend/miniprogram/services/api.js
```

## 后端代码在哪里

```text
backend
```

后端接口入口：

```text
backend/app/api
```

后端服务模块：

```text
backend/app/services
```

后端数据模型：

```text
backend/app/models
```

## API 文档在哪里

```text
docs/api.md
```

后端基础地址：

```text
http://localhost:5000/api/v1
```

健康检查接口：

```text
http://localhost:5000/api/v1/health
```

## 前端资源放哪里

```text
frontend/miniprogram/assets
```

- 图片：`frontend/miniprogram/assets/images`
- 图标：`frontend/miniprogram/assets/icons`
- 公共样式：`frontend/miniprogram/assets/styles`

当前版本主要用 WXSS 实现界面，还没有额外图片素材。

## 微信开发者工具运行

1. 打开微信开发者工具。
2. 选择“导入项目”。
3. 项目目录选择：`D:\study\vscode\大作业`。
4. AppID 使用你当前配置的 AppID，或选择测试号。
5. 编译后即可看到小程序页面。

需要执行开发者工具内的自动化冒烟测试时：

```powershell
npm install
& "微信开发者工具安装目录\cli.bat" auto --project "D:\study\vscode\大作业" --auto-port 9420 --trust-project
npm run test:miniprogram
```

测试会在真实小程序运行实例中验证授权、隐私政策、每日记录、AI、我的、个人数据导出、授权撤回和重新授权恢复；不会访问浏览器预览。

`project.config.json` 已经配置：

```json
{
  "miniprogramRoot": "frontend/miniprogram/"
}
```

## Docker 运行

```powershell
cd "D:\study\vscode\大作业"
docker compose up -d --build
```

后端容器启动时会先执行 `flask db upgrade`，迁移成功后才启动 Gunicorn；迁移失败时容器不会带着不完整表结构继续提供服务。

全部业务数据已使用正式 SQLAlchemy Repository。容器升级会把旧 `app_state` 数据导入领域表；全部完成后该表只保留迁移标记，不再参与请求持久化。确认所有旧部署均升级后，可在后续独立版本删除兼容表。

如果 Docker Desktop 配置的 Docker Hub 镜像源不可用，可以只对本项目临时切换官方镜像代理，不需要修改全局 Docker 配置：

```powershell
$env:DOCKER_BASE_REGISTRY = "public.ecr.aws/docker/library"
docker compose up -d --build
```

`DOCKER_BASE_REGISTRY` 同时作用于 Python、Node、MySQL 和 Redis 基础镜像；Compose 默认使用 `docker.io/library`，当前 `.env.example` 使用本机已验证可用的 `public.ecr.aws/docker/library`。

前端页面只在微信开发者工具模拟器、自动化环境或真机中运行和验收。历史
`frontend/preview` 被保留用于追溯旧迭代，但 Compose 默认不构建、不启动，也不作为功能完成依据。

后端 API：

```text
http://localhost:5000/api/v1/health
```

停止：

```powershell
docker compose down
```

首次启动前可复制 `.env.example` 为 `.env`，并完成其中所有占位值。Compose 默认只启动 MySQL、Redis 和后端 API；MySQL、Redis 与上传文件均使用持久卷。详细步骤和微信公众平台人工配置项见 `docs/上线部署清单.md`。

## 当前非 AI 业务能力

- 小程序启动时自动调用 `wx.login`；后端生产模式使用微信 `code2Session` 按 openid/unionid 建立多用户身份，请求和文件上传自动携带签名 Token。
- 每日血压、血糖和体重支持真实编辑、范围校验与保存。
- 饮食记录支持新增、营养数据汇总与删除。
- 健康档案支持年龄、身高、体重、三高类型、病史和用药维护，BMI 自动计算。
- 首次使用增加隐私政策、用户协议和敏感健康数据授权，小程序原生展示协议并由后端按版本记录确认时间。
- “我的数据”支持生成当前用户JSON数据副本，在小程序临时目录保存并调用微信文件分享能力；安全标识、审计IP哈希和内部存储地址不会导出。
- “我的数据”支持撤回敏感健康数据授权；撤回后健康记录、趋势、报告和AI相关接口立即停用，重新授权后恢复。
- 报告支持图片、拍照及 PDF 上传，限制为安全扩展名且最大 10MB。
- 后端统一处理鉴权、参数错误、文件过大及未知异常。
- 小程序按 develop/trial/release 区分 API 地址，请求具备超时、请求追踪 ID、401 自动重登和上传失败处理。
- 后端具备生产配置启动自检、登录审计、Token 版本撤销、账号停用即时下线、Redis 共享限流、CORS 白名单、安全响应头、数据库就绪检查和多 worker Gunicorn。

OCR、健康问答和预测接口继续保留；算法内部实现由对应 AI 服务替换，不放在小程序端。
