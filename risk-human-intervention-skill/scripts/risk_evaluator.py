#!/usr/bin/env python3
"""
Risk & Human Intervention Evaluator 路 风险与人工介入评估器
Assess whether a knowledge-base response needs human review before sending.

Version: 1.4.0
Changes vs 1.3.0 (2026-08-01, eval loop iteration 4 - answering-boundary coverage):
  - 新增“回答边界四类”维度：输出 response_mode(direct|clarify|partial|refuse_or_escalate)
      * 边界1 可直接回答：信息完整、规则明确 -> direct（低风险自动发送）
      * 边界2 需先澄清：缺尺寸/地点/时间/对象等关键条件 -> clarify（R14，先澄清再答复）
      * 边界3 只能回答一部分：已知信息可答但必须声明未覆盖部分与下一步 -> partial（R15）
      * 边界4 不能回答：超范围/证据不足/风险过高 -> refuse_or_escalate（R16/高危/异常）
  - R13 政策口径问答（“价格以哪里为准”）不误报为澄清；高风险规则仍优先于边界判定

Changes vs 1.2.0 (2026-08-01, eval loop iteration 3 - requirement coverage):
  - 规则引擎层: 新增 R10 发货/物流时效承诺、R11 特殊尺寸/大件、R12 价格例外/议价
      * 时效承诺（次日达/48小时/什么时候发货/预计送达等）一律转人工，不再自动发送
      * 特殊尺寸/超重/大件计费一律转人工
      * 议价/差价/内部价等价格例外一律转人工；纯价格政策 FAQ（价格以页面为准）不误报
  - 规则引擎层: 新增 R13 政策出处校验（context.policy_source）
      * 承诺/宣称类内容无政策出处时追加风险因素，禁止自动断言（只根据可追溯政策回答）
      * 输出新增 policy_source / policy_traceable 字段，供人工核验与留痕
  - 原 N-05「快递时效 FAQ(顺丰次日达)」按约定修正为 high/yes（时效承诺不自动发送）

Changes vs 1.1.0 (2026-08-01, eval loop iteration 2):
  - 规则引擎层: 否定消解升级为“分句 + 否定计数”制
      * 修复多关键词顿号分隔列表（“不含任何美白、祛斑成分”不再误报）
      * 修复双重否定（“不是没有优惠”= 有优惠，正确判 high）
      * 保留原行为（“暂无优惠”“不参加促销”“暂未缺货，库存充足”等）
  - 规则引擎层: 投诉词表增加“政策 FAQ 消解”
      * answer 侧“支持/可以/提供/允许/享有/享受 + 退款/退货”视为政策声明，不触发 R4
      * query 侧与投诉/差评/维权/不良反应/过敏 不受影响
"""

import json
import re
import sys


# ---- Risk Rules Engine ----

SENSITIVE_CATEGORIES = {"母婴", "育儿", "婴儿", "孕妇"}
HIGH_RISK_KEYWORDS = {
    "promo": ["促销", "优惠", "折扣", "满减", "买赠", "特价", "限时", "秒杀"],
    "inventory": ["有货", "缺货", "库存", "断货", "预售", "补货"],
    "medical": ["美白", "祛斑", "抗皱", "治疗", "消炎", "药妆", "医美",
                "防晒功效", "防晒指数", "防晒倍数", "防晒效果", "防晒力", "SPF", "spf"],
    "complaint": ["投诉", "差评", "维权", "不良反应", "过敏"],
    "shipping_time": ["时效", "次日达", "当天达", "当日达", "隔日达", "半日达",
                      "多久能到", "多久送到", "多久发货", "多久到", "几天能到", "几天送到",
                      "几天发货", "几天到", "什么时候到", "什么时候能到", "什么时候送到",
                      "什么时候发货", "什么时候能发", "预计送达", "预计到达", "送达时间",
                      "发货时间", "发货时效", "配送时间", "派送时间", "48小时", "24小时",
                      "72小时", "工作日", "明天送达", "明天送到", "今天送达", "今天送到", "加急"],
    "special_size": ["尺寸", "超长", "超宽", "超高", "超重", "大件", "异形",
                     "体积重", "体积重量", "特殊规格", "特殊尺寸", "非标", "易碎"],
    "price_exception": ["议价", "还价", "便宜点", "优惠点", "打折吗", "补差价", "差价",
                        "买贵", "贵了", "内部价", "员工价", "专属价", "特殊价格",
                        "例外价", "价格不符", "价格不对", "多收", "少收"],
}
COMPLAINT_REFUND_KEYWORDS = ["退款", "退货"]

MAX_INPUT_LEN = 2000

