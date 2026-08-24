# 三高健康管理小程序接口文档

本文档用于指导后端 Flask API 编写，接口按小程序页面功能拆分。当前小程序底部有三个主页面：`每日记录`、`AI`、`我的`。体检报告上传和 OCR 识别属于每日记录页面里的功能入口。

## 1. 基础约定

### 1.1 接口地址

开发环境：

```text
http://localhost:5000/api/v1
```

小程序端统一在 `frontend/miniprogram/services/api.js` 中配置 `API_BASE_URL`。

### 1.2 请求格式

普通接口使用 JSON：

```http
Content-Type: application/json
Authorization: Bearer <token>
```

上传图片或 PDF 使用表单文件：

```http
Content-Type: multipart/form-data
Authorization: Bearer <token>
```

### 1.3 通用返回格式

成功：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

失败：

```json
{
  "code": 40001,
  "message": "参数错误",
  "data": null
}
```

### 1.4 常用状态码

| code | 含义 | 说明 |
| --- | --- | --- |
| 0 | 成功 | 请求处理成功 |
| 40001 | 参数错误 | 缺少参数、格式不正确 |
| 40101 | 未登录 | token 缺失或过期 |
| 40301 | 无权限 | 用户无权访问该资源 |
| 40401 | 数据不存在 | 查询对象不存在 |
| 40901 | 数据冲突 | 重复提交、版本冲突 |
| 50001 | 服务异常 | 后端内部错误 |
| 50002 | AI 服务异常 | 大模型接口调用失败 |
| 50003 | OCR 服务异常 | OCR 识别失败 |

### 1.5 时间格式

| 类型 | 格式 | 示例 |
| --- | --- | --- |
| 日期 | `YYYY-MM-DD` | `2026-08-18` |
| 月份 | `YYYY-MM` | `2026-08` |
| 时间 | `HH:mm` | `20:30` |
| 日期时间 | ISO 8601 | `2026-08-18T08:30:00+08:00` |

### 1.6 身份环境说明

本地开发默认使用 `WECHAT_LOGIN_MODE=mock`，便于在没有 AppSecret 时联调；生产环境强制使用
`WECHAT_LOGIN_MODE=code2session`，后端以微信返回的 `openid`/`unionid` 创建或匹配独立用户。
生产配置若缺少 AppID、AppSecret，或仍使用 mock 登录，应用会拒绝启动。

## 2. 页面接口总览

| 页面 | 功能 | 主要接口 |
| --- | --- | --- |
| 每日记录 | 默认打开今日记录 | `GET /daily-records/today` |
| 每日记录 | 查看某一天记录 | `GET /daily-records?date=2026-08-18` |
| 每日记录 | 大日历记录标记 | `GET /daily-records/calendar?month=2026-08` |
| 每日记录 | 编辑今日待办表单 | `GET /daily-records/{record_id}/tasks`、`PATCH /daily-tasks/{task_id}`、`PUT /daily-task-templates/current` |
| 每日记录 | 录入血压血糖 | `PATCH /daily-records/{record_id}/vitals` |
| 每日记录 | 录入饮食 | `GET /daily-records/{record_id}/meals`、`POST /daily-records/{record_id}/meals` |
| 每日记录 | 趋势和预测 | `GET /trends/vitals`、`GET /predictions/vitals` |
| 每日记录 | 报告上传和 OCR | `POST /reports/upload`、`POST /reports/{report_id}/recognize`、`GET /reports/{report_id}/progress` |
| AI | AI 对话 | `POST /ai/conversations`、`POST /ai/conversations/{conversation_id}/messages` |
| AI | 对话记录 | `GET /ai/conversations`、`GET /ai/conversations/{conversation_id}/messages` |
| 我的 | 用户头像、年龄、电话、用户名 | `GET /me/profile`、`PUT /me/profile` |
| 我的 | 健康档案摘要编辑 | `PUT /me/health-profile` |
| 我的 | 提醒设置 | `GET /me/settings`、`PUT /me/settings` |
| 首次使用/我的 | 隐私政策、用户协议和健康数据授权留痕 | `GET /me/consents`、`PUT /me/consents` |
| 管理员 | 用户、报告、食物、公告维护 | `/admin/*` |

