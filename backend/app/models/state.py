from app.extensions import db


class AppState(db.Model):
    """Compatibility marker for upgrading first-version JSON deployments.

    All business data is domain-owned. After import, this row contains only
    repository migration markers and is not written after API mutations.
    """

    __tablename__ = "app_state"

    key = db.Column(db.String(64), primary_key=True)
    payload = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)
