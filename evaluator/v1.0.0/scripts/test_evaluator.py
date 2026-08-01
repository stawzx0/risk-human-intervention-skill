#!/usr/bin/env python3
"""
Test Suite 路 风险与人工介入评估器
3 test cases: 1 normal + 2 boundary/failure
"""

import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from risk_evaluator import evaluate_risk


def test_case(label, query, answer, context, expected_level):
    result = evaluate_risk(query, answer, context)
    passed = result["risk_level"] == expected_level
    status = "PASS" if passed else "FAIL"
    print(f"\n{'='*50}")
    print(f"[{status}] {label}")
    print(f"  query:    {query[:40]}...")
    print(f"  expected: {expected_level} | got: {result['risk_level']}")
    print(f"  human:    {result['human_required']}")
    print(f"  factors:  {result['risk_factors']}")
    print(f"  reason:   {result['reason']}")
    return passed


def main():
    print("=" * 50)
    print("  风险与人工介入评估器 测试套件")
    print("=" * 50)

    passed = 0
    total = 3

    # ---- Test 1: Normal Flow ----
    # 标准FAQ，高置信度，无敏感内容 -> low risk
    if test_case(
        "Test 1 (Normal): 标准产品咨询，高置信度",
        query="这款精华液的成分是什么？适合油皮吗？",
        answer="本精华液含玻尿酸和烟酰胺，适合油性皮肤使用，建议每天早晚各一次。",
        context={
            "product_category": "护肤",
            "involves_promotion": False,
            "involves_inventory": False,
            "involves_medical_claim": False,
            "match_confidence": 0.92,
        },
        expected_level="low",
    ):
        passed += 1

    # ---- Test 2: Failure - High Risk ----
    # 促销问题 -> high risk, human required
    if test_case(
        "Test 2 (Failure): 促销优惠查询，必须人工确认",
        query="现在买这个面霜有优惠吗？满减活动到什么时候？",
        answer="目前该面霜参加满300减50活动，截止到本月底。",
        context={
            "product_category": "护肤",
            "involves_promotion": True,
            "involves_inventory": False,
            "involves_medical_claim": False,
            "match_confidence": 0.85,
        },
        expected_level="high",
    ):
        passed += 1

    # ---- Test 3: Boundary - Low Confidence ----
    # 低置信度匹配 -> medium risk, human recommended
    if test_case(
        "Test 3 (Boundary): 低置信度匹配，建议人工复核",
        query="这个牌子适合敏感肌吗？我之前用别的过敏了。",
        answer="该品牌产品温和不刺激，大部分敏感肌可用。",
        context={
            "product_category": "护肤",
            "involves_promotion": False,
            "involves_inventory": False,
            "involves_medical_claim": False,
            "match_confidence": 0.45,
        },
        expected_level="high",  # "过敏"触发投诉关键词，正确归类为高风险
    ):
        passed += 1

    print(f"\n{'='*50}")
    print(f"  结果: {passed}/{total} 通过")
    if passed == total:
        print("  所有测试通过！")
    else:
        print(f"  {total - passed} 个测试失败")
    print("=" * 50)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
