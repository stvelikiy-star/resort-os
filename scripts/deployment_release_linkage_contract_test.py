#!/usr/bin/env python3
from __future__ import annotations

from deployment_release_linkage import REQUIRED_SERVICES, validate_release_linkage

GOOD_SHA = "0123456789abcdef0123456789abcdef01234567"
OTHER_SHA = "89abcdef0123456789abcdef0123456789abcdef"


def rows(revision: str = GOOD_SHA):
    return [
        {
            "service": service,
            "state": "running",
            "image_id": f"sha256:{index + 1:064x}",
            "revision": revision,
        }
        for index, service in enumerate(REQUIRED_SERVICES)
    ]


def expect_red(label: str, errors: list[str], needle: str):
    assert errors, f"{label}: expected failure"
    assert any(needle in item for item in errors), f"{label}: missing {needle!r}: {errors}"


def main() -> int:
    clean = validate_release_linkage(
        expected_sha=GOOD_SHA,
        source_sha=GOOD_SHA,
        source_dirty=False,
        services=rows(),
    )
    assert clean == [], clean

    expect_red(
        "source mismatch",
        validate_release_linkage(
            expected_sha=GOOD_SHA,
            source_sha=OTHER_SHA,
            source_dirty=False,
            services=rows(),
        ),
        "source checkout SHA mismatch",
    )
    expect_red(
        "dirty source",
        validate_release_linkage(
            expected_sha=GOOD_SHA,
            source_sha=GOOD_SHA,
            source_dirty=True,
            services=rows(),
        ),
        "source checkout is dirty",
    )

    missing = rows()
    missing.pop()
    expect_red(
        "missing service",
        validate_release_linkage(
            expected_sha=GOOD_SHA,
            source_sha=GOOD_SHA,
            source_dirty=False,
            services=missing,
        ),
        "required deployed service missing",
    )

    no_image = rows()
    no_image[0]["image_id"] = ""
    expect_red(
        "missing image id",
        validate_release_linkage(
            expected_sha=GOOD_SHA,
            source_sha=GOOD_SHA,
            source_dirty=False,
            services=no_image,
        ),
        "image id missing",
    )

    missing_label = rows()
    missing_label[1]["revision"] = ""
    expect_red(
        "missing revision",
        validate_release_linkage(
            expected_sha=GOOD_SHA,
            source_sha=GOOD_SHA,
            source_dirty=False,
            services=missing_label,
        ),
        "revision label missing",
    )

    wrong_label = rows()
    wrong_label[2]["revision"] = OTHER_SHA
    expect_red(
        "revision mismatch",
        validate_release_linkage(
            expected_sha=GOOD_SHA,
            source_sha=GOOD_SHA,
            source_dirty=False,
            services=wrong_label,
        ),
        "revision mismatch",
    )

    stopped = rows()
    stopped[3]["state"] = "exited"
    expect_red(
        "stopped service",
        validate_release_linkage(
            expected_sha=GOOD_SHA,
            source_sha=GOOD_SHA,
            source_dirty=False,
            services=stopped,
        ),
        "not running",
    )

    expect_red(
        "invalid expected SHA",
        validate_release_linkage(
            expected_sha="main",
            source_sha=GOOD_SHA,
            source_dirty=False,
            services=rows(),
        ),
        "40-character hexadecimal",
    )

    print("PASS: deployment release linkage adversarial contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
