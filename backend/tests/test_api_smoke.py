from app import create_app
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from itsdangerous import URLSafeTimedSerializer
import pytest
from werkzeug.security import generate_password_hash

from app.config import Config, validate_production_config
from app.extensions import db
from app.models import (
    AiConversation, AiMessage, Announcement, AppState, DailyRecord, DailyTask,
    DailyTaskTemplate, FoodItem, HealthAlert, HealthProfile, MealRecord,
    MedicalReport, ReportIndicator, User, UserConsent, UserLoginEvent, UserSettings, VitalRecord,
)


def client():
    app = create_app()
    return app.test_client()


def admin_headers(test_client):
    response = test_client.post("/api/v1/auth/admin-login", json={"username": "admin", "password": "admin123"})
    token = response.get_json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint():
    test_client = client()

    response = test_client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "health-check-0001"},
    )

    assert response.status_code == 200
    assert response.get_json()["code"] == 0
    assert response.get_json()["data"]["status"] == "ready"
    assert response.headers["X-Request-ID"] == "health-check-0001"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"


def test_production_config_rejects_insecure_defaults():
    with pytest.raises(RuntimeError) as error:
        validate_production_config({
            "APP_ENV": "production",
            "SECRET_KEY": "dev-only-change-me",
            "AUTH_REQUIRED": False,
            "AUTO_CREATE_TABLES": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///unsafe.db",
            "ADMIN_PASSWORD_HASH": "",
            "CORS_ORIGINS": ["*"],
            "RATELIMIT_STORAGE_URI": "memory://",
        })

    message = str(error.value)
    assert "SECRET_KEY" in message
    assert "AUTH_REQUIRED" in message
    assert "ADMIN_PASSWORD_HASH" in message
    assert "RATELIMIT_STORAGE_URI" in message
    assert "WECHAT_LOGIN_MODE" in message
    assert "WECHAT_APP_ID" in message
    assert "HEALTH_CONSENT_REQUIRED" in message


def test_code2session_login_creates_user_and_logout_revokes_token():
    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "wechat-login-test.db"

        class WechatConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
            UPLOAD_FOLDER = str(Path(temp_dir) / "uploads")
            AUTO_CREATE_TABLES = True
            PERSIST_DEMO_STATE = False
            DOMAIN_REPOSITORIES_ENABLED = False
            AUTH_REQUIRED = True
            TOKEN_VERSION_REQUIRED = True
            WECHAT_LOGIN_MODE = "code2session"
            WECHAT_APP_ID = "test-app-id"
            WECHAT_APP_SECRET = "test-app-secret"
            RATELIMIT_STORAGE_URI = "memory://"

        class FakeWechatResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"openid":"openid-user-2","unionid":"unionid-user-2"}'

        captured = {}

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            return FakeWechatResponse()

        app = create_app(WechatConfig)
        test_client = app.test_client()
        with patch("app.services.wechat_auth.urlopen", side_effect=fake_urlopen):
            first_login = test_client.post(
                "/api/v1/auth/wechat-login",
                json={"code": "single-use-code", "nickname": "新微信用户"},
                headers={"X-Request-ID": "wechat-login-0001"},
            )
            first_token = first_login.get_json()["data"]["token"]
            profile_before_logout = test_client.get(
                "/api/v1/me/profile",
                headers={"Authorization": f"Bearer {first_token}"},
            )
            logout = test_client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {first_token}"},
            )
            revoked = test_client.get(
                "/api/v1/me/profile",
                headers={"Authorization": f"Bearer {first_token}"},
            )
            second_login = test_client.post(
                "/api/v1/auth/wechat-login",
                json={"code": "another-single-use-code"},
                headers={"X-Request-ID": "wechat-login-0002"},
            )

        assert first_login.status_code == 200
        assert profile_before_logout.status_code == 200
        assert logout.status_code == 200
        assert revoked.status_code == 401
        assert second_login.status_code == 200
        assert "appid=test-app-id" in captured["url"]
        assert "secret=test-app-secret" in captured["url"]
        assert captured["timeout"] == WechatConfig.WECHAT_API_TIMEOUT_SECONDS

        with app.app_context():
            user = User.query.filter_by(openid="openid-user-2").one()
            assert user.unionid == "unionid-user-2"
            assert user.username == "新微信用户"
            assert user.login_count == 2
            assert user.token_version == 2
            assert HealthProfile.query.filter_by(user_id=user.id).count() == 1
            assert UserSettings.query.filter_by(user_id=user.id).count() == 1
            assert UserLoginEvent.query.filter_by(user_id=user.id, success=True).count() == 2
            db.session.remove()
            db.engine.dispose()


def test_code2session_invalid_code_is_audited_without_creating_user():
    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "wechat-failure-test.db"

        class WechatFailureConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
            UPLOAD_FOLDER = str(Path(temp_dir) / "uploads")
            AUTO_CREATE_TABLES = True
            PERSIST_DEMO_STATE = False
            DOMAIN_REPOSITORIES_ENABLED = False
            WECHAT_LOGIN_MODE = "code2session"
            WECHAT_APP_ID = "test-app-id"
            WECHAT_APP_SECRET = "test-app-secret"
            RATELIMIT_STORAGE_URI = "memory://"

        class InvalidCodeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"errcode":40029,"errmsg":"invalid code"}'

        app = create_app(WechatFailureConfig)
        test_client = app.test_client()
        with patch("app.services.wechat_auth.urlopen", return_value=InvalidCodeResponse()):
            response = test_client.post(
                "/api/v1/auth/wechat-login",
                json={"code": "invalid-code"},
                headers={"X-Request-ID": "wechat-failure-0001"},
            )

        assert response.status_code == 401
        assert response.get_json()["code"] == 40105
        with app.app_context():
            assert User.query.count() == 0
            event = UserLoginEvent.query.one()
            assert event.success is False
            assert event.failure_code == "WECHAT_40029"
            assert event.request_id == "wechat-failure-0001"
            assert len(event.client_ip_hash) == 64
            db.session.remove()
            db.engine.dispose()


