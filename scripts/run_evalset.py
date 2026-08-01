# -*- coding: utf-8 -*-
"""Eval runner for risk-human-intervention skill.
Usage:
  python run_eval.py --evaluator <scripts_dir> --evalset <json> --out <result.json> [--tag <name>]
"""
import argparse
import json
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VALID_LEVELS = {"low", "medium", "high"}


def load_evalset(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def expand_input(inp):
    inp = dict(inp)
    if "query_repeat" in inp:
        seg, times = inp.pop("query_repeat")
        inp["query"] = seg * times
    if "answer_repeat" in inp:
        seg, times = inp.pop("answer_repeat")
        inp["answer"] = seg * times
    return inp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evaluator", required=True)
    ap.add_argument("--evalset", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="run")
    args = ap.parse_args()

    sys.path.insert(0, os.path.abspath(args.evaluator))
    from risk_evaluator import evaluate_risk

    cases = load_evalset(args.evalset)
    results = []
    for c in cases:
        inp = expand_input(c["input"])
        query = inp.get("query", "")
        answer = inp.get("answer", "")
        context = inp.get("context")
        expected = c["expected"]

        answer_before = answer
        crash = None
        try:
            actual = evaluate_risk(query, answer, context)
        except Exception as e:  # noqa: BLE001
            actual = None
            crash = f"{type(e).__name__}: {e}"

        immutability_ok = (answer_before == answer)
        pii_ok = True
        if crash is None:
            blob = json.dumps(actual, ensure_ascii=False)
            for probe in ("13800138001", "张三"):
                if probe in blob:
                    pii_ok = False

        level_ok = crash is None and actual.get("risk_level") == expected.get("risk_level")
        human_ok = crash is None and actual.get("human_required") == expected.get("human_required")
        extra_ok = True
        if expected.get("immutability"):
            extra_ok = extra_ok and immutability_ok
        if expected.get("no_pii_leak"):
            extra_ok = extra_ok and pii_ok
        if expected.get("expected_factors"):
            factors = "".join(actual.get("risk_factors", [])) if actual else ""
            extra_ok = extra_ok and all(f in factors for f in expected["expected_factors"])
        if expected.get("response_mode"):
            extra_ok = extra_ok and actual is not None and actual.get("response_mode") == expected["response_mode"]

        passed = (crash is None) and level_ok and human_ok and extra_ok
        results.append({
            "id": c["id"], "scenario": c["scenario"], "category": c["category"],
            "input": {"query": str(query)[:60] + ("..." if len(str(query)) > 60 else ""),
                      "answer": str(answer)[:60] + ("..." if len(str(answer)) > 60 else ""),
                      "context": context},
            "expected": expected, "actual": actual, "crash": crash,
            "level_ok": level_ok, "human_ok": human_ok, "extra_ok": extra_ok,
            "passed": passed,
        })

    # ---- Metrics ----
    n_total = len(results)
    n_pass = sum(1 for r in results if r["passed"])
    valid = [r for r in results if r["expected"].get("risk_level") in VALID_LEVELS]
    invalid = [r for r in results if r["expected"].get("risk_level") == "error"]

    acc_ok = sum(1 for r in valid if r["level_ok"])
    dis_ok = sum(1 for r in valid if r["human_ok"])
    inv_ok = sum(1 for r in invalid if r["crash"] is None and r["level_ok"] and r["human_ok"])
    n_crash = sum(1 for r in results if r["crash"])

    classes = {cls: {"tp": 0, "fp": 0, "fn": 0, "total": 0} for cls in VALID_LEVELS}
    for r in valid:
        exp = r["expected"]["risk_level"]
        act = r["actual"]["risk_level"] if r["actual"] else None
        classes[exp]["total"] += 1
        if act == exp:
            classes[exp]["tp"] += 1
        else:
            classes[exp]["fn"] += 1
            if act in classes:
                classes[act]["fp"] += 1
    for cls, v in classes.items():
        v["precision"] = round(v["tp"] / (v["tp"] + v["fp"]), 4) if (v["tp"] + v["fp"]) else 0.0
        v["recall"] = round(v["tp"] / (v["tp"] + v["fn"]), 4) if (v["tp"] + v["fn"]) else 0.0
        v["f1"] = round(2 * v["precision"] * v["recall"] / (v["precision"] + v["recall"]), 4) if (v["precision"] + v["recall"]) else 0.0

    metrics = {
        "total_cases": n_total, "passed": n_pass, "crash_count": n_crash,
        "valid_cases": len(valid), "invalid_input_cases": len(invalid),
        "risk_accuracy": round(acc_ok / len(valid), 4) if valid else 0.0,
        "disposition_accuracy": round(dis_ok / len(valid), 4) if valid else 0.0,
        "business_effective_resolution_rate": round(dis_ok / len(valid), 4) if valid else 0.0,
        "invalid_input_handling_rate": round(inv_ok / len(invalid), 4) if invalid else 0.0,
        "per_class": classes, "pass_rate": round(n_pass / n_total, 4) if n_total else 0.0,
    }

    report = {"tag": args.tag, "metrics": metrics, "cases": results}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=" * 120)
    print(f"EVAL RUN [{args.tag}]  evaluator={os.path.abspath(args.evaluator)}  cases={n_total}")
    print("=" * 120)
    print(f"{'ID':6} {'测试场景':30} {'预期(风险/人工)':18} {'实际(风险/人工)':22} {'通过':6} 备注")
    for r in results:
        exp = r["expected"]
        exp_s = f"{exp.get('risk_level')}/{exp.get('human_required')}"
        if r["crash"]:
            act_s = f"CRASH({r['crash'][:40]})"
        else:
            a = r["actual"]
            act_s = f"{a.get('risk_level')}/{a.get('human_required')}"
        note = ""
        if not r["passed"]:
            if r["crash"]:
                note = "系统异常未捕获"
            else:
                why = []
                if not r["level_ok"]:
                    why.append("风险等级不符")
                if not r["human_ok"]:
                    why.append("人工决策不符")
                if not r["extra_ok"]:
                    why.append("因素/安全不符")
                note = ";".join(why)
        print(f"{r['id']:6} {r['scenario'][:28]:30} {exp_s:18} {act_s:22} {'PASS' if r['passed'] else 'FAIL':6} {note}")
    print("=" * 120)
    print("METRICS:", json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
