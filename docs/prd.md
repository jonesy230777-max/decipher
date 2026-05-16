# Decipher — PRD (BMAD Phase 2, John)

**Input:** `docs/analysis.md`, `docs/super_prompt.md`.
**Date:** 2026-05-16.
**Author:** John (PM).
**Scale:** small-to-medium prototype.

---

## 1. Product summary

Decipher is a local-first sales DNA platform. It runs Steve's Mac on Docker. A respondent completes a 47-question audit; the platform scores them across 4 dimensions, classifies an archetype, assigns bands, generates a personalised 5–6 page PDF report via the Claude API, and emails it. Sales directors see team-level diagnostics. Steve sees everything plus a Squarespace asset exporter that produces the bundle for the public marketing site.

## 2. Goals + non-goals

**Goals**
1. End-to-end audit → PDF in ≤ 90 seconds.
2. Three role-based dashboards (operator, executive, respondent), all HIG-compliant.
3. Generate a complete Squarespace asset bundle (zip download).
4. Cohort intelligence: validated patterns across respondents, surfaced in the operator dashboard.
5. Strip-mall-simple ops: one Mac, one operator, one runbook.

**Non-goals**
- SaaS multi-tenancy.
- Mobile app.
- Direct Squarespace API integration (Steve uploads by hand).
- Real-money trading or any non-sales-training feature.

## 3. Personas (recap from analysis.md)

| | Steve | Executive | Respondent |
|---|---|---|---|
| Role | Operator | Sales Director / L&D Buyer | Salesperson |
| Sees | Everything | Their team aggregate (consent gates individuals) | Self only |
| Auth | Magic link | Magic link | Magic link |
| Primary goal | Generate Squarespace bundle, monitor cohort, run business | Diagnose team, prioritise coaching | Take audit, get report, improve |

## 4. User stories + acceptance criteria

Stories live under `docs/stories/`. Each is sliced 1–3 days. Bob the Scrum Master writes them; James the Developer pulls one at a time. Acceptance criteria mirror spec §16 Definition of Done.

### Epic A — Audit lifecycle (respondent)
- **S001** Respondent starts an audit and receives the question sequence.
- **S002** Respondent submits answers one at a time; state persists.
- **S003** Respondent completes the audit; scoring fires automatically.
- **S004** Respondent receives the PDF report by email within 90 seconds of completing.
- **S005** Respondent logs in via magic link and sees their own report (no cohort, no others).

### Epic B — Scoring + classification
- **S010** Audit scorer computes 4 dimension scores from tagged responses.
- **S011** Quality gate runs (5 checks); failures logged + report blocked.
- **S012** Archetype classifier assigns 1 of N archetypes (N = active taxonomy) with confidence.
- **S013** Band assigner maps each dimension score to {Developing, Practising, Performing, Elite}.
- **S014** Archetype taxonomy is settings-flag switchable between Source A (4) and Source B (8).

### Epic C — Report generation
- **S020** Claude API integration via the product-self-knowledge skill (Opus 4.7 narrative, Haiku 4.5 structured).
- **S021** Report HTML template is HIG-compliant (typography, spacing, colour, contrast).
- **S022** Puppeteer renders HTML → PDF, branded.
- **S023** Email dispatcher drains queue every 60s, sends via Mailpit (dev) / production provider (deferred).
- **S024** Every Claude call logged to `events_log` (model, tokens, cost).

### Epic D — Operator dashboard (Steve)
- **S030** Magic-link login + role-based routing.
- **S031** Mission Control header strip: audits today/month, mean dimension scores 30d, pipeline value, resolved port list.
- **S032** Audits table with filter/sort/detail drawer.
- **S033** Cohort Insights page: distribution charts + validated patterns from `pattern_library`.
- **S034** Events Log page.
- **S035** Industries CRUD page.
- **S036** Bespoke clients CRUD page + unique URL slug generation.
- **S037** Promo Codes CRUD page.
- **S038** Squarespace Export page with **Download Bundle** button (see Epic G).
- **S039** Settings page including archetype taxonomy flip (S014).

