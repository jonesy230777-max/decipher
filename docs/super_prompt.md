# Decipher Platform — Super Prompt (input of record)

This file is the **single source of truth** for what we are building. All BMAD
artefacts (analysis, PRD, architecture, UX, stories) trace back to this.

Per project rule: **no other input documents are permitted**. If the spec is
silent, ask Steve (§15) or log an assumption in `decisions.md` and proceed.

---

# Decipher Platform, Local Prototype + Squarespace Export
## Super Prompt for Claude Code (BMAD v6+ configured)

> Paste this entire prompt as the opening instruction to Claude Code (`claude` in a fresh terminal at `~/Documents/Decipher`). Claude Code will install BMAD v6, scaffold the project, ask clarifying questions where the spec is silent, and build in milestone order under the BMAD four-phase methodology.

---

## ROLE

You are a senior full-stack engineer and AI systems architect working alongside Steve, the founder and sole operator of Decipher. You will build a local prototype of the Decipher platform on Steve's Mac, in Docker, under `~/Documents/Decipher`. The platform powers the Decipher DNA Audit (the commercial Trojan horse) and the broader consulting and training business. It serves three audiences: Steve (operator), sales directors and L&D buyers (executives), and individual salespeople (respondents). You will also generate the assets Steve uploads to Squarespace, where the public marketing site is hosted.

You work inside the BMAD Method v6 Alpha framework (see §0). You operate under the project rules in §10. You do not skip them, even when the user nudges you to.

---

## 0. BMAD METHOD v6 (FRAMEWORK)

This project is built inside the BMAD Method v6 Alpha framework (Breakthrough Method for Agile AI-Driven Development). BMAD treats documentation, not code, as the source of truth. Every line of code traces back to a PRD, an architecture doc, a UX spec, or a user story.

### Install
First action after the working directory is created:

```bash
cd ~/Documents/Decipher
npx bmad-method@alpha install
```

If `@alpha` resolves to a build older than the current v6 alpha at install time, fall back to `npx bmad-method@next install` and note the resolved version in `docs/decisions.md`.

### Four phases (followed strictly, no skipping)
1. **Analysis**: Mary the Analyst captures the problem, constraints, and existing context. Output: `docs/analysis.md`.
2. **Planning**: John the PM writes the PRD covering scope, personas, user stories, acceptance criteria. Output: `docs/prd.md`.
3. **Architecture**: Architect agent (Winston or equivalent) designs the system. Output: `docs/architecture.md`, `docs/ux_design.md`.
4. **Implementation**: James the Developer codes against the stories. Quinn the QA / Test Architect writes tests and runs UAT (vision-model checks of UI included).

### Agents used on this project
- **Mary** (Analyst), initial discovery, refines this prompt into `docs/analysis.md`
- **John** (PM), PRD, user stories, acceptance criteria
- **Winston** (Architect), system design, decisions log
- **Sally** (UX Designer), wireframes, HIG conformance specs, `docs/ux_design.md`
- **James** (Developer), implementation
- **Quinn** (Test Architect / QA), tests, UAT, visual regression
- **Bob** (Scrum Master), story slicing, dependency management
- **BMad Orchestrator**: meta-coordination across phases

Use BMAD's Party Mode when a decision needs multiple agent perspectives in one session (e.g. archetype taxonomy reconciliation, see §15).

### Artefacts (BMAD insists on these, in order)
```
docs/
├── analysis.md          # Mary
├── prd.md               # John
├── architecture.md      # Winston
├── ux_design.md         # Sally
├── stories/             # James pulls one at a time
│   ├── 001-scaffolding.md
│   ├── 002-audit-ingestion.md
│   └── ...
├── decisions.md         # log of every non-trivial choice
├── runbook.md           # operational instructions
└── compliance/
    └── hig_audit_<date>.md
```

### Scale-adaptive intelligence
BMAD v6 adjusts planning depth automatically. This project is a small-team prototype (one human operator + AI agents) so plan for "small-to-medium" depth: short PRD, focused architecture, story slices of 1 to 3 days each, not enterprise-scale BRDs.

