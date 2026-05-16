# Decipher — Project rules (spec §10) + role taxonomy

## Rules (non-negotiable)

1. No lying.
2. No assumptions. Never fabricate data.
3. Nothing fails silently. Log + surface.
4. No stale numbers in UI. DB-driven, live.
5. No physical browser. Headless Playwright only.
6. All UI data DB-driven. No hardcoded values.
7. Australian English everywhere (organisation, behaviour, recognise, colour, programme = course, program = software).
8. No em dashes anywhere.
9. Always check links before referencing.
10. No double negatives.
11. No bro-sales clichés (close, crush, killer).
12. No generic AI filler (unlock, elevate, seamless, delve, tapestry, leverage, empower, in today's fast-paced world, game-changer).
13. Diagnose before prescribe.
14. DNA Audit = Trojan horse. Clean breadcrumb to consulting/training, never hard-sold.
15. Steve is sole operator.
16. Apple HIG non-negotiable (spec §9).
17. Never send anything from operator email accounts (drafts only, operator sends).
18. **All laundry-list table headings are clickable and sort the column.** Non-negotiable. Every column header is a button with a sort-state indicator (▲ asc / ▼ desc / · unsorted). Use the `SortableTable` component; do not roll your own `<thead>`. Applies to Audits, Industries, Promo Codes, Events Log, Team Audits, Bespoke, and every future table.

## Role taxonomy (added 2026-05-16)

Six roles. Each gets a route-guarded view of the dashboard.

| Role | Sees | Notes |
|---|---|---|
| **Admin** | Everything across all clients, cohorts, audits, exports | Steve. Sole operator. |
| **CEO** | Org-level summary across teams; pipeline value; cohort lift | Outcome owner, board-facing view. |
| **Sales Director** | Their sales team(s) only; mirrors the executive mockup slide | Team aggregate. Individual report only with consent. |
| **HR** | Org-level talent + retention signals; cross-team risk | Aggregate only. Individual reports gated by consent. |
| **Learning & Development** | All teams in their org; intervention queue; training cohorts | Coaching surface. Drives consulting + training prescription. |
| **Sales Person** | Self only: own audit + own report | Respondent view. Re-audit reminder at 90 days. |

- Schema `respondents.role` CHECK list updated to: `admin | ceo | sales_director | hr | learning_development | sales_person`.
- Toolbar shows "Logged in as ${name} (${role})". M5 magic-link auth flips it from the seeded admin to the actual logged user.
- Consent flag `respondents.consent_share_individual` gates individual-report visibility for Sales Director / HR / L&D.
- Steve is seeded as `role='admin'`.
