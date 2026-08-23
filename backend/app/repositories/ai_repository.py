from __future__ import annotations

from datetime import date, datetime

from app.extensions import db
from app.models import AiConversation, AiMessage


def _now(): return datetime.now().replace(microsecond=0)
def _date(value): return value if isinstance(value,date) else datetime.strptime(str(value),"%Y-%m-%d").date()
def _datetime(value):
    if isinstance(value,datetime):return value.replace(tzinfo=None)
    return datetime.fromisoformat(str(value)).replace(tzinfo=None) if value else None


class AiRepository:
    @staticmethod
    def get(conversation_id,user_id=1):
        return AiConversation.query.filter_by(id=conversation_id,user_id=user_id).one_or_none()

    @classmethod
    def create(cls,title,source=None,related_date=None,user_id=1):
        now=_now();row=AiConversation(user_id=user_id,title=title or "健康问答",source=source or "manual",related_date=_date(related_date) if related_date else None,summary="",created_at=now,updated_at=now)
        db.session.add(row);db.session.commit();return {"conversation_id":row.id,"title":row.title,"created_at":row.created_at.isoformat()}

    @classmethod
    def list(cls,page,page_size,user_id=1):
        q=AiConversation.query.filter_by(user_id=user_id);total=q.count();rows=q.order_by(AiConversation.updated_at.desc()).offset((page-1)*page_size).limit(page_size).all();items=[]
        for row in rows:
            last=AiMessage.query.filter_by(conversation_id=row.id,user_id=user_id).order_by(AiMessage.created_at.desc(),AiMessage.id.desc()).first()
            items.append({"id":row.id,"title":row.title,"last_message":last.content if last else "","related_date":row.related_date.isoformat() if row.related_date else None,"updated_at":row.updated_at.isoformat()})
        return {"items":items,"page":page,"page_size":page_size,"total":total}

    @classmethod
    def messages(cls,conversation_id,user_id=1):
        if cls.get(conversation_id,user_id) is None:return None
        rows=AiMessage.query.filter_by(conversation_id=conversation_id,user_id=user_id).order_by(AiMessage.created_at,AiMessage.id).all()
        return [{"id":r.id,"role":r.role,"content":r.content,"created_at":r.created_at.isoformat()} for r in rows]

    @classmethod
    def add_message(cls,conversation_id,role,content,user_id=1):
        conversation=cls.get(conversation_id,user_id)
        if conversation is None:return None
        row=AiMessage(conversation_id=conversation_id,user_id=user_id,role=role,content=content,created_at=_now())
        db.session.add(row);conversation.updated_at=row.created_at;db.session.commit()
        return {"id":row.id,"role":row.role,"content":row.content,"created_at":row.created_at.isoformat()}

    @classmethod
    def delete(cls,conversation_id,user_id=1):
        row=cls.get(conversation_id,user_id)
        if row is None:return False
        AiMessage.query.filter_by(conversation_id=row.id,user_id=user_id).delete();db.session.delete(row);db.session.commit();return True


def bootstrap_ai_data(store):
    for s in store.conversations.values():db.session.merge(AiConversation(id=s["id"],user_id=s.get("user_id",1),title=s.get("title"),source=s.get("source","manual"),related_date=_date(s["related_date"]) if s.get("related_date") else None,summary=s.get("summary",""),created_at=_datetime(s.get("created_at")) or _now(),updated_at=_datetime(s.get("updated_at")) or _now()))
    db.session.flush()
    for conversation_id,items in store.messages_by_conversation_id.items():
        for s in items:db.session.merge(AiMessage(id=s["id"],conversation_id=int(conversation_id),user_id=s.get("user_id",1),role=s["role"],content=s["content"],created_at=_datetime(s.get("created_at")) or _now()))
    db.session.commit()
