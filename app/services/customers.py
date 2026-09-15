"""客户域服务（设计稿§2.1）：列表徽标 / 详情组装 / 动态录入 / 待办闭环。

列表页的 pendingTasks / nearMaturity / maturityDays 在这里计算：
到期天数解析自持仓 JSON 的 dueDate 字段（holdings 内嵌方案，已评审确认）。
"""
import datetime as dt

from sqlalchemy.orm import Session

from app.core.errors import BizError
from app.models import Customer, CustomerEvent, FollowTask, ScriptItem
from app.schemas import EventCreateRequest

MATURITY_WINDOW_DAYS = 7  # 列表页"临近到期"徽标的窗口


def _parse_dt(s: str | None) -> dt.datetime:
    """"YYYY-MM-DD[ HH:mm[:SS]]" → datetime，缺省当前时间"""
    if not s:
        return dt.datetime.now()
    s = s.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise BizError("时间格式不对，请用 YYYY-MM-DD HH:mm", code=400)


def _days_to_due(holdings: list) -> int | None:
    """持仓中最近一个到期日距今天数（可为负=已过期），无持仓返回 None"""
    today = dt.date.today()
    best: int | None = None
    for h in holdings or []:
        due = (h or {}).get("dueDate")
        if not due:
            continue
        try:
            d = dt.date.fromisoformat(str(due)[:10])
        except ValueError:
            continue
        delta = (d - today).days
        best = delta if best is None else min(best, delta)
    return best


def _get_customer_or_404(db: Session, customer_id: str) -> Customer:
    c = db.get(Customer, customer_id)
    if not c:
        raise BizError(f"客户不存在: {customer_id}", code=404)
    return c


def list_customers(db: Session) -> list[dict]:
    """客户列表：每条带待办数 + 临近到期徽标"""
    customers = db.query(Customer).order_by(Customer.created_at.desc(), Customer.id).all()
    pending = (
        db.query(FollowTask.customer_id)
        .filter(FollowTask.status == "pending")
        .all()
    )
    pending_count: dict[str, int] = {}
    for (cid,) in pending:
        pending_count[cid] = pending_count.get(cid, 0) + 1

    personal_ids = {
        sid for (sid,) in db.query(ScriptItem.customer_id).filter(ScriptItem.customer_id.isnot(None)).all()
    }

    result = []
    for c in customers:
        d = c.to_dict()
        days = _days_to_due(c.holdings)
        talk = (c.profile or {}).get("talk") if isinstance(c.profile, dict) else {}
        ice = (talk or {}).get("icebreak") if talk else None
        d["pendingTasks"] = pending_count.get(c.id, 0)
        d["maturityDays"] = days
        d["nearMaturity"] = days is not None and 0 <= days <= MATURITY_WINDOW_DAYS
        d["hasPersonalScript"] = c.id in personal_ids or bool(ice)
        result.append(d)
    return result


def get_detail(db: Session, customer_id: str) -> dict:
    """客户详情：主档 + 动态时间线(倒序20条) + 待办(pending优先,按到期时间)"""
    c = _get_customer_or_404(db, customer_id)
    events = (
        db.query(CustomerEvent)
        .filter(CustomerEvent.customer_id == customer_id)
        .order_by(CustomerEvent.event_time.desc())
        .limit(20)
        .all()
    )
    tasks = (
        db.query(FollowTask)
        .filter(FollowTask.customer_id == customer_id)
        .order_by(
            (FollowTask.status == "pending").desc(),
            FollowTask.due_time.is_(None),
            FollowTask.due_time,
        )
        .all()
    )
    d = c.to_dict(include_profile=True)
    d["events"] = [e.to_dict() for e in events]
    d["tasks"] = [t.to_dict() for t in tasks]
    d["maturityDays"] = _days_to_due(c.holdings)
    return d


def add_event(db: Session, customer_id: str, req: EventCreateRequest) -> dict:
    """手工录入动态（赎回/买入/大额变动等）"""
    _get_customer_or_404(db, customer_id)
    ev = CustomerEvent(
        customer_id=customer_id,
        type=req.type,
        title=req.title,
        payload=req.payload or {},
        source="manual",
        event_time=_parse_dt(req.event_time),
        created_at=dt.datetime.now(),
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev.to_dict()


def list_tasks(db: Session, customer_id: str) -> list[dict]:
    _get_customer_or_404(db, customer_id)
    tasks = (
        db.query(FollowTask)
        .filter(FollowTask.customer_id == customer_id)
        .order_by(
            (FollowTask.status == "pending").desc(),
            FollowTask.due_time.is_(None),
            FollowTask.due_time,
        )
        .all()
    )
    return [t.to_dict() for t in tasks]


def done_task(db: Session, task_id: int, done_note: str | None) -> dict:
    """完成待办（闭环）"""
    t = db.get(FollowTask, task_id)
    if not t:
        raise BizError(f"待办不存在: {task_id}", code=404)
    t.status = "done"
    t.done_note = done_note
    t.updated_at = dt.datetime.now()
    db.commit()
    db.refresh(t)
    return t.to_dict()
