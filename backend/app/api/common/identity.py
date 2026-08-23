from flask import g


def current_user_id():
    """Return the verified token user, with user 1 as local demo fallback."""
    identity = getattr(g, "identity", None) or {}
    return int(identity.get("user_id", 1))
