# 接口与 AI/RAG 联调测试报告

生成日期：2026-08-24

## 1. 本轮改动结论

本轮已将 AI 对话接口改为“无真实大模型接入时的 RAG 演示模式”：

1. 用户发送消息后，后端仍会保存用户消息到 `ai_messages`。
2. 后端调用 `RagDemoService` 从数据库资料中收集可检索文本。
3. 服务按顺序返回第一条、最后一条和随机一条资料。
4. 这三条资料会直接拼成助手回复，并保存为 assistant 消息。
5. 响应体 `retrieval.items` 同时返回三条结构化命中结果，便于前端调试和测试断言。

当前没有调用 OpenAI 兼容大模型接口，也没有依赖真实 Chroma 服务，因此适合明天演示前的稳定 demo。

## 2. 新增测试代码位置

```text
backend/integration_tests/
  README.md
  test_all_api_contracts.py
```

`test_all_api_contracts.py` 使用隔离 SQLite 数据库，不污染 Docker MySQL 演示数据。测试覆盖每日记录、报告、AI、我的、管理员端和认证相关接口。

## 3. 5 轮检查记录

| 轮次 | 检查内容 | 命令/方式 | 结果 |
| --- | --- | --- | --- |
| 第 1 轮 | 原有后端测试 | `docker exec -e AUTH_REQUIRED=false -e RATELIMIT_STORAGE_URI=memory:// three-high-backend-api python -m pytest tests -q` | 36 passed |
| 第 2 轮 | 新增全接口联调测试 | `docker exec -e AUTH_REQUIRED=true -e HEALTH_CONSENT_REQUIRED=false -e RATELIMIT_STORAGE_URI=memory:// three-high-backend-api python -m pytest integration_tests -q` | 1 passed |
| 第 3 轮 | 新增全接口联调复测 | 同第 2 轮 | 1 passed |
| 第 4 轮 | 原有测试复测 | 同第 1 轮 | 36 passed |
| 第 5 轮 | 语法与差异检查 | `python -m compileall -q app integration_tests tests`、`git diff --check` | 通过，仅有 LF/CRLF 提示 |
| 第 6 轮 | 真实 HTTP AI/RAG 检查 | `http://127.0.0.1:5000/api/v1` 登录、创建会话、发送消息 | 通过，返回 first/last/random 三条数据 |

说明：第一次直接在容器默认环境下运行原有测试时出现 401，是因为容器正式联调配置为 `AUTH_REQUIRED=true`，而原有部分测试按免登录开发模式编写。使用其对应配置 `AUTH_REQUIRED=false` 后全部通过。新增联调测试保持 `AUTH_REQUIRED=true`，会先登录再访问业务接口。

## 4. 本轮发现并处理的问题

| 问题 | 处理 |
| --- | --- |
| AI 回复原来是关键词硬编码，不是真正读取数据 | 新增 `backend/app/services/rag_demo.py`，改为从数据库资料中取三条数据 |
| 新全接口测试初版使用新 openid，导致没有演示种子提醒 | 改为使用 `demo-openid`，覆盖现有演示用户完整数据链 |
| 测试中先手动生成待办再勾选旧 `task_id`，导致待办不存在 | 调整顺序为先勾选，再调用生成接口 |
| 本机 Python 缺少后端依赖 | 改用 Docker 容器运行测试，贴近实际部署环境 |

## 5. AI/RAG 返回示例

真实 HTTP 检查中，AI 接口返回的 `retrieval` 示例：

```json
{
  "collection": "database_demo_rag",
  "mode": "no_llm_first_last_random",
  "hit_count": 3,
  "items": [
    {
      "position": "first",
      "source": "health_profiles",
      "content": "健康档案：性别男，年龄56，BMI 25，慢病类型hypertension、diabetes..."
    },
    {
      "position": "last",
      "source": "announcements",
      "content": "系统公告：夏季血压管理提醒。高温天气请注意补水，按时测量血压。"
    },
    {
      "position": "random",
      "source": "vital_records",
      "content": "血压血糖：收缩压120mmHg，舒张压78mmHg，空腹血糖5.5mmol/L..."
    }
  ]
}
```

## 6. 覆盖接口范围

本轮新增测试覆盖以下接口类型：

- `/auth/*`
- `/daily-records/*`
- `/daily-tasks/*`
- `/daily-task-templates/*`
- `/meals/*`
- `/trends/vitals`
- `/predictions/vitals`
- `/alerts/*`
- `/reports/*`
- `/ai/*`
- `/me/*`
- `/admin/*`

## 7. 后续建议

正式接入大模型时，可以保留当前 `RagDemoService` 作为 fallback：当 OpenAI 兼容接口超时、密钥未配置或 Chroma 不可用时，仍返回数据库三条资料，保证小程序 demo 不会空白。
