from __future__ import annotations

import sys
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402
from app.services.demo_store import store  # noqa: E402


def ok(response, expected_status=200):
    payload = response.get_json()
    assert response.status_code == expected_status, payload
    assert payload["code"] == 0, payload
    return payload["data"]


@pytest.fixture()
def api_client(tmp_path):
    store.domain_migrations = {}

    class IntegrationConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp_path / 'three-high-integration.db').as_posix()}"
        UPLOAD_FOLDER = str(tmp_path / "uploads")
        SECRET_KEY = "integration-test-secret-key-change-me-123456"
        AUTO_CREATE_TABLES = True
        PERSIST_DEMO_STATE = False
        DOMAIN_REPOSITORIES_ENABLED = True
        AUTH_REQUIRED = True
        TOKEN_VERSION_REQUIRED = False
        HEALTH_CONSENT_REQUIRED = False
        RATELIMIT_STORAGE_URI = "memory://"
        RATELIMIT_DEFAULT = "10000 per minute"
        WECHAT_LOGIN_RATE_LIMIT = "10000 per minute"
        ADMIN_LOGIN_RATE_LIMIT = "10000 per minute"
        WECHAT_LOGIN_MODE = "mock"
        WECHAT_MOCK_OPENID = "demo-openid"

    app = create_app(IntegrationConfig)
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture()
def user_headers(api_client):
    data = ok(api_client.post("/api/v1/auth/wechat-login", json={
        "code": "integration-code",
        "nickname": "集成测试用户",
    }))
    return {"Authorization": f"Bearer {data['token']}"}


@pytest.fixture()
def admin_headers(api_client):
    data = ok(api_client.post("/api/v1/auth/admin-login", json={
        "username": "admin",
        "password": "admin123",
    }))
    return {"Authorization": f"Bearer {data['token']}"}


