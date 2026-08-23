from flask import request
from flask_restful import Resource

from app.api.common.responses import fail, json_body, success
from app.api.common.identity import current_user_id
from app.services.demo_store import parse_date, today_str, store


class DailyTodayResource(Resource):
    def get(self):
        return success(store.daily_payload(today_str(), create=True, user_id=current_user_id()))


class DailyRecordsResource(Resource):
    def get(self):
        record_date = request.args.get("date")
        if not record_date:
            return fail("缺少 date 参数")
        data = store.daily_payload(record_date, create=record_date == today_str(), user_id=current_user_id())
        if data is None:
            return fail("该日期暂无记录", 40401, 404)
        return success(data)

    def post(self):
        payload = json_body()
        record_date = payload.get("date")
        if not record_date:
            return fail("缺少 date 参数")
        try:
            target_date = parse_date(record_date)
        except (TypeError, ValueError):
            return fail("date 格式必须为 YYYY-MM-DD")
        if target_date > parse_date(today_str()):
            return fail("不能创建未来日期的健康记录")
        user_id = current_user_id()
        if store.daily_payload(record_date, create=False, user_id=user_id) is not None:
            return fail("该日期记录已存在", 40901, 409)
        return success(store.daily_payload(record_date, create=True, user_id=user_id), "记录已创建"), 201


class DailyCalendarResource(Resource):
    def get(self):
        month = request.args.get("month")
        if not month:
            return fail("缺少 month 参数")
        return success(store.calendar_marks(month, current_user_id()))


class DailyRecordResource(Resource):
    def patch(self, record_id):
        payload = json_body()
        if "note" in payload and len(str(payload["note"])) > 500:
            return fail("每日备注不能超过 500 个字符")
        if "summary" in payload and len(str(payload["summary"])) > 1000:
            return fail("健康小结不能超过 1000 个字符")
        if "mood" in payload and payload["mood"] not in {"平稳", "愉快", "疲惫", "焦虑", "不适", ""}:
            return fail("mood 参数无效")
        data = store.update_daily_record(record_id, payload, current_user_id())
        if data is None:
            return fail("每日记录不存在", 40401, 404)
        return success(data)


class DailyVitalsResource(Resource):
    def patch(self, record_id):
        payload = json_body()
        ranges = {
            "systolic_pressure": (60, 260), "diastolic_pressure": (30, 160),
            "fasting_glucose": (1, 40), "postprandial_glucose": (1, 40),
            "weight_kg": (20, 300),
        }
        for field, (minimum, maximum) in ranges.items():
            if field not in payload:
                continue
            try:
                value = float(payload[field])
            except (TypeError, ValueError):
                return fail(f"{field} 必须是数字")
            if not minimum <= value <= maximum:
                return fail(f"{field} 超出合理范围 {minimum}-{maximum}")
        data = store.update_vitals(record_id, payload, current_user_id())
        if data is None:
            return fail("每日记录不存在", 40401, 404)
        return success(data)


class DailyTasksResource(Resource):
    def get(self, record_id):
        if not store.get_record_by_id(record_id, current_user_id()):
            return fail("每日记录不存在", 40401, 404)
        return success(store.serialize_tasks(record_id, current_user_id()))


class DailyTaskResource(Resource):
    def patch(self, task_id):
        payload = json_body()
        if "is_done" not in payload:
            return fail("缺少 is_done 参数")
        data = store.update_task(task_id, payload["is_done"], current_user_id())
        if data is None:
            return fail("待办不存在", 40401, 404)
        return success(data)


class DailyTaskTemplateCurrentResource(Resource):
    def get(self):
        record_date = request.args.get("date", today_str())
        return success(store.get_current_template(record_date, current_user_id()))

    def put(self):
        payload = json_body()
        effective_date = payload.get("effective_date", today_str())
        items = payload.get("items", [])
        return success(store.update_template(effective_date, items, current_user_id()))


class DailyTasksGenerateResource(Resource):
    def post(self, record_id):
        payload = json_body()
        data = store.generate_tasks_for_record(record_id, payload.get("date"), current_user_id())
        if data is None:
            return fail("每日记录不存在", 40401, 404)
        return success(data)


class DailyMealsResource(Resource):
    def get(self, record_id):
        user_id = current_user_id()
        if not store.get_record_by_id(record_id, user_id):
            return fail("每日记录不存在", 40401, 404)
        return success(store.get_meals(record_id, user_id))

    def post(self, record_id):
        payload = json_body()
        if payload.get("meal_type") not in {"breakfast", "lunch", "dinner", "extra"}:
            return fail("meal_type 参数无效")
        foods = payload.get("foods")
        if not isinstance(foods, list) or not foods or not all(str(item.get("name", "")).strip() for item in foods):
            return fail("请至少填写一种食物")
        data = store.add_meal(record_id, payload, current_user_id())
        if data is None:
            return fail("每日记录不存在", 40401, 404)
        return success({
            "id": data["id"],
            "meal_type": data["meal_type"],
            "meal_name": data["meal_name"],
        })


class MealResource(Resource):
    def put(self, meal_id):
        payload = json_body()
        if "meal_type" in payload and payload["meal_type"] not in {"breakfast", "lunch", "dinner", "extra"}:
            return fail("meal_type 参数无效")
        if "foods" in payload:
            foods = payload["foods"]
            if not isinstance(foods, list) or not foods or not all(str(item.get("name", "")).strip() for item in foods):
                return fail("请至少填写一种食物")
        data = store.update_meal(meal_id, payload, current_user_id())
        if data is None:
            return fail("饮食记录不存在", 40401, 404)
        return success(data)

    def delete(self, meal_id):
        deleted = store.delete_meal(meal_id, current_user_id())
        if not deleted:
            return fail("饮食记录不存在", 40401, 404)
        return success(True)


class VitalsTrendResource(Resource):
    def get(self):
        range_value = request.args.get("range", "7d")
        return success(store.trends(range_value, current_user_id()))


class VitalsPredictionResource(Resource):
    def get(self):
        days = request.args.get("days", 7, type=int)
        return success(store.predictions(max(min(days, 30), 1)))


class AlertsResource(Resource):
    def get(self):
        return success(store.list_alerts(request.args.get("date"), current_user_id()))


class AlertReadResource(Resource):
    def patch(self, alert_id):
        if not store.mark_alert_read(alert_id, current_user_id()):
            return fail("提醒不存在", 40401, 404)
        return success(True)
