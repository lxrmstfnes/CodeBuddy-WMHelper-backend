"""合规违禁词（§3.7 / §4.4）：词库服务端建表维护，检查逻辑与前端 complianceCheck 一致——
按词库顺序找第一个命中词（保持与前端 FORBIDDEN_WORDS.find 相同的语义）。"""
from sqlalchemy.orm import Session

from app.models import ForbiddenWord

DEFAULT_ALTERNATIVE = "请改用「历史业绩稳健」「风险等级较低」等行内核准表述"

# 写入微信话术时不能整句替换（太长），只换短词
SCRIPT_SHORT_REPLACE = {
    "保本": "本金波动较小",
    "稳赚": "历史业绩较稳",
    "刚兑": "净值型管理",
    "零风险": "风险等级较低",
    "无风险": "风险等级较低",
    "保收益": "业绩比较基准",
}


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


def scrub_script(db: Session, text: str) -> tuple[str, bool, list[str]]:
    """清洗话术中的违禁词。返回 (文本, 原文是否已合规, 命中词列表)。"""
    s = text or ""
    hits: list[str] = []
    for w in _enabled_words(db):
        word = w.word or ""
        if word and word in s:
            hits.append(word)
            s = s.replace(word, SCRIPT_SHORT_REPLACE.get(word, "风险等级较低"))
    return s, len(hits) == 0, hits
