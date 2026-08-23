import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app


class WechatAuthError(Exception):
    def __init__(self, message, code="WECHAT_AUTH_FAILED", status=401):
        super().__init__(message)
        self.code = code
        self.status = status


def exchange_login_code(code):
    code = str(code or "").strip()
    if not code or len(code) > 128:
        raise WechatAuthError("微信登录凭证无效", "INVALID_LOGIN_CODE", 400)

    mode = current_app.config["WECHAT_LOGIN_MODE"]
    if mode == "mock":
        return {
            "openid": current_app.config["WECHAT_MOCK_OPENID"],
            "unionid": None,
        }
    if mode != "code2session":
        raise WechatAuthError("微信登录模式配置错误", "INVALID_LOGIN_MODE", 503)

    query = urlencode({
        "appid": current_app.config["WECHAT_APP_ID"],
        "secret": current_app.config["WECHAT_APP_SECRET"],
        "js_code": code,
        "grant_type": "authorization_code",
    })
    request = Request(
        f"{current_app.config['WECHAT_CODE2SESSION_URL']}?{query}",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=current_app.config["WECHAT_API_TIMEOUT_SECONDS"]) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise WechatAuthError("微信登录服务暂时不可用", "WECHAT_UPSTREAM_UNAVAILABLE", 503) from error

    if payload.get("errcode"):
        errcode = int(payload["errcode"])
        if errcode in {40029, 40163}:
            raise WechatAuthError("微信登录凭证已失效，请重试", f"WECHAT_{errcode}", 401)
        raise WechatAuthError("微信登录校验失败", f"WECHAT_{errcode}", 502)
    if not payload.get("openid"):
        raise WechatAuthError("微信登录响应缺少用户标识", "WECHAT_OPENID_MISSING", 502)

    return {
        "openid": str(payload["openid"])[:64],
        "unionid": str(payload.get("unionid") or "")[:64] or None,
    }
