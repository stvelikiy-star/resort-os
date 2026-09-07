#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main() -> None:
    demo = read("scripts/prepare_demo_showcase.py")
    ops = read("scripts/release_operations_smoke.py")

    for name, text in (("prepare_demo_showcase.py", demo), ("release_operations_smoke.py", ops)):
        require('os.environ.get("APP_ENV", "")' in text, f"{name} has no implicit development APP_ENV fallback")
        require('ALLOWED_SYNTHETIC_ENVS = {"development", "test", "ci", "staging"}' in text, f"{name} declares explicit synthetic environments")
        require("APP_ENV not in ALLOWED_SYNTHETIC_ENVS" in text, f"{name} fails closed outside explicit synthetic environments")
        require('os.environ.get("APP_ENV", "development")' not in text, f"{name} cannot silently assume development")

    require("/api/v1/admin/booking/requests/" in demo and "/confirm-payment" in demo, "demo verifier covers a mutating reservation/payment script")
    require('/api/v1/ops/rooms/' in ops and '/api/v1/ops/tasks' in ops, "operations verifier covers mutating room/task actions")
    print("SYNTHETIC_SCRIPT_SAFETY_PASS")


if __name__ == "__main__":
    main()
