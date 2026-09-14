"""合规违禁词（§3.7 / §4.4）：词库服务端建表维护，检查逻辑与前端 complianceCheck 一致——
按词库顺序找第一个命中词（保持与前端 FORBIDDEN_WORDS.find 相同的语义）。"""
from sqlalchemy.orm import Session

from app.models import ForbiddenWord

DEFAULT_ALTERNATIVE = "请改用「历史业绩稳健」「风险等级较低」等行内核准表述"


def _enabled_words(db: Session) -> list[ForbiddenWord]:
    return db.query(ForbiddenWord).filter(ForbiddenWord.enabled == 1).order_by(ForbiddenWord.id).all()


def list_words(db: Session) -> list[dict]:
    """GET /api/compliance/words：前端启动时拉取缓存"""
    return [w.to_dict() for w in _enabled_words(db)]


def check(db: Session, text: str) -> dict:
    """POST /api/compliance/check：{ok:true} | {ok:false, word, alternative}"""
    s = text or ""
    for w in _enabled_words(db):
        if w.word and w.word in s:
            return {"ok": False, "word": w.word, "alternative": w.alternative or DEFAULT_ALTERNATIVE}
    return {"ok": True}
