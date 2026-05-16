# Decipher — UX Design (BMAD Phase 3, Sally)

**Date:** 2026-05-16. **Anchor:** Apple HIG. Mirror Steve's exec mockup slide 1:1.

---

## 1. Design tokens (single source of truth)

Lives at `dashboard/src/styles/tokens.css` and is mirrored into `design/tokens.json` in the Squarespace export. One token map, two consumers.

### Colour (light)
| Token | Value | Use |
|---|---|---|
| `--colour-bg-base` | `#ffffff` | Page background |
| `--colour-bg-elevated` | `#f7f7f8` | Cards |
| `--colour-text-primary` | `#0a0a0a` | Body |
| `--colour-text-secondary` | `#5b5b5d` | Sub-labels |
| `--colour-text-tertiary` | `#8e8e93` | Captions |
| `--colour-fill-primary` | `#0a0a0a` | Filled buttons |
| `--colour-fill-secondary` | `#eeeeef` | Tinted buttons |
| `--colour-accent` | `#1f8a4f` | Decipher green (used sparingly) |
| `--colour-border-subtle` | `#e6e6e8` | Card edges |
| `--colour-band-elite` | `#1f8a4f` | Elite |
| `--colour-band-performing` | `#3a82e8` | Performing |
| `--colour-band-practising` | `#e3a13a` | Practising |
| `--colour-band-developing` | `#c63d3d` | Developing |

### Colour (dark via `prefers-color-scheme`)
Same tokens, recomputed: `--colour-bg-base #0a0a0a`, `--colour-bg-elevated #161618`, `--colour-text-primary #f5f5f7`, etc. Accent + band colours hold (slightly desaturated).

### Typography (Apple Dynamic Type → web via `clamp()`)
| Token | clamp() | Weight | Use |
|---|---|---|---|
| `--type-large-title` | `clamp(32px, 4vw, 44px)` | 700 | Hero numerals (KPI cards) |
| `--type-title-1` | `clamp(24px, 2.6vw, 30px)` | 600 | Page title |
| `--type-title-2` | `clamp(20px, 2.1vw, 24px)` | 600 | Section header |
| `--type-title-3` | `clamp(17px, 1.6vw, 19px)` | 600 | Card title |
| `--type-headline` | `15px` | 600 | Strong inline |
| `--type-body` | `15px` | 400 | Body |
| `--type-callout` | `14px` | 400 | Secondary body |
| `--type-subhead` | `13px` | 600 (caps) | Section eyebrow |
| `--type-footnote` | `12px` | 400 | Footnote |
| `--type-caption` | `11px` | 400 | Chip text |

Font stack: `'SF Pro Text', 'SF Pro Display', 'Inter', system-ui, -apple-system, sans-serif`.

### Spacing (8pt grid, 4pt sub)
`--space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-5: 24px; --space-6: 32px; --space-7: 48px; --space-8: 64px;`

### Radii + shadows
`--radius-sm: 6px; --radius-md: 10px; --radius-lg: 16px; --shadow-1: 0 1px 2px rgba(0,0,0,.04); --shadow-2: 0 4px 12px rgba(0,0,0,.06);`

### Motion
`--duration-fast: 0.2s; --duration-base: 0.3s; --duration-slow: 0.4s; --easing: cubic-bezier(0.4, 0, 0.2, 1);`

## 2. Component primitives

`Button` (variants: filled, tinted, plain; size: sm/md/lg; min 44pt tap), `Card`, `Stat` (KPI card), `BandPill`, `BandBar` (stacked horizontal), `Sheet`, `Modal`, `Toast`, `EmptyState`, `Skeleton`, `Tabs` (max 5), `Disclosure`. Buttons confirm within 100ms; long ops show progress, not a bare spinner.

## 3. Operator wireframes (10 pages, low-fi)

```
+-----------------------------------------------------------+
| Decipher · Mission Control                          [⚙]   |
| audits today 7 · this month 142 · μ-scores 0.67 / 0.71 / |
| 0.64 / 0.59 · pipeline AUD $58k · ports DB 55432 API 58080|
+-----------------------------------------------------------+
| [Latest patterns]   [Today's activity]   [Alerts]         |
| pattern_library     audits + reports     events_log       |
|                                                           |
+-----------------------------------------------------------+
| Nav: Mission · Audits · Cohort · Teams · Industries ·     |
|      Bespoke · Promo · Squarespace · Events · Settings    |
+-----------------------------------------------------------+
```

Per-page sketches mirror spec §7A. `Squarespace Export` page wireframe at §5.

## 4. Executive dashboard wireframe (mirror Steve's slide 1:1)

