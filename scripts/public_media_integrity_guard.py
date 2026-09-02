#!/usr/bin/env python3
"""Fail closed when public pages reference corrupt or unapproved media.

General resort imagery may be materialized only from the owner-approved media
registry. Exact room-category media remains a separate public-binding decision;
room catalogue/detail surfaces therefore keep the verified generic resort
fallback until that authority exists.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps/web"
VERIFIED_FALLBACK = WEB / "public/media/three-crowns/hero-resort.webp"
POLISH_CSS = WEB / "app/public-site-polish-20260902.css"

APPROVED_PUBLIC_GENERAL_MEDIA = [
    WEB / "public/media/three-crowns/approved/territory/beach-mountains.webp",
    WEB / "public/media/three-crowns/approved/territory/pier-front.webp",
    WEB / "public/media/three-crowns/approved/territory/pool.webp",
]

PUBLIC_SOURCE_FILES = [
    WEB / "app/page.tsx",
    WEB / "app/layout.tsx",
    WEB / "app/rooms/page.tsx",
    WEB / "app/rooms/[slug]/page.tsx",
    WEB / "components/SiteHeader.tsx",
    POLISH_CSS,
]

KNOWN_CORRUPT_PUBLIC_PATHS = [
    "/media/three-crowns/room-double.webp",
    "/media/three-crowns/lake-night.webp",
    "/media/three-crowns/hero-resort.mp4",
    "/media/three-crowns/territory.mp4",
    "/media/three-crowns/lake.mp4",
]

APPROVED_PUBLIC_URLS = [
    "/media/three-crowns/approved/territory/beach-mountains.webp",
    "/media/three-crowns/approved/territory/pier-front.webp",
    "/media/three-crowns/approved/territory/pool.webp",
]


def valid_webp(path: Path) -> bool:
    if not path.is_file():
        return False
    data = path.read_bytes()[:12]
    return len(data) == 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def main() -> int:
    errors: list[str] = []
    if not valid_webp(VERIFIED_FALLBACK):
        errors.append("verified hero-resort.webp fallback is missing or not a valid RIFF/WEBP file")

    for approved in APPROVED_PUBLIC_GENERAL_MEDIA:
        if not valid_webp(approved):
            errors.append(f"approved public general media is missing or invalid WEBP: {approved.relative_to(ROOT)}")

    for path in PUBLIC_SOURCE_FILES:
        if not path.exists():
            errors.append(f"missing public source file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for corrupt in KNOWN_CORRUPT_PUBLIC_PATHS:
            if corrupt in text:
                errors.append(f"{path.relative_to(ROOT)} references known-corrupt media {corrupt}")

    home = (WEB / "app/page.tsx").read_text(encoding="utf-8")
    if 'const VERIFIED_MEDIA_FALLBACK = "/media/three-crowns/hero-resort.webp"' not in home:
        errors.append("home page is not pinned to the verified media fallback")
    if "<source src=" in home:
        errors.append("home page must not request repository video placeholders until valid approved MP4 binaries are materialized")

    rooms = (WEB / "app/rooms/page.tsx").read_text(encoding="utf-8")
    detail = (WEB / "app/rooms/[slug]/page.tsx").read_text(encoding="utf-8")
    for label, text in [("rooms index", rooms), ("room detail", detail)]:
        if 'const ROOM_MEDIA_FALLBACK = "/media/three-crowns/hero-resort.webp"' not in text:
            errors.append(f"{label} is not pinned to the verified fallback while exact category public binding is pending")
        for approved_url in APPROVED_PUBLIC_URLS:
            if approved_url in text:
                errors.append(f"{label} must not reuse general resort imagery as exact room-category media: {approved_url}")

    if not POLISH_CSS.exists():
        errors.append("public-site polish CSS is missing")
    else:
        polish = POLISH_CSS.read_text(encoding="utf-8")
        for approved_url in APPROVED_PUBLIC_URLS:
            if approved_url not in polish:
                errors.append(f"public-site polish must reference approved general media: {approved_url}")

    layout = (WEB / "app/layout.tsx").read_text(encoding="utf-8")
    if 'import "./public-site-polish-20260902.css";' not in layout:
        errors.append("public-site polish CSS is not loaded by the root layout")
    elif layout.rfind('import "./public-site-polish-20260902.css";') < layout.rfind('import "./luxury-director.css";'):
        errors.append("public-site polish CSS must load after luxury-director.css")

    print("Three Crowns public media integrity guard")
    print(f"FACT: verified_fallback_webp={valid_webp(VERIFIED_FALLBACK)}")
    print(f"FACT: approved_general_webp={sum(valid_webp(path) for path in APPROVED_PUBLIC_GENERAL_MEDIA)}/{len(APPROVED_PUBLIC_GENERAL_MEDIA)}")
    print(f"FACT: protected_public_sources={len(PUBLIC_SOURCE_FILES)}")
    print(f"FACT: known_corrupt_paths={len(KNOWN_CORRUPT_PUBLIC_PATHS)}")
    print("FACT: exact_room_category_public_binding=pending")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: PUBLIC MEDIA INTEGRITY DRIFT")
        return 1

    print("PASS: approved general resort media is valid and exact room media remains fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
