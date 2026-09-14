"""请求 DTO：AI 接口输入契约（BACKEND_SPEC §4），camelCase 入参自动映射 snake_case。"""
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ChatMessage(CamelModel):
    """对话历史条目：role 仅 customer / manager 两种（§4.1）"""
    role: Literal["customer", "manager"]
    text: str


# ---------- §4.1 对练评分 ----------
class GradeRequest(CamelModel):
    script_id: str
    round_idx: int
    answer: str
    history: list[ChatMessage] = []


class OpeningRequest(CamelModel):
    script_id: str


# ---------- §4.2 整场总结 ----------
class GradeItem(CamelModel):
    score: int
    level: str


class SummaryRequest(CamelModel):
    script_id: str
    history: list[ChatMessage] = []
    grades: list[GradeItem] = []


# ---------- §4.3 客户诊断 ----------
class DiagnoseRequest(CamelModel):
    age: str
    amount: str
    source: str
    preferences: list[str] = []


# ---------- §4.4 合规检查 ----------
class ComplianceCheckRequest(BaseModel):
    text: str = ""


# ---------- CRM 跟进记录提取（前端 pages/assistant 在用，spec 未列出） ----------
class CrmExtractRequest(BaseModel):
    text: str
