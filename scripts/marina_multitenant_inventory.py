#!/usr/bin/env python3
"""Inventory multi-tenant migration risks without changing the application.

This is intentionally report-only. It does not connect to a database, edit files,
or change runtime behavior. It provides a repeatable baseline before tenant
schema/auth work is introduced.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = [ROOT / "services" / "api" / "app", ROOT / "scripts"]
PATTERNS = {
    "deployment_global_property_code": re.compile(r"PROPERTY_CODE"),
    "property_lookup_by_code": re.compile(r"properties\s+WHERE\s+code|FROM\s+properties\s+WHERE\s+code", re.I),
    "client_supplied_tenant_header": re.compile(r"X-Tenant-Id|X-Property-Id|X-User-Id|X-Role"),
    "property_context_from_session": re.compile(r'property_code'),
}


def iter_files():
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        yield from sorted(root.rglob("*.py"))


def main() -> int:
    counts = {name: 0 for name in PATTERNS}
    findings: list[tuple[str, int, str, str]] = []

    for path in iter_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    counts[name] += 1
                    findings.append((name, line_no, str(path.relative_to(ROOT)), line.strip()))

    print("MARINA SMART multi-tenant inventory (report-only)")
    for name, count in counts.items():
        print(f"- {name}: {count}")

    for name, line_no, path, line in findings:
        print(f"{name}\t{path}:{line_no}\t{line}")

    print("No files or databases were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