def test_admin_disable_user_revokes_existing_token():
    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "disable-user-test.db"

        class DisableUserConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
            UPLOAD_FOLDER = str(Path(temp_dir) / "uploads")
            AUTO_CREATE_TABLES = True
            PERSIST_DEMO_STATE = False
            DOMAIN_REPOSITORIES_ENABLED = False
            AUTH_REQUIRED = True
            TOKEN_VERSION_REQUIRED = True
            WECHAT_LOGIN_MODE = "mock"
            WECHAT_MOCK_OPENID = "disable-test-openid"
            RATELIMIT_STORAGE_URI = "memory://"

        app = create_app(DisableUserConfig)
        test_client = app.test_client()
        login = test_client.post("/api/v1/auth/wechat-login", json={"code": "local-test-code"})
        user = login.get_json()["data"]["user"]
        user_headers = {"Authorization": f"Bearer {login.get_json()['data']['token']}"}
        headers = admin_headers(test_client)

        assert test_client.get("/api/v1/me/profile", headers=user_headers).status_code == 200
        assert test_client.put(
            f"/api/v1/admin/users/{user['id']}", json={"status": True}, headers=headers
        ).status_code == 400
        disabled = test_client.put(
            f"/api/v1/admin/users/{user['id']}", json={"status": 0}, headers=headers
        )
        assert disabled.status_code == 200
        assert disabled.get_json()["data"]["status"] == 0
        assert test_client.get("/api/v1/me/profile", headers=user_headers).status_code == 403
        assert test_client.post("/api/v1/auth/wechat-login", json={"code": "new-code"}).status_code == 403

        with app.app_context():
            row = db.session.get(User, user["id"])
            assert row.token_version == 2
            assert UserLoginEvent.query.filter_by(
                user_id=user["id"], success=False, failure_code="ACCOUNT_DISABLED"
            ).count() == 1
            db.session.remove()
            db.engine.dispose()


def test_versioned_health_data_consent_contract():
    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "consent-test.db"

        class ConsentConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
            UPLOAD_FOLDER = str(Path(temp_dir) / "uploads")
            AUTO_CREATE_TABLES = True
            PERSIST_DEMO_STATE = False
            DOMAIN_REPOSITORIES_ENABLED = False
            AUTH_REQUIRED = True
            TOKEN_VERSION_REQUIRED = True
            WECHAT_LOGIN_MODE = "mock"
            WECHAT_MOCK_OPENID = "consent-test-openid"
            RATELIMIT_STORAGE_URI = "memory://"
            PRIVACY_POLICY_VERSION = "privacy-v1"
            USER_AGREEMENT_VERSION = "agreement-v1"
            HEALTH_DATA_CONSENT_VERSION = "health-v1"

        app = create_app(ConsentConfig)
        test_client = app.test_client()
        login = test_client.post("/api/v1/auth/wechat-login", json={"code": "consent-code"})
        headers = {"Authorization": f"Bearer {login.get_json()['data']['token']}"}

        before = test_client.get("/api/v1/me/consents", headers=headers)
        assert before.status_code == 200
        assert before.get_json()["data"]["required_complete"] is False
        invalid = test_client.put(
            "/api/v1/me/consents",
            json={
                "privacy_policy_accepted": True,
                "user_agreement_accepted": True,
                "health_data_consent": False,
            },
            headers=headers,
        )
        assert invalid.status_code == 400

        accepted = test_client.put(
            "/api/v1/me/consents",
            json={
                "privacy_policy_accepted": True,
                "user_agreement_accepted": True,
                "health_data_consent": True,
            },
            headers=headers,
        )
        assert accepted.status_code == 200
        assert accepted.get_json()["data"]["required_complete"] is True
        assert accepted.get_json()["data"]["versions"]["privacy_policy"] == "privacy-v1"

        app.config["PRIVACY_POLICY_VERSION"] = "privacy-v2"
        outdated = test_client.get("/api/v1/me/consents", headers=headers)
        assert outdated.get_json()["data"]["required_complete"] is False
        assert outdated.get_json()["data"]["privacy_policy_accepted"] is False

        with app.app_context():
            row = UserConsent.query.one()
            assert row.health_data_consent is True
            assert row.accepted_at is not None
            db.session.remove()
            db.engine.dispose()


def test_health_consent_withdrawal_blocks_sensitive_apis_and_allows_reauthorization():
    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "consent-withdrawal-test.db"

        class ConsentWithdrawalConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
            UPLOAD_FOLDER = str(Path(temp_dir) / "uploads")
            AUTO_CREATE_TABLES = True
            PERSIST_DEMO_STATE = False
            DOMAIN_REPOSITORIES_ENABLED = False
            AUTH_REQUIRED = True
            TOKEN_VERSION_REQUIRED = True
            HEALTH_CONSENT_REQUIRED = True
            WECHAT_LOGIN_MODE = "mock"
            WECHAT_MOCK_OPENID = "consent-withdrawal-openid"
            RATELIMIT_STORAGE_URI = "memory://"
            PRIVACY_POLICY_VERSION = "privacy-v1"
            USER_AGREEMENT_VERSION = "agreement-v1"
            HEALTH_DATA_CONSENT_VERSION = "health-v1"

        app = create_app(ConsentWithdrawalConfig)
        test_client = app.test_client()
        login = test_client.post("/api/v1/auth/wechat-login", json={"code": "withdraw-code"})
        headers = {"Authorization": f"Bearer {login.get_json()['data']['token']}"}
        consent_payload = {
            "privacy_policy_accepted": True,
            "user_agreement_accepted": True,
            "health_data_consent": True,
        }

        assert test_client.get("/api/v1/me/profile", headers=headers).status_code == 200
        blocked_before = test_client.get("/api/v1/daily-records/today", headers=headers)
        assert blocked_before.status_code == 403
        assert blocked_before.get_json()["code"] == 40303

        accepted = test_client.put("/api/v1/me/consents", json=consent_payload, headers=headers)
        assert accepted.status_code == 200
        assert test_client.get("/api/v1/daily-records/today", headers=headers).status_code == 200

        invalid = test_client.post(
            "/api/v1/me/consents/withdraw", json={"confirmation": "确认"}, headers=headers
        )
        assert invalid.status_code == 400
        withdrawn = test_client.post(
            "/api/v1/me/consents/withdraw", json={"confirmation": "撤回授权"}, headers=headers
        )
        assert withdrawn.status_code == 200
        assert withdrawn.get_json()["data"]["required_complete"] is False
        assert withdrawn.get_json()["data"]["withdrawn_at"] is not None
        assert test_client.get("/api/v1/reports/history", headers=headers).status_code == 403
        assert test_client.get("/api/v1/ai/context/today", headers=headers).status_code == 403
        assert test_client.get("/api/v1/me/data-export", headers=headers).status_code == 200

        reaccepted = test_client.put("/api/v1/me/consents", json=consent_payload, headers=headers)
        assert reaccepted.status_code == 200
        assert reaccepted.get_json()["data"]["withdrawn_at"] is None
        assert test_client.get("/api/v1/daily-records/today", headers=headers).status_code == 200

        with app.app_context():
            row = UserConsent.query.one()
            assert row.health_data_consent is True
            assert row.withdrawn_at is None
            db.session.remove()
            db.engine.dispose()