# ---- 回答边界四类（v1.4.0）----
# 边界2：需先澄清——query 在索取具体信息，answer 却是占位/模板回复
QUERY_INFO_NEED = [
    "多少钱", "多久", "几号", "几点", "什么时候", "能不能", "可不可以", "有没有",
    "多大", "多少", "哪个", "哪些", "什么", "怎么", "如何", "是什么", "到哪",
    "在哪里", "在哪", "规格",
]
TEMPLATE_ANSWER = [
    "以官网为准", "以官网页面为准", "以页面为准", "以实际为准", "请提供",
    "请确认您要", "需要您的", "请具体说明", "需要查询", "查询后回复", "稍后回复",
    "暂未公布", "无法确认", "以官方公告为准", "请关注官方渠道", "需确认后", "帮您确认",
]
# 政策口径问答（“价格以哪里为准”）不视为澄清场景
_POLICY_WORDING_RE = re.compile(r"为准")

# 边界3：部分回答——多子问但 answer 只覆盖一部分，并声明未覆盖部分与下一步
UNCOVERED_MARKERS = [
    "暂未确认", "暂未公布", "尚未", "未覆盖", "需要进一步", "建议咨询",
    "需遵医嘱", "需人工", "无法确认", "待确认",
]
_MULTI_QUESTION_RE = re.compile(r"[?？]")

# 边界4：不能回答——超出范围/证据不足，拒绝并说明边界
BOUNDARY_REFUSE_MARKERS = [
    "不在服务范围", "超出", "仅提供", "只提供", "无法回答", "建议联系",
    "请关注官方渠道", "暂未公布", "以官方公告为准",
]

# answer 侧否定词（分句计数：奇数=否定，偶数=双重否定取消）
_NEGATION_RE = re.compile(
    r"没有|暂无|不含|未曾|不曾|并非|并不|无须|无需|不会|不再|没|无|不|非|未"
)
# 投诉“政策 FAQ 消解”：支持/可以/提供/允许/享有/享受 + 至多 8 字 + 退款/退货
_COMPLAINT_POLICY_RE = re.compile(r"(?:支持|可以|提供|允许|享有|享受)[^。！？；\n]{0,8}(?:退款|退货)")


def _error(reason: str, detail: str) -> dict:
    """统一的 error 输出契约。"""
    return {
        "risk_level": "error",
        "human_required": "error",
        "risk_factors": [detail],
        "confidence_sufficient": False,
        "reason": reason,
    }


def _answer_keyword_negated(answer: str, keyword: str) -> bool:
    """分句判断 answer 中关键词是否处于否定语境。

    按句读（。！？；，,;!?）分句，不拆顿号（顿号连接的同组否定列表保持否定语义）。
    同一分句内、关键词之前的否定词计数为奇数时消解；偶数（双重否定）不消解。
    例：不含任何医美成分→消解；不含任何美白、祛斑成分→两词均消解；
        不是没有优惠→不消解（实为有优惠）；暂未缺货，库存充足→缺货消解、库存仍触发。
    """
    for clause in re.split(r"[，。！？；,;!?\n]+", answer):
        for m in re.finditer(re.escape(keyword), clause):
            prefix = clause[: m.start()]
            if len(_NEGATION_RE.findall(prefix)) % 2 == 1:
                return True
    return False


def _has_risk_keyword(query: str, answer: str, keywords: list) -> bool:
    """关键词命中：query 侧命中即触发；answer 侧命中且未被否定消解才触发。"""
    for kw in keywords:
        if kw in query:
            return True
        if kw in answer and not _answer_keyword_negated(answer, kw):
            return True
    return False


def _has_complaint_risk(query: str, answer: str) -> bool:
    """R4 投诉/纠纷：query 侧命中或 answer 侧命中（政策 FAQ 除外）。"""
    if _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["complaint"]):
        return True
    for kw in COMPLAINT_REFUND_KEYWORDS:
        if kw in query:
            return True
        if kw in answer and not _COMPLAINT_POLICY_RE.search(answer) and not _answer_keyword_negated(answer, kw):
            return True
    return False


def has_high_risk_keyword(text: str, keyword_list: list) -> bool:
    """兼容 1.0.0 的公开函数（text 视为 query 侧）。"""
    return any(kw in text for kw in keyword_list)


def _detect_clarify(query: str, answer: str) -> bool:
    """R14 边界2：query 索取具体信息，answer 却是占位/模板回复 -> 需先澄清。

    政策口径问答（如“价格以哪里为准？”）有明确答案，不属于澄清场景。
    """
    if _POLICY_WORDING_RE.search(query):
        return False
    if not any(kw in query for kw in QUERY_INFO_NEED):
        return False
    return any(t in answer for t in TEMPLATE_ANSWER)


