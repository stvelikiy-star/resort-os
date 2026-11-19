#!/usr/bin/env bash
# Adapt only disposable listener, upstream addresses and local static root.
set -euo pipefail
mkdir -p runtime/placeholder
cp new/deploy/marina/customer-unpublished.html runtime/placeholder/index.html
{ echo '{'; echo ' admin off'; echo ' auto_https off'; echo '}'; sed -e 's/^:3000 {/http:\/\/127.0.0.1:18200 {/' -e 's/guest-web:3000/127.0.0.1:18104/g' -e 's/api:8000/127.0.0.1:18002/g' -e "s@root \* /srv@root * $PWD/runtime/placeholder@" new/deploy/marina/customer-unpublished.Caddyfile; } > runtime/EdgeCaddyfile
exec runtime/caddy/usr/bin/caddy run --config runtime/EdgeCaddyfile --adapter caddyfile