def test_admin_login_supports_password_hash_and_rate_limit():
    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "security-test.db"

        class SecurityConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
            UPLOAD_FOLDER = str(Path(temp_dir) / "uploads")
            AUTO_CREATE_TABLES = False
            PERSIST_DEMO_STATE = False
            DOMAIN_REPOSITORIES_ENABLED = False
            ADMIN_PASSWORD_HASH = generate_password_hash("strong-admin-password")
            ADMIN_LOGIN_RATE_LIMIT = "2 per minute"
            RATELIMIT_STORAGE_URI = "memory://"

        app = create_app(SecurityConfig)
        test_client = app.test_client()
        remote = {"REMOTE_ADDR": "192.0.2.55"}
        success_response = test_client.post(
            "/api/v1/auth/admin-login",
            json={"username": "admin", "password": "strong-admin-password"},
            environ_base=remote,
        )
        invalid_response = test_client.post(
            "/api/v1/auth/admin-login",
            json={"username": "admin", "password": "wrong-password"},
            environ_base=remote,
        )
        limited_response = test_client.post(
            "/api/v1/auth/admin-login",
            json={"username": "admin", "password": "wrong-password"},
            environ_base=remote,
        )

        assert success_response.status_code == 200
        assert invalid_response.status_code == 401
        assert limited_response.status_code == 429

        with app.app_context():
            db.session.remove()
            db.engine.dispose()


def test_sqlite_bigint_variant_supports_autoincrement():
    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "migration-test.db"

        class TestConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
            UPLOAD_FOLDER = str(Path(temp_dir) / "uploads")
            AUTO_CREATE_TABLES = True
            PERSIST_DEMO_STATE = False
            DOMAIN_REPOSITORIES_ENABLED = False
            AUTH_REQUIRED = False

        app = create_app(TestConfig)
        with app.app_context():
            try:
                user = User(username="migration-test", created_at=datetime.now(), updated_at=datetime.now())
                db.session.add(user)
                db.session.commit()
                assert user.id == 1
            finally:
                db.session.remove()
                db.engine.dispose()


def test_reference_repositories_import_and_persist_without_app_state_duplication():
    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "reference-repository.db"

        class RepositoryConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
            UPLOAD_FOLDER = str(Path(temp_dir) / "uploads")
            AUTO_CREATE_TABLES = True
            PERSIST_DEMO_STATE = True
            DOMAIN_REPOSITORIES_ENABLED = True
            AUTH_REQUIRED = False

        app = create_app(RepositoryConfig)
        test_client = app.test_client()
        headers = admin_headers(test_client)

        with app.app_context():
            assert FoodItem.query.count() == 2
            assert Announcement.query.count() == 1
            state = db.session.get(AppState, "demo-store-v1")
            assert "food_items" not in state.payload
            assert "announcements" not in state.payload
            assert state.payload["domain_migrations"]["reference-repositories-v1"] is True

        created = test_client.post("/api/v1/admin/foods", json={
            "name": "Repository 持久化测试",
            "category": "测试",
            "unit": "50g",
            "calories": 88,
            "sugar": 1.2,
            "fat": 2.3,
            "salt": 0.1,
        }, headers=headers)
        assert created.status_code == 200
        food_id = created.get_json()["data"]["id"]

        with app.app_context():
            db.session.remove()
            db.engine.dispose()

        restarted_app = create_app(RepositoryConfig)
        with restarted_app.app_context():
            row = db.session.get(FoodItem, food_id)
            assert row is not None
            assert row.unit == "50g"

        restarted_client = restarted_app.test_client()
        restarted_headers = admin_headers(restarted_client)
        assert restarted_client.delete(
            f"/api/v1/admin/foods/{food_id}", headers=restarted_headers
        ).status_code == 200

        with restarted_app.app_context():
            FoodItem.query.delete()
            db.session.commit()
            db.session.remove()
            db.engine.dispose()

        empty_restart_app = create_app(RepositoryConfig)
        with empty_restart_app.app_context():
            assert FoodItem.query.count() == 0
            db.session.remove()
            db.engine.dispose()


def test_user_repositories_import_persist_and_isolate_by_token_user_id():
    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "user-repository.db"

        class UserRepositoryConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
            UPLOAD_FOLDER = str(Path(temp_dir) / "uploads")
            AUTO_CREATE_TABLES = True
            PERSIST_DEMO_STATE = True
            DOMAIN_REPOSITORIES_ENABLED = True
            AUTH_REQUIRED = True
            SECRET_KEY = "user-repository-test-secret"

        app = create_app(UserRepositoryConfig)
        with app.app_context():
            assert User.query.count() == 1
            assert HealthProfile.query.count() == 1
            assert UserSettings.query.count() == 1
            state = db.session.get(AppState, "demo-store-v1")
            assert "user" not in state.payload
            assert "health_profile" not in state.payload
            assert "settings" not in state.payload
            assert state.payload["domain_migrations"]["user-repositories-v1"] is True

            now = datetime.now()
            second_user = User(
                openid="isolated-openid",
                username="隔离用户",
                phone="13900000002",
                role="user",
                status=1,
                created_at=now,
                updated_at=now,
            )
            db.session.add(second_user)
            db.session.flush()
            db.session.add(HealthProfile(
                user_id=second_user.id,
                age=35,
                chronic_types=["hypertension"],
                created_at=now,
                updated_at=now,
            ))
            db.session.add(UserSettings(
                user_id=second_user.id,
                alert_push_enabled=True,
                daily_record_reminder_enabled=True,
                daily_record_reminder_time="20:30",
                created_at=now,
                updated_at=now,
            ))
            db.session.commit()
            second_user_id = second_user.id

        serializer = URLSafeTimedSerializer(UserRepositoryConfig.SECRET_KEY, salt="wechat-login")
        token = serializer.dumps({"user_id": second_user_id, "role": "user"})
        headers = {"Authorization": f"Bearer {token}"}
        test_client = app.test_client()

        profile = test_client.get("/api/v1/me/profile", headers=headers).get_json()["data"]
        assert profile["user"]["nickname"] == "隔离用户"
        assert profile["health_profile"]["age"] == 35

        updated = test_client.put(
            "/api/v1/me/profile",
            json={"nickname": "隔离用户已更新", "age": 36},
            headers=headers,
        )
        assert updated.status_code == 200
        saved_settings = test_client.put(
            "/api/v1/me/settings",
            json={
                "alert_push_enabled": False,
                "daily_record_reminder_enabled": True,
                "daily_record_reminder_time": "18:45",
            },
            headers=headers,
        )
        assert saved_settings.get_json()["data"]["daily_record_reminder_time"] == "18:45"

        with app.app_context():
            assert db.session.get(User, 1).username != "隔离用户已更新"
            db.session.remove()
            db.engine.dispose()

        restarted_app = create_app(UserRepositoryConfig)
        restarted_client = restarted_app.test_client()
        restarted_profile = restarted_client.get("/api/v1/me/profile", headers=headers).get_json()["data"]
        assert restarted_profile["user"]["nickname"] == "隔离用户已更新"
        assert restarted_profile["health_profile"]["age"] == 36
        restarted_settings = restarted_client.get("/api/v1/me/settings", headers=headers).get_json()["data"]
        assert restarted_settings["daily_record_reminder_time"] == "18:45"

        with restarted_app.app_context():
            db.session.remove()
            db.engine.dispose()