## 3. 登录与用户身份

### 3.1 微信登录

```http
POST /auth/wechat-login
```

用途：小程序调用 `wx.login` 获得 `code` 后，发送给后端换取登录 token。

请求体：

```json
{
  "code": "wx_login_code",
  "nickname": "李明",
  "avatar_url": "https://example.com/avatar.png"
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "jwt_token",
    "user": {
      "id": 1,
      "nickname": "李明",
      "age": 56,
      "phone": "138****0926",
      "avatar_url": ""
    }
  }
}
```

后端在 `code2session` 模式下调用微信官方接口，只保存 `openid` 和可选 `unionid`，不持久化
`session_key`。每次成功或失败登录都会写入脱敏审计记录。Token 内含用户令牌版本；账号被管理员
停用或用户退出登录后，旧 Token 立即失效。登录 `code` 只能使用一次，客户端遇到 401 后必须重新
调用 `wx.login` 获取新 code。

### 3.2 退出登录

```http
POST /auth/logout
```

需要携带用户 Bearer Token。退出后服务端递增 `token_version`，当前用户此前签发的所有 Token 都会失效。

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": true
}
```

## 4. 每日记录页面接口

每日记录是用户打开小程序后的默认首页。页面需要展示日期、大日历入口、今日待办、血压血糖、饮食、趋势、体检报告上传和异常提醒。

### 4.1 获取今日记录

```http
GET /daily-records/today
```

用途：用户打开小程序时默认加载今日表单。如果今天还没有记录，后端自动创建一条当天 `daily_records`，并根据当前有效待办模板生成当天待办快照。

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "record": {
      "id": 101,
      "record_date": "2026-08-18",
      "completion_rate": 80,
      "status": "editing"
    },
    "tasks": [
      {
        "id": 1001,
        "task_name": "晨间血压",
        "is_done": true,
        "completed_at": "2026-08-18T08:10:00+08:00",
        "sort_order": 1
      },
      {
        "id": 1002,
        "task_name": "空腹血糖",
        "is_done": true,
        "completed_at": "2026-08-18T08:20:00+08:00",
        "sort_order": 2
      },
      {
        "id": 1003,
        "task_name": "晚间复测",
        "is_done": false,
        "completed_at": null,
        "sort_order": 3
      }
    ],
    "vitals": {
      "systolic_pressure": 138,
      "diastolic_pressure": 86,
      "fasting_glucose": 6.8,
      "postprandial_glucose": 8.4
    },
    "nutrition": {
      "calories": 1680,
      "sugar": 28,
      "fat": 42,
      "salt": 4.8
    },
    "alerts": [
      {
        "id": 501,
        "level": "medium",
        "title": "空腹血糖偏高",
        "description": "建议晚餐减少精制碳水，饭后散步 20-30 分钟。"
      }
    ]
  }
}
```

### 4.2 查询指定日期记录

```http
GET /daily-records?date=2026-08-17
```

用途：用户在日历中点击某一天时，查看该日期的历史记录。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| date | string | 是 | 要查看的日期 |

返回：结构同 `GET /daily-records/today`。

说明：如果查询的是历史日期，不应自动套用最新待办模板。历史日期只返回当时已经生成的 `daily_tasks` 快照。

### 4.3 获取日历月份标记

```http
GET /daily-records/calendar?month=2026-08
```

