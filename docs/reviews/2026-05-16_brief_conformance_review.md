# Decipher · Logic-flow vs brief conformance review

**Date:** 2026-05-16
**Scope:** does the implementation match the original Media-Sales-DNA brief? Scoring math, business rules, role workflow, Trojan-horse value loop, test patterns.
**Method:** independent agent reading `docs/super_prompt.md`, `docs/prd.md`, `reference_docs/media_sales_v1_*.json`, `CLAUDE.md`, against `app/`, `dashboard/src/pages/`, `schema.sql`.

## Conformance status summary

The Decipher prototype delivers a credible front-half of the brief: a 34-question native survey, a deterministic scoring engine, the 8-archetype assignment with all-high/all-low special cases, the executive KPI strip mirroring the slide, role taxonomy + capability matrix in DB, end-to-end Mailpit delivery of a 3-page ReportLab PDF, and the Owen-to-Grant drill-down. Where it diverges hard:

1. consent gating is implemented but not enforced from the only caller that matters (RespondentDetail);
2. two parallel band-threshold formulas (0.40/0.60/0.80 vs 40/65/85) coexist and contradict each other;
3. the original `seed_media_sales_dna_v1.py` writes the wrong trait-per-question table and a synthetic positional score map instead of the canonical per-option scores (a follow-up `fix_media_sales_v1_questions.py` patches this but is a manual second step);
4. Stripe / promo-redemption / re-audit cadence / Squarespace bundle generation are stubs;
5. no automated test pack exists.

## P0 (brief-breaking — implementation contradicts spec)

- **`app/api_server.py:1166-1170` vs brief §7B + §4.** `_band_for(v)` for the Exec Dashboard uses 0.40/0.60/0.80 — the spec §4 legacy 0-1 thresholds. The same file at `:337-343` and `dna_scoring.py:37` use 40/65/85. Direct contradiction with §7B legend "Performing 65-84". Pick one (§7B 65/85 wins per brief), delete the other.
- **`app/api_server.py:2037,2054` + `dashboard/src/pages/RespondentDetail.tsx:67` vs brief §3 + §7B.** `respondent_detail` defaults `viewer_role="admin"`. The frontend never sends a `viewer_role` query param. Any unauthenticated caller hitting `/api/respondents/{id}` sees full name, email, mobile, even when `consent_share_individual=false`. The §7B box "Individual reports only with consent (default off)" is broken at the API surface.
- **`scripts/seed_media_sales_dna_v1.py:22-55` + `:113` vs brief §3 (47-q seed).** First-pass seed scrambles the trait map (Q1 marked `eq` vs canonical `cognitive_empathy`; Q3 marked `pressure_composure` vs canonical `cognitive_empathy`; Q26 marked `pressure_composure` vs canonical `eq_bonus`/`eq`; Q31 marked `storytelling` vs canonical `eq_bonus`/`eq`) and overwrites canonical option scores with synthetic `[0.10, 0.30, 0.50, 0.70, 0.95]` positional scores that ignore the brief's calibrated per-option scores (Q9 option B = 4, option D = 2; Q11 option B = 4, option D = 4, option E = 5). It also names the 4th EQ identity "labeler" not the canonical "namer". Without running `fix_media_sales_v1_questions.py`, the platform scores wrong. This script must BE the seed, not an optional repair.
- **`reference_docs/media_sales_v1_full.json:1209,1262, etc.` + narrative pulls in `app/dna_report.py` vs rule 8 (no em dashes).** The canonical narratives ingested into `narrative_library` contain em-dashes verbatim. The report writes verbatim narrative_library content. Strip at ingest; replace with ". " or "; ". (Fixed during 2026-05-16 patching for 20 rows; ensure ingest pipeline scrubs going forward.)
- **`schema.sql` vs `app/api_server.py:79` + brief §3.** `narrative_library` is queried in code but has no `CREATE TABLE` in `schema.sql`. The table is created implicitly via `scripts/seed_archetype_descriptions_and_eq_identities.py`. A fresh `psql -f schema.sql && psql -f seed.sql` boot produces a server that crashes on `/api/health/scoring`.
- **`app/api_server.py:2001-2033` + `:2893-2922` vs brief §6 + §8.** `/api/squarespace/generate` writes a row with fixed `file_count=47, size_bytes=1_250_000` and a path to a file it never creates. `/api/squarespace/exports/{id}/download` then builds an in-memory zip containing the literal string "DUMMY placeholder for …". §7D calls the Download button "the single most important UI element on this page." Today it ships a fake bundle.

