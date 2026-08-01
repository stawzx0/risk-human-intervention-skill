# -*- coding: utf-8 -*-
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\Users\admin\Documents\Codex\2026-08-01\new-chat\work\eval-project\evaluator\v1.1.0\scripts")
from risk_evaluator import evaluate_risk

cases = [
    ("N01 营业时间FAQ", "你们几点营业？", "9:00-21:00。", {"product_category":"其他","match_confidence":0.9}),
    ("N02 退款政策FAQ", "你们的退货政策是什么？", "支持7天无理由退款退货。", {"product_category":"其他","match_confidence":0.92}),
    ("N03 预售商品", "这个新品什么时候预售？", "预计8月15日开启预售。", {"product_category":"彩妆","match_confidence":0.88}),
    ("N04 支付方式", "支持哪些支付方式？", "微信、支付宝、银行卡。", {"product_category":"其他","match_confidence":0.9}),
    ("N05 快递时效", "多久能送到？", "顺丰次日达。", {"product_category":"其他","match_confidence":0.9}),
    ("N06 会员积分", "积分怎么用？", "积分可抵扣现金。", {"product_category":"其他","match_confidence":0.85}),
    ("N07 conf=1.0", "你们在哪？", "官网有门店列表。", {"product_category":"其他","match_confidence":1.0}),
    ("N08 conf=0.0", "你们在哪？", "官网有门店列表。", {"product_category":"其他","match_confidence":0.0}),
    ("N09 置信度缺失", "你们在哪？", "官网有门店列表。", {"product_category":"其他"}),
    ("N10 空context对象", "你们在哪？", "官网有门店列表。", {}),
    ("N11 confidence=bool", "你好", "您好！", {"product_category":"其他","match_confidence":True}),
    ("N12 category=数字", "你好", "您好！", {"product_category":123,"match_confidence":0.9}),
    ("N13 query=null", None, "您好！", {"product_category":"其他","match_confidence":0.9}),
    ("N14 query=数字", 123, "您好！", {"product_category":"其他","match_confidence":0.9}),
    ("N15 answer超长", "你好", "谢谢"*1300, {"product_category":"其他","match_confidence":0.9}),
    ("N16 emoji特殊字符", "这款好用吗？😊", "很好用，回购率高。", {"product_category":"护肤","match_confidence":0.9}),
    ("N17 纯英文", "What is the ingredient?", "Hyaluronic acid and niacinamide.", {"product_category":"skincare","match_confidence":0.9}),
    ("N18 query侧敏感词(否定问句)", "你们没有优惠吗？", "本月无优惠。", {"product_category":"护肤","match_confidence":0.85}),
    ("N19 answer侧不参加促销", "这个月店铺有活动吗？", "本店不参加促销。", {"product_category":"护肤","match_confidence":0.85}),
    ("N20 库存query触发", "这个有货吗？", "暂未缺货，库存充足。", {"product_category":"个护","match_confidence":0.9}),
    ("N21 多重否定词消解", "这个精华敏感肌能用吗？", "本品不含任何美白、祛斑成分。", {"product_category":"护肤","match_confidence":0.9}),
    ("N22 风险因素优先级", "孕妇可以用吗？", "本品参加满300减50。", {"product_category":"母婴","involves_promotion":True,"match_confidence":0.9}),
    ("N23 处理中退款(非政策)", "你好", "系统正在为您处理退款。", {"product_category":"其他","match_confidence":0.9}),
    ("N24 维权query", "我要维权！", "我们为您登记处理。", {"product_category":"其他","match_confidence":0.8}),
    ("N25 政策FAQ退货(可)", "怎么退换？", "可以免费退换货。", {"product_category":"其他","match_confidence":0.9}),
    ("N26 双重否定", "这个月店铺有活动吗？", "本品不是没有优惠，全场8折起。", {"product_category":"护肤","match_confidence":0.85}),
    ("N27 防晒功效宣称", "这款防晒效果好吗？", "SPF50+，防晒指数高。", {"product_category":"护肤","match_confidence":0.9}),
    ("N28 不含酒精", "敏感肌能用吗？", "本品不含酒精。", {"product_category":"护肤","match_confidence":0.9}),
    ("N29 差评处理", "你们东西太差了，差评！", "很抱歉，我们为您处理。", {"product_category":"其他","match_confidence":0.7}),
]

for label, q, a, ctx in cases:
    try:
        r = evaluate_risk(q, a, ctx)
        print(f"{label} => {r.get('risk_level')}/{r.get('human_required')} factors={r.get('risk_factors')}")
    except Exception as e:
        print(f"{label} => CRASH {type(e).__name__}: {e}")