用途：大日历展示某个月哪些日期有记录、哪些日期有异常、哪些日期记录完成。

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| month | string | 是 | 月份，格式 `YYYY-MM` |

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "month": "2026-08",
    "days": [
      {
        "date": "2026-08-17",
        "has_record": true,
        "completion_rate": 100,
        "has_alert": false
      },
      {
        "date": "2026-08-18",
        "has_record": true,
        "completion_rate": 80,
        "has_alert": true
      }
    ]
  }
}
```

### 4.4 更新每日记录基础字段

```http
PATCH /daily-records/{record_id}
```

用途：保存当天备注、情绪、睡眠等基础记录字段。如果前端暂时没有这些字段，可以后端先预留。

请求体：

```json
{
  "note": "今天晚饭吃得较清淡",
  "mood": "平稳"
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 101,
    "record_date": "2026-08-18",
    "note": "今天晚饭吃得较清淡",
    "mood": "平稳"
  }
}
```

### 4.5 更新血压血糖

```http
PATCH /daily-records/{record_id}/vitals
```

用途：用户在每日记录中录入或修改血压、血糖。

请求体：

```json
{
  "systolic_pressure": 138,
  "diastolic_pressure": 86,
  "fasting_glucose": 6.8,
  "postprandial_glucose": 8.4,
  "measured_at": "2026-08-18T08:20:00+08:00"
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 301,
    "daily_record_id": 101,
    "systolic_pressure": 138,
    "diastolic_pressure": 86,
    "fasting_glucose": 6.8,
    "postprandial_glucose": 8.4,
    "risk_level": "medium",
    "advice": "空腹血糖偏高，建议减少晚间精制碳水。"
  }
}
```

### 4.6 获取当天待办

```http
GET /daily-records/{record_id}/tasks
```

用途：显示当天表单里的待办列表。

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1001,
      "task_name": "晨间血压",
      "is_done": true,
      "completed_at": "2026-08-18T08:10:00+08:00",
      "sort_order": 1
    },
    {
      "id": 1002,
      "task_name": "空腹血糖",
      "is_done": false,
      "completed_at": null,
      "sort_order": 2
    }
  ]
}
```

### 4.7 勾选或取消当天待办

```http
PATCH /daily-tasks/{task_id}
```

用途：用户点击某条待办的完成状态。这个接口只修改某一天的快照，不修改长期模板。

请求体：

```json
{
  "is_done": true
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1002,
    "task_name": "空腹血糖",
    "is_done": true,
    "completed_at": "2026-08-18T08:30:00+08:00"
  }
}
```

### 4.8 获取当前待办模板

```http
GET /daily-task-templates/current?date=2026-08-18
```

用途：进入“编辑今日待办”时，获取当前日期生效的待办模板。

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "template_id": 21,
    "version_no": 2,
    "effective_from": "2026-08-18",
    "effective_to": null,
    "items": [
      {
        "id": 201,
        "task_name": "晨间血压",
        "sort_order": 1
      },
      {
        "id": 202,
        "task_name": "空腹血糖",
        "sort_order": 2
      },
      {
        "id": 203,
        "task_name": "晚间复测",
        "sort_order": 3
      }
    ]
  }
}
```

### 4.9 更新待办模板

```http
PUT /daily-task-templates/current
```

用途：用户编辑今日待办内容，例如新增、删除、改名、调整排序。

请求体：

```json
{
  "effective_date": "2026-08-18",
  "items": [
    {
      "task_name": "晨间血压",
      "sort_order": 1
    },
    {
      "task_name": "空腹血糖",
      "sort_order": 2
    },
    {
      "task_name": "晚间复测",
      "sort_order": 3
    }
  ]
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "template_id": 22,
    "version_no": 3,
    "effective_from": "2026-08-18",
    "effective_to": null,
    "items": [
      {
        "id": 301,
        "task_name": "晨间血压",
        "sort_order": 1
      },
      {
        "id": 302,
        "task_name": "空腹血糖",
        "sort_order": 2
      },
      {
        "id": 303,
        "task_name": "晚间复测",
        "sort_order": 3
      }
    ]
  }
}
```

业务规则：

1. 待办属于某一天的每日表单，保存到 `daily_tasks` 快照表。
2. 每天 24:00，也就是次日 00:00，系统根据当前生效模板生成新一天的待办快照。
3. 用户修改待办内容时，从 `effective_date` 开始创建新的模板版本。
4. `effective_date` 之前的待办快照保持不变。
5. `effective_date` 当天如果已经生成待办，后端只重建当天快照，同名待办尽量保留完成状态。
6. `effective_date` 之后的日期继续沿用新模板，直到下一次用户修改。

### 4.10 手动生成某日待办快照

```http
POST /daily-records/{record_id}/tasks/generate
```

用途：定时任务失败或开发调试时，手动为某一天生成待办快照。正式环境中主要由定时任务调用。

请求体：

```json
{
  "date": "2026-08-19"
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "record_id": 102,
    "generated_count": 3
  }
}
```

### 4.11 获取饮食记录

```http
GET /daily-records/{record_id}/meals
```

用途：查看当天三餐和营养统计。

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "meals": [
      {
        "id": 401,
        "meal_type": "breakfast",
        "meal_name": "早餐",
        "foods": [
          {
            "name": "燕麦粥",
            "amount": "1 碗",
            "calories": 180,
            "sugar": 3.2,
            "fat": 2.1,
            "salt": 0.3
          }
        ]
      }
    ],
    "summary": {
      "calories": 1680,
      "sugar": 28,
      "fat": 42,
      "salt": 4.8
    }
  }
}
```

