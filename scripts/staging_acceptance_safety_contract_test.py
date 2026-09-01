#!/usr/bin/env python3
from __future__ import annotations

import os

from staging_acceptance import MUTATION_ACK, validate_staging_mutation_target


def expect_green(label: str, *, app_env: str, url: str, ack: str):
    errors = validate_staging_mutation_target(app_env=app_env, base_url=url, mutation_ack=ack)
    assert errors == [], f"{label}: {errors}"


def expect_red(label: str, needle: str, *, app_env: str, url: str, ack: str):
    errors = validate_staging_mutation_target(app_env=app_env, base_url=url, mutation_ack=ack)
    assert errors, f"{label}: expected RED"
    assert any(needle in item for item in errors), f"{label}: missing {needle!r}: {errors}"


def main() -> int:
    expect_green(
        "loopback staging",
        app_env="staging",
        url="http://127.0.0.1:18000",
        ack=MUTATION_ACK,
    )
    expect_green(
        "external staging",
        app_env="staging",
        url="https://api-staging.3korony.com",
        ack=MUTATION_ACK,
    )
    expect_red(
        "production env",
        "APP_ENV must be exactly staging",
        app_env="production",
        url="https://api-staging.3korony.com",
        ack=MUTATION_ACK,
    )
    expect_red(
        "production host",
        "hostname must explicitly contain staging",
        app_env="staging",
        url="https://api.3korony.com",
        ack=MUTATION_ACK,
    )
    expect_red(
        "missing opt-in",
        "explicit opt-in is missing",
        app_env="staging",
        url="https://api-staging.3korony.com",
        ack="",
    )
    expect_red(
        "wrong opt-in",
        "explicit opt-in is missing",
        app_env="staging",
        url="https://api-staging.3korony.com",
        ack="yes",
    )
    expect_red(
        "malformed target",
        "http/https URL",
        app_env="staging",
        url="api-staging.3korony.com",
        ack=MUTATION_ACK,
    )
    expect_red(
        "non-http target",
        "http/https URL",
        app_env="staging",
        url="ftp://api-staging.3korony.com",
        ack=MUTATION_ACK,
    )

    # The pure validator must never inherit CI state implicitly. Trusted CI
    # bypass, if any, belongs to the outer runtime guard and only for loopback.
    old = os.environ.get("GITHUB_ACTIONS")
    os.environ["GITHUB_ACTIONS"] = "true"
    try:
        expect_red(
            "validator still requires explicit ack under CI",
            "explicit opt-in is missing",
            app_env="staging",
            url="http://127.0.0.1:18000",
            ack="",
        )
    finally:
        if old is None:
            os.environ.pop("GITHUB_ACTIONS", None)
        else:
            os.environ["GITHUB_ACTIONS"] = old

    print("PASS: staging acceptance mutation safety adversarial contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
