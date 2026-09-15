"""话术库 + 群发编排。

POC 不直连企微群发接口：生成每人一条合规话术，写入客户动态，并返回可复制文本。
个人话术优先：script_item(customer_id) → customer.profile.talk.icebreak → 选中的公共模板。
"""
import datetime as dt
import logging

from sqlalchemy.orm import Session

from app.core.errors import BizError
from app.models import Customer, CustomerEvent, ScriptItem
from app.schemas import MassSendRequest, ScriptCreateRequest
from app.services import compliance

logger = logging.getLogger(__name__)

CAT_LABEL = {"season": "季节问候", "sales": "销售转化", "care": "客户关怀", "personal": "个人话术"}


def _render(body: str, customer: Customer) -> str:
    persona = customer.persona or ""
    return (
        (body or "")
        .replace("{name}", customer.name or "您")
        .replace("{persona}", persona)
    )


def _personal_body(db: Session, customer: Customer) -> str | None:
    row = (
        db.query(ScriptItem)
        .filter(ScriptItem.customer_id == customer.id)
        .order_by(ScriptItem.created_at.desc())
        .first()
    )
    if row and row.body:
        return row.body
    profile = customer.profile if isinstance(customer.profile, dict) else {}
    talk = profile.get("talk") or {}
    ice = talk.get("icebreak")
    if isinstance(ice, dict):
        ice = ice.get("plain") or ice.get("raw")
    if ice:
        return str(ice)
    return None


def list_scripts(db: Session, manager_id: str, category: str | None = None) -> list[dict]:
    q = db.query(ScriptItem).filter(ScriptItem.manager_id == manager_id)
    if category:
        q = q.filter(ScriptItem.category == category)
    rows = q.order_by(ScriptItem.category, ScriptItem.id.desc()).all()
    names = {}
    cids = [r.customer_id for r in rows if r.customer_id]
    if cids:
        for c in db.query(Customer).filter(Customer.id.in_(cids)).all():
            names[c.id] = c.name
    return [r.to_dict(customer_name=names.get(r.customer_id)) for r in rows]


def create_script(db: Session, manager_id: str, req: ScriptCreateRequest) -> dict:
    title = (req.title or "").strip()
    body = (req.body or "").strip()
    if not title or not body:
        raise BizError("请填写标题和话术正文", code=400)
    cat = req.category or "sales"
    if cat not in CAT_LABEL:
        raise BizError("分类不对", code=400)
    cid = req.customer_id
    if cid:
        c = db.get(Customer, cid)
        if not c:
            raise BizError("关联客户不存在", code=404)
        cat = "personal"
    now = dt.datetime.now()
    row = ScriptItem(
        manager_id=manager_id,
        title=title[:64],
        category=cat,
        body=body,
        customer_id=cid,
        source=req.source or "manual",
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row.to_dict()


def delete_script(db: Session, script_id: int, manager_id: str) -> dict:
    row = db.get(ScriptItem, script_id)
    if not row or row.manager_id != manager_id:
        raise BizError("话术不存在", code=404)
    db.delete(row)
    db.commit()
    return {"id": script_id}


def mass_send(db: Session, manager_id: str, req: MassSendRequest) -> dict:
    ids = list(dict.fromkeys(req.customer_ids or []))
    if not ids:
        raise BizError("请至少选择一位客户", code=400)
    if req.mode == "library" and not req.script_id:
        raise BizError("请选择一条话术", code=400)

    tmpl: ScriptItem | None = None
    if req.script_id:
        tmpl = db.get(ScriptItem, req.script_id)
        if not tmpl:
            raise BizError("话术不存在", code=404)

    customers = db.query(Customer).filter(Customer.id.in_(ids)).all()
    found = {c.id: c for c in customers}
    missing = [i for i in ids if i not in found]
    if missing:
        raise BizError(f"客户不存在: {missing[0]}", code=404)

    now = dt.datetime.now()
    items = []
    for cid in ids:
        c = found[cid]
        used_personal = False
        raw = None
        if req.mode == "personal":
            raw = _personal_body(db, c)
            used_personal = bool(raw)
        if not raw:
            if not tmpl:
                raise BizError(f"{c.name}没有个人话术，请改选公共话术作兜底", code=400)
            raw = tmpl.body
        text = _render(raw, c)
        text, _, hits = compliance.scrub_script(db, text)
        ev = CustomerEvent(
            customer_id=c.id,
            type="contact",
            title=f"群发：{(tmpl.title if tmpl else '个人话术')}",
            payload={
                "channel": "mass_send",
                "text": text,
                "mode": req.mode,
                "usedPersonal": used_personal,
                "complianceHits": hits,
            },
            source="system",
            event_time=now,
            created_at=now,
        )
        db.add(ev)
        items.append({
            "customerId": c.id,
            "name": c.name,
            "text": text,
            "usedPersonal": used_personal,
            "complianceHits": hits,
        })
    db.commit()
    logger.info("[mass-send] manager=%s count=%s mode=%s", manager_id, len(items), req.mode)
    copy_all = "\n\n————\n\n".join(f"【{x['name']}】\n{x['text']}" for x in items)
    return {
        "count": len(items),
        "mode": req.mode,
        "items": items,
        "copyAll": copy_all,
        "disclaimer": "POC 未对接企微群发接口，已写入客户动态；请复制后在企微/微信发送",
    }