def test_daily_repositories_import_restart_and_user_isolation():
    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "daily-repository.db"

        class DailyRepositoryConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
            UPLOAD_FOLDER = str(Path(temp_dir) / "uploads")
            AUTO_CREATE_TABLES = True
            PERSIST_DEMO_STATE = True
            DOMAIN_REPOSITORIES_ENABLED = True
            AUTH_REQUIRED = True
            SECRET_KEY = "daily-repository-test-secret"

        app = create_app(DailyRepositoryConfig)
        test_client = app.test_client()
        user_login = test_client.post("/api/v1/auth/wechat-login", json={"code": "daily-user"}).get_json()
        user_headers = {"Authorization": f"Bearer {user_login['data']['token']}"}

        with app.app_context():
            assert DailyRecord.query.count() == 2
            assert VitalRecord.query.count() == 2
            assert MealRecord.query.count() == 2
            state = db.session.get(AppState, "demo-store-v1")
            assert "daily_records_by_id" not in state.payload
            assert "vitals_by_record_id" not in state.payload
            assert "meals_by_record_id" not in state.payload
            assert state.payload["domain_migrations"]["daily-repositories-v1"] is True

        today_payload = test_client.get("/api/v1/daily-records/today", headers=user_headers).get_json()["data"]
        record_id = today_payload["record"]["id"]
        assert today_payload["vitals"]["systolic_pressure"] == 138
        assert today_payload["nutrition"]["calories"] == 590

        assert test_client.patch(
            f"/api/v1/daily-records/{record_id}",
            json={"note": "Repository 重启测试", "mood": "愉快"},
            headers=user_headers,
        ).status_code == 200
        assert test_client.patch(
            f"/api/v1/daily-records/{record_id}/vitals",
            json={"systolic_pressure": 126, "diastolic_pressure": 81, "fasting_glucose": 5.7},
            headers=user_headers,
        ).status_code == 200
        meal = test_client.post(
            f"/api/v1/daily-records/{record_id}/meals",
            json={
                "meal_type": "dinner",
                "meal_name": "重启测试晚餐",
                "foods": [{"name": "玉米", "amount": "半根", "calories": 80, "sugar": 1}],
            },
            headers=user_headers,
        )
        assert meal.status_code == 200

        with app.app_context():
            now = datetime.now()
            second_user = User(
                openid="daily-isolated-openid", username="每日隔离用户", role="user", status=1,
                created_at=now, updated_at=now,
            )
            db.session.add(second_user)
            db.session.commit()
            second_user_id = second_user.id

        serializer = URLSafeTimedSerializer(DailyRepositoryConfig.SECRET_KEY, salt="wechat-login")
        second_token = serializer.dumps({"user_id": second_user_id, "role": "user"})
        second_headers = {"Authorization": f"Bearer {second_token}"}
        assert test_client.patch(
            f"/api/v1/daily-records/{record_id}", json={"note": "越权修改"}, headers=second_headers
        ).status_code == 404
        second_today = test_client.get("/api/v1/daily-records/today", headers=second_headers).get_json()["data"]
        assert second_today["record"]["id"] != record_id
        assert second_today["vitals"] == {}
        assert len(second_today["tasks"]) == 1
        assert second_today["tasks"][0]["id"] not in {row["id"] for row in today_payload["tasks"]}

        with app.app_context():
            db.session.remove()
            db.engine.dispose()

        restarted_app = create_app(DailyRepositoryConfig)
        restarted_client = restarted_app.test_client()
        restarted = restarted_client.get("/api/v1/daily-records/today", headers=user_headers).get_json()["data"]
        assert restarted["record"]["note"] == "Repository 重启测试"
        assert restarted["vitals"]["systolic_pressure"] == 126
        assert any(row["meal_name"] == "重启测试晚餐" for row in restarted_client.get(
            f"/api/v1/daily-records/{record_id}/meals", headers=user_headers
        ).get_json()["data"]["meals"])

        with restarted_app.app_context():
            db.session.remove()
            db.engine.dispose()


