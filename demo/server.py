#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo server for risk-human-intervention skill (stdlib only).

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


class Handler(BaseHTTPRequestHandler):
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
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/evaluate":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            self._send(400, {"error": f"bad json: {e}"})
            return
        try:
            result = evaluate_risk(
                payload.get("query", ""),
                payload.get("answer", ""),
                payload.get("context"),
            )
            self._send(200, {"ok": True, "result": result})
        except Exception as e:  # noqa: BLE001
            self._send(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    print(f"Demo server: http://127.0.0.1:{PORT}  (evaluator: {SCRIPTS})")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
