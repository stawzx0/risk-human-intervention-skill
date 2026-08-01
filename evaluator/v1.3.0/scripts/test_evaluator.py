#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Suite 风险与人工介入评估器（完整回归套件，v1.3.0）
- 覆盖：正常、人工介入(促销/库存/医疗/投诉/母婴)、置信度边界、无效输入、系统异常、否定语境、权限(不越权)
- 运行：python scripts/test_evaluator.py
- 依赖：仅标准库
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from risk_evaluator import evaluate_risk  # noqa: E402


def check(label, query, answer, context, exp_level, exp_human):
    result = evaluate_risk(query, answer, context)
    return (label, result, exp_level, exp_human,
            result["risk_level"] == exp_level and result["human_required"] == exp_human)


class TestRiskEvaluator(unittest.TestCase):
    def _assert_risk(self, query, answer, context, exp_level, exp_human, label=""):
        result = evaluate_risk(query, answer, context)
        self.assertEqual(result["risk_level"], exp_level, f"[{label}] risk_level: {result}")
        self.assertEqual(result["human_required"], exp_human, f"[{label}] human_required: {result}")
        return result

    # ---- 正常 ----
    def test_01_normal_faq_low(self):
        self._assert_risk(
            "这款精华液的成分是什么？", "含玻尿酸和烟酰胺，适合油皮。",
            {"product_category": "护肤", "match_confidence": 0.92},
            "low", "no", "标准FAQ")

    # ---- 人工介入 ----
    def test_02_promotion_high(self):
        self._assert_risk(
            "现在买这个面霜有优惠吗？", "目前参加满300减50活动，截止到本月底。",
            {"product_category": "护肤", "involves_promotion": True, "match_confidence": 0.85},
            "high", "yes", "促销")

    def test_03_inventory_high(self):
        self._assert_risk(
            "这个口红有货吗？", "目前库存紧张，预计3天后补货到仓。",
            {"product_category": "彩妆", "involves_inventory": True, "match_confidence": 0.9},
            "high", "yes", "库存")

    def test_04_medical_high(self):
        self._assert_risk(
            "这个面霜能祛斑吗？", "本品具有美白祛斑功效。",
            {"product_category": "护肤", "involves_medical_claim": True, "match_confidence": 0.88},
            "high", "yes", "医疗宣称")

    def test_05_complaint_high(self):
        self._assert_risk(
            "用了之后过敏了怎么办？", "请立即停用，我们马上为您处理售后。",
            {"product_category": "护肤", "match_confidence": 0.8},
            "high", "yes", "投诉/过敏")

    def test_06_maternal_high(self):
        self._assert_risk(
            "孕妇可以用这款吗？", "本品配方温和，建议使用前咨询医生。",
            {"product_category": "母婴", "match_confidence": 0.95},
            "high", "yes", "母婴")

    # ---- 置信度边界 ----
    def test_07_conf_0_8_low(self):
        self._assert_risk("你们几点营业？", "9:00-21:00。",
                          {"product_category": "其他", "match_confidence": 0.8}, "low", "no", "conf=0.8")

    def test_08_conf_0_6_medium(self):
        self._assert_risk("有实体店吗？", "全国300家门店。",
                          {"product_category": "其他", "match_confidence": 0.6}, "medium", "recommended", "conf=0.6")

    def test_09_conf_0_79_medium(self):
        self._assert_risk("能开发票吗？", "支持开具电子发票。",
                          {"product_category": "其他", "match_confidence": 0.79}, "medium", "recommended", "conf=0.79")

    # ---- 无效输入（不崩溃）----
    def test_10_conf_out_of_range(self):
        self._assert_risk("有实体店吗？", "有。",
                          {"product_category": "其他", "match_confidence": 1.5}, "error", "error", "conf=1.5")
        self._assert_risk("你们在哪？", "官网可见。",
                          {"product_category": "其他", "match_confidence": -0.2}, "error", "error", "conf=-0.2")

    def test_11_empty_input(self):
        self._assert_risk("", "欢迎咨询。",
                          {"product_category": "其他", "match_confidence": 0.9}, "error", "error", "空query")
        self._assert_risk("你好", "",
                          {"product_category": "其他", "match_confidence": 0.9}, "error", "error", "空answer")

    def test_12_oversize_input(self):
        self._assert_risk("你好" * 1300, "谢谢。",
                          {"product_category": "其他", "match_confidence": 0.95}, "error", "error", "超长输入")

    def test_13_conf_type_error(self):
        self._assert_risk("你好", "您好！",
                          {"product_category": "其他", "match_confidence": "abc"}, "error", "error", "conf类型")

    def test_14_category_none(self):
        self._assert_risk("你好", "您好，很高兴为您服务！",
                          {"product_category": None, "match_confidence": 0.9}, "low", "no", "未知分类")

    # ---- 否定语境消解 ----
    def test_15_negation_medical(self):
        self._assert_risk(
            "这个精华敏感肌可以用吗？", "本品不含任何医美成分，成分温和。",
            {"product_category": "护肤", "match_confidence": 0.9}, "low", "no", "否定-医美")

    def test_16_negation_promo(self):
        self._assert_risk(
            "这个月店铺有什么活动吗？", "本月暂无优惠活动，价格与官网一致。",
            {"product_category": "护肤", "match_confidence": 0.85}, "low", "no", "否定-优惠")

    def test_17_sunscreen_usage_faq(self):
        self._assert_risk(
            "防晒霜怎么用？", "出门前15分钟涂抹，户外每2小时补涂一次。",
            {"product_category": "护肤", "match_confidence": 0.93}, "low", "no", "防晒使用说明")

    # ---- 系统异常降级 ----
    def test_18_context_missing(self):
        self._assert_risk("你们有哪些产品？", "详见官网产品页。", None,
                          "medium", "recommended", "context缺失")

    # ---- 权限：不越权 ----
    def test_19_no_pii_and_immutability(self):
        answer = "您的订单已发货，请联系客服张三电话13800138001。"
        result = evaluate_risk("查询我的订单", answer,
                               {"product_category": "其他", "match_confidence": 0.9})
        blob = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("13800138001", blob, "输出不应包含客户手机号")
        self.assertNotIn("张三", blob, "输出不应包含客户姓名")



    # ---- v1.2.0：分句否定消解 + 投诉政策 FAQ（输入与评测集 N-02/N-16/N-18/N-20/N-23 对齐）----
    def test_20_negation_list_medical(self):
        self._assert_risk(
            "这个精华敏感肌能用吗？", "本品不含任何美白、祛斑成分。",
            {"product_category": "护肤", "match_confidence": 0.9}, "low", "no", "顿号否定列表")

    def test_21_double_negation_promo(self):
        self._assert_risk(
            "这个月店铺有活动吗？", "本品不是没有优惠，全场8折起。",
            {"product_category": "护肤", "match_confidence": 0.85},
            "high", "yes", "双重否定=有优惠")

    def test_22_refund_policy_faq(self):
        self._assert_risk(
            "你们的售后政策是什么？", "支持7天无理由退款退货。",
            {"product_category": "其他", "match_confidence": 0.92}, "low", "no", "退款政策FAQ")

    def test_23_query_refund_triggers(self):
        self._assert_risk(
            "怎么申请退货？", "请联系人工客服办理退货。",
            {"product_category": "其他", "match_confidence": 0.9}, "high", "yes", "query含退货")

    def test_24_answer_refund_non_policy(self):
        self._assert_risk(
            "你好", "系统正在为您处理退款。",
            {"product_category": "其他", "match_confidence": 0.9}, "high", "yes", "answer非政策声明")

    # ---- v1.3.0：发货/物流时效承诺（R10，与评测集 N-05/N-24/N-25 对齐）----
    def test_25_shipping_time_commitment_high(self):
        r = self._assert_risk(
            "今天下单什么时候发货？", "付款后48小时内发货。",
            {"product_category": "其他", "match_confidence": 0.9},
            "high", "yes", "发货时效承诺(48小时)")
        self.assertIn("时效承诺", "".join(r["risk_factors"]), "应命中 R10 时效承诺")
        self.assertIn("政策出处缺失", "".join(r["risk_factors"]), "无出处应追加 R13 风险因素")

    def test_26_shipping_next_day_high(self):
        self._assert_risk(
            "多久能送到？", "顺丰次日达。",
            {"product_category": "其他", "match_confidence": 0.9},
            "high", "yes", "快递时效承诺(次日达)")

    def test_27_shipping_policy_faq_low(self):
        self._assert_risk(
            "你们发什么快递？", "默认顺丰，偏远地区发圆通。",
            {"product_category": "其他", "match_confidence": 0.9},
            "low", "no", "发货政策FAQ(非承诺)")
        self._assert_risk(
            "运费怎么收？", "满99元包邮，不满收12元运费。",
            {"product_category": "其他", "match_confidence": 0.9},
            "low", "no", "运费政策FAQ(非例外)")

    # ---- v1.3.0：特殊尺寸/大件（R11）----
    def test_28_special_size_high(self):
        r = self._assert_risk(
            "超出标准尺寸的件怎么收费？", "超出标准尺寸按体积重计费。",
            {"product_category": "其他", "match_confidence": 0.9},
            "high", "yes", "特殊尺寸计费")
        self.assertIn("特殊尺寸", "".join(r["risk_factors"]), "应命中 R11")

    def test_29_oversize_package_high(self):
        self._assert_risk(
            "我的包裹超重了怎么办？", "超重包裹需补运费，具体以快递公司为准。",
            {"product_category": "其他", "match_confidence": 0.9},
            "high", "yes", "超重包裹")

    # ---- v1.3.0：价格例外/议价（R12）----
    def test_30_price_exception_high(self):
        r = self._assert_risk(
            "为什么我买的比别人贵？可以补差价吗？", "不同订单优惠不同，无法补差价。",
            {"product_category": "护肤", "match_confidence": 0.9},
            "high", "yes", "价格例外(补差价)")
        self.assertIn("价格例外", "".join(r["risk_factors"]), "应命中 R12")

    def test_31_negotiation_high(self):
        self._assert_risk(
            "能给我一个内部价吗？", "抱歉，价格以页面为准。",
            {"product_category": "护肤", "match_confidence": 0.9},
            "high", "yes", "议价(query侧)")

    def test_32_price_policy_faq_low(self):
        self._assert_risk(
            "价格以哪里为准？", "价格以官网页面为准。",
            {"product_category": "其他", "match_confidence": 0.9},
            "low", "no", "价格政策FAQ(非例外，R12 不误报)")

    # ---- v1.3.0：政策出处（R13 可追溯性）----
    def test_33_policy_source_traceable(self):
        r = evaluate_risk(
            "今天下单什么时候发货？", "付款后48小时内发货。",
            {"product_category": "其他", "match_confidence": 0.9, "policy_source": "shipping-policy#SP-01"})
        self.assertEqual(r["risk_level"], "high", f"承诺仍需人工: {r}")
        self.assertTrue(r["policy_traceable"], "提供出处应可追溯")
        self.assertIn("政策出处：shipping-policy#SP-01", "".join(r["risk_factors"]), "应回显出处")

    def test_34_policy_source_invalid_type_error(self):
        self._assert_risk(
            "你好", "您好！",
            {"product_category": "其他", "match_confidence": 0.9, "policy_source": 123},
            "error", "error", "policy_source 非字符串")

if __name__ == "__main__":
    unittest.main(verbosity=2)
