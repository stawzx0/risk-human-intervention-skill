#!/usr/bin/env python3
"""
Risk & Human Intervention Evaluator 路 风险与人工介入评估器
Assess whether a knowledge-base response needs human review before sending.

Version: 1.2.0
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
}
COMPLAINT_REFUND_KEYWORDS = ["退款", "退货"]

MAX_INPUT_LEN = 2000

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

    conf_sufficient = confidence >= 0.8

    # ---- Decision Logic ----
    # Priority: sensitive rules > confidence rules > normal flow

    sensitive = any(kw in category for kw in SENSITIVE_CATEGORIES)
    has_promo = ctx.get("involves_promotion", False) or _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["promo"])
    has_inv = ctx.get("involves_inventory", False) or _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["inventory"])
    has_med = ctx.get("involves_medical_claim", False) or _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["medical"])
    has_complaint = _has_complaint_risk(query, answer)

    is_high_risk = sensitive or has_promo or has_inv or has_med or has_complaint

    if not risk_factors:
        risk_factors.append("未检测到高风险内容")

    if is_high_risk:
        return {"risk_level": "high", "human_required": "yes",
                "risk_factors": risk_factors,
                "confidence_sufficient": conf_sufficient,
                "reason": "检测到高风险因素，必须人工确认后发送"}
    if confidence < 0.6:
        reason = (f"置信度({confidence:.2f})较低，建议人工确认"
                  if conf_provided else "未提供置信度，按保守策略建议人工复核")
        return {"risk_level": "medium", "human_required": "recommended",
                "risk_factors": risk_factors,
                "confidence_sufficient": False,
                "reason": reason}
    if confidence < 0.8:
        reason = (f"置信度({confidence:.2f})不足，建议人工复核"
                  if conf_provided else "未提供置信度，按保守策略建议人工复核")
        return {"risk_level": "medium", "human_required": "recommended",
                "risk_factors": risk_factors,
                "confidence_sufficient": False,
                "reason": reason}
    return {"risk_level": "low", "human_required": "no",
            "risk_factors": risk_factors,
            "confidence_sufficient": True,
            "reason": "标准FAQ，置信度充足，可自动发送"}


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
