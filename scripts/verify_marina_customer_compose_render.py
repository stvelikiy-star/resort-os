#!/usr/bin/env python3
"""Render, never start, two independent MARINA customer Compose projects.

Only synthetic credentials and hostnames are used. Requires Docker Compose v2
CLI, but NOT the daemon. This does not prove real Ubuntu or database isolation.
"""
import json
import subprocess
import tempfile
from pathlib import Path

from test_verify_marina_customer_isolation import hotel
from verify_marina_customer_isolation import validate_one, validate_pair

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose.production.yaml"
EXAMPLE = ROOT / ".env.production.example"


def format_env(d: dict[str, str]) -> str:
    return "".join(f"{key}={value}\n" for key, value in d.items())


def render(env: dict[str, str], directory: Path) -> dict:
    envfile = directory / "customer.env"
    envfile.write_text(format_env(env), encoding="utf-8")
    try:
        result = subprocess.run(
            ["docker", "compose", "--env-file", str(envfile), "-p",
             env["COMPOSE_PROJECT_NAME"], "-f", str(COMPOSE),
             "config", "--format", "json"],
            cwd=ROOT, text=True, capture_output=True, timeout=90, check=False,
        )
        if result.returncode:
            # Compose stderr may include sensitive interpolated values; never print.
            raise RuntimeError("docker compose config failed on synthetic fixture")
        return json.loads(result.stdout)
    finally:
        envfile.unlink(missing_ok=True)


def mounted_postgres(rendered: dict) -> str:
    postgres = rendered["services"]["postgres"]
    mounts = postgres["volumes"]
    paths = [v.get("source", "") for v in mounts if v.get("target") == "/var/lib/postgresql/data"]
    assert len(paths) == 1 and paths[0], "Missing postgres persistent mount"
    return paths[0]


def main() -> None:
    if not COMPOSE.is_file() or not EXAMPLE.is_file():
        raise AssertionError("Missing committed production blueprint")
    example: dict[str, str] = {}
    for line in EXAMPLE.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        example[key.strip()] = value.strip()
    a, b = hotel(1), hotel(2)
    assert validate_one(a, "A") == []
    assert validate_one(b, "B") == []
    assert validate_pair(a, b) == []
    rendered = []
    with tempfile.TemporaryDirectory() as root:
        for idx, overrides in enumerate((a, b), 1):
            cfg = dict(example)
            cfg.update(overrides)
            cfg["TLS_EMAIL"] = "synthetic-tests@domain.invalid"
            cfg["CORS_ORIGINS"] = ",".join("https://" + overrides[k] for k in ("PUBLIC_HOST", "ADMIN_HOST", "STAFF_HOST"))
            cfg["COOKIE_DOMAIN"] = ""
            # The env example is Three Crowns-specific and is only used as a
            # list of optional Compose keys. Overrides represent new customers.
            home = Path(root) / str(idx)
            home.mkdir()
            rendered.append(render(cfg, home))

    one, two = rendered
    assert one["name"] != two["name"], "Shared Compose project name"
    assert mounted_postgres(one) != mounted_postgres(two), "Shared PostgreSQL host directory"
    assert one["services"]["api"]["environment"]["PROPERTY_CODE"] != two["services"]["api"]["environment"]["PROPERTY_CODE"]
    assert one["services"]["n8n"]["environment"]["GREEN_API_ID_INSTANCE"] != two["services"]["n8n"]["environment"]["GREEN_API_ID_INSTANCE"]
    assert one["volumes"]["caddy_data"]["name"] != two["volumes"]["caddy_data"]["name"]
    assert one["networks"]["resort"]["name"] != two["networks"]["resort"]["name"]
    # Both blueprints directly publish the HTTPS edge; this topology works
    # only on distinct hosts. Static guard refuses a shared host.
    for cfg in rendered:
        caddy_ports = {str(port["published"]) for port in cfg["services"]["caddy"]["ports"]}
        assert "80" in caddy_ports and "443" in caddy_ports
    print("PASS: two synthetic customer Compose configs render distinct DB, network, volume, project and provider bindings")
    print("BOUNDARY: customer stacks require separate hosts with this Compose; same-Ubuntu shared HTTPS edge not yet accepted")


if __name__ == "__main__":
    main()