def test_remaining_repositories_restart_isolation_and_app_state_cleanup():
    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / "remaining-repositories.db"

        class RemainingConfig(Config):
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
            UPLOAD_FOLDER = str(Path(temp_dir) / "uploads")
            AUTO_CREATE_TABLES = True
            PERSIST_DEMO_STATE = True
            DOMAIN_REPOSITORIES_ENABLED = True
            AUTH_REQUIRED = True
            SECRET_KEY = "remaining-repositories-test-secret"

        app = create_app(RemainingConfig)
        client_one = app.test_client()
        login = client_one.post("/api/v1/auth/wechat-login", json={"code": "remaining-user"}).get_json()
        headers_one = {"Authorization": f"Bearer {login['data']['token']}"}

        with app.app_context():
            assert DailyTaskTemplate.query.count() == 2
            assert DailyTask.query.count() == 9
            assert HealthAlert.query.count() == 1
            assert MedicalReport.query.count() == 1
            assert ReportIndicator.query.count() == 2
            assert AiConversation.query.count() == 1
            assert AiMessage.query.count() == 2
            state = db.session.get(AppState, "demo-store-v1")
            assert set(state.payload) == {"domain_migrations"}
            assert len(state.payload["domain_migrations"]) == 6

        today = client_one.get("/api/v1/daily-records/today", headers=headers_one).get_json()["data"]
        task_id = today["tasks"][0]["id"]
        assert client_one.patch(
            f"/api/v1/daily-tasks/{task_id}", json={"is_done": False}, headers=headers_one
        ).status_code == 200
        alerts = client_one.get("/api/v1/alerts", headers=headers_one).get_json()["data"]
        alert_id = alerts[0]["id"]
        assert client_one.patch(f"/api/v1/alerts/{alert_id}/read", headers=headers_one).status_code == 200
        report_id = client_one.get("/api/v1/reports/history", headers=headers_one).get_json()["data"]["items"][0]["id"]
        conversation = client_one.post(
            "/api/v1/ai/conversations", json={"title": "Repository restart"}, headers=headers_one
        ).get_json()["data"]
        conversation_id = conversation["conversation_id"]
        assert client_one.post(
            f"/api/v1/ai/conversations/{conversation_id}/messages",
            json={"content": "血压偏高怎么办"}, headers=headers_one,
        ).status_code == 200

        with app.app_context():
            now = datetime.now()
            second_user = User(
                openid="remaining-isolated-openid", username="剩余迁移隔离用户",
                role="user", status=1, created_at=now, updated_at=now,
            )
            db.session.add(second_user)
            db.session.commit()
            second_id = second_user.id

        serializer = URLSafeTimedSerializer(RemainingConfig.SECRET_KEY, salt="wechat-login")
        headers_two = {"Authorization": f"Bearer {serializer.dumps({'user_id': second_id, 'role': 'user'})}"}
        assert client_one.get(f"/api/v1/reports/{report_id}", headers=headers_two).status_code == 404
        assert client_one.get(
            f"/api/v1/ai/conversations/{conversation_id}/messages", headers=headers_two
        ).status_code == 404
        assert client_one.patch(
            f"/api/v1/daily-tasks/{task_id}", json={"is_done": True}, headers=headers_two
        ).status_code == 404

        with app.app_context():
            db.session.remove()
            db.engine.dispose()

        restarted = create_app(RemainingConfig)
        client_restarted = restarted.test_client()
        restarted_today = client_restarted.get(
            "/api/v1/daily-records/today", headers=headers_one
        ).get_json()["data"]
        assert next(row for row in restarted_today["tasks"] if row["id"] == task_id)["is_done"] is False
        restarted_alerts = client_restarted.get("/api/v1/alerts", headers=headers_one).get_json()["data"]
        assert next(row for row in restarted_alerts if row["id"] == alert_id)["is_read"] is True
        restarted_messages = client_restarted.get(
            f"/api/v1/ai/conversations/{conversation_id}/messages", headers=headers_one
        ).get_json()["data"]
        assert len(restarted_messages) == 2
        assert client_restarted.delete(
            f"/api/v1/ai/conversations/{conversation_id}", headers=headers_one
        ).status_code == 200

        with restarted.app_context():
            db.session.remove()
            db.engine.dispose()


def test_daily_page_contract():
    test_client = client()

    response = test_client.get("/api/v1/daily-records/today")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["code"] == 0
    assert "record" in payload["data"]
    assert "tasks" in payload["data"]
    assert "vitals" in payload["data"]


def test_daily_task_template_update_keeps_api_shape():
    test_client = client()

    response = test_client.put("/api/v1/daily-task-templates/current", json={
        "effective_date": "2026-08-18",
        "items": [
            {"task_name": "晨间血压", "sort_order": 1},
            {"task_name": "空腹血糖", "sort_order": 2},
            {"task_name": "晚间复测", "sort_order": 3},
        ],
    })
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["code"] == 0
    assert payload["data"]["effective_from"] == "2026-08-18"
    assert len(payload["data"]["items"]) == 3


def test_mine_page_contract():
    test_client = client()

    response = test_client.get("/api/v1/me/profile")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["code"] == 0
    assert "user" in payload["data"]
    assert "health_profile" in payload["data"]


def test_personal_data_export_excludes_security_fields():
    test_client = client()
    response = test_client.get("/api/v1/me/data-export")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["code"] == 0
    export = payload["data"]
    assert export["schema_version"] == "1.0"
    assert export["user_id"] == 1
    assert export["counts"]["account"] == 1
    assert "openid" not in export["data"]["account"]
    assert "unionid" not in export["data"]["account"]
    assert "token_version" not in export["data"]["account"]
    assert all("file_url" not in item and "ocr_doc_id" not in item for item in export["data"]["medical_reports"])
    assert all("mongo_trace_id" not in item for item in export["data"]["ai_messages"])


