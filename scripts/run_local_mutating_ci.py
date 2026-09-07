#!/usr/bin/env python3
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_TARGETS = {
    "verify_guest_os_core.py",
    "verify_owner_intelligence.py",
    "verify_owner_growth_control.py",
    "verify_pms_resize_financial_invariants.py",
}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def require_local_url(name: str, value: str) -> None:
    parsed = urlparse(value)
    if parsed.hostname not in LOCAL_HOSTS:
        fail(f"{name} must target localhost for mutating CI; got host={parsed.hostname!r}")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: run_local_mutating_ci.py <approved-verifier.py>")

    app_env = os.environ.get("APP_ENV", "").strip().lower()
    if app_env not in {"ci", "test"}:
        fail("mutating CI runner requires explicit APP_ENV=ci|test")

    target_name = Path(sys.argv[1]).name
    if target_name not in ALLOWED_TARGETS:
        fail(f"target is not allowlisted: {target_name}")

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        fail("DATABASE_URL must be explicitly configured")
    require_local_url("DATABASE_URL", database_url)

    core_url = (
        os.environ.get("RESORT_CORE_TEST_URL")
        or os.environ.get("CORE_API_URL")
        or ""
    ).strip()
    if not core_url:
        fail("RESORT_CORE_TEST_URL or CORE_API_URL must be explicitly configured")
    require_local_url("Core URL", core_url)

    if not os.environ.get("BOOTSTRAP_OWNER_USERNAME", "").strip():
        fail("BOOTSTRAP_OWNER_USERNAME must be explicitly configured")
    if not os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "").strip():
        fail("BOOTSTRAP_OWNER_PASSWORD must be explicitly configured")

    target = Path(__file__).resolve().parent / target_name
    if not target.is_file():
        fail(f"approved verifier does not exist: {target}")

    print(
        f"PASS: local mutating CI boundary env={app_env} "
        f"db={urlparse(database_url).hostname} core={urlparse(core_url).hostname} target={target_name}"
    )
    sys.argv = [str(target)]
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