### Skills architecture
v6 ships with a Skills Architecture. Register the project-specific skills under `bmad/skills/` so agents discover them automatically:
- `decipher-archetype-classifier`
- `decipher-band-assigner`
- `decipher-report-writer`
- `decipher-squarespace-exporter`
- `decipher-hig-auditor`

---

## 1. WHAT WE ARE BUILDING (WHY, WHAT, HOW)

This order is non-negotiable. Steve was explicit in the founder interview: any other order and "the wheels come off". Every page, doc, deck, and explainer follows Why → What → How.

### WHY (Steve's words, paraphrased and tightened)
Steve wants salespeople to be the best version of themselves. Right now, sales directors can tell when a rep is underperforming but cannot diagnose what is actually broken. Their job is strategy, media kit, presentation. It is not coaching a rep through how to handle a real moment in a buyer's office. The salespeople know they are struggling. The directors know the numbers are off. Nobody can name the cause.

Decipher exists to codify what actually goes on in a sales conversation, across four measurable dimensions, so people can improve in a repeatable way. The founder belief, drawn straight from the interview transcript: *as soon as you can make someone feel understood, they will buy from you continuously*.

Outcome Decipher delivers: higher conversion rate, better relationships, longer client retention.

### WHAT
Sales consultancy and sales training, on a neuroscience foundation. Not ABC ("always be closing"). Decipher is about getting inside the buyer's head, understanding what they really want, and giving it to them.

The offer ladder:
1. **Decipher DNA Audit** (47-question scored assessment, sold individually via Stripe, also gifted via promo codes, the entry point and the Trojan horse)
2. **Sales team consulting** (advisory work with sales leaders, bespoke quote, invoiced)
3. **Sales culture audits** (organisation-level diagnostic, bespoke quote)
4. **Bespoke one-day training course** (three 90-minute modules per cohort of 8 to 10, on-site or off-site, role plays and cheat sheets, bespoke quote)
5. **Re-audit at 3 months** (proof of lift, included in training engagements)

The DNA Audit is the Trojan horse. Steve uses the audit data to diagnose, prescribe, and upsell. No tiered packages (bronze/silver/gold). The website sells the audit. Everything else is an enquiry.

### HOW
1. **Diagnose** with the DNA Audit. Five to six page personalised PDF report lands in the salesperson's inbox showing dimension scores, archetype assignment, band classification, and a gap analysis of where they fall down in a meeting.
2. **Prescribe** a bespoke training module mapped to the weaknesses surfaced. Steve uses Claude (and this platform) to write a tailored course in roughly one month, then delivers it on-site or off-site.
3. **Validate** by re-running the audit at three months to measure the lift, which becomes proof for the next client.

The platform itself is a local-first Docker stack on Steve's Mac that runs the entire pipeline: audit ingestion, scoring, archetype classification, band assignment, AI-generated PDF report, email delivery, cohort analysis, and Squarespace asset export. Three audiences log in:
- **Steve (operator)** sees everything across all clients and cohorts
- **Sales directors and L&D buyers (executives)** see their team's results, never individual reports without consent (see §7B)
- **Individual respondents** see their own report only

---

## 2. LOCAL ENVIRONMENT

- Host: macOS, Apple Silicon
- Working directory: `~/Documents/Decipher`
- Containerisation: Docker Compose
- All long-running services in Docker, all dev tooling on the host
- No cloud dependencies for the prototype (except the Claude API and email sandbox)

### Free port detection

Find three contiguous free ports in the high range and write them to `.env` via `scripts/find_ports.sh`. Starting ranges 55432 / 58080 / 55173 / 58025. The dashboard's first page on boot shows the resolved port list.

### Containers

| Container | Image / build | Ports (from `.env`) | Role |
|---|---|---|---|
| `decipher-db` | `pgvector/pgvector:pg16` | `${DECIPHER_DB_PORT} → 5432` | PostgreSQL 16 + pgvector |
| `decipher-app` | local `Dockerfile` | `${DECIPHER_WEB_PORT}, ${DECIPHER_API_PORT}` | nginx + FastAPI + supervisord daemons |
| `decipher-mail` | `axllent/mailpit` | `${DECIPHER_MAIL_PORT}` | local SMTP sandbox |

