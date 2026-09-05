#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "apps/admin/app/page.tsx"
SHELL = ROOT / "apps/admin/components/AdminShell.tsx"
GRID_V9 = ROOT / "apps/admin/components/PMSGridV9.tsx"
OWNER_GRID = ROOT / "apps/admin/components/PMSOwnerGrid.tsx"
STAFF_BOARD = ROOT / "apps/admin/components/StaffBoard.tsx"


def require(path: Path, *needles: str) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise AssertionError(f"{path.relative_to(ROOT)} missing required runtime markers: {missing}")


def forbid(path: Path, *needles: str) -> None:
    text = path.read_text(encoding="utf-8")
    found = [needle for needle in needles if needle in text]
    if found:
        raise AssertionError(f"{path.relative_to(ROOT)} contains forbidden demo markers: {found}")


def main() -> int:
    # The admin root must always enter the authenticated Core-backed shell.
    require(PAGE, 'import AdminShell from "../components/AdminShell"', "<AdminShell />")
    require(
        SHELL,
        'fetch("/core/api/v1/auth/me"',
        'fetch("/core/api/v1/auth/login"',
        'import PMSGrid from "./PMSGridV9"',
        'user.role',
        'isManager',
        'isReception',
        'const ADMIN_ROLES = new Set(["OWNER", "MANAGER", "RECEPTION", "MAID", "TECHNICIAN"]);',
        'if (payload && !canEnterAdmin(payload.role))',
        'if (!canEnterAdmin(payload.role))',
        'Эта роль работает в интерфейсе «Моя смена», а не в Admin/PMS.',
        'const canUseOps = isManager || ["MAID", "TECHNICIAN"].includes(user.role);',
        '{canUseOps && <button className={tab === "OPS"',
        '{tab === "OPS" && canUseOps && <OperationsBoard user={user} />}',
        'if (["MAID", "TECHNICIAN"].includes(role || "")) return "OPS";',
    )
    require(GRID_V9, 'import PMSOwnerGrid from "./PMSOwnerGrid"', "<PMSOwnerGrid />")
    require(
        OWNER_GRID,
        'fetch(`/core/api/v1/pms/grid?',
        'fetch("/core/api/v1/admin/reception/reservations?limit=500"',
        '/ws/pms/grid?',
        'PMS · рабочая шахматка',
    )
    require(
        STAFF_BOARD,
        'RECEPTION: "Ресепшен"',
        '<option value="RECEPTION">Ресепшен</option>',
        'BEACH_PARTNER: "Пляжный партнёр"',
        '<option value="BEACH_PARTNER">Пляжные партнёры</option>',
        'fetch("/core/api/v1/admin/staff/overview"',
    )

    # These markers belong to the historical one-file owner-review/demo surface and
    # must never become the normal authenticated PMS runtime.
    forbidden = (
        "OWNER REVIEW",
        "Offline Test / API-ready",
        "ONE FILE · TEST",
        "Сбросить демо",
        "three-crowns-pms-v10-owner",
        "localStorage.setItem",
        "function initState()",
    )
    for path in (PAGE, SHELL, GRID_V9, OWNER_GRID):
        forbid(path, *forbidden)

    demo_route = ROOT / "apps/admin/app/demo/page.tsx"
    if demo_route.exists():
        # A historical explicit /demo route may remain for internal archaeology,
        # but normal root runtime must not import, redirect to, or depend on it.
        page_text = PAGE.read_text(encoding="utf-8")
        shell_text = SHELL.read_text(encoding="utf-8")
        if "/demo" in page_text or "/demo" in shell_text or "app/demo" in page_text or "app/demo" in shell_text:
            raise AssertionError("normal admin runtime references the historical /demo route")

    print("ADMIN_RUNTIME_TRUTH_OK: / is authenticated Core-backed PMS; non-admin staff roles fail closed, demo markers are absent, operations UI follows staff RBAC, and existing staff roles are visible")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"ADMIN_RUNTIME_TRUTH_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1)
