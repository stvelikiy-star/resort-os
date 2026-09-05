#!/usr/bin/env python3
"""One-command staging gate for the Three Crowns integration branch."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, script: str) -> None:
    print(f"\n== {label} ==")
    subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, env=dict(os.environ), check=True)


def main() -> int:
    run("Public truth", "scripts/public_site_truth_guard.py")
    run("Public RU/KG/EN", "scripts/public_i18n_guard.py")
    run("Full staging acceptance", "scripts/staging_acceptance.py")
    print("\nTHREE CROWNS STAGING FULL GATE PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"\nTHREE CROWNS STAGING FULL GATE FAILED: exit={exc.returncode}", file=sys.stderr)
        raise
