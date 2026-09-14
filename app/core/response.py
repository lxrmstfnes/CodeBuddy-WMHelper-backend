"""统一响应包装：{ "code": 0, "message": "ok", "data": {...} }（BACKEND_SPEC §5）"""
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def ok(data: Any = None) -> JSONResponse:
    return JSONResponse({"code": 0, "message": "ok", "data": jsonable_encoder(data)})


def error(code: int, message: str, http_status: int = 200) -> JSONResponse:
    """业务错误也以 HTTP 200 + 非零 code 返回，前端统一从 code 判断（AI 接口永远 200，见 §4.5）"""
    return JSONResponse({"code": code, "message": message, "data": None}, status_code=http_status)
