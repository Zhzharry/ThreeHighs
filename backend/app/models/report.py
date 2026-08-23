from app.extensions import db
from app.models.types import BIGINT


class MedicalReport(db.Model):
    __tablename__ = "medical_reports"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.Enum("image", "pdf"), nullable=False)
    file_url = db.Column(db.String(255))
    source = db.Column(db.String(30), nullable=False, default="manual", server_default="manual")
    report_date = db.Column(db.Date, nullable=False)
    ocr_doc_id = db.Column(db.String(64))
    status = db.Column(
        db.Enum("uploaded", "recognizing", "extracting", "recognized", "review_pending", "completed", "rejected", "failed", "archived"),
        default="uploaded",
    )
    confidence = db.Column(db.Numeric(5, 2))
    progress = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    summary = db.Column(db.Text)
    review_note = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, nullable=False)
    reviewed_by = db.Column(BIGINT, db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.DateTime)


class ReportIndicator(db.Model):
    __tablename__ = "report_indicators"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    report_id = db.Column(BIGINT, db.ForeignKey("medical_reports.id"), nullable=False)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    indicator_name = db.Column(db.String(100), nullable=False)
    indicator_code = db.Column(db.String(50))
    value = db.Column(db.String(50), nullable=False)
    unit = db.Column(db.String(30))
    reference_range = db.Column(db.String(100))
    result_status = db.Column(db.Enum("normal", "high", "low", "abnormal"), nullable=False)
    risk_level = db.Column(db.Enum("low", "medium", "high"), default="low")
    created_at = db.Column(db.DateTime, nullable=False)
