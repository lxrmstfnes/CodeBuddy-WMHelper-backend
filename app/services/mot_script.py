"""MoT 一键生成微信话术：LLM 现场写稿，合规清洗，失败回落种子稿。"""
import logging
import re

from sqlalchemy.orm import Session

from app.core.errors import BizError
from app.models import Customer, MotEvent, Product
from app.services import compliance, llm, prompts

logger = logging.getLogger(__name__)


def generate(db: Session, event_id: int) -> dict:
    ev = db.get(MotEvent, event_id)
    if not ev:
        raise BizError(f"商机不存在: {event_id}", code=404)

    products = [p.to_dict() for p in db.query(Product).order_by(Product.id).all()]
    customer_row = None
    if ev.client_name:
        customer_row = db.query(Customer).filter(Customer.name == ev.client_name).first()
        if customer_row is None:
            # 「李大姐」对「李姐」：同姓且客户名被称呼包含
            surname = ev.client_name[0]
            candidates = db.query(Customer).filter(Customer.name.like(f"{surname}%")).all()
            customer_row = next(
                (c for c in candidates if c.name and (c.name in ev.client_name or ev.client_name.startswith(c.name))),
                None,
            )
    customer = customer_row.to_dict() if customer_row else None

    source = "fallback"
    raw = (ev.generated_script or "").strip()
    try:
        data = llm.chat_json(
            prompts.MOT_SCRIPT_SYSTEM_PROMPT,
            prompts.mot_script_user_prompt(ev, products, customer),
            temperature=0.6,
            max_tokens=500,
        )
        script = re.sub(r"\s+", " ", str(data.get("script") or "").strip())
        if 40 <= len(script) <= 400:
            raw = script
            source = "ai"
        else:
            logger.warning("[mot-script] 模型输出长度异常，回落种子稿 event=%s len=%s", event_id, len(script))
    except llm.LLMError as e:
        logger.warning("[mot-script] LLM 失败，回落种子稿 event=%s: %s", event_id, e)

    if not raw:
        raw = "您好，关于您这边的情况我想跟您同步一下，方便的话回我一句，我再把细节给您讲清楚。"

    cleaned, passed, hits = compliance.scrub_script(db, raw)
    if hits:
        logger.info("[mot-script] 合规替换 event=%s hits=%s", event_id, hits)

    if source == "ai":
        ev.generated_script = cleaned
        db.commit()

    return {
        "script": cleaned,
        "source": source,
        "compliancePass": passed,
        "complianceNote": "🛡️ 合规词库已校验" if passed else "🛡️ 已替换违禁表述",
    }
