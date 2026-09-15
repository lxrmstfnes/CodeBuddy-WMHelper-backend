"""数据接口（BACKEND_SPEC §5 第一步：纯数据接口，前端 mock → wx.request 直接切换）"""
import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import BizError
from app.core.response import ok
from app.db import get_db
from app.models import (
    ClientPersona, Company, MarketReport, MarketReportCard, MotEvent,
    Product, RolePlayScript, ScriptRound,
)
from app.schemas import MotDoneRequest
from app.services import mot as mot_svc

router = APIRouter(prefix="/api", tags=["数据接口"])


@router.get("/products")
def list_products(company: str | None = Query(default=None), db: Session = Depends(get_db)):
    """产品列表，支持公司筛选（公司 id 如 icbc 或公司名如 工银理财 均可）"""
    q = db.query(Product)
    if company:
        comp = db.get(Company, company)
        q = q.filter(Product.company == (comp.name if comp else company))
    return ok([p.to_dict() for p in q.order_by(Product.id).all()])


@router.get("/products/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise BizError(f"产品不存在: {product_id}", code=404)
    return ok(p.to_dict())


# 公司展示顺序与前端 mock.js 对齐（首页公司筛选胶囊的顺序）：工银/杭银/兴银/渝农商
COMPANY_ORDER = ["icbc", "hangyin", "xingyin", "nongshang"]


@router.get("/companies")
def list_companies(db: Session = Depends(get_db)):
    rows = {c.id: c for c in db.query(Company).all()}
    ordered = [rows.pop(cid) for cid in COMPANY_ORDER if cid in rows]
    ordered += rows.values()  # 未来新增公司排在最后
    return ok([c.to_dict() for c in ordered])


@router.get("/market-report")
def market_report(db: Session = Depends(get_db)):
    """快报卡片 + AI 金句：取最新一期"""
    report = db.query(MarketReport).order_by(MarketReport.report_date.desc()).first()
    if not report:
        raise BizError("暂无市场快报", code=404)
    cards = (
        db.query(MarketReportCard)
        .filter(MarketReportCard.report_date == report.report_date)
        .order_by(MarketReportCard.sort_no, MarketReportCard.card_no)
        .all()
    )
    return ok({
        "date": report.report_date.isoformat(),
        "cards": [c.to_dict() for c in cards],
        "goldenSentence": report.golden_sentence,
    })


@router.get("/personas")
def list_personas(db: Session = Depends(get_db)):
    return ok([p.to_dict() for p in db.query(ClientPersona).order_by(ClientPersona.id).all()])


@router.get("/scripts")
def list_scripts(db: Session = Depends(get_db)):
    """对练剧本列表（含 rounds 子表，§3.5）"""
    scripts = db.query(RolePlayScript).order_by(RolePlayScript.id).all()
    rounds = db.query(ScriptRound).order_by(ScriptRound.round_no).all()
    by_script: dict[str, list[ScriptRound]] = {}
    for r in rounds:
        by_script.setdefault(r.script_id, []).append(r)
    return ok([s.to_dict(rounds=by_script.get(s.id, [])) for s in scripts])


@router.get("/mot/events")
def mot_events(day: dt.date | None = Query(default=None, alias="date"), db: Session = Depends(get_db)):
    """MoT 商机事件（§3.6），date 缺省为当天。含 pending / done，前端自行拆分。"""
    d = day or dt.date.today()
    events = (
        db.query(MotEvent)
        .filter(MotEvent.event_date == d)
        .order_by(MotEvent.event_time)
        .all()
    )
    return ok([e.to_dict() for e in events])


@router.post("/mot/events/{event_id}/done")
def done_mot_event(event_id: int, req: MotDoneRequest, db: Session = Depends(get_db)):
    """提交跟进结论（已购买/已意向/已了解等），今日商机移入已完成"""
    return ok(mot_svc.mark_done(db, event_id, req.result, req.next_action))


@router.post("/mot/events/{event_id}/reopen")
def reopen_mot_event(event_id: int, db: Session = Depends(get_db)):
    """从已完成撤销回待办"""
    return ok(mot_svc.reopen(db, event_id))
