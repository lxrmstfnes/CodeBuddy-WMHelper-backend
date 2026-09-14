"""模型输出归一化：移植自前端 utils/ai.js 的 normalize* 系列函数。

职责：把大模型的自由输出钳制进 §4 契约——字段缺失/越界时修复，
修不了的（如产品 id 编造、话术结构残缺）抛 LLMError 走规则兜底。
"""
from app.services.llm import LLMError
from app.services.prompts import CRM_FIELDS

RADAR_LABELS = ["保本偏好", "流动性需求", "收益追求", "投资经验", "期限接受"]


def _clamp_int(v, lo: int, hi: int, dft: int) -> int:
    try:
        n = round(float(v))
    except (TypeError, ValueError):
        return dft
    return max(lo, min(hi, n))


def _null_str(v):
    """字符串 "null" / 空串 归一化为 None（对应 ai.js 的处理）"""
    if not isinstance(v, str):
        return None
    v = v.strip()
    return None if not v or v.lower() == "null" else v


# ---------- §4.1 评分结果 ----------
def normalize_grade(data: dict) -> dict:
    try:
        score = round(float(data.get("score")))
    except (TypeError, ValueError):
        raise LLMError("score 字段非法")
    score = max(0, min(100, score))

    level = str(data.get("level") or "")
    if level not in ("优秀", "良好", "待提升"):
        level = "优秀" if score >= 85 else "良好" if score >= 70 else "待提升"

    comment = str(data.get("comment") or "").strip() or \
        "本次回应已记录，建议先共情客户情绪，再用数据回应，最后给出明确的下一步动作。"

    # 模型按 Prompt 输出 snake_case 的 next_question；兼容驼峰
    next_question = _null_str(data.get("next_question")) or _null_str(data.get("nextQuestion"))

    return {"score": score, "level": level, "comment": comment, "nextQuestion": next_question}


# ---------- §4.2 总结建议 ----------
def normalize_summary(data: dict) -> dict:
    advice = str(data.get("advice") or "").strip()
    if not advice:
        raise LLMError("advice 字段为空")
    return {"advice": advice}


# ---------- §4.3 客户诊断 ----------
def normalize_diagnosis(data: dict, form, products: list[dict]) -> dict:
    """products 为真实产品库（dict 列表），用于校验 matched 的 id，防止模型编造产品（ai.js 同款铁律）"""
    score = _clamp_int(data.get("score"), 0, 100, 50)
    persona = str(data.get("persona") or "").strip() or "稳健进阶型客户"

    radar_raw = data.get("radar") if isinstance(data.get("radar"), list) else []
    radar = [_clamp_int(radar_raw[i] if i < len(radar_raw) else None, 0, 100, 50) for i in range(5)]

    c = data.get("config") or {}
    cash = max(0, _clamp_int(c.get("cash"), 0, 100, 0))
    fixed = max(0, _clamp_int(c.get("fixed"), 0, 100, 0))
    equity = max(0, _clamp_int(c.get("equity"), 0, 100, 0))
    total = cash + fixed + equity
    if total <= 0:
        cash, fixed, equity = 30, 60, 10
    else:
        cash = round(cash / total * 100)
        fixed = round(fixed / total * 100)
        equity = 100 - cash - fixed

    by_id = {p["id"]: p for p in products}
    matched = []
    for m in data.get("matched") or []:
        p = by_id.get((m or {}).get("id"))
        if not p:
            continue
        matched.append({
            **p,
            "matchScore": _clamp_int(m.get("matchScore"), 0, 99, 85),
            "matchReason": str(m.get("reason") or "").strip(),
        })
    matched = matched[:3]
    if not matched:
        raise LLMError("matched 为空或产品 id 非法")

    talk = data.get("talk") or {}

    def scene(o):
        raw = str((o or {}).get("raw") or "").strip()
        plain = str((o or {}).get("plain") or "").strip()
        return {"raw": raw, "plain": plain} if raw and plain else None

    icebreak, interview, objection = scene(talk.get("icebreak")), scene(talk.get("interview")), scene(talk.get("objection"))
    if not (icebreak and interview and objection):
        raise LLMError("talk 话术结构不完整")

    terms = [
        {"term": str((t or {}).get("term") or "").strip(), "plain": str((t or {}).get("plain") or "").strip()}
        for t in (talk.get("terms") or [])
    ]
    terms = [t for t in terms if t["term"] and t["plain"]]

    return {
        "score": score,
        "persona": persona,
        "radar": radar,
        "radarLabels": RADAR_LABELS,
        "config": {"cash": cash, "fixed": fixed, "equity": equity},
        "matched": matched,
        "talk": {"terms": terms, "icebreak": icebreak, "interview": interview, "objection": objection},
        "form": form.model_dump(by_alias=True),
    }


# ---------- CRM 跟进记录 ----------
def normalize_crm_record(data: dict) -> dict:
    record = {}
    for f in CRM_FIELDS:
        key = f["key"]
        v = data.get(key)
        if key == "intentProducts":
            if isinstance(v, str):
                v = [v] if v else []
            record[key] = [x for x in (v if isinstance(v, list) else []) if x]
        else:
            record[key] = _null_str(v) if isinstance(v, str) else None
    return record
