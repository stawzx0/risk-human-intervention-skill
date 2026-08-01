# Risk Rules Reference 风险规则参考

本技能使用的 9 条风险规则详细说明。

## Rule Priority

敏感规则 (R1-R4, R8) > 置信度规则 (R6-R7) > 正常流程 (R5)

## Rules Table

| ID | 触发条件 | 风险等级 | 人工介入 | 说明 |
|----|---------|---------|---------|------|
| R1 | involves_promotion=true 或 keyword match | high | yes | 促销/优惠/价格内容需确认后发送 |
| R2 | involves_inventory=true 或 keyword match | high | yes | 库存/缺货信息需确认后发送 |
| R3 | involves_medical_claim=true 或 keyword match | high | yes | 医疗功效/成分宣称需合规审核 |
| R4 | keyword match (投诉/退款/过敏等) | high | yes | 投诉纠纷需升级处理 |
| R5 | 无敏感规则命中 + confidence >= 0.8 | low | no | 标准FAQ可自动发送 |
| R6 | confidence < 0.6 | medium | recommended | 低置信度建议人工确认 |
| R7 | 0.6 <= confidence < 0.8 + 无敏感规则 | medium | recommended | 置信度不足建议复核 |
| R8 | product_category 含母婴/育儿/婴儿/孕妇 | high | yes | 母婴产品始终高风险 |
