"""CRM 跟进记录提取（前端 pages/assistant 在用，BACKEND_SPEC 未列出，按 ai.js 契约补齐）"""
import logging

from app.services import llm, normalize, prompts

logger = logging.getLogger(__name__)


def extract(text: str) -> dict:
    try:
        data = llm.chat_json(
            prompts.CRM_SYSTEM_PROMPT,
            prompts.crm_user_prompt(text),
            temperature=0.2, max_tokens=800,
        )
        return normalize.normalize_crm_record(data)
    except llm.LLMError as e:
        logger.warning("[crm] LLM 失败，回退空记录 + 原文截断摘要: %s", e)
        # 兜底：无法可靠抽取时不编造，返回全空记录，摘要截断原文 30 字，前端可正常渲染
        record = normalize.normalize_crm_record({})
        record["summary"] = (text or "")[:30] or None
        return record
