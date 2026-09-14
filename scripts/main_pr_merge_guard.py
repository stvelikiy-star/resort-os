#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys

MERGE_MESSAGE_RE = re.compile(r"^Merge PR #(\d+):\s+.+")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    print("RESULT: MAIN PR MERGE GUARD RED")
    return 1


def main() -> int:
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
    match = MERGE_MESSAGE_RE.match(first_line)
    if not match:
        return fail(f"main merge commit message is not canonical PR merge form: {first_line!r}")

    print(f"FACT: main_head={head}")
    print(f"FACT: pull_request_number={match.group(1)}")
    print(f"FACT: parent_count={len(parents) - 1}")
    print("RESULT: MAIN PR MERGE GUARD GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
