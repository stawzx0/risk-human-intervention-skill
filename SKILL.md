---
name: risk-human-intervention
description: Evaluate whether customer service knowledge base responses in beauty retail require human intervention. Use when: (1) assessing risk in automated customer service answers, (2) determining whether human review is needed before sending a response, (3) validating knowledge base response safety, (4) auditing or testing a knowledge base system risk classification logic.
---

# Risk & Human Intervention 风险与人工介入评估

Evaluate whether a knowledge-base-suggested response can be sent automatically or requires human review.

## Input

```json
{
  "query": "string, 客户原始问题",
  "answer": "string, 系统推荐回复",
  "context": {
    "product_category": "护肤品/彩妆/香水/母婴/个护/其他",
    "involves_promotion": "bool",
    "involves_inventory": "bool",
    "involves_medical_claim": "bool",
    "match_confidence": "float 0-1"
  }
}
```

## Output

```json
{
  "risk_level": "low | medium | high",
  "human_required": "yes | no | recommended",
  "risk_factors": ["风险因素说明"],
  "confidence_sufficient": "bool",
  "reason": "决策理由"
}
```

## Risk Rules

| # | 条件 | 风险 | 人工 |
|---|------|------|------|
| R1 | 涉及促销/优惠/价格变更 | high | yes |
| R2 | 涉及库存承诺/缺货信息 | high | yes |
| R3 | 涉及医疗功效宣称/成分安全 | high | yes |
| R4 | 投诉/纠纷类问题 | high | yes |
| R5 | 标准FAQ，置信度 >= 0.8 | low | no |
| R6 | 置信度 < 0.6 | medium | recommended |
| R7 | 置信度 0.6-0.8 且无敏感内容 | medium | recommended |
| R8 | 母婴产品相关（无论置信度）| high | yes |

优先级: 敏感规则(R1-R4/R8) > 置信度规则(R6-R7) > 正常(R5)

## Boundaries

- **领域**: 美妆零售客服，不适用于医疗/金融/法律
- **语言**: 中文
- **输入限制**: query+answer <= 2000字
- **不做什么**: 不生成新回复，不修改answer，不执行自动发送
- **置信度由外部提供**: 评估器不做语义匹配计算

## Usage

```python
from scripts.risk_evaluator import evaluate_risk
result = evaluate_risk(query, answer, context)
```

```bash
python scripts/risk_evaluator.py --query "..." --answer "..." --category 护肤 --confidence 0.92
```
