#!/usr/bin/env python3
"""Ephemeral Caddy HTTP routing smoke: no real hotel, external host or API."""
from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CADDY = ROOT / "deploy/marina/customer-unpublished.Caddyfile"
HOST = "127.0.0.1"
EDGE_PORT = 18550
API_PORT = 18551


class EchoAPI(BaseHTTPRequestHandler):
    def do_GET(self):
        status = 404 if "unmapped-slug" in self.path else 200
        data = self.path.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass


def fetch(path: str) -> tuple[int, str]:
    req = urllib.request.Request(
        f"http://{HOST}:{EDGE_PORT}{path}",
        headers={"Accept": "text/html"},
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def main():
    assert os.environ.get("CI") == "true", "Only ephemeral GitHub Actions"
    original = CADDY.read_text(encoding="utf-8")
    assert original.count(":3000 {") == 1
    assert "api:8000" in original
    config = original.replace(":3000 {", f"http://{HOST}:{EDGE_PORT} {{")
    config = config.replace("api:8000", f"{HOST}:{API_PORT}")
    server = HTTPServer((HOST, API_PORT), EchoAPI)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    container_name = "marina-customer-routing-" + uuid.uuid4().hex[:10]
    with tempfile.TemporaryDirectory(prefix="marina-customer-caddy-") as directory:
        root = Path(directory)
        (root / "Caddyfile").write_text(config)
        (root / "index.html").write_text("NOT_PUBLISHED_PLACEHOLDER")
        command = [
            "docker", "run", "--rm", "--name", container_name, "--network", "host",
            "-v", f"{root / 'Caddyfile'}:/etc/caddy/Caddyfile:ro",
            "-v", f"{root}:/srv:ro",
            "caddy:2.10.2", "caddy", "run", "--config", "/etc/caddy/Caddyfile",
            "--adapter", "caddyfile",
        ]
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(40):
                if process.poll() is not None:
                    raise AssertionError("Caddy process exited while starting")
                try:
                    status, _ = fetch("/?locale=ru")
                    if status == 200:
                        break
                except (ConnectionError, urllib.error.URLError):
                    pass
                time.sleep(0.25)
            else:
                raise AssertionError("Caddy edge did not start on isolated localhost")

            expected = {
                "/?lang=kg": "/api/v1/site/customer-page?lang=kg",
                "/rooms?lang=en": "/api/v1/site/customer-rooms?lang=en",
                "/rooms/old-standard?lang=ru":
                    "/api/v1/site/customer-room/old-standard?lang=ru",
            }
            for source, destination in expected.items():
                status, body = fetch(source)
                assert (status, body) == (200, destination), (source, status, body)
            status, body = fetch("/rooms/unmapped-slug?lang=ru")
            assert status == 404, (status, body)
            print("CADDY_LEGACY_HOME_ROOMS_DEEP_LINKS_PASS")
        finally:
            subprocess.run(["docker", "rm", "-f", container_name],
                           check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.wait(timeout=10)
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
