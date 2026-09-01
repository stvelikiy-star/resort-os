#!/usr/bin/env python3
"""Fail-closed wrapper for the mutating Three Crowns staging acceptance smoke."""
from __future__ import annotations

import os
import sys
import urllib.parse

MUTATION_ACK = "I_UNDERSTAND_SYNTHETIC_WRITES"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def validate_staging_mutation_target(*, app_env: str, base_url: str, mutation_ack: str) -> list[str]:
    errors: list[str] = []
    if app_env.strip().lower() != "staging":
        errors.append("APP_ENV must be exactly staging")

    parsed = urllib.parse.urlparse(base_url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not hostname:
        errors.append("CORE_API_URL must be an http/https URL with a hostname")
    elif hostname not in LOOPBACK_HOSTS and "staging" not in hostname:
        errors.append("non-loopback CORE_API_URL hostname must explicitly contain staging")

    if mutation_ack != MUTATION_ACK:
        errors.append("STAGING_ACCEPTANCE_MUTATIONS explicit opt-in is missing")
    return errors


def runtime_mutation_ack(base_url: str) -> str:
    explicit = os.environ.get("STAGING_ACCEPTANCE_MUTATIONS", "")
    if explicit:
        return explicit

    parsed = urllib.parse.urlparse(base_url)
    hostname = (parsed.hostname or "").lower()
    trusted_ci_loopback = (
        os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"
        and hostname in LOOPBACK_HOSTS
    )
    return MUTATION_ACK if trusted_ci_loopback else ""


def require_safe_staging_target(base_url: str) -> None:
    errors = validate_staging_mutation_target(
        app_env=os.environ.get("APP_ENV", ""),
        base_url=base_url,
        mutation_ack=runtime_mutation_ack(base_url),
    )
    if errors:
        raise RuntimeError("Unsafe staging acceptance target: " + "; ".join(errors))
    print(f"PASS: staging mutation safety guard · target={base_url}")


def main() -> int:
    base_url = os.environ.get("CORE_API_URL", "http://127.0.0.1:18000").rstrip("/")
    require_safe_staging_target(base_url)

    # Import only after the mutation gate is green. The preserved implementation
    # performs the synthetic CRM/task/room-state lifecycle against the target.
    from staging_acceptance_impl import main as smoke_main

    return smoke_main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"STAGING ACCEPTANCE FAILED: {exc}", file=sys.stderr)
        raise
