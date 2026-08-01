# Risk Rules Reference 风险规则参考

本技能使用的 9 条风险规则详细说明（v1.1.0）。

## Rule Priority

敏感规则 (R1-R4, R8) > 置信度规则 (R6-R7, R9) > 正常流程 (R5)

## Rules Table

| ID | 触发条件 | 风险等级 | 人工介入 | 说明 |
|----|---------|---------|---------|------|
| R1 | involves_promotion=true 或 keyword match（query 侧命中即触发；answer 侧命中需未被否定消解） | high | yes | 促销/优惠/价格内容需确认后发送 |
| R2 | involves_inventory=true 或 keyword match（同上） | high | yes | 库存/缺货信息需确认后发送 |
| R3 | involves_medical_claim=true 或 keyword match（同上） | high | yes | 医疗功效/成分宣称需合规审核 |
| R4 | keyword match（投诉/退款/退货/差评/过敏/不良反应/维权） | high | yes | 投诉纠纷需升级处理 |
| R5 | 无敏感规则命中 + confidence >= 0.8 | low | no | 标准FAQ可自动发送 |
| R6 | confidence < 0.6（且无敏感规则命中） | medium | recommended | 低置信度建议人工确认 |
| R7 | 0.6 <= confidence < 0.8（且无敏感规则命中） | medium | recommended | 置信度不足建议复核 |
| R8 | product_category 含母婴/育儿/婴儿/孕妇 | high | yes | 母婴产品始终高风险 |
| R9 | 未提供 match_confidence（上下文缺失或缺字段） | medium | recommended | 保守兜底：无置信度一律建议人工复核 |

## Keyword Lists（v1.1.0）

| 规则 | 关键词 |
|------|--------|
| promo | 促销、优惠、折扣、满减、买赠、特价、限时、秒杀 |
| inventory | 有货、缺货、库存、断货、预售、补货 |
| medical | 美白、祛斑、抗皱、治疗、消炎、药妆、医美、防晒功效、防晒指数、防晒倍数、防晒效果、防晒力、SPF、spf |
| complaint | 投诉、退款、退货、差评、过敏、不良反应、维权 |

## 否定语境消解（v1.1.0）

- 否定词集合：没有、暂无、不含、未曾、不曾、并非、并不、无须、无需、不会、不再、没、无、不、非、未
- 否定词与关键词之间允许修饰词：任何、什么、一点、较多、太多、多余、一个、些、参加、参与、搞、做、组织、举办、提供、支持、存在、涉及、有、是
- 示例：`不含任何医美成分` → 医美被消解；`暂无优惠活动` → 优惠被消解；`暂未缺货，库存充足` → 缺货被消解，库存仍触发（承诺库存充足属库存信息）
- 仅作用于 answer 侧；query 侧命中始终触发

## Error Contract（v1.1.0）

输入无效返回 `risk_level=error`，不抛异常。错误场景与原因见 SKILL.md【错误契约】章节。

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.1.0 | 2026-08-01 | 补充 R9；新增否定语境消解；medical 词表精修；error 契约文档化 |
| v1.0.0 | 2026-07-31 | 初版 8 条规则 |
