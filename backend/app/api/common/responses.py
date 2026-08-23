from flask import request


def success(data=None, message="success"):
    return {
        "code": 0,
        "message": message,
        "data": {} if data is None else data,
    }


def fail(message="参数错误", code=40001, status=400):
    return {
        "code": code,
        "message": message,
        "data": None,
    }, status


def json_body():
    return request.get_json(silent=True) or {}


def pagination_args(default_page_size=20):
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", default_page_size, type=int)
    return max(page, 1), max(min(page_size, 100), 1)

