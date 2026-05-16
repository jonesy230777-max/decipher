# Decipher · Apple HIG / UI-UX 2026 May review

**Date:** 2026-05-16
**Scope:** design system, typography, colour, spacing, motion, accessibility, density, information hierarchy, interaction patterns.
**Method:** independent agent reading `dashboard/src/**`, `tokens.css`, `index.css`, against May-2026 HIG (post-Liquid Glass / post-iOS 18 refresh).

## P0 (ship-blocking for HIG compliance)

- **Recharts tooltips use library defaults across every chart** (`MissionControl.tsx:98,116,130,147,160`; `CohortInsights.tsx:176`). Default white card, default Arial-ish font, no tabular nums, no token colours. Breaks dark mode (white tooltip on near-black page). Build one `<ChartTooltip>` wrapper with `contentStyle={{ background: 'var(--colour-bg-system-secondary)', border: '1px solid var(--colour-separator-opaque)', borderRadius: 'var(--radius-md)', fontVariantNumeric: 'tabular-nums', fontSize: 12 }}` and pass to every Recharts `<Tooltip>`.
- **Hex literals leak into chart fills and gradients** (`MissionControl.tsx:87,88,91,92,100,101,117,131,148,161`: `#1B8A4F`, `#3B82F6`). Spec §1 says one token map. These do not invert in dark; dark-mode accent is `#30D158`. Resolve via `getComputedStyle(document.documentElement).getPropertyValue('--colour-accent')` once at mount.
- **Decorative em dashes in source files violate project rule 8** (`App.tsx:231`, `Card.tsx:42,59`, `TeamExecutive.tsx:2,103`).
- **`Card.tsx:91` button transition omits `transform`**; Button has no `:hover` / `:active` / `:focus-visible` styles. HIG (Buttons, 2024 refresh) requires visible press feedback within 100ms. Add `:hover { filter: brightness(1.05) }` and `:active { transform: scale(0.98) }` via a CSS class instead of inline style.
- **Default-size Button is 36px tall** (`Card.tsx:73` `heights = { sm: 28, md: 36, lg: 44 }`). Every secondary action fails the 44pt touch target. Either raise `md` to 44 or audit and force `lg` for every page-level action.
- **AuditTake answer buttons rely on JS `onMouseEnter`/`onMouseLeave` for hover** (`AuditTake.tsx:220-221`). No `:focus-visible` ring. No keyboard A-D shortcuts despite labels "A. / B. / C. / D." (`AuditTake.tsx:224`).
- **AuditTake input height 40px** (`:364`), **Login input height 40px** (`Login.tsx:124`), **Industries inline form input 36px** (`Industries.tsx:98`). All below 44px. AuditTake is the customer-facing flow and worst offender.
- **Sidebar active state uses raw `#FFFFFF` on `--colour-accent`** (`App.tsx:217-218`). Dark accent is `#30D158`; white on lime = 2.4:1 contrast, fails WCAG AA. Use `--colour-fill-tertiary` background + `--colour-accent` label, or darken accent for selected states.
- **Hardcoded white on accent recurs in 15+ places** (`BandBar.tsx:65`, `AuditTake.tsx:284,324`, `GapAnalysis.tsx:96`, `TeamExecutive.tsx:400`, `Companies.tsx:131`, `Teams.tsx:132`, `RespondentDetail.tsx:108,343`, `Funnel.tsx:300`, `Landing.tsx:33,70`, `CompanyDetail.tsx:108`, `Settings.tsx:44-46`). Define `--colour-label-on-accent` token for both themes (dark = `#0a0a0a`).
- **Sortable table indicator uses ASCII `▲ ▼ ·`** (`SortableTable.tsx:79-80`). Font fallback often = Times. Replace with SF Symbols inline SVG (`chevron.up`, `chevron.up.chevron.down` for unsorted); at minimum wrap in `font-family: -apple-system`.

## P1 (next-sprint design polish)