### 4.12 新增饮食记录

```http
POST /daily-records/{record_id}/meals
```

请求体：

```json
{
  "meal_type": "dinner",
  "meal_name": "晚餐",
  "foods": [
    {
      "name": "糙米饭",
      "amount": "半碗",
      "calories": 120,
      "sugar": 1.1,
      "fat": 0.8,
      "salt": 0.1
    },
    {
      "name": "清炒西兰花",
      "amount": "1 份",
      "calories": 90,
      "sugar": 2.6,
      "fat": 4.5,
      "salt": 0.7
    }
  ]
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 402,
    "meal_type": "dinner",
    "meal_name": "晚餐"
  }
}
```

### 4.13 修改饮食记录

```http
PUT /meals/{meal_id}
```

请求体同新增饮食记录。

### 4.14 删除饮食记录

```http
DELETE /meals/{meal_id}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": true
}
```

### 4.15 获取血压血糖趋势

```http
GET /trends/vitals?range=7d
```

查询参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| range | string | 否 | `7d`、`30d`、`90d` |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "range": "7d",
    "points": [
      {
        "date": "2026-08-12",
        "systolic_pressure": 132,
        "diastolic_pressure": 84,
        "fasting_glucose": 6.2
      },
      {
        "date": "2026-08-18",
        "systolic_pressure": 138,
        "diastolic_pressure": 86,
        "fasting_glucose": 6.8
      }
    ]
  }
}
```

### 4.16 获取血压血糖预测

```http
GET /predictions/vitals?days=7
```

用途：调用后端机器学习模型，预测未来几天血压血糖变化趋势。

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "model_name": "RandomForestRegressor",
    "model_version": "demo-1.0",
    "days": 7,
    "predictions": [
      {
        "date": "2026-08-19",
        "systolic_pressure": 136,
        "diastolic_pressure": 85,
        "fasting_glucose": 6.6,
        "risk_level": "medium"
      }
    ],
    "explanation": "近期空腹血糖略高，晚餐碳水和餐后运动对预测结果影响较大。"
  }
}
```

### 4.17 获取异常提醒

```http
GET /alerts?date=2026-08-18
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 501,
      "alert_type": "glucose",
      "level": "medium",
      "title": "空腹血糖偏高",
      "description": "空腹血糖 6.8 mmol/L，建议关注晚餐结构。",
      "is_read": false,
      "created_at": "2026-08-18T08:40:00+08:00"
    }
  ]
}
```

### 4.18 标记提醒已读

```http
PATCH /alerts/{alert_id}/read
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": true
}
```

## 5. 体检报告上传与 OCR 接口

这些接口服务于每日记录页面中的“上传体检报告”模块。用户点击虚线框后选择拍照或相册图片，也可以上传 PDF。

### 5.1 上传体检报告文件

```http
POST /reports/upload
```

请求格式：`multipart/form-data`

表单字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file | file | 是 | 图片或 PDF |
| source | string | 否 | `camera`、`album`、`pdf` |
| report_date | string | 否 | 体检日期 |

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "report_id": 601,
    "file_name": "体检报告.pdf",
    "file_type": "pdf",
    "status": "uploaded",
    "progress": 0
  }
}
```

### 5.2 开始 OCR 识别

```http
POST /reports/{report_id}/recognize
```

用途：用户点击“开始识别”后触发。前端显示进度条。

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "report_id": 601,
    "status": "recognizing",
    "progress": 10
  }
}
```

### 5.3 查询识别进度

```http
GET /reports/{report_id}/progress
```

