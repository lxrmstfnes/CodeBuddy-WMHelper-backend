"""AI 客户诊断编排（§4.3）：LLM 优先，normalize 校验不过 / 调用失败 → 规则引擎兜底。"""
import logging

from sqlalchemy.orm import Session

from app.core.errors import BizError
from app.models import Product
from app.schemas import DiagnoseRequest
from app.services import llm, normalize, prompts, rules

logger = logging.getLogger(__name__)


def diagnose(db: Session, form: DiagnoseRequest) -> dict:
    products = [p.to_dict() for p in db.query(Product).order_by(Product.id).all()]
    if not products:
        raise BizError("产品库为空", code=500)

    try:
        data = llm.chat_json(
            prompts.DIAGNOSE_SYSTEM_PROMPT,
            prompts.diagnose_user_prompt(form, products),
            temperature=0.7, max_tokens=2500,
        )
        # matched 的 id 必须来自真实产品库、talk 结构必须完整，否则抛 LLMError 走兜底（ai.js 同款铁律）
        return normalize.normalize_diagnosis(data, form, products)
    except llm.LLMError as e:
        logger.warning("[diagnose] LLM 失败，回退规则引擎: %s", e)
        return rules.diagnose_client(form, products)
