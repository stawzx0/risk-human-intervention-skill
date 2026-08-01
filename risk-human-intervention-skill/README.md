# risk-human-intervention Skill（完整版 v1.3.0）

美妆零售知识库与客服协作系统中的「发送前安全阀」：判定客服回复是否可自动发送或需人工介入（含发货/物流咨询）。

## 包结构

```
risk-human-intervention-skill/
├── SKILL.md                      # 技能说明：输入输出、13 条规则、错误契约、示例、版本
├── README.md                     # 本文档
├── CHANGELOG.md                  # 变更留痕
├── install-skill.ps1             # 安装到 %USERPROFILE%\.codex\skills\
├── agents/openai.yaml            # Agent 接口描述
├── references/
│   ├── risk-rules-reference.md   # 13 条规则明细 + 词表 + 否定消解 + 政策出处校验
│   └── shipping-policy.md        # 发货知识库（SP-01~SP-05 政策条目，可作 policy_source）
├── evalset/evalset.json          # 第一版评测集 v3（58 条用例）
├── results/                      # 基线 v1.0.0 ~ 回归 v1.3.0 结果（可复现）
└── scripts/
    ├── risk_evaluator.py         # 评估器（v1.3.0，纯标准库）
    ├── test_evaluator.py         # 完整回归套件（34 个测试方法）
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
# context 可选 policy_source（可追溯政策出处，如 "shipping-policy#SP-01"）
```

```bash
python scripts/risk_evaluator.py --query "..." --answer "..." --category 护肤 --confidence 0.92
```

## 测试与评测

```bash
# 快速回归（单元测试，无外部依赖）
python scripts/test_evaluator.py

# 全量评测（58 条用例，五字段结果表 + 指标）
python scripts/run_evalset.py --evaluator scripts --evalset evalset/evalset.json --out results/latest.json
```

## 评测闭环（2026-08-01）

| 轮次 | 版本 | 用例数 | 通过率 | 风险判定准确率 | 业务有效处置率 | 无效输入处理率 | 崩溃数 |
|------|------|--------|--------|----------------|----------------|----------------|--------|
| 基线1 | v1.0.0 | 21 | 15/21 (71.4%) | 78.6% | 78.6% | 66.7% | 2 |
| 回归1 | v1.1.0 | 21 | 21/21 (100%) | 100% | 100% | 100% | 0 |
| 基线2 | v1.1.0 | 44 | 41/44 (93.2%) | 91.2% | 91.2% | 100% | 0 |
| 回归2 | v1.2.0 | 44 | 44/44 (100%) | 100% | 100% | 100% | 0 |
| 基线3 | v1.2.0 | 58 | 47/58 (81.0%) | 83.0% | 83.0% | 100% | 0 |
| 回归3 | v1.3.0 | 58 | 58/58 (100%) | 100% | 100% | 100% | 0 |

### 第三轮（v1.2.0 → v1.3.0）定位并修复的问题（需求覆盖核验）

按 Day 1–2 约定核验「覆盖最常见发货问题 / 只根据可追溯政策回答 / 规则之外不做断言 / 允许查询发货知识库 / 特殊尺寸、时效承诺、价格例外转人工」：

1. 规则引擎层：发货时效承诺（次日达/48小时/什么时候发货）v1.2.0 判 low 自动发送 → 新增 R10 转人工（含 N-05 预期修正）
2. 规则引擎层：特殊尺寸/超重计费无任何规则 → 新增 R11 转人工
3. 规则引擎层：价格例外/议价/补差价无任何规则 → 新增 R12 转人工
4. 规则引擎层：承诺/宣称无政策出处约束 → 新增 R13（policy_source 校验，禁止无出处自动断言）
5. 发货知识库：新增 references/shipping-policy.md（SP-01~SP-05），Demo 增加知识库查询面板与出处回显

## 可复现性

- 版本留痕：`git tag v1.0.0 / v1.1.0 / v1.2.0 / v1.3.0`（GitHub: stawzx0/risk-human-intervention-skill），评测集与结果 JSON 随包附带
- 重跑方式：`python scripts/run_evalset.py --evaluator scripts --evalset evalset/evalset.json --out results/latest.json`
- 预期结果来源：规则 R1-R13（SKILL.md）+ 需人工确认的业务预期（见评测集 confirmed_by 字段）