用途：前端每隔 1-2 秒轮询一次，用于更新识别进度条。

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "report_id": 601,
    "status": "extracting",
    "progress": 70,
    "message": "正在提取关键指标"
  }
}
```

状态枚举：

| status | 含义 |
| --- | --- |
| uploaded | 已上传 |
| recognizing | OCR 识别中 |
| extracting | 指标提取中 |
| review_pending | 等待人工复核 |
| completed | 识别完成 |
| failed | 识别失败 |

### 5.4 获取报告详情

```http
GET /reports/{report_id}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 601,
    "file_name": "体检报告.pdf",
    "file_type": "pdf",
    "report_date": "2026-08-18",
    "status": "review_pending",
    "confidence": 0.92,
    "summary": "空腹血糖、总胆固醇偏高",
    "created_at": "2026-08-18T10:00:00+08:00"
  }
}
```

### 5.5 获取报告指标

```http
GET /reports/{report_id}/indicators
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 701,
      "indicator_name": "空腹血糖",
      "indicator_code": "GLU",
      "value": 6.8,
      "unit": "mmol/L",
      "reference_range": "3.9-6.1",
      "status": "high",
      "risk_level": "medium"
    },
    {
      "id": 702,
      "indicator_name": "总胆固醇",
      "indicator_code": "TC",
      "value": 5.9,
      "unit": "mmol/L",
      "reference_range": "<5.2",
      "status": "high",
      "risk_level": "medium"
    }
  ]
}
```

### 5.6 获取报告历史

```http
GET /reports/history?page=1&page_size=10
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 601,
        "file_name": "2026 春季体检报告",
        "report_date": "2026-08-18",
        "status": "review_pending",
        "summary": "空腹血糖、总胆固醇偏高"
      }
    ],
    "page": 1,
    "page_size": 10,
    "total": 1
  }
}
```

## 6. AI 页面接口

AI 页面需要提供健康问答、对话记录、快捷提问、风险摘要。后端负责封装 OpenAI 兼容大模型接口，并结合 Chroma 向量库检索健康知识和用户历史健康数据。

### 6.1 获取快捷问题

```http
GET /ai/quick-questions
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    "晚饭怎么吃",
    "血压偏高怎么办",
    "报告异常怎么看",
    "今天适合运动吗"
  ]
}
```

### 6.2 获取 AI 页面上下文摘要

```http
GET /ai/context/today?date=2026-08-18
```

用途：AI 页面展示“来自每日记录”的风险摘要。

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "date": "2026-08-18",
    "risk_cards": [
      {
        "label": "空腹血糖",
        "value": "6.8",
        "unit": "mmol/L",
        "level": "medium"
      },
      {
        "label": "收缩压",
        "value": "138",
        "unit": "mmHg",
        "level": "medium"
      }
    ],
    "summary": "今日空腹血糖和收缩压略高，建议控制晚餐碳水和盐分。"
  }
}
```

### 6.3 创建 AI 会话

```http
POST /ai/conversations
```

请求体：

```json
{
  "title": "晚饭怎么吃",
  "source": "daily_record",
  "related_date": "2026-08-18"
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "conversation_id": 801,
    "title": "晚饭怎么吃",
    "created_at": "2026-08-18T18:00:00+08:00"
  }
}
```

### 6.4 获取 AI 会话列表

