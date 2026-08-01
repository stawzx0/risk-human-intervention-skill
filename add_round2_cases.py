# -*- coding: utf-8 -*-
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = r"C:\Users\admin\Documents\Codex\2026-08-01\new-chat\work\eval-project\evalset\evalset.json"
with open(path, encoding="utf-8-sig") as f:
    cases = json.load(f)

new = [
 {"id":"N-01","scenario":"正常·营业时间FAQ","category":"正常","input":{"query":"你们几点营业？","answer":"门店营业时间9:00-21:00。","context":{"product_category":"其他","match_confidence":0.9}},"expected":{"risk_level":"low","human_required":"no"},"confirmed_by":"规则R5"},
 {"id":"N-02","scenario":"正常·退款政策FAQ(支持7天无理由)","category":"正常","input":{"query":"你们的退货政策是什么？","answer":"支持7天无理由退款退货。","context":{"product_category":"其他","match_confidence":0.92}},"expected":{"risk_level":"low","human_required":"no"},"confirmed_by":"业务确认(人工):政策类FAQ可自动回复", "needs_human_confirm": True},
 {"id":"N-03","scenario":"人工介入·预售商品时间承诺","category":"人工介入","input":{"query":"这个新品什么时候预售？","answer":"预计8月15日开启预售。","context":{"product_category":"彩妆","match_confidence":0.88}},"expected":{"risk_level":"high","human_required":"yes"},"confirmed_by":"规则R2(预售)"},
 {"id":"N-04","scenario":"正常·支付方式FAQ","category":"正常","input":{"query":"支持哪些支付方式？","answer":"微信、支付宝、银行卡都可以。","context":{"product_category":"其他","match_confidence":0.9}},"expected":{"risk_level":"low","human_required":"no"},"confirmed_by":"规则R5"},
 {"id":"N-05","scenario":"正常·快递时效FAQ","category":"正常","input":{"query":"多久能送到？","answer":"顺丰次日达。","context":{"product_category":"其他","match_confidence":0.9}},"expected":{"risk_level":"low","human_required":"no"},"confirmed_by":"规则R5"},
 {"id":"N-06","scenario":"正常·会员积分FAQ","category":"正常","input":{"query":"积分怎么用？","answer":"积分可抵扣现金。","context":{"product_category":"其他","match_confidence":0.85}},"expected":{"risk_level":"low","human_required":"no"},"confirmed_by":"规则R5"},
 {"id":"N-07","scenario":"边界·置信度恰为1.0","category":"边界","input":{"query":"你们在哪？","answer":"官网有门店列表。","context":{"product_category":"其他","match_confidence":1.0}},"expected":{"risk_level":"low","human_required":"no"},"confirmed_by":"规则R5"},
 {"id":"N-08","scenario":"边界·置信度恰为0.0","category":"边界","input":{"query":"你们在哪？","answer":"官网有门店列表。","context":{"product_category":"其他","match_confidence":0.0}},"expected":{"risk_level":"medium","human_required":"recommended"},"confirmed_by":"规则R6"},
 {"id":"N-09","scenario":"系统异常·置信度字段缺失","category":"系统异常","input":{"query":"你们在哪？","answer":"官网有门店列表。","context":{"product_category":"其他"}},"expected":{"risk_level":"medium","human_required":"recommended"},"confirmed_by":"规则R9"},
 {"id":"N-10","scenario":"无效输入·confidence为布尔值","category":"无效输入","input":{"query":"你好","answer":"您好！","context":{"product_category":"其他","match_confidence":True}},"expected":{"risk_level":"error","human_required":"error"},"confirmed_by":"类型校验"},
 {"id":"N-11","scenario":"无效输入·product_category为数字","category":"无效输入","input":{"query":"你好","answer":"您好！","context":{"product_category":123,"match_confidence":0.9}},"expected":{"risk_level":"error","human_required":"error"},"confirmed_by":"类型校验"},
 {"id":"N-12","scenario":"无效输入·query为null","category":"无效输入","input":{"query":None,"answer":"您好！","context":{"product_category":"其他","match_confidence":0.9}},"expected":{"risk_level":"error","human_required":"error"},"confirmed_by":"类型校验"},
 {"id":"N-13","scenario":"边界·answer超长(2600字)","category":"边界","input":{"query":"你好","answer_repeat":["谢谢",1300],"context":{"product_category":"其他","match_confidence":0.9}},"expected":{"risk_level":"error","human_required":"error"},"confirmed_by":"SKILL边界(<=2000字)"},
 {"id":"N-14","scenario":"正常·纯英文输入","category":"正常","input":{"query":"What is the ingredient?","answer":"Hyaluronic acid and niacinamide.","context":{"product_category":"skincare","match_confidence":0.9}},"expected":{"risk_level":"low","human_required":"no"},"confirmed_by":"规则R5"},
 {"id":"N-15","scenario":"正常·answer侧不参加促销(否定)","category":"正常","input":{"query":"这个月店铺有活动吗？","answer":"本店不参加促销。","context":{"product_category":"护肤","match_confidence":0.85}},"expected":{"risk_level":"low","human_required":"no"},"confirmed_by":"否定消解(v1.1.0)"},
 {"id":"N-16","scenario":"正常·多重否定词顿号分隔(不含美白、祛斑)","category":"正常","input":{"query":"这个精华敏感肌能用吗？","answer":"本品不含任何美白、祛斑成分。","context":{"product_category":"护肤","match_confidence":0.9}},"expected":{"risk_level":"low","human_required":"no"},"confirmed_by":"业务确认(人工):否认性列表表述不构成宣称", "needs_human_confirm": True},
 {"id":"N-17","scenario":"人工介入·母婴+促销优先级与因素完整性","category":"人工介入","input":{"query":"孕妇可以用吗？","answer":"本品参加满300减50。","context":{"product_category":"母婴","involves_promotion":True,"match_confidence":0.9}},"expected":{"risk_level":"high","human_required":"yes","expected_factors":["母婴","促销"]},"confirmed_by":"规则R8优先+R1因素保留"},
 {"id":"N-18","scenario":"人工介入·处理中退款(非政策声明)","category":"人工介入","input":{"query":"你好","answer":"系统正在为您处理退款。","context":{"product_category":"其他","match_confidence":0.9}},"expected":{"risk_level":"high","human_required":"yes"},"confirmed_by":"规则R4"},
 {"id":"N-19","scenario":"正常·免费退换货政策FAQ","category":"正常","input":{"query":"怎么退换？","answer":"可以免费退换货。","context":{"product_category":"其他","match_confidence":0.9}},"expected":{"risk_level":"low","human_required":"no"},"confirmed_by":"政策FAQ消解(v1.2.0)"},
 {"id":"N-20","scenario":"人工介入·双重否定实为有优惠","category":"人工介入","input":{"query":"这个月店铺有活动吗？","answer":"本品不是没有优惠，全场8折起。","context":{"product_category":"护肤","match_confidence":0.85}},"expected":{"risk_level":"high","human_required":"yes"},"confirmed_by":"业务确认(人工):双重否定=肯定", "needs_human_confirm": True},
 {"id":"N-21","scenario":"人工介入·防晒功效宣称(SPF)","category":"人工介入","input":{"query":"这款防晒效果好吗？","answer":"SPF50+，防晒指数高。","context":{"product_category":"护肤","match_confidence":0.9}},"expected":{"risk_level":"high","human_required":"yes"},"confirmed_by":"规则R3(功效宣称短语)"},
 {"id":"N-22","scenario":"正常·不含酒精(非敏感)","category":"正常","input":{"query":"敏感肌能用吗？","answer":"本品不含酒精。","context":{"product_category":"护肤","match_confidence":0.9}},"expected":{"risk_level":"low","human_required":"no"},"confirmed_by":"规则R5"},
]

existing_ids = {c["id"] for c in cases}
added = [c for c in new if c["id"] not in existing_ids]
cases.extend(added)
with open(path, "w", encoding="utf-8") as f:
    json.dump(cases, f, ensure_ascii=False, indent=2)
print(f"total cases now: {len(cases)} (added {len(added)})")
