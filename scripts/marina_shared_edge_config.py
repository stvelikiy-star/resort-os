#!/usr/bin/env python3
"""Generate ONE shared HTTPS edge for independent MARINA customer stacks.

Never starts services or reads databases. Keep private .env files outside Git.
Outputs contain ONLY public hostname/project identifiers (no secret values).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from verify_marina_customer_isolation import (
    HOST_KEYS, parse_env, validate_one, validate_pair,
)

COLLISION_MESSAGE = "same Ubuntu/VM host unsupported by compose.production.yaml"
NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{2,62}$")
FQDN = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}$")


def validate_shared_edge(hotels: list[dict[str, str]]) -> list[str]:
    problems: list[str] = []
    if len(hotels) < 2:
        return ["shared edge requires at least two independent hotel configs"]
    host_ids = {h.get("MARINA_DEPLOYMENT_HOST_ID", "") for h in hotels}
    if len(host_ids) != 1 or not next(iter(host_ids)):
        problems.append("hotels must declare the SAME actual Ubuntu host ID for shared edge")
    for i, hotel in enumerate(hotels):
        problems.extend(validate_one(hotel, f"hotel_{i+1}"))
        project = hotel.get("COMPOSE_PROJECT_NAME", "")
        if not NAME.fullmatch(project):
            problems.append(f"hotel_{i+1}: invalid Docker project")
        for key in HOST_KEYS:
            if not FQDN.fullmatch(hotel.get(key, "").lower()):
                problems.append(f"hotel_{i+1}: {key} must be a valid public DNS name")
        expected_origins = {"https://" + hotel.get(key, "").lower() for key in
                            ("PUBLIC_HOST", "ADMIN_HOST", "STAFF_HOST")}
        supplied_origins = {value.strip().lower() for value in
                            hotel.get("CORS_ORIGINS", "").split(",") if value.strip()}
        if supplied_origins != expected_origins:
            problems.append(f"hotel_{i+1}: CORS_ORIGINS must contain exactly this hotel's public/admin/staff HTTPS origins")
        # Host-only session cookies are required for customer privacy; a parent
        # domain cookie could be shared with unrelated client subdomains.
        if hotel.get("COOKIE_DOMAIN", "").strip():
            problems.append(f"hotel_{i+1}: COOKIE_DOMAIN must be empty (host-only cookies)")

    # The public www redirect is a real additional edge hostname.
    # Do not allow it to overlap another customer's API/Admin/Staff host.
    all_hosts: list[str] = []
    for item in hotels:
        all_hosts.extend(item.get(key, "").lower() for key in HOST_KEYS)
        all_hosts.append("www." + item.get("PUBLIC_HOST", "").lower())
    if len(all_hosts) != len(set(all_hosts)):
        problems.append("public host/redirect www aliases collide across service routes")
    for i, a in enumerate(hotels):
        for j in range(i + 1, len(hotels)):
            b = hotels[j]
            pair_errors = [
                err for err in validate_pair(a, b)
                if not err.startswith(COLLISION_MESSAGE)
            ]
            problems.extend(f"hotel_{i+1}/hotel_{j+1}: {e}" for e in pair_errors)
    return problems


def render(hotels: list[dict[str, str]]) -> tuple[str, str]:
    errors = validate_shared_edge(hotels)
    if errors:
        raise ValueError("; ".join(errors))
    caddy = [
        "{",
        "  email {$TLS_EMAIL}",
        "  servers {",
        "    protocols h1 h2 h3",
        "  }",
        "}",
        "",
    ]
    network_names: list[str] = []
    for hotel in hotels:
        project = hotel["COMPOSE_PROJECT_NAME"]
        alias = f"marina_{project}_gateway"
        network_names.append(f"ingress_{project}")
        for key in HOST_KEYS:
            host = hotel[key].lower()
            caddy.extend([
                f"{host} {{",
                "  encode zstd gzip",
                f"  reverse_proxy http://{alias}:80",
                "}",
                "",
            ])
        caddy.extend([
            f"www.{hotel['PUBLIC_HOST'].lower()} {{",
            f"  redir https://{hotel['PUBLIC_HOST'].lower()}{{uri}} permanent",
            "}",
            "",
        ])
    compose = [
        "# Generated MARINA shared edge. Review before deploying; do not commit real envs.",
        "services:",
        "  marina_edge:",
        "    image: caddy:2.11.4-alpine",
        "    restart: unless-stopped",
        "    environment:",
        "      TLS_EMAIL: ${TLS_EMAIL}",
        "    ports:",
        '      - "80:80"',
        '      - "443:443"',
        '      - "443:443/udp"',
        "    volumes:",
        "      - ./Caddyfile:/etc/caddy/Caddyfile:ro",
        "      - caddy_data:/data",
        "      - caddy_config:/config",
        "    networks:",
    ]
    compose.extend(f"      - {net}" for net in network_names)
    compose.extend(["networks:"])
    for name, hotel in zip(network_names, hotels):
        compose.extend([
            f"  {name}:",
            "    external: true",
            f"    name: marina_ingress_{hotel['COMPOSE_PROJECT_NAME']}",
        ])
    compose.extend(["volumes:", "  caddy_data:", "  caddy_config:", ""])
    return "\n".join(caddy), "\n".join(compose)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("hotel_env", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        hotels = [parse_env(path) for path in args.hotel_env]
        caddy, compose = render(hotels)
    except (OSError, ValueError) as exc:
        # Exception messages are field names and public route metadata only.
        # Never include secret contents or full env file values in stdout.
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "Caddyfile").write_text(caddy, encoding="utf-8")
    (out / "compose.marina-edge.yaml").write_text(compose, encoding="utf-8")
    print(f"PASS: generated shared edge routing for {len(hotels)} independent customer stacks")
    print("BOUNDARY: generated files do not start Docker, verify TLS or authorize production")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
