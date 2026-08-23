from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.extensions import db
from app.models import Announcement, FoodItem, User


def _now():
    return datetime.now().replace(microsecond=0)


def _number(value):
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return value


class FoodRepository:
    @staticmethod
    def serialize(row):
        return {
            "id": row.id,
            "name": row.name,
            "category": row.category or "",
            "unit": row.unit or "100g",
            "calories": _number(row.calories_per_100g),
            "sugar": _number(row.sugar_per_100g),
            "fat": _number(row.fat_per_100g),
            "salt": _number(row.salt_per_100g),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @classmethod
    def list(cls, page, page_size, keyword=None):
        query = FoodItem.query
        if keyword:
            query = query.filter(FoodItem.name.contains(keyword))
        total = query.count()
        rows = query.order_by(FoodItem.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": [cls.serialize(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    @classmethod
    def create(cls, payload):
        now = _now()
        row = FoodItem(
            name=payload["name"],
            category=payload.get("category", ""),
            unit=payload.get("unit", "100g"),
            calories_per_100g=payload.get("calories", 0),
            sugar_per_100g=payload.get("sugar", 0),
            fat_per_100g=payload.get("fat", 0),
            salt_per_100g=payload.get("salt", 0),
            created_at=now,
            updated_at=now,
        )
        db.session.add(row)
        db.session.commit()
        return cls.serialize(row)

    @classmethod
    def update(cls, food_id, payload):
        row = db.session.get(FoodItem, food_id)
        if row is None:
            return None
        mappings = {
            "name": "name",
            "category": "category",
            "unit": "unit",
            "calories": "calories_per_100g",
            "sugar": "sugar_per_100g",
            "fat": "fat_per_100g",
            "salt": "salt_per_100g",
        }
        for source, target in mappings.items():
            if source in payload:
                setattr(row, target, payload[source])
        row.updated_at = _now()
        db.session.commit()
        return cls.serialize(row)

    @staticmethod
    def delete(food_id):
        row = db.session.get(FoodItem, food_id)
        if row is None:
            return False
        db.session.delete(row)
        db.session.commit()
        return True

    @classmethod
    def batch_delete(cls, food_ids):
        existing = {
            row.id for row in FoodItem.query.filter(FoodItem.id.in_(food_ids)).all()
        }
        if existing:
            FoodItem.query.filter(FoodItem.id.in_(existing)).delete(synchronize_session=False)
            db.session.commit()
        processed_ids = [food_id for food_id in food_ids if food_id in existing]
        return {
            "requested_count": len(food_ids),
            "processed_count": len(processed_ids),
            "processed_ids": processed_ids,
            "missing_ids": [food_id for food_id in food_ids if food_id not in existing],
        }


class AnnouncementRepository:
    @staticmethod
    def serialize(row):
        return {
            "id": row.id,
            "title": row.title,
            "content": row.content,
            "is_published": row.publish_status == "published",
            "publish_status": row.publish_status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @classmethod
    def list(cls, page, page_size):
        query = Announcement.query
        total = query.count()
        rows = query.order_by(Announcement.created_at.desc(), Announcement.id.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        return {
            "items": [cls.serialize(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    @classmethod
    def create(cls, payload, created_by=1):
        now = _now()
        row = Announcement(
            title=payload["title"],
            content=payload["content"],
            publish_status="published" if payload.get("is_published") else "draft",
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        db.session.add(row)
        db.session.commit()
        return cls.serialize(row)

    @classmethod
    def update(cls, announcement_id, payload):
        row = db.session.get(Announcement, announcement_id)
        if row is None:
            return None
        if "title" in payload:
            row.title = payload["title"]
        if "content" in payload:
            row.content = payload["content"]
        if "is_published" in payload:
            row.publish_status = "published" if payload["is_published"] else "draft"
        row.updated_at = _now()
        db.session.commit()
        return cls.serialize(row)

    @staticmethod
    def delete(announcement_id):
        row = db.session.get(Announcement, announcement_id)
        if row is None:
            return False
        db.session.delete(row)
        db.session.commit()
        return True

    @classmethod
    def batch_publish(cls, announcement_ids, is_published):
        rows = Announcement.query.filter(Announcement.id.in_(announcement_ids)).all()
        existing = {row.id for row in rows}
        now = _now()
        for row in rows:
            row.publish_status = "published" if is_published else "draft"
            row.updated_at = now
        if rows:
            db.session.commit()
        processed_ids = [item_id for item_id in announcement_ids if item_id in existing]
        return {
            "requested_count": len(announcement_ids),
            "processed_count": len(processed_ids),
            "processed_ids": processed_ids,
            "missing_ids": [item_id for item_id in announcement_ids if item_id not in existing],
        }


def bootstrap_reference_data(store):
    """Import first-version JSON data once when the domain tables are empty."""
    changed = False
    user = db.session.get(User, int(store.user["id"]))
    if user is None:
        user = User(
            id=int(store.user["id"]),
            openid=store.user.get("openid"),
            username=store.user.get("nickname") or store.user.get("username") or "演示用户",
            avatar_url=store.user.get("avatar_url", ""),
            phone=store.user.get("phone", ""),
            role=store.user.get("role", "user"),
            status=store.user.get("status", 1),
            created_at=_now(),
            updated_at=_now(),
        )
        db.session.add(user)
        db.session.flush()
        changed = True

    if FoodItem.query.count() == 0:
        for source in store.food_items.values():
            db.session.add(FoodItem(
                id=source.get("id"),
                name=source["name"],
                category=source.get("category", ""),
                unit=source.get("unit", "100g"),
                calories_per_100g=source.get("calories", 0),
                sugar_per_100g=source.get("sugar", 0),
                fat_per_100g=source.get("fat", 0),
                salt_per_100g=source.get("salt", 0),
                created_at=_now(),
                updated_at=_now(),
            ))
        changed = True

    if Announcement.query.count() == 0:
        for source in store.announcements.values():
            db.session.add(Announcement(
                id=source.get("id"),
                title=source["title"],
                content=source["content"],
                publish_status=source.get("publish_status") or (
                    "published" if source.get("is_published") else "draft"
                ),
                created_by=user.id,
                created_at=_now(),
                updated_at=_now(),
            ))
        changed = True

    if changed:
        db.session.commit()
    return changed
