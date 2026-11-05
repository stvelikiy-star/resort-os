#!/usr/bin/env python3
"""Prepare and control isolated synthetic MARINA hotel stacks on Ubuntu. Never production-seed customer data."""
import argparse
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".marina-fleet"
COMPOSE = ROOT / "compose.marina-fleet.yaml"
SLUG = re.compile(r"[a-z][a-z0-9_]{2,28}\Z")

def env_path(slug):
    if not SLUG.fullmatch(slug):
        raise SystemExit("Hotel slug must be 3-29 lowercase letters/numbers/underscore and start with letter")
    return STATE / f"{slug}.env"

def parse_env(path):
    pairs = {}
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        name, value = line.split("=", 1)
        pairs[name] = value
    return pairs

def check_ports(base, slug):
    if not 15000 <= base <= 59000:
        raise SystemExit("Choose a port base in 15000..59000")
    for other in STATE.glob("*.env"):
        if other.name == f"{slug}.env":
            continue
        settings = parse_env(other)
        used = {int(settings[key]) for key in ("MARINA_FLEET_WEB_PORT", "MARINA_FLEET_ADMIN_PORT", "MARINA_FLEET_STAFF_PORT")}
        if used.intersection({base, base+1, base+2}):
            raise SystemExit(f"Ports clash with {other.name}")

def create(args):
    path = env_path(args.slug)
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    STATE.chmod(0o700)
    if path.exists():
        raise SystemExit(f"Hotel already registered: {path.name}. Use start/status, never overwrite credentials.")
    check_ports(args.port_base, args.slug)
    cfg = {
        "MARINA_INSTANCE_SLUG": args.slug,
        "MARINA_FLEET_DB": "marina_" + args.slug,
        "MARINA_FLEET_DB_PASSWORD": secrets.token_hex(24),
        "MARINA_FLEET_PROPERTY_CODE": "MARINA_" + args.slug.upper(),
        "MARINA_FLEET_PROPERTY_NAME": "MARINA Synthetic " + args.slug,
        "MARINA_FLEET_OWNER_USERNAME": "owner_" + args.slug,
        "MARINA_FLEET_OWNER_PASSWORD": secrets.token_urlsafe(24),
        "MARINA_FLEET_WEB_PORT": str(args.port_base),
        "MARINA_FLEET_ADMIN_PORT": str(args.port_base+1),
        "MARINA_FLEET_STAFF_PORT": str(args.port_base+2),
    }
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        for key, value in cfg.items():
            f.write(f"{key}={value}\n")
    print(f"Created isolated SYNTHETIC hotel {args.slug} with private ports {args.port_base}-{args.port_base+2}")
    print(f"Run: python3 scripts/marina_fleet.py start {args.slug}")

def docker(args):
    path = env_path(args.slug)
    if not path.exists():
        raise SystemExit("Hotel not registered; create it first")
    command = ["docker", "compose", "--env-file", str(path), "-f", str(COMPOSE)]
    if args.operation == "start":
        command += ["up", "-d", "--build", "--wait"]
    elif args.operation == "status":
        command += ["ps"]
    else:
        command += ["down"]  # no -v: preserve all database volumes
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)
    if args.operation == "start":
        config = parse_env(path)
        print(f"Owner: {config['MARINA_FLEET_OWNER_USERNAME']}; private admin: http://127.0.0.1:{config['MARINA_FLEET_ADMIN_PORT']}")
        print(f"Credentials retained in {path} (chmod 600); do not publish. Synthetic data only.")

def main():
    parser = argparse.ArgumentParser(description="Isolated synthetic MARINA SMART hotel fleet")
    sub = parser.add_subparsers(dest="operation", required=True)
    create_parser = sub.add_parser("create")
    create_parser.add_argument("slug")
    create_parser.add_argument("--port-base", type=int, required=True)
    for op in ("start", "status", "stop"):
        sub.add_parser(op).add_argument("slug")
    args = parser.parse_args()
    if args.operation == "create":
        create(args)
    else:
        docker(args)

if __name__ == "__main__":
    main()
