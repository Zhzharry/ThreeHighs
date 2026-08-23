from app.extensions import db
from app.models.types import BIGINT


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    publish_status = db.Column(db.Enum("draft", "published", "offline"), default="draft")
    created_by = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)
