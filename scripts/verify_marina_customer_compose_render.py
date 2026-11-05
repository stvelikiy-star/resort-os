#!/usr/bin/env python3
"""Render, never start, two independent MARINA customer Compose projects.

Only synthetic credentials and hostnames are used. Requires Docker Compose v2
CLI, but NOT the daemon. This does not prove real Ubuntu or database isolation.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

from test_verify_marina_customer_isolation import hotel
from marina_shared_edge_config import render as render_edge
from verify_marina_customer_isolation import validate_one, validate_pair

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose.production.yaml"
EXAMPLE = ROOT / ".env.production.example"


def format_env(d: dict[str, str]) -> str:
    return "".join(f"{key}={value}\n" for key, value in d.items())


def render(env: dict[str, str], directory: Path, shared: bool = False) -> dict:
    envfile = directory / "customer.env"
    envfile.write_text(format_env(env), encoding="utf-8")
    try:
        command = ["docker", "compose", "--env-file", str(envfile), "-p",
                   env["COMPOSE_PROJECT_NAME"], "-f", str(COMPOSE)]
        if shared:
            command += ["-f", str(ROOT / "compose.marina-customer-shared-edge.yaml")]
        command += ["config", "--format", "json"]
        result = subprocess.run(
            command,
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
    # Now render a DIFFERENT deployment mode: both customers on ONE Ubuntu,
    # each with its own private ingress network and no published gateway ports.
    a["MARINA_DEPLOYMENT_HOST_ID"] = "synthetic-single-host"
    b["MARINA_DEPLOYMENT_HOST_ID"] = "synthetic-single-host"
    edge_caddy, edge_yaml = render_edge([a, b])
    with tempfile.TemporaryDirectory() as base:
        shared = []
        for i, overrides in enumerate((a, b), 1):
            env = dict(example)
            env.update(overrides)
            env["TLS_EMAIL"] = "synthetic-tests@domain.invalid"
            home = Path(base) / str(i)
            home.mkdir()
            shared.append(render(env, home, shared=True))
        edge_dir = Path(base) / "edge"
        edge_dir.mkdir()
        (edge_dir / "Caddyfile").write_text(edge_caddy, encoding="utf-8")
        edge_file = edge_dir / "compose.marina-edge.yaml"
        edge_file.write_text(edge_yaml, encoding="utf-8")
        checked = subprocess.run(
            ["docker", "compose", "-f", str(edge_file), "config", "--format", "json"],
            env={**os.environ, "TLS_EMAIL": "synthetic-tests@domain.invalid"},
            cwd=edge_dir, text=True, capture_output=True, timeout=90,
        )
        if checked.returncode:
            raise AssertionError("Generated edge Compose graph invalid")
        edge = json.loads(checked.stdout)
    for cfg, customer in zip(shared, (a, b)):
        gateway = cfg["services"]["customer_gateway"]
        assert not gateway.get("ports"), "Private gateway exposes host ports"
        assert "caddy" not in cfg["services"], "Standalone public Caddy must be disabled in customer shared-edge mode"
        assert cfg["networks"]["marina_ingress"]["name"] == "marina_ingress_" + customer["COMPOSE_PROJECT_NAME"]
        assert cfg["services"]["postgres"].get("ports") in (None, []), "PostgreSQL exposed"
    edge_ports = {str(p["published"]) for p in edge["services"]["marina_edge"]["ports"]}
    assert "80" in edge_ports and "443" in edge_ports
    assert len(edge["services"]["marina_edge"]["networks"]) == 2
    assert len(edge["networks"]) == 2
    for customer in (a, b):
        assert "marina_ingress_" + customer["COMPOSE_PROJECT_NAME"] in [v["name"] for v in edge["networks"].values()]
    print("PASS: two synthetic same-host customer gateways + ONE shared HTTPS edge render without leaked DB ports")
    print("PASS: two synthetic customer Compose configs render distinct DB, network, volume, project and provider bindings")
    print("BOUNDARY: customer stacks require separate hosts with this Compose; same-Ubuntu shared HTTPS edge not yet accepted")


if __name__ == "__main__":
    main()