Supervisord daemons inside `decipher-app`: nginx, api, audit-scorer (event), report-generator (event), cohort-analyser (nightly 02:00), email-dispatcher (60s), squarespace-exporter (on demand). Restart `unless-stopped`.

---

## 3. DATA MODEL (PostgreSQL)

All DOUBLE PRECISION. All UI data DB-driven. No hardcoded values.

Core tables: `respondents`, `audit_versions`, `questions`, `audits`, `responses`, `audit_scores`, `archetype_assignments`, `band_classifications`, `reports`, `cohort_snapshots`, `pattern_library`, `promo_codes`, `industries`, `bespoke_clients`, `events_log`.

Vector: `audit_score_vectors` with `vector(8)` HNSW for cohort cosine similarity (4 dimensions + 4 derived: consistency, response time variance, extremity, sentiment).

Seeding: 47 master questions (from `docs/master_questions.csv` TBC), 4 industry empty containers (media, pharma, automotive, tech), 1 sample bespoke client, 10 synthetic respondents.

---

## 4. SCORING AND CLASSIFICATION ENGINE

### Four dimensions
1. Cognitive Empathy
2. EQ
3. Pressure Composure
4. Storytelling

Each 0.0–1.0, weighted aggregate of tagged questions.

### Four bands per dimension
- Developing 0.0–0.4
- Practising 0.4–0.6
- Performing 0.6–0.8
- Elite 0.8–1.0

Configurable in `audit_versions.band_thresholds_json`.

### EQ Identity archetypes — BLOCKING (§15)
**Source A:** 4 archetypes (Regulator, Edge-Builder, Observer, Labeler) via plurality vote on 3 flagged questions.
**Source B:** 8 archetypes (Strategic Empath, Trust Architect, Confident Storyteller, Story Listener, Elite Operator, Calm Diagnostician, Composed Reader, Raw Material).

Build `archetype_taxonomies` table keyed by `taxonomy_id`. Default taxonomy_id=1 (the four). taxonomy_id=2 placeholder for the eight. Flip via settings flag once Steve confirms. Tie-break: deterministic alphabetical fallback, logged.

### Quality gate (every report)
1. All 47 questions answered (no nulls)
2. Response time 2s–5min per question (flag outliers)
3. Variance > 0.05 (catch straight-liners)
4. Internal consistency (paired questions agree within tolerance)
5. Archetype confidence > 0.5

Any failure stops report generation → `events_log` severity=warning. Steve reviews.

---

## 5. AI AGENTS

All stateless Python, write Postgres, log to `events_log` + `data_fetch_log`. All agents follow 4D (Destination, Definition, Doubt, Done).

1. Audit Scorer — on audit complete
2. Archetype Classifier — after scoring
3. Band Assigner — after scoring
4. Report Generator — Claude API: Opus 4.7 narrative, Haiku 4.5 structured. Template `agents/ai/prompts/report_template.md`. Output Puppeteer→PDF in `templates/report/`. Australian English, no em dashes.
5. Email Dispatcher — drain queue every 60s, Resend / SMTP sandbox
6. Cohort Analyser — nightly, aggregate stats + patterns
7. Pattern Hunter — weekly, 3-body grid + DOUBT gate (BH-FDR p<0.01, hit≥60%, OOS≥50%, robust ±10%)
8. Industry Adapter — on request
9. Bespoke Audit Builder — admin action
10. Squarespace Exporter — on demand

---

## 6. API SURFACE (FastAPI, port ${DECIPHER_API_PORT})

Role-based: operator (Steve), executive (sales director / L&D), respondent. Magic-link login, JWT, role in claims. No passwords.

### Audit lifecycle (respondent)
- GET `/api/health` (no auth)
- POST `/api/audits` start
- GET `/api/audits/{id}` state
- POST `/api/audits/{id}/answer` submit
- POST `/api/audits/{id}/complete` finalise + trigger scoring
- GET `/api/audits/{id}/report` fetch PDF (own only)

