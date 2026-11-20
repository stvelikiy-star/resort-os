#!/usr/bin/env python3
"""Read-only MARINA staging health gate; does not log in or write business data."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

def request(base, path, timeout):
    url = base.rstrip("/") + path
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Invalid URL")
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "marina-staging-readiness/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read(4096).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(4096).decode("utf-8", "replace")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--api", required=True, help="Explicit isolated staging API origin")
    p.add_argument("--web", help="Optional public web origin")
    p.add_argument("--admin", help="Optional admin origin")
    p.add_argument("--staff", help="Optional staff origin")
    p.add_argument("--timeout", type=float, default=8)
    args = p.parse_args()
    if args.timeout <= 0 or args.timeout > 60:
        p.error("timeout must be > 0 and <= 60")
    origins = {"api": args.api, "web": args.web, "admin": args.admin, "staff": args.staff}
    for label, origin in origins.items():
        if not origin:
            continue
        parsed = urllib.parse.urlparse(origin)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            p.error(f"{label}: expected an origin URL, without credentials, path, query or fragment")
        if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            p.error(f"{label}: plaintext HTTP allowed only on localhost")
    checks = [("api_live", "api", "/health/live"), ("api_ready", "api", "/health/ready")]
    checks.extend((f"{label}_root", label, "/") for label in ("web", "admin", "staff") if origins[label])
    results = []
    for name, label, path in checks:
        try:
            status, _ = request(origins[label], path, args.timeout)
            results.append({"check": name, "status": status, "pass": status == 200})
        except (OSError, ValueError, TimeoutError) as exc:
            results.append({"check": name, "status": None, "pass": False, "error": type(exc).__name__})
    print(json.dumps({"all_pass": all(r["pass"] for r in results), "results": results}, indent=2))
    return 0 if all(r["pass"] for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())
