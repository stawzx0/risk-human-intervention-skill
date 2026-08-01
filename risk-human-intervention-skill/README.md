# risk-human-intervention Skill（完整版 v1.1.0）

美妆零售知识库与客服协作系统中的「发送前安全阀」：判定客服回复是否可自动发送或需人工介入。

## 包结构

```
risk-human-intervention-skill/
├── SKILL.md                      # 技能说明：输入输出、9 条规则、错误契约、示例、版本
├── README.md                     # 本文档
├── CHANGELOG.md                  # 变更留痕
├── install-skill.ps1             # 安装到 %USERPROFILE%\.codex\skills\
├── agents/openai.yaml            # Agent 接口描述
├── references/risk-rules-reference.md   # 9 条规则明细 + 词表 + 否定消解说明
├── evalset/evalset.json          # 第一版评测集（21 条用例）
├── results/                      # 基线 v1.0.0 与回归 v1.1.0 结果（可复现）
└── scripts/
    ├── risk_evaluator.py         # 评估器（v1.1.0，纯标准库）
    ├── test_evaluator.py         # 完整回归套件（19 个测试方法 / 12+ 断言）
    └── run_evalset.py            # 评测运行器（输出五字段结果表 + 指标）
```

## 安装

```powershell
.\install-skill.ps1
```

安装后 Codex 即可通过 `$risk-human-intervention` 使用。

## 使用

```python
from scripts.risk_evaluator import evaluate_risk
result = evaluate_risk(query, answer, context)
```

```bash
python scripts/risk_evaluator.py --query "..." --answer "..." --category 护肤 --confidence 0.92
```

## 测试与评测

```bash
# 快速回归（单元测试，无外部依赖）
python scripts/test_evaluator.py

# 全量评测（21 条用例，五字段结果表 + 指标）
python scripts/run_evalset.py --evaluator scripts --evalset evalset/evalset.json --out results/latest.json
```

## 评测闭环（2026-08-01，第一版）

| 轮次 | 版本 | 通过率 | 风险判定准确率 | 业务有效处置率 | 无效输入处理率 | 崩溃数 |
|------|------|--------|----------------|----------------|----------------|--------|
| 基线 | v1.0.0 | 15/21 (71.4%) | 78.6% | 78.6% | 66.7% | 2 |
| 回归 | v1.1.0 | 21/21 (100%) | 100% | 100% | 100% | 0 |

定位并修复的问题（详见 CHANGELOG 与《Eval 与项目验收报告》）：
1. 输入校验层：`confidence="abc"`、`product_category=null` 导致 TypeError 崩溃 → 类型/空值校验，统一 error 契约
2. 输入校验层：SKILL.md 2000 字边界未落地 → 强制校验
3. 规则引擎层：否定语境误报（“不含任何医美成分”“暂无优惠”被判 high）→ 否定消解
4. 规则引擎层：medical 词表过宽（“防晒霜怎么用”使用说明误报）→ 词表精修
5. 输出契约层：error 分支未文档化 → 错误契约补齐（9 条规则齐备）

## 可复现性

- 版本留痕：`git tag v1.0.0` / `v1.1.0`（见 eval-project 仓库），评测集与结果 JSON 随包附带
- 重跑方式：`python scripts/run_evalset.py --evaluator scripts --evalset evalset/evalset.json --out results/latest.json`
- 预期结果来源：规则 R1-R9（SKILL.md）+ 3 条需人工确认的业务预期（E-17/E-18/E-19，见评测集 confirmed_by 字段）
