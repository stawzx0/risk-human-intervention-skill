---
name: risk-human-intervention
description: Evaluate whether customer service knowledge base responses in beauty retail (including shipping/logistics questions) require human intervention. Use when: (1) assessing risk in automated customer service answers, (2) determining whether human review is needed before sending a response, (3) validating knowledge base response safety, (4) auditing or testing a knowledge base system risk classification logic.
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
    "match_confidence": "number 0-1, 可选；缺失时按保守策略处理（R9）",
    "policy_source": "string|null, 可选；可追溯政策出处（如 shipping-policy#SP-01），承诺/宣称类内容建议必填（R13）"
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
  "reason": "决策理由",
  "policy_source": "string|null，回显输入出处",
  "policy_traceable": "bool，承诺/宣称类内容是否带有可追溯政策出处",
  "response_mode": "direct | clarify | partial | refuse_or_escalate，回答边界四类（v1.4.0）",
  "response_mode_reason": "string，回答边界判定依据"
}
```

`risk_level=error` 表示输入无效（见【错误契约】），调用方应在上游修复输入，不应继续发送。

## Risk Rules（16 条）

| # | 条件 | 风险 | 人工 |
|---|------|------|------|
| R1 | 涉及促销/优惠/价格变更（context 标记或关键词，query 侧命中即触发） | high | yes |
| R2 | 涉及库存承诺/缺货信息（同上） | high | yes |
| R3 | 涉及医疗功效宣称/成分安全（同上） | high | yes |
| R4 | 投诉/纠纷类问题（投诉/差评/维权/不良反应/过敏；退款/退货：query 侧命中即触发，answer 侧命中仅政策声明可消解） | high | yes |
| R5 | 标准FAQ，无敏感规则命中且置信度 >= 0.8 | low | no |
| R6 | 置信度 < 0.6 | medium | recommended |
| R7 | 置信度 0.6-0.8 且无敏感内容 | medium | recommended |
| R8 | 母婴产品相关（品类含母婴/育儿/婴儿/孕妇，无论置信度） | high | yes |
| R9 | 未提供 match_confidence（上下文缺失/缺字段） | medium | recommended |
| R10 | 涉及发货/物流时效承诺（时效、次日达、48小时、什么时候发货/送到、预计送达、工作日等，query 或 answer 命中） | high | yes |
| R11 | 涉及特殊尺寸/大件（尺寸、超长/超重、体积重、异形、特殊规格等） | high | yes |
| R12 | 涉及价格例外/议价（议价、还价、补差价、买贵、内部价、员工价等；纯价格政策 FAQ 如“价格以页面为准”不触发） | high | yes |
| R13 | 承诺/宣称类内容（R1/R2/R3/R10/R11/R12 命中）的**政策出处校验**：未提供 policy_source 时追加风险因素“政策出处缺失，禁止自动断言”；提供时回显出处供人工核验 | 不改变等级 | 承诺仍须人工 |
| R14 | **边界2·需先澄清**：query 索取具体信息（多少钱/多久/多大规格/哪些地区/是什么等）而 answer 为占位/模板回复（以官网为准、请提供、需要查询、暂未公布等）；政策口径问答（“价格以哪里为准？”）除外 | medium | recommended |
| R15 | **边界3·只能回答一部分**：query 含多子问、answer 只覆盖一部分且已声明未覆盖部分与下一步（暂未确认/建议咨询等） | low | recommended |
| R16 | **边界4·不能回答**：超出业务范围或证据不足（不在服务范围、仅提供、建议联系、暂未公布等），拒绝回答并说明边界，不自动断言 | low | no |

优先级: 敏感规则(R1-R4/R8/R10-R12) > 边界4(R16) > 边界2(R14) > 边界3(R15) > 置信度规则(R6-R7/R9) > 正常(R5)

### v1.3.0 规则细节（发货/物流时效承诺 + 特殊尺寸 + 价格例外 + 政策出处）

- **R10 发货/物流时效承诺**：时效承诺类关键词（时效、次日达/当天达/隔日达、48/24/72小时、什么时候发货/能到/送到、预计送达、X个工作日、明天送达等）query 或 answer 命中即触发 high。
  - 例：`多久能送到？→ 顺丰次日达。` → high/yes（v1.2.0 误判 low，按约定修正：时效承诺不自动发送）。
  - 政策口径 FAQ 不触发：`你们发什么快递？→ 默认顺丰，偏远地区发圆通。`、`运费怎么收？→ 满99元包邮` → low/no。
- **R11 特殊尺寸/大件**：尺寸、超长/超宽/超高/超重、大件、异形、体积重、特殊规格等 → high/yes（如“超出标准尺寸的件怎么收费”）。
- **R12 价格例外/议价**：议价、还价、便宜点、补差价、差价、买贵、内部价/员工价/专属价、价格不符/不对等 → high/yes；纯价格政策 FAQ（“价格以官网页面为准”）不误报。
- **R13 政策出处（可追溯性）**：承诺/宣称类内容（促销/库存/医疗/时效/尺寸/价格例外任一命中）必须能追溯到政策出处。context 提供 `policy_source` 时输出回显出处（`policy_traceable=true`）供人工核验；未提供时追加风险因素“政策出处缺失，禁止自动断言”。**规则之外的内容不做断言**：所有承诺一律转人工，评估器不自动放行无出处的承诺/宣称。
- 发货知识库见 `references/shipping-policy.md`（SP-01~SP-05 政策条目，可作 policy_source 引用）。

### v1.4.0 规则细节（回答边界四类 response_mode）

- **边界1 可直接回答**（`direct`）：信息完整、规则明确、无敏感规则命中且置信度 >= 0.8 → 自动发送简洁正确结果。
- **边界2 需先澄清**（`clarify`，R14）：缺少尺寸/地点/时间/对象等关键条件时不能直接下结论。判定：query 含信息索取词（多少钱/多久/几号/几点/什么时候/能不能/多大/多少/哪个/哪些/什么/怎么/如何/是什么/规格等）且 answer 为占位/模板回复（以官网为准、请提供、请确认您要、需要查询、查询后回复、暂未公布、无法确认等）→ `medium/recommended/clarify`。
  - 例：`这款精华液多少钱？→ 价格以官网页面为准。` → clarify（缺对象，需先澄清再答复）。
  - 政策口径问答不误报：`价格以哪里为准？→ 价格以官网页面为准。` → direct（R14 跳过“为准”句式）。
- **边界3 只能回答一部分**（`partial`，R15）：已知信息可答，但必须声明未覆盖部分与下一步动作。判定：query 含 >= 2 个子问题（中英文问号计数）且 answer 含未覆盖声明（暂未确认/尚未/需要进一步/建议咨询/需遵医嘱等）→ `low/recommended/partial`。
  - 例：`这款精华敏感肌能用吗？油皮能用吗？→ 敏感肌可用；油皮适配性暂未确认，建议咨询人工确认。` → partial。
  - 高危场景优先：`孕妇能用吗？敏感肌能用吗？→ 敏感肌可用；孕妇使用需遵医嘱。`（母婴 R8）→ high/yes/refuse_or_escalate。
- **边界4 不能回答**（`refuse_or_escalate`，R16）：超出业务范围、证据不足或风险过高 → 拒绝、转人工或说明边界。判定：高风险规则命中（high）、输入无效（error）、置信度不足（medium），或 answer 含边界说明（不在服务范围/仅提供/建议联系/暂未公布/以官方公告为准等）→ 拒绝回答并说明边界，不自动断言。
  - 例：`你们可以修手机吗？→ 本店仅提供美妆售前咨询，手机维修不在服务范围。` → low/no/refuse_or_escalate（安全拒绝）。
  - 例：`这款面膜什么时候上新款？→ 新品上市时间暂未公布，请关注官方渠道通知。` → low/no/refuse_or_escalate（证据不足，不自动断言）。

### v1.2.0 规则细节（分句否定消解 + 投诉政策 FAQ 消解）

- 否定消解升级为**分句 + 否定计数**：按句读（。！？；，,;!?）分句，不拆顿号；同一分句内关键词之前的否定词计数为奇数时消解，偶数（双重否定）不消解。
  - 例：`不含任何美白、祛斑成分` → 美白/祛斑均消解（顿号列表保持同一否定语境，v1.1.0 漏判）。
  - 例：`不是没有优惠` → 双重否定 = 有优惠，不消解、触发 R1（v1.1.0 误消解）。
  - 例：`暂未缺货，库存充足` → 缺货消解、库存仍触发（原行为保留）。
- 投诉词表分离：`complaint` 仅保留 投诉/差评/维权/不良反应/过敏；`退款/退货` 单独处理——answer 侧命中 `支持/可以/提供/允许/享有/享受 + 退款/退货`（至多 8 字间隔）视为**政策声明**，不触发 R4；query 侧命中退款/退货始终触发。

### v1.1.0 规则细节（否定语境消解）

- 关键词命中分两侧：**query 侧命中即触发**（客户主动询问促销/库存/投诉等本身敏感）；**answer 侧命中且处于否定语境时消解**（如“不含任何医美成分”“暂无优惠活动”“暂未缺货”不构成宣称/承诺，不触发）。
- medical 词表只包含功效宣称类短语（美白/祛斑/抗皱/治疗/消炎/药妆/医美/防晒功效/防晒指数/防晒倍数/防晒效果/防晒力/SPF），**使用说明类 FAQ（如“防晒霜怎么用”）不再误报**。

## Boundaries

- **领域**: 美妆零售客服（含发货/物流咨询），不适用于医疗/金融/法律
- **发货知识库**: 政策条目见 `references/shipping-policy.md`（SP-01~SP-05），可追溯出处（policy_source）供人工核验；评估器不做知识库检索
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
# 快速单元回归（无外部依赖）
python scripts/test_evaluator.py

# 全量评测集（44 条用例，输出五字段结果表与指标）
python scripts/run_evalset.py --evaluator scripts --evalset evalset/evalset.json --out results/latest.json
# 对比两版本：python run_eval.py --evaluator <v1.2.0/scripts> --evalset evalset/evalset.json --out results/regression_v1.2.0.json
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

### Example 4 — 退款政策 FAQ（v1.2.0，low/no）

query: `你们支持7天无理由退款退货吗？`
answer: `支持7天无理由退款退货，商品不影响二次销售即可。`
context: `{product_category: 护肤, match_confidence: 0.9}`
结果: `low / no`（v1.1.0 误判为投诉 high；v1.2.0 识别为政策声明）

### Example 6 — 发货时效承诺（v1.3.0，high/yes）

query: `今天下单什么时候发货？`
answer: `付款后48小时内发货。`
context: `{product_category: 其他, match_confidence: 0.9}`
结果: `high / yes`，风险因素含“发货/物流时效承诺”与“政策出处缺失”（R10+R13）

### Example 7 — 特殊尺寸/价格例外（v1.3.0，high/yes）

query: `超出标准尺寸的件怎么收费？` / `能给我一个内部价吗？`
answer: `超出标准尺寸按体积重计费。` / `抱歉，价格以页面为准。`
结果: `high / yes`（R11 / R12）；而 `价格以官网页面为准。` 不误报 → low/no

### Example 8 — 可追溯政策出处（v1.3.0）

query: `今天下单什么时候发货？`
answer: `付款后48小时内发货。`
context: `{product_category: 其他, match_confidence: 0.9, policy_source: "shipping-policy#SP-01"}`
结果: `high / yes`，`policy_traceable: true`，风险因素回显出处供人工核验

### Example 9 — 回答边界四类（v1.4.0）

- 边界2 需先澄清：`这个精华液多大规格？ → 请确认您要的规格（15ml/30ml），不同规格价格不同。`
  结果: `medium / recommended / clarify`（R14：缺规格，先澄清再答复，不直接下结论）
- 边界3 部分回答：`这款精华敏感肌能用吗？油皮能用吗？ → 敏感肌可用；油皮适配性暂未确认，建议咨询人工确认。`
  结果: `low / recommended / partial`（R15：已声明未覆盖部分与下一步动作）
- 边界4 不能回答：`你们可以修手机吗？ → 本店仅提供美妆售前咨询，手机维修不在服务范围。`
  结果: `low / no / refuse_or_escalate`（R16：超出业务范围，拒绝并说明边界）
- 政策口径不误报：`价格以哪里为准？ → 价格以官网页面为准。` → `low / no / direct`（R14 排除“为准”句式）

### Example 5 — 双重否定（v1.2.0，high/yes）

query: `这次618是不是没有优惠了？`
answer: `不是没有优惠，叠加满减后力度更大。`
context: `{product_category: 护肤, involves_promotion: false, match_confidence: 0.85}`
结果: `high / yes`（v1.1.0 误消解为 low；v1.2.0 识别双重否定）

## Version

- v1.3.0（2026-08-01，评测第三轮·需求覆盖核验）：新增 R10 发货/物流时效承诺、R11 特殊尺寸/大件、R12 价格例外/议价、R13 政策出处校验（policy_source）；按约定修正“快递时效 FAQ(次日达)”为转人工；评测集扩至 58 条
- v1.2.0（2026-08-01，评测第二轮）：否定消解升级为分句+否定计数（修复顿号列表漏判与双重否定误消解）、投诉词表分离 + 退款政策 FAQ 消解
- v1.1.0（2026-08-01）：输入校验（类型/空值/2000 字边界）、否定语境消解、medical 词表精修、error 契约文档化、9 条规则齐备
- v1.0.0（2026-07-31）：初始版本，8 条规则实现
- 变更明细见 `CHANGELOG.md`；评测闭环见 `README.md` 与 `results/`
