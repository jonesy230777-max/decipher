# Decipher — Architecture (BMAD Phase 3, Winston)

**Date:** 2026-05-16. **Input:** `docs/prd.md`, `docs/super_prompt.md`.

---

## 1. Topology

Three-container Docker Compose stack on Steve's Mac. Free ports discovered by `scripts/find_ports.sh` and pinned in `.env`.

```
                  Steve's browser
                        │
              ┌─────────┼─────────┐
              ▼         ▼         ▼
        :${WEB_PORT}  :${API_PORT}  :${MAIL_PORT}
            │           │             │
   ┌────────┴────┐  ┌───┴────┐   ┌────┴────────┐
   │ nginx +     │  │FastAPI │   │  Mailpit    │
   │ Vite build  │  │  +     │   │  (axllent)  │
   │ (in app)    │  │ super- │   └──────┬──────┘
   └─────────────┘  │ visord │          │
                    │ daemons│          │ SMTP capture
                    └───┬────┘          │
                        │ psycopg pool  │
                        ▼               │
                  :${DB_PORT}           │
                ┌─────┴─────┐           │
                │  Postgres │◄──────────┘ (delivery + receipts)
                │  16 +     │
                │  pgvector │
                └───────────┘
```

`decipher-app` runs nginx + FastAPI + 5 daemons under supervisord (per spec §2).
For the local dev loop the dashboard runs in Vite dev mode against host
`uvicorn`; the supervisord/nginx path lights up at production-hardening (M12).

## 2. Containers

| Container | Image | Internal port | Host port | Restart |
|---|---|---|---|---|
| `decipher-db` | `pgvector/pgvector:pg16` | 5432 | `${DECIPHER_DB_PORT}` | `unless-stopped` |
| `decipher-app` | local `Dockerfile` (Python 3.12 + Node 22 + nginx + supervisord) | 80 + 8000 | `${DECIPHER_WEB_PORT}` + `${DECIPHER_API_PORT}` | `unless-stopped` |
| `decipher-mail` | `axllent/mailpit:latest` | 1025 (SMTP) + 8025 (UI) | `${DECIPHER_MAIL_PORT}` (UI) | `unless-stopped` |

Volumes:
- `decipher_pgdata` (Postgres data)
- `./reports:/data/reports` (PDF artefacts; bind-mounted for inspection)
- `./_squarespace_exports:/data/exports`

## 3. Supervisord daemons (inside `decipher-app`)

`nginx`, `api`, `audit-scorer`, `report-generator`, `cohort-analyser`, `email-dispatcher`, `squarespace-exporter`. Spec §2 cadence verbatim.

## 4. Data model (Postgres) — load-bearing tables

Spec §3 verbatim, plus three implementation notes:

- All numeric columns `DOUBLE PRECISION` (no `numeric`, no rounding at ingest).
- `audit_score_vectors.vec vector(8)` with HNSW cosine ops index for cohort similarity (§3).
- `archetype_taxonomies` first-class table; `archetype_assignments.taxonomy_id` FK so flip-without-loss (D-006).
- `events_log` is the audit trail for every state transition, agent run, Claude API call, Stripe webhook, email send. Schema: `id BIGSERIAL, occurred_at TIMESTAMPTZ, actor TEXT, action TEXT, severity TEXT, subject_id TEXT, payload JSONB`.

`schema.sql` lives at repo root and is applied on container boot via `db/init.d/`.

## 5. API surface

FastAPI per spec §6. Three role bands enforced via JWT claim `role ∈ {operator, executive, respondent}`. Magic-link login (email a 6-hr token; click → JWT).

Module layout:
- `app/api_server.py` — FastAPI app, routers, middleware
- `app/db.py` — psycopg pool, transaction helpers
- `app/auth.py` — magic-link issuance, JWT verification, role decorators
- `app/analytics.py` — pgvector similarity, cohort aggregates, DuckDB-attached read-only views (M9)
- `app/stripe_handlers.py` — checkout session, webhook
- `app/exports.py` — Squarespace bundle assembler, zip streamer

## 6. Agents

Per spec §5. All Python, stateless. Triggers split:
- **Event-driven** (audit-scorer, report-generator): drained from `audit_jobs` queue table; supervisord daemon polls every 2s.
- **Schedule-driven** (cohort-analyser nightly 02:00, pattern-hunter weekly Mon 03:00, email-dispatcher 60s).
- **API-driven** (squarespace-exporter, bespoke-builder).

Every agent runs through `agents/_base.py` `with fetch_log(...)` so success/error always lands in `events_log` + `data_fetch_log`.

## 7. Claude API integration

Per project rule, every Claude integration file reads `/mnt/skills/public/product-self-knowledge/SKILL.md` first.
- `claude-opus-4-7` — `report_generator`, `squarespace_exporter`, `priority-interventions` writer
- `claude-haiku-4-5-20251001` — `archetype_classifier` (structured), `bespoke_builder` (question extraction)
- Prompt prefixes cached via Anthropic prompt caching where the prefix exceeds ~2k tokens.
- All calls write a row to `events_log` with action='claude_api_call', payload JSON {model, input_tokens, output_tokens, cost_usd}.

## 8. Dashboard

React 18 + Vite 5 + TypeScript + Tailwind 3 (downstream of HIG token map).
- One codebase, three role routes: `/operator/*`, `/executive/*`, `/me`.
- Auth state hydrates from JWT in cookie; role drives route guard.
- Charts: Recharts (HIG-compliant defaults applied via wrapper components).
- Token map: `dashboard/src/styles/tokens.css` exports CSS custom properties matching `design/tokens.json` so dashboard + Squarespace bundle share one design source of truth.

## 9. HIG conformance

Verification pipeline (M11):
- `compliance/hig_audit.ts` Playwright script screenshots every page at 3 breakpoints (375 / 768 / 1440) in both colour schemes.
- Headless contrast checker (axe-core) runs on every page.
- Vision-model UAT (Claude Opus, image input) flags spacing/hierarchy violations.
- Report written to `compliance/hig_audit_<ISO-date>.md`.

## 10. Security posture (prototype)

- Local-only binds (`127.0.0.1`) on all host ports.
- JWT HS256, secret in `.env`, never committed.
- Stripe webhook signed-payload verification.
- Magic-link tokens single-use, 6h expiry, rate-limited per email (10/hr).
- Postgres password in `.env` only.
- No cloud secrets at prototype stage; production hardening deferred to M12.

## 11. Observability

- `events_log` table is the single timeline (human-readable filter view on the Events Log dashboard page).
- `data_fetch_log` is the agent-run timeline.
- Mailpit captures every outbound email in dev; production provider adds delivery webhooks.
- Postgres logs surfaced via `docker compose logs db`.

## 12. Build sequence implications

- **M2 scaffolding** establishes the spine: ports → docker-compose → schema → /api/health → React shell. Everything else hangs off this.
- **M5 + M6 operator/exec dashboards** depend only on M2-M4. Can build in parallel after M4.
- **M11 HIG compliance** is a gate, not an addition. Each milestone running its own page-level HIG check shortens M11 to a final pass.

## 13. Open architectural questions

- Whether to run Vite dev server inside the app container or on host during dev. Lean: host (faster reload, simpler). Containerised production build at M12.
- Whether to use Anthropic Files API for the report PDF or only inline. Lean: inline (smaller, simpler) until report exceeds 1MB.
- pgvector HNSW `ef_construction` / `m` tuning: defaults are fine at prototype scale (<10k respondents). Re-tune at M9 if cohort searches slow.

---

*End of architecture. Hand to Sally for UX.*
