---
name: risk-human-intervention
description: Evaluate whether customer service knowledge base responses in beauty retail require human intervention. Use when: (1) assessing risk in automated customer service answers, (2) determining whether human review is needed before sending a response, (3) validating knowledge base response safety, (4) auditing or testing a knowledge base system risk classification logic.
---

# Risk & Human Intervention 风险与人工介入评估

Evaluate whether a knowledge-base-suggested response can be sent automatically or requires human review. 本技能是美妆零售知识库与客服协作系统中的“发送前安全阀”：在话术推荐引擎产出回复后、自动发送前，判定该回复的风险等级与处置方式（自动发送 / 建议人工复核 / 必须人工）。

## Input

```json
{
  "query": "string, 客户原始问题",
  "answer": "string, 系统推荐回复",
  "context": {
    "product_category": "string|null, 护肤品/彩妆/香水/母婴/个护/其他；null 表示未知，不触发 R8",
    "involves_promotion": "bool, 可选",
    "involves_inventory": "bool, 可选",
    "involves_medical_claim": "bool, 可选",
    "match_confidence": "number 0-1, 可选；缺失时按保守策略处理（R9）"
  }
}
```

## Output

```json
{
  "risk_level": "low | medium | high | error",
  "human_required": "no | recommended | yes | error",
  "risk_factors": ["风险因素说明"],
  "confidence_sufficient": "bool",
  "reason": "决策理由"
}
```

`risk_level=error` 表示输入无效（见【错误契约】），调用方应在上游修复输入，不应继续发送。

## Risk Rules（9 条）

| # | 条件 | 风险 | 人工 |
|---|------|------|------|
| R1 | 涉及促销/优惠/价格变更（context 标记或关键词，query 侧命中即触发） | high | yes |
| R2 | 涉及库存承诺/缺货信息（同上） | high | yes |
| R3 | 涉及医疗功效宣称/成分安全（同上） | high | yes |
| R4 | 投诉/纠纷类问题（投诉/退款/退货/差评/过敏/不良反应/维权） | high | yes |
| R5 | 标准FAQ，无敏感规则命中且置信度 >= 0.8 | low | no |
| R6 | 置信度 < 0.6 | medium | recommended |
| R7 | 置信度 0.6-0.8 且无敏感内容 | medium | recommended |
| R8 | 母婴产品相关（品类含母婴/育儿/婴儿/孕妇，无论置信度） | high | yes |
| R9 | 未提供 match_confidence（上下文缺失/缺字段） | medium | recommended |

优先级: 敏感规则(R1-R4/R8) > 置信度规则(R6-R7/R9) > 正常(R5)

### v1.1.0 规则细节（否定语境消解）

- 关键词命中分两侧：**query 侧命中即触发**（客户主动询问促销/库存/投诉等本身敏感）；**answer 侧命中且处于否定语境时消解**（如“不含任何医美成分”“暂无优惠活动”“暂未缺货”不构成宣称/承诺，不触发）。
- medical 词表只包含功效宣称类短语（美白/祛斑/抗皱/治疗/消炎/药妆/医美/防晒功效/防晒指数/防晒倍数/防晒效果/防晒力/SPF），**使用说明类 FAQ（如“防晒霜怎么用”）不再误报**。

## Boundaries

- **领域**: 美妆零售客服，不适用于医疗/金融/法律
- **语言**: 中文为主（英文关键词如 SPF 也覆盖）
- **输入限制**: query + answer 合计 <= 2000 字（超限返回 error，v1.1.0 起强制校验）
- **不做什么**: 不生成新回复，不修改 answer，不执行自动发送，不输出客户敏感信息（评估结果只含规则判定文本）
- **置信度由外部提供**: 评估器不做语义匹配计算；缺失置信度按 R9 保守兜底

## 错误契约（Error Contract，v1.1.0）

输入无效时统一返回 `{"risk_level":"error","human_required":"error","risk_factors":[原因],"confidence_sufficient":false,"reason":说明}`，**不抛异常**。错误场景与原因：

| 错误场景 | reason / risk_factors |
|---------|----------------------|
| query/answer 非字符串 | 输入不合法 / query、answer 必须为字符串 |
| query 或 answer 为空（含纯空白） | 输入不完整，无法评估 |
| query+answer 超过 2000 字 | 输入超限 |
| context 非 JSON 对象 | context 不合法 |
| product_category 非字符串且非 null | context 不合法 |
| match_confidence 非数值（含 bool） | 置信度参数不合法 |
| match_confidence 超出 [0,1] | 置信度参数不合法 |

## Usage

### Python API

```python
from scripts.risk_evaluator import evaluate_risk

result = evaluate_risk(
    query="这款精华液的成分是什么？",
    answer="含玻尿酸和烟酰胺，适合油皮。",
    context={"product_category": "护肤", "match_confidence": 0.92},
)
# {"risk_level": "low", "human_required": "no", ...}
```

### CLI

```bash
python scripts/risk_evaluator.py --query "..." --answer "..." --category 护肤 --confidence 0.92
python scripts/risk_evaluator.py --query "..." --answer "..." --promotion
```

### 测试与评测

```bash
# 快速单元回归（12 条断言，无外部依赖）
python scripts/test_evaluator.py

# 全量评测集（21 条用例，输出五字段结果表与指标）
python scripts/run_evalset.py --evaluator scripts --evalset evalset/evalset.json --out results/latest.json
```

## Examples

### Example 1 — 自动发送（low/no）

query: `这款精华液的成分是什么？`
answer: `含玻尿酸和烟酰胺，适合油皮。`
context: `{product_category: 护肤, match_confidence: 0.92}`
结果: `low / no / "标准FAQ，置信度充足，可自动发送"`

### Example 2 — 必须人工（high/yes，促销）

query: `现在买这个面霜有优惠吗？`
answer: `目前参加满300减50活动，截止到本月底。`
context: `{product_category: 护肤, involves_promotion: true, match_confidence: 0.85}`
结果: `high / yes / "检测到高风险因素，必须人工确认后发送"`

### Example 3 — 否定语境消解（v1.1.0，low/no）

query: `这个精华敏感肌可以用吗？`
answer: `本品不含任何医美成分，成分温和，敏感肌可用。`
context: `{product_category: 护肤, match_confidence: 0.9}`
结果: `low / no`（v1.0.0 会误报 high）

## Version

- v1.1.0（2026-08-01）：输入校验（类型/空值/2000 字边界）、否定语境消解、medical 词表精修、error 契约文档化、9 条规则齐备
- v1.0.0（2026-07-31）：初始版本，8 条规则实现
- 变更明细见 `CHANGELOG.md`；评测闭环见 `README.md` 与 `results/`
