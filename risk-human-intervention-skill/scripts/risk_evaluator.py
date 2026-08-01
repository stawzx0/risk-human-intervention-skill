#!/usr/bin/env python3
"""
Risk & Human Intervention Evaluator 路 风险与人工介入评估器
Assess whether a knowledge-base response needs human review before sending.

Version: 1.1.0
Changes vs 1.0.0 (2026-08-01, eval loop iteration 1):
  - 输入校验层: 类型/空值/长度校验，杜绝 TypeError 崩溃；落地 SKILL.md 2000 字边界
  - 规则引擎层: answer 侧否定语境消解（如“不含任何医美成分”“暂无优惠”不再误报）；
                medical 词表移除裸词“防晒”，改为功效宣称类短语，使用说明 FAQ 不再误报
  - 输出契约层: 所有 error 分支统一输出结构（含 confidence_sufficient），
                未提供置信度时 reason 说明保守策略而非误报“置信度低”
"""

import json
import re
import sys


# ---- Risk Rules Engine ----

SENSITIVE_CATEGORIES = {"母婴", "育儿", "婴儿", "孕妇"}
HIGH_RISK_KEYWORDS = {
    "promo": ["促销", "优惠", "折扣", "满减", "买赠", "特价", "限时", "秒杀"],
    "inventory": ["有货", "缺货", "库存", "断货", "预售", "补货"],
    # v1.1.0: 移除裸词“防晒”，改为功效宣称类短语（使用说明 ≠ 功效宣称）
    "medical": ["美白", "祛斑", "抗皱", "治疗", "消炎", "药妆", "医美",
                "防晒功效", "防晒指数", "防晒倍数", "防晒效果", "防晒力", "SPF", "spf"],
    "complaint": ["投诉", "退款", "退货", "差评", "过敏", "不良反应", "维权"],
}

# SKILL.md 边界：query + answer <= 2000 字
MAX_INPUT_LEN = 2000

# answer 侧否定词（仅用于消解 answer 中的关键词；query 侧关键词始终触发）
_NEGATION_WORDS = ("没有", "暂无", "不含", "未曾", "不曾", "并非", "并不",
                   "无须", "无需", "不会", "不再", "没", "无", "不", "非", "未")
# 否定词与关键词之间允许出现的修饰词/动词（如“不含任何医美成分”）
_NEGATION_GAP = re.compile(
    r"^(?:任何|什么|一点|较多|太多|多余|一个|些|参加|参与|搞|做|组织|"
    r"举办|提供|支持|存在|涉及|有|是|搞过|做过)*$"
)


def _error(reason: str, detail: str) -> dict:
    """统一的 error 输出契约（v1.1.0）。"""
    return {
        "risk_level": "error",
        "human_required": "error",
        "risk_factors": [detail],
        "confidence_sufficient": False,
        "reason": reason,
    }


def _answer_keyword_negated(answer: str, keyword: str) -> bool:
    """判断 answer 中关键词是否处于否定语境（如“不含任何医美成分”“暂无优惠”）。"""
    idx = answer.find(keyword)
    while idx != -1:
        window = answer[max(0, idx - 10):idx]
        neg_pos = -1
        neg_word = ""
        for neg in _NEGATION_WORDS:
            p = window.rfind(neg)
            if p > neg_pos:
                neg_pos = p
                neg_word = neg
        if neg_pos != -1:
            tail = window[neg_pos + len(neg_word):]
            if _NEGATION_GAP.fullmatch(tail):
                return True
        idx = answer.find(keyword, idx + 1)
    return False


def _has_risk_keyword(query: str, answer: str, keywords: list) -> bool:
    """关键词命中：query 侧命中即触发；answer 侧命中且未被否定消解才触发。"""
    for kw in keywords:
        if kw in query:
            return True
        if kw in answer and not _answer_keyword_negated(answer, kw):
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
    if _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["complaint"]):
        risk_factors.append("涉及投诉/纠纷，需升级处理")

    conf_sufficient = confidence >= 0.8

    # ---- Decision Logic ----
    # Priority: sensitive rules > confidence rules > normal flow

    sensitive = any(kw in category for kw in SENSITIVE_CATEGORIES)
    has_promo = ctx.get("involves_promotion", False) or _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["promo"])
    has_inv = ctx.get("involves_inventory", False) or _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["inventory"])
    has_med = ctx.get("involves_medical_claim", False) or _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["medical"])
    has_complaint = _has_risk_keyword(query, answer, HIGH_RISK_KEYWORDS["complaint"])

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
