#!/usr/bin/env python3
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = os.environ.get("MOCK_TELEGRAM_HOST", "127.0.0.1")
PORT = int(os.environ.get("MOCK_TELEGRAM_PORT", "18080"))
COUNT_FILE = Path(os.environ.get("MOCK_TELEGRAM_COUNT_FILE", "/tmp/mock-telegram-send-count"))


def next_count() -> int:
    try:
        value = int(COUNT_FILE.read_text().strip())
    except Exception:
        value = 0
    value += 1
    COUNT_FILE.write_text(str(value))
    return value


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def do_POST(self):
        if not self.path.endswith("/sendMessage"):
            self._json(404, {"ok": False, "description": "Not Found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "description": "Bad JSON"})
            return

        count = next_count()
        text = str(payload.get("text", ""))
        if "[SLOW]" in text:
            time.sleep(0.6)
        if "[FAIL]" in text:
            self._json(400, {"ok": False, "error_code": 400, "description": "CI forced provider rejection"})
            return

        self._json(200, {
            "ok": True,
            "result": {
                "message_id": 9000 + count,
                "date": int(time.time()),
                "chat": {"id": payload.get("chat_id"), "type": "private"},
                "text": text,
            },
        })


if __name__ == "__main__":
    COUNT_FILE.write_text("0")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
