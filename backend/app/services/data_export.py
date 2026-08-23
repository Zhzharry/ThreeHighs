from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import inspect

from app.extensions import db
from app.models import (
    AiConversation,
    AiMessage,
    DailyRecord,
    DailyTask,
    DailyTaskTemplate,
    DailyTaskTemplateItem,
    HealthAlert,
    HealthProfile,
    MealRecord,
    MedicalReport,
    ReportIndicator,
    User,
    UserConsent,
    UserSettings,
    VitalRecord,
)


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _serialize(row, excluded=()):
    if row is None:
        return None
    excluded = set(excluded)
    return {
        attribute.key: _json_value(getattr(row, attribute.key))
        for attribute in inspect(row).mapper.column_attrs
        if attribute.key not in excluded
    }


def _rows(model, user_id, excluded=()):
    return [_serialize(row, excluded) for row in model.query.filter_by(user_id=user_id).order_by(model.id).all()]


def export_user_data(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return None

    templates = DailyTaskTemplate.query.filter_by(user_id=user_id).order_by(DailyTaskTemplate.id).all()
    template_ids = [row.id for row in templates]
    template_items = (
        DailyTaskTemplateItem.query.filter(DailyTaskTemplateItem.template_id.in_(template_ids))
        .order_by(DailyTaskTemplateItem.id)
        .all()
        if template_ids else []
    )

    categories = {
        "account": {
            "id": user.id,
            "nickname": user.username,
            "avatar_url": user.avatar_url or "",
            "phone": user.phone or "",
            "role": user.role,
            "status": user.status,
            "created_at": _json_value(user.created_at),
            "updated_at": _json_value(user.updated_at),
        },
        "health_profile": _serialize(HealthProfile.query.filter_by(user_id=user_id).one_or_none()),
        "settings": _serialize(UserSettings.query.filter_by(user_id=user_id).one_or_none()),
        "consent": _serialize(UserConsent.query.filter_by(user_id=user_id).one_or_none()),
        "daily_records": _rows(DailyRecord, user_id),
        "vital_records": _rows(VitalRecord, user_id),
        "meal_records": _rows(MealRecord, user_id),
        "task_templates": [_serialize(row) for row in templates],
        "task_template_items": [_serialize(row) for row in template_items],
        "daily_tasks": _rows(DailyTask, user_id),
        "health_alerts": _rows(HealthAlert, user_id),
        "medical_reports": _rows(
            MedicalReport,
            user_id,
            excluded={"file_url", "ocr_doc_id", "reviewed_by"},
        ),
        "report_indicators": _rows(ReportIndicator, user_id),
        "ai_conversations": _rows(AiConversation, user_id),
        "ai_messages": _rows(AiMessage, user_id, excluded={"mongo_trace_id"}),
    }
    counts = {
        key: len(value) if isinstance(value, list) else (1 if value else 0)
        for key, value in categories.items()
    }
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "user_id": user_id,
        "counts": counts,
        "data": categories,
        "excluded_security_fields": [
            "openid",
            "unionid",
            "token_version",
            "login audit IP hash",
            "report storage URL",
            "AI internal trace ID",
        ],
    }
