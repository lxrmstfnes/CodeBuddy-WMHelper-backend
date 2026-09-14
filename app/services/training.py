"""对练 AI 编排（§4.1 / §4.2）：LLM 优先，LLMError → 规则引擎兜底，接口永远 200（§4.5）。"""
import logging

from sqlalchemy.orm import Session

from app.core.errors import BizError
from app.models import RolePlayScript, ScriptRound
from app.schemas import GradeRequest, SummaryRequest
from app.services import llm, normalize, prompts, rules

logger = logging.getLogger(__name__)


def _load_script(db: Session, script_id: str) -> tuple[RolePlayScript, list[ScriptRound]]:
    script = db.get(RolePlayScript, script_id)
    if not script:
        raise BizError(f"剧本不存在: {script_id}", code=404)
    rounds = (
        db.query(ScriptRound)
        .filter(ScriptRound.script_id == script_id)
        .order_by(ScriptRound.round_no)
        .all()
    )
    return script, rounds


def grade(db: Session, req: GradeRequest) -> dict:
    """§4.1 对练评分 + 客户下一句话：{score, level, comment, nextQuestion}"""
    script, rounds = _load_script(db, req.script_id)
    if req.round_idx < 0 or req.round_idx >= len(rounds):
        raise BizError(f"轮次不存在: roundIdx={req.round_idx}")

    round_ = rounds[req.round_idx]
    next_round = rounds[req.round_idx + 1] if req.round_idx + 1 < len(rounds) else None

    try:
        data = llm.chat_json(
            prompts.GRADE_SYSTEM_PROMPT,
            prompts.grade_user_prompt(
                script.to_dict(), round_.to_dict(),
                next_round.to_dict() if next_round else None,
                req.round_idx, len(rounds), req.answer, prompts.history_text(req.history),
            ),
            temperature=0.7, max_tokens=1000,
        )
        return normalize.normalize_grade(data)
    except llm.LLMError as e:
        logger.warning("[grade] LLM 失败，回退规则引擎: %s", e)
        result = rules.grade_answer(round_.keywords or [], req.answer)
        if result is None:
            # 空回答：与前端 training.js 的敷衍回应处理对齐
            return {
                "score": 0, "level": "待提升",
                "comment": "检测到无效或过于敷衍的回应，本轮计 0 分。实战对练请认真组织话术：先接住客户情绪，再回应客户的问题，最后给出明确的下一步动作。",
                "nextQuestion": None,
            }
        return result


def summary(db: Session, req: SummaryRequest) -> dict:
    """§4.2 整场总结建议：{advice}"""
    script, _ = _load_script(db, req.script_id)
    try:
        data = llm.chat_json(
            prompts.SUMMARY_SYSTEM_PROMPT,
            prompts.summary_user_prompt(script.to_dict(), prompts.history_text(req.history), req.grades),
            temperature=0.5, max_tokens=600,
        )
        return normalize.normalize_summary(data)
    except llm.LLMError as e:
        logger.warning("[summary] LLM 失败，回退规则引擎: %s", e)
        return rules.summary_fallback(req.grades)


def opening(db: Session, script_id: str) -> dict:
    """生成全新客户开场白（前端 training 页 generateOpeningWithAI，spec 未列出）"""
    script, rounds = _load_script(db, script_id)
    first_question = rounds[0].question if rounds else ""
    try:
        data = llm.chat_json(
            prompts.OPENING_SYSTEM_PROMPT,
            prompts.opening_user_prompt(script.to_dict(), first_question),
            temperature=1.0, max_tokens=300,
        )
        text = str(data.get("opening") or "").strip()
        if not text:
            raise llm.LLMError("opening 为空")
        return {"opening": text}
    except llm.LLMError as e:
        logger.warning("[opening] LLM 失败，回退剧本默认开场白: %s", e)
        return {"opening": script.opening}
