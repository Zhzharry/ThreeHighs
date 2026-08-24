# 全接口联调测试说明

本目录用于存放独立于原有 `backend/tests` 的接口联调测试代码。

## 测试内容

`test_all_api_contracts.py` 使用 Flask test client 和隔离 SQLite 数据库，覆盖当前 `backend/app/api/__init__.py` 注册的主要接口流程：

- 健康检查、微信模拟登录、退出登录、管理员登录。
- 每日记录、日历、待办模板、待办勾选、血压血糖、饮食、趋势、预测、异常提醒。
- 体检报告上传、OCR 演示进度、指标读取与修正、报告确认和删除。
- AI 快捷问题、上下文摘要、会话创建、消息发送、会话列表、消息记录和删除。
- 我的页面资料、头像、健康档案、提醒设置、授权、数据导出。
- 管理员 dashboard、用户维护、报告审核、食物库、公告和批量接口。

AI 测试不会调用真实大模型。当前演示逻辑会通过 `RagDemoService` 从数据库中取第一条、最后一条和随机一条资料，直接作为助手回复返回。

## 运行方式

在项目根目录执行：

```powershell
docker compose build backend-api
docker compose up -d backend-api
docker exec -e AUTH_REQUIRED=true -e HEALTH_CONSENT_REQUIRED=false -e RATELIMIT_STORAGE_URI=memory:// three-high-backend-api python -m pytest integration_tests -q
```

如果只想跑原有后端测试：

```powershell
docker exec -e AUTH_REQUIRED=false -e RATELIMIT_STORAGE_URI=memory:// three-high-backend-api python -m pytest tests -q
```
