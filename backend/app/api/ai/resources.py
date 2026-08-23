from flask import request
from flask_restful import Resource

from app.api.common.responses import fail, json_body, pagination_args, success
from app.api.common.identity import current_user_id
from app.services.demo_store import today_str, store


class AiQuickQuestionsResource(Resource):
    def get(self):
        return success(store.quick_questions())


class AiContextTodayResource(Resource):
    def get(self):
        record_date = request.args.get("date", today_str())
        return success(store.ai_context_today(record_date, current_user_id()))


class AiConversationsResource(Resource):
    def get(self):
        page, page_size = pagination_args()
        return success(store.list_conversations(page, page_size, current_user_id()))

    def post(self):
        payload = json_body()
        return success(store.create_conversation(
            payload.get("title", "健康问答"),
            payload.get("source"),
            payload.get("related_date"),
            current_user_id(),
        ))


class AiConversationMessagesResource(Resource):
    def get(self, conversation_id):
        data = store.list_messages(conversation_id, current_user_id())
        if data is None:
            return fail("会话不存在", 40401, 404)
        return success(data)

    def post(self, conversation_id):
        payload = json_body()
        content = payload.get("content")
        if not content:
            return fail("缺少 content 参数")
        data = store.send_message(
            conversation_id=conversation_id,
            content=content,
            use_daily_context=payload.get("use_daily_context", True),
            related_date=payload.get("related_date"),
            user_id=current_user_id(),
        )
        if data is None:
            return fail("会话不存在", 40401, 404)
        return success(data)


class AiConversationResource(Resource):
    def delete(self, conversation_id):
        if not store.delete_conversation(conversation_id, current_user_id()):
            return fail("会话不存在", 40401, 404)
        return success(True)