```http
GET /ai/conversations?page=1&page_size=20
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 801,
        "title": "晚饭怎么吃",
        "last_message": "晚餐主食建议控制在半碗左右...",
        "related_date": "2026-08-18",
        "updated_at": "2026-08-18T18:02:00+08:00"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

### 6.5 获取某个会话消息

```http
GET /ai/conversations/{conversation_id}/messages
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 9001,
      "role": "user",
      "content": "最近空腹血糖偏高，晚饭应该怎么吃？",
      "created_at": "2026-08-18T18:01:00+08:00"
    },
    {
      "id": 9002,
      "role": "assistant",
      "content": "晚餐主食建议控制在半碗左右，优先选择杂粮、豆制品和深色蔬菜，饭后散步 20-30 分钟。",
      "created_at": "2026-08-18T18:02:00+08:00"
    }
  ]
}
```

### 6.6 发送消息并获取 AI 回复

```http
POST /ai/conversations/{conversation_id}/messages
```

请求体：

```json
{
  "content": "最近空腹血糖偏高，晚饭应该怎么吃？",
  "use_daily_context": true,
  "related_date": "2026-08-18"
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "user_message": {
      "id": 9001,
      "role": "user",
      "content": "最近空腹血糖偏高，晚饭应该怎么吃？"
    },
    "assistant_message": {
      "id": 9002,
      "role": "assistant",
      "content": "晚餐主食建议控制在半碗左右，优先选择杂粮、豆制品和深色蔬菜，饭后散步 20-30 分钟。"
    },
    "retrieval": {
      "collection": "health_knowledge",
      "hit_count": 3
    }
  }
}
```

说明：

1. `use_daily_context = true` 时，后端会读取当天每日记录、血压血糖、饮食、报告异常。
2. 当前 demo 未接入真实大模型时，后端使用 `RagDemoService` 从数据库资料中取第一条、最后一条和随机一条，直接拼成助手回复。
3. 当前 demo 响应的 `retrieval.items` 会返回三条结构化命中结果，字段包含 `position`、`source`、`source_id` 和 `content`。
4. 正式接入大模型后，后端再使用 Prompt 约束 AI 回复，只给生活方式建议和就医提醒，不替代医生诊断。
5. 正式检索增强数据来自 Chroma 向量库，例如健康知识、指标参考范围、用户健康记忆。

### 6.7 删除 AI 会话

```http
DELETE /ai/conversations/{conversation_id}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": true
}
```

## 7. 我的页面接口

我的页面包含用户资料、健康档案、提醒设置以及隐私与账号安全入口；首次使用时先完成协议和敏感健康数据授权。

### 7.1 获取个人资料和健康档案

```http
GET /me/profile
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "user": {
      "id": 1,
      "avatar_url": "",
      "nickname": "李明",
      "age": 56,
      "phone": "138****0926"
    },
    "health_profile": {
      "gender": "男",
      "height_cm": 172,
      "weight_kg": 74,
      "bmi": 25.1,
      "medical_history": "轻度脂肪肝",
      "chronic_types": [
        "hypertension",
        "diabetes"
      ],
      "medications": "二甲双胍、氨氯地平"
    }
  }
}
```

### 7.2 更新个人资料

```http
PUT /me/profile
```

请求体：

```json
{
  "nickname": "李明",
  "age": 56,
  "phone": "13812340926",
  "avatar_url": ""
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "nickname": "李明",
    "age": 56,
    "phone": "138****0926",
    "avatar_url": ""
  }
}
```

### 7.3 更新健康档案摘要

```http
PUT /me/health-profile
```

请求体：

```json
{
  "gender": "男",
  "height_cm": 172,
  "weight_kg": 74,
  "medical_history": "轻度脂肪肝",
  "chronic_types": [
    "hypertension",
    "diabetes"
  ],
  "medications": "二甲双胍、氨氯地平"
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "gender": "男",
    "height_cm": 172,
    "weight_kg": 74,
    "bmi": 25.1,
    "medical_history": "轻度脂肪肝",
    "chronic_types": [
      "hypertension",
      "diabetes"
    ],
    "medications": "二甲双胍、氨氯地平",
    "updated_at": "2026-08-18T19:00:00+08:00"
  }
}
```

说明：BMI 由后端根据身高体重自动计算。

### 7.4 获取提醒设置

```http
GET /me/settings
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "alert_push_enabled": true,
    "daily_record_reminder_enabled": true,
    "daily_record_reminder_time": "20:30"
  }
}
```

### 7.5 更新提醒设置

```http
PUT /me/settings
```

请求体：

```json
{
  "alert_push_enabled": true,
  "daily_record_reminder_enabled": true,
  "daily_record_reminder_time": "20:30"
}
```

### 7.6 获取当前授权状态

```http
GET /me/consents
```

返回当前服务端要求的隐私政策、用户协议和健康数据授权版本，以及用户是否已经对三个当前版本完成确认。任一版本升级后，`required_complete` 自动变为 `false`，小程序会重新进入授权页。

### 7.7 保存授权记录

```http
PUT /me/consents
```

请求体：

```json
{
  "privacy_policy_accepted": true,
  "user_agreement_accepted": true,
  "health_data_consent": true
}
```

三个字段必须严格为 `true`。后端记录当前三个文档版本和确认时间，不接受客户端自报版本号，避免伪造或版本错配。

### 7.8 撤回健康数据授权

```http
POST /me/consents/withdraw
```

请求体必须包含明确确认语句：

```json
{ "confirmation": "撤回授权" }
```

撤回成功后记录 `withdrawn_at`，并立即将健康数据授权置为 `false`。启用 `HEALTH_CONSENT_REQUIRED=true` 时，用户访问每日记录、待办、饮食、趋势、预测、提醒、体检报告、AI健康上下文及健康档案写入接口会返回 HTTP 403、业务码 `40303`。个人资料、提醒设置、协议状态、个人数据导出、退出登录及重新授权仍可访问。再次调用 `PUT /me/consents` 会清除撤回时间并恢复健康功能。

### 7.9 导出当前用户数据副本

```http
GET /me/data-export
```

返回当前 Bearer Token 所属用户的账号资料、健康档案、设置、授权记录、每日记录、指标、饮食、待办、提醒、报告元数据与指标、AI会话和消息。响应包含 `schema_version`、UTC生成时间、各分类数量和数据正文。

安全排除项：openid、unionid、Token版本、登录审计IP哈希、报告实际存储URL、OCR内部文档ID和AI内部追踪ID。接口不会接受客户端提供 `user_id`，避免导出其他用户数据。

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "alert_push_enabled": true,
    "daily_record_reminder_enabled": true,
    "daily_record_reminder_time": "20:30"
  }
}
```

