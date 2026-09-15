"""MoT 商机闭环：跟进结论 + 后续动作（对齐大行客户经理工作台）。"""
import datetime as dt

from sqlalchemy.orm import Session

from app.core.errors import BizError
from app.models import MOT_RESULT_LABELS, MotEvent

RESULT_LABELS = MOT_RESULT_LABELS

NEXT_ACTIONS = {"crm", "none"}


def _get_or_404(db: Session, event_id: int) -> MotEvent:
    ev = db.get(MotEvent, event_id)
    if not ev:
        raise BizError(f"商机不存在: {event_id}", code=404)
    return ev


def mark_done(db: Session, event_id: int, result: str, next_action: str | None = None) -> dict:
    if result not in RESULT_LABELS:
        raise BizError("请选择跟进结论（已购买/已意向/已了解等）", code=400)
    action = next_action or "none"
    if action not in NEXT_ACTIONS:
        raise BizError("后续动作不合法", code=400)
    ev = _get_or_404(db, event_id)
    ev.status = "done"
    ev.result = result
    ev.next_action = action
    ev.done_at = dt.datetime.now()
    db.commit()
    db.refresh(ev)
    return ev.to_dict()


def reopen(db: Session, event_id: int) -> dict:
    ev = _get_or_404(db, event_id)
    ev.status = "pending"
    ev.done_at = None
    ev.result = None
    ev.next_action = None
    db.commit()
    db.refresh(ev)
    return ev.to_dict()
