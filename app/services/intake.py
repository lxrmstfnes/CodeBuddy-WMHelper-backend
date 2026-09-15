"""扫码建档：经理出示一次性码 → 客户自助填写 → 主档 + 画像快照落库。

合规约定：客户自述不写入正式 risk_level（保持未评级），画像进 profile JSON，
并生成「待正式风险测评」待办。数字（AUM 档位映射）由系统换算，LLM 只产出画像语言。
"""
import datetime as dt
import io
import logging
import re
import secrets

from sqlalchemy.orm import Session

from app.core.errors import BizError
from app.models import Customer, CustomerEvent, FollowTask, IntakeToken
from app.schemas import DiagnoseRequest, IntakeSubmitRequest
from app.services import diagnose

logger = logging.getLogger(__name__)

TOKEN_TTL = dt.timedelta(hours=2)
QR_PATH = "pages/intake/intake?token="
AUM_MAP = {
    "10万以下": 50_000,
    "10-50万": 300_000,
    "50-100万": 800_000,
    "100万以上": 1_500_000,
}
PHONE_RE = re.compile(r"^1\d{10}$")


def _payload(token: str) -> str:
    return QR_PATH + token


def create_ticket(db: Session, manager_id: str) -> dict:
    """作废该经理未使用的旧码，签发一张新的 2 小时有效采集码。"""
    now = dt.datetime.now()
    db.query(IntakeToken).filter(
        IntakeToken.manager_id == manager_id,
        IntakeToken.status == "pending",
    ).update({"status": "cancelled"}, synchronize_session=False)

    token = secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16]
    row = IntakeToken(
        token=token,
        manager_id=manager_id,
        status="pending",
        expire_at=now + TOKEN_TTL,
        created_at=now,
    )
    db.add(row)
    db.commit()
    return {
        "token": token,
        "expireAt": row.expire_at.strftime("%Y-%m-%d %H:%M"),
        "path": "/" + _payload(token),
        "qrUrl": f"/api/intake/tickets/{token}/qr",
        "ttlHours": 2,
    }


def _get_live_token(db: Session, token: str) -> IntakeToken:
    row = db.get(IntakeToken, token)
    if not row:
        raise BizError("采集码无效，请让理财经理重新出示", code=404)
    now = dt.datetime.now()
    if row.status == "used":
        raise BizError("该采集码已使用", code=409)
    if row.status != "pending" or row.expire_at <= now:
        if row.status == "pending":
            row.status = "expired"
            db.commit()
        raise BizError("采集码已过期，请让理财经理重新出示", code=410)
    return row


def get_ticket(db: Session, token: str) -> dict:
    """采集页 onLoad 校验。已使用时仍返回 used，便于展示「已提交」。"""
    row = db.get(IntakeToken, token)
    if not row:
        raise BizError("采集码无效，请让理财经理重新出示", code=404)
    now = dt.datetime.now()
    expired = row.status == "pending" and row.expire_at <= now
    if expired:
        row.status = "expired"
        db.commit()
    status = "expired" if expired else (row.status or "pending")
    return {
        "token": token,
        "status": status,
        "managerId": row.manager_id,
        "expireAt": row.expire_at.strftime("%Y-%m-%d %H:%M") if row.expire_at else None,
        "customerId": row.customer_id,
    }


