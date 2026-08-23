from app.extensions import db
from app.models.types import BIGINT


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    openid = db.Column(db.String(64), unique=True)
    unionid = db.Column(db.String(64), unique=True)
    username = db.Column(db.String(50), nullable=False)
    avatar_url = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    role = db.Column(db.Enum("user", "admin"), default="user")
    status = db.Column(db.SmallInteger, default=1)
    token_version = db.Column(db.Integer, nullable=False, default=1)
    last_login_at = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)


class HealthProfile(db.Model):
    __tablename__ = "health_profiles"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)
    height_cm = db.Column(db.Numeric(5, 2))
    weight_kg = db.Column(db.Numeric(5, 2))
    bmi = db.Column(db.Numeric(5, 2))
    disease_type = db.Column(db.String(100))
    chronic_types = db.Column(db.JSON, nullable=False, default=list)
    medical_history = db.Column(db.Text)
    medication = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", name="uk_health_profile_user"),
    )


class UserSettings(db.Model):
    __tablename__ = "user_settings"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False, unique=True)
    alert_push_enabled = db.Column(db.Boolean, default=True)
    daily_record_reminder_enabled = db.Column(db.Boolean, default=True)
    daily_record_reminder_time = db.Column(db.String(5), default="20:30")
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)


class UserLoginEvent(db.Model):
    __tablename__ = "user_login_events"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"))
    login_method = db.Column(db.String(20), nullable=False, default="wechat")
    success = db.Column(db.Boolean, nullable=False)
    failure_code = db.Column(db.String(32))
    request_id = db.Column(db.String(64), nullable=False)
    client_ip_hash = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        db.Index("ix_user_login_events_user_created", "user_id", "created_at"),
        db.Index("ix_user_login_events_request_id", "request_id"),
    )


class UserConsent(db.Model):
    __tablename__ = "user_consents"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False, unique=True)
    privacy_policy_version = db.Column(db.String(20), nullable=False)
    user_agreement_version = db.Column(db.String(20), nullable=False)
    health_data_consent_version = db.Column(db.String(20), nullable=False)
    health_data_consent = db.Column(db.Boolean, nullable=False, default=False)
    accepted_at = db.Column(db.DateTime, nullable=False)
    withdrawn_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)
