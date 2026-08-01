# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\Users\admin\Documents\Codex\2026-08-01\new-chat\work\eval-project\evaluator\v1.2.0\scripts")
import risk_evaluator as r
print("regex:", r._COMPLAINT_POLICY_RE.pattern)
ans = "支持7天无理由退款退货。"
m = r._COMPLAINT_POLICY_RE.search(ans)
print("match:", m)
print("complaint:", r._has_complaint_risk("你们的退货政策是什么？", ans))
print("evaluate:", r.evaluate_risk("你们的退货政策是什么？", ans, {"product_category":"其他","match_confidence":0.92}))
