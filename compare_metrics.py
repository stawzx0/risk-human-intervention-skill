import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
base = json.load(open(r"C:\Users\admin\Documents\Codex\2026-08-01\new-chat\work\eval-project\results\baseline_v1.0.0.json", encoding="utf-8"))
reg = json.load(open(r"C:\Users\admin\Documents\Codex\2026-08-01\new-chat\work\eval-project\results\regression_v1.1.0.json", encoding="utf-8"))
for tag, d in [("BASELINE", base), ("REGRESSION", reg)]:
    m = d["metrics"]
    print(f"--- {tag} ---")
    print(json.dumps({k: v for k, v in m.items() if k != "per_class"}, ensure_ascii=False))
    print("per_class:", json.dumps(m["per_class"], ensure_ascii=False))
    print()
# 逐条对照
print("case comparison (id: base->reg)")
for bc in base["cases"]:
    rc = next(r for r in reg["cases"] if r["id"] == bc["id"])
    flag = "OK " if (bc["passed"] == rc["passed"] and bc["passed"]) else ("FIX" if (not bc["passed"] and rc["passed"]) else "REG!")
    print(f"{flag} {bc['id']}: base_pass={bc['passed']} reg_pass={rc['passed']}")