- **Toolbar metric chips 10px/13px** (`App.tsx:88,98`) below HIG caption-2 (11px). Promote to `var(--type-caption-2)` + `var(--type-footnote)`.
- **MissionControl KPI strip 8 columns equal width** (`MissionControl.tsx:65-78`). On 13" MacBook each Stat ~150px and value clips into hint. HIG pattern is 4-up above the fold. Drop to 4 KPIs or 4×2.
- **Stat tile padding `var(--space-3) var(--space-4)`** (`Stat.tsx:17`) = 12/16, while `Card` uses 24 (`Card.tsx:19`). Rhythm breaks where Stats sit beside Cards. Standardise on 16/20 compact or 24 spacious.
- **`hig-title-3` (20px) used as card title AND as kpi value suffix "/100"** (`TeamExecutive.tsx:287`). Suffix dwarfs the 16px hint. Use `hig-callout` for the suffix.
- **Logo `<img src>` switches on theme** (`Logo.tsx:33`) with no preload — 100-300ms blank on first dark toggle. Preload both in `index.html`.
- **Eight top-level metric chips with sparklines** (`App.tsx:141-157`) at 40×12px carry no readable signal. Drop to four headline metrics or unify into a single Apple-Numbers-style sparkline strip.
- **`SectionEyebrow` (`Card.tsx:46`) uses `hig-footnote`** whereas elsewhere eyebrows use `hig-caption-1` uppercase + letter-spacing. Pick one. 2024 HIG pattern is Footnote, sentence case, secondaryLabel, no caps.
- **TeamExecutive roster is a CSS grid, not a `SortableTable`** (`TeamExecutive.tsx:226-241`). Violates project rule 18 (every laundry-list table sortable) + impossible to keyboard-navigate (`<div>`s not `<tr>`s).
- **`TeamExecutive.tsx:329-337` toast** fixed-positioned, no exit animation. Add fade-out `var(--duration-base) var(--easing)`.
- **`window.prompt()` used for invite UX** (`TeamExecutive.tsx:303-307`). Three sequential prompts is jarring, not stylable, not HIG. Use a Sheet/Modal.

## P2 (modernisation toward May-2026 HIG)

- **Liquid Glass surfaces only on toolbar** (`App.tsx:117-119`, `Landing.tsx:23-24`). Sidebar uses solid `--colour-bg-system-secondary`. 2026 HIG says secondary nav adopts `.regularMaterial`. Apply `backdrop-filter: blur(40px) saturate(180%)` with semi-transparent background token.
- **No materials tokens** in `tokens.css`. Add `--material-thin`, `--material-regular`, `--material-thick`, `--material-chrome`.
- **No SF Symbols anywhere.** ASCII glyphs `›`, `↓`, `↻`, `✉`, `+`, `→` substitute. Add inline SVG equivalents or `font-family: 'SF Pro Display'` so codepoint resolves to SF on Apple devices.
- **Dark-mode accent jumps from `#1B8A4F` (forest) to `#30D158` (lime).** Different brands. Pick one Decipher green; tune lightness per scheme.
- **`--colour-separator` light `rgba(60,60,67,0.36)`** renders as ~#9B9B9F at 1px. Apple 2024 separators use 0.18 hairline. Drop to 0.18; reserve 0.36 for `separator-opaque`.
- **No `letter-spacing` on body / callout / footnote**. HIG 2024 type table specifies `-0.078em` at large title scaling to `+0.066em` at caption. Only `.hig-title-*` have tracking (`index.css:36-39`). Add tracking tokens.
- **No skeleton states.** Multiple pages render `Loading...` text. `ux_design.md` §2 calls for a `Skeleton` primitive — doesn't exist in `/components`.
- **No focus-trap on GlobalSearch dropdown** (`GlobalSearch.tsx:121-191`). Tab leaves listbox; no `aria-activedescendant`; Enter does not select highlighted hit; no `aria-expanded`.
- **AuditTake done-state functional but flat** (`AuditTake.tsx:261-344`). Deserves a 2026 reveal: spring-eased archetype card scale-in, subtle gradient sweep behind archetype name, haptic-feedback hint "Saved to your inbox".

## P3 (delight / advanced)

- **Mobile: zero `@media` rules anywhere** (`grep` confirms 0). AuditTake must be mobile-first as the public flow. Add breakpoints 480/768/1024 and stack the question/answer card edge-to-edge under 480px.
- Add a `prefers-contrast: more` block. Switches separators to opaque, raises secondary labels to 0.75, removes glass blur.
- Add `view-transition-name` to page roots so route changes animate the 2026 way (cross-fade by default, slide for drill-downs).
- AuditTake keyboard A-D shortcut + Enter-to-advance with spring micro-bounce on selected option.
- Sparkline is monochrome; add direction colour rule (green up / red down) per Apple Stocks 2026.

## Design-system recommendations

1. **Promote inline styles to CSS modules per primitive.** ~70% of components carry inline `style={{...}}` literals. Inline styles cannot use pseudo-selectors — this is why every button is dead on press. Migrate `Card`, `Button`, `Stat`, `BandBar`, `SortableTable`.
2. **Add `--colour-on-accent` token pair** (light `#FFFFFF`, dark `#0a0a0a`) to kill the 15+ hardcoded `color: "#FFFFFF"` violations.
3. **Build a `ChartTheme` provider for Recharts** that injects axis/grid/tooltip styles + series palette from CSS variables.
4. **Introduce a `Material` component** wrapping `backdrop-filter` + the four 2026 glass tokens. Toolbar + Sidebar consume; Sheets and Popovers reuse later.
5. **Codify a 44-default Button.** Rename: `md=44` (default touch), `compact=36` (desktop dense tables only with keyboard parity), `lg=52` (hero). Remove the 28px `sm` — uninteractable on mobile.
