#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import ssl
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

EXPECTED_HOSTS = {
    "public": "3korony.com",
    "core": "api.3korony.com",
    "admin": "admin.3korony.com",
    "staff": "staff.3korony.com",
}
EXPECTED_WSS_HOST = "api.3korony.com"
EXPECTED_WSS_PATH = "/ws/pms/grid"


@dataclass(frozen=True)
class Targets:
    public_url: str
    core_url: str
    admin_url: str
    staff_url: str
    wss_url: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_https_base(label: str, value: str, expected_host: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname != expected_host:
        raise ValueError(f"{label} must be https://{expected_host}")
    if parsed.username or parsed.password:
        raise ValueError(f"{label} must not contain credentials")
    if parsed.port not in (None, 443):
        raise ValueError(f"{label} must use default HTTPS port 443")
    if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
        raise ValueError(f"{label} must be a bare HTTPS origin")
    return f"https://{expected_host}"


def validate_wss(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "wss" or parsed.hostname != EXPECTED_WSS_HOST:
        raise ValueError(f"wss_url must use wss://{EXPECTED_WSS_HOST}{EXPECTED_WSS_PATH}")
    if parsed.username or parsed.password:
        raise ValueError("wss_url must not contain credentials")
    if parsed.port not in (None, 443):
        raise ValueError("wss_url must use default WSS port 443")
    if parsed.path != EXPECTED_WSS_PATH or parsed.params or parsed.query or parsed.fragment:
        raise ValueError(f"wss_url path must be exactly {EXPECTED_WSS_PATH}")
    return f"wss://{EXPECTED_WSS_HOST}{EXPECTED_WSS_PATH}"


def validate_targets(targets: Targets) -> Targets:
    return Targets(
        public_url=validate_https_base("public_url", targets.public_url, EXPECTED_HOSTS["public"]),
        core_url=validate_https_base("core_url", targets.core_url, EXPECTED_HOSTS["core"]),
        admin_url=validate_https_base("admin_url", targets.admin_url, EXPECTED_HOSTS["admin"]),
        staff_url=validate_https_base("staff_url", targets.staff_url, EXPECTED_HOSTS["staff"]),
        wss_url=validate_wss(targets.wss_url),
    )


def check_http(url: str, timeout: float) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": "three-crowns-production-probe/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = int(response.status)
    if not 200 <= status < 300:
        raise RuntimeError(f"unexpected HTTP status {status} for {url}")
    return status


def parse_http_status_line(data: bytes) -> int:
    first = data.split(b"\r\n", 1)[0].decode("ascii", "replace")
    parts = first.split()
    if len(parts) < 2 or not parts[1].isdigit():
        raise ValueError(f"invalid HTTP status line: {first!r}")
    return int(parts[1])


def check_wss(url: str, timeout: float) -> int:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or 443
    path = parsed.path or "/"
    context = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as raw:
        with context.wrap_socket(raw, server_hostname=host) as tls:
            tls.settimeout(timeout)
            request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                "Connection: Upgrade\r\n"
                "Upgrade: websocket\r\n"
                "Sec-WebSocket-Version: 13\r\n"
                "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
                "Origin: https://admin.3korony.com\r\n"
                "User-Agent: three-crowns-production-probe/1\r\n"
                "\r\n"
            ).encode("ascii")
            tls.sendall(request)
            response = tls.recv(4096)
    status = parse_http_status_line(response)
    if status not in {101, 401, 403}:
        raise RuntimeError(f"unexpected WSS handshake HTTP status {status}")
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only production HTTPS/WSS probe for canonical Three Crowns hostnames")
    parser.add_argument("--public-url", required=True)
    parser.add_argument("--core-url", required=True)
    parser.add_argument("--admin-url", required=True)
    parser.add_argument("--staff-url", required=True)
    parser.add_argument("--wss-url", required=True)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.timeout <= 0:
        print("FAIL: timeout must be positive")
        print("RESULT: PRODUCTION_ENDPOINT_PROBE_RED")
        return 2

    try:
        targets = validate_targets(
            Targets(
                public_url=args.public_url,
                core_url=args.core_url,
                admin_url=args.admin_url,
                staff_url=args.staff_url,
                wss_url=args.wss_url,
            )
        )
        results = {
            "core_ready": check_http(f"{targets.core_url}/health/ready", args.timeout),
            "public": check_http(f"{targets.public_url}/", args.timeout),
            "admin": check_http(f"{targets.admin_url}/", args.timeout),
            "staff": check_http(f"{targets.staff_url}/", args.timeout),
            "wss": check_wss(targets.wss_url, args.timeout),
        }
    except Exception as exc:
        print(f"FAIL: production endpoint probe: {type(exc).__name__}: {exc}")
        print("RESULT: PRODUCTION_ENDPOINT_PROBE_RED")
        return 1

    evidence = {
        "schema_version": 1,
        "kind": "THREE_CROWNS_PRODUCTION_ENDPOINT_PROBE",
        "status": "VERIFIED",
        "verified_at": utc_now(),
        "targets": {
            "public_url": targets.public_url,
            "core_url": targets.core_url,
            "admin_url": targets.admin_url,
            "staff_url": targets.staff_url,
            "wss_url": targets.wss_url,
        },
        "results": results,
        "safety": {
            "read_only": True,
            "changes_dns": False,
            "mutates_business_data": False,
            "activates_providers": False,
            "contains_credentials": False,
        },
    }
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PRODUCTION_ENDPOINT_EVIDENCE={output}")

    for name, status in results.items():
        print(f"FACT: {name}_http_status={status}")
    print("RESULT: PRODUCTION_ENDPOINT_PROBE_GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
