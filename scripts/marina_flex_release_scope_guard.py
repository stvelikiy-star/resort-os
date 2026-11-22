#!/usr/bin/env python3
"""MARINA FLEX integrated candidate scope audit, independent of November release freeze.

Fail-closed: this is NOT a replacement for release-rc-truth. It verifies
that the accumulated FLEX candidate adds only isolated commercial files and
does not overwrite any existing MARINA SMART PMS application, schema or CI.
"""
from __future__ import annotations

import re
import subprocess
import sys

FROZEN_MAIN = "2642eedc27431fdb9eaa9f7bf306904d487f4b9c"

SAFE_PATHS = (
    re.compile(r"^docs/flex/[A-Za-z0-9_./-]+$"),
    # New isolated commercial UI; explicit file set, no changes to existing admin/PMS.
    re.compile(r"^apps/flex-console/(?:README\.md|package\.json|server\.mjs|public/(?:index\.html|app\.js|styles\.css)|test/(?:security|onboarding-e2e)\.test\.mjs)$"),
    re.compile(r"^scripts/marina_flex_[A-Za-z0-9_.-]+$"),
    re.compile(r"^services/api/app/flex_[A-Za-z0-9_]+\.py$"),
    re.compile(r"^services/api/requirements-flex-control\.txt$"),
    re.compile(r"^\.github/workflows/marina-flex-[A-Za-z0-9_-]+\.yml$"),
)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, text=True,
                          capture_output=True).stdout.strip()


def safe_file(path: str, status: str) -> bool:
    # No deletes, renames, edits to old files or symlinks in the new module.
    return status == "A" and ".." not in path.split("/") and any(
        regex.fullmatch(path) for regex in SAFE_PATHS
    )


def run() -> int:
    if sys.argv[1:] == ["--self-test"]:
        assert safe_file("docs/flex/sql/0010_flex_partner_earnings_preview.sql", "A")
        assert safe_file("apps/flex-console/server.mjs", "A")
        assert safe_file("apps/flex-console/public/index.html", "A")
        assert safe_file("apps/flex-console/test/onboarding-e2e.test.mjs", "A")
        assert not safe_file("apps/admin/app/page.tsx", "A")
        assert not safe_file("apps/flex-console/.env", "A")
        assert not safe_file("apps/flex-console/server.mjs", "M")
        assert safe_file("services/api/app/flex_renewal.py", "A")
        assert safe_file(".github/workflows/marina-flex-integration-ci.yml", "A")
        assert not safe_file("services/api/app/main.py", "M")
        assert not safe_file("packages/database/prisma/schema.prisma", "A")
        assert not safe_file("docs/flex/../../secrets.txt", "A")
        assert not safe_file(".github/workflows/release-rc-truth-ci.yml", "A")
        assert not safe_file("docs/flex/old.txt", "D")
        print("PASS: isolated FLEX candidate scope guard self-test")
        return 0
    if len(sys.argv) != 1:
        print("FAIL: unexpected arguments", file=sys.stderr)
        return 2

    try:
        _git("cat-file", "-e", FROZEN_MAIN + "^{commit}")
        _git("merge-base", "--is-ancestor", FROZEN_MAIN, "HEAD")
        status_lines = _git(
            "diff", "--name-status", "--no-renames", FROZEN_MAIN, "HEAD"
        ).splitlines()
        if not status_lines:
            raise ValueError("No FLEX candidate files present")
        changed = []
        for line in status_lines:
            status, _, path = line.partition("\t")
            if not path or not safe_file(path, status):
                raise ValueError(f"Forbidden baseline change: {line}")
            mode = _git("ls-tree", "HEAD", "--", path).split(maxsplit=1)[0]
            if mode != "100644":
                raise ValueError(f"Unsafe executable/symlink file mode: {path}")
            changed.append(path)
        if "docs/flex/sql/0010_flex_partner_earnings_preview.sql" not in changed:
            raise ValueError("Missing complete ten-layer commercial migration candidate")
        if "scripts/marina_flex_release_scope_guard.py" not in changed:
            raise ValueError("Missing scope enforcement")
        print("PASS: candidate is strictly additive and contains " +
              str(len(changed)) + " isolated FLEX-only files")
        print("FACT: frozen operational main ancestor " + FROZEN_MAIN)
        print("FACT: November Release RC Truth remains a separate mandatory blocker")
        print("FACT: PMS binaries, existing schema and user records are untouched by this diff")
        print("NO-GO: production migration, billing activation and bank payments not approved")
    except (ValueError, subprocess.CalledProcessError, OSError) as exc:
        print("FAIL: MARINA FLEX release scope is unsafe: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
