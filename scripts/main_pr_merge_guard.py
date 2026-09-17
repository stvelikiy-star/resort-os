#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys

MERGE_MESSAGE_PATTERNS = (
    re.compile(r"^Merge PR #(\d+):\s+.+$"),
    re.compile(r"^Merge pull request #(\d+)(?:\s+from\s+.+)?$"),
    re.compile(r"^.+\s+\(#(\d+)\)$"),
)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    print("RESULT: MAIN PR MERGE GUARD RED")
    return 1


def pull_request_number(first_line: str) -> str | None:
    for pattern in MERGE_MESSAGE_PATTERNS:
        match = pattern.match(first_line)
        if match:
            return match.group(1)
    return None


def verify_message_parser_contract() -> None:
    accepted = {
        "Merge PR #172: feat: full operational launch profile without payments": "172",
        "Merge pull request #174 from stvelikiy-star/release/refreeze-no-payments-20260917": "174",
        "release: refreeze 0.62.2 on FULL_NO_PAYMENTS boundary (#174)": "174",
    }
    rejected = (
        "direct commit on main",
        "release: refreeze 0.62.2 on FULL_NO_PAYMENTS boundary",
        "(#174)",
    )

    for message, expected in accepted.items():
        actual = pull_request_number(message)
        if actual != expected:
            raise AssertionError(f"merge parser rejected canonical PR message: {message!r}")
    for message in rejected:
        if pull_request_number(message) is not None:
            raise AssertionError(f"merge parser accepted non-canonical message: {message!r}")


def main() -> int:
    verify_message_parser_contract()

    ref = os.environ.get("GITHUB_REF", "")
    event = os.environ.get("GITHUB_EVENT_NAME", "")

    # Local/manual validation may run without GitHub event metadata.
    if event and event != "push":
        print(f"SKIP: event={event}; guard is authoritative on push to main")
        return 0
    if ref and ref != "refs/heads/main":
        print(f"SKIP: ref={ref}; guard is authoritative only on main")
        return 0

    head = git("rev-parse", "HEAD")
    parents = git("rev-list", "--parents", "-n", "1", "HEAD").split()
    message = git("log", "-1", "--pretty=%B").strip()

    if len(parents) < 3:
        return fail(f"main head {head} is not a merge commit; direct/squash/rebase push is not accepted")

    first_line = message.splitlines()[0] if message else ""
    pr_number = pull_request_number(first_line)
    if pr_number is None:
        return fail(f"main merge commit message is not canonical PR merge form: {first_line!r}")

    print(f"FACT: main_head={head}")
    print(f"FACT: pull_request_number={pr_number}")
    print(f"FACT: parent_count={len(parents) - 1}")
    print("RESULT: MAIN PR MERGE GUARD GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