## 8. 管理员端接口

管理员端不是当前小程序底部 Tab，但原需求中包含用户管理、健康数据维护、饮食数据维护、报告审核和系统公告管理，因此后端保留接口。

### 8.1 用户列表

```http
GET /admin/users?page=1&page_size=20&keyword=李明
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "nickname": "李明",
        "age": 56,
        "phone": "138****0926",
        "chronic_types": [
          "hypertension",
          "diabetes"
        ],
        "created_at": "2026-08-01T09:00:00+08:00"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

#### 8.1.1 用户健康档案详情

```http
GET /admin/users/{user_id}
```

仅管理员 Token 可访问。返回用户昵称、完整手机号、账号状态、登录次数、最近登录时间、性别、年龄、身高、体重、BMI、慢病类型、既往病史和用药情况；用户列表中的手机号仍保持脱敏。

#### 8.1.2 修改用户健康档案

```http
PUT /admin/users/{user_id}
```

除健康档案字段外可提交 `status: 0|1`。设为 `0` 会停用账号并递增令牌版本，现有会话立即失效；
停用用户再次微信登录时返回 HTTP 403。

请求体示例：

```json
{
  "nickname": "李明",
  "phone": "13812340926",
  "gender": "男",
  "age": 56,
  "height_cm": 172,
  "weight_kg": 74,
  "chronic_types": ["hypertension", "diabetes"],
  "medical_history": "轻度脂肪肝",
  "medication": "二甲双胍、氨氯地平"
}
```

后端会校验手机号、年龄、身高、体重、性别、慢病枚举和文本长度，保存后重新计算 BMI，并同步到普通用户端个人资料和健康档案。

### 8.2 管理员查看待审核报告

```http
GET /admin/reports?status=review_pending&page=1&page_size=20
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 601,
        "user_name": "李明",
        "file_name": "体检报告.pdf",
        "status": "review_pending",
        "confidence": 0.92,
        "summary": "空腹血糖、总胆固醇偏高",
        "created_at": "2026-08-18T10:00:00+08:00"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

### 8.3 管理员复核报告

```http
PATCH /admin/reports/{report_id}/review
```

请求体：

```json
{
  "status": "completed",
  "review_note": "指标识别正确",
  "indicators": [
    {
      "indicator_name": "空腹血糖",
      "value": 6.8,
      "unit": "mmol/L",
      "reference_range": "3.9-6.1",
      "status": "high"
    }
  ]
}
```

