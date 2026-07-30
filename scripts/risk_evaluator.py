#!/usr/bin/env python3
"""
Risk & Human Intervention Evaluator 路 风险与人工介入评估器
Assess whether a knowledge-base response needs human review before sending.
"""

import json
import sys
from typing import Optional  # noqa: UP035


# ---- Risk Rules Engine ----

SENSITIVE_CATEGORIES = {"母婴", "育儿", "婴儿", "孕妇"}
HIGH_RISK_KEYWORDS = {
    "promo": ["促销", "优惠", "折扣", "满减", "买赠", "特价", "限时", "秒杀"],
    "inventory": ["有货", "缺货", "库存", "断货", "预售", "补货"],
    "medical": ["美白", "祛斑", "抗皱", "治疗", "消炎", "药妆", "医美", "防晒"],
    "complaint": ["投诉", "退款", "退货", "差评", "过敏", "不良反应", "维权"],
}


def has_high_risk_keyword(text: str, keyword_list: list) -> bool:
    return any(kw in text for kw in keyword_list)


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
        dict: 包含 risk_level, human_required, risk_factors, reason
    """
    if not context:
        context = {}

    if not query or not answer:
        return {"risk_level": "error", "human_required": "error",
                "risk_factors": ["query 或 answer 为空"], "reason": "输入不完整，无法评估"}

    risk_factors = []
    category = context.get("product_category", "")

    # R8: 母婴产品
    for kw in SENSITIVE_CATEGORIES:
        if kw in category:
            risk_factors.append(f"母婴产品类({kw})，自动回复高风险")

    # R1: 促销
    if context.get("involves_promotion") or has_high_risk_keyword(query + answer, HIGH_RISK_KEYWORDS["promo"]):
        risk_factors.append("涉及促销/优惠/价格内容，需人工确认")

    # R2: 库存
    if context.get("involves_inventory") or has_high_risk_keyword(query + answer, HIGH_RISK_KEYWORDS["inventory"]):
        risk_factors.append("涉及库存/缺货信息，需人工确认")

    # R3: 医疗宣称
    if context.get("involves_medical_claim") or has_high_risk_keyword(query + answer, HIGH_RISK_KEYWORDS["medical"]):
        risk_factors.append("涉及医疗功效/成分宣称，需合规审核")

    # R4: 投诉
    if has_high_risk_keyword(query + answer, HIGH_RISK_KEYWORDS["complaint"]):
        risk_factors.append("涉及投诉/纠纷，需升级处理")

    # Confidence
    confidence = context.get("match_confidence", 0.0)
    if not (0.0 <= confidence <= 1.0):
        return {"risk_level": "error", "human_required": "error",
                "risk_factors": [f"confidence 值 {confidence} 不在 0-1 范围内"],
                "confidence_sufficient": False,
                "reason": "置信度参数不合法"}
    conf_sufficient = confidence >= 0.8

    # ---- Decision Logic ----
    # Priority: sensitive rules > confidence rules > normal flow

    sensitive = any(kw in category for kw in SENSITIVE_CATEGORIES)
    has_promo = context.get("involves_promotion", False) or has_high_risk_keyword(query + answer, HIGH_RISK_KEYWORDS["promo"])
    has_inv = context.get("involves_inventory", False) or has_high_risk_keyword(query + answer, HIGH_RISK_KEYWORDS["inventory"])
    has_med = context.get("involves_medical_claim", False) or has_high_risk_keyword(query + answer, HIGH_RISK_KEYWORDS["medical"])
    has_complaint = has_high_risk_keyword(query + answer, HIGH_RISK_KEYWORDS["complaint"])

    is_high_risk = sensitive or has_promo or has_inv or has_med or has_complaint

    if not risk_factors:
        risk_factors.append("未检测到高风险内容")

    if is_high_risk:
        return {"risk_level": "high", "human_required": "yes",
                "risk_factors": risk_factors,
                "confidence_sufficient": conf_sufficient,
                "reason": "检测到高风险因素，必须人工确认后发送"}
    elif confidence < 0.6:
        return {"risk_level": "medium", "human_required": "recommended",
                "risk_factors": risk_factors,
                "confidence_sufficient": False,
                "reason": f"置信度({confidence:.2f})较低，建议人工确认"}
    elif confidence < 0.8:
        return {"risk_level": "medium", "human_required": "recommended",
                "risk_factors": risk_factors,
                "confidence_sufficient": False,
                "reason": f"置信度({confidence:.2f})不足，建议人工复核"}
    else:
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
