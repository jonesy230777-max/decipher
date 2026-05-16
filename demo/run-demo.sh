#!/usr/bin/env bash
# Decipher · interactive demo bootstrap.
# Works on macOS or Linux. Asks before doing anything destructive.
set -euo pipefail
cd "$(dirname "$0")/.."

# ---------- Colours + helpers ----------
if [[ -t 1 ]]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; CLR=$'\033[0m'
  GREEN=$'\033[32m'; BLUE=$'\033[34m'; RED=$'\033[31m'
  YELLOW=$'\033[33m'; CYAN=$'\033[36m'; MAGENTA=$'\033[35m'
else
  BOLD=''; DIM=''; CLR=''; GREEN=''; BLUE=''; RED=''; YELLOW=''; CYAN=''; MAGENTA=''
fi
TICK="${GREEN}✓${CLR}"; CROSS="${RED}✗${CLR}"; DASH="${DIM}·${CLR}"; ARROW="${CYAN}▸${CLR}"
say()    { printf "  %s  %s\n" "$ARROW" "$*"; }
ok()     { printf "  %s  %s\n" "$TICK"  "$*"; }
warn()   { printf "  ${YELLOW}!${CLR}  %s\n" "$*"; }
fail()   { printf "  %s  ${RED}%s${CLR}\n" "$CROSS" "$*"; exit 1; }
section(){ printf "\n${BOLD}${MAGENTA}%s${CLR}\n" "$*"; printf "${DIM}%s${CLR}\n" "$(printf '%.0s─' $(seq 1 ${#1}))"; }

confirm() {
  # confirm "Question?" [default Y|n]
  local prompt="$1" default="${2:-Y}" reply
  local hint="[Y/n]"; [[ "$default" =~ ^[Nn]$ ]] && hint="[y/N]"
  if [[ "${DECIPHER_DEMO_YES:-}" == "1" ]]; then
    printf "  %s  %s %s ${DIM}auto-yes${CLR}\n" "$ARROW" "$prompt" "$hint"; return 0
  fi
  while true; do
    printf "  %s  %s %s " "$ARROW" "$prompt" "$hint"
    read -r reply </dev/tty || reply=""
    reply="${reply:-$default}"
    case "$reply" in
      Y|y|YES|yes) return 0 ;;
      N|n|NO|no)   return 1 ;;
      *) printf "      ${DIM}please answer y or n${CLR}\n" ;;
    esac
  done
}

# ---------- Banner ----------
clear 2>/dev/null || true
cat <<BANNER
${BOLD}${BLUE}
   ████  ████  ████  ████  ████  ████  ████  ████  ████  ████
   ────────────────────────────────────────────────────────────
        D E C I P H E R    ·    Sales DNA Audit Platform
   ────────────────────────────────────────────────────────────
${CLR}${DIM}   one-shot interactive demo bootstrap${CLR}

BANNER

# ---------- Step 1 · prerequisites ----------
section "Step 1 of 6 · Checking prerequisites"

missing=()
if command -v docker >/dev/null 2>&1; then
  ok "docker · $(docker --version | head -c 40)"
else
  missing+=("Docker Desktop · https://www.docker.com/products/docker-desktop")
fi

if command -v node >/dev/null 2>&1; then
  NODE_V="$(node --version)"
  ok "node   · $NODE_V"
else
  missing+=("Node 18+ · https://nodejs.org")
fi

PY_BIN="$(command -v python3.12 || command -v python3 || true)"
if [[ -n "$PY_BIN" ]]; then
  ok "python · $($PY_BIN --version 2>&1)"
else
  missing+=("Python 3.12+ · https://www.python.org")
fi

