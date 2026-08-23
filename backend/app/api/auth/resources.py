from hashlib import sha256
from secrets import compare_digest

from flask import current_app, g, request
from flask_restful import Resource
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import check_password_hash

from app.api.common.responses import fail, json_body, success
from app.repositories import UserRepository
from app.extensions import limiter
from app.services.wechat_auth import WechatAuthError, exchange_login_code


class WechatLoginResource(Resource):
    @limiter.limit(lambda: current_app.config["WECHAT_LOGIN_RATE_LIMIT"])
    def post(self):
        payload = json_body()
        request_id = getattr(g, "request_id", "unknown")
        client_ip_hash = sha256(
            f"{current_app.config['SECRET_KEY']}:{request.remote_addr or 'unknown'}".encode("utf-8")
        ).hexdigest()
        try:
            identity = exchange_login_code(payload.get("code"))
            user_row = UserRepository.login_wechat_user(
                identity["openid"],
                unionid=identity.get("unionid"),
                nickname=payload.get("nickname"),
                avatar_url=payload.get("avatar_url"),
            )
        except WechatAuthError as error:
            UserRepository.record_login_event(None, False, error.code, request_id, client_ip_hash)
            response_code = 40011 if error.status == 400 else 40105 if error.status == 401 else 50302
            return fail(str(error), response_code, error.status)

        if int(user_row.status or 0) != 1:
            UserRepository.record_login_event(user_row.id, False, "ACCOUNT_DISABLED", request_id, client_ip_hash)
            return fail("账号已停用，请联系管理员", 40302, 403)

        UserRepository.record_login_event(user_row.id, True, None, request_id, client_ip_hash)
        user = UserRepository.user_summary(user_row.id)

        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="wechat-login")
        token = serializer.dumps({
            "user_id": user["id"],
            "role": user["role"],
            "token_version": user["token_version"],
        })
        return success({
            "token": token,
            "user": UserRepository.user_summary(user["id"], masked_phone=True),
        })


class LogoutResource(Resource):
    def post(self):
        identity = getattr(g, "identity", None) or {}
        if identity.get("role") == "user" and identity.get("user_id"):
            UserRepository.revoke_tokens(int(identity["user_id"]))
        return success(True)


class AdminLoginResource(Resource):
    @limiter.limit(lambda: current_app.config["ADMIN_LOGIN_RATE_LIMIT"])
    def post(self):
        payload = json_body()
        username = str(payload.get("username", ""))
        password = str(payload.get("password", ""))
        username_matches = compare_digest(username, str(current_app.config["ADMIN_USERNAME"]))
        password_hash = str(current_app.config.get("ADMIN_PASSWORD_HASH", ""))
        password_matches = (
            check_password_hash(password_hash, password)
            if password_hash
            else compare_digest(password, str(current_app.config["ADMIN_PASSWORD"]))
        )
        if not (username_matches and password_matches):
            return fail("管理员账号或密码错误", 40104, 401)

        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="wechat-login")
        token = serializer.dumps({"user_id": 0, "role": "admin", "username": username})
        return success({
            "token": token,
            "user": {"username": username, "role": "admin", "display_name": "系统管理员"},
        }, "管理员登录成功")