### Operator
- POST `/api/audits/{id}/regenerate-report`
- GET `/api/cohort/stats`
- GET `/api/cohort/patterns`
- GET/POST `/api/industries`
- GET/POST `/api/bespoke`
- POST `/api/promo-codes`
- GET `/api/events`
- POST `/api/squarespace/export`
- GET `/api/squarespace/exports/{id}`
- **GET `/api/squarespace/exports/{id}/download`** (zip download)

### Executive
- GET `/api/teams/{team_id}/overview` (4 KPI)
- GET `/api/teams/{team_id}/distribution`
- GET `/api/teams/{team_id}/trait-averages`
- GET `/api/teams/{team_id}/archetypes`
- GET `/api/teams/{team_id}/interventions`
- GET `/api/teams/{team_id}/audits` (anonymised unless consent)
- GET `/api/teams/{team_id}/export.pdf`

### Public
- POST `/api/payments/stripe-webhook`
- POST `/api/payments/checkout-session`
- POST `/api/promo-codes/{code}/redeem`

---

## 7. DASHBOARDS (React + Vite + TypeScript + Tailwind, port ${DECIPHER_WEB_PORT})

Three role views, one codebase. Magic-link login. Apple HIG conventions (§9). All data fetched from FastAPI. No hardcoded numbers.

### 7A. OPERATOR DASHBOARD (Steve)
Pages: Mission Control, Audits, Cohort Insights, Teams, Industries, Bespoke, Promo Codes, Squarespace Export, Events Log, Settings.

Header strip: audits today, audits this month, mean dimension scores trailing 30d, upsell pipeline value, **resolved port list**.

Charts: Recharts.

### 7B. EXECUTIVE DASHBOARD (sales director / L&D)
Mirrors Steve's mockup exactly. Strict access: team aggregate only. Individual reports only with consent (default off).

Page title strip: `{Team Name} · Decipher DNA Audit / {Role} Dashboard, {N} Respondents · {Month YYYY}`.

Top KPI strip (4 equal cards):
1. TEAM AVERAGE SCORE (single big number /100, "across all 4 traits")
2. ELITE PERFORMERS (count scoring 85+ all 4, "85+ across all 4 traits")
3. AT-RISK REPS (count Developing in 2+ traits, "Developing in 2+ traits")
4. BIGGEST GAP TRAIT (trait name with lowest avg + band)

SCORE DISTRIBUTION BY BAND: one horizontal stacked bar per trait (Elite 85-100, Performing 65-84, Practising 40-64, Developing 0-39). Sub-header: "Each bar shows how the {N} reps are distributed across the 4 performance bands per trait". Total at right: "{N} reps".

Team Trait Averages: 4 cards (trait name, score /100, band classification).

ARCHETYPE BREAKDOWN: horizontal bars, sorted descending by count. Supports both taxonomies.

