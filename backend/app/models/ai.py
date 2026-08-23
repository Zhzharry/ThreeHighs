from app.extensions import db
from app.models.types import BIGINT


class AiConversation(db.Model):
    __tablename__ = "ai_conversations"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(100))
    source = db.Column(db.String(30), nullable=False, default="manual", server_default="manual")
    related_date = db.Column(db.Date)
    summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)


class AiMessage(db.Model):
    __tablename__ = "ai_messages"

    id = db.Column(BIGINT, primary_key=True, autoincrement=True)
    conversation_id = db.Column(BIGINT, db.ForeignKey("ai_conversations.id"), nullable=False)
    user_id = db.Column(BIGINT, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.Enum("user", "assistant", "system"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    mongo_trace_id = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, nullable=False)
