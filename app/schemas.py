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
class CrmExtractRequest(CamelModel):
    text: str
    customer_id: str | None = None  # 传入则抽取结果落客户档案并自动生成待办（设计稿§3.1）


# ---------- 客户域（客户数据库与AI跟踪设计稿 §2.1） ----------
class EventCreateRequest(CamelModel):
    """手工录入客户动态"""
    type: str
    title: str
    payload: dict = {}
    event_time: str | None = None  # "YYYY-MM-DD HH:mm"，缺省为当前时间


class MotDoneRequest(CamelModel):
    """MoT 处理提交：跟进结论必填，后续动作默认 none"""
    result: Literal["purchased", "intent", "informed", "follow", "no_intent", "missed"]
    next_action: Literal["crm", "none"] = "none"


class MotScriptRequest(CamelModel):
    """MoT 一键生成微信话术"""
    event_id: int


class TaskDoneRequest(CamelModel):
    done_note: str | None = None


class IntakeSubmitRequest(CamelModel):
    """客户自助采集提交（扫码建档）"""
    name: str
    phone: str
    age: str
    amount: str
    source: str
    preferences: list[str] = []


class ScriptCreateRequest(CamelModel):
    title: str
    body: str
    category: str = "sales"
    customer_id: str | None = None
    source: str | None = None


class MassSendRequest(CamelModel):
    customer_ids: list[str]
    mode: Literal["library", "personal"] = "library"
    script_id: int | None = None
