/* Risk & Human Intervention Evaluator — JavaScript port v1.4.0
   与 risk_evaluator.py (v1.4.0) 行为一致的纯前端移植，用于静态部署（GitHub Pages）降级。
   验证方式：68 条评测集在 Node 中与 Python 输出逐字段比对（100% 一致）。 */
(function (global) {
  "use strict";

  var SENSITIVE_CATEGORIES = ["母婴", "育儿", "婴儿", "孕妇"];
  var HIGH_RISK_KEYWORDS = {
    promo: ["促销", "优惠", "折扣", "满减", "买赠", "特价", "限时", "秒杀"],
    inventory: ["有货", "缺货", "库存", "断货", "预售", "补货"],
    medical: ["美白", "祛斑", "抗皱", "治疗", "消炎", "药妆", "医美",
              "防晒功效", "防晒指数", "防晒倍数", "防晒效果", "防晒力", "SPF", "spf"],
    complaint: ["投诉", "差评", "维权", "不良反应", "过敏"],
    shipping_time: ["时效", "次日达", "当天达", "当日达", "隔日达", "半日达",
                    "多久能到", "多久送到", "多久发货", "多久到", "几天能到", "几天送到",
                    "几天发货", "几天到", "什么时候到", "什么时候能到", "什么时候送到",
                    "什么时候发货", "什么时候能发", "预计送达", "预计到达", "送达时间",
                    "发货时间", "发货时效", "配送时间", "派送时间", "48小时", "24小时",
                    "72小时", "工作日", "明天送达", "明天送到", "今天送达", "今天送到", "加急"],
    special_size: ["尺寸", "超长", "超宽", "超高", "超重", "大件", "异形",
                   "体积重", "体积重量", "特殊规格", "特殊尺寸", "非标", "易碎"],
    price_exception: ["议价", "还价", "便宜点", "优惠点", "打折吗", "补差价", "差价",
                      "买贵", "贵了", "内部价", "员工价", "专属价", "特殊价格",
                      "例外价", "价格不符", "价格不对", "多收", "少收"]
  };
  var COMPLAINT_REFUND_KEYWORDS = ["退款", "退货"];
  var MAX_INPUT_LEN = 2000;

  var QUERY_INFO_NEED = [
    "多少钱", "多久", "几号", "几点", "什么时候", "能不能", "可不可以", "有没有",
    "多大", "多少", "哪个", "哪些", "什么", "怎么", "如何", "是什么", "到哪",
    "在哪里", "在哪", "规格"
  ];
  var TEMPLATE_ANSWER = [
    "以官网为准", "以官网页面为准", "以页面为准", "以实际为准", "请提供",
    "请确认您要", "需要您的", "请具体说明", "需要查询", "查询后回复", "稍后回复",
    "暂未公布", "无法确认", "以官方公告为准", "请关注官方渠道", "需确认后", "帮您确认"
  ];
  var UNCOVERED_MARKERS = [
    "暂未确认", "暂未公布", "尚未", "未覆盖", "需要进一步", "建议咨询",
    "需遵医嘱", "需人工", "无法确认", "待确认"
  ];
  var BOUNDARY_REFUSE_MARKERS = [
    "不在服务范围", "超出", "仅提供", "只提供", "无法回答", "建议联系",
    "请关注官方渠道", "暂未公布", "以官方公告为准"
  ];

  var NEGATION_PATTERN = "没有|暂无|不含|未曾|不曾|并非|并不|无须|无需|不会|不再|没|无|不|非|未";
  var COMPLAINT_POLICY_RE = /(?:支持|可以|提供|允许|享有|享受)[^。！？；\n]{0,8}(?:退款|退货)/;
  var POLICY_WORDING_RE = /为准/;

  function negCount(s) {
    var m = s.match(new RegExp(NEGATION_PATTERN, "g"));
    return m ? m.length : 0;
  }

  function answerKeywordNegated(answer, keyword) {
    var clauses = answer.split(/[，。！？；,;!?\n]+/);
    for (var i = 0; i < clauses.length; i++) {
      var clause = clauses[i];
      var start = 0;
      while (true) {
        var idx = clause.indexOf(keyword, start);
        if (idx === -1) break;
        var prefix = clause.slice(0, idx);
        if (negCount(prefix) % 2 === 1) return true;
        start = idx + keyword.length;
      }
    }
    return false;
  }

  function hasRiskKeyword(query, answer, keywords) {
    for (var i = 0; i < keywords.length; i++) {
      var kw = keywords[i];
      if (query.indexOf(kw) !== -1) return true;
      if (answer.indexOf(kw) !== -1 && !answerKeywordNegated(answer, kw)) return true;
    }
    return false;
  }

  function hasComplaintRisk(query, answer) {
    if (hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.complaint)) return true;
    for (var i = 0; i < COMPLAINT_REFUND_KEYWORDS.length; i++) {
      var kw = COMPLAINT_REFUND_KEYWORDS[i];
      if (query.indexOf(kw) !== -1) return true;
      if (answer.indexOf(kw) !== -1 && !COMPLAINT_POLICY_RE.test(answer) && !answerKeywordNegated(answer, kw)) return true;
    }
    return false;
  }

  function detectClarify(query, answer) {
    if (POLICY_WORDING_RE.test(query)) return false;
    var qHit = false;
    for (var i = 0; i < QUERY_INFO_NEED.length; i++) {
      if (query.indexOf(QUERY_INFO_NEED[i]) !== -1) { qHit = true; break; }
    }
    if (!qHit) return false;
    for (var j = 0; j < TEMPLATE_ANSWER.length; j++) {
      if (answer.indexOf(TEMPLATE_ANSWER[j]) !== -1) return true;
    }
    return false;
  }

  function detectPartial(query, answer) {
    var qCount = (query.match(/[?？]/g) || []).length;
    if (qCount < 2) return false;
    for (var i = 0; i < UNCOVERED_MARKERS.length; i++) {
      if (answer.indexOf(UNCOVERED_MARKERS[i]) !== -1) return true;
    }
    return false;
  }

  function detectBoundary(answer) {
    for (var i = 0; i < BOUNDARY_REFUSE_MARKERS.length; i++) {
      if (answer.indexOf(BOUNDARY_REFUSE_MARKERS[i]) !== -1) return true;
    }
    return false;
  }

  function pyRepr(v) {
    if (v === null) return "None";
    if (typeof v === "string") return "'" + v + "'";
    if (typeof v === "boolean") return v ? "True" : "False";
    return String(v);
  }

  function errorResult(reason, detail) {
    return {
      risk_level: "error",
      human_required: "error",
      risk_factors: [detail],
      confidence_sufficient: false,
      reason: reason
    };
  }

  function validate(query, answer, context) {
    if (typeof query !== "string" || typeof answer !== "string") {
      return [errorResult("输入不合法", "query/answer 必须为字符串"), null];
    }
    if (!query.trim() || !answer.trim()) {
      return [errorResult("输入不完整，无法评估", "query 或 answer 为空"), null];
    }
    if (query.length + answer.length > MAX_INPUT_LEN) {
      return [errorResult("输入超限", "query+answer 超过 " + MAX_INPUT_LEN + " 字上限"), null];
    }
    if (context === null || context === undefined) context = {};
    if (typeof context !== "object" || Array.isArray(context)) {
      return [errorResult("context 不合法", "context 必须为 JSON 对象"), null];
    }
    var category = context.product_category;
    if (category !== null && category !== undefined && typeof category !== "string") {
      return [errorResult("context 不合法", "product_category 必须为字符串"), null];
    }
    var confidence = context.match_confidence !== undefined ? context.match_confidence : 0.0;
    if (typeof confidence === "boolean" || typeof confidence !== "number") {
      return [errorResult("置信度参数不合法", "confidence 值 " + pyRepr(confidence) + " 必须为数值"), null];
    }
    var ps = context.policy_source;
    if (ps !== null && ps !== undefined && typeof ps !== "string") {
      return [errorResult("context 不合法", "policy_source 必须为字符串"), null];
    }
    if (!(confidence >= 0 && confidence <= 1)) {
      return [errorResult("置信度参数不合法", "confidence 值 " + confidence + " 不在 0-1 范围内"), null];
    }
    return [null, context];
  }

  function evaluateRisk(query, answer, context) {
    var v = validate(query, answer, context);
    var err = v[0], ctx = v[1];
    if (err !== null) return err;

    var category = ctx.product_category || "";
    var confidence = ctx.match_confidence !== undefined ? ctx.match_confidence : 0.0;
    var confProvided = Object.prototype.hasOwnProperty.call(ctx, "match_confidence");
    var policySource = ctx.policy_source === undefined ? null : ctx.policy_source;

    var riskFactors = [];

    for (var i = 0; i < SENSITIVE_CATEGORIES.length; i++) {
      var kw8 = SENSITIVE_CATEGORIES[i];
      if (category.indexOf(kw8) !== -1) riskFactors.push("母婴产品类(" + kw8 + ")，自动回复高风险");
    }
    if (!!ctx.involves_promotion || hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.promo)) {
      riskFactors.push("涉及促销/优惠/价格内容，需人工确认");
    }
    if (!!ctx.involves_inventory || hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.inventory)) {
      riskFactors.push("涉及库存/缺货信息，需人工确认");
    }
    if (!!ctx.involves_medical_claim || hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.medical)) {
      riskFactors.push("涉及医疗功效/成分宣称，需合规审核");
    }
    if (hasComplaintRisk(query, answer)) {
      riskFactors.push("涉及投诉/纠纷，需升级处理");
    }
    if (hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.shipping_time)) {
      riskFactors.push("涉及发货/物流时效承诺，需人工确认");
    }
    if (hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.special_size)) {
      riskFactors.push("涉及特殊尺寸/大件运输，需人工确认");
    }
    if (hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.price_exception)) {
      riskFactors.push("涉及价格例外/议价，需人工确认");
    }

    var confSufficient = confidence >= 0.8;

    var sensitive = false;
    for (var s = 0; s < SENSITIVE_CATEGORIES.length; s++) {
      if (category.indexOf(SENSITIVE_CATEGORIES[s]) !== -1) { sensitive = true; break; }
    }
    var hasPromo = !!ctx.involves_promotion || hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.promo);
    var hasInv = !!ctx.involves_inventory || hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.inventory);
    var hasMed = !!ctx.involves_medical_claim || hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.medical);
    var hasComplaint = hasComplaintRisk(query, answer);
    var hasShipTime = hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.shipping_time);
    var hasSpecialSize = hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.special_size);
    var hasPriceExc = hasRiskKeyword(query, answer, HIGH_RISK_KEYWORDS.price_exception);

    var isHighRisk = sensitive || hasPromo || hasInv || hasMed || hasComplaint || hasShipTime || hasSpecialSize || hasPriceExc;

    var commitmentHit = hasPromo || hasInv || hasMed || hasShipTime || hasSpecialSize || hasPriceExc;
    if (commitmentHit) {
      if (!policySource) {
        riskFactors.push("政策出处缺失（policy_source 未提供），禁止自动断言，需人工核验政策后回复");
      } else {
        riskFactors.push("政策出处：" + policySource + "（供人工核验，仍需确认后发送）");
      }
    }
    if (riskFactors.length === 0) {
      riskFactors.push("未检测到高风险内容");
    }

    var base = { policy_source: policySource, policy_traceable: !!policySource };

    if (isHighRisk) {
      return {
        risk_level: "high", human_required: "yes",
        risk_factors: riskFactors,
        confidence_sufficient: confSufficient,
        response_mode: "refuse_or_escalate",
        response_mode_reason: "检测到高风险因素，拒绝自动断言，转人工处理",
        reason: "检测到高风险因素，必须人工确认后发送",
        policy_source: base.policy_source, policy_traceable: base.policy_traceable
      };
    }

    if (detectBoundary(answer)) {
      return {
        risk_level: "low", human_required: "no",
        risk_factors: riskFactors,
        confidence_sufficient: confSufficient,
        response_mode: "refuse_or_escalate",
        response_mode_reason: "超出业务范围或证据不足，拒绝回答并说明边界",
        reason: "超出业务范围/证据不足，安全拒绝并说明边界，不自动断言",
        policy_source: base.policy_source, policy_traceable: base.policy_traceable
      };
    }

    if (detectClarify(query, answer)) {
      riskFactors.push("缺少关键条件（对象/地点/规格/时间等），需先向客户澄清");
      return {
        risk_level: "medium", human_required: "recommended",
        risk_factors: riskFactors,
        confidence_sufficient: confSufficient,
        response_mode: "clarify",
        response_mode_reason: "缺少尺寸/地点/时间/对象等关键条件，应先澄清再答复",
        reason: "缺少关键条件，需先向客户澄清，不能直接下结论",
        policy_source: base.policy_source, policy_traceable: base.policy_traceable
      };
    }

    if (detectPartial(query, answer)) {
      riskFactors.push("仅部分问题可回答，需声明未覆盖部分与下一步动作");
      return {
        risk_level: "low", human_required: "recommended",
        risk_factors: riskFactors,
        confidence_sufficient: confSufficient,
        response_mode: "partial",
        response_mode_reason: "仅覆盖部分问题，需声明未覆盖部分与下一步动作",
        reason: "部分回答：已知信息可答，须声明未覆盖部分与下一步动作",
        policy_source: base.policy_source, policy_traceable: base.policy_traceable
      };
    }

    if (confidence < 0.6) {
      var reason60 = confProvided ? "置信度(" + confidence.toFixed(2) + ")较低，建议人工确认" : "未提供置信度，按保守策略建议人工复核";
      return {
        risk_level: "medium", human_required: "recommended",
        risk_factors: riskFactors,
        confidence_sufficient: false,
        response_mode: "refuse_or_escalate",
        response_mode_reason: "证据不足（置信度低），说明边界并建议人工复核",
        reason: reason60,
        policy_source: base.policy_source, policy_traceable: base.policy_traceable
      };
    }
    if (confidence < 0.8) {
      var reason80 = confProvided ? "置信度(" + confidence.toFixed(2) + ")不足，建议人工复核" : "未提供置信度，按保守策略建议人工复核";
      return {
        risk_level: "medium", human_required: "recommended",
        risk_factors: riskFactors,
        confidence_sufficient: false,
        response_mode: "refuse_or_escalate",
        response_mode_reason: "证据不足（置信度不足），说明边界并建议人工复核",
        reason: reason80,
        policy_source: base.policy_source, policy_traceable: base.policy_traceable
      };
    }
    return {
      risk_level: "low", human_required: "no",
      risk_factors: riskFactors,
      confidence_sufficient: true,
      response_mode: "direct",
      response_mode_reason: "信息完整、规则明确，可直接简洁回答",
      reason: "标准FAQ，置信度充足，可自动发送",
      policy_source: base.policy_source, policy_traceable: base.policy_traceable
    };
  }

  var SHIPPING_KB = [
    {id: "SP-01", title: "发货时效", auto: "no",
     keywords: ["发货", "48小时", "什么时候发货", "多久发货"],
     policy: "默认现货商品付款后 48 小时内发出（工作日，节假日顺延）；预售/定制商品以页面或人工告知为准。"},
    {id: "SP-02", title: "物流时效", auto: "no",
     keywords: ["时效", "次日达", "几天能到", "多久能到", "什么时候到", "预计送达", "送达"],
     policy: "顺丰次日达仅限现货、13:00 前付款且地址在覆盖范围；普通快递 3-5 个工作日。时效属承诺性内容，须人工核实后回复。"},
    {id: "SP-03", title: "运费规则", auto: "yes",
     keywords: ["运费", "包邮", "邮费"],
     policy: "满 99 元包邮（特价/秒杀除外，以结算页为准）；未满收取 12 元运费；偏远地区以结算页为准。"},
    {id: "SP-04", title: "特殊尺寸/大件", auto: "no",
     keywords: ["尺寸", "超重", "超长", "大件", "异形", "体积重", "特殊规格"],
     policy: "超长（>1.2m）/超重（>10kg）/异形/易碎件运费需单独核算，以客服人工报价为准，系统不得自动报价。"},
    {id: "SP-05", title: "价格例外", auto: "no",
     keywords: ["内部价", "员工价", "专属价", "议价", "补差价", "差价", "便宜", "贵"],
     policy: "公开价目以官网页面为准；渠道价/内部价/员工价/专属价需人工确认；差价补偿按售后政策逐单审核，不接受自动承诺。"}
  ];

  global.evaluateRisk = evaluateRisk;
  global.SHIPPING_KB = SHIPPING_KB;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { evaluateRisk: evaluateRisk, SHIPPING_KB: SHIPPING_KB };
  }
})(typeof window !== "undefined" ? window : globalThis);