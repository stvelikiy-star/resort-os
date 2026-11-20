#!/usr/bin/env bash
# Read-only inventory; no service changes, package installs or credentials.
set -euo pipefail
printf '\nMARINA SMART | Ubuntu server inventory\n'
printf 'System: '; uname -a
printf '\nCPU:\n'; nproc || true
printf '\nRAM:\n'; free -h || true
printf '\nDisk:\n'; df -h / || true
printf '\nUptime:\n'; uptime || true
printf '\nDocker:\n'
if command -v docker >/dev/null 2>&1; then
  docker version --format '{{.Server.Version}}' 2>/dev/null || echo 'Docker engine unavailable'
  docker compose version || true
  docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true
else
  echo 'Docker missing'
fi
printf '\nTailscale:\n'
if command -v tailscale >/dev/null 2>&1; then
  tailscale status 2>/dev/null | head -35 || true
else
  echo 'Tailscale missing'
fi
printf '\nListening TCP (no secrets):\n'
if command -v ss >/dev/null 2>&1; then ss -lnt | head -45; fi
printf '\nBackup location free space:\n'
df -h . || true
echo 'Inventory complete. No configuration changed.'
