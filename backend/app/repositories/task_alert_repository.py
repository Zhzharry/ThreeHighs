from __future__ import annotations

from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import (
    DailyRecord, DailyTask, DailyTaskTemplate, DailyTaskTemplateItem, HealthAlert,
)


def _now():
    return datetime.now().replace(microsecond=0)


def _date(value):
    return value if isinstance(value, date) else datetime.strptime(str(value), "%Y-%m-%d").date()


def _datetime(value):
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    return datetime.fromisoformat(str(value)).replace(tzinfo=None) if value else None


class TaskRepository:
    @staticmethod
    def serialize_tasks(record_id, user_id=1):
        rows = DailyTask.query.filter_by(daily_record_id=record_id, user_id=user_id).order_by(DailyTask.sort_order).all()
        return [{
            "id": row.id, "task_name": row.task_name_snapshot, "is_done": bool(row.is_done),
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "sort_order": row.sort_order,
        } for row in rows]

    @staticmethod
    def _template_for(record_date, user_id=1):
        target = _date(record_date)
        return DailyTaskTemplate.query.filter(
            DailyTaskTemplate.user_id == user_id,
            DailyTaskTemplate.effective_from <= target,
            db.or_(DailyTaskTemplate.effective_to.is_(None), DailyTaskTemplate.effective_to >= target),
        ).order_by(DailyTaskTemplate.version_no.desc()).first()

    @staticmethod
    def serialize_template(template):
        if template is None:
            return {"template_id": None, "version_no": 0, "effective_from": None, "effective_to": None, "items": []}
        items = DailyTaskTemplateItem.query.filter_by(template_id=template.id).order_by(DailyTaskTemplateItem.sort_order).all()
        return {
            "template_id": template.id, "version_no": template.version_no,
            "effective_from": template.effective_from.isoformat(),
            "effective_to": template.effective_to.isoformat() if template.effective_to else None,
            "items": [{"id": row.id, "task_name": row.task_name, "sort_order": row.sort_order} for row in items],
        }

    @classmethod
    def current_template(cls, record_date, user_id=1):
        return cls.serialize_template(cls._template_for(record_date, user_id))

    @classmethod
    def generate(cls, record_id, record_date=None, user_id=1, force=False):
        record = DailyRecord.query.filter_by(id=record_id, user_id=user_id).one_or_none()
        if record is None:
            return None
        existing = DailyTask.query.filter_by(daily_record_id=record_id, user_id=user_id).all()
        if existing and not force:
            return cls.serialize_tasks(record_id, user_id)
        preserved = {row.task_name_snapshot: bool(row.is_done) for row in existing}
        if existing:
            DailyTask.query.filter_by(daily_record_id=record_id, user_id=user_id).delete()
        target = _date(record_date or record.record_date)
        template = cls._template_for(target, user_id)
        if template is None:
            template = cls.update_template(target, [{"task_name": "晨间血压", "sort_order": 1}], user_id, regenerate=False)
        items = DailyTaskTemplateItem.query.filter_by(template_id=template.id).order_by(DailyTaskTemplateItem.sort_order).all()
        now = _now()
        for item in items:
            done = preserved.get(item.task_name, False)
            db.session.add(DailyTask(
                daily_record_id=record.id, user_id=user_id, record_date=target,
                template_id=template.id, template_item_id=item.id,
                task_name_snapshot=item.task_name, is_done=done,
                completed_at=now if done else None, sort_order=item.sort_order,
                created_at=now, updated_at=now,
            ))
        db.session.commit()
        cls.recalculate(record_id, user_id)
        return cls.serialize_tasks(record_id, user_id)

    @classmethod
    def update_template(cls, effective_date, items, user_id=1, regenerate=True):
        effective = _date(effective_date)
        current = cls._template_for(effective, user_id)
        if current:
            current.effective_to = effective - timedelta(days=1)
            current.is_active = False
            current.updated_at = _now()
        version = db.session.query(db.func.max(DailyTaskTemplate.version_no)).filter_by(user_id=user_id).scalar() or 0
        now = _now()
        template = DailyTaskTemplate(
            user_id=user_id, version_no=version + 1, effective_from=effective,
            is_active=True, created_at=now, updated_at=now,
        )
        db.session.add(template); db.session.flush()
        normalized = [row for row in items if row.get("task_name")] or [{"task_name": "晨间血压", "sort_order": 1}]
        for index, item in enumerate(normalized, 1):
            db.session.add(DailyTaskTemplateItem(
                template_id=template.id, task_name=item["task_name"],
                sort_order=item.get("sort_order", index), is_required=item.get("is_required", True), created_at=now,
            ))
        db.session.commit()
        if regenerate:
            record = DailyRecord.query.filter_by(user_id=user_id, record_date=effective).one_or_none()
            if record:
                cls.generate(record.id, effective, user_id, force=True)
        return template

    @staticmethod
    def recalculate(record_id, user_id=1):
        rows = DailyTask.query.filter_by(daily_record_id=record_id, user_id=user_id).all()
        record = DailyRecord.query.filter_by(id=record_id, user_id=user_id).one_or_none()
        if record:
            record.completion_rate = round(sum(bool(row.is_done) for row in rows) / len(rows) * 100) if rows else 0
            record.updated_at = _now(); db.session.commit()

    @classmethod
    def update_task(cls, task_id, is_done, user_id=1):
        row = DailyTask.query.filter_by(id=task_id, user_id=user_id).one_or_none()
        if row is None:
            return None
        row.is_done = bool(is_done)
        row.completed_at = _now() if row.is_done else None
        row.updated_at = _now()
        db.session.commit()
        cls.recalculate(row.daily_record_id, user_id)
        return {
            "id": row.id,
            "task_name": row.task_name_snapshot,
            "is_done": bool(row.is_done),
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }


class AlertRepository:
    @staticmethod
    def list(record_date=None, user_id=1):
        query = HealthAlert.query.filter_by(user_id=user_id)
        if record_date: query = query.filter_by(record_date=_date(record_date))
        rows = query.order_by(HealthAlert.created_at.desc()).all()
        return [{"id":r.id,"alert_type":r.alert_type,"level":r.risk_level,"risk_level":r.risk_level,"title":r.title,"description":r.description,"content":r.content,"is_read":bool(r.is_read),"created_at":r.created_at.isoformat()} for r in rows]

    @staticmethod
    def mark_read(alert_id, user_id=1):
        row=HealthAlert.query.filter_by(id=alert_id,user_id=user_id).one_or_none()
        if not row:return False
        row.is_read=True;db.session.commit();return True

    @staticmethod
    def sync_vitals(record, vitals, user_id=1):
        record_date = _date(record["record_date"])
        systolic = int(vitals.get("systolic_pressure") or 0)
        diastolic = int(vitals.get("diastolic_pressure") or 0)
        fasting = float(vitals.get("fasting_glucose") or 0)
        rules = {
            "pressure": None if systolic < 130 and diastolic < 85 else {
                "risk_level": "high" if systolic >= 160 or diastolic >= 100 else "medium",
                "title": "血压偏高" if systolic >= 140 or diastolic >= 90 else "血压需要关注",
                "description": f"当前血压 {systolic}/{diastolic} mmHg，建议低盐饮食并按计划复测。",
                "content": f"血压 {systolic}/{diastolic} mmHg，需要持续关注。",
            },
            "glucose": None if fasting < 6.1 else {
                "risk_level": "high" if fasting >= 7.0 else "medium",
                "title": "空腹血糖偏高",
                "description": f"空腹血糖 {fasting:g} mmol/L，建议控制精制碳水并保持餐后活动。",
                "content": f"空腹血糖 {fasting:g} mmol/L，需要持续关注。",
            },
        }
        for alert_type, values in rules.items():
            row = HealthAlert.query.filter_by(
                user_id=user_id, record_date=record_date, alert_type=alert_type
            ).one_or_none()
            if values is None:
                if row:
                    db.session.delete(row)
                continue
            if row is None:
                row = HealthAlert(
                    user_id=user_id, alert_type=alert_type, record_date=record_date,
                    source_type="vital", source_id=vitals["id"], is_read=False,
                    created_at=_now(), **values,
                )
                db.session.add(row)
            else:
                changed = row.content != values["content"]
                for key, value in values.items():
                    setattr(row, key, value)
                row.source_id = vitals["id"]
                row.created_at = _now()
                if changed:
                    row.is_read = False
        db.session.commit()

    @staticmethod
    def count(user_id=None):
        query = HealthAlert.query
        if user_id is not None:
            query = query.filter_by(user_id=user_id)
        return query.count()


def bootstrap_task_alert_data(store):
    for source in store.task_templates:
        template=DailyTaskTemplate(id=source["id"],user_id=source.get("user_id",1),version_no=source["version_no"],effective_from=_date(source["effective_from"]),effective_to=_date(source["effective_to"]) if source.get("effective_to") else None,is_active=source.get("is_active",True),created_at=_datetime(source.get("created_at")) or _now(),updated_at=_datetime(source.get("updated_at")) or _now())
        db.session.merge(template)
        for item in source.get("items",[]):db.session.merge(DailyTaskTemplateItem(id=item["id"],template_id=source["id"],task_name=item["task_name"],sort_order=item.get("sort_order",0),is_required=item.get("is_required",True),created_at=_datetime(item.get("created_at")) or _now()))
    db.session.flush()
    existing_record_ids = {
        row[0] for row in db.session.query(DailyRecord.id).all()
    }
    for record_id,sources in store.tasks_by_record_id.items():
        if int(record_id) not in existing_record_ids:
            continue
        for s in sources:db.session.merge(DailyTask(id=s["id"],daily_record_id=int(record_id),user_id=s.get("user_id",1),record_date=_date(s["record_date"]),template_id=s["template_id"],template_item_id=s["template_item_id"],task_name_snapshot=s["task_name_snapshot"],is_done=s.get("is_done",False),completed_at=_datetime(s.get("completed_at")),sort_order=s.get("sort_order",0),created_at=_datetime(s.get("created_at")) or _now(),updated_at=_datetime(s.get("updated_at")) or _now()))
    for s in store.alerts.values():db.session.merge(HealthAlert(id=s["id"],user_id=s.get("user_id",1),alert_type=s.get("alert_type","vital"),record_date=_date(s["date"]),source_type=s.get("source_type","vital"),source_id=s.get("source_id"),title=s["title"],content=s["content"],description=s.get("description",s["content"]),risk_level=s.get("risk_level",s.get("level","low")),is_read=s.get("is_read",False),created_at=_datetime(s.get("created_at")) or _now()))
    db.session.commit()