if (( ${#missing[@]} )); then
  printf "\n  %s  Missing prerequisites:\n" "$CROSS"
  for m in "${missing[@]}"; do printf "      - %s\n" "$m"; done
  printf "\n  Install the above and re-run this script.\n\n"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  warn "Docker daemon is not running."
  if confirm "Open Docker Desktop now and wait for it?" Y; then
    if command -v open >/dev/null 2>&1; then open -a Docker || true; fi
    printf "  waiting for Docker daemon "
    for _ in $(seq 1 60); do
      if docker info >/dev/null 2>&1; then printf "ready\n"; break; fi
      printf "."; sleep 1
    done
    docker info >/dev/null 2>&1 || fail "Docker still not running. Start it manually and re-run."
  else
    fail "Docker required."
  fi
fi
ok "docker daemon running"

# ---------- Step 2 · ports ----------
section "Step 2 of 6 · Resolving free ports"
bash scripts/find_ports.sh
set -a; . ./.env; set +a
printf "      DB  ${BOLD}%s${CLR}   API ${BOLD}%s${CLR}   WEB ${BOLD}%s${CLR}   MAIL ${BOLD}%s${CLR}\n" \
  "$DECIPHER_DB_PORT" "$DECIPHER_API_PORT" "$DECIPHER_WEB_PORT" "$DECIPHER_MAIL_PORT"
confirm "Proceed with these ports?" Y || fail "Edit .env and re-run."

# ---------- Step 3 · Postgres + Mailpit ----------
section "Step 3 of 6 · Starting Postgres + Mailpit (Docker)"
say  "docker compose up -d postgres mailpit"
docker compose up -d postgres mailpit >/dev/null
printf "      waiting for postgres "
for _ in $(seq 1 60); do
  if docker compose exec -T postgres pg_isready -U decipher -d decipher -h 127.0.0.1 -p 5432 >/dev/null 2>&1; then
    printf "${GREEN}ready${CLR}\n"; break
  fi
  printf "."; sleep 1
done
ok "postgres + mailpit up"

# ---------- Step 4 · load demo data ----------
section "Step 4 of 6 · Loading demo data"
EXISTING_RESPS=$(PGPASSWORD=decipher_local_dev psql \
  -h 127.0.0.1 -p "$DECIPHER_DB_PORT" -U decipher -d decipher \
  -tAc "SELECT count(*) FROM information_schema.tables WHERE table_name='respondents'" 2>/dev/null || echo 0)

LOAD=true
if [[ "$EXISTING_RESPS" == "1" ]]; then
  N=$(PGPASSWORD=decipher_local_dev psql -h 127.0.0.1 -p "$DECIPHER_DB_PORT" -U decipher -d decipher -tAc "SELECT count(*) FROM respondents")
  warn "Database already has $N respondents. Re-loading will WIPE and replace."
  confirm "Reload demo data from snapshot?" N || LOAD=false
fi

if [[ "$LOAD" == true ]]; then
  say "loading demo/decipher_dump.sql (~1.5 MB)"
  PGPASSWORD=decipher_local_dev psql \
    -h 127.0.0.1 -p "$DECIPHER_DB_PORT" -U decipher -d decipher \
    -v ON_ERROR_STOP=1 --quiet -f demo/decipher_dump.sql > /tmp/decipher_load.log 2>&1 \
    || { tail -40 /tmp/decipher_load.log; fail "psql load failed. See /tmp/decipher_load.log"; }
fi
N=$(PGPASSWORD=decipher_local_dev psql -h 127.0.0.1 -p "$DECIPHER_DB_PORT" -U decipher -d decipher -tAc "SELECT count(*) FROM respondents")
A=$(PGPASSWORD=decipher_local_dev psql -h 127.0.0.1 -p "$DECIPHER_DB_PORT" -U decipher -d decipher -tAc "SELECT count(*) FROM audits")
ok "loaded · ${N} respondents · ${A} audits"

# ---------- Step 5 · install deps ----------
section "Step 5 of 6 · Installing dependencies"

if [[ -x .venv/bin/python ]]; then
  ok "python venv exists · skipping create"
else
  say "creating Python venv"
  "$PY_BIN" -m venv .venv
fi
say "pip install -r requirements.txt"
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
ok "python deps ready"

if [[ -d dashboard/node_modules ]]; then
  ok "node_modules exists · skipping install"
else
  say "npm install (this can take ~1 minute the first time)"
  ( cd dashboard && npm install --silent --no-audit --no-fund )
fi
ok "node deps ready"

# ---------- Step 6 · launch + wait ----------
section "Step 6 of 6 · Launching API + Dashboard"

pkill -f "uvicorn app.api_server:app" 2>/dev/null && warn "killed stale API process" || true
pkill -f "vite.*--port $DECIPHER_WEB_PORT" 2>/dev/null && warn "killed stale dashboard" || true
sleep 1

mkdir -p var/logs

say "starting API   on http://127.0.0.1:$DECIPHER_API_PORT"
PYTHONPATH=. nohup .venv/bin/uvicorn app.api_server:app \
  --host 127.0.0.1 --port "$DECIPHER_API_PORT" --reload --log-level error \
  > var/logs/api.log 2>&1 &
echo $! > var/logs/api.pid

say "starting WEB   on http://127.0.0.1:$DECIPHER_WEB_PORT"
( cd dashboard && nohup npm run dev -- --host 127.0.0.1 --port "$DECIPHER_WEB_PORT" \
  > ../var/logs/web.log 2>&1 & echo $! > ../var/logs/web.pid )

printf "      waiting for API "
for _ in $(seq 1 30); do
  if curl -fs "http://127.0.0.1:$DECIPHER_API_PORT/api/health" >/dev/null 2>&1; then
    printf "${GREEN}ready${CLR}\n"; break
  fi
  printf "."; sleep 1
done
printf "      waiting for WEB "
for _ in $(seq 1 30); do
  if curl -fs "http://127.0.0.1:$DECIPHER_WEB_PORT/" >/dev/null 2>&1; then
    printf "${GREEN}ready${CLR}\n"; break
  fi
  printf "."; sleep 1
done

# ---------- Done ----------
DASH_URL="http://127.0.0.1:$DECIPHER_WEB_PORT"
MAIL_URL="http://127.0.0.1:$DECIPHER_MAIL_PORT"

printf "\n${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CLR}\n"
printf "${BOLD}${GREEN}  Decipher demo is live.${CLR}\n"
printf "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CLR}\n\n"
printf "  ${BOLD}Dashboard${CLR}  ${BLUE}%s${CLR}\n" "$DASH_URL"
printf "  ${BOLD}Mailpit  ${CLR}  ${BLUE}%s${CLR}    ${DIM}(catches every demo email)${CLR}\n" "$MAIL_URL"
printf "  ${BOLD}API      ${CLR}  ${DIM}http://127.0.0.1:%s/api/health${CLR}\n" "$DECIPHER_API_PORT"
printf "  ${BOLD}Logs     ${CLR}  ${DIM}var/logs/api.log  +  var/logs/web.log${CLR}\n\n"

printf "  ${BOLD}Demo logins${CLR} (click on the login page to auto-fill):\n"
printf "    ${CYAN}admin${CLR}                  steve@decipher.local              decipher2026\n"
printf "    ${CYAN}ceo${CLR}                    maya.chen@atlasmedia.demo         demo2026\n"
printf "    ${CYAN}sales_director${CLR}         owen.wright@atlasmedia.demo       demo2026\n"
printf "    ${CYAN}hr${CLR}                     sara.holloway@atlasmedia.demo     demo2026\n"
printf "    ${CYAN}learning_development${CLR}   eddie.lin@atlasmedia.demo         demo2026\n\n"

printf "  ${DIM}To stop everything:   ${CLR}./demo/stop-demo.sh\n\n"

if [[ "${DECIPHER_DEMO_YES:-}" != "1" ]] && confirm "Open the dashboard in your browser now?" Y; then
  if command -v open >/dev/null 2>&1;       then open "$DASH_URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$DASH_URL"
  fi
fi
