#!/usr/bin/env python3
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = os.environ.get("MOCK_STAFF_VOICE_HOST", "127.0.0.1")
PORT = int(os.environ.get("MOCK_STAFF_VOICE_PORT", "18082"))
TELEGRAM_COUNT = Path("/tmp/mock-staff-telegram-count")
TRANSCRIBE_COUNT = Path("/tmp/mock-staff-transcribe-count")


def bump(path: Path) -> int:
    try:
        value = int(path.read_text().strip())
    except Exception:
        value = 0
    value += 1
    path.write_text(str(value))
    return value


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def _json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)

        if self.path.endswith("/getFile"):
            bump(TELEGRAM_COUNT)
            try:
                payload = json.loads(body or b"{}")
            except json.JSONDecodeError:
                self._json(400, {"ok": False, "description": "bad json"})
                return
            file_id = str(payload.get("file_id", ""))
            mapping = {
                "voice-214": "voice/214.ogg",
                "voice-floor1": "voice/floor1.ogg",
            }
            file_path = mapping.get(file_id)
            if not file_path:
                self._json(400, {"ok": False, "description": "unknown file"})
                return
            self._json(200, {"ok": True, "result": {"file_id": file_id, "file_unique_id": file_id, "file_size": 8, "file_path": file_path}})
            return

        if self.path == "/v1/audio/transcriptions":
            bump(TRANSCRIBE_COUNT)
            if b"VOICE214" in body:
                text = "В номере 214 течет смеситель, нужно посмотреть."
            elif b"FLOORONE" in body:
                text = "На 1 этаже возле лестницы проблема с освещением."
            else:
                self._json(422, {"error": {"message": "unknown mock audio"}})
                return
            self._json(200, {"text": text})
            return

        self._json(404, {"error": {"message": "not found"}})

    def do_GET(self):
        if self.path.endswith("/voice/214.ogg"):
            body = b"VOICE214"
        elif self.path.endswith("/voice/floor1.ogg"):
            body = b"FLOORONE"
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "audio/ogg")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    TELEGRAM_COUNT.write_text("0")
    TRANSCRIBE_COUNT.write_text("0")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
