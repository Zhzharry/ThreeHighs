from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import DailyRecord, HealthAlert, MealRecord, User, VitalRecord


MEAL_NAMES = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐", "extra": "加餐"}


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


def _date(value):
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _number(value):
    return float(value) if isinstance(value, Decimal) else value


class DailyRepository:
    @staticmethod
    def serialize_record(row):
        return {
            "id": row.id,
            "record_date": row.record_date.isoformat(),
            "completion_rate": row.completion_rate or 0,
            "health_score": row.health_score,
            "summary": row.summary,
            "note": row.note or "",
            "mood": row.mood or "",
            "status": "editing",
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @classmethod
    def get_by_date(cls, record_date, user_id=1):
        return DailyRecord.query.filter_by(user_id=user_id, record_date=_date(record_date)).one_or_none()

    @staticmethod
    def get_by_id(record_id, user_id=1):
        return DailyRecord.query.filter_by(id=record_id, user_id=user_id).one_or_none()

    @classmethod
    def get_or_create(cls, record_date, user_id=1, create=True):
        row = cls.get_by_date(record_date, user_id)
        if row is None and create:
            now = _now()
            row = DailyRecord(
                user_id=user_id,
                record_date=_date(record_date),
                completion_rate=0,
                health_score=82,
                summary="今日血糖略高，建议晚餐减少主食。",
                note="",
                mood="平稳",
                created_at=now,
                updated_at=now,
            )
            db.session.add(row)
            db.session.commit()
        return row

    @classmethod
    def update(cls, record_id, payload, user_id=1):
        row = cls.get_by_id(record_id, user_id)
        if row is None:
            return None
        for key in ("note", "mood", "summary"):
            if key in payload:
                setattr(row, key, payload[key])
        row.updated_at = _now()
        db.session.commit()
        return cls.serialize_record(row)

    @classmethod
    def set_completion(cls, record_id, completion_rate, user_id=1):
        row = cls.get_by_id(record_id, user_id)
        if row is None:
            return False
        row.completion_rate = completion_rate
        row.updated_at = _now()
        db.session.commit()
        return True

    @classmethod
    def calendar_marks(cls, month, user_id=1):
        month_start = datetime.strptime(month, "%Y-%m").date()
        _, last_day = calendar.monthrange(month_start.year, month_start.month)
        start = date(month_start.year, month_start.month, 1)
        end = date(month_start.year, month_start.month, last_day)
        rows = DailyRecord.query.filter(
            DailyRecord.user_id == user_id,
            DailyRecord.record_date.between(start, end),
        ).all()
        by_date = {row.record_date.isoformat(): row for row in rows}
        alert_dates = {
            row.record_date.isoformat() for row in HealthAlert.query.filter(
                HealthAlert.user_id == user_id,
                HealthAlert.record_date.between(start, end),
            ).all()
        }
        days = [{
            "date": value,
            "has_record": True,
            "completion_rate": row.completion_rate or 0,
            "has_alert": value in alert_dates,
        } for value, row in sorted(by_date.items())]
        return {"month": month, "days": days}

    @staticmethod
    def serialize_vital(row):
        if row is None:
            return {}
        return {
            "id": row.id,
            "daily_record_id": row.daily_record_id,
            "systolic_pressure": row.systolic_pressure,
            "diastolic_pressure": row.diastolic_pressure,
            "fasting_glucose": _number(row.fasting_glucose),
            "postprandial_glucose": _number(row.postprandial_glucose),
            "weight_kg": _number(row.weight_kg),
            "measured_at": row.measured_at.isoformat() if row.measured_at else None,
            "remark": row.remark or "",
        }

    @classmethod
    def get_vital(cls, record_id, user_id=1):
        row = VitalRecord.query.filter_by(daily_record_id=record_id, user_id=user_id).one_or_none()
        return cls.serialize_vital(row)

    @classmethod
    def update_vital(cls, record_id, payload, user_id=1):
        record = cls.get_by_id(record_id, user_id)
        if record is None:
            return None, None
        row = VitalRecord.query.filter_by(daily_record_id=record_id, user_id=user_id).one_or_none()
        if row is None:
            row = VitalRecord(daily_record_id=record_id, user_id=user_id, created_at=_now())
            db.session.add(row)
        for key in (
            "systolic_pressure", "diastolic_pressure", "fasting_glucose",
            "postprandial_glucose", "weight_kg", "remark",
        ):
            if key in payload:
                setattr(row, key, payload[key])
        if "measured_at" in payload:
            row.measured_at = _datetime(payload["measured_at"])
        elif row.measured_at is None:
            row.measured_at = _now()
        db.session.commit()
        return cls.serialize_record(record), cls.serialize_vital(row)

    @staticmethod
    def _foods(row):
        try:
            value = json.loads(row.food_text or "[]")
            return value if isinstance(value, list) else []
        except (TypeError, ValueError):
            return []

    @classmethod
    def serialize_meal(cls, row):
        return {
            "id": row.id,
            "meal_type": row.meal_type,
            "meal_name": row.meal_name or MEAL_NAMES.get(row.meal_type, "加餐"),
            "foods": cls._foods(row),
        }

    @staticmethod
    def _nutrition(foods):
        totals = {"calories": 0.0, "sugar": 0.0, "fat": 0.0, "salt": 0.0}
        for food in foods:
            for key in totals:
                totals[key] += float(food.get(key, 0) or 0)
        return totals

    @classmethod
    def nutrition_summary(cls, record_id, user_id=1):
        rows = MealRecord.query.filter_by(daily_record_id=record_id, user_id=user_id).all()
        totals = {"calories": 0.0, "sugar": 0.0, "fat": 0.0, "salt": 0.0}
        for row in rows:
            values = cls._nutrition(cls._foods(row))
            for key in totals:
                totals[key] += values[key]
        return {
            "calories": round(totals["calories"]),
            "sugar": round(totals["sugar"], 1),
            "fat": round(totals["fat"], 1),
            "salt": round(totals["salt"], 1),
        }

    @classmethod
    def get_meals(cls, record_id, user_id=1):
        rows = MealRecord.query.filter_by(daily_record_id=record_id, user_id=user_id).order_by(MealRecord.id).all()
        return {"meals": [cls.serialize_meal(row) for row in rows], "summary": cls.nutrition_summary(record_id, user_id)}

    @classmethod
    def add_meal(cls, record_id, payload, user_id=1):
        if cls.get_by_id(record_id, user_id) is None:
            return None
        now = _now()
        foods = payload.get("foods", [])
        totals = cls._nutrition(foods)
        meal_type = payload.get("meal_type", "extra")
        row = MealRecord(
            daily_record_id=record_id,
            user_id=user_id,
            meal_type=meal_type,
            meal_name=payload.get("meal_name") or MEAL_NAMES.get(meal_type, "加餐"),
            food_text=json.dumps(foods, ensure_ascii=False),
            calories=totals["calories"],
            sugar_g=totals["sugar"],
            fat_g=totals["fat"],
            salt_g=totals["salt"],
            created_at=now,
            updated_at=now,
        )
        db.session.add(row)
        db.session.commit()
        return cls.serialize_meal(row)

    @classmethod
    def update_meal(cls, meal_id, payload, user_id=1):
        row = MealRecord.query.filter_by(id=meal_id, user_id=user_id).one_or_none()
        if row is None:
            return None
        if "meal_type" in payload:
            row.meal_type = payload["meal_type"]
        if "meal_name" in payload:
            row.meal_name = payload["meal_name"]
        if "foods" in payload:
            foods = payload["foods"]
            totals = cls._nutrition(foods)
            row.food_text = json.dumps(foods, ensure_ascii=False)
            row.calories = totals["calories"]
            row.sugar_g = totals["sugar"]
            row.fat_g = totals["fat"]
            row.salt_g = totals["salt"]
        row.updated_at = _now()
        db.session.commit()
        return cls.serialize_meal(row)

    @staticmethod
    def delete_meal(meal_id, user_id=1):
        row = MealRecord.query.filter_by(id=meal_id, user_id=user_id).one_or_none()
        if row is None:
            return False
        db.session.delete(row)
        db.session.commit()
        return True

    @classmethod
    def trends(cls, range_value="7d", user_id=1):
        days = {"7d": 7, "30d": 30, "90d": 90}.get(range_value, 7)
        end = date.today()
        start = end - timedelta(days=days - 1)
        rows = db.session.query(DailyRecord, VitalRecord).outerjoin(
            VitalRecord,
            (VitalRecord.daily_record_id == DailyRecord.id) & (VitalRecord.user_id == user_id),
        ).filter(
            DailyRecord.user_id == user_id,
            DailyRecord.record_date.between(start, end),
        ).all()
        by_date = {record.record_date: vital for record, vital in rows}
        points = []
        for offset in range(days - 1, -1, -1):
            current = end - timedelta(days=offset)
            vital = by_date.get(current)
            base = 130 + (days - offset) % 8
            points.append({
                "date": current.isoformat(),
                "systolic_pressure": vital.systolic_pressure if vital and vital.systolic_pressure is not None else base,
                "diastolic_pressure": vital.diastolic_pressure if vital and vital.diastolic_pressure is not None else 82 + base % 5,
                "fasting_glucose": _number(vital.fasting_glucose) if vital and vital.fasting_glucose is not None else round(6.0 + (base % 6) * 0.1, 1),
            })
        return {"range": range_value, "points": points}


def bootstrap_daily_data(store):
    """Import daily records, vitals and meals from the compatibility state."""
    if db.session.get(User, 1) is None:
        raise RuntimeError("User repository must be initialized before daily data")

    for source in store.daily_records_by_id.values():
        row = db.session.get(DailyRecord, int(source["id"]))
        if row is None:
            row = DailyRecord(id=int(source["id"]), user_id=int(source.get("user_id", 1)))
            db.session.add(row)
        row.record_date = _date(source["record_date"])
        row.completion_rate = source.get("completion_rate", 0)
        row.health_score = source.get("health_score")
        row.summary = source.get("summary")
        row.note = source.get("note", "")
        row.mood = source.get("mood", "")
        row.created_at = _datetime(source.get("created_at"))
        row.updated_at = _datetime(source.get("updated_at"))
    db.session.flush()

    for record_id, source in store.vitals_by_record_id.items():
        row = db.session.get(VitalRecord, int(source["id"]))
        if row is None:
            row = VitalRecord(id=int(source["id"]), daily_record_id=int(record_id), user_id=1)
            db.session.add(row)
        for key in ("systolic_pressure", "diastolic_pressure", "fasting_glucose", "postprandial_glucose", "weight_kg", "remark"):
            if key in source:
                setattr(row, key, source[key])
        row.measured_at = _datetime(source.get("measured_at"))
        row.created_at = _datetime(source.get("created_at"), row.measured_at)

    for record_id, sources in store.meals_by_record_id.items():
        for source in sources:
            if db.session.get(MealRecord, int(source["id"])) is not None:
                continue
            foods = source.get("foods", [])
            totals = DailyRepository._nutrition(foods)
            db.session.add(MealRecord(
                id=int(source["id"]), daily_record_id=int(record_id), user_id=1,
                meal_type=source.get("meal_type", "extra"),
                meal_name=source.get("meal_name") or MEAL_NAMES.get(source.get("meal_type"), "加餐"),
                food_text=json.dumps(foods, ensure_ascii=False),
                calories=totals["calories"], sugar_g=totals["sugar"], fat_g=totals["fat"], salt_g=totals["salt"],
                created_at=_now(), updated_at=_now(),
            ))
    db.session.commit()