```
+----------------------------------------------------------------+
| NSW Sales Team · Decipher DNA Audit                            |
| Head of Sales Dashboard, 100 Respondents · April 2026          |
+----------------------------------------------------------------+
| [TEAM AVG SCORE] [ELITE PERFORMERS] [AT-RISK REPS] [BIGGEST    |
|       67         |       12          |     24        | GAP    |
|  /100            |  85+ across       | Developing    | TRAIT  |
|  across all 4    |  all 4 traits     | in 2+ traits  | Pressure
|  traits          |                   |               | Composure
|                  |                   |               | 58 /100|
|                  |                   |               | Practising
+----------------------------------------------------------------+
| SCORE DISTRIBUTION BY BAND                          100 reps   |
| Each bar shows how the 100 reps are distributed                |
| across the 4 performance bands per trait                       |
|                                                                |
| Cognitive Empathy  [█Elite 18██Performing 41██Practising 28██D 13]
| EQ                 [█Elite 14██Performing 39██Practising 30██D 17]
| Pressure Composure [█Elite  9██Performing 28██Practising 39██D 24]
| Storytelling       [█Elite 11██Performing 33██Practising 35██D 21]
+----------------------------------------------------------------+
| Team Trait Averages                                            |
| [Cognitive Empathy 67.1 Performing] [EQ 64.8 Performing]       |
| [Pressure Composure 58.4 Practising] [Storytelling 62.1 Practising]
+----------------------------------------------------------------+
| ARCHETYPE BREAKDOWN                                            |
| Regulator     ████████████████████  34                         |
| Edge-Builder  ████████████████  27                             |
| Observer      ███████████  22                                  |
| Labeler       ████████  17                                     |
+----------------------------------------------------------------+
| PRIORITY COACHING INTERVENTIONS                                |
| [Card 1: 24 reps, Pressure Composure (Developing) — pattern/  |
|  cause/intervention paragraph]                                 |
| [Card 2: 21 reps, Storytelling (Developing) — ...]            |
| [Card 3: 17 reps, EQ (Developing) — ...]                       |
| [Card 4: Leverage your top 12 Elite performers — ...]          |
+----------------------------------------------------------------+
| [Download Executive Summary (PDF) →]                           |
| Footer: decipher.com.au · Confidential, For Head of Sales      |
|         Use Only · April 2026                                  |
+----------------------------------------------------------------+
```

Spec §7B is the source of truth for copy. This wireframe is the layout.

## 5. Squarespace Export page wireframe

```
+----------------------------------------------------------------+
| Squarespace Export                                             |
+----------------------------------------------------------------+
|                                                                |
|   [Generate New Export →]   (filled-primary, large)            |
|                                                                |
|   Last export: 2026-05-14 14:22 · 47 files · v3                |
+----------------------------------------------------------------+
| Preview tree                          | History                |
| ├ pages/                              | 2026-05-14 14:22 v3 [↓]|
| │  ├ home.md            [preview]     | 2026-05-12 09:11 v2 [↓]|
| │  ├ dna_audit.md       [preview]     | 2026-05-10 16:48 v1 [↓]|
| │  ├ training.md        [preview]     |                        |
| │  └ ...                              |                        |
| ├ seo/meta.json         [preview]     |                        |
| ├ design/tokens.json    [swatch]      |                        |
| └ voice/brand_voice.md  [preview]     |                        |
+----------------------------------------------------------------+
|                                  [Download Bundle (.zip) ↓]    |
+----------------------------------------------------------------+
```

The Download Bundle button is large, filled-primary, bottom-right, single most important UI element on this page.

## 6. Respondent view wireframe (intentionally minimal)

```
+--------------------------------------------+
| Hi, Lina.                                  |
|                                            |
| Your most recent audit completed 14 Apr.   |
| Your report:  [Download PDF ↓]             |
|                                            |
| Re-take in 14 days to measure your lift.   |
|                                            |
| Learn more about consulting + training →   |
+--------------------------------------------+
```

## 7. Microcopy register

- Concise. Active voice. Australian English (organisation, behaviour, recognise, colour). Programme = the training course. Program = software.
- No bro-sales: no "close", "crush", "killer".
- No AI filler: no "unlock", "elevate", "seamless", "delve", "tapestry", "leverage", "empower", "in today's fast-paced world", "game-changer".
- No em dashes. Use commas, full stops, colons, or parentheses.
- Diagnose-then-prescribe in every page: name the gap, suggest the intervention.

## 8. HIG checklist (every page passes before milestone close)

- [ ] Type scale uses tokens, not hardcoded px
- [ ] Spacing on 8pt grid
- [ ] Min contrast 4.5:1 body / 3:1 large
- [ ] All interactive 44pt tap, keyboard-reachable
- [ ] Images have descriptive alt text
- [ ] No colour-only meaning (bands carry text labels)
- [ ] `prefers-reduced-motion` respected (animations short-circuit to fade)
- [ ] `prefers-color-scheme` dark/light both render
- [ ] Skeletons used for loading, not spinners
- [ ] Actions confirm within 100ms

---

*End of UX design. Hand to James for implementation, with the wireframes above as the brief.*