## P1 (brief-shortfall — present but incomplete)

- **`app/api_server.py:2783-2800` vs brief §4 quality gate.** Completeness gate present. Other four checks missing: response time 2s-5min per question, variance > 0.05 (straight-liner detection), paired-question consistency, archetype confidence > 0.5. None block report generation. `archetype_assignments.confidence` is computed (`dna_scoring.py:122`) but never gated.
- **`app/dna_scoring.py:166-188` vs brief §4 EQ identity.** Plurality vote works. Tie-break is only "max by count" (Python's stable max returns first-by-insertion). Brief required "deterministic alphabetical fallback, logged". Today a 1-1-1 vote silently picks `regulator` because of insertion order. No `tiebreak_applied` for EQ identity (only trait pair).
- **`app/api_server.py:2698-2751` vs brief §6.** `/api/audit/start` does not require payment or promo redemption. Anyone with the URL can take the audit unpaid. Stripe webhook not implemented; `payment_ref` never written.
- **vs brief §7C.** "Re-take in 90 days reminder if last audit > 75d" not implemented. `audit_jobs` schema supports `reaudit_reminder` but no scheduler dispatches them, no email template ships, no respondent-view page exists at all (no `/me` route).
- **`app/api_server.py:108-251` vs brief §7A.** Bootstrap exposes counts but **not** "mean dimension scores trailing 30d" as required header metric. Pipeline exposed; trailing-30d trait means missing.
- **vs brief §5 agent list.** Spec names 10 stateless Python agents. Today: scoring + report run inline inside `/api/audit/{id}/complete`. No `audit-scorer / report-generator / cohort-analyser / pattern-hunter / email-dispatcher` daemons. `audit_jobs` queue exists but is unread.
- **`app/dna_scoring.py:107-124`.** Tie-break for trait-pair ranking only fires when `abs(top2 - third) < 1e-6` — sound. But `ARCHETYPE_BY_PAIR.get(...) or ELITE_OPERATOR` fallback (line 120) silently mislabels any unrecognised pair as Elite Operator. Should raise.
- **`dashboard/src/pages/AuditTake.tsx:72` vs brief rule 6.** Submits `value: optionIndex`. If `fix_media_sales_v1_questions.py` is run with `options` reordered, the index breaks scoring. Submit the option letter or `question_option_id`, not the position.
- **`app/api_server.py:479-530` vs brief §11 4D.** `/api/ai/ask` is a hand-coded keyword router, not Claude. Cost/token logging to `events_log` (brief §14) never occurs.

## P2 (brief-implicit — needed for credibility)

- **`app/api_server.py:1592-1606` + `:1647-1668` vs rule 17.** Invite email + report email pass-able but both hardcode `noreply@decipher.com.au` with no DKIM/SPF readiness, no Steve-verified send domain, no language about consent or unsubscribe. Brand voice is Mailpit-ready only.
- **`app/api_server.py:1604` vs rule 8.** Invite uses "7-10 minutes" hyphen-minus, fine. But report subject uses `"·"` separators and body has no breadcrumb to consulting/training pages (rule 14 "Trojan horse, clean breadcrumb"). No CTA back to platform.
- **`/api/teams/{id}/export.pdf`** route present, content not audited here.
- **`schema.sql:178-185` `audit_score_vectors`** has only 1 of the 4 derived dimensions plumbed (no `consistency`, `response_time_variance`, `extremity`, `sentiment` writers exist).

## End-to-end happy-path walkthrough

1. Operator hits Funnel, sends invite. ✅ `app/api_server.py:1689` `audit_invite()` upserts respondent + row in `audit_invites` + Mailpit email.
2. Respondent receives email. ✅ HTML lands in Mailpit on `DECIPHER_MAIL_PORT`.
3. Respondent clicks `?invite=<token>`. ⚠ Link → `/audit/start?invite=<token>`, but `audit_start` does not validate or consume the token. Anyone can take an audit by typing the URL.
4. Respondent fills name/email/job title, clicks Begin. ✅ `AuditTake.tsx:78` → `/api/audit/start`.
5. 34 questions rendered. ✅ From `/api/audit/versions/media_sales_v1/questions`.
6. Each answer POSTed as positional index. ⚠ Brittle to option reorder.
7. `POST /api/audit/{id}/complete`. ✅ Completeness gate fires. ❌ Other quality gates absent.
8. Inline `score_audit` then `generate_report`. ✅ Works for `audit_version_id == 2` only; any other version silently skips scoring.
9. PDF emailed via Mailpit. ✅ `_send_report_email` attaches PDF, logs `delivered_at`.
10. Done card shows scores, archetype, EQ identity. ✅ Confidence pill + trait grid render.
11. Admin opens Audits → RespondentDetail. ❌ `viewer_role` defaults admin server-side, identity leaks regardless of consent.
12. Admin opens TeamExecutive. ✅ KPIs + distribution + interventions render, but biggest-gap labels via wrong band table.
13. Admin downloads Squarespace bundle. ❌ Returns dummy zip.
14. 90-day re-audit reminder. ❌ Not scheduled.

## Test pattern map

No `tests/` directory exists. Priority pack to land under `tests/`:

| Priority | Test | Location | Rule |
|---|---|---|---|
| P0 | `test_scoring_normalisation` — `_normalise([1]*6)==0.0`, `[5]*6==100.0`, mixed cases match canonical | `tests/test_dna_scoring.py` | brief §4 (raw-6)/24*100 |
| P0 | `test_band_boundaries` — 39.999→developing, 40→practising, 64.999→practising, 65→performing, 84.999→performing, 85→elite | `tests/test_dna_scoring.py` | brief §7B |
| P0 | `test_band_consistency_across_codebase` — `_band_for` in api_server matches `dna_scoring._band_for` for 0-100 range | `tests/test_band_consistency.py` | Catches current contradiction |
| P0 | `test_archetype_pair_table` — all 6 pair combinations resolve to correct archetype | `tests/test_dna_scoring.py` | brief §4 |
| P0 | `test_archetype_all_high_low` — `[86]*4 → Elite Operator`, `[39]*4 → Raw Material`, `[85,84,84,84] → pair` | `tests/test_dna_scoring.py` | brief §4 |
| P0 | `test_consent_gates_identity_in_respondent_detail` | `tests/test_consent_gating.py` | brief §7B |
| P0 | `test_seed_matches_canonical` — every question in DB has trait + per-option scores matching canonical | `tests/test_audit_instrument.py` | brief §1 |
| P1 | `test_eq_identity_winner` — 2-1 wins, 3-0 wins, 1-1-1 falls back alphabetical + flags tiebreak | `tests/test_eq_identity.py` | brief §4 |
| P1 | `test_completeness_gate_blocks_complete` — answer 33 of 34 → 400 incomplete_audit | `tests/test_audit_lifecycle.py` | brief §4 |
| P1 | `test_quality_gates` — straight-liner, out-of-range response_ms, inconsistent paired → status `failed_quality_gate` | `tests/test_quality_gates.py` | brief §4 |
| P1 | `test_team_strict_scoping` — Team A audits not visible in `/api/teams/{B}/...` payloads | `tests/test_rbac.py` | brief §7B |
| P1 | `test_role_capability_matrix` — sales_person POST /api/audit/invite → 403; SD from team A inviting team B → 403 | `tests/test_rbac.py` | role taxonomy |
| P1 | `test_no_em_dash_in_artefacts` — scan reports + emails + narrative_library → 0 | `tests/test_brand_rules.py` | rule 8 |
| P1 | `test_no_filler_words` — scan narrative_library + brand_voice + Squarespace strings for banned list | `tests/test_brand_rules.py` | rule 12 |
| P2 | `test_reaudit_reminder_enqueued_at_75d` | `tests/test_reaudit_cadence.py` | brief §7C |
| P2 | `test_squarespace_bundle_round_trip` | `tests/test_squarespace_export.py` | brief §8 + §16 DoD #6 |
| P2 | `test_promo_free_grants_audit_without_stripe` | `tests/test_payments.py` | brief §16 DoD #8 |