返回：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "report_id": 601,
    "status": "completed",
    "reviewed_at": "2026-08-18T11:00:00+08:00"
  }
}
```

### 8.4 食物库列表

```http
GET /admin/foods?keyword=米饭&page=1&page_size=20
```

### 8.5 新增食物

```http
POST /admin/foods
```

请求体：

```json
{
  "name": "糙米饭",
  "category": "主食",
  "unit": "100g",
  "calories": 116,
  "sugar": 0.4,
  "fat": 0.9,
  "salt": 0.02
}
```

### 8.6 修改食物

```http
PUT /admin/foods/{food_id}
```

请求体同新增食物。

### 8.7 删除食物

```http
DELETE /admin/foods/{food_id}
```

### 8.8 公告列表

```http
GET /admin/announcements?page=1&page_size=20
```

### 8.9 新增公告

```http
POST /admin/announcements
```

请求体：

```json
{
  "title": "夏季血压管理提醒",
  "content": "高温天气请注意补水，按时测量血压。",
  "is_published": true
}
```

### 8.10 修改公告

```http
PUT /admin/announcements/{announcement_id}
```

### 8.11 删除公告

```http
DELETE /admin/announcements/{announcement_id}
```

### 8.12 批量审核报告

```http
PATCH /admin/reports/batch-review
```

```json
{
  "ids": [601, 602],
  "status": "completed",
  "review_note": "管理员批量通过"
}
```

### 8.13 批量删除食物

```http
POST /admin/foods/batch-delete
```

```json
{
  "ids": [10001, 10002]
}
```

### 8.14 批量更新公告发布状态

```http
PATCH /admin/announcements/batch-publish
```

```json
{
  "ids": [11001, 11002],
  "is_published": true
}
```

三个批量接口均只允许管理员 Token，单次至少1条、最多100条，自动去除重复 ID。返回 `requested_count`、`processed_count`、`processed_ids` 和 `missing_ids`，便于前端展示部分成功结果。

## 9. 后端服务接口与数据关系

### 9.1 MySQL 主要承载

| 数据 | 相关接口 |
| --- | --- |
| 用户账号 `users` | `/auth/*`、`/me/profile` |
| 健康档案 `health_profiles` | `/me/health-profile` |
| 每日记录 `daily_records` | `/daily-records/*` |
| 血压血糖 `vital_records` | `/daily-records/{record_id}/vitals`、`/trends/vitals` |
| 饮食记录 `meal_records`、`food_items` | `/daily-records/{record_id}/meals`、`/admin/foods` |
| 体检报告 `medical_reports`、`report_indicators` | `/reports/*`、`/admin/reports/*` |
| 异常提醒 `health_alerts` | `/alerts/*` |
| 待办模板和快照 | `/daily-task-templates/*`、`/daily-tasks/*` |
| AI 会话 `ai_conversations`、`ai_messages` | `/ai/conversations/*` |

### 9.2 MongoDB 主要承载

| 数据 | 说明 |
| --- | --- |
| `ocr_results` | 保存 OCR 原始文本、页面坐标、置信度、结构化中间结果 |
| `ai_call_logs` | 保存大模型请求、模型名称、token 用量、响应时间、错误信息 |
| `api_request_logs` | 保存接口访问日志，方便排查演示问题 |
| `prediction_snapshots` | 保存预测模型输入、输出、模型版本和解释 |

### 9.3 Chroma 向量库主要承载

| Collection | 用途 |
| --- | --- |
| `health_knowledge` | 三高饮食、血压血糖管理、生活方式建议知识 |
| `indicator_reference` | 体检指标解释、参考范围、异常风险解释 |
| `user_health_memory` | 用户长期健康摘要，用于 AI 个性化回答 |

## 10. 后端开发顺序建议

第一阶段先完成能支撑前端演示的接口：

1. `GET /daily-records/today`
2. `GET /daily-records?date=...`
3. `GET /daily-records/calendar`
4. `GET /daily-records/{record_id}/tasks`
5. `PATCH /daily-tasks/{task_id}`
6. `PUT /daily-task-templates/current`
7. `GET /me/profile`
8. `PUT /me/profile`
9. `PUT /me/health-profile`
10. `POST /reports/upload`
11. `POST /reports/{report_id}/recognize`
12. `GET /reports/{report_id}/progress`
13. `GET /ai/conversations`
14. `POST /ai/conversations/{conversation_id}/messages`

饮食、趋势预测、报告复核、管理员维护和真实微信登录的普通前后端边界均已实现；预测/OCR/问答的算法内部与真实 AI 服务联调仍由 AI 团队完成。
