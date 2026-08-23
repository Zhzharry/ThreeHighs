import re
from pathlib import Path
from uuid import uuid4

from flask import current_app, request, send_from_directory
from flask_restful import Resource

from app.api.common.responses import fail, json_body, success
from app.api.common.identity import current_user_id
from app.repositories import UserRepository
from app.services.demo_store import store
from app.services.data_export import export_user_data


class MeProfileResource(Resource):
    def get(self):
        return success(store.get_profile(current_user_id()))

    def put(self):
        payload = json_body()
        nickname = str(payload.get("nickname", "")).strip()
        if "nickname" in payload and not 1 <= len(nickname) <= 30:
            return fail("昵称长度必须为1到30个字符")
        phone = str(payload.get("phone", "")).strip()
        if "phone" in payload and phone and not re.fullmatch(r"1[3-9]\d{9}", phone):
            return fail("手机号格式不正确")
        if "age" in payload and payload["age"] is not None:
            try:
                age = int(payload["age"])
            except (TypeError, ValueError):
                return fail("年龄必须是整数")
            if not 1 <= age <= 120:
                return fail("年龄超出合理范围")
            payload["age"] = age
        if "nickname" in payload:
            payload["nickname"] = nickname
        if "phone" in payload:
            payload["phone"] = phone
        return success(store.update_profile(payload, current_user_id()), "个人资料已保存")


class MeAvatarResource(Resource):
    def post(self):
        upload = request.files.get("file")
        if not upload:
            return fail("请选择头像图片")
        suffix = Path(upload.filename or "avatar.jpg").suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"} or not (upload.mimetype or "").startswith("image/"):
            return fail("头像仅支持 JPG、PNG 或 WEBP 图片")

        avatar_dir = Path(current_app.config["UPLOAD_FOLDER"]) / "avatars"
        avatar_dir.mkdir(parents=True, exist_ok=True)
        file_path = avatar_dir / f"{uuid4().hex}{suffix}"
        upload.save(file_path)
        if file_path.stat().st_size > 2 * 1024 * 1024:
            file_path.unlink()
            return fail("头像图片不能超过2MB", 41301, 413)

        user_id = current_user_id()
        old_url = (store.get_profile(user_id) or {"user": {}})["user"].get("avatar_url", "")
        old_name = old_url.rsplit("/", 1)[-1] if "/me/avatar/files/" in old_url else ""
        old_path = (avatar_dir / old_name).resolve() if old_name else None
        if old_path and old_path.is_relative_to(avatar_dir.resolve()) and old_path.is_file():
            old_path.unlink()

        avatar_url = f"{request.host_url.rstrip('/')}/api/v1/me/avatar/files/{file_path.name}"
        data = store.update_profile({"avatar_url": avatar_url}, user_id)
        return success({"avatar_url": avatar_url, "user": data}, "头像已更新")

    def delete(self):
        avatar_dir = Path(current_app.config["UPLOAD_FOLDER"]) / "avatars"
        user_id = current_user_id()
        old_url = (store.get_profile(user_id) or {"user": {}})["user"].get("avatar_url", "")
        old_name = old_url.rsplit("/", 1)[-1] if "/me/avatar/files/" in old_url else ""
        old_path = (avatar_dir / old_name).resolve() if old_name else None
        if old_path and old_path.is_relative_to(avatar_dir.resolve()) and old_path.is_file():
            old_path.unlink()
        data = store.update_profile({"avatar_url": ""}, user_id)
        return success({"avatar_url": "", "user": data}, "头像已移除")


class MeAvatarFileResource(Resource):
    def get(self, filename):
        if Path(filename).name != filename:
            return fail("头像文件不存在", 40401, 404)
        avatar_dir = Path(current_app.config["UPLOAD_FOLDER"]) / "avatars"
        return send_from_directory(avatar_dir, filename)


class MeHealthProfileResource(Resource):
    def put(self):
        payload = json_body()
        ranges = {"age": (1, 120), "height_cm": (80, 240), "weight_kg": (20, 300)}
        for field, (minimum, maximum) in ranges.items():
            if field in payload and payload[field] is not None:
                try:
                    value = float(payload[field])
                except (TypeError, ValueError):
                    return {"code": 40001, "message": f"{field} 必须是数字", "data": None}, 400
                if not minimum <= value <= maximum:
                    return {"code": 40001, "message": f"{field} 超出合理范围", "data": None}, 400
        return success(store.update_health_profile(payload, current_user_id()))


class MeSettingsResource(Resource):
    def get(self):
        return success(store.get_settings(current_user_id()))

    def put(self):
        payload = json_body()
        for field in ("alert_push_enabled", "daily_record_reminder_enabled"):
            if field in payload and not isinstance(payload[field], bool):
                return {"code": 40001, "message": f"{field} 必须是布尔值", "data": None}, 400
        reminder_time = payload.get("daily_record_reminder_time")
        if reminder_time is not None and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(reminder_time)):
            return {"code": 40001, "message": "提醒时间格式必须为 HH:mm", "data": None}, 400
        return success(store.update_settings(payload, current_user_id()))


def _consent_versions():
    return {
        "privacy_policy": current_app.config["PRIVACY_POLICY_VERSION"],
        "user_agreement": current_app.config["USER_AGREEMENT_VERSION"],
        "health_data_consent": current_app.config["HEALTH_DATA_CONSENT_VERSION"],
    }


class MeConsentsResource(Resource):
    def get(self):
        return success(UserRepository.get_consents(current_user_id(), _consent_versions()))

    def put(self):
        payload = json_body()
        required = ("privacy_policy_accepted", "user_agreement_accepted", "health_data_consent")
        for field in required:
            if payload.get(field) is not True:
                return fail("请阅读并同意用户协议、隐私政策和健康数据处理授权")
        return success(
            UserRepository.accept_consents(current_user_id(), _consent_versions()),
            "授权记录已保存",
        )


class MeConsentWithdrawalResource(Resource):
    def post(self):
        payload = json_body()
        if payload.get("confirmation") != "撤回授权":
            return fail("请明确确认撤回健康数据授权")
        return success(
            UserRepository.withdraw_health_consent(current_user_id(), _consent_versions()),
            "健康数据授权已撤回",
        )


class MeDataExportResource(Resource):
    def get(self):
        data = export_user_data(current_user_id())
        if data is None:
            return fail("用户不存在", 40401, 404)
        return success(data, "个人数据副本已生成")
