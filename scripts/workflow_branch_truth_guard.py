#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
LEGACY = "integration/site-pms-cms-20260827"
CANONICAL = "main"
EVENTS = {"pull_request", "push"}


def event_blocks(text: str) -> dict[str, list[str]]:
    lines = text.splitlines()
    result: dict[str, list[str]] = {}
    in_on = False
    current: str | None = None
    for line in lines:
        if line == "on:":
            in_on = True
            current = None
            continue
        if not in_on:
            continue
        if line and not line.startswith(" "):
            break
        if line.startswith("  ") and not line.startswith("    ") and line.rstrip().endswith(":"):
            event = line.strip()[:-1]
            current = event if event in EVENTS else None
            if current:
                result.setdefault(current, [])
            continue
        if current:
            result[current].append(line)
    return result


def main() -> None:
    offenders: list[str] = []
    legacy_mentions = 0
    checked = 0
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8")
        blocks = event_blocks(text)
        for event, lines in blocks.items():
            block = "\n".join(lines)
            if LEGACY not in block:
                continue
            legacy_mentions += 1
            canonical_line = f"- {CANONICAL}"
            if canonical_line not in block:
                offenders.append(f"{path.relative_to(ROOT)} :: {event}")
        checked += 1

    if offenders:
        print("FAIL: canonical main CI coverage is missing where legacy integration branch is still targeted:")
        for offender in offenders:
            print(f" - {offender}")
        print(f"FACT: workflows_checked={checked}")
        print(f"FACT: legacy_trigger_mentions={legacy_mentions}")
        raise SystemExit(1)

    print(f"PASS: canonical main CI coverage present in all legacy-targeted push/PR trigger blocks")
    print(f"FACT: workflows_checked={checked}")
    print(f"FACT: legacy_trigger_mentions={legacy_mentions}")


if __name__ == "__main__":
    main()