def test_ai_message_contract():
    test_client = client()
    created = test_client.post("/api/v1/ai/conversations", json={"title": "血压偏高怎么办"}).get_json()
    conversation_id = created["data"]["conversation_id"]

    response = test_client.post(
        f"/api/v1/ai/conversations/{conversation_id}/messages",
        json={"content": "血压偏高怎么办", "use_daily_context": True},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["code"] == 0
    assert "assistant_message" in payload["data"]


def test_report_history_contract():
    test_client = client()

    response = test_client.get("/api/v1/reports/history")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["code"] == 0
    assert "items" in payload["data"]


def test_report_recognition_progress_contract():
    test_client = client()

    start_response = test_client.post("/api/v1/reports/601/recognize")
    progress_response = test_client.get("/api/v1/reports/601/progress")

    assert start_response.status_code == 200
    assert start_response.get_json()["code"] == 0
    assert progress_response.status_code == 200
    assert progress_response.get_json()["data"]["progress"] >= 10


def test_admin_users_contract():
    test_client = client()
    headers = admin_headers(test_client)

    response = test_client.get("/api/v1/admin/users", headers=headers)
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["code"] == 0
    assert "items" in payload["data"]
    assert payload["data"]["total"] == 1
    second_page = test_client.get("/api/v1/admin/users?page=2&page_size=1", headers=headers).get_json()["data"]
    assert second_page["items"] == []
    assert second_page["total"] == 1


def test_admin_user_health_profile_edit_contract():
    app = create_app()
    app.config.update(PERSIST_DEMO_STATE=False)
    test_client = app.test_client()
    headers = admin_headers(test_client)

    detail_response = test_client.get("/api/v1/admin/users/1", headers=headers)
    assert detail_response.status_code == 200
    original = detail_response.get_json()["data"]
    restore_payload = {key: original[key] for key in (
        "nickname", "phone", "gender", "age", "height_cm", "weight_kg",
        "chronic_types", "medical_history", "medication",
    )}

    try:
        invalid_phone = test_client.put("/api/v1/admin/users/1", json={"phone": "123"}, headers=headers)
        assert invalid_phone.status_code == 400
        invalid_chronic = test_client.put(
            "/api/v1/admin/users/1", json={"chronic_types": ["unknown"]}, headers=headers
        )
        assert invalid_chronic.status_code == 400
        assert test_client.get("/api/v1/admin/users/999", headers=headers).status_code == 404

        updated = test_client.put("/api/v1/admin/users/1", json={
            "nickname": "档案验收用户",
            "phone": "13912345678",
            "gender": "女",
            "age": 52,
            "height_cm": 165.5,
            "weight_kg": 62.5,
            "chronic_types": ["hypertension", "hyperlipidemia"],
            "medical_history": "管理员端测试病史",
            "medication": "管理员端测试用药",
        }, headers=headers)
        assert updated.status_code == 200
        data = updated.get_json()["data"]
        assert data["nickname"] == "档案验收用户"
        assert data["chronic_types"] == ["hypertension", "hyperlipidemia"]
        assert data["bmi"] == 22.8
        profile = test_client.get("/api/v1/me/profile").get_json()["data"]
        assert profile["user"]["nickname"] == "档案验收用户"
        assert profile["health_profile"]["medical_history"] == "管理员端测试病史"
    finally:
        restored = test_client.put("/api/v1/admin/users/1", json=restore_payload, headers=headers)
        assert restored.status_code == 200


def test_admin_login_and_role_guard_contract():
    test_client = client()
    assert test_client.get("/api/v1/admin/dashboard").status_code == 401

    invalid = test_client.post("/api/v1/auth/admin-login", json={"username": "admin", "password": "wrong"})
    assert invalid.status_code == 401

    user_token = test_client.post("/api/v1/auth/wechat-login", json={"code": "normal-user"}).get_json()["data"]["token"]
    forbidden = test_client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {user_token}"})
    assert forbidden.status_code == 403

    allowed = test_client.get("/api/v1/admin/dashboard", headers=admin_headers(test_client))
    assert allowed.status_code == 200


def test_admin_management_crud_and_validation_contract():
    app = create_app()
    with TemporaryDirectory() as upload_dir:
        app.config.update(PERSIST_DEMO_STATE=False, UPLOAD_FOLDER=upload_dir)
        test_client = app.test_client()
        headers = admin_headers(test_client)

        invalid_food = test_client.post("/api/v1/admin/foods", json={"name": "", "calories": -1}, headers=headers)
        assert invalid_food.status_code == 400
        created_food = test_client.post("/api/v1/admin/foods", json={
            "name": "测试燕麦",
            "category": "主食",
            "unit": "100g",
            "calories": 368,
            "sugar": 1.2,
            "fat": 6.7,
            "salt": 0.01,
        }, headers=headers)
        assert created_food.status_code == 200
        food_id = created_food.get_json()["data"]["id"]
        updated_food = test_client.put(f"/api/v1/admin/foods/{food_id}", json={
            "name": "测试燕麦片",
            "category": "主食",
            "unit": "100g",
            "calories": 360,
            "sugar": 1,
            "fat": 6,
            "salt": 0.01,
        }, headers=headers)
        assert updated_food.get_json()["data"]["name"] == "测试燕麦片"
        assert test_client.delete(f"/api/v1/admin/foods/{food_id}", headers=headers).status_code == 200

        invalid_announcement = test_client.post("/api/v1/admin/announcements", json={"title": "", "content": ""}, headers=headers)
        assert invalid_announcement.status_code == 400
        created_announcement = test_client.post("/api/v1/admin/announcements", json={
            "title": "测试公告",
            "content": "这是一条接口测试公告。",
            "is_published": False,
        }, headers=headers)
        announcement_id = created_announcement.get_json()["data"]["id"]
        updated_announcement = test_client.put(f"/api/v1/admin/announcements/{announcement_id}", json={
            "title": "测试公告已更新",
            "content": "更新后的测试内容。",
            "is_published": True,
        }, headers=headers)
        assert updated_announcement.get_json()["data"]["is_published"] is True
        assert test_client.delete(f"/api/v1/admin/announcements/{announcement_id}", headers=headers).status_code == 200

        uploaded = test_client.post("/api/v1/reports/upload", data={
            "file": (BytesIO(b"admin review image"), "admin-review.jpg"),
        }, content_type="multipart/form-data")
        report_id = uploaded.get_json()["data"]["report_id"]
        invalid_review = test_client.patch(f"/api/v1/admin/reports/{report_id}/review", json={"status": "unknown"}, headers=headers)
        assert invalid_review.status_code == 400
        reviewed = test_client.patch(f"/api/v1/admin/reports/{report_id}/review", json={
            "status": "rejected",
            "review_note": "图片不清晰，请重新上传",
        }, headers=headers)
        assert reviewed.status_code == 200
        assert reviewed.get_json()["data"]["status"] == "rejected"
        assert test_client.delete(f"/api/v1/reports/{report_id}").status_code == 200


def test_admin_batch_management_contract():
    app = create_app()
    with TemporaryDirectory() as upload_dir:
        app.config.update(PERSIST_DEMO_STATE=False, UPLOAD_FOLDER=upload_dir)
        test_client = app.test_client()
        headers = admin_headers(test_client)

        assert test_client.post("/api/v1/admin/foods/batch-delete", json={"ids": []}).status_code == 401
        invalid_ids = test_client.post("/api/v1/admin/foods/batch-delete", json={"ids": []}, headers=headers)
        assert invalid_ids.status_code == 400
        too_many = test_client.post(
            "/api/v1/admin/foods/batch-delete", json={"ids": list(range(1, 102))}, headers=headers
        )
        assert too_many.status_code == 400

        food_ids = []
        for index in range(2):
            created = test_client.post("/api/v1/admin/foods", json={
                "name": f"批量测试食物{index + 1}", "category": "测试", "unit": "100g",
                "calories": 100, "sugar": 1, "fat": 1, "salt": 0.1,
            }, headers=headers)
            food_ids.append(created.get_json()["data"]["id"])
        deleted = test_client.post(
            "/api/v1/admin/foods/batch-delete",
            json={"ids": [food_ids[0], food_ids[0], food_ids[1], 999999]},
            headers=headers,
        )
        assert deleted.status_code == 200
        assert deleted.get_json()["data"]["processed_count"] == 2
        assert deleted.get_json()["data"]["missing_ids"] == [999999]

        announcement_ids = []
        for index in range(2):
            created = test_client.post("/api/v1/admin/announcements", json={
                "title": f"批量测试公告{index + 1}", "content": "批量发布契约测试", "is_published": False,
            }, headers=headers)
            announcement_ids.append(created.get_json()["data"]["id"])
        invalid_publish = test_client.patch(
            "/api/v1/admin/announcements/batch-publish",
            json={"ids": announcement_ids, "is_published": "true"}, headers=headers,
        )
        assert invalid_publish.status_code == 400
        published = test_client.patch(
            "/api/v1/admin/announcements/batch-publish",
            json={"ids": announcement_ids, "is_published": True}, headers=headers,
        )
        assert published.get_json()["data"]["processed_count"] == 2
        rows = test_client.get("/api/v1/admin/announcements?page_size=100", headers=headers).get_json()["data"]["items"]
        assert all(row["is_published"] for row in rows if row["id"] in announcement_ids)
        for announcement_id in announcement_ids:
            assert test_client.delete(f"/api/v1/admin/announcements/{announcement_id}", headers=headers).status_code == 200

        report_ids = []
        for index in range(2):
            uploaded = test_client.post("/api/v1/reports/upload", data={
                "file": (BytesIO(f"batch report {index}".encode()), f"batch-report-{index}.jpg"),
            }, content_type="multipart/form-data")
            report_ids.append(uploaded.get_json()["data"]["report_id"])
        invalid_review = test_client.patch(
            "/api/v1/admin/reports/batch-review",
            json={"ids": report_ids, "status": "unknown"}, headers=headers,
        )
        assert invalid_review.status_code == 400
        reviewed = test_client.patch(
            "/api/v1/admin/reports/batch-review",
            json={"ids": report_ids, "status": "completed", "review_note": "批量审核测试"},
            headers=headers,
        )
        assert reviewed.status_code == 200
        assert reviewed.get_json()["data"]["processed_count"] == 2
        for report_id in report_ids:
            assert test_client.get(f"/api/v1/reports/{report_id}").get_json()["data"]["status"] == "completed"
            assert test_client.delete(f"/api/v1/reports/{report_id}").status_code == 200


def test_vitals_validation_and_save_contract():
    test_client = client()
    record_id = test_client.get("/api/v1/daily-records/today").get_json()["data"]["record"]["id"]

    invalid = test_client.patch(f"/api/v1/daily-records/{record_id}/vitals", json={"systolic_pressure": 999})
    assert invalid.status_code == 400

    saved = test_client.patch(f"/api/v1/daily-records/{record_id}/vitals", json={
        "systolic_pressure": 128,
        "diastolic_pressure": 82,
        "fasting_glucose": 5.8,
        "postprandial_glucose": 7.1,
        "weight_kg": 72.5,
    })
    assert saved.status_code == 200
    assert saved.get_json()["data"]["systolic_pressure"] == 128


def test_meal_create_and_delete_contract():
    test_client = client()
    record_id = test_client.get("/api/v1/daily-records/today").get_json()["data"]["record"]["id"]
    created = test_client.post(f"/api/v1/daily-records/{record_id}/meals", json={
        "meal_type": "dinner",
        "meal_name": "晚餐",
        "foods": [{"name": "杂粮饭", "amount": "半碗", "calories": 120}],
    })
    assert created.status_code == 200
    meal_id = created.get_json()["data"]["id"]
    updated = test_client.put(f"/api/v1/meals/{meal_id}", json={
        "meal_type": "dinner",
        "meal_name": "晚餐",
        "foods": [{"name": "蒸玉米", "amount": "半根", "calories": 80}],
    })
    assert updated.status_code == 200
    assert updated.get_json()["data"]["foods"][0]["name"] == "蒸玉米"
    deleted = test_client.delete(f"/api/v1/meals/{meal_id}")
    assert deleted.status_code == 200


def test_login_returns_signed_token():
    response = client().post("/api/v1/auth/wechat-login", json={"code": "test-code"})
    assert response.status_code == 200
    assert response.get_json()["data"]["token"] != "demo-token-user-1"


def test_protected_api_requires_and_accepts_token():
    app = create_app()
    app.config["AUTH_REQUIRED"] = True
    test_client = app.test_client()

    denied = test_client.get("/api/v1/me/profile")
    assert denied.status_code == 401

    token = test_client.post("/api/v1/auth/wechat-login", json={"code": "test-code"}).get_json()["data"]["token"]
    allowed = test_client.get("/api/v1/me/profile", headers={"Authorization": f"Bearer {token}"})
    assert allowed.status_code == 200


def test_settings_validation_and_save_contract():
    test_client = client()
    invalid = test_client.put("/api/v1/me/settings", json={"daily_record_reminder_time": "25:90"})
    assert invalid.status_code == 400

    saved = test_client.put("/api/v1/me/settings", json={
        "alert_push_enabled": False,
        "daily_record_reminder_enabled": True,
        "daily_record_reminder_time": "19:45",
    })
    assert saved.status_code == 200
    assert saved.get_json()["data"]["daily_record_reminder_time"] == "19:45"


def test_profile_validation_and_avatar_upload_contract():
    app = create_app()
    original = dict(app.test_client().get("/api/v1/me/profile").get_json()["data"]["user"])

    with TemporaryDirectory() as upload_dir:
        app.config.update(PERSIST_DEMO_STATE=False, UPLOAD_FOLDER=upload_dir)
        test_client = app.test_client()

        invalid_nickname = test_client.put("/api/v1/me/profile", json={"nickname": ""})
        assert invalid_nickname.status_code == 400
        invalid_phone = test_client.put("/api/v1/me/profile", json={"phone": "12345"})
        assert invalid_phone.status_code == 400

        saved = test_client.put("/api/v1/me/profile", json={
            "nickname": "健康用户",
            "phone": "13800138000",
            "age": 56,
        })
        assert saved.status_code == 200
        assert saved.get_json()["data"]["nickname"] == "健康用户"

        invalid_avatar = test_client.post("/api/v1/me/avatar", data={
            "file": (BytesIO(b"not an image"), "avatar.txt"),
        }, content_type="multipart/form-data")
        assert invalid_avatar.status_code == 400

        uploaded = test_client.post("/api/v1/me/avatar", data={
            "file": (BytesIO(b"demo image"), "avatar.png"),
        }, content_type="multipart/form-data")
        assert uploaded.status_code == 200
        avatar_url = uploaded.get_json()["data"]["avatar_url"]
        avatar_path = avatar_url.removeprefix("http://localhost")
        assert test_client.get(avatar_path).status_code == 200

        removed = test_client.delete("/api/v1/me/avatar")
        assert removed.status_code == 200
        assert removed.get_json()["data"]["avatar_url"] == ""

        test_client.put("/api/v1/me/profile", json={
            "nickname": original["nickname"],
            "phone": original["phone"],
            "age": original["age"],
            "avatar_url": original["avatar_url"],
        })


def test_daily_note_and_mood_contract():
    test_client = client()
    record_id = test_client.get("/api/v1/daily-records/today").get_json()["data"]["record"]["id"]

    invalid = test_client.patch(f"/api/v1/daily-records/{record_id}", json={"mood": "unknown"})
    assert invalid.status_code == 400

    saved = test_client.patch(f"/api/v1/daily-records/{record_id}", json={
        "mood": "平稳",
        "note": "晚餐后散步 30 分钟，身体状态平稳。",
    })
    assert saved.status_code == 200
    assert saved.get_json()["data"]["mood"] == "平稳"
    assert "散步" in saved.get_json()["data"]["note"]


def test_alert_mark_read_contract():
    test_client = client()
    record_id = test_client.get("/api/v1/daily-records/today").get_json()["data"]["record"]["id"]
    test_client.patch(f"/api/v1/daily-records/{record_id}/vitals", json={
        "systolic_pressure": 142,
        "diastolic_pressure": 92,
        "fasting_glucose": 6.6,
    })
    items = test_client.get("/api/v1/alerts").get_json()["data"]
    assert items
    alert_id = items[0]["id"]

    response = test_client.patch(f"/api/v1/alerts/{alert_id}/read")
    assert response.status_code == 200
    refreshed = test_client.get("/api/v1/alerts").get_json()["data"]
    selected = next(item for item in refreshed if item["id"] == alert_id)
    assert selected["is_read"] is True


def test_vitals_save_synchronizes_alerts():
    test_client = client()
    record_id = test_client.get("/api/v1/daily-records/today").get_json()["data"]["record"]["id"]

    test_client.patch(f"/api/v1/daily-records/{record_id}/vitals", json={
        "systolic_pressure": 168,
        "diastolic_pressure": 102,
        "fasting_glucose": 7.4,
    })
    alerts = test_client.get("/api/v1/alerts").get_json()["data"]
    pressure = next(item for item in alerts if item["alert_type"] == "pressure")
    glucose = next(item for item in alerts if item["alert_type"] == "glucose")
    assert pressure["risk_level"] == "high"
    assert glucose["risk_level"] == "high"

    test_client.patch(f"/api/v1/daily-records/{record_id}/vitals", json={
        "systolic_pressure": 120,
        "diastolic_pressure": 78,
        "fasting_glucose": 5.5,
    })
    refreshed = test_client.get("/api/v1/alerts").get_json()["data"]
    assert not any(item["alert_type"] in {"pressure", "glucose"} for item in refreshed)


def test_create_historical_daily_record_contract():
    test_client = client()
    target = date.today() - timedelta(days=30)
    for _ in range(365):
        date_text = target.isoformat()
        if test_client.get(f"/api/v1/daily-records?date={date_text}").status_code == 404:
            break
        target -= timedelta(days=1)

    created = test_client.post("/api/v1/daily-records", json={"date": date_text})
    assert created.status_code == 201
    payload = created.get_json()["data"]
    assert payload["record"]["record_date"] == date_text
    assert payload["tasks"]

    duplicate = test_client.post("/api/v1/daily-records", json={"date": date_text})
    assert duplicate.status_code == 409

    future = (date.today() + timedelta(days=1)).isoformat()
    invalid = test_client.post("/api/v1/daily-records", json={"date": future})
    assert invalid.status_code == 400


def test_report_correction_confirmation_rerecognition_and_delete():
    test_client = client()
    uploaded = test_client.post("/api/v1/reports/upload", data={
        "file": (BytesIO(b"fake image content"), "report-test.jpg"),
        "report_date": date.today().isoformat(),
    }, content_type="multipart/form-data")
    assert uploaded.status_code == 200
    report_id = uploaded.get_json()["data"]["report_id"]

    assert test_client.post(f"/api/v1/reports/{report_id}/recognize").status_code == 200
    for _ in range(3):
        progress = test_client.get(f"/api/v1/reports/{report_id}/progress")
    assert progress.get_json()["data"]["status"] == "review_pending"

    corrected = test_client.put(f"/api/v1/reports/{report_id}/indicators", json={"items": [{
        "indicator_name": "空腹血糖",
        "indicator_code": "GLU",
        "value": "6.5",
        "unit": "mmol/L",
        "reference_range": "3.9-6.1",
        "status": "high",
        "risk_level": "medium",
    }]})
    assert corrected.status_code == 200
    assert corrected.get_json()["data"][0]["value"] == "6.5"

    confirmed = test_client.patch(f"/api/v1/reports/{report_id}", json={
        "action": "confirm",
        "review_note": "用户已核对原始报告",
    })
    assert confirmed.status_code == 200
    assert confirmed.get_json()["data"]["status"] == "completed"

    restarted = test_client.post(f"/api/v1/reports/{report_id}/recognize")
    assert restarted.status_code == 200
    assert test_client.get(f"/api/v1/reports/{report_id}/indicators").get_json()["data"] == []

    deleted = test_client.delete(f"/api/v1/reports/{report_id}")
    assert deleted.status_code == 200
    assert test_client.get(f"/api/v1/reports/{report_id}").status_code == 404
