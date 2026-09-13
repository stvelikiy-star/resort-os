#!/usr/bin/env python3
"""Ensure every current Admin/PMS navigation tab has RU/KG/EN coverage."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "apps/admin/components/AdminShell.tsx"
COVERAGE = ROOT / "apps/admin/components/AdminNavLocaleCoverage.tsx"
LAYOUT = ROOT / "apps/admin/app/layout.tsx"


def main() -> int:
    shell = SHELL.read_text(encoding="utf-8")
    coverage = COVERAGE.read_text(encoding="utf-8")
    layout = LAYOUT.read_text(encoding="utf-8")

    nav_labels = set(re.findall(r'setTab\("[A-Z_]+"\).*?>([^<]+)</button>', shell))
    translated_ru = set(re.findall(r'\{ ru: "([^"]+)", kg: "[^"]+", en: "[^"]+" \}', coverage))

    missing = sorted(nav_labels - translated_ru)
    if missing:
        raise AssertionError(f"Admin navigation labels missing RU/KG/EN coverage: {missing}")
    if len(nav_labels) < 20:
        raise AssertionError(f"Unexpectedly small Admin navigation surface: {len(nav_labels)} tabs")
    if "<AdminNavLocaleCoverage />" not in layout:
        raise AssertionError("AdminNavLocaleCoverage is not mounted in admin layout")
    if 'const STORAGE_KEY = "three-crowns-admin-locale"' not in coverage:
        raise AssertionError("Admin navigation locale coverage is not synchronized with the canonical locale key")

    print(f"ADMIN_NAV_I18N_PASS tabs={len(nav_labels)} translated={len(nav_labels)} locales=ru,kg,en")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"ADMIN_NAV_I18N_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1)
