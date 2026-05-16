# Decipher

Sales DNA platform. Local prototype on Docker. Steve's Mac, single operator.

**Spec of record:** `docs/super_prompt.md` (verbatim Decipher_ClaudeCode_SuperPrompt.md).
**Framework:** [BMAD Method v6.6.0](https://bmadcode.com/) (installed under `_bmad/`).

## What works (v0.2, M0-M2 complete)

- ✅ BMAD v6.6.0 installed (`_bmad/`, 42 Claude Code skills under `.claude/skills/`)
- ✅ `docs/{analysis,prd,architecture,ux_design,decisions}.md` written
- ✅ `scripts/find_ports.sh` discovers free ports → `.env`
- ✅ `decipher-db` (pgvector/pg16) up with full 24-table schema + seed (taxonomies, archetypes, industries, Steve, brand voice)
- ✅ `decipher-mail` (Mailpit) up for local SMTP capture
- ✅ FastAPI `/api/health`, `/api/bootstrap`, `/api/events`, `/api/industries`, `/api/archetypes`
- ✅ React + Vite + TS + Tailwind dashboard, 10 routed pages, HIG-conformant tokens, dark/light auto
- ✅ Mission Control DB-driven (resolved port list, audit counts, taxonomy)

## Local ports (this Mac, run `scripts/find_ports.sh` to re-resolve)

| Service | Port |
|---|---|
| Postgres (pgvector) | **55432** |
| FastAPI | **58080** |
| Vite dashboard | **55173** |
| Mailpit (web UI) | **58025** |

## Run

```bash
cd ~/Documents/Decipher

# 1. (One-off) discover free ports and write .env
./scripts/find_ports.sh

# 2. Start Postgres + Mailpit
docker compose --env-file .env up -d

# 3. (One-off) Python venv + deps
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 4. API (host)
set -a; source .env; set +a
.venv/bin/uvicorn app.api_server:app --host 127.0.0.1 --port "$DECIPHER_API_PORT" --reload

# 5. Dashboard (other terminal)
cd dashboard
npm install
set -a; source ../.env; set +a
npm run dev
```

Open `http://localhost:$DECIPHER_WEB_PORT` and `http://localhost:$DECIPHER_MAIL_PORT` (Mailpit UI).

## Project rules (non-negotiable, from spec §10)

1. No lying  2. No assumptions  3. Nothing fails silently  4. No stale numbers in UI
5. No physical browser (headless Playwright only)  6. All UI data DB-driven
7. Australian English  8. No em dashes  9. Always check links  10. No double negatives
11. No bro-sales clichés  12. No AI filler  13. Diagnose before prescribe
14. DNA Audit = Trojan horse  15. Steve sole operator  16. Apple HIG non-negotiable

## Next

- M3 Audit ingestion (47 questions, lifecycle endpoints, scorer, classifier, bands)
- M4 Report generation (Claude API, HIG PDF, Mailpit delivery)
- M5 Operator dashboard (magic-link auth, populated pages)
- M6 Executive dashboard (mirror Steve's slide 1:1)

See `docs/prd.md` for full epic list and `docs/decisions.md` for choices made.
