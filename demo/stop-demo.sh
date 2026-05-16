#!/usr/bin/env bash
# Decipher · stop the demo cleanly.
set -euo pipefail
cd "$(dirname "$0")/.."

GREEN=$'\033[32m'; YELLOW=$'\033[33m'; DIM=$'\033[2m'; CLR=$'\033[0m'
TICK="${GREEN}✓${CLR}"
say() { printf "  ${YELLOW}▸${CLR}  %s\n" "$*"; }
ok()  { printf "  %s  %s\n" "$TICK" "$*"; }

say "stopping API + dashboard"
[[ -f var/logs/api.pid ]] && kill "$(cat var/logs/api.pid)" 2>/dev/null || true
[[ -f var/logs/web.pid ]] && kill "$(cat var/logs/web.pid)" 2>/dev/null || true
pkill -f "uvicorn app.api_server:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
ok "API + dashboard stopped"

say "stopping Postgres + Mailpit (docker compose down)"
docker compose down >/dev/null 2>&1 || true
ok "containers down"

printf "\n  ${DIM}Postgres volume preserved. Run ./demo/run-demo.sh to restart.${CLR}\n\n"