def qr_png(db: Session, token: str) -> bytes:
    row = db.get(IntakeToken, token)
    if not row:
        raise BizError("采集码无效", code=404)
    try:
        import qrcode
    except ImportError as e:
        raise BizError("服务未安装二维码组件", code=500) from e
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
    qr.add_data(_payload(token))
    qr.make(fit=True)
    img = qr.make_image(fill_color="#00A85A", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _new_id(db: Session) -> str:
    for _ in range(12):
        cid = "n" + secrets.token_hex(4)
        if not db.get(Customer, cid):
            return cid
    raise BizError("无法分配客户编号", code=500)


def _compact_profile(diag: dict, form: IntakeSubmitRequest, diagnosed_at: str) -> dict:
    matched = []
    for p in (diag.get("matched") or [])[:3]:
        matched.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "matchScore": p.get("matchScore"),
            "riskLevel": p.get("riskLevel"),
        })
    out = {
        "score": diag.get("score"),
        "persona": diag.get("persona"),
        "radar": diag.get("radar") or [],
        "radarLabels": diag.get("radarLabels") or [],
        "config": diag.get("config") or {},
        "matched": matched,
        "form": {
            "age": form.age,
            "amount": form.amount,
            "source": form.source,
            "preferences": form.preferences or [],
        },
        "diagnosedAt": diagnosed_at,
        "officialRisk": None,
        "disclaimer": "客户自述，非正式风险测评，正式等级以网点双录测评为准",
    }
    talk = diag.get("talk") or {}
    ice = talk.get("icebreak")
    if isinstance(ice, dict):
        ice = ice.get("plain") or ice.get("raw")
    if ice:
        out["talk"] = {"icebreak": ice}
    return out


def submit(db: Session, token: str, req: IntakeSubmitRequest) -> dict:
    row = _get_live_token(db, token)
    name = (req.name or "").strip()
    phone = re.sub(r"\s+", "", req.phone or "")
    if len(name) < 2:
        raise BizError("请填写真实姓名", code=400)
    if not PHONE_RE.match(phone):
        raise BizError("请填写 11 位手机号", code=400)
    if not (req.age and req.amount and req.source and req.preferences):
        raise BizError("请完整选择年龄、资金体量、来源和偏好", code=400)

    dup = db.query(Customer).filter(Customer.phone == phone).first()
    if dup:
        raise BizError("该手机号已在客户库中，请联系理财经理", code=409)

    now = dt.datetime.now()
    diag = diagnose.diagnose(db, DiagnoseRequest(
        age=req.age, amount=req.amount, source=req.source, preferences=req.preferences,
    ))
    profile = _compact_profile(diag, req, now.strftime("%Y-%m-%d %H:%M"))
    cid = _new_id(db)
    tags = list(req.preferences or []) + ["扫码获客", "待正式测评"]
    customer = Customer(
        id=cid,
        manager_id=row.manager_id,
        name=name,
        phone=phone,
        age=req.age,
        risk_level=None,
        aum=AUM_MAP.get(req.amount, 0),
        tags=tags,
        persona=diag.get("persona") or "待评估客户",
        holdings=[],
        touch_pref="客户自助填写，触达偏好待经理确认",
        source="intake",
        profile=profile,
        created_at=now,
        updated_at=now,
    )
    db.add(customer)
    db.flush()

    ev = CustomerEvent(
        customer_id=cid,
        type="intake",
        title=f"扫码自助建档：{diag.get('persona') or '已提交基本信息'}",
        payload={
            "channel": "qr",
            "amount": req.amount,
            "source": req.source,
            "disclaimer": profile["disclaimer"],
        },
        source="system",
        event_time=now,
        created_at=now,
    )
    db.add(ev)
    db.flush()

    task = FollowTask(
        customer_id=cid,
        title=f"回访{name}：核对信息并完成正式风险测评",
        due_time=now + dt.timedelta(days=1),
        status="pending",
        source="system",
        related_event_id=ev.id,
        ai_suggestion="先确认联系方式与资金来源，再约网点做适当性测评；客户自述偏好不可当作正式风险等级。",
        created_at=now,
        updated_at=now,
    )
    db.add(task)

    row.status = "used"
    row.customer_id = cid
    row.used_at = now
    db.commit()

    logger.info("[intake] manager=%s customer=%s name=%s", row.manager_id, cid, name)
    return {
        "customerId": cid,
        "name": name,
        "persona": customer.persona,
        "disclaimer": profile["disclaimer"],
    }
