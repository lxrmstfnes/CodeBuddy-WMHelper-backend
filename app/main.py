"""智能理财经理赋能助手 · 后端 POC 入口（FastAPI）

- 接口契约见 BACKEND_SPEC §5（REST API）与 §4（AI 能力契约）
- 统一响应 {code, message, data}；AI 接口永远 200（LLM 失败自动规则兜底）
- 交互式接口文档：http://localhost:8080/docs
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from app.core.errors import BizError
from app.core.response import error, ok
from app.routers import ai, compliance, customer, data, intake, scripts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="智能理财经理赋能助手 · 后端 POC",
    version="0.1.0",
    description="BACKEND_SPEC §5 数据接口 + §4 AI 代理网关。统一响应 {code, message, data}。",
)

# POC 阶段全放开；小程序开发工具直连 http://localhost:8080 即可（需勾选"不校验合法域名"）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(compliance.router)
app.include_router(ai.router)
app.include_router(customer.router)
app.include_router(intake.router)
app.include_router(scripts.router)


@app.get("/api/health")
def health():
    return ok({"status": "up"})


@app.exception_handler(BizError)
async def biz_error_handler(_: Request, exc: BizError):
    return error(exc.code, exc.message)


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException):
    return error(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    return error(422, f"请求参数校验失败: {exc.errors()[0].get('msg') if exc.errors() else 'unknown'}")


@app.exception_handler(Exception)
async def unknown_error_handler(_: Request, exc: Exception):
    logger.exception("未捕获异常")
    # 统一包装为 200 + code 500，前端从 code 判断（对齐 §5 响应包装约定）
    return error(500, f"服务内部错误: {exc}")
