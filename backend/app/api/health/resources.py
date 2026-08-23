from flask_restful import Resource
from sqlalchemy import text

from app.api.common.responses import fail, success
from app.extensions import db, limiter


class HealthResource(Resource):
    @limiter.exempt
    def get(self):
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            db.session.rollback()
            return fail("数据库暂不可用", 50301, 503)
        return success({
            "service": "three-high-health-api",
            "status": "ready",
        })
