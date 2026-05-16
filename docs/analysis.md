# Decipher — Analysis (BMAD Phase 1, Mary)

**Input of record:** `docs/super_prompt.md` (verbatim Decipher_ClaudeCode_SuperPrompt).
**Date:** 2026-05-16.
**Author:** Mary (Analyst).
**Scale:** small-to-medium prototype, one-operator (per BMAD v6 scale-adaptive guidance, spec §0).

---

## 1. Problem

Sales directors can see when a rep is underperforming but cannot diagnose what is broken. Reps know they are struggling. Nobody can name the cause. The result is generic training, drifting numbers, and lost deals. Decipher exists to codify what actually happens in a sales conversation across four measurable dimensions so improvement is repeatable.

## 2. Outcome Decipher delivers

Higher conversion rate, better relationships, longer client retention. Reachable via three steps: diagnose (47-question DNA Audit + PDF report), prescribe (bespoke training mapped to weaknesses), validate (re-audit at 3 months).

## 3. Personas (three audiences)

| Persona | Goal | Permission scope |
|---|---|---|
| Steve (Operator) | Run everything. See all clients, all cohorts, all individual reports. Generate Squarespace assets. | Full |
| Sales Director / L&D Buyer (Executive) | Diagnose their team's weaknesses, prioritise coaching investment, demonstrate ROI. | Team aggregate only. Individual reports only with consent. |
| Salesperson (Respondent) | Take the audit, receive a report, improve. Re-audit at 3 months. | Self only |

## 4. Existing context

- Steve has a 47-question audit, currently in Google Apps Script (to be ported via `docs/master_questions.csv`).
- Steve has mocked an executive dashboard slide ("NSW Sales Team · Decipher DNA Audit / Head of Sales Dashboard, 100 Respondents · April 2026"). The exec dashboard must mirror this exactly.
- Two archetype taxonomies exist in the source (4 vs 8). Reconciliation is BLOCKING M3 (see Decision D-006 for the placeholder).
- Squarespace hosts the marketing site. The platform generates the asset bundle Steve uploads by hand.

## 5. Constraints

- **Local-first** Docker stack on Steve's Mac (Apple Silicon). No cloud beyond Claude API + email sandbox in dev.
- **One human operator.** No team, no partners. Resilience comes from automation + a clean runbook, not headcount.
- **Apple HIG conformance non-negotiable** across dashboards and Squarespace. Verified via Playwright + vision-model UAT.
- **Trojan-horse commercial model.** Public site sells only the audit. Consulting/training are enquiries. No tiered packages.
- **Australian English everywhere.** No em dashes. No bro-sales clichés. No generic AI filler.

## 6. Risks + open questions

| # | Risk / Question | Impact | Owner | Mitigation |
|---|---|---|---|---|
| R1 | Archetype taxonomy ambiguity | Blocks classifier in M3 | Steve | Schema agnostic now (D-006); Party Mode session before M3 closes |
| R2 | Master questions CSV not yet provided | Blocks audit seed in M3 | Steve | Use 47 placeholder questions tagged by dimension for scaffolding; swap when CSV lands |
| R3 | Production email provider undecided | Blocks M4 production cutover (Mailpit covers dev) | Steve | Mailpit in dev. Production decision deferred to M4 closeout. |
| R4 | Stripe credentials + product setup | Blocks M8 | Steve | Webhook + checkout structure built against test keys; flip at M8 |
| R5 | Founder bio for About page | Blocks M10 Squarespace export | Steve | Other 9 pages can ship without; About blocked at the end |
| R6 | Audit flow: platform-only vs Squarespace-embedded | Affects M10 + handoff UX | Steve | Spec lean: platform-only. Default to that; re-confirm at M10. |

## 7. Out of scope (explicitly)

- Tiered packages (bronze / silver / gold) on the website.
- Hard-selling consulting or training on the audit page.
- Mobile app.
- Multi-tenant SaaS architecture (this is local-first single-operator).
- Replacement for Squarespace (Decipher generates an asset bundle; Squarespace remains the public site).

## 8. Success indicators (mapped to spec §16 Definition of Done)

- Audit → PDF in ≤ 90 seconds end-to-end.
- Exec dashboard matches Steve's mockup slide 1:1.
- Download Bundle button delivers a complete Squarespace zip.
- Zero HIG violations on Playwright + vision-model UAT across all three dashboards.
- All BMAD artefacts (analysis, PRD, architecture, UX, stories) traceable to running code.

## 9. Next phase (PRD)

Hand to John. PRD will translate this into user stories under `docs/stories/`, sliced 1–3 days each per BMAD scale guidance. PRD must cover all three personas.
