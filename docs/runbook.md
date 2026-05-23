# Decipher Runbook

Single-operator runbook for Steve Jones. All commands assume the repo is at
`~/Decipher` on your Mac/Linux host and Docker is running.

---

## Cold start

Start everything from scratch after a reboot or fresh clone.

```bash
cd ~/Decipher

# 1. Start the database
docker compose up -d db
sleep 3   # let Postgres initialise

# 2. Apply schema and seed data (safe to re-run -- uses IF NOT EXISTS / ON CONFLICT)
docker exec -i decipher-db psql -U decipher decipher < schema.sql
docker exec -i decipher-db psql -U decipher decipher < seed.sql

# 3. Source the environment
export $(grep -v '^#' .env | xargs)

# 4. Activate the Python venv and start the API
source .venv/bin/activate
uvicorn app.api_server:app --port "$DECIPHER_API_PORT" &

# 5. Start the dashboard dev server
cd dashboard
npm run dev -- --port "$DECIPHER_WEB_PORT" &

# 6. Open in browser
open "http://localhost:$DECIPHER_WEB_PORT"
```

Sign in: `steve@decipher.com.au` / `Decipher2026!`

---

## Port re-discovery after reboot

Ports are auto-assigned by `scripts/find_ports.sh` and written to `.env`.
If Docker or the OS has reassigned ports:

```bash
cd ~/Decipher
bash scripts/find_ports.sh     # regenerates DECIPHER_* port vars in .env
cat .env                       # verify the new ports
```

Then re-run the cold start steps 3-6 above with the new ports.

---

## Restoring from backup

Backups are at `var/backups/decipher_<timestamp>.sql.gz`, retained 14 days.

```bash
# List available backups
ls -lh ~/Decipher/var/backups/

# Restore a specific backup (destructive -- drops and recreates all data)
BACKUP=var/backups/decipher_2026-05-23_023000.sql.gz

gunzip -c "$BACKUP" | docker exec -i decipher-db psql \
  -U decipher decipher
```

After restoring, restart the API server so caches are cleared:

```bash
pkill -f "uvicorn app.api_server"
source .venv/bin/activate && export $(grep -v '^#' .env | xargs)
uvicorn app.api_server:app --port "$DECIPHER_API_PORT" &
```

Manual backup trigger (without waiting for the 02:30 AEST schedule):

```bash
bash scripts/pg_backup.sh
# or via the API:
curl -X POST http://localhost:$DECIPHER_API_PORT/api/admin/backup
```

---

## Manual report regeneration

Regenerate a PDF report for a completed audit:

```bash
source .venv/bin/activate && export $(grep -v '^#' .env | xargs)

# Replace 123 with the actual audit_id
python3 -c "
from app.dna_report import generate_report
result = generate_report(audit_id=123)
print(result)
"
```

Or via the API (fires in background, check events log for completion):

```bash
curl -X POST http://localhost:$DECIPHER_API_PORT/api/report/generate \
  -H 'Content-Type: application/json' \
  -d '{"audit_id": 123}'
```

---

## Squarespace bundle rebuild

Generate a fresh Squarespace bundle pulling live brand voice and cohort data:

```bash
# Via dashboard: Squarespace Export page → Generate New Export
# Via API:
curl -X POST http://localhost:$DECIPHER_API_PORT/api/squarespace/generate
```

The zip lands at `_squarespace_exports/squarespace_export_<id>_<timestamp>.zip`.
Upload to Squarespace manually via their admin panel.

---

## Stripe key rotation

1. Generate new keys in the Stripe dashboard (live or test).
2. Update `.env`:
   ```
   STRIPE_SECRET_KEY=sk_live_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```
3. Update the webhook endpoint URL in Stripe dashboard if the server address changed.
4. Restart the API server:
   ```bash
   pkill -f "uvicorn app.api_server"
   export $(grep -v '^#' .env | xargs)
   source .venv/bin/activate
   uvicorn app.api_server:app --port "$DECIPHER_API_PORT" &
   ```
5. Test with a Stripe test-mode checkout to confirm the webhook fires correctly.

---

## HIG compliance audit

Run the automated Playwright audit at any time:

```bash
source .venv/bin/activate && export $(grep -v '^#' .env | xargs)
python3 compliance/playwright_audit.py
```

Report writes to `compliance/hig_audit_<timestamp>.md`.
Screenshots in `compliance/screenshots/<timestamp>/`.

Follow with the Quinn vision UAT pass:

```bash
python3 compliance/quinn_uat.py
```

Quinn appends a UAT section to the most recent audit report.

---

## Scheduled jobs (APScheduler, AEST)

| Job | Schedule | Description |
|---|---|---|
| cohort_snapshot | Daily 02:00 | Aggregate band and archetype distributions into cohort_snapshots |
| pg_backup | Daily 02:30 | Dump Postgres to var/backups/, prune >14 days |
| pattern_hunt | Monday 03:00 | 2-3 condition grid search with DOUBT gate |

Manual triggers:

```bash
curl -X POST http://localhost:$DECIPHER_API_PORT/api/admin/cohort/snapshot
curl -X POST http://localhost:$DECIPHER_API_PORT/api/admin/cohort/pattern-hunt
curl -X POST http://localhost:$DECIPHER_API_PORT/api/admin/backup
```

---

## Key file locations

| File | Purpose |
|---|---|
| `.env` | All secrets and port config. Never commit. |
| `schema.sql` | DB schema (idempotent) |
| `seed.sql` | Seed data (demo respondents, industries, archetypes) |
| `var/backups/` | Postgres dumps (14-day retention) |
| `_squarespace_exports/` | Generated Squarespace bundles |
| `compliance/` | HIG audit scripts and reports |
| `dashboard/` | Vite/React operator dashboard |
| `app/` | FastAPI backend |
| `docs/` | Architecture, PRD, decisions, this runbook |
