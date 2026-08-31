#!/usr/bin/env python3
"""Fail closed when public pages reference known-corrupt media placeholders.

Binary replacement is intentionally separate from factual/public copy. Until the
owner-approved media pack is materialized into Git, public surfaces must use only
repository assets whose signatures are verifiably valid.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps/web"
VERIFIED_FALLBACK = WEB / "public/media/three-crowns/hero-resort.webp"
PUBLIC_SOURCE_FILES = [
    WEB / "app/page.tsx",
    WEB / "app/layout.tsx",
    WEB / "app/rooms/page.tsx",
    WEB / "app/rooms/[slug]/page.tsx",
    WEB / "components/SiteHeader.tsx",
]

KNOWN_CORRUPT_PUBLIC_PATHS = [
    "/media/three-crowns/room-double.webp",
    "/media/three-crowns/lake-night.webp",
    "/media/three-crowns/hero-resort.mp4",
    "/media/three-crowns/territory.mp4",
    "/media/three-crowns/lake.mp4",
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
        errors.append("home page must not request repository video placeholders until valid MP4 binaries are materialized")

    rooms = (WEB / "app/rooms/page.tsx").read_text(encoding="utf-8")
    detail = (WEB / "app/rooms/[slug]/page.tsx").read_text(encoding="utf-8")
    for label, text in [("rooms index", rooms), ("room detail", detail)]:
        if 'const ROOM_MEDIA_FALLBACK = "/media/three-crowns/hero-resort.webp"' not in text:
            errors.append(f"{label} is not pinned to the verified fallback while exact category media is pending")

    print("Three Crowns public media integrity guard")
    print(f"FACT: verified_fallback_webp={valid_webp(VERIFIED_FALLBACK)}")
    print(f"FACT: protected_public_sources={len(PUBLIC_SOURCE_FILES)}")
    print(f"FACT: known_corrupt_paths={len(KNOWN_CORRUPT_PUBLIC_PATHS)}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: PUBLIC MEDIA INTEGRITY DRIFT")
        return 1

    print("PASS: public surfaces do not reference known-corrupt media placeholders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
