"""CRM 跟进记录提取（前端 pages/assistant 在用，BACKEND_SPEC 未列出，按 ai.js 契约补齐）

设计稿§3.1 扩展：传 customerId 时，抽取结果落客户档案（customer_event type=contact），
并基于 nextAction/nextFollowTime 自动生成 follow_task（跟进闭环）。
反幻觉约定：prompt 里时间保留原文（如"下周五"），由本文件 parse_follow_time 在服务端换算成具体日期。
"""
import datetime as dt
import logging
import re

from sqlalchemy.orm import Session

from app.models import CustomerEvent, FollowTask
from app.services import llm, normalize, prompts

logger = logging.getLogger(__name__)

_FOLLOW_TYPE_TO_CHANNEL = {"面谈": "store", "电话": "phone", "微信": "wechat"}
_WEEKDAY = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}


def parse_follow_time(text: str | None) -> dt.datetime | None:
    """把"周五前/明天下午/15号"这类中文相对时间换算成具体日期（POC 常见句式兜底，解析不出返回 None）。

    换算规则：周X=本周内最近的那个X（今天就是今天）；下周X=下一自然周的X；默认上午9点，
    含"下午"→14点，含"晚"→19点，含"中午"→12点。
    """
    if not text:
        return None
    today = dt.date.today()
    day: dt.date | None = None

    if "大后天" in text:
        day = today + dt.timedelta(days=3)
    elif "后天" in text:
        day = today + dt.timedelta(days=2)
    elif "明天" in text or "明日" in text:
        day = today + dt.timedelta(days=1)
    elif "今天" in text or "今日" in text or "今晚" in text:
        day = today
    else:
        m = re.search(r"(下周|周|星期)([一二三四五六日天])", text)
        if m:
            target = _WEEKDAY[m.group(2)]
            if m.group(1) == "下周":
                delta = 7 - today.weekday() + target  # 下一自然周的那一天
            else:
                delta = (target - today.weekday()) % 7  # 本周内最近的那天（可为今天）
            day = today + dt.timedelta(days=delta)
    if day is None:
        m = re.search(r"(\d{1,2})\s*[号日]", text)  # "15号"：本月15日，已过则顺延下月
        if m:
            d = int(m.group(1))
            try:
                cand = dt.date(today.year, today.month, min(d, 28))
                if cand < today:
                    nxt = (cand.replace(day=28) + dt.timedelta(days=7))
                    cand = dt.date(nxt.year, nxt.month, min(d, 28))
                day = cand
            except ValueError:
                pass
    if day is None:
        return None

    hour = 9
    if "下午" in text:
        hour = 14
    elif "中午" in text:
        hour = 12
    elif "晚" in text:
        hour = 19
    return dt.datetime.combine(day, dt.time(hour))


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


def extract_and_archive(db: Session, text: str, customer_id: str | None) -> dict:
    """抽取 + （可选）落库闭环。返回 {record, eventId, tasksCreated}（2026-09 起的新契约）。"""
    record = extract(text)
    result: dict = {"record": record, "eventId": None, "tasksCreated": []}
    if not customer_id:
        return result

    # ① 沟通记录入客户动态流（type=contact，沟通记录并入事件流——评审已确认）
    now = dt.datetime.now()
    ev = CustomerEvent(
        customer_id=customer_id,
        type="contact",
        title=record.get("summary") or (text or "")[:20] or "沟通记录",
        payload={
            "channel": _FOLLOW_TYPE_TO_CHANNEL.get(record.get("followType") or "", "other"),
            "summary": record.get("summary"),
            "aiExtract": record,
        },
        source="ai_extract",
        event_time=now,
        created_at=now,
    )
    db.add(ev)
    db.flush()  # 取 ev.id 供任务追溯
    result["eventId"] = ev.id

    # ② 有"下一步动作"则自动生成待办（"周五前回访"→ 服务端换算具体日期）
    if record.get("nextAction"):
        task = FollowTask(
            customer_id=customer_id,
            title=record["nextAction"],
            due_time=parse_follow_time(record.get("nextFollowTime")),
            status="pending",
            source="ai",
            related_event_id=ev.id,
            ai_suggestion=record.get("summary"),
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        db.flush()
        result["tasksCreated"] = [task.to_dict()]

    db.commit()
    return result
