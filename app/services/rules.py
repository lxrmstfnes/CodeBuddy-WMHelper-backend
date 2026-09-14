"""规则引擎兜底：从前端 utils/mock.js 逐行移植（§4.5 韧性设计——AI 失败时接口永远 200）。

原则：降级结果与前端本地 mock 完全一致，前端感受不到差异。
"""
import re

RADAR_LABELS = ["保本偏好", "流动性需求", "收益追求", "投资经验", "期限接受"]

_DEFAULT_ALTERNATIVE = "请改用「历史业绩稳健」「风险等级较低」等行内核准表述"


# ================= 对练评分（mock.js #gradeAnswer，§4.5 点名的关键词命中率公式） =================
def grade_answer(keywords: list, answer: str) -> dict | None:
    text = (answer or "").strip()
    if not text:
        return None

    hit_kws = [k for k in keywords if k in text]
    hit_rate = len(hit_kws) / len(keywords) if keywords else 0
    len_score = min(25, len(text) // 5)

    score = 45 + hit_rate * 40 + len_score
    if re.search(r"理解|您说得对|没关系|辛苦|确实", text):
        score += 8
    if re.search(r"[？?]", text):
        score += 4
    score = round(max(35, min(98, score)))

    if score >= 85:
        level = "优秀"
    elif score >= 70:
        level = "良好"
    else:
        level = "待提升"

    if level == "优秀":
        detail = f"准确触达了「{'」「'.join(hit_kws[:2])}」等关键点" if hit_kws else "表达完整"
        comment = f"思路清晰，{detail}，共情与推进节奏都把握得不错，基本可以照此实战。"
    elif level == "良好":
        comment = "整体方向正确，覆盖了部分关键要素，但还可以更聚焦：先共情客户情绪，再用数据和方案回应，最后给出明确的下一步动作。"
    else:
        comment = "这次回应偏直给了。建议先接住客户情绪（认同+共情），再讲事实与数据，最后用一个小问题引导客户往下走，避免与客户形成对立。"

    # 本地兜底不生成客户追问（nextQuestion=None），前端自动用剧本写死台词兜底（training.js）
    return {"score": score, "level": level, "comment": comment, "nextQuestion": None}


# ================= 整场总结（前端无本地实现，后端按 §4.5 自实现保底） =================
def summary_fallback(grades: list) -> dict:
    if not grades:
        return {"advice": "本场对练暂无有效评分记录，建议完整完成三轮攻防后再查看总结建议。"}
    scores = [g.score for g in grades]
    avg = sum(scores) / len(scores)
    best_i = scores.index(max(scores))
    worst_i = scores.index(min(scores))
    advice = (
        f"整场对练平均 {avg:.0f} 分，第{best_i + 1}轮拿到 {scores[best_i]} 分是全场亮点，好状态的共性值得复盘固化。"
        f"需要重点看的是第{worst_i + 1}轮（{scores[worst_i]} 分），对照该轮考察关键点，检查是共情没接住、"
        f"还是数据与方案没用上。下一步建议针对薄弱轮次单独再练一遍，把高分轮的表达节奏内化成自己的话术习惯。"
    )
    return {"advice": advice}


# ================= 客户诊断（mock.js #diagnoseClient 全量移植） =================
def _risk_num(risk_level) -> int:
    digits = re.sub(r"\D", "", str(risk_level or ""))
    return int(digits) if digits else 2


def _parse_pct(v) -> float:
    """'3.15%' → 3.15，对齐 JS parseFloat 行为"""
    m = re.match(r"^\s*([\d.]+)", str(v or ""))
    return float(m.group(1)) if m else 0.0


def _estimate_interest(benchmark_yield) -> str:
    """'2.85%' → 一万元一年的大白话利息"""
    return f"{round(_parse_pct(benchmark_yield) / 100 * 10000)}块上下"


def _asset_plain(asset_type: str) -> str:
    if "货币市场工具" in asset_type:
        return "最稳妥的短期借钱凭据，要用钱随时能取出来"
    if "同业存单" in asset_type or "纯债" in asset_type:
        return "最稳妥的国债、银行存单这类"
    if "非标" in asset_type:
        return "稳稳的债券，外加一小部分优质项目的借款"
    if "权益" in asset_type:
        return "大部分买债券打底，小部分才参与股票，涨跌都会有一点点"
    return "稳健的债券类资产"


def _min_amount_plain(min_amount) -> str:
    if min_amount <= 100:
        return "100块钱就能买"
    if min_amount >= 10000:
        return "1万块钱就能起"
    return f"{min_amount}块钱就能买"


def build_plain_talk(top: dict, config: dict) -> dict:
    """大白话转化引擎（mock.js #buildPlainTalk 逐字移植）：产品条款 → 县域客户听得懂的话"""
    is_rural = top["company"] == "渝农商理财"
    asset_words = _asset_plain(top["assetType"] or "")
    interest = _estimate_interest(top["benchmarkYield"])
    min_plain = _min_amount_plain(top["minAmount"] or 0)

    terms = [
        {"term": f"业绩比较基准 {top['benchmarkYield']}",
         "plain": f"按现在的行情，一万块放一年，利息大概{interest}"},
        {"term": f"{top['riskLevel']} 风险等级",
         "plain": "风险很低，但按监管规矩，谁也不能跟您拍胸脯说保本"},
        {"term": top["assetType"], "plain": f"主要投的都是{asset_words}"},
        {"term": f"{top['minAmount']}元起购", "plain": min_plain},
        {"term": f"{top['term']}期限",
         "plain": "跟活期一样，要用钱随时取" if top["term"] == "活期" else f"钱放{top['term']}不动，中途一般不取就行"},
    ]

    recommend = ("隔壁重庆农商行自己人出的专属产品，咱们农商行懂自己人"
                 if is_rural else f"{top['company']}这样的大机构出的稳妥产品")
    try_money = "100块钱" if (top["minAmount"] or 0) <= 100 else "一小部分钱"

    return {
        "terms": terms,
        # 场景一：微信破冰
        "icebreak": {
            "raw": f"王阿姨，我们行代销了{top['company']}的理财产品「{top['name']}」，业绩比较基准{top['benchmarkYield']}，{top['riskLevel']}风险等级，投资{top['assetType']}，您考虑一下？",
            "plain": f"王阿姨，您看您这笔定期下周就到期了。现在降息，我给您挑了一款{recommend}，{min_plain}，主要投的都是{asset_words}，虽然不承诺保本，但风险极低，比您放定期、活期都划算。先拿一小部分资金试试水，您看行不？",
        },
        # 场景二：深度面谈
        "interview": {
            "raw": f"王姐，基于您的风险画像与资金体量，建议按{config['cash']}%现金管理类、{config['fixed']}%固收类、{config['equity']}%权益类进行配置，具体产品说明书稍后发您查阅。",
            "plain": f"王姐，我给您打个比方，这笔钱就像分三个口袋：【{config['cash']}%】放\"随手袋\"，跟活期一样随用随取，人情往来、应急都不耽误；【{config['fixed']}%】放\"稳当袋\"，买的是{top['name']}这样的稳妥产品，一万块一年利息大概{interest}，比定期强；最后【{config['equity']}%】才是\"进取袋\"，搏个好收益，亏了也不伤元气。您看咱们先从哪个口袋说起？",
        },
        # 场景三：异议处理
        "objection": {
            "raw": f"阿姨，理财都是净值型的，不保本，您要看清风险揭示书再签字，{top['riskLevel']}已经是中低风险等级了，底层是{top['assetType']}。",
            "plain": f"阿姨，您担心亏钱我特别理解，我也不瞒您——所有理财都不承诺保本，谁跟您说\"保本\"，您反而要多留个心眼。但您看这款，{top['riskLevel']}级，里头放的是{asset_words}，历史上一路都稳稳当当。这样，您先拿{try_money}试水，赚了看得见，不合适随时走，主动权都在您手里，好不好？",
        },
    }


def diagnose_client(form, products: list[dict]) -> dict:
    """mock.js #diagnoseClient：form 为 DiagnoseRequest，products 为产品库 dict（camelCase 键）"""
    prefs = form.preferences or []

    # 风险得分测算
    score = 40
    score += {"25-35岁": 10, "36-50岁": 6, "51-65岁": 0, "65岁以上": -8}.get(form.age, 0)
    score += {"10万以下": 0, "10-50万": 4, "50-100万": 8, "100万以上": 12}.get(form.amount, 0)
    score += {"工资结余": 2, "理财到期/年终奖": 6, "房产/拆迁等大额资金": 8, "企业闲置资金": 10}.get(form.source, 0)
    for p in prefs:
        score += {"稳健保本": -15, "流动性优先": -5, "分散配置": 5, "追求收益": 12, "学习权益投资": 15}.get(p, 0)
    score = max(8, min(96, score))

    # 雷达图（5 维）
    liquid_need = 90 if "流动性优先" in prefs else 55
    safe = max(10, 100 - score * 0.9)
    radar = [
        round(safe),
        round(liquid_need),
        round(min(95, score * 0.9 + 15)),
        # ⚠️ 前端 mock.js 此处有运算符优先级 bug（score+bool 恒真，第4维恒为20）；
        # 按预期公式移植，与 §4.3 契约示例输出（radar[3]=67）一致
        round(min(95, score + (20 if "学习权益投资" in prefs else 5))),
        round(min(95, 30 + score * 0.65)),
    ]

    # 资产配置比例
    if score < 35:
        config = {"cash": 45, "fixed": 50, "equity": 5}
    elif score < 55:
        config = {"cash": 30, "fixed": 60, "equity": 10}
    elif score < 75:
        config = {"cash": 15, "fixed": 60, "equity": 25}
    else:
        config = {"cash": 10, "fixed": 45, "equity": 45}

    # 匹配产品：风险预算 + 流动性 + 门槛
    max_risk = 1 if score < 35 else (2 if score < 55 else (3 if score < 75 else 4))
    prefer_liquid = "流动性优先" in prefs
    prefer_safe = "稳健保本" in prefs
    base_score = {"R1": 88, "R2": 92, "R3": 86, "R4": 80}

    def _match(p: dict) -> dict:
        s = base_score.get(p["riskLevel"], 85)
        min_amt = p["minAmount"] or 0
        if prefer_liquid and p["term"] == "活期":
            s += 25
        if not prefer_liquid and _parse_pct(p["benchmarkYield"]) >= 3.5:
            s += 8
        if prefer_safe and _risk_num(p["riskLevel"]) <= 2:
            s += 6
        # 乡镇下沉客群：低门槛产品更贴合
        if prefer_safe and min_amt <= 100:
            s += 4
        if form.amount == "10万以下" and min_amt >= 10000:
            s -= 40
        if form.amount == "10万以下" and min_amt <= 100:
            s += 15
        if form.amount == "100万以上" and min_amt >= 10000:
            s += 5
        return {**p, "matchScore": min(99, s)}

    matched = sorted(
        (_match(p) for p in products if _risk_num(p["riskLevel"]) <= max_risk),
        key=lambda x: x["matchScore"], reverse=True,
    )[:3]

    # 客户画像命名
    if score < 35:
        persona = "保守储蓄型客户"
    elif score < 55:
        persona = "稳健增值型客户"
    elif score < 75:
        persona = "平衡成长型客户"
    else:
        persona = "进取配置型客户"

    top = matched[0] if matched else products[0]
    talk = build_plain_talk(top, config)

    return {
        "score": score,
        "persona": persona,
        "radar": radar,
        "radarLabels": RADAR_LABELS,
        "config": config,
        "matched": matched,
        "talk": talk,
        "form": form.model_dump(by_alias=True),
    }
