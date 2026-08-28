#!/usr/bin/env python3
"""Non-destructive external acceptance probe for the deployed Three Crowns public site.

This does not mutate DNS, hosting, files or database state. It is intended to be
run against an isolated HTTPS staging URL (and again after controlled cutover)
to prove that the rendered public surface preserves the canonical V1 sales truth.
"""
from __future__ import annotations

import argparse
import html
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from public_site_truth_guard import FORBIDDEN_PATTERNS

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
REQUIRED_RENDERED_SNIPPETS = (
    "Собственный пляж",
    "Пирс длиной 150 метров",
    "Номер автоматически не блокируется",
    "Заявка ещё не является подтверждённой бронью",
)


@dataclass(frozen=True)
class ProbeResult:
    url: str
    status: int
    bytes_read: int
    errors: tuple[str, ...]


def validate_target(url: str, *, allow_http: bool = False) -> None:
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError("target URL must contain a hostname")
    if parsed.username or parsed.password:
        raise ValueError("credentials in target URL are forbidden")
    allowed = {"https"} | ({"http"} if allow_http else set())
    if parsed.scheme not in allowed:
        expected = "https" if not allow_http else "http/https"
        raise ValueError(f"target URL must use {expected}")


def analyze_rendered_html(text: str) -> list[str]:
    decoded = html.unescape(text)
    errors: list[str] = []

    for label, pattern in FORBIDDEN_PATTERNS.items():
        if pattern.search(decoded):
            errors.append(f"forbidden public claim: {label}")

    for snippet in REQUIRED_RENDERED_SNIPPETS:
        if snippet not in decoded:
            errors.append(f"missing required rendered truth: {snippet!r}")

    return errors


def fetch_html(url: str, timeout: float) -> tuple[int, bytes]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Three-Crowns-Resort-OS-External-Truth-Probe/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = int(getattr(response, "status", 200))
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError(f"unexpected content type: {content_type}")
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
        return status, body


def probe(url: str, *, timeout: float = 15.0, allow_http: bool = False) -> ProbeResult:
    validate_target(url, allow_http=allow_http)
    status, body = fetch_html(url, timeout)
    if status != 200:
        return ProbeResult(url=url, status=status, bytes_read=len(body), errors=(f"HTTP status {status}",))
    text = body.decode("utf-8", errors="replace")
    return ProbeResult(url=url, status=status, bytes_read=len(body), errors=tuple(analyze_rendered_html(text)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify rendered Three Crowns public truth on external staging")
    parser.add_argument("url", help="HTTPS staging/public URL, e.g. https://staging.3korony.com/")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--allow-http", action="store_true", help="Only for isolated local/non-production diagnostics")
    args = parser.parse_args(argv)

    print("Three Crowns external public truth probe")
    print(f"FACT: target={args.url}")
    try:
        result = probe(args.url, timeout=args.timeout, allow_http=args.allow_http)
    except (ValueError, urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"FAIL: probe error: {exc}")
        print("RESULT: BLOCKED / EXTERNAL PUBLIC TRUTH NOT VERIFIED")
        return 2

    print(f"FACT: http_status={result.status}")
    print(f"FACT: bytes_read={result.bytes_read}")
    if result.errors:
        for error in result.errors:
            print(f"FAIL: {error}")
        print("RESULT: EXTERNAL PUBLIC TRUTH DRIFT")
        return 1

    print("PASS: rendered external site matches the protected Three Crowns V1 public boundary")
    print("RESULT: EXTERNAL PUBLIC TRUTH VERIFIED FOR THIS URL/RESPONSE ONLY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