def _detect_partial(query: str, answer: str) -> bool:
    """R15 边界3：query 含多个子问题，answer 只覆盖一部分并声明未覆盖+下一步。"""
    if len(_MULTI_QUESTION_RE.findall(query)) < 2:
        return False
    return any(m in answer for m in UNCOVERED_MARKERS)


def _detect_boundary(answer: str) -> bool:
    """R16 边界4：超出业务范围或证据不足，应拒绝回答并说明边界。"""
    return any(m in answer for m in BOUNDARY_REFUSE_MARKERS)


def _validate(query, answer, context):
    """输入校验层：返回 (error_result or None, 规范化后的 context dict)。"""
    if not isinstance(query, str) or not isinstance(answer, str):
        return _error("输入不合法", "query/answer 必须为字符串"), None
    if not query.strip() or not answer.strip():
        return _error("输入不完整，无法评估", "query 或 answer 为空"), None
    if len(query) + len(answer) > MAX_INPUT_LEN:
        return _error("输入超限", f"query+answer 超过 {MAX_INPUT_LEN} 字上限"), None
    if context is None:
        context = {}
    if not isinstance(context, dict):
        return _error("context 不合法", "context 必须为 JSON 对象"), None
    category = context.get("product_category")
    if category is not None and not isinstance(category, str):
        return _error("context 不合法", "product_category 必须为字符串"), None
    confidence = context.get("match_confidence", 0.0)
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return _error("置信度参数不合法", f"confidence 值 {confidence!r} 必须为数值"), None
    ps = context.get("policy_source")
    if ps is not None and not isinstance(ps, str):
        return _error("context 不合法", "policy_source 必须为字符串"), None
    if not (0.0 <= confidence <= 1.0):
        return _error("置信度参数不合法", f"confidence 值 {confidence} 不在 0-1 范围内"), None
    return None, context


