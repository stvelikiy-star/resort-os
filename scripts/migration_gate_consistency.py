#!/usr/bin/env python3
"""Detect stale exact migration-ledger assertions in GitHub Actions.

The project intentionally uses exact migration counts/names as deployment gates.
That is useful only when every gate moves with the shared release contract. This
script scans workflow YAML for common exact assertions and fails when an obsolete
ledger is still hard-coded after a forward migration.
"""
from __future__ import annotations

import re
from pathlib import Path

from release_contract import EXPECTED_MIGRATIONS

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
EXPECTED_COUNT = len(EXPECTED_MIGRATIONS)
EXPECTED_CSV = ",".join(EXPECTED_MIGRATIONS)

COUNT_PATTERNS = (
    re.compile(r"test\s+\"\$migration_count\"\s*=\s*'(?P<n>\d+)'"),
    re.compile(r"applied_migrations=(?P<n>\d+)"),
    re.compile(r"BACKUP_MIGRATIONS=(?P<n>\d+)"),
    re.compile(r"RESTORED_APPLIED_MIGRATIONS=(?P<n>\d+)"),
)


def main() -> int:
    stale: list[str] = []
    checked = 0
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if "_prisma_migrations" not in text and "applied_migrations=" not in text and "BACKUP_MIGRATIONS=" not in text:
            continue
        checked += 1
        for pattern in COUNT_PATTERNS:
            for match in pattern.finditer(text):
                value = int(match.group("n"))
                if value != EXPECTED_COUNT:
                    stale.append(f"{path.relative_to(ROOT)}: stale migration count {value}, expected {EXPECTED_COUNT}")
        # Any exact CSV assertion that begins at 0_init must match the release ledger.
        for match in re.finditer(r"0_init,1_site_content,[A-Za-z0-9_,_-]+", text):
            value = match.group(0)
            if value != EXPECTED_CSV:
                stale.append(f"{path.relative_to(ROOT)}: stale migration names {value}")

    if stale:
        print("MIGRATION_GATE_CONSISTENCY=FAIL")
        for item in sorted(set(stale)):
            print(item)
        return 1

    print("MIGRATION_GATE_CONSISTENCY=PASS")
    print(f"expected_migrations={EXPECTED_COUNT} checked_workflows={checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
