#!/usr/bin/env bash
set -u

# Three Crowns Resort OS — non-destructive host capability preflight.
# Safe to run before deployment. It does not install packages, stop services,
# change firewall/DNS, create users, or overwrite application data.

FAILS=0
WARNS=0

pass() { printf 'PASS: %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*"; WARNS=$((WARNS + 1)); }
fail() { printf 'FAIL: %s\n' "$*"; FAILS=$((FAILS + 1)); }
fact() { printf 'FACT: %s\n' "$*"; }

printf 'Three Crowns single-server host preflight\n'
printf '=========================================\n'

if [ "$(uname -s 2>/dev/null || true)" = "Linux" ]; then
  pass "Linux host detected"
else
  fail "Linux host is required for the approved production package"
fi

if [ -r /etc/os-release ]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  fact "os=${PRETTY_NAME:-unknown}"
  case "${ID:-}" in
    ubuntu|debian) pass "Supported Debian-family host detected" ;;
    *) warn "Host OS is not Ubuntu/Debian; validate Docker/Caddy compatibility before deployment" ;;
  esac
else
  warn "/etc/os-release is unavailable"
fi

ARCH="$(uname -m 2>/dev/null || true)"
fact "architecture=${ARCH:-unknown}"
case "$ARCH" in
  x86_64|amd64|aarch64|arm64) pass "Supported CPU architecture" ;;
  *) fail "Unsupported/unknown CPU architecture: ${ARCH:-unknown}" ;;
esac

CPU_COUNT="$(getconf _NPROCESSORS_ONLN 2>/dev/null || nproc 2>/dev/null || echo 0)"
fact "cpu_count=$CPU_COUNT"
if [ "$CPU_COUNT" -ge 4 ] 2>/dev/null; then
  pass "CPU meets recommended 4 vCPU baseline"
elif [ "$CPU_COUNT" -ge 2 ] 2>/dev/null; then
  warn "CPU is below recommended 4 vCPU baseline"
else
  fail "At least 2 vCPU are required for this topology"
fi

MEM_KB="$(awk '/MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
MEM_MB=$((MEM_KB / 1024))
fact "memory_mb=$MEM_MB"
if [ "$MEM_MB" -ge 7500 ]; then
  pass "RAM meets recommended 8 GB class"
elif [ "$MEM_MB" -ge 3800 ]; then
  warn "RAM is usable for a reduced-load start but below recommended 8 GB"
else
  fail "Host has less than approximately 4 GB RAM"
fi

ROOT_FREE_KB="$(df -Pk / 2>/dev/null | awk 'NR==2 {print $4}' || echo 0)"
ROOT_FREE_GB=$((ROOT_FREE_KB / 1024 / 1024))
fact "root_free_gb=$ROOT_FREE_GB"
if [ "$ROOT_FREE_GB" -ge 100 ]; then
  pass "Free disk meets recommended working headroom"
elif [ "$ROOT_FREE_GB" -ge 50 ]; then
  warn "Free disk is below recommended 100+ GB headroom"
else
  fail "Less than 50 GB free disk is unsuitable for application + database + local backups"
fi

if [ "$(id -u)" -eq 0 ]; then
  pass "Running with root privileges"
elif command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
  pass "Passwordless sudo is available"
else
  fail "Root or usable sudo access is required"
fi

if command -v docker >/dev/null 2>&1; then
  DOCKER_VERSION="$(docker --version 2>/dev/null || true)"
  fact "docker=${DOCKER_VERSION:-unknown}"
  if docker info >/dev/null 2>&1; then
    pass "Docker Engine is installed and usable"
  else
    fail "Docker command exists but daemon is not usable by this account"
  fi
else
  fail "Docker Engine is not installed"
fi

if docker compose version >/dev/null 2>&1; then
  fact "compose=$(docker compose version 2>/dev/null | head -1)"
  pass "Docker Compose plugin is available"
else
  fail "Docker Compose plugin is required"
fi

if command -v git >/dev/null 2>&1; then
  fact "git=$(git --version 2>/dev/null)"
  pass "Git is available"
else
  warn "Git is not installed; deployment can still use a release archive, but Git checkout is preferred"
fi

if command -v curl >/dev/null 2>&1; then
  if curl -fsS --max-time 10 https://registry-1.docker.io/v2/ >/dev/null 2>&1; then
    pass "Outbound HTTPS to Docker registry is reachable"
  else
    # Docker Hub commonly returns 401 at /v2/; network reachability can still be proven by headers.
    if curl -sS -I --max-time 10 https://registry-1.docker.io/v2/ 2>/dev/null | head -1 | grep -Eq 'HTTP/.* (200|401)'; then
      pass "Outbound HTTPS to Docker registry is reachable"
    else
      warn "Could not prove outbound Docker registry connectivity"
    fi
  fi
else
  warn "curl is unavailable; outbound network test skipped"
fi

for PORT in 80 443; do
  LISTENER=""
  if command -v ss >/dev/null 2>&1; then
    LISTENER="$(ss -ltnp 2>/dev/null | awk -v p=":$PORT" '$4 ~ p"$" {print; exit}')"
  elif command -v netstat >/dev/null 2>&1; then
    LISTENER="$(netstat -ltnp 2>/dev/null | awk -v p=":$PORT" '$4 ~ p"$" {print; exit}')"
  fi
  if [ -n "$LISTENER" ]; then
    warn "TCP/$PORT is currently occupied (expected if the legacy 3korony.com site is still live); record and plan controlled cutover: $LISTENER"
  else
    pass "TCP/$PORT is currently free for Caddy"
  fi
done

if command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | awk '$4 ~ /:5432$/ {found=1} END {exit !found}'; then
  warn "A process is listening on TCP/5432. Verify PostgreSQL is not exposed on a public interface"
else
  pass "No host-level TCP/5432 listener detected"
fi

TARGET_ROOT="${THREE_CROWNS_ROOT:-/srv/three-crowns}"
fact "target_root=$TARGET_ROOT"
PARENT="$(dirname "$TARGET_ROOT")"
if [ -d "$TARGET_ROOT" ]; then
  if [ -w "$TARGET_ROOT" ]; then
    pass "$TARGET_ROOT exists and is writable"
  else
    warn "$TARGET_ROOT exists but current account cannot write it directly"
  fi
elif [ -d "$PARENT" ] && [ -w "$PARENT" ]; then
  pass "Parent $PARENT is writable; target layout can be created during deployment"
elif [ "$(id -u)" -eq 0 ] || { command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; }; then
  pass "Target layout can be created with root/sudo"
else
  fail "Cannot create persistent target layout $TARGET_ROOT"
fi

if command -v systemctl >/dev/null 2>&1; then
  for svc in nginx apache2 httpd caddy; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
      warn "Existing web service is active: $svc. Preserve current-site backup and plan a controlled proxy/cutover; do not stop it during preflight"
    fi
  done
fi

printf '%s\n' '-----------------------------------------'
fact "warnings=$WARNS"
fact "failures=$FAILS"
if [ "$FAILS" -gt 0 ]; then
  printf 'RESULT: BLOCKED — host does not yet satisfy mandatory requirements\n'
  exit 1
fi
if [ "$WARNS" -gt 0 ]; then
  printf 'RESULT: PASS WITH WARNINGS — resolve/accept warnings before production cutover\n'
  exit 0
fi
printf 'RESULT: PASS — host satisfies the checked infrastructure requirements\n'
