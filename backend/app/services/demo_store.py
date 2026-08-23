from __future__ import annotations

import calendar
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone

from app.extensions import db
from app.models.state import AppState


CN_TZ = timezone(timedelta(hours=8))


def now_iso():
    return datetime.now(CN_TZ).replace(microsecond=0).isoformat()


def today_str():
    return date.today().isoformat()


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_month(value):
    return datetime.strptime(value, "%Y-%m").date()


def mask_phone(phone):
    if not phone or len(phone) < 7:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


class DemoStore:
    """First-version seed/import source plus deterministic demo AI responses."""

    def __init__(self):
        self.user = {
            "id": 1,
            "openid": "demo-openid",
            "username": "李明",
            "nickname": "李明",
            "avatar_url": "",
            "age": 56,
            "phone": "13812340926",
            "role": "user",
            "status": 1,
            "created_at": "2026-08-01T09:00:00+08:00",
            "updated_at": now_iso(),
        }
        self.health_profile = {
            "gender": "男",
            "age": 56,
            "height_cm": 172,
            "weight_kg": 74,
            "bmi": 25.1,
            "disease_type": "高血压 + 高血糖",
            "medical_history": "轻度脂肪肝",
            "chronic_types": ["hypertension", "diabetes"],
            "medication": "二甲双胍、氨氯地平",
            "medications": "二甲双胍、氨氯地平",
            "updated_at": now_iso(),
        }
        self.settings = {
            "alert_push_enabled": True,
            "daily_record_reminder_enabled": True,
            "daily_record_reminder_time": "20:30",
        }
        self.domain_migrations = {}

        self._next_record_id = 101
        self._next_task_id = 1001
        self._next_template_id = 21
        self._next_template_item_id = 201
        self._next_vital_id = 301
        self._next_meal_id = 401
        self._next_report_id = 601
        self._next_indicator_id = 701
        self._next_alert_id = 501
        self._next_conversation_id = 801
        self._next_message_id = 9001
        self._next_food_id = 10001
        self._next_announcement_id = 11001

        self.daily_records_by_date = {}
        self.daily_records_by_id = {}
        self.vitals_by_record_id = {}
        self.meals_by_record_id = {}
        self.alerts = {}
        self.task_templates = []
        self.tasks_by_record_id = {}
        self.reports = {}
        self.indicators_by_report_id = {}
        self.conversations = {}
        self.messages_by_conversation_id = {}
        self.food_items = {}
        self.announcements = {}

        self._seed()

    def load_persisted_state(self):
        state = db.session.get(AppState, "demo-store-v1")
        if not state or not state.payload:
            return False

        payload = deepcopy(state.payload)
        integer_key_maps = {
            "daily_records_by_id", "vitals_by_record_id", "meals_by_record_id",
            "alerts", "tasks_by_record_id", "reports", "indicators_by_report_id",
            "conversations", "messages_by_conversation_id", "food_items", "announcements",
        }
        for name in integer_key_maps:
            if name in payload:
                payload[name] = {int(key): value for key, value in payload[name].items()}
        self.__dict__.update(payload)
        self.daily_records_by_date = {
            record["record_date"]: record for record in self.daily_records_by_id.values()
        }
        return True

    def persist(self):
        payload = deepcopy(self.__dict__)
        # Migrated records are owned by domain tables. Keeping them out of
        # app_state prevents two writable sources of truth while preserving
        # the source data until each one-time import has completed.
        migrations = payload.get("domain_migrations", {})
        if migrations.get("reference-repositories-v1"):
            payload.pop("food_items", None)
            payload.pop("announcements", None)
        if migrations.get("user-repositories-v1"):
            payload.pop("user", None)
            payload.pop("health_profile", None)
            payload.pop("settings", None)
        if migrations.get("daily-repositories-v1"):
            payload.pop("daily_records_by_date", None)
            payload.pop("daily_records_by_id", None)
            payload.pop("vitals_by_record_id", None)
            payload.pop("meals_by_record_id", None)
        if migrations.get("task-alert-repositories-v1"):
            payload.pop("task_templates", None)
            payload.pop("tasks_by_record_id", None)
            payload.pop("alerts", None)
        if migrations.get("report-repositories-v1"):
            payload.pop("reports", None)
            payload.pop("indicators_by_report_id", None)
        if migrations.get("ai-repositories-v1"):
            payload.pop("conversations", None)
            payload.pop("messages_by_conversation_id", None)
        completed_migrations = {
            "reference-repositories-v1", "user-repositories-v1", "daily-repositories-v1",
            "task-alert-repositories-v1", "report-repositories-v1", "ai-repositories-v1",
        }
        if completed_migrations.issubset({key for key, value in migrations.items() if value}):
            payload = {"domain_migrations": migrations}
        state = db.session.get(AppState, "demo-store-v1")
        if state is None:
            state = AppState(key="demo-store-v1", payload=payload, updated_at=datetime.now(CN_TZ))
            db.session.add(state)
        else:
            state.payload = payload
            state.updated_at = datetime.now(CN_TZ)
        db.session.commit()

    def _seed(self):
        current_date = today_str()
        previous_date = (parse_date(current_date) - timedelta(days=1)).isoformat()

        old_template = self._create_template(
            effective_from="2026-08-01",
            effective_to=(parse_date(current_date) - timedelta(days=1)).isoformat(),
            items=["晨间血压", "空腹血糖", "三餐饮食", "晚间复测", "用药打卡"],
            active=False,
        )
        current_template = self._create_template(
            effective_from=current_date,
            effective_to=None,
            items=["晨间血压", "空腹血糖", "三餐饮食", "晚间复测"],
            active=True,
        )

        previous_record = self._create_daily_record(previous_date, generate_tasks=False)
        self._generate_tasks(previous_record["id"], previous_date, old_template, force=True)
        for task in self.tasks_by_record_id[previous_record["id"]]:
            task["is_done"] = True
            task["completed_at"] = f"{previous_date}T20:10:00+08:00"
        self._recalculate_completion(previous_record["id"])

        today_record = self._create_daily_record(current_date, generate_tasks=False)
        self._generate_tasks(today_record["id"], current_date, current_template, force=True)
        for task in self.tasks_by_record_id[today_record["id"]][:3]:
            task["is_done"] = True
            task["completed_at"] = f"{current_date}T08:30:00+08:00"
        self._recalculate_completion(today_record["id"])

        self.vitals_by_record_id[today_record["id"]] = {
            "id": self._take("vital"),
            "daily_record_id": today_record["id"],
            "systolic_pressure": 138,
            "diastolic_pressure": 86,
            "fasting_glucose": 6.8,
            "postprandial_glucose": 8.4,
            "measured_at": f"{current_date}T08:20:00+08:00",
        }
        self.vitals_by_record_id[previous_record["id"]] = {
            "id": self._take("vital"),
            "daily_record_id": previous_record["id"],
            "systolic_pressure": 132,
            "diastolic_pressure": 84,
            "fasting_glucose": 6.2,
            "postprandial_glucose": 7.6,
            "measured_at": f"{previous_date}T08:15:00+08:00",
        }

        self.meals_by_record_id[today_record["id"]] = [
            {
                "id": self._take("meal"),
                "meal_type": "breakfast",
                "meal_name": "早餐",
                "foods": [
                    {"name": "燕麦粥", "amount": "1 碗", "calories": 180, "sugar": 3.2, "fat": 2.1, "salt": 0.3},
                    {"name": "鸡蛋", "amount": "1 个", "calories": 70, "sugar": 0.2, "fat": 5.0, "salt": 0.2},
                ],
            },
            {
                "id": self._take("meal"),
                "meal_type": "lunch",
                "meal_name": "午餐",
                "foods": [
                    {"name": "糙米饭", "amount": "半碗", "calories": 120, "sugar": 1.1, "fat": 0.8, "salt": 0.1},
                    {"name": "清蒸鱼", "amount": "1 份", "calories": 220, "sugar": 0.1, "fat": 8.5, "salt": 0.8},
                ],
            },
        ]

        alert_id = self._take("alert")
        self.alerts[alert_id] = {
            "id": alert_id,
            "alert_type": "glucose",
            "source_type": "vital",
            "source_id": self.vitals_by_record_id[today_record["id"]]["id"],
            "date": current_date,
            "level": "medium",
            "risk_level": "medium",
            "title": "空腹血糖偏高",
            "description": "建议晚餐减少精制碳水，饭后散步 20-30 分钟。",
            "content": "空腹血糖 6.8 mmol/L，建议关注晚餐结构。",
            "is_read": False,
            "created_at": f"{current_date}T08:40:00+08:00",
        }

        report = self._create_report(
            file_name="体检报告.pdf",
            file_type="pdf",
            source="pdf",
            report_date=current_date,
            file_url="/storage/uploads/demo-report.pdf",
        )
        report["status"] = "review_pending"
        report["progress"] = 100
        report["confidence"] = 0.92
        report["summary"] = "空腹血糖、总胆固醇偏高"
        self._replace_report_indicators(report["id"], [
            {
                "indicator_name": "空腹血糖",
                "indicator_code": "GLU",
                "value": 6.8,
                "unit": "mmol/L",
                "reference_range": "3.9-6.1",
                "status": "high",
                "result_status": "high",
                "risk_level": "medium",
            },
            {
                "indicator_name": "总胆固醇",
                "indicator_code": "TC",
                "value": 5.9,
                "unit": "mmol/L",
                "reference_range": "<5.2",
                "status": "high",
                "result_status": "high",
                "risk_level": "medium",
            },
        ])

        conversation = self.create_conversation("晚饭怎么吃", "daily_record", current_date)
        self._add_message(conversation["conversation_id"], "user", "最近空腹血糖偏高，晚饭应该怎么吃？")
        self._add_message(
            conversation["conversation_id"],
            "assistant",
            "晚餐主食建议控制在半碗左右，优先选择杂粮、豆制品和深色蔬菜，饭后散步 20-30 分钟。",
        )

        self._create_food("糙米饭", "主食", "100g", 116, 0.4, 0.9, 0.02)
        self._create_food("燕麦粥", "主食", "100g", 68, 0.7, 1.4, 0.01)
        self._create_announcement("夏季血压管理提醒", "高温天气请注意补水，按时测量血压。", True)

    def _take(self, name):
        attr = f"_next_{name}_id"
        value = getattr(self, attr)
        setattr(self, attr, value + 1)
        return value

    def _create_template(self, effective_from, effective_to, items, active):
        template = {
            "id": self._take("template"),
            "template_id": self._next_template_id - 1,
            "user_id": 1,
            "version_no": len(self.task_templates) + 1,
            "effective_from": effective_from,
            "effective_to": effective_to,
            "is_active": active,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "items": [],
        }
        for index, task_name in enumerate(items, start=1):
            template["items"].append({
                "id": self._take("template_item"),
                "task_name": task_name,
                "sort_order": index,
                "is_required": True,
                "created_at": now_iso(),
            })
        self.task_templates.append(template)
        return template

    def _create_daily_record(self, record_date, generate_tasks=True):
        if record_date in self.daily_records_by_date:
            return self.daily_records_by_date[record_date]
        record = {
            "id": self._take("record"),
            "user_id": 1,
            "record_date": record_date,
            "completion_rate": 0,
            "health_score": 82,
            "summary": "今日血糖略高，建议晚餐减少主食。",
            "note": "",
            "mood": "平稳",
            "status": "editing",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        self.daily_records_by_date[record_date] = record
        self.daily_records_by_id[record["id"]] = record
        self.meals_by_record_id.setdefault(record["id"], [])
        if generate_tasks:
            self._generate_tasks(record["id"], record_date)
        return record

    def _effective_template(self, record_date):
        target = parse_date(record_date)
        candidates = []
        for template in self.task_templates:
            start = parse_date(template["effective_from"])
            end = parse_date(template["effective_to"]) if template["effective_to"] else None
            if start <= target and (end is None or target <= end):
                candidates.append(template)
        if not candidates:
            return self._create_template(record_date, None, ["晨间血压", "空腹血糖", "三餐饮食"], True)
        return sorted(candidates, key=lambda item: item["version_no"])[-1]

    def _generate_tasks(self, record_id, record_date, template=None, force=False, preserve_by_name=None):
        if self.tasks_by_record_id.get(record_id) and not force:
            return self.tasks_by_record_id[record_id]
        template = template or self._effective_template(record_date)
        preserve_by_name = preserve_by_name or {}
        tasks = []
        for item in sorted(template["items"], key=lambda row: row["sort_order"]):
            preserved = preserve_by_name.get(item["task_name"], {})
            is_done = bool(preserved.get("is_done", False))
            tasks.append({
                "id": self._take("task"),
                "daily_record_id": record_id,
                "user_id": 1,
                "record_date": record_date,
                "template_id": template["id"],
                "template_item_id": item["id"],
                "task_name": item["task_name"],
                "task_name_snapshot": item["task_name"],
                "is_done": is_done,
                "completed_at": preserved.get("completed_at") if is_done else None,
                "sort_order": item["sort_order"],
                "created_at": now_iso(),
                "updated_at": now_iso(),
            })
        self.tasks_by_record_id[record_id] = tasks
        self._recalculate_completion(record_id)
        return tasks

    def _recalculate_completion(self, record_id, user_id=1):
        from flask import has_app_context

        tasks = self.tasks_by_record_id.get(record_id, [])
        completion = round(sum(1 for task in tasks if task["is_done"]) / len(tasks) * 100) if tasks else 0
        shadow = self.daily_records_by_id.get(record_id)
        if shadow:
            shadow["completion_rate"] = completion
            shadow["updated_at"] = now_iso()
        if has_app_context():
            from app.repositories import DailyRepository

            DailyRepository.set_completion(record_id, completion, user_id)

    def daily_payload(self, record_date=None, create=True, user_id=1):
        from app.repositories import DailyRepository

        record_date = record_date or today_str()
        record = DailyRepository.get_or_create(record_date, user_id, create)
        if not record:
            return None
        from app.repositories import TaskRepository

        TaskRepository.generate(record.id, record_date, user_id)
        return {
            "record": DailyRepository.serialize_record(record),
            "tasks": TaskRepository.serialize_tasks(record.id, user_id),
            "vitals": DailyRepository.get_vital(record.id, user_id),
            "nutrition": DailyRepository.nutrition_summary(record.id, user_id),
            "alerts": self.list_alerts(record_date, user_id),
        }

    def serialize_record(self, record):
        return {
            "id": record["id"],
            "record_date": record["record_date"],
            "completion_rate": record["completion_rate"],
            "health_score": record.get("health_score"),
            "summary": record.get("summary"),
            "note": record.get("note", ""),
            "mood": record.get("mood", ""),
            "status": record.get("status", "editing"),
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }

    def serialize_tasks(self, record_id, user_id=1):
        from app.repositories import TaskRepository

        return TaskRepository.serialize_tasks(record_id, user_id)

    def get_record_by_id(self, record_id, user_id=1):
        from app.repositories import DailyRepository

        row = DailyRepository.get_by_id(record_id, user_id)
        return DailyRepository.serialize_record(row) if row else None

    def update_daily_record(self, record_id, payload, user_id=1):
        from app.repositories import DailyRepository

        return DailyRepository.update(record_id, payload, user_id)

    def calendar_marks(self, month, user_id=1):
        from app.repositories import DailyRepository

        return DailyRepository.calendar_marks(month, user_id)

    def update_vitals(self, record_id, payload, user_id=1):
        from app.repositories import DailyRepository

        record, current = DailyRepository.update_vital(record_id, payload, user_id)
        if not record:
            return None
        risk_level = self._vital_risk(current)
        self._sync_vital_alerts(record, current)
        return {
            **deepcopy(current),
            "risk_level": risk_level,
            "advice": "指标略高，建议控制晚餐碳水和盐分，并保持规律复测。" if risk_level != "low" else "当前指标较平稳，请继续保持。",
        }

    def _sync_vital_alerts(self, record, vitals):
        """Keep pressure/glucose alerts aligned with the latest daily values."""
        from app.repositories import AlertRepository

        AlertRepository.sync_vitals(record, vitals, int(record.get("user_id", 1)))
        return

        record_date = record["record_date"]
        systolic = int(vitals.get("systolic_pressure") or 0)
        diastolic = int(vitals.get("diastolic_pressure") or 0)
        fasting = float(vitals.get("fasting_glucose") or 0)

        rules = {
            "pressure": None if systolic < 130 and diastolic < 85 else {
                "level": "high" if systolic >= 160 or diastolic >= 100 else "medium",
                "title": "血压偏高" if systolic >= 140 or diastolic >= 90 else "血压需要关注",
                "description": f"当前血压 {systolic}/{diastolic} mmHg，建议低盐饮食并按计划复测。",
                "content": f"血压 {systolic}/{diastolic} mmHg，需要持续关注。",
            },
            "glucose": None if fasting < 6.1 else {
                "level": "high" if fasting >= 7.0 else "medium",
                "title": "空腹血糖偏高",
                "description": f"空腹血糖 {fasting:g} mmol/L，建议控制精制碳水并保持餐后活动。",
                "content": f"空腹血糖 {fasting:g} mmol/L，需要持续关注。",
            },
        }

        for alert_type, result in rules.items():
            existing = next((
                alert for alert in self.alerts.values()
                if alert["date"] == record_date and alert["alert_type"] == alert_type
            ), None)
            if result is None:
                if existing:
                    self.alerts.pop(existing["id"], None)
                continue

            if existing:
                changed = existing.get("content") != result["content"]
                existing.update({
                    **result,
                    "risk_level": result["level"],
                    "source_id": vitals["id"],
                    "created_at": now_iso(),
                })
                if changed:
                    existing["is_read"] = False
                continue

            alert_id = self._take("alert")
            self.alerts[alert_id] = {
                "id": alert_id,
                "user_id": record.get("user_id", 1),
                "alert_type": alert_type,
                "source_type": "vital",
                "source_id": vitals["id"],
                "date": record_date,
                **result,
                "risk_level": result["level"],
                "is_read": False,
                "created_at": now_iso(),
            }

    def _vital_risk(self, vitals):
        systolic = vitals.get("systolic_pressure") or 0
        fasting = float(vitals.get("fasting_glucose") or 0)
        if systolic >= 160 or fasting >= 7.0:
            return "high"
        if systolic >= 130 or fasting >= 6.1:
            return "medium"
        return "low"

    def nutrition_summary(self, record_id, user_id=1):
        from app.repositories import DailyRepository

        return DailyRepository.nutrition_summary(record_id, user_id)

    def get_meals(self, record_id, user_id=1):
        from app.repositories import DailyRepository

        return DailyRepository.get_meals(record_id, user_id)

    def add_meal(self, record_id, payload, user_id=1):
        from app.repositories import DailyRepository

        return DailyRepository.add_meal(record_id, payload, user_id)

    def update_meal(self, meal_id, payload, user_id=1):
        from app.repositories import DailyRepository

        return DailyRepository.update_meal(meal_id, payload, user_id)

    def delete_meal(self, meal_id, user_id=1):
        from app.repositories import DailyRepository

        return DailyRepository.delete_meal(meal_id, user_id)

    def get_current_template(self, record_date, user_id=1):
        from app.repositories import TaskRepository

        return TaskRepository.current_template(record_date, user_id)

    def update_template(self, effective_date, items, user_id=1):
        from app.repositories import TaskRepository

        template = TaskRepository.update_template(effective_date, items, user_id)
        return TaskRepository.serialize_template(template)

    def _update_template_compatibility(self, effective_date, items):
        effective = parse_date(effective_date)
        normalized_items = [item for item in items if item.get("task_name")]
        if not normalized_items:
            normalized_items = [{"task_name": "晨间血压", "sort_order": 1}]

        for template in self.task_templates:
            start = parse_date(template["effective_from"])
            end = parse_date(template["effective_to"]) if template["effective_to"] else None
            if start <= effective and (end is None or effective <= end):
                template["effective_to"] = (effective - timedelta(days=1)).isoformat()
                template["is_active"] = False
                template["updated_at"] = now_iso()

        template = {
            "id": self._take("template"),
            "template_id": self._next_template_id - 1,
            "user_id": 1,
            "version_no": max([row["version_no"] for row in self.task_templates] or [0]) + 1,
            "effective_from": effective_date,
            "effective_to": None,
            "is_active": True,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "items": [],
        }
        for index, item in enumerate(normalized_items, start=1):
            template["items"].append({
                "id": self._take("template_item"),
                "task_name": item["task_name"],
                "sort_order": item.get("sort_order", index),
                "is_required": item.get("is_required", True),
                "created_at": now_iso(),
            })
        self.task_templates.append(template)

        from app.repositories import DailyRepository

        record = DailyRepository.get_by_date(effective_date, 1)
        if record:
            old_tasks = self.tasks_by_record_id.get(record.id, [])
            preserve = {task["task_name_snapshot"]: task for task in old_tasks}
            self._generate_tasks(record.id, effective_date, template=template, force=True, preserve_by_name=preserve)
        return self._serialize_template(template)

    def generate_tasks_for_record(self, record_id, record_date=None, user_id=1):
        from app.repositories import TaskRepository

        tasks = TaskRepository.generate(record_id, record_date, user_id, force=True)
        if tasks is None:
            return None
        return {"record_id": record_id, "generated_count": len(tasks)}

    def update_task(self, task_id, is_done, user_id=1):
        from app.repositories import TaskRepository

        return TaskRepository.update_task(task_id, is_done, user_id)

    def _serialize_template(self, template):
        return {
            "template_id": template["id"],
            "version_no": template["version_no"],
            "effective_from": template["effective_from"],
            "effective_to": template["effective_to"],
            "items": [
                {
                    "id": item["id"],
                    "task_name": item["task_name"],
                    "sort_order": item["sort_order"],
                }
                for item in sorted(template["items"], key=lambda row: row["sort_order"])
            ],
        }

    def trends(self, range_value="7d", user_id=1):
        from app.repositories import DailyRepository

        return DailyRepository.trends(range_value, user_id)

    def predictions(self, days=7):
        start = parse_date(today_str())
        predictions = []
        for offset in range(1, days + 1):
            predictions.append({
                "date": (start + timedelta(days=offset)).isoformat(),
                "systolic_pressure": max(128, 138 - offset),
                "diastolic_pressure": max(80, 86 - offset // 2),
                "fasting_glucose": round(max(6.1, 6.8 - offset * 0.08), 1),
                "risk_level": "medium" if offset < 5 else "low",
            })
        return {
            "model_name": "RandomForestRegressor",
            "model_version": "demo-1.0",
            "days": days,
            "predictions": predictions,
            "explanation": "近期空腹血糖略高，晚餐碳水和餐后运动对预测结果影响较大。",
        }

    def list_alerts(self, record_date=None, user_id=1):
        from app.repositories import AlertRepository

        return AlertRepository.list(record_date, user_id)

    def mark_alert_read(self, alert_id, user_id=1):
        from app.repositories import AlertRepository

        return AlertRepository.mark_read(alert_id, user_id)

    def _create_report(self, file_name, file_type, source, report_date, file_url):
        report = {
            "id": self._take("report"),
            "report_id": self._next_report_id - 1,
            "user_id": 1,
            "file_name": file_name,
            "file_type": file_type,
            "source": source,
            "file_url": file_url,
            "report_date": report_date,
            "status": "uploaded",
            "progress": 0,
            "confidence": None,
            "summary": "",
            "created_at": now_iso(),
            "uploaded_at": now_iso(),
            "reviewed_at": None,
        }
        self.reports[report["id"]] = report
        self.indicators_by_report_id[report["id"]] = []
        return report

    def upload_report(self, file_name, file_type, source, report_date, file_url, user_id=1):
        from app.repositories import ReportRepository
        return ReportRepository.upload(file_name, file_type, source, report_date or today_str(), file_url, user_id)

    def start_recognition(self, report_id, user_id=1):
        from app.repositories import ReportRepository
        return ReportRepository.start(report_id, user_id)

    def _start_recognition_compatibility(self, report_id):
        report = self.reports.get(report_id)
        if not report:
            return None
        report["status"] = "recognizing"
        report["progress"] = 10
        report["confidence"] = None
        report["reviewed_at"] = None
        report["summary"] = "正在识别体检报告"
        self.indicators_by_report_id[report_id] = []
        return {"report_id": report_id, "status": report["status"], "progress": report["progress"]}

    def report_progress(self, report_id, user_id=1):
        from app.repositories import ReportRepository
        return ReportRepository.progress(report_id, user_id)

    def _report_progress_compatibility(self, report_id):
        report = self.reports.get(report_id)
        if not report:
            return None
        if report["status"] in ("recognizing", "extracting"):
            report["progress"] = min(100, report["progress"] + 35)
            if report["progress"] < 70:
                report["status"] = "recognizing"
                message = "正在进行 OCR 识别"
            elif report["progress"] < 100:
                report["status"] = "extracting"
                message = "正在提取关键指标"
            else:
                report["status"] = "review_pending"
                report["confidence"] = 0.92
                report["summary"] = "空腹血糖、总胆固醇偏高"
                self._replace_report_indicators(report_id, self._default_indicators())
                message = "识别完成，等待管理员复核"
        else:
            message = "等待开始识别" if report["status"] == "uploaded" else "处理完成"
        return {
            "report_id": report_id,
            "status": report["status"],
            "progress": report["progress"],
            "message": message,
        }

    def report_detail(self, report_id, user_id=1):
        from app.repositories import ReportRepository
        row = ReportRepository.get(report_id, user_id)
        return ReportRepository.detail(row) if row else None

    def _report_detail_compatibility(self, report_id):
        report = self.reports.get(report_id)
        if not report:
            return None
        return {
            "id": report["id"],
            "file_name": report["file_name"],
            "file_type": report["file_type"],
            "report_date": report["report_date"],
            "status": report["status"],
            "confidence": report["confidence"],
            "summary": report["summary"],
            "created_at": report["created_at"],
        }

    def report_history(self, page, page_size, user_id=1):
        from app.repositories import ReportRepository
        return ReportRepository.history(page, page_size, user_id)

    def _report_history_compatibility(self, page, page_size):
        reports = sorted(self.reports.values(), key=lambda row: row["created_at"], reverse=True)
        total = len(reports)
        start = (page - 1) * page_size
        items = [
            {
                "id": report["id"],
                "file_name": report["file_name"],
                "report_date": report["report_date"],
                "status": report["status"],
                "summary": report["summary"],
            }
            for report in reports[start:start + page_size]
        ]
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    def report_indicators(self, report_id, user_id=1):
        from app.repositories import ReportRepository
        return ReportRepository.indicators(report_id, user_id)

    def update_report_indicators(self, report_id, indicators, user_id=1):
        from app.repositories import ReportRepository
        return ReportRepository.update_indicators(report_id, indicators, user_id)

    def _update_report_indicators_compatibility(self, report_id, indicators):
        report = self.reports.get(report_id)
        if not report:
            return None
        self._replace_report_indicators(report_id, indicators)
        report["status"] = "review_pending"
        report["summary"] = "指标已人工纠正，等待确认"
        report["updated_at"] = now_iso()
        return self.report_indicators(report_id)

    def confirm_report(self, report_id, review_note="", user_id=1):
        from app.repositories import ReportRepository
        return ReportRepository.confirm(report_id, review_note, user_id)

    def _confirm_report_compatibility(self, report_id, review_note=""):
        report = self.reports.get(report_id)
        if not report:
            return None
        if not self.indicators_by_report_id.get(report_id):
            return False
        report["status"] = "completed"
        report["review_note"] = review_note
        report["reviewed_at"] = now_iso()
        report["summary"] = review_note or report.get("summary") or "报告指标已确认"
        return self.report_detail(report_id)

    def delete_report(self, report_id, user_id=1):
        from app.repositories import ReportRepository
        return ReportRepository.delete(report_id, user_id)

    def _delete_report_compatibility(self, report_id):
        report = self.reports.pop(report_id, None)
        if not report:
            return None
        self.indicators_by_report_id.pop(report_id, None)
        return deepcopy(report)

    def _default_indicators(self):
        return [
            {
                "indicator_name": "空腹血糖",
                "indicator_code": "GLU",
                "value": 6.8,
                "unit": "mmol/L",
                "reference_range": "3.9-6.1",
                "status": "high",
                "result_status": "high",
                "risk_level": "medium",
            },
            {
                "indicator_name": "总胆固醇",
                "indicator_code": "TC",
                "value": 5.9,
                "unit": "mmol/L",
                "reference_range": "<5.2",
                "status": "high",
                "result_status": "high",
                "risk_level": "medium",
            },
        ]

    def _replace_report_indicators(self, report_id, indicators):
        rows = []
        for indicator in indicators:
            rows.append({
                "id": self._take("indicator"),
                "report_id": report_id,
                "user_id": 1,
                "indicator_name": indicator["indicator_name"],
                "indicator_code": indicator.get("indicator_code"),
                "value": indicator["value"],
                "unit": indicator.get("unit"),
                "reference_range": indicator.get("reference_range"),
                "status": indicator.get("status", indicator.get("result_status", "normal")),
                "result_status": indicator.get("result_status", indicator.get("status", "normal")),
                "risk_level": indicator.get("risk_level", "low"),
                "created_at": now_iso(),
            })
        self.indicators_by_report_id[report_id] = rows

    def review_report(self, report_id, payload):
        from app.repositories import ReportRepository
        return ReportRepository.review(report_id, payload)

    def _review_report_compatibility(self, report_id, payload):
        report = self.reports.get(report_id)
        if not report:
            return None
        report["status"] = payload.get("status", "completed")
        report["review_note"] = payload.get("review_note", "")
        report["reviewed_at"] = now_iso()
        if payload.get("indicators"):
            self._replace_report_indicators(report_id, payload["indicators"])
        return {
            "report_id": report_id,
            "status": report["status"],
            "reviewed_at": report["reviewed_at"],
        }

    def batch_review_reports(self, report_ids, status, review_note=""):
        from app.repositories import ReportRepository
        return ReportRepository.batch_review(report_ids, status, review_note)

    def _batch_review_reports_compatibility(self, report_ids, status, review_note=""):
        processed_ids = []
        for report_id in report_ids:
            if self.review_report(report_id, {"status": status, "review_note": review_note}):
                processed_ids.append(report_id)
        return {
            "requested_count": len(report_ids),
            "processed_count": len(processed_ids),
            "processed_ids": processed_ids,
            "missing_ids": [report_id for report_id in report_ids if report_id not in processed_ids],
        }

    def quick_questions(self):
        return ["晚饭怎么吃", "血压偏高怎么办", "报告异常怎么看", "今天适合运动吗"]

    def ai_context_today(self, record_date, user_id=1):
        payload = self.daily_payload(record_date, create=True, user_id=user_id)
        vitals = payload["vitals"]
        return {
            "date": record_date,
            "risk_cards": [
                {"label": "空腹血糖", "value": str(vitals.get("fasting_glucose", 6.8)), "unit": "mmol/L", "level": "medium"},
                {"label": "收缩压", "value": str(vitals.get("systolic_pressure", 138)), "unit": "mmHg", "level": "medium"},
            ],
            "summary": "今日空腹血糖和收缩压略高，建议控制晚餐碳水和盐分。",
        }

    def create_conversation(self, title, source=None, related_date=None, user_id=1):
        from flask import has_app_context
        if has_app_context():
            from app.repositories import AiRepository
            return AiRepository.create(title, source, related_date, user_id)
        conversation = {
            "id": self._take("conversation"),
            "conversation_id": self._next_conversation_id - 1,
            "user_id": 1,
            "title": title or "健康问答",
            "source": source or "manual",
            "related_date": related_date,
            "summary": "",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        self.conversations[conversation["id"]] = conversation
        self.messages_by_conversation_id[conversation["id"]] = []
        return {
            "conversation_id": conversation["id"],
            "title": conversation["title"],
            "created_at": conversation["created_at"],
        }

    def list_conversations(self, page, page_size, user_id=1):
        from app.repositories import AiRepository
        return AiRepository.list(page, page_size, user_id)

    def list_messages(self, conversation_id, user_id=1):
        from app.repositories import AiRepository
        return AiRepository.messages(conversation_id, user_id)

    def send_message(self, conversation_id, content, use_daily_context=True, related_date=None, user_id=1):
        from app.repositories import AiRepository
        user_message = AiRepository.add_message(conversation_id, "user", content, user_id)
        if user_message is None:
            return None
        answer = self._ai_answer(content, use_daily_context, related_date)
        assistant_message = AiRepository.add_message(conversation_id, "assistant", answer, user_id)
        return {
            "user_message": user_message,
            "assistant_message": assistant_message,
            "retrieval": {
                "collection": "health_knowledge",
                "hit_count": 3,
            },
        }

    def _add_message(self, conversation_id, role, content):
        message = {
            "id": self._take("message"),
            "role": role,
            "content": content,
            "created_at": now_iso(),
        }
        self.messages_by_conversation_id.setdefault(conversation_id, []).append(message)
        return deepcopy(message)

    def _ai_answer(self, content, use_daily_context, related_date):
        if "血压" in content:
            return "建议连续记录早晚血压，晚餐控制盐分，避免情绪波动和熬夜；如果收缩压持续高于 140 mmHg，建议及时咨询医生。"
        if "报告" in content or "异常" in content:
            return "报告异常需要结合参考范围和个人病史看。空腹血糖和总胆固醇偏高时，建议先复查并调整饮食结构。"
        if "运动" in content:
            return "今天适合低到中等强度运动，例如饭后散步 20-30 分钟。若头晕、胸闷或血压明显升高，应停止运动。"
        return "晚餐主食建议控制在半碗左右，优先选择杂粮、豆制品和深色蔬菜，饭后散步 20-30 分钟。"

    def delete_conversation(self, conversation_id, user_id=1):
        from app.repositories import AiRepository
        return AiRepository.delete(conversation_id, user_id)

    def get_profile(self, user_id=1):
        from app.repositories import UserRepository

        return UserRepository.get_profile(user_id)

    def update_profile(self, payload, user_id=1):
        from app.repositories import UserRepository

        return UserRepository.update_profile(payload, user_id)

    def update_health_profile(self, payload, user_id=1):
        from app.repositories import UserRepository

        return UserRepository.update_health_profile(payload, user_id)

    def get_settings(self, user_id=1):
        from app.repositories import UserRepository

        return UserRepository.get_settings(user_id)

    def update_settings(self, payload, user_id=1):
        from app.repositories import UserRepository

        return UserRepository.update_settings(payload, user_id)

    def admin_users(self, page, page_size, keyword=None):
        from app.repositories import UserRepository

        return UserRepository.admin_users(page, page_size, keyword)

    def admin_user_detail(self, user_id):
        from app.repositories import UserRepository

        return UserRepository.admin_user_detail(user_id)

    def update_admin_user(self, user_id, payload):
        from app.repositories import UserRepository

        return UserRepository.update_admin_user(user_id, payload)

    def admin_reports(self, page, page_size, status=None):
        from app.repositories import ReportRepository
        return ReportRepository.admin_list(page, page_size, status)

    def _create_food(self, name, category, unit, calories, sugar, fat, salt):
        food = {
            "id": self._take("food"),
            "name": name,
            "category": category,
            "unit": unit,
            "calories": calories,
            "sugar": sugar,
            "fat": fat,
            "salt": salt,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        self.food_items[food["id"]] = food
        return food

    def list_foods(self, page, page_size, keyword=None):
        from app.repositories import FoodRepository

        return FoodRepository.list(page, page_size, keyword)

    def create_food(self, payload):
        from app.repositories import FoodRepository

        return FoodRepository.create(payload)

    def update_food(self, food_id, payload):
        from app.repositories import FoodRepository

        return FoodRepository.update(food_id, payload)

    def delete_food(self, food_id):
        from app.repositories import FoodRepository

        return FoodRepository.delete(food_id)

    def batch_delete_foods(self, food_ids):
        from app.repositories import FoodRepository

        return FoodRepository.batch_delete(food_ids)

    def _create_announcement(self, title, content, published):
        announcement = {
            "id": self._take("announcement"),
            "title": title,
            "content": content,
            "is_published": bool(published),
            "publish_status": "published" if published else "draft",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        self.announcements[announcement["id"]] = announcement
        return announcement

    def list_announcements(self, page, page_size):
        from app.repositories import AnnouncementRepository

        return AnnouncementRepository.list(page, page_size)

    def create_announcement(self, payload):
        from app.repositories import AnnouncementRepository

        return AnnouncementRepository.create(payload)

    def update_announcement(self, announcement_id, payload):
        from app.repositories import AnnouncementRepository

        return AnnouncementRepository.update(announcement_id, payload)

    def delete_announcement(self, announcement_id):
        from app.repositories import AnnouncementRepository

        return AnnouncementRepository.delete(announcement_id)

    def batch_publish_announcements(self, announcement_ids, is_published):
        from app.repositories import AnnouncementRepository

        return AnnouncementRepository.batch_publish(announcement_ids, is_published)

    def admin_dashboard(self):
        from app.repositories import AlertRepository, AnnouncementRepository, ReportRepository, UserRepository

        pending = ReportRepository.pending_count()
        user = UserRepository.admin_user_detail(1)
        disease_labels = {"hypertension": "高血压", "diabetes": "高血糖", "hyperlipidemia": "高血脂"}
        return {
            "stats": {
                "users": UserRepository.count(),
                "mediumHighRisk": AlertRepository.count(),
                "pendingReports": pending,
                "announcements": AnnouncementRepository.list(1, 1)["total"],
            },
            "users": [
                {
                    "name": user["nickname"] if user else "暂无用户",
                    "type": " + ".join(
                        disease_labels.get(item, item) for item in (user or {}).get("chronic_types", [])
                    ) or "暂无",
                    "risk": "中风险",
                }
            ] if user else [],
        }


store = DemoStore()
