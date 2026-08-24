import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def _csv_env(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


class Config:
    APP_ENV = os.getenv("APP_ENV", "development").lower()
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'storage' / 'three_high_health.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800")),
    }
    JSON_AS_ASCII = False
    RESTFUL_JSON = {"ensure_ascii": False}
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "storage" / "uploads"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    AUTO_CREATE_TABLES = os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true"
    PERSIST_DEMO_STATE = os.getenv("PERSIST_DEMO_STATE", "true").lower() == "true"
    DOMAIN_REPOSITORIES_ENABLED = os.getenv("DOMAIN_REPOSITORIES_ENABLED", "true").lower() == "true"
    AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "false").lower() == "true"
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
    TOKEN_MAX_AGE_SECONDS = int(os.getenv("TOKEN_MAX_AGE_SECONDS", str(7 * 24 * 3600)))
    TOKEN_VERSION_REQUIRED = os.getenv(
        "TOKEN_VERSION_REQUIRED",
        "true" if APP_ENV == "production" else "false",
    ).lower() == "true"
    WECHAT_LOGIN_MODE = os.getenv("WECHAT_LOGIN_MODE", "mock").lower()
    WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "")
    WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")
    WECHAT_MOCK_OPENID = os.getenv("WECHAT_MOCK_OPENID", "demo-openid")
    WECHAT_CODE2SESSION_URL = os.getenv(
        "WECHAT_CODE2SESSION_URL",
        "https://api.weixin.qq.com/sns/jscode2session",
    )
    WECHAT_API_TIMEOUT_SECONDS = float(os.getenv("WECHAT_API_TIMEOUT_SECONDS", "5"))
    PRIVACY_POLICY_VERSION = os.getenv("PRIVACY_POLICY_VERSION", "2026-08-23")
    USER_AGREEMENT_VERSION = os.getenv("USER_AGREEMENT_VERSION", "2026-08-23")
    HEALTH_DATA_CONSENT_VERSION = os.getenv("HEALTH_DATA_CONSENT_VERSION", "2026-08-23")
    HEALTH_CONSENT_REQUIRED = os.getenv(
        "HEALTH_CONSENT_REQUIRED",
        "true" if APP_ENV == "production" else "false",
    ).lower() == "true"
    TRUST_PROXY_COUNT = int(os.getenv("TRUST_PROXY_COUNT", "0"))
    CORS_ORIGINS = _csv_env(
        "CORS_ORIGINS",
        "http://localhost:8088,http://127.0.0.1:8088" if APP_ENV != "production" else "",
    )
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "1000 per minute")
    RATELIMIT_HEADERS_ENABLED = True
    WECHAT_LOGIN_RATE_LIMIT = os.getenv("WECHAT_LOGIN_RATE_LIMIT", "120 per minute")
    ADMIN_LOGIN_RATE_LIMIT = os.getenv("ADMIN_LOGIN_RATE_LIMIT", "60 per minute")


def validate_production_config(config):
    if str(config.get("APP_ENV", "development")).lower() != "production":
        return

    errors = []
    secret_key = str(config.get("SECRET_KEY", ""))
    if len(secret_key) < 32 or secret_key == "dev-only-change-me":
        errors.append("SECRET_KEY 必须是至少 32 位的随机值")
    if not config.get("AUTH_REQUIRED"):
        errors.append("AUTH_REQUIRED 必须为 true")
    if config.get("AUTO_CREATE_TABLES"):
        errors.append("AUTO_CREATE_TABLES 必须为 false，并使用数据库迁移")
    if str(config.get("SQLALCHEMY_DATABASE_URI", "")).startswith("sqlite"):
        errors.append("生产环境不能使用 SQLite")
    if "://root:" in str(config.get("SQLALCHEMY_DATABASE_URI", "")):
        errors.append("生产环境数据库不能使用 root 账号")
    if not config.get("ADMIN_PASSWORD_HASH"):
        errors.append("必须配置 ADMIN_PASSWORD_HASH，不能使用管理员明文密码")
    origins = config.get("CORS_ORIGINS") or []
    if "*" in origins:
        errors.append("CORS_ORIGINS 禁止使用通配来源")
    if str(config.get("RATELIMIT_STORAGE_URI", "")).startswith("memory"):
        errors.append("RATELIMIT_STORAGE_URI 必须使用 Redis 等共享存储")
    if config.get("WECHAT_LOGIN_MODE") != "code2session":
        errors.append("WECHAT_LOGIN_MODE 必须为 code2session")
    if not config.get("WECHAT_APP_ID") or not config.get("WECHAT_APP_SECRET"):
        errors.append("必须配置 WECHAT_APP_ID 和 WECHAT_APP_SECRET")
    if not config.get("TOKEN_VERSION_REQUIRED"):
        errors.append("TOKEN_VERSION_REQUIRED 必须为 true")
    if not config.get("HEALTH_CONSENT_REQUIRED"):
        errors.append("HEALTH_CONSENT_REQUIRED 必须为 true")

    if errors:
        raise RuntimeError("生产环境配置检查失败：" + "；".join(errors))
