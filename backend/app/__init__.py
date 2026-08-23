import re
from uuid import uuid4

from flask import Flask, g, request
from flask_cors import CORS
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from pathlib import Path
from sqlalchemy import inspect

from .api import api_bp
from .config import Config, validate_production_config
from .extensions import db, limiter, migrate
from .repositories import (
    bootstrap_ai_data, bootstrap_daily_data, bootstrap_reference_data, bootstrap_report_data,
    bootstrap_task_alert_data, bootstrap_user_data,
)
from .services.demo_store import store


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.json.ensure_ascii = False
    validate_production_config(app.config)
    if app.config["TRUST_PROXY_COUNT"] > 0:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config["TRUST_PROXY_COUNT"],
            x_proto=app.config["TRUST_PROXY_COUNT"],
            x_host=app.config["TRUST_PROXY_COUNT"],
        )

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=False,
    )
    db.init_app(app)
    limiter.init_app(app)
    from . import models  # noqa: F401

    migrate.init_app(
        app,
        db,
        compare_type=True,
        render_as_batch=app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"),
    )
    app.register_blueprint(api_bp)

    @app.before_request
    def authenticate_request():
        supplied_request_id = request.headers.get("X-Request-ID", "")
        g.request_id = (
            supplied_request_id
            if re.fullmatch(r"[A-Za-z0-9._-]{8,64}", supplied_request_id)
            else uuid4().hex
        )
        if request.method == "OPTIONS":
            return None
        public_paths = {"/api/v1/health", "/api/v1/auth/wechat-login", "/api/v1/auth/admin-login"}
        if request.path in public_paths or request.path.startswith("/api/v1/me/avatar/files/"):
            return None
        is_admin_api = request.path.startswith("/api/v1/admin/")
        if not app.config.get("AUTH_REQUIRED") and not is_admin_api:
            return None
        value = request.headers.get("Authorization", "")
        if not value.startswith("Bearer "):
            return {"code": 40101, "message": "请先登录", "data": None}, 401
        serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="wechat-login")
        try:
            g.identity = serializer.loads(value[7:], max_age=app.config["TOKEN_MAX_AGE_SECONDS"])
        except SignatureExpired:
            return {"code": 40102, "message": "登录已过期，请重新登录", "data": None}, 401
        except BadSignature:
            return {"code": 40103, "message": "登录凭证无效", "data": None}, 401
        if g.identity.get("role") == "user":
            from .models import User, UserConsent

            try:
                user_id = int(g.identity.get("user_id"))
            except (TypeError, ValueError):
                return {"code": 40103, "message": "登录凭证无效", "data": None}, 401
            user = db.session.get(User, user_id)
            if user is None:
                return {"code": 40103, "message": "登录用户不存在", "data": None}, 401
            if int(user.status or 0) != 1:
                return {"code": 40302, "message": "账号已停用，请联系管理员", "data": None}, 403
            token_version = g.identity.get("token_version")
            if token_version is None and app.config["TOKEN_VERSION_REQUIRED"]:
                return {"code": 40103, "message": "登录凭证版本无效", "data": None}, 401
            if token_version is not None and int(token_version) != int(user.token_version or 1):
                return {"code": 40103, "message": "登录凭证已失效，请重新登录", "data": None}, 401
            health_paths = (
                "/api/v1/daily-records", "/api/v1/daily-tasks",
                "/api/v1/daily-task-templates", "/api/v1/meals",
                "/api/v1/trends", "/api/v1/predictions", "/api/v1/alerts",
                "/api/v1/reports", "/api/v1/ai",
            )
            requires_health_consent = (
                request.path == "/api/v1/me/health-profile"
                or any(request.path.startswith(prefix) for prefix in health_paths)
            )
            if app.config.get("HEALTH_CONSENT_REQUIRED") and requires_health_consent:
                consent = UserConsent.query.filter_by(user_id=user_id).one_or_none()
                consent_current = bool(
                    consent
                    and consent.health_data_consent
                    and consent.privacy_policy_version == app.config["PRIVACY_POLICY_VERSION"]
                    and consent.user_agreement_version == app.config["USER_AGREEMENT_VERSION"]
                    and consent.health_data_consent_version == app.config["HEALTH_DATA_CONSENT_VERSION"]
                )
                if not consent_current:
                    return {"code": 40303, "message": "请先完成健康数据授权", "data": None}, 403
        if is_admin_api and g.identity.get("role") != "admin":
            return {"code": 40301, "message": "需要管理员权限", "data": None}, 403
        return None

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", uuid4().hex)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    with app.app_context():
        Path(app.config["UPLOAD_FOLDER"]).parent.mkdir(parents=True, exist_ok=True)
        if app.config.get("AUTO_CREATE_TABLES"):
            db.create_all()
        inspector = inspect(db.engine)
        has_state_table = inspector.has_table("app_state")
        if app.config.get("PERSIST_DEMO_STATE") and has_state_table:
            if not store.load_persisted_state():
                store.domain_migrations = {}
                store.persist()
        reference_tables = {"users", "food_items", "announcements"}
        food_columns = (
            {column["name"] for column in inspector.get_columns("food_items")}
            if inspector.has_table("food_items")
            else set()
        )
        if (
            app.config.get("DOMAIN_REPOSITORIES_ENABLED")
            and reference_tables.issubset(set(inspector.get_table_names()))
            and "unit" in food_columns
        ):
            migration_key = "reference-repositories-v1"
            if not store.domain_migrations.get(migration_key):
                bootstrap_reference_data(store)
                store.domain_migrations[migration_key] = True
            if has_state_table:
                store.persist()
        ai_tables = {"ai_conversations", "ai_messages"}
        ai_columns = (
            {column["name"] for column in inspector.get_columns("ai_conversations")}
            if inspector.has_table("ai_conversations") else set()
        )
        if (
            app.config.get("DOMAIN_REPOSITORIES_ENABLED")
            and ai_tables.issubset(set(inspector.get_table_names()))
            and {"source", "related_date"}.issubset(ai_columns)
        ):
            migration_key = "ai-repositories-v1"
            if not store.domain_migrations.get(migration_key):
                bootstrap_ai_data(store)
                store.domain_migrations[migration_key] = True
            if has_state_table:
                store.persist()
        report_tables = {"medical_reports", "report_indicators"}
        report_columns = (
            {column["name"] for column in inspector.get_columns("medical_reports")}
            if inspector.has_table("medical_reports") else set()
        )
        if (
            app.config.get("DOMAIN_REPOSITORIES_ENABLED")
            and report_tables.issubset(set(inspector.get_table_names()))
            and {"source", "report_date", "progress", "summary", "review_note"}.issubset(report_columns)
        ):
            migration_key = "report-repositories-v1"
            if not store.domain_migrations.get(migration_key):
                bootstrap_report_data(store)
                store.domain_migrations[migration_key] = True
            if has_state_table:
                store.persist()
        task_alert_tables = {"daily_task_templates", "daily_task_template_items", "daily_tasks", "health_alerts"}
        alert_columns = (
            {column["name"] for column in inspector.get_columns("health_alerts")}
            if inspector.has_table("health_alerts") else set()
        )
        if (
            app.config.get("DOMAIN_REPOSITORIES_ENABLED")
            and task_alert_tables.issubset(set(inspector.get_table_names()))
            and {"alert_type", "record_date", "description"}.issubset(alert_columns)
        ):
            migration_key = "task-alert-repositories-v1"
            if not store.domain_migrations.get(migration_key):
                bootstrap_task_alert_data(store)
                store.domain_migrations[migration_key] = True
            if has_state_table:
                store.persist()
        daily_tables = {"daily_records", "vital_records", "meal_records"}
        meal_columns = (
            {column["name"] for column in inspector.get_columns("meal_records")}
            if inspector.has_table("meal_records")
            else set()
        )
        if (
            app.config.get("DOMAIN_REPOSITORIES_ENABLED")
            and daily_tables.issubset(set(inspector.get_table_names()))
            and "meal_name" in meal_columns
        ):
            migration_key = "daily-repositories-v1"
            if not store.domain_migrations.get(migration_key):
                bootstrap_daily_data(store)
                store.domain_migrations[migration_key] = True
            if has_state_table:
                store.persist()
        user_tables = {"users", "health_profiles", "user_settings"}
        profile_columns = (
            {column["name"] for column in inspector.get_columns("health_profiles")}
            if inspector.has_table("health_profiles")
            else set()
        )
        if (
            app.config.get("DOMAIN_REPOSITORIES_ENABLED")
            and user_tables.issubset(set(inspector.get_table_names()))
            and "chronic_types" in profile_columns
        ):
            migration_key = "user-repositories-v1"
            if not store.domain_migrations.get(migration_key):
                bootstrap_user_data(store)
                store.domain_migrations[migration_key] = True
            if has_state_table:
                store.persist()

    @app.errorhandler(413)
    def file_too_large(_error):
        return {"code": 41301, "message": "上传文件不能超过 10MB", "data": None}, 413

    @app.errorhandler(Exception)
    def unexpected_error(error):
        if isinstance(error, HTTPException):
            return {"code": error.code * 100 + 1, "message": error.description, "data": None}, error.code
        app.logger.exception("Unhandled application error", exc_info=error)
        db.session.rollback()
        return {"code": 50001, "message": "服务器内部错误", "data": None}, 500

    return app
