# Decipher · BMAD codebase review

**Date:** 2026-05-16
**Scope:** backend + repository hygiene only (UI/UX and brief-conformance covered in sibling reports).
**Method:** independent agent grounded in `CLAUDE.md`, `docs/architecture.md`, `docs/decisions.md`, `app/`, `schema.sql`, `docker-compose.yml`, `requirements.txt`, `scripts/`.

## P0 (ship-blocking)

- **`app/api_server.py:2037`** `respondent_detail(viewer_role: str = "admin")` — role is a query-param trivially spoofed (`?viewer_role=admin`). Identity gating collapses. Rule 6 + Role-taxonomy violation. **Fix:** delete the param; resolve role server-side from session/JWT (M5) and, until then, from a signed cookie populated by `/api/auth/login`.
- **`app/api_server.py:2107` (`team_audits`), `:303` (`team_gap_analysis`), `:1083` (`team_overview`), `:1173` (`team_distribution`), `:1206` (`team_trait_averages`), `:1239` (`team_archetypes`), `:1256` (`team_interventions`), `:1329` (`team_export.pdf`), `:2619` (`team_roster`)** — zero RBAC. Any caller can hit `/api/teams/{any_team_id}/...` and read another company's data. Rule 6 (no leaks between teams/companies) is broken across the entire executive surface. **Fix:** wrap every team-scoped route in a `require_team_access(caller, team_id)` that joins caller role with their `team_id`/`company_id`.
- **`app/api_server.py:1576` `_resolve_caller_role`** — trust model is fake. If `actor_email` is unknown it falls back to `admin`. Any unauthenticated POST to `/api/users`, `/api/companies`, `/api/teams`, `/api/promo-codes`, `/api/audit/invite/bulk` runs as admin. **Fix:** default to `None` and 401; never silently elevate.
- **`app/api_server.py:2324` `/api/auth/login`** — password = SHA-256(salt + password). No work factor, no rate-limit, no lockout. **Fix:** `bcrypt` or `argon2-cffi`; add per-email throttle.
- **`app/api_server.py:2359` `/api/auth/demo-credentials`** — public endpoint that returns five real working passwords in cleartext including the admin. Anyone who can hit the API can become Steve. **Fix:** gate behind `DECIPHER_ENV=dev` env check or delete; on prod, 404.
- **`.env:11`** `JWT_SECRET=change-me-in-prod` checked into the repo path. **Fix:** confirm `.env` in `.gitignore`, rotate the secret, and add a startup assertion that refuses to boot if it equals the default.
- **`app/api_server.py:34-40`** `CORSMiddleware(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])`. Combined with cookie auth (M5) this is a CSRF/CORS hole. **Fix:** pin to `http://127.0.0.1:${DECIPHER_WEB_PORT}` and the prod origin only.
- **`schema.sql`** — schema drift, ~5 tables missing: `narrative_library`, `audit_invites`, `role_permissions`, plus columns on `respondents` (`first_name`, `last_name`, `mobile`, `job_title`, `location`, `timezone`, `password_hash`, `password_salt`), `companies` (`contact_*`, `website`, `country`, `abn`), `teams` (`region`, `country`, `contact_*`), `reports` (`delivered_at`, `recipient_email`). Fresh `docker-compose up` on a clean volume boots a broken DB. **Fix:** consolidate every script-applied DDL into `schema.sql` (or stand up Alembic).
- **`app/api_server.py:2777` `/api/audit/{audit_id}/complete`** — no idempotency or locking. Two concurrent `/complete` calls both pass the coverage check, both render the PDF, both email. **Fix:** `SELECT … FOR UPDATE` on `audits` row, plus early return if `status IN ('scored','reported')`.

## P1 (next-sprint)

- **2923-line `api_server.py` monolith.** Natural seams to extract: `auth.py`, `routers/teams.py`, `routers/companies.py`, `routers/audits.py`, `routers/invites.py` (with `_send_invite_email` + `_send_report_email`), `routers/squarespace.py`, `routers/reports.py`, `routers/search.py`, `routers/ai.py`, `routers/permissions.py`, `pdf/team_export.py` (lift the 220-line PDF builder out of an endpoint), `services/scoring_pipeline.py` (the `score → report → email` triplet duplicated at lines 2818-2841 and 2854-2860).
- **No `tests/` directory.** Top-6 must-test units in order: (1) `dna_scoring._normalise` + `_pick_archetype` + `_band_for` (pure, gold-standard fixtures from the brief); (2) `audit_complete` completeness gate + idempotency; (3) RBAC matrix `_role_can` × every capability; (4) `_resolve_caller_role` spoof resistance; (5) team scoping (caller in team A cannot read team B); (6) every f-string SQL builder via parametric inputs.
- **`audit_invite` inline SMTP in request handler with 5-second timeout** — if Mailpit is down the request waits then logs `delivered=False`. Same issue at `:2835` (report email blocks `/complete`). **Fix:** push onto the `audit_jobs` table and have a worker drain it.
- **`team_export_pdf`** — inline reportlab in request thread, 200+ lines, plus the `new_page()/page_num` closure-with-list hack at `:1358-1373`. PDF generation should be a job; the endpoint should return a `report_id` to poll. Same for `dna_report.generate_report` chained inside `/complete`.
- **`squarespace_generate`** — fake numbers: `file_count = 47`, `size_bytes = 1_250_000`, `cost = 0.18 + (microsecond % 14)/100`. CLAUDE.md Rule 2 ("never fabricate data") + Rule 4 ("no stale numbers"). Either build the real bundle or return `{"status": "stub"}` rather than fake rows persisted to `squarespace_exports`.
- **`squarespace_export_download`** — serves a "DUMMY placeholder" zip to anyone calling the endpoint while persisting it as if real.
- **`audit_invite_bulk`** — `except Exception: failed += 1` swallows the actual error. CLAUDE.md Rule 3 ("nothing fails silently"). **Fix:** capture `str(exc)` per target and return in the response.
- **`/api/health`** returns `degraded` body but `200 OK`. Container healthcheck cannot trip. **Fix:** raise 503 with body.
- **`audit_invite`** swallows SMTP errors and returns `delivered=False`. The frontend has no way to know whether the issue was rejection, timeout, or auth. **Fix:** structured `error_code` field.
- **`requirements.txt`** — unused deps: `anthropic`, `playwright`, `PyJWT`, `httpx`, `python-multipart`, `python-dotenv` are never imported in `app/` or `scripts/`. Each is supply-chain surface. Either wire them in or remove.
- **`docker-compose.yml`** — no `decipher-app` container despite `docs/architecture.md` §2 listing it. FastAPI runs on the host. Either ship the app container or correct the architecture doc.
- **`app/api_server.py:23-30` `_active_taxonomy_id`** — module-level cache. If the operator toggles the active taxonomy at runtime, every endpoint keeps returning the old id until process restart. **Fix:** drop the cache or invalidate on PATCH.

