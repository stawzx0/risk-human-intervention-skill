# -*- coding: utf-8 -*-
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
path = r"C:\Users\admin\Documents\Codex\2026-08-01\new-chat\work\eval-project\evalset\evalset.json"
with open(path, encoding="utf-8-sig") as f:
    cases = json.load(f)

for c in cases:
    if c["id"] == "N-02":
        c["scenario"] = "正常·退款政策FAQ(answer侧政策声明)"
        c["input"]["query"] = "你们的售后政策是什么？"
        c["confirmed_by"] = "业务确认(人工):answer侧政策声明不触发R4"
    if c["id"] == "N-19":
        c["confirmed_by"] = "政策FAQ消解(v1.2.0)"

# 新增：query 侧含退货仍转人工（锁定规则）
new_case = {"id":"N-23","scenario":"人工介入·客户咨询退货流程(query含退货)","category":"人工介入",
  "input":{"query":"怎么申请退货？","answer":"请联系人工客服办理退货。","context":{"product_category":"其他","match_confidence":0.9}},
  "expected":{"risk_level":"high","human_required":"yes"},"confirmed_by":"规则R4(query侧始终触发)"}
if not any(c["id"] == "N-23" for c in cases):
    cases.append(new_case)

with open(path, "w", encoding="utf-8") as f:
    json.dump(cases, f, ensure_ascii=False, indent=2)
print("total:", len(cases))
