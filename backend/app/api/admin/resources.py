import re

from flask import request
from flask_restful import Resource

from app.api.common.responses import fail, json_body, pagination_args, success
from app.services.demo_store import store


def validate_food(payload):
    name = str(payload.get("name", "")).strip()
    if not name:
        return None, fail("食物名称不能为空")
    normalized = {
        "name": name[:100],
        "category": str(payload.get("category", "")).strip()[:50],
        "unit": str(payload.get("unit", "100g")).strip()[:30] or "100g",
    }
    for field in ("calories", "sugar", "fat", "salt"):
        try:
            value = float(payload.get(field, 0))
        except (TypeError, ValueError):
            return None, fail(f"{field} 必须是数字")
        if value < 0:
            return None, fail(f"{field} 不能小于0")
        normalized[field] = value
    return normalized, None


def validate_announcement(payload):
    title = str(payload.get("title", "")).strip()
    content = str(payload.get("content", "")).strip()
    if not title or not content:
        return None, fail("公告标题和内容不能为空")
    published = payload.get("is_published", False)
    if not isinstance(published, bool):
        return None, fail("is_published 必须是布尔值")
    return {"title": title[:150], "content": content[:5000], "is_published": published}, None


def validate_admin_user(payload):
    normalized = {}
    if "status" in payload:
        status = payload.get("status")
        if isinstance(status, bool) or status not in {0, 1}:
            return None, fail("账号状态只能为正常或停用")
        normalized["status"] = status

    if "nickname" in payload:
        nickname = str(payload.get("nickname", "")).strip()
        if not 1 <= len(nickname) <= 30:
            return None, fail("昵称长度必须为1到30个字符")
        normalized["nickname"] = nickname

    if "phone" in payload:
        phone = str(payload.get("phone", "")).strip()
        if phone and not re.fullmatch(r"1[3-9]\d{9}", phone):
            return None, fail("手机号格式不正确")
        normalized["phone"] = phone

    numeric_ranges = {"age": (1, 120, int), "height_cm": (80, 240, float), "weight_kg": (20, 300, float)}
    for field, (minimum, maximum, converter) in numeric_ranges.items():
        if field not in payload:
            continue
        try:
            value = converter(payload[field])
        except (TypeError, ValueError):
            return None, fail(f"{field} 必须是数字")
        if not minimum <= value <= maximum:
            return None, fail(f"{field} 超出合理范围")
        normalized[field] = value

    if "gender" in payload:
        gender = str(payload.get("gender", "")).strip()
        if gender not in {"", "男", "女", "其他"}:
            return None, fail("性别选项无效")
        normalized["gender"] = gender

    if "chronic_types" in payload:
        chronic_types = payload.get("chronic_types")
        allowed = {"hypertension", "diabetes", "hyperlipidemia"}
        if not isinstance(chronic_types, list) or any(item not in allowed for item in chronic_types):
            return None, fail("慢病类型无效")
        normalized["chronic_types"] = list(dict.fromkeys(chronic_types))

    for field, label in (("medical_history", "病史"), ("medication", "用药情况")):
        if field in payload:
            value = str(payload.get(field, "")).strip()
            if len(value) > 1000:
                return None, fail(f"{label}不能超过1000个字符")
            normalized[field] = value
    return normalized, None


def validate_batch_ids(payload):
    ids = payload.get("ids")
    if not isinstance(ids, list) or not ids:
        return None, fail("请选择至少一条数据")
    if len(ids) > 100:
        return None, fail("单次批量操作不能超过100条")
    normalized = []
    for value in ids:
        if isinstance(value, bool):
            return None, fail("数据ID格式不正确")
        try:
            item_id = int(value)
        except (TypeError, ValueError):
            return None, fail("数据ID格式不正确")
        if item_id <= 0:
            return None, fail("数据ID格式不正确")
        if item_id not in normalized:
            normalized.append(item_id)
    return normalized, None


class AdminDashboardResource(Resource):
    def get(self):
        return success(store.admin_dashboard())


class AdminUsersResource(Resource):
    def get(self):
        page, page_size = pagination_args()
        return success(store.admin_users(page, page_size, request.args.get("keyword")))


class AdminUserResource(Resource):
    def get(self, user_id):
        data = store.admin_user_detail(user_id)
        if data is None:
            return fail("用户不存在", 40401, 404)
        return success(data)

    def put(self, user_id):
        payload, error = validate_admin_user(json_body())
        if error:
            return error
        data = store.update_admin_user(user_id, payload)
        if data is None:
            return fail("用户不存在", 40401, 404)
        return success(data, "用户资料与账号状态已保存")


class AdminReportsResource(Resource):
    def get(self):
        page, page_size = pagination_args()
        return success(store.admin_reports(page, page_size, request.args.get("status")))


class AdminReportReviewResource(Resource):
    def patch(self, report_id):
        payload = json_body()
        if payload.get("status") not in {"completed", "rejected", "review_pending"}:
            return fail("审核状态无效")
        payload["review_note"] = str(payload.get("review_note", ""))[:500]
        data = store.review_report(report_id, payload)
        if data is None:
            return fail("报告不存在", 40401, 404)
        return success(data, "报告审核已保存")


class AdminReportsBatchReviewResource(Resource):
    def patch(self):
        payload = json_body()
        ids, error = validate_batch_ids(payload)
        if error:
            return error
        if payload.get("status") not in {"completed", "rejected", "review_pending"}:
            return fail("审核状态无效")
        review_note = str(payload.get("review_note", ""))[:500]
        return success(store.batch_review_reports(ids, payload["status"], review_note), "报告批量审核已保存")


class AdminFoodsResource(Resource):
    def get(self):
        page, page_size = pagination_args()
        return success(store.list_foods(page, page_size, request.args.get("keyword")))

    def post(self):
        payload, error = validate_food(json_body())
        if error:
            return error
        return success(store.create_food(payload), "食物已新增")


class AdminFoodResource(Resource):
    def put(self, food_id):
        payload, error = validate_food(json_body())
        if error:
            return error
        data = store.update_food(food_id, payload)
        if data is None:
            return fail("食物不存在", 40401, 404)
        return success(data, "食物已更新")

    def delete(self, food_id):
        if not store.delete_food(food_id):
            return fail("食物不存在", 40401, 404)
        return success(True, "食物已删除")


class AdminFoodsBatchDeleteResource(Resource):
    def post(self):
        ids, error = validate_batch_ids(json_body())
        if error:
            return error
        return success(store.batch_delete_foods(ids), "食物批量删除已完成")


class AdminAnnouncementsResource(Resource):
    def get(self):
        page, page_size = pagination_args()
        return success(store.list_announcements(page, page_size))

    def post(self):
        payload, error = validate_announcement(json_body())
        if error:
            return error
        return success(store.create_announcement(payload), "公告已新增")


class AdminAnnouncementResource(Resource):
    def put(self, announcement_id):
        payload, error = validate_announcement(json_body())
        if error:
            return error
        data = store.update_announcement(announcement_id, payload)
        if data is None:
            return fail("公告不存在", 40401, 404)
        return success(data, "公告已更新")

    def delete(self, announcement_id):
        if not store.delete_announcement(announcement_id):
            return fail("公告不存在", 40401, 404)
        return success(True, "公告已删除")


class AdminAnnouncementsBatchPublishResource(Resource):
    def patch(self):
        payload = json_body()
        ids, error = validate_batch_ids(payload)
        if error:
            return error
        if not isinstance(payload.get("is_published"), bool):
            return fail("is_published 必须是布尔值")
        return success(store.batch_publish_announcements(ids, payload["is_published"]), "公告发布状态已批量更新")