## P2 (polish / scale)

- **`bootstrap()`** fires 14 sequential round-trips. Each is `host=127.0.0.1` with `autocommit=True`. Page first-paint is bound by this. **Fix:** one `WITH` query, or materialised view refreshed by `cohort-analyser`.
- **`companies_list` + `teams_list`** — N+1 per company/team for `n_teams`, `n_reps`, `avg`, `elite`, `at_risk`, `bands`. With 50 companies that's 300 queries. **Fix:** single GROUP BY.
- **`app/db.py:26`** — `max_size=8` connection pool. With the N+1 patterns above, 8 concurrent dashboard loads saturate. Raise or batch.
- **`search()` runs 7 separate ILIKE queries against unindexed columns.** `schema.sql` enables `pg_trgm` but no `gin_trgm_ops` indexes exist on any of these columns. **Fix:** `CREATE INDEX ... USING gin (name gin_trgm_ops)` on respondents/teams/companies/bespoke_clients/promo_codes.
- **`/api/ai/ask`** pretends to be an AI endpoint, hard-codes string replies. Either label `/api/ai/stub` or wire to Claude (Rules 1 + 2).
- **`_send_report_email`** reads PDF off disk after `generate_report` just wrote it. Pass bytes through to avoid second IO + race.
- **`scripts/seed_polish.py`** — backdates audits and forces 8 elite. Useful for demos but should not run on prod boot. Gate with `DECIPHER_ENV`.
- **Scripts classification:**
  - must-have-CI: `find_ports.sh`
  - useful tool (keep, document): `backfill_scoring.py`
  - one-off seeders → fold into `schema.sql` + `seed.sql` or move to `scripts/_archive/`: `parse_brief.py`, `fix_media_sales_v1_questions.py`, `seed_media_sales_dna_v1.py`, `seed_archetype_descriptions_and_eq_identities.py`
  - demo-only, gate with env var: `seed_dummy.py`, `seed_polish.py`
- **`audit_invites.token_hash`** stores the raw token, not a hash. Misnamed and insecure. **Fix:** store `sha256(token)`; compare on consumption.
- **Invite link** bakes `localhost` into emails. **Fix:** `PUBLIC_BASE_URL` env.

## P3 (nice-to-have)

- `REPORT_DIR.mkdir(parents=True, exist_ok=True)` at import time fails on read-only FS. Move into the first call.
- `_band_for` duplicated across `api_server` and `dna_scoring` with different thresholds (0.80 vs 0.85). Two sources of truth.
- Hard-coded band thresholds inlined three places. Move to `audit_versions.band_thresholds_json` and read.
- HTML emails interpolate `name`/`link` unescaped. Low-risk, XSS-shaped.
- No `ON DELETE` for `respondents.team_id`/`company_id`. Deleting a company orphans respondents silently.
- `datetime.utcnow()` deprecated in 3.12; use `datetime.now(timezone.utc)`.
- `docs/architecture.md:71-86` describes `auth.py`, `analytics.py`, `stripe_handlers.py`, `exports.py`, `agents/_base.py` — none exist.

## Architectural recommendations

1. **Split `api_server.py` along resource lines.** Each router gets a router-level dependency that resolves caller identity + capability. The current "every endpoint re-derives role from the body" pattern is the root cause of the P0 RBAC findings.
2. **Stand up a real auth layer this sprint**, not at M5. Cookie + signed session is enough; the prototype currently has no enforced identity, which makes every other rule moot. Drop `viewer_role`/`actor_role`/`invited_by_role` from request bodies entirely.
3. **Move PDF + email out of request handlers** onto the `audit_jobs` queue that `schema.sql` already defines.
4. **Codify schema in one place.** Either keep `schema.sql` as the boot script and bring drifted DDL into it now, or adopt Alembic.
5. **Write the first 100 tests against pure functions and SQL builders** before any new feature. `dna_scoring` is fully unit-testable with no DB. The RBAC matrix is a 6×16 truth table.

## Single most dangerous lines

- `app/api_server.py:2037` (`viewer_role: str = "admin"` query param) — nullifies the entire consent model.
- `_resolve_caller_role` defaulting to `"admin"` (line 1588) — every "RBAC-protected" mutation is actually open. `_require_capability` plumbing is theatre until that default changes.
