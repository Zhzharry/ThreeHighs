from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import HealthProfile, User, UserConsent, UserLoginEvent, UserSettings


DISEASE_LABELS = {
    "hypertension": "高血压",
    "diabetes": "高血糖",
    "hyperlipidemia": "高血脂",
}


def _now():
    return datetime.now().replace(microsecond=0)


def _datetime(value, fallback=None):
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if value:
        try:
            return datetime.fromisoformat(str(value)).replace(tzinfo=None)
        except ValueError:
            pass
    return fallback or _now()


def _number(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def _mask_phone(phone):
    if not phone or len(phone) < 7:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


class UserRepository:
    @classmethod
    def login_wechat_user(cls, openid, unionid=None, nickname=None, avatar_url=None):
        now = _now()
        user = User.query.filter_by(openid=openid).one_or_none()
        if user is None and unionid:
            user = User.query.filter_by(unionid=unionid).one_or_none()

        if user is None:
            suffix = openid[-6:] if len(openid) >= 6 else openid
            user = User(
                openid=openid,
                unionid=unionid,
                username=(str(nickname or "").strip() or f"微信用户{suffix}")[:50],
                avatar_url=str(avatar_url or "")[:255],
                role="user",
                status=1,
                token_version=1,
                login_count=1,
                last_login_at=now,
                created_at=now,
                updated_at=now,
            )
            db.session.add(user)
        else:
            if not user.openid:
                user.openid = openid
            if unionid and not user.unionid:
                user.unionid = unionid
            if nickname:
                user.username = str(nickname).strip()[:50] or user.username
            if avatar_url:
                user.avatar_url = str(avatar_url)[:255]
            user.token_version = int(user.token_version or 1)
            user.login_count = int(user.login_count or 0) + 1
            user.last_login_at = now
            user.updated_at = now

        try:
            db.session.flush()
            cls._profile(user.id, create=True)
            cls._settings(user.id, create=True)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            user = User.query.filter_by(openid=openid).one_or_none()
            if user is None:
                raise
            user.login_count = int(user.login_count or 0) + 1
            user.last_login_at = now
            user.updated_at = now
            db.session.commit()
        return user

    @staticmethod
    def record_login_event(user_id, success, failure_code, request_id, client_ip_hash):
        db.session.add(UserLoginEvent(
            user_id=user_id,
            login_method="wechat",
            success=bool(success),
            failure_code=str(failure_code or "")[:32] or None,
            request_id=str(request_id)[:64],
            client_ip_hash=str(client_ip_hash)[:64],
            created_at=_now(),
        ))
        db.session.commit()

    @staticmethod
    def revoke_tokens(user_id):
        user = db.session.get(User, user_id)
        if user is None:
            return False
        user.token_version = int(user.token_version or 1) + 1
        user.updated_at = _now()
        db.session.commit()
        return True

    @staticmethod
    def get_consents(user_id, versions):
        row = UserConsent.query.filter_by(user_id=user_id).one_or_none()
        accepted = bool(
            row
            and row.privacy_policy_version == versions["privacy_policy"]
            and row.user_agreement_version == versions["user_agreement"]
            and row.health_data_consent_version == versions["health_data_consent"]
            and row.health_data_consent
        )
        return {
            "versions": versions,
            "privacy_policy_accepted": bool(row and row.privacy_policy_version == versions["privacy_policy"]),
            "user_agreement_accepted": bool(row and row.user_agreement_version == versions["user_agreement"]),
            "health_data_consent": bool(
                row
                and row.health_data_consent
                and row.health_data_consent_version == versions["health_data_consent"]
            ),
            "required_complete": accepted,
            "accepted_at": row.accepted_at.isoformat() if row and row.accepted_at else None,
            "withdrawn_at": row.withdrawn_at.isoformat() if row and row.withdrawn_at else None,
        }

    @staticmethod
    def accept_consents(user_id, versions):
        now = _now()
        row = UserConsent.query.filter_by(user_id=user_id).one_or_none()
        if row is None:
            row = UserConsent(user_id=user_id, created_at=now)
            db.session.add(row)
        row.privacy_policy_version = versions["privacy_policy"]
        row.user_agreement_version = versions["user_agreement"]
        row.health_data_consent_version = versions["health_data_consent"]
        row.health_data_consent = True
        row.accepted_at = now
        row.withdrawn_at = None
        row.updated_at = now
        db.session.commit()
        return UserRepository.get_consents(user_id, versions)

    @staticmethod
    def withdraw_health_consent(user_id, versions):
        row = UserConsent.query.filter_by(user_id=user_id).one_or_none()
        if row is None:
            return UserRepository.get_consents(user_id, versions)
        now = _now()
        row.health_data_consent = False
        row.withdrawn_at = now
        row.updated_at = now
        db.session.commit()
        return UserRepository.get_consents(user_id, versions)

    @staticmethod
    def _profile(user_id, create=False):
        row = HealthProfile.query.filter_by(user_id=user_id).one_or_none()
        if row is None and create:
            now = _now()
            row = HealthProfile(
                user_id=user_id,
                chronic_types=[],
                created_at=now,
                updated_at=now,
            )
            db.session.add(row)
        return row

    @staticmethod
    def _settings(user_id, create=False):
        row = UserSettings.query.filter_by(user_id=user_id).one_or_none()
        if row is None and create:
            now = _now()
            row = UserSettings(
                user_id=user_id,
                alert_push_enabled=True,
                daily_record_reminder_enabled=True,
                daily_record_reminder_time="20:30",
                created_at=now,
                updated_at=now,
            )
            db.session.add(row)
        return row

    @classmethod
    def user_summary(cls, user_id=1, masked_phone=False):
        user = db.session.get(User, user_id)
        if user is None:
            return None
        profile = cls._profile(user_id)
        phone = _mask_phone(user.phone) if masked_phone else (user.phone or "")
        return {
            "id": user.id,
            "nickname": user.username,
            "age": profile.age if profile else None,
            "phone": phone,
            "avatar_url": user.avatar_url or "",
            "role": user.role,
            "status": user.status,
            "token_version": int(user.token_version or 1),
        }

    @staticmethod
    def _serialize_health_profile(profile):
        if profile is None:
            return {
                "gender": "",
                "age": None,
                "height_cm": None,
                "weight_kg": None,
                "bmi": None,
                "disease_type": "",
                "medical_history": "",
                "chronic_types": [],
                "medication": "",
                "medications": "",
                "updated_at": None,
            }
        return {
            "gender": profile.gender or "",
            "age": profile.age,
            "height_cm": _number(profile.height_cm),
            "weight_kg": _number(profile.weight_kg),
            "bmi": _number(profile.bmi),
            "disease_type": profile.disease_type or "",
            "medical_history": profile.medical_history or "",
            "chronic_types": list(profile.chronic_types or []),
            "medication": profile.medication or "",
            "medications": profile.medication or "",
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }

    @classmethod
    def get_profile(cls, user_id=1):
        user = db.session.get(User, user_id)
        if user is None:
            return None
        profile = cls._profile(user_id)
        return {
            "user": {
                "id": user.id,
                "avatar_url": user.avatar_url or "",
                "nickname": user.username,
                "age": profile.age if profile else None,
                "phone": user.phone or "",
                "phone_masked": _mask_phone(user.phone or ""),
            },
            "health_profile": cls._serialize_health_profile(profile),
        }

    @classmethod
    def update_profile(cls, payload, user_id=1):
        user = db.session.get(User, user_id)
        if user is None:
            return None
        profile = cls._profile(user_id, create=True)
        if "nickname" in payload:
            user.username = payload["nickname"]
        if "avatar_url" in payload:
            user.avatar_url = payload["avatar_url"]
        if "phone" in payload:
            user.phone = payload["phone"]
        if "age" in payload:
            profile.age = payload["age"]
            profile.updated_at = _now()
        user.updated_at = _now()
        db.session.commit()
        return cls.user_summary(user_id, masked_phone=True)

    @classmethod
    def update_health_profile(cls, payload, user_id=1):
        if db.session.get(User, user_id) is None:
            return None
        profile = cls._profile(user_id, create=True)
        for key in ("gender", "age", "height_cm", "weight_kg", "medical_history", "disease_type"):
            if key in payload:
                setattr(profile, key, payload[key])
        if "chronic_types" in payload:
            profile.chronic_types = list(payload["chronic_types"])
            if "disease_type" not in payload:
                profile.disease_type = " + ".join(
                    DISEASE_LABELS[item] for item in profile.chronic_types if item in DISEASE_LABELS
                ) or "暂无"
        if "medications" in payload:
            profile.medication = payload["medications"]
        if "medication" in payload:
            profile.medication = payload["medication"]
        height = float(profile.height_cm or 0)
        weight = float(profile.weight_kg or 0)
        if height and weight:
            profile.bmi = round(weight / ((height / 100) ** 2), 1)
        profile.updated_at = _now()
        db.session.commit()
        return cls._serialize_health_profile(profile)

    @classmethod
    def get_settings(cls, user_id=1):
        if db.session.get(User, user_id) is None:
            return None
        row = cls._settings(user_id, create=True)
        db.session.commit()
        return {
            "alert_push_enabled": bool(row.alert_push_enabled),
            "daily_record_reminder_enabled": bool(row.daily_record_reminder_enabled),
            "daily_record_reminder_time": row.daily_record_reminder_time,
        }

    @classmethod
    def update_settings(cls, payload, user_id=1):
        if db.session.get(User, user_id) is None:
            return None
        row = cls._settings(user_id, create=True)
        for key in ("alert_push_enabled", "daily_record_reminder_enabled", "daily_record_reminder_time"):
            if key in payload:
                setattr(row, key, payload[key])
        row.updated_at = _now()
        db.session.commit()
        return cls.get_settings(user_id)

    @classmethod
    def admin_users(cls, page, page_size, keyword=None):
        query = User.query
        if keyword:
            query = query.filter(or_(User.username.contains(keyword), User.phone.contains(keyword)))
        total = query.count()
        rows = query.order_by(User.created_at.desc(), User.id.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        items = []
        for user in rows:
            profile = cls._profile(user.id)
            items.append({
                "id": user.id,
                "nickname": user.username,
                "age": profile.age if profile else None,
                "phone": _mask_phone(user.phone or ""),
                "chronic_types": list(profile.chronic_types or []) if profile else [],
                "status": user.status,
                "login_count": int(user.login_count or 0),
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            })
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    @classmethod
    def admin_user_detail(cls, user_id):
        user = db.session.get(User, user_id)
        if user is None:
            return None
        profile = cls._profile(user_id)
        health = cls._serialize_health_profile(profile)
        return {
            "id": user.id,
            "nickname": user.username,
            "phone": user.phone or "",
            "avatar_url": user.avatar_url or "",
            "status": user.status,
            "login_count": int(user.login_count or 0),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "gender": health["gender"],
            "age": health["age"],
            "height_cm": health["height_cm"],
            "weight_kg": health["weight_kg"],
            "bmi": health["bmi"],
            "chronic_types": health["chronic_types"],
            "medical_history": health["medical_history"],
            "medication": health["medication"],
        }

    @classmethod
    def update_admin_user(cls, user_id, payload):
        user = db.session.get(User, user_id)
        if user is None:
            return None
        profile_payload = {}
        account_payload = {key: payload[key] for key in ("nickname", "phone") if key in payload}
        if "age" in payload:
            account_payload["age"] = payload["age"]
        if account_payload:
            cls.update_profile(account_payload, user_id)
        for key in ("gender", "age", "height_cm", "weight_kg", "chronic_types", "medical_history", "medication"):
            if key in payload:
                profile_payload[key] = payload[key]
        if profile_payload:
            cls.update_health_profile(profile_payload, user_id)
        if "status" in payload and user.status != payload["status"]:
            user.status = payload["status"]
            user.token_version = int(user.token_version or 1) + 1
            user.updated_at = _now()
            db.session.commit()
        return cls.admin_user_detail(user_id)

    @staticmethod
    def count():
        return User.query.count()


def bootstrap_user_data(store):
    """Import the compatibility user, profile and settings exactly once."""
    user_id = int(store.user["id"])
    now = _now()
    user = db.session.get(User, user_id)
    if user is None:
        user = User(id=user_id, created_at=now, updated_at=now)
        db.session.add(user)
    user.openid = store.user.get("openid")
    user.username = store.user.get("nickname") or store.user.get("username") or "演示用户"
    user.avatar_url = store.user.get("avatar_url", "")
    user.phone = store.user.get("phone", "")
    user.role = store.user.get("role", "user")
    user.status = store.user.get("status", 1)
    user.token_version = int(user.token_version or 1)
    user.login_count = int(user.login_count or 0)
    user.created_at = _datetime(store.user.get("created_at"), user.created_at)
    user.updated_at = _datetime(store.user.get("updated_at"), now)
    db.session.flush()

    source_profile = store.health_profile
    profile = UserRepository._profile(user_id, create=True)
    for key in ("gender", "age", "height_cm", "weight_kg", "bmi", "disease_type", "medical_history", "medication"):
        setattr(profile, key, source_profile.get(key))
    profile.chronic_types = list(source_profile.get("chronic_types", []))
    profile.created_at = profile.created_at or now
    profile.updated_at = _datetime(source_profile.get("updated_at"), now)

    source_settings = store.settings
    settings = UserRepository._settings(user_id, create=True)
    settings.alert_push_enabled = source_settings.get("alert_push_enabled", True)
    settings.daily_record_reminder_enabled = source_settings.get("daily_record_reminder_enabled", True)
    settings.daily_record_reminder_time = source_settings.get("daily_record_reminder_time", "20:30")
    settings.created_at = settings.created_at or now
    settings.updated_at = now
    db.session.commit()
