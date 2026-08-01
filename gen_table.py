import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def load(p):
    return json.load(open(p, encoding="utf-8"))

base = load(r"C:\Users\admin\Documents\Codex\2026-08-01\new-chat\work\eval-project\results\baseline_v1.0.0.json")
reg = load(r"C:\Users\admin\Documents\Codex\2026-08-01\new-chat\work\eval-project\results\regression_v1.1.0.json")

def short_inp(r):
    q = r["input"]["query"]; a = r["input"]["answer"]
    return f"q:{q} | a:{a}"

def act_str(r):
    if r["crash"]:
        return "崩溃(TypeError)"
    a = r["actual"]
    return f"{a['risk_level']} / {a['human_required']}"

lines = []
for i, bc in enumerate(base["cases"]):
    rc = next(x for x in reg["cases"] if x["id"] == bc["id"])
    exp = bc["expected"]
    exp_s = f"{exp['risk_level']} / {exp['human_required']}"
    lines.append(f"| {bc['id']} | {bc['scenario']} | {short_inp(bc)} | {exp_s} | {act_str(bc)} | {'✅ 通过' if bc['passed'] else '❌ 失败'} | {act_str(rc)} | {'✅ 通过' if rc['passed'] else '❌ 失败'} |")
table = "\n".join(lines)
header = "| 编号 | 测试场景 | 输入内容(截断) | 预期结果(风险/人工) | 基线实际(v1.0.0) | 基线是否通过 | 回归实际(v1.1.0) | 回归是否通过 |"
sep = "|---|---|---|---|---|---|---|---|"
print(header)
print(sep)
print(table)