### Epic E — Executive dashboard
- **S040** Magic-link login for executive role.
- **S041** Page title strip per spec §7B.
- **S042** Top KPI strip (4 cards): Team Average Score, Elite Performers, At-Risk Reps, Biggest Gap Trait.
- **S043** Score Distribution by Band: one horizontal stacked bar per trait, sub-header per spec.
- **S044** Team Trait Averages: 4 cards.
- **S045** Archetype Breakdown: horizontal bars, supports either taxonomy.
- **S046** Priority Coaching Interventions: 4 AI-generated cards (3 at-risk + 1 leverage), 4D-bound.
- **S047** Download Executive Summary (PDF) button → one-page mirror.
- **S048** Consent toggle on individual respondent reports (default off); without consent, exec sees aggregates only.
- **S049** Footer per spec: `decipher.com.au · Confidential, For {Role} Use Only · {Month YYYY}`. No "mediasalesacademy" carry-over.

### Epic F — Industries + bespoke
- **S050** Industry adapter swaps question bank at audit start based on industry tag.
- **S051** Bespoke audit builder ingests a client brief, creates a new `audit_version`, generates unique URL slug.
- **S052** Industry-specific framing flows into the report narrative.

### Epic G — Squarespace export
- **S060** Squarespace exporter agent generates the full bundle (pages, seo, design, audit_app, pdf_report, voice, README).
- **S061** Preview tree in dashboard with modal previews per file.
- **S062** **Download Bundle (.zip) button** wired to `GET /api/squarespace/exports/{id}/download`.
- **S063** Re-runs stay on-brand by pulling live brand voice from DB.
- **S064** Export history sidebar (default last 10 retained).

### Epic H — Payments + access
- **S070** Stripe checkout session for single audit.
- **S071** Stripe webhook handler creates respondent record + audit on payment success.
- **S072** Promo code generation in operator dashboard.
- **S073** Promo code redemption at audit start (validates, decrements uses).
- **S074** 100% discount code grants free access end-to-end.

### Epic I — Cohort intelligence
- **S080** Cohort analyser nightly job: aggregate stats, pattern detection across cohort.
- **S081** Pattern hunter weekly job: 3-body grid search with DOUBT gate (BH-FDR p<0.01, hit≥60%, OOS≥50%, robust ±10%).
- **S082** Cohort Insights page surfaces validated patterns.

### Epic J — Compliance + ops
- **S090** Playwright HIG audit script + report to `compliance/hig_audit_<date>.md`.
- **S091** Quinn's vision-model UAT pass across all 3 dashboards + Squarespace preview.
- **S092** Nightly Postgres dump, retained 14 days locally.
- **S093** Runbook in `docs/runbook.md` covering: cold start, port re-discovery after reboot, restoring from backup, manual report regeneration, Squarespace bundle rebuild, Stripe key rotation.

## 5. Build order (milestones, mirrors spec §12)

M0 BMAD install + Analysis + Planning · M1 Architecture + UX · M2 Scaffolding · M3 Audit ingestion · M4 Report generation · M5 Operator dashboard · M6 Executive dashboard · M7 Industries + bespoke · M8 Stripe + promo · M9 Cohort + pattern hunting · M10 Squarespace export with Download button · M11 HIG compliance pass · M12 Production hardening.

## 6. Out-of-scope decisions queued

- Production email provider (M4 closeout).
- Final pricing (M8 start).
- Audit lives on platform vs embeds on Squarespace (M10 start; default platform-only per spec).
- Tax inclusivity for AUD pricing on Squarespace (M8 + Squarespace export coordination).

## 7. Acceptance for PRD itself

PRD is signed off when:
- Steve has read this file.
- All BLOCKING questions in spec §15 are either answered or have a placeholder + Party Mode session scheduled.
- Bob has sliced the above epics into individual story files under `docs/stories/`.
- Winston can begin architecture (M1).

---

*End of PRD. Hand to Bob for story slicing, then Winston for architecture.*
