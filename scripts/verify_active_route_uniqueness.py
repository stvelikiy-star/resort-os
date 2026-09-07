#!/usr/bin/env python3
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from app.app_entry import app  # noqa: E402


def main() -> int:
    seen: dict[tuple[str, str], list[str]] = defaultdict(list)
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = set(getattr(route, "methods", set()) or set())
        if not path or not path.startswith("/api/"):
            continue
        name = getattr(route, "name", repr(route))
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            seen[(method, path)].append(name)

    duplicates = {
        f"{method} {path}": names
        for (method, path), names in seen.items()
        if len(names) > 1
    }
    if duplicates:
        for key, names in sorted(duplicates.items()):
            print(f"DUPLICATE_ROUTE {key}: {names}", file=sys.stderr)
        raise SystemExit(1)

    expected = {
        ("POST", "/api/v1/kitchen/menu/bootstrap-draft"),
        ("PATCH", "/api/v1/kitchen/menu/{item_id}"),
    }
    missing = [f"{method} {path}" for method, path in expected if (method, path) not in seen]
    if missing:
        print(f"MISSING_CANONICAL_ROUTE: {missing}", file=sys.stderr)
        raise SystemExit(1)

    print(f"ACTIVE_ROUTE_UNIQUENESS_PASS routes={len(seen)}")
    print("Kitchen menu mutations are single-owner routes; authorization cannot depend on router order.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
