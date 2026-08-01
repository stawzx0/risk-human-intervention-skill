#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo server for risk-human-intervention skill v1.3.0 (stdlib only).

Run:  python demo/server.py
Open: http://127.0.0.1:8765
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "risk-human-intervention-skill", "scripts"))
sys.path.insert(0, SCRIPTS)

from risk_evaluator import evaluate_risk  # noqa: E402

PORT = 8765
MAX_BODY = 2 * 1024 * 1024  # 2MB 请求体上限
READ_TIMEOUT = 10  # 秒，防慢速/悬挂连接

# ---- 发货知识库（与 references/shipping-policy.md 对应）----
SHIPPING_KB = [
    {"id": "SP-01", "title": "发货时效", "auto": "no",
     "keywords": ["发货", "48小时", "什么时候发货", "多久发货"],
     "policy": "默认现货商品付款后 48 小时内发出（工作日，节假日顺延）；预售/定制商品以页面或人工告知为准。"},
    {"id": "SP-02", "title": "物流时效", "auto": "no",
     "keywords": ["时效", "次日达", "几天能到", "多久能到", "什么时候到", "预计送达", "送达"],
     "policy": "顺丰次日达仅限现货、13:00 前付款且地址在覆盖范围；普通快递 3-5 个工作日。时效属承诺性内容，须人工核实后回复。"},
    {"id": "SP-03", "title": "运费规则", "auto": "yes",
     "keywords": ["运费", "包邮", "邮费"],
     "policy": "满 99 元包邮（特价/秒杀除外，以结算页为准）；未满收取 12 元运费；偏远地区以结算页为准。"},
    {"id": "SP-04", "title": "特殊尺寸/大件", "auto": "no",
     "keywords": ["尺寸", "超重", "超长", "大件", "异形", "体积重", "特殊规格"],
     "policy": "超长（>1.2m）/超重（>10kg）/异形/易碎件运费需单独核算，以客服人工报价为准，系统不得自动报价。"},
    {"id": "SP-05", "title": "价格例外", "auto": "no",
     "keywords": ["内部价", "员工价", "专属价", "议价", "补差价", "差价", "便宜", "贵"],
     "policy": "公开价目以官网页面为准；渠道价/内部价/员工价/专属价需人工确认；差价补偿按售后政策逐单审核，不接受自动承诺。"},
]


class Handler(BaseHTTPRequestHandler):
    server_version = "DemoServer"
    sys_version = ""

    def log_message(self, fmt, *args):  # quieter logs
        sys.stderr.write("  %s\n" % (fmt % args))

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                html = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        elif self.path == "/api/kb":
            self._send(200, {"ok": True, "kb": SHIPPING_KB})
        else:
            self._send(404, {"error": "not found"})

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            length = -1
        if length < 0 or length > MAX_BODY:
            self._send(400, {"error": "bad request: invalid or oversized body"})
            return None
        try:
            self.connection.settimeout(READ_TIMEOUT)
            raw = self.rfile.read(length)
        except Exception:  # noqa: BLE001
            self._send(400, {"error": "bad request: body read failed"})
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:  # noqa: BLE001
            self._send(400, {"error": "bad json"})
            return None

    def do_POST(self):
        if self.path != "/api/evaluate":
            self._send(404, {"error": "not found"})
            return
        payload = self._read_body()
        if payload is None:
            return
        try:
            result = evaluate_risk(
                payload.get("query", ""),
                payload.get("answer", ""),
                payload.get("context"),
            )
            self._send(200, {"ok": True, "result": result})
        except Exception as e:  # noqa: BLE001
            sys.stderr.write("  eval error: %s\n" % e)
            self._send(500, {"ok": False, "error": "internal error"})


if __name__ == "__main__":
    print(f"Demo server v1.3.0: http://127.0.0.1:{PORT}  (evaluator: {SCRIPTS})")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
