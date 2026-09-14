"""ORM 模型：与 sql/01-schema.sql 的 9 张表一一对应（BACKEND_SPEC §3 / §6.4）。

每个模型的 to_dict() 输出前端 mock.js 的原始字段结构（camelCase），
保证前端展示层零改动切换（§4 导语）。
"""
from datetime import date

from sqlalchemy import JSON, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Product(Base):
    """§3.1 理财产品"""
    __tablename__ = "product"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    company: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(64))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    nature: Mapped[str | None] = mapped_column(String(16))
    sale_type: Mapped[str | None] = mapped_column(String(16))
    risk_level: Mapped[str | None] = mapped_column(String(4))
    min_amount: Mapped[int | None] = mapped_column(Integer)
    term: Mapped[str | None] = mapped_column(String(16))
    benchmark_yield: Mapped[str | None] = mapped_column(String(8))
    trend: Mapped[list] = mapped_column(JSON, default=list)
    asset_type: Mapped[str | None] = mapped_column(String(128))
    selling_point: Mapped[str | None] = mapped_column(String(255))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company": self.company,
            "name": self.name,
            "tags": self.tags or [],
            "nature": self.nature,
            "saleType": self.sale_type,
            "riskLevel": self.risk_level,
            "minAmount": self.min_amount,
            "term": self.term,
            "benchmarkYield": self.benchmark_yield,
            "trend": self.trend or [],
            "assetType": self.asset_type,
            "sellingPoint": self.selling_point,
        }


class Company(Base):
    """§3.2 理财子公司"""
    __tablename__ = "company"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(32))
    short: Mapped[str | None] = mapped_column(String(16))
    slogan: Mapped[str | None] = mapped_column(String(64))
    color: Mapped[str | None] = mapped_column(String(8))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "short": self.short,
            "slogan": self.slogan,
            "color": self.color,
        }


class ClientPersona(Base):
    """§3.3 客群画像"""
    __tablename__ = "client_persona"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    label: Mapped[str] = mapped_column(String(64))
    assets: Mapped[str | None] = mapped_column(String(16))
    age: Mapped[str | None] = mapped_column(String(16))
    pain_point: Mapped[str | None] = mapped_column(String(255))
    golden_line: Mapped[str | None] = mapped_column(String(128))
    quick_prefs: Mapped[list] = mapped_column(JSON, default=list)
    ai_match: Mapped[list] = mapped_column(JSON, default=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "assets": self.assets,
            "age": self.age,
            "painPoint": self.pain_point,
            "goldenLine": self.golden_line,
            "quickPrefs": self.quick_prefs or [],
            "aiMatch": self.ai_match or [],
        }


class MarketReport(Base):
    """§3.4 市场快报主表"""
    __tablename__ = "market_report"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date)
    golden_sentence: Mapped[str | None] = mapped_column(String(255))


class MarketReportCard(Base):
    """§3.4 快报卡片（前端卡片 id 即 card_no）"""
    __tablename__ = "market_report_card"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date)
    card_no: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(64))
    highlight: Mapped[str | None] = mapped_column(String(32))
    arrow: Mapped[str | None] = mapped_column(String(8))
    sub_text: Mapped[str | None] = mapped_column(String(64))
    color: Mapped[str | None] = mapped_column(String(8))
    show_progress: Mapped[int] = mapped_column(Integer, default=0)
    progress_value: Mapped[int | None] = mapped_column(Integer)
    pulse_dot: Mapped[int] = mapped_column(Integer, default=0)
    sort_no: Mapped[int] = mapped_column(Integer, default=0)

    def to_dict(self) -> dict:
        d = {
            "id": self.card_no,
            "title": self.title,
            "highlight": self.highlight,
            "subText": self.sub_text,
            "color": self.color,
            "showProgress": bool(self.show_progress),
        }
        if self.arrow:
            d["arrow"] = self.arrow
        if self.show_progress:
            d["progressValue"] = self.progress_value
        if self.pulse_dot:
            d["pulseDot"] = True
        return d


class RolePlayScript(Base):
    """§3.5 对练剧本主表"""
    __tablename__ = "role_play_script"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(64))
    difficulty: Mapped[str | None] = mapped_column(String(8))
    persona: Mapped[str | None] = mapped_column(String(255))
    opening: Mapped[str | None] = mapped_column(Text)

    def to_dict(self, rounds: list["ScriptRound"] | None = None) -> dict:
        d = {
            "id": self.id,
            "title": self.title,
            "difficulty": self.difficulty,
            "persona": self.persona,
            "opening": self.opening,
        }
        if rounds is not None:
            d["rounds"] = [r.to_dict() for r in rounds]
        return d


class ScriptRound(Base):
    """§3.5 剧本轮次子表（round_no 与前端 roundIdx 对齐，从 0 开始）"""
    __tablename__ = "script_round"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    script_id: Mapped[str] = mapped_column(String(16))
    round_no: Mapped[int] = mapped_column(Integer)
    question: Mapped[str | None] = mapped_column(String(255))
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    tips: Mapped[str | None] = mapped_column(String(255))
    best_reply: Mapped[str | None] = mapped_column(Text)

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "keywords": self.keywords or [],
            "tips": self.tips,
            "bestReply": self.best_reply,
        }


class ForbiddenWord(Base):
    """§3.7 合规违禁词"""
    __tablename__ = "forbidden_word"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(32))
    alternative: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[int] = mapped_column(Integer, default=1)

    def to_dict(self) -> dict:
        return {"word": self.word, "alternative": self.alternative}


class MotEvent(Base):
    """§3.6 MoT 商机事件（type: maturity到期 / behavior行为追踪 / alert风险预警）"""
    __tablename__ = "mot_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_date: Mapped[date | None] = mapped_column(Date)
    event_time: Mapped[str | None] = mapped_column(String(8))
    type: Mapped[str | None] = mapped_column(String(16))
    client_name: Mapped[str | None] = mapped_column(String(32))
    client_tag: Mapped[str | None] = mapped_column(String(64))
    event_title: Mapped[str | None] = mapped_column(String(128))
    detail: Mapped[str | None] = mapped_column(String(255))
    ai_strategy: Mapped[str | None] = mapped_column(Text)
    generated_script: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(16))
    customer_no: Mapped[str | None] = mapped_column(String(32))
    assets: Mapped[str | None] = mapped_column(String(32))
    risk: Mapped[str | None] = mapped_column(String(32))
    traits: Mapped[str | None] = mapped_column(String(255))
    touch: Mapped[str | None] = mapped_column(String(255))

    def to_dict(self) -> dict:
        # 注意：前端字段是 time（不是 eventTime），见 §3.6
        return {
            "id": self.id,
            "date": self.event_date.isoformat() if self.event_date else None,
            "time": self.event_time,
            "type": self.type,
            "clientName": self.client_name,
            "clientTag": self.client_tag,
            "eventTitle": self.event_title,
            "detail": self.detail,
            "aiStrategy": self.ai_strategy,
            "generatedScript": self.generated_script,
            "phone": self.phone,
            "customerNo": self.customer_no,
            "assets": self.assets,
            "risk": self.risk,
            "traits": self.traits,
            "touch": self.touch,
        }