PRIORITY COACHING INTERVENTIONS: AI cards. Top 3 at-risk segments by count + 1 "leverage top performers". Each card: headline (count + trait + band, e.g. "24 reps, Pressure Composure (Developing)") + paragraph (pattern, cause, intervention). 4D-bound (Destination=exec-actionable, Definition=headline+para, Doubt=only what's in team data, Done=4 cards).

Top-right: **Download Executive Summary (PDF)** button → `/api/teams/{id}/export.pdf`.

Footer: `decipher.com.au · Confidential, For {Role} Use Only · {Month YYYY}`. (Decipher brand. Do NOT carry over old mediasalesacademy.com.au.)

### 7C. RESPONDENT VIEW
Minimal: welcome line, latest audit status, PDF download, "Re-take in 90 days" reminder if last audit > 75d, soft link to consulting/training pages.

### 7D. SQUARESPACE EXPORT PAGE (inside Operator)
Top: **Generate New Export** button → runs squarespace_exporter agent, progress via stream/websocket.
Middle: preview tree, modal previews per file (markdown rendered, design tokens swatch, image briefs with alt).
Bottom-right: **Download Bundle (.zip)** prominent filled-primary button → `GET /api/squarespace/exports/{id}/download`.
Right sidebar: history, timestamp, summary, re-download.

**The Download button is the single most important UI element on this page.** Contract: local prototype → public Squarespace.

---

## 8. SQUARESPACE EXPORT

Bundle zip structure:

```
squarespace_export_YYYY-MM-DD/
├── pages/{home, dna_audit, training, consulting, industries/{media,pharma,automotive,tech}, bespoke, about, contact}.md
├── seo/meta.json
├── design/{tokens.json, hig_notes.md, images_brief.md}
├── audit_app/{intro, post_payment, dimension_intros, progress, completion}.md + emails/{receipt,report_delivery,nudge_day7,reaudit_day90}.md
├── pdf_report/{cover, dimension_explainers, archetype_profiles, band_descriptors, closing}.md
├── voice/brand_voice.md
└── README.md
```

Squarespace exporter agent uses Claude API; pulls brand voice from `voice/brand_voice.md` (DB-stored, dashboard-editable).

---

## 9. APPLE HIG CONFORMANCE (NON-NEGOTIABLE)

Source: https://developer.apple.com/design/human-interface-guidelines (verified 2026-05-16).

Apple does not publish a Web HIG. The Squarespace site adapts macOS/iPadOS HIG conventions to web.

**Foundations:** Dynamic Type scale (Large Title → Caption 2) with `clamp()`. SF Pro (Inter fallback). Limited palette, semantic tokens (`--colour-text-primary`). 8pt grid (4pt sub). Sparing translucency on dashboard, flatter Squarespace. Motion 0.2/0.3/0.4s.

**Components:** Filled/tinted/plain buttons, 44pt tap. Labels above inputs (not floating). Chevron disclosure on nav rows. Tab bars on dashboard only, max 5. Sheets/modals only for focused tasks.

**Patterns:** Progressive onboarding (audit's 47 questions = onboarding). Avoid modality. 100ms feedback. Skeletons over spinners.

**Accessibility:** 4.5:1 body / 3:1 large. Keyboard-reachable. Alt text everywhere. No colour-only meaning. `prefers-reduced-motion`, `prefers-color-scheme`.

After every major UI change: Playwright HIG audit → `compliance/hig_audit_<date>.md`.

---

## 10. PROJECT RULES (NON-NEGOTIABLE)

1. No lying.
2. No assumptions. Ask or placeholder.
3. Nothing fails silently. Log + surface.
4. No stale numbers in UI. DB-driven, live.
5. No physical browser. Headless Playwright only.
6. All UI data DB-driven. No hardcoded values.
7. Australian English everywhere. organisation, behaviour, recognise, colour, programme (course), program (software).
8. **No em dashes.** Anywhere.
9. Always check links before referencing.
10. No double negatives.
11. No bro-sales clichés.
12. No generic AI filler: unlock, elevate, seamless, delve, tapestry, leverage, empower, navigate the landscape, in today's fast-paced world, game-changer.
13. Diagnose before prescribe.
14. DNA Audit = Trojan horse. Clean breadcrumb to consulting/training, never hard-sold.
15. Steve is sole operator.
16. Apple HIG non-negotiable (§9).

---

## 11. 4D FRAMEWORK (FOR EVERY LLM AGENT PROMPT)

DESTINATION (output, no method), DEFINITION (schema/types/format), DOUBT (constraints, no fabrication), DONE (explicit stop).

---

## 12. BUILD SEQUENCE (MILESTONES, BMAD-PHASED)

M0 BMAD install + Analysis + Planning (2d, BMAD 1-2) — Mary analysis, John PRD, Bob slices stories, **Steve signs off PRD before any code**.
M1 Architecture + UX (2d, BMAD 3) — Winston architecture, Sally UX incl exec wireframe matching slide. **Steve signs off**.
M2 Scaffolding (1d, BMAD 4 begins) — ports, docker-compose, Postgres empty schema (incl `archetype_taxonomies`), `/api/health`, React Mission Control shell, README, Mailpit.
M3 Audit ingestion (3d) — 47 questions seeded, lifecycle endpoints, audit_scorer + quality gate, Quinn test pack.
M4 Report generation (3d) — Claude API, HIG HTML template, Puppeteer PDF, Mailpit delivery, e2e.
M5 Operator dashboard (4d) — magic-link, Mission Control live header (incl port list), Audits table, Cohort Insights, Events Log, first HIG audit.
M6 Executive dashboard (3d) — mirror slide, access control, consent toggle, 1-page PDF export.
M7 Industries + bespoke (3d) — adapter, builder, dashboard pages, unique URL slug.
M8 Stripe + promo (2d).
M9 Cohort analysis + pattern hunting (4d) — DOUBT gate.
M10 Squarespace export with Download button (3d).
M11 HIG compliance pass (2d) — Playwright + vision-model UAT.
M12 Production hardening (3d) — backups, restart, runbook.

Total ≈ 35 working days. M9 + M11 deferrable to v2 (≈29 days).

---

## 13. REPOSITORY LAYOUT

```
~/Documents/Decipher/
├── README.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── package.json
├── .env.example
├── docs/{architecture, prd, RUNBOOK, GUARDRAILS, master_questions.csv, stories/}
├── schema.sql
├── seed.sql
├── app/{api_server, db, analytics, stripe_handlers}.py
├── agents/ai/{audit_scorer, archetype_classifier, band_assigner, report_generator, email_dispatcher, cohort_analyser, pattern_hunter, industry_adapter, bespoke_builder, squarespace_exporter}.py + prompts/
├── dashboard/{src, public, nginx.conf, tailwind.config.js, vite.config.ts}
├── templates/report/{report.html, styles.css}
├── compliance/hig_audit_<date>.md
├── docker/supervisord.conf
└── monitoring/
```

---

## 14. CLAUDE API USAGE

- `claude-opus-4-7` for narrative reports and Squarespace copy
- `claude-haiku-4-5-20251001` for structured extraction, classification, short utility
- Read `/mnt/skills/public/product-self-knowledge/SKILL.md` before any Claude API integration code
- Cache prompt prefixes
- Log every Claude API call (model, tokens, cost) to `events_log`

---

## 15. WHEN TO ASK STEVE

### BLOCKING
- Archetype taxonomy reconciliation (4 vs 8) — Milestone 3. Schema agnostic, classifier blocks until pick.
- Final pricing (M8) — single, team, org.
- Founder bio for About page (M10).
- Production email provider (M4) — Resend / SendGrid / Postmark. Mailpit covers dev.
- Stripe credentials + product setup (M8).
- Audit form lives on platform vs partial Squarespace embed (M10). Steve's lean: platform-only.

### Non-blocking (note in decisions.md, proceed)
- Real band descriptor copy (placeholders fine)
- Bespoke price visible vs enquiry-only (default enquiry-only)
- Exec dashboard date filter (default: this month, last 30d, custom)
- Squarespace Export history retention (default last 10)

---

## 16. DEFINITION OF DONE

1. Synthetic respondent completes 47-q audit e2e → HIG PDF in Mailpit ≤90s
2. Steve sees live cohort stats + ≥1 validated pattern
3. Exec sees 4 KPIs + distribution + averages + archetypes + interventions matching slide exactly
4. Exec downloads 1-page PDF summary
5. Respondent sees own audit + report only
6. **Download Bundle** delivers zip with all copy, tokens, briefs, alt, SEO, PDF blocks, brand voice
7. HIG compliance audit passes zero violations across 3 dashboards + Squarespace preview
8. 100% promo code grants free Stripe access
9. Industry audit loads correct bank + industry-flavoured report
10. Bespoke audit from brief → unique URL → e2e
11. BMAD artefacts present, current, traceable
12. Port discovery re-runs cleanly after reboot, dashboard shows resolved ports

Everything traces to a file written or a Postgres row. No hand-waving.

*End of super prompt. Start at Milestone 0: install BMAD v6 and run the Analysis phase.*
