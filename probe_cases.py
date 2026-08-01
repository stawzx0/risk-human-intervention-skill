# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\Users\admin\Documents\Codex\2026-08-01\new-chat\work\eval-project\evaluator\v1.0.0\scripts")
from risk_evaluator import evaluate_risk

cases = [
    ("T01 标准FAQ高置信", "这款精华液的成分是什么？", "含玻尿酸和烟酰胺，适合油皮。", {"product_category":"护肤","match_confidence":0.92}),
    ("T02 促销咨询", "现在买面霜有优惠吗？", "参加满300减50活动。", {"product_category":"护肤","involves_promotion":True,"match_confidence":0.85}),
    ("T03 库存缺货", "这个口红有货吗？", "目前库存紧张，预计3天到货。", {"product_category":"彩妆","match_confidence":0.9}),
    ("T04 医疗宣称", "这个面霜能祛斑吗？", "具有美白祛斑功效。", {"product_category":"护肤","match_confidence":0.88}),
    ("T05 投诉过敏", "用了之后过敏了怎么办？", "请立即停用并联系我们。", {"product_category":"护肤","match_confidence":0.8}),
    ("T06 母婴产品", "孕妇可以用这款吗？", "本品温和，建议咨询医生。", {"product_category":"母婴","match_confidence":0.95}),
    ("T07 conf=0.8边界", "你们几点营业？", "9:00-21:00。", {"product_category":"其他","match_confidence":0.8}),
    ("T08 conf=0.6边界", "有实体店吗？", "全国300家门店。", {"product_category":"其他","match_confidence":0.6}),
    ("T09 conf=0.79", "能开发票吗？", "支持电子发票。", {"product_category":"其他","match_confidence":0.79}),
    ("T10 conf越界1.5", "有实体店吗？", "有。", {"product_category":"其他","match_confidence":1.5}),
    ("T11 conf负数", "你们在哪？", "门店列表见官网。", {"product_category":"其他","match_confidence":-0.2}),
    ("T12 空query", "", "欢迎咨询。", {"product_category":"其他","match_confidence":0.9}),
    ("T13 空answer", "你好", "", {"product_category":"其他","match_confidence":0.9}),
    ("T14 超长输入2500字", "你好"*1300, "谢谢"*10, {"product_category":"其他","match_confidence":0.95}),
    ("T15 否定促销(answer侧)", "这个月有什么活动吗？", "暂无优惠活动，价格与官网一致。", {"product_category":"护肤","match_confidence":0.85}),
    ("T16 否定医疗(answer侧)", "这个精华敏感肌可以用吗？", "本品不含任何医美成分，成分温和。", {"product_category":"护肤","match_confidence":0.9}),
    ("T17 防晒使用说明", "防晒霜怎么用？", "出门前15分钟涂抹，每2小时补涂。", {"product_category":"护肤","match_confidence":0.93}),
    ("T18 category=None", "你好", "您好，很高兴为您服务。", {"product_category":None,"match_confidence":0.9}),
    ("T19 confidence字符串", "你好", "您好！", {"product_category":"其他","match_confidence":"abc"}),
    ("T20 无context", "你们有哪些产品？", "详见官网产品页。", None),
    ("T21 否定库存(answer侧)", "这个还卖吗？", "本商品暂未缺货，库存充足。", {"product_category":"个护","match_confidence":0.9}),
    ("T22 政策FAQ退款", "可以退货吗？", "支持7天无理由退款退货。", {"product_category":"其他","match_confidence":0.9}),
]

for label, q, a, ctx in cases:
    try:
        r = evaluate_risk(q, a, ctx)
        print(f"{label} => level={r.get('risk_level')} human={r.get('human_required')} factors={r.get('risk_factors')}")
    except Exception as e:
        print(f"{label} => CRASH: {type(e).__name__}: {e}")