def test_every_registered_api_endpoint_and_demo_rag(api_client, user_headers, admin_headers):
    today = date.today().isoformat()
    new_record_date = (date.today() - timedelta(days=2)).isoformat()

    health = ok(api_client.get("/api/v1/health"))
    assert health["status"] == "ready"

    today_payload = ok(api_client.get("/api/v1/daily-records/today", headers=user_headers))
    record_id = today_payload["record"]["id"]
    task_id = today_payload["tasks"][0]["id"]
    alert_id = today_payload["alerts"][0]["id"]

    ok(api_client.get(f"/api/v1/daily-records?date={today}", headers=user_headers))
    ok(api_client.post("/api/v1/daily-records", json={"date": new_record_date}, headers=user_headers), 201)
    ok(api_client.get(f"/api/v1/daily-records/calendar?month={today[:7]}", headers=user_headers))
    ok(api_client.patch(f"/api/v1/daily-records/{record_id}", json={
        "note": "接口联调备注",
        "mood": "平稳",
    }, headers=user_headers))
    ok(api_client.patch(f"/api/v1/daily-records/{record_id}/vitals", json={
        "systolic_pressure": 139,
        "diastolic_pressure": 86,
        "fasting_glucose": 6.9,
        "postprandial_glucose": 8.5,
        "weight_kg": 73.8,
    }, headers=user_headers))
    ok(api_client.get(f"/api/v1/daily-records/{record_id}/tasks", headers=user_headers))
    ok(api_client.patch(f"/api/v1/daily-tasks/{task_id}", json={"is_done": False}, headers=user_headers))
    ok(api_client.post(f"/api/v1/daily-records/{record_id}/tasks/generate", json={"date": today}, headers=user_headers))
    ok(api_client.get(f"/api/v1/daily-task-templates/current?date={today}", headers=user_headers))
    ok(api_client.put("/api/v1/daily-task-templates/current", json={
        "effective_date": today,
        "items": [
            {"task_name": "晨间血压", "sort_order": 1},
            {"task_name": "空腹血糖", "sort_order": 2},
            {"task_name": "晚间复测", "sort_order": 3},
        ],
    }, headers=user_headers))

    meals = ok(api_client.get(f"/api/v1/daily-records/{record_id}/meals", headers=user_headers))
    assert "summary" in meals
    new_meal = ok(api_client.post(f"/api/v1/daily-records/{record_id}/meals", json={
        "meal_type": "dinner",
        "meal_name": "晚餐",
        "foods": [
            {"name": "糙米饭", "amount": "半碗", "calories": 120, "sugar": 1.1, "fat": 0.8, "salt": 0.1}
        ],
    }, headers=user_headers))
    meal_id = new_meal["id"]
    ok(api_client.put(f"/api/v1/meals/{meal_id}", json={
        "meal_type": "dinner",
        "meal_name": "晚餐",
        "foods": [
            {"name": "清炒西兰花", "amount": "1份", "calories": 90, "sugar": 2.6, "fat": 4.5, "salt": 0.7}
        ],
    }, headers=user_headers))
    ok(api_client.delete(f"/api/v1/meals/{meal_id}", headers=user_headers))

    ok(api_client.get("/api/v1/trends/vitals?range=7d", headers=user_headers))
    prediction = ok(api_client.get("/api/v1/predictions/vitals?days=7", headers=user_headers))
    assert prediction["days"] == 7
    ok(api_client.get(f"/api/v1/alerts?date={today}", headers=user_headers))
    ok(api_client.patch(f"/api/v1/alerts/{alert_id}/read", headers=user_headers))

    report_upload = ok(api_client.post("/api/v1/reports/upload", data={
        "source": "pdf",
        "report_date": today,
        "file": (BytesIO(b"%PDF-1.4\n% demo report\n"), "integration-report.pdf"),
    }, headers=user_headers, content_type="multipart/form-data"))
    report_id = report_upload["report_id"]
    ok(api_client.post(f"/api/v1/reports/{report_id}/recognize", headers=user_headers))
    progress = {}
    for _ in range(3):
        progress = ok(api_client.get(f"/api/v1/reports/{report_id}/progress", headers=user_headers))
    assert progress["progress"] == 100
    ok(api_client.get("/api/v1/reports/history?page=1&page_size=10", headers=user_headers))
    ok(api_client.get(f"/api/v1/reports/{report_id}", headers=user_headers))
    indicators = ok(api_client.get(f"/api/v1/reports/{report_id}/indicators", headers=user_headers))
    assert indicators
    ok(api_client.put(f"/api/v1/reports/{report_id}/indicators", json={
        "items": [{
            "indicator_name": "空腹血糖",
            "indicator_code": "GLU",
            "value": "6.9",
            "unit": "mmol/L",
            "reference_range": "3.9-6.1",
            "status": "high",
            "risk_level": "medium",
        }]
    }, headers=user_headers))
    ok(api_client.patch(f"/api/v1/reports/{report_id}", json={
        "action": "confirm",
        "review_note": "测试确认",
    }, headers=user_headers))

    quick_questions = ok(api_client.get("/api/v1/ai/quick-questions", headers=user_headers))
    assert quick_questions
    ok(api_client.get(f"/api/v1/ai/context/today?date={today}", headers=user_headers))
    conversation = ok(api_client.post("/api/v1/ai/conversations", json={
        "title": "RAG联调",
        "source": "daily_record",
        "related_date": today,
    }, headers=user_headers))
    conversation_id = conversation["conversation_id"]
    ai_reply = ok(api_client.post(f"/api/v1/ai/conversations/{conversation_id}/messages", json={
        "content": "请读取数据库里的RAG内容",
        "use_daily_context": True,
        "related_date": today,
    }, headers=user_headers))
    retrieval = ai_reply["retrieval"]
    assert retrieval["mode"] == "no_llm_first_last_random"
    assert retrieval["hit_count"] == 3
    assert [item["position"] for item in retrieval["items"]] == ["first", "last", "random"]
    assert ai_reply["assistant_message"]["content"].count("\n") == 2
    ok(api_client.get("/api/v1/ai/conversations?page=1&page_size=20", headers=user_headers))
    messages = ok(api_client.get(f"/api/v1/ai/conversations/{conversation_id}/messages", headers=user_headers))
    assert len(messages) == 2
    ok(api_client.delete(f"/api/v1/ai/conversations/{conversation_id}", headers=user_headers))

    profile = ok(api_client.get("/api/v1/me/profile", headers=user_headers))
    assert "user" in profile and "health_profile" in profile
    ok(api_client.put("/api/v1/me/profile", json={
        "nickname": "集成测试用户",
        "age": 57,
        "phone": "13812340926",
        "avatar_url": "",
    }, headers=user_headers))
    avatar = ok(api_client.post("/api/v1/me/avatar", data={
        "file": (BytesIO(b"\x89PNG\r\n\x1a\n"), "avatar.png"),
    }, headers=user_headers, content_type="multipart/form-data"))
    avatar_filename = avatar["avatar_url"].rsplit("/", 1)[-1]
    assert api_client.get(f"/api/v1/me/avatar/files/{avatar_filename}").status_code == 200
    ok(api_client.delete("/api/v1/me/avatar", headers=user_headers))
    ok(api_client.put("/api/v1/me/health-profile", json={
        "gender": "男",
        "age": 57,
        "height_cm": 172,
        "weight_kg": 73.5,
        "medical_history": "轻度脂肪肝",
        "chronic_types": ["hypertension", "diabetes"],
        "medication": "二甲双胍、氨氯地平",
    }, headers=user_headers))
    ok(api_client.get("/api/v1/me/settings", headers=user_headers))
    ok(api_client.put("/api/v1/me/settings", json={
        "alert_push_enabled": True,
        "daily_record_reminder_enabled": True,
        "daily_record_reminder_time": "20:30",
    }, headers=user_headers))
    ok(api_client.get("/api/v1/me/consents", headers=user_headers))
    ok(api_client.put("/api/v1/me/consents", json={
        "privacy_policy_accepted": True,
        "user_agreement_accepted": True,
        "health_data_consent": True,
    }, headers=user_headers))
    ok(api_client.post("/api/v1/me/consents/withdraw", json={"confirmation": "撤回授权"}, headers=user_headers))
    export = ok(api_client.get("/api/v1/me/data-export", headers=user_headers))
    assert export["counts"]["account"] == 1

    ok(api_client.get("/api/v1/admin/dashboard", headers=admin_headers))
    ok(api_client.get("/api/v1/admin/users?page=1&page_size=20", headers=admin_headers))
    ok(api_client.get("/api/v1/admin/users/1", headers=admin_headers))
    ok(api_client.put("/api/v1/admin/users/1", json={
        "nickname": "集成测试用户",
        "phone": "13812340926",
        "gender": "男",
        "age": 57,
        "height_cm": 172,
        "weight_kg": 73.5,
        "chronic_types": ["hypertension", "diabetes"],
        "medical_history": "轻度脂肪肝",
        "medication": "二甲双胍、氨氯地平",
    }, headers=admin_headers))
    ok(api_client.get("/api/v1/admin/reports?status=completed", headers=admin_headers))
    ok(api_client.patch(f"/api/v1/admin/reports/{report_id}/review", json={
        "status": "review_pending",
        "review_note": "管理员复核测试",
    }, headers=admin_headers))
    ok(api_client.patch("/api/v1/admin/reports/batch-review", json={
        "ids": [report_id],
        "status": "completed",
        "review_note": "批量复核测试",
    }, headers=admin_headers))

    ok(api_client.get("/api/v1/admin/foods?page=1&page_size=20", headers=admin_headers))
    food_one = ok(api_client.post("/api/v1/admin/foods", json={
        "name": "接口测试食物A",
        "category": "测试",
        "unit": "100g",
        "calories": 88,
        "sugar": 1,
        "fat": 2,
        "salt": 0.1,
    }, headers=admin_headers))
    food_two = ok(api_client.post("/api/v1/admin/foods", json={
        "name": "接口测试食物B",
        "category": "测试",
        "unit": "100g",
        "calories": 99,
        "sugar": 2,
        "fat": 3,
        "salt": 0.2,
    }, headers=admin_headers))
    ok(api_client.put(f"/api/v1/admin/foods/{food_one['id']}", json={
        "name": "接口测试食物A-更新",
        "category": "测试",
        "unit": "100g",
        "calories": 90,
        "sugar": 1,
        "fat": 2,
        "salt": 0.1,
    }, headers=admin_headers))
    ok(api_client.post("/api/v1/admin/foods/batch-delete", json={"ids": [food_two["id"]]}, headers=admin_headers))
    ok(api_client.delete(f"/api/v1/admin/foods/{food_one['id']}", headers=admin_headers))

    ok(api_client.get("/api/v1/admin/announcements?page=1&page_size=20", headers=admin_headers))
    announcement_one = ok(api_client.post("/api/v1/admin/announcements", json={
        "title": "接口测试公告A",
        "content": "公告内容",
        "is_published": False,
    }, headers=admin_headers))
    announcement_two = ok(api_client.post("/api/v1/admin/announcements", json={
        "title": "接口测试公告B",
        "content": "公告内容",
        "is_published": False,
    }, headers=admin_headers))
    ok(api_client.put(f"/api/v1/admin/announcements/{announcement_one['id']}", json={
        "title": "接口测试公告A-更新",
        "content": "公告内容更新",
        "is_published": True,
    }, headers=admin_headers))
    ok(api_client.patch("/api/v1/admin/announcements/batch-publish", json={
        "ids": [announcement_two["id"]],
        "is_published": True,
    }, headers=admin_headers))
    ok(api_client.delete(f"/api/v1/admin/announcements/{announcement_one['id']}", headers=admin_headers))

    ok(api_client.delete(f"/api/v1/reports/{report_id}", headers=user_headers))
    ok(api_client.post("/api/v1/auth/logout", headers=user_headers))