def evaluate_risk(
    query: str,
    answer: str,
    context: dict | None = None,
) -> dict:
    """
    评估风险等级与是否需要人工介入。

    Args:
        query: 客户原始问题
        answer: 系统生成的回复
        context: 上下文，包含 product_category, involves_promotion,
                 involves_inventory, involves_medical_claim, match_confidence

    Returns:
        dict: 包含 risk_level(low|medium|high|error), human_required(no|recommended|yes|error),
              risk_factors, reason
    """
    err, ctx = _validate(query, answer, context)
    if err is not None:
        return err

    category = ctx.get("product_category", "") or ""
    confidence = ctx.get("match_confidence", 0.0)
    conf_provided = "match_confidence" in ctx

    risk_factors = []

    # R8: 母婴产品
    for kw in SENSITIVE_CATEGORIES:
        if kw in category:
            risk_factors.append(f"母婴产品类({kw})，自动回复高风险")

    # R1: 促销
    if ctx.get("involves_promotion") or _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["promo"]):
        risk_factors.append("涉及促销/优惠/价格内容，需人工确认")

    # R2: 库存
    if ctx.get("involves_inventory") or _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["inventory"]):
        risk_factors.append("涉及库存/缺货信息，需人工确认")

    # R3: 医疗宣称
    if ctx.get("involves_medical_claim") or _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["medical"]):
        risk_factors.append("涉及医疗功效/成分宣称，需合规审核")

    # R4: 投诉
    if _has_complaint_risk(query, answer):
        risk_factors.append("涉及投诉/纠纷，需升级处理")

    # R10: 发货/物流时效承诺
    if _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["shipping_time"]):
        risk_factors.append("涉及发货/物流时效承诺，需人工确认")

    # R11: 特殊尺寸/大件
    if _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["special_size"]):
        risk_factors.append("涉及特殊尺寸/大件运输，需人工确认")

    # R12: 价格例外/议价
    if _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["price_exception"]):
        risk_factors.append("涉及价格例外/议价，需人工确认")

    conf_sufficient = confidence >= 0.8

    # ---- Decision Logic ----
    # Priority: sensitive rules > confidence rules > normal flow

    sensitive = any(kw in category for kw in SENSITIVE_CATEGORIES)
    has_promo = ctx.get("involves_promotion", False) or _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["promo"])
    has_inv = ctx.get("involves_inventory", False) or _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["inventory"])
    has_med = ctx.get("involves_medical_claim", False) or _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["medical"])
    has_complaint = _has_complaint_risk(query, answer)
    has_ship_time = _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["shipping_time"])
    has_special_size = _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["special_size"])
    has_price_exc = _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["price_exception"])

    is_high_risk = sensitive or has_promo or has_inv or has_med or has_complaint or has_ship_time or has_special_size or has_price_exc

    # R13: 政策出处校验（只根据可追溯政策回答，规则之外不做断言）
    policy_source = ctx.get("policy_source")
    commitment_hit = has_promo or has_inv or has_med or has_ship_time or has_special_size or has_price_exc
    if commitment_hit:
        if not policy_source:
            risk_factors.append("政策出处缺失（policy_source 未提供），禁止自动断言，需人工核验政策后回复")
        else:
            risk_factors.append(f"政策出处：{policy_source}（供人工核验，仍需确认后发送）")

    if not risk_factors:
        risk_factors.append("未检测到高风险内容")

    base = {"policy_source": policy_source,
            "policy_traceable": bool(policy_source)}

    if is_high_risk:
        return {"risk_level": "high", "human_required": "yes",
                "risk_factors": risk_factors,
                "confidence_sufficient": conf_sufficient,
                "response_mode": "refuse_or_escalate",
                "response_mode_reason": "检测到高风险因素，拒绝自动断言，转人工处理",
                "reason": "检测到高风险因素，必须人工确认后发送",
                **base}

    # ---- 回答边界四类判定（v1.4.0）：边界4 > 边界2 > 边界3 > 置信度 > 边界1 ----
    boundary_hit = _detect_boundary(answer)
    if boundary_hit:
        return {"risk_level": "low", "human_required": "no",
                "risk_factors": risk_factors,
                "confidence_sufficient": conf_sufficient,
                "response_mode": "refuse_or_escalate",
                "response_mode_reason": "超出业务范围或证据不足，拒绝回答并说明边界",
                "reason": "超出业务范围/证据不足，安全拒绝并说明边界，不自动断言",
                **base}

    clarify_hit = _detect_clarify(query, answer)
    if clarify_hit:
        risk_factors.append("缺少关键条件（对象/地点/规格/时间等），需先向客户澄清")
        return {"risk_level": "medium", "human_required": "recommended",
                "risk_factors": risk_factors,
                "confidence_sufficient": conf_sufficient,
                "response_mode": "clarify",
                "response_mode_reason": "缺少尺寸/地点/时间/对象等关键条件，应先澄清再答复",
                "reason": "缺少关键条件，需先向客户澄清，不能直接下结论",
                **base}

    partial_hit = _detect_partial(query, answer)
    if partial_hit:
        risk_factors.append("仅部分问题可回答，需声明未覆盖部分与下一步动作")
        return {"risk_level": "low", "human_required": "recommended",
                "risk_factors": risk_factors,
                "confidence_sufficient": conf_sufficient,
                "response_mode": "partial",
                "response_mode_reason": "仅覆盖部分问题，需声明未覆盖部分与下一步动作",
                "reason": "部分回答：已知信息可答，须声明未覆盖部分与下一步动作",
                **base}

    if confidence < 0.6:
        reason = (f"置信度({confidence:.2f})较低，建议人工确认"
                  if conf_provided else "未提供置信度，按保守策略建议人工复核")
        return {"risk_level": "medium", "human_required": "recommended",
                "risk_factors": risk_factors,
                "confidence_sufficient": False,
                "response_mode": "refuse_or_escalate",
                "response_mode_reason": "证据不足（置信度低），说明边界并建议人工复核",
                "reason": reason,
                **base}
    if confidence < 0.8:
        reason = (f"置信度({confidence:.2f})不足，建议人工复核"
                  if conf_provided else "未提供置信度，按保守策略建议人工复核")
        return {"risk_level": "medium", "human_required": "recommended",
                "risk_factors": risk_factors,
                "confidence_sufficient": False,
                "response_mode": "refuse_or_escalate",
                "response_mode_reason": "证据不足（置信度不足），说明边界并建议人工复核",
                "reason": reason,
                **base}
    return {"risk_level": "low", "human_required": "no",
            "risk_factors": risk_factors,
            "confidence_sufficient": True,
            "response_mode": "direct",
            "response_mode_reason": "信息完整、规则明确，可直接简洁回答",
            "reason": "标准FAQ，置信度充足，可自动发送",
            **base}


# ---- CLI ----

def main():
    import argparse
    parser = argparse.ArgumentParser(description="风险与人工介入评估")
    parser.add_argument("--query", required=True, help="客户问题")
    parser.add_argument("--answer", required=True, help="系统回复")
    parser.add_argument("--category", default="其他", help="产品品类")
    parser.add_argument("--promotion", action="store_true", help="涉及促销")
    parser.add_argument("--inventory", action="store_true", help="涉及库存")
    parser.add_argument("--medical", action="store_true", help="涉及医疗宣称")
    parser.add_argument("--confidence", type=float, default=0.9, help="匹配置信度 0-1")

    args = parser.parse_args()
    ctx = {
        "product_category": args.category,
        "involves_promotion": args.promotion,
        "involves_inventory": args.inventory,
        "involves_medical_claim": args.medical,
        "match_confidence": args.confidence,
    }
    result = evaluate_risk(args.query, args.answer, ctx)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
