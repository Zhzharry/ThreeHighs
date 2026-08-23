from pathlib import Path
from uuid import uuid4

from flask import current_app, request
from flask_restful import Resource
from werkzeug.utils import secure_filename

from app.api.common.responses import fail, pagination_args, success
from app.api.common.identity import current_user_id
from app.services.demo_store import today_str, store


class ReportUploadResource(Resource):
    def post(self):
        upload = request.files.get("file")
        if not upload:
            return fail("请上传图片或 PDF 文件")

        raw_name = upload.filename or "report.pdf"
        suffix = Path(raw_name).suffix.lower()
        allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
        if suffix not in allowed_suffixes:
            return fail("仅支持 JPG、PNG、WEBP 或 PDF 文件")

        safe_original_name = secure_filename(raw_name)
        filename = f"{uuid4().hex}{suffix}"
        file_type = "pdf" if suffix == ".pdf" else "image"
        upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        save_path = upload_dir / filename
        upload.save(save_path)

        return success(store.upload_report(
            file_name=safe_original_name or f"report{suffix}",
            file_type=file_type,
            source=request.form.get("source", file_type),
            report_date=request.form.get("report_date", today_str()),
            file_url=str(save_path),
            user_id=current_user_id(),
        ))


class ReportRecognizeResource(Resource):
    def post(self, report_id):
        data = store.start_recognition(report_id, current_user_id())
        if data is None:
            return fail("报告不存在", 40401, 404)
        return success(data)


class ReportProgressResource(Resource):
    def get(self, report_id):
        data = store.report_progress(report_id, current_user_id())
        if data is None:
            return fail("报告不存在", 40401, 404)
        return success(data)


class ReportDetailResource(Resource):
    def get(self, report_id):
        data = store.report_detail(report_id, current_user_id())
        if data is None:
            return fail("报告不存在", 40401, 404)
        return success(data)

    def patch(self, report_id):
        payload = request.get_json(silent=True) or {}
        if payload.get("action") != "confirm":
            return fail("仅支持 action=confirm")
        data = store.confirm_report(report_id, str(payload.get("review_note", ""))[:500], current_user_id())
        if data is None:
            return fail("报告不存在", 40401, 404)
        if data is False:
            return fail("报告尚无可确认的指标")
        return success(data, "报告已确认")

    def delete(self, report_id):
        data = store.delete_report(report_id, current_user_id())
        if data is None:
            return fail("报告不存在", 40401, 404)
        file_url = data.get("file_url")
        if file_url:
            upload_dir = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
            file_path = Path(file_url).resolve()
            if file_path.is_relative_to(upload_dir) and file_path.is_file():
                file_path.unlink()
        return success(True, "报告已删除")


class ReportIndicatorsResource(Resource):
    def get(self, report_id):
        user_id = current_user_id()
        if store.report_detail(report_id, user_id) is None:
            return fail("报告不存在", 40401, 404)
        return success(store.report_indicators(report_id, user_id))

    def put(self, report_id):
        payload = request.get_json(silent=True) or {}
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            return fail("指标列表不能为空")
        allowed_statuses = {"normal", "high", "low", "abnormal"}
        normalized = []
        for index, item in enumerate(items, start=1):
            name = str(item.get("indicator_name", "")).strip()
            value = str(item.get("value", "")).strip()
            status = item.get("status", item.get("result_status", "normal"))
            if not name or not value:
                return fail(f"第 {index} 项指标名称和值不能为空")
            if status not in allowed_statuses:
                return fail(f"第 {index} 项指标状态无效")
            normalized.append({
                "indicator_name": name[:100],
                "indicator_code": str(item.get("indicator_code", ""))[:50] or None,
                "value": value[:50],
                "unit": str(item.get("unit", ""))[:30] or None,
                "reference_range": str(item.get("reference_range", ""))[:100] or None,
                "status": status,
                "result_status": status,
                "risk_level": item.get("risk_level", "low") if item.get("risk_level") in {"low", "medium", "high"} else "low",
            })
        data = store.update_report_indicators(report_id, normalized, current_user_id())
        if data is None:
            return fail("报告不存在", 40401, 404)
        return success(data, "指标已保存")


class ReportHistoryResource(Resource):
    def get(self):
        page, page_size = pagination_args(default_page_size=10)
        return success(store.report_history(page, page_size, current_user_id()))
