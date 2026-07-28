"""Decipher DNA Audit report generator -- v2, redesigned to match Steve's
target sample report (DNA-Audit-Sample-Report.pdf) section for section.

Routed to behind a flag: app/dna_report.py's generate_report() delegates
here only for audit_ids listed in DECIPHER_REPORT_V2_AUDIT_IDS. Mirrors the
real app/dna_report.py function names and _load_context() shape. The only
genuinely new runtime dependency is app.trait_content.

Structure (matches sample):
  Page 1  Cover / summary: archetype, EQ identity, score circle, trait bars,
          top strength / growth area, band legend, "this report contains"
  Page 2-5  One deep-dive per trait: synthesis, performance ladder,
          strength/gap, what-the-band-above-does, where-you-sit,
          commercial cost, real conversation example, next action
  Page 6  30-Day Action Plan: four-week focus plan + 3 immediate actions
  Page 7  Glossary of terms (static, reference)

Content sourcing:
  - Per-trait/per-band sections: trait_content.py (static, hand-authored,
    length-matched per Steve's consistency instruction)
  - Archetype description: archetypes.description (existing DB field)
  - EQ identity description + chips: trait_content.EQ_IDENTITY_CONTENT
  - Opening synthesis paragraphs (page 1 profile + each trait page's lead
    paragraph): Claude-generated per audit, informed by the actual scores
    (this is the one place personalisation belongs -- see notes to Steve)

generate_report(audit_id) keeps the same signature and side effects as the
live app/dna_report.py: renders PDF, writes to REPORT_DIR, inserts into
`reports`, marks the audit 'reported', fires an event.
"""
from __future__ import annotations

import html as _html
import json
import os
from datetime import datetime
from pathlib import Path

from app.db import conn, rows, scalar, event
from app.trait_content import (
    DIM_LABEL, DIM_ORDER, BAND_LABEL, BAND_ORDER, BAND_RANGE_LABEL,
    LADDER, EQ_IDENTITY_LABEL, EQ_IDENTITY_CONTENT, ARCHETYPE_OBJECTIVE,
    REPORT_CONTAINS, band_for, get_trait_content,
)

REPORT_DIR = Path(os.getenv("DECIPHER_REPORT_DIR", "var/reports"))
REPORT_DIR.mkdir(parents=True, exist_ok=True)

_LOGO_DATA_URI = "data:image/png;base64,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"

BAND_HEX = {
    "elite": "#34C759",
    "performing": "#007AFF",
    "practising": "#FF9500",
    "developing": "#FF3B30",
}
TRAIT_HEX = {
    "cognitive_empathy": "#3762F0",
    "eq": "#2FA84F",
    "pressure_composure": "#F08A24",
    "storytelling": "#8B5CF6",
}

# ---------------------------------------------------------------------------
# Claude prompt: page-1 profile paragraph + one lead paragraph per trait
# page, all in a single structured call per report.
# ---------------------------------------------------------------------------
_SYNTHESIS_SYSTEM_PROMPT = """\
You are writing narrative sections of a DNA Audit report for a {industry} sales \
professional. The report is produced by Decipher, an Australian sales \
intelligence platform.

You will receive one respondent's four trait scores (0-100), their band per \
trait, their archetype and their EQ identity. Return ONLY a JSON object, no \
markdown, no commentary, with exactly these keys:

  "profile": 3-5 sentences for the report cover page. Synthesise the four \
  scores into one coherent read of how this person sells, the way a skilled \
  executive coach would describe what they observe. End with one sentence \
  naming the single highest-leverage development opportunity (or, if every \
  score is above 85, the contribution opportunity).

  "cognitive_empathy", "eq", "pressure_composure", "storytelling": \
  for each, write 3 short paragraphs (2-3 sentences each) that open that \
  trait's page, synthesising this person's specific score and band into a \
  natural read of their current standing. Reference the actual score number \
  naturally at least once across the three paragraphs. Do not repeat the \
  band label as a bare word (e.g. do not write "you are Practising"); \
  describe the behaviour instead. End the third paragraph by naming, in one \
  sentence, what separates their current band from the next one up (or, for \
  Elite, what the ceiling looks like now).

Writing rules for every field:
- Second person throughout ("You", "Your").
- Australian English: practise, behaviour, recognise, colour, organisation.
- No em dashes. Use a comma or a full stop instead.
- No generic filler: no "unlock", "elevate", "seamless", "leverage", \
"empower", "game-changer", "tapestry", "delve", "in today's fast-paced world".
- No bro-sales clichés: no "close", "crush it", "killer instinct".
- Plain text only inside each string. No markdown, no bullet points, no \
headings, no bold, no asterisks.
- Keep each trait's 3 paragraphs within a similar length to the others, \
this report holds section lengths consistent across every trait.

The four dimensions measured:
Cognitive Empathy: reading and naming what a buyer is feeling, holding \
silence, diagnosing the source of hesitation rather than only sensing it.
Emotional Intelligence: reading the emotional dynamics of a room and \
adapting to the individual buyer, understanding what they fear versus what \
they say.
Pressure Composure: staying diagnostically calm under objection, rate \
challenges and competitor comparisons, treating pressure as information \
rather than an attack.
Narrative Persuasion: structuring stories so the client is the hero, \
engineering the one line a buyer repeats afterwards rather than hoping it \
emerges naturally.

Band thresholds: Elite 85+, Performing 65-84, Practising 40-64, \
Developing under 40. Do not quote these numbers back in the output.
"""


def _synthesis_user_turn(ctx: dict) -> str:
    r = ctx["respondent"]
    name = r.get("name") or r.get("first_name") or "this respondent"
    scores = ctx["scores_100"]
    bands = ctx["bands"]
    lines = [
        f"Respondent: {name}",
        f"Industry: {ctx.get('industry_name') or 'Media'} sales",
        f"Role: {r.get('job_title') or 'sales professional'}",
        "",
        "Scores:",
    ]
    for dim in DIM_ORDER:
        lines.append(f"  {DIM_LABEL[dim]}: {scores[dim]:.1f}/100 ({BAND_LABEL[bands[dim]]})")
    lines += [
        "",
        f"Archetype: {ctx.get('archetype_name') or 'unknown'}",
        f"EQ identity: {EQ_IDENTITY_LABEL.get(ctx.get('eq_identity'), ctx.get('eq_identity') or 'unknown')}",
        "",
        "Return the JSON object described in the system prompt.",
    ]
    return "\n".join(lines)


def _get_synthesis(ctx: dict) -> dict:
    """Call Claude once for the profile paragraph + 4 trait lead paragraphs.
    Falls back to a plain, honest placeholder per field on failure so a
    report never blocks on the AI call, matching the live app's pattern of
    logging claude_api_call errors rather than failing generate_report.
    """
    from app.claude_client import complete_narrative, ClaudeCallError

    fallback = {
        "profile": (
            f"{ctx['respondent'].get('first_name') or 'This respondent'}'s results "
            "are summarised in the trait scores and archetype below."
        ),
        **{dim: "" for dim in DIM_ORDER},
    }
    try:
        raw = complete_narrative(
            _SYNTHESIS_SYSTEM_PROMPT.format(industry=(ctx.get("industry_name") or "media").lower()),
            _synthesis_user_turn(ctx),
        )
        data = json.loads(raw)
        for key in ("profile", *DIM_ORDER):
            if key not in data or not isinstance(data[key], str):
                data[key] = fallback[key]
        return data
    except (ClaudeCallError, json.JSONDecodeError, TypeError) as exc:
        event("claude_api_call", severity="error", subject_id=str(ctx["audit"]["audit_id"]),
              payload={"error": str(exc), "step": "synthesis_v2"})
        return fallback


# ---------------------------------------------------------------------------
# Data loading -- same shape as the live _load_context(), plus the fields
# this template needs (scores_100/bands as plain dicts, eq_identity, etc).
# ---------------------------------------------------------------------------
def _load_context(audit_id: int) -> dict:
    a = rows(
        """SELECT a.audit_id, a.respondent_id, a.audit_version_id, a.started_at, a.completed_at,
                  s.cognitive_empathy, s.eq, s.pressure_composure, s.storytelling, s.raw_band_json,
                  aa.confidence, ar.name AS archetype_name, ar.description AS archetype_description,
                  ar.code AS archetype_code
           FROM audits a
           LEFT JOIN audit_scores s ON s.audit_id = a.audit_id
           LEFT JOIN archetype_assignments aa ON aa.audit_id = a.audit_id AND aa.taxonomy_id = 2
           LEFT JOIN archetypes ar ON ar.archetype_id = aa.archetype_id AND ar.taxonomy_id = 2
           WHERE a.audit_id = %s""",
        (audit_id,),
    )
    if not a:
        raise ValueError(f"audit {audit_id} not found")
    audit = a[0]

    r = rows(
        """SELECT respondent_id, name, first_name, last_name, email, mobile, job_title,
                  team_id, company_id, role
           FROM respondents WHERE respondent_id = %s""",
        (audit["respondent_id"],),
    )[0]

    team = scalar("SELECT name FROM teams WHERE team_id = %s", (r["team_id"],)) if r["team_id"] else None
    company = scalar("SELECT name FROM companies WHERE company_id = %s", (r["company_id"],)) if r["company_id"] else None
    industry_name = scalar(
        """SELECT i.name FROM audit_versions av
           JOIN industries i ON i.industry_id = av.industry_id
           WHERE av.audit_version_id = %s""",
        (audit["audit_version_id"],),
    )

    scores_100 = {
        "cognitive_empathy": (audit.get("cognitive_empathy") or 0.0) * 100.0,
        "eq": (audit.get("eq") or 0.0) * 100.0,
        "pressure_composure": (audit.get("pressure_composure") or 0.0) * 100.0,
        "storytelling": (audit.get("storytelling") or 0.0) * 100.0,
    }
    band_rows = rows(
        "SELECT dimension, band, score FROM band_classifications WHERE audit_id = %s",
        (audit_id,),
    )
    bands_by_dim = {b["dimension"]: b for b in band_rows}
    bands = {dim: bands_by_dim.get(dim, {}).get("band", "-") for dim in DIM_ORDER}

    raw_band = audit.get("raw_band_json") or {}
    if isinstance(raw_band, str):
        raw_band = json.loads(raw_band)
    eq_identity = raw_band.get("eq_identity")

    history = rows(
        """SELECT a.audit_id, a.started_at, a.status,
                  s.cognitive_empathy, s.eq, s.pressure_composure, s.storytelling
           FROM audits a
           LEFT JOIN audit_scores s ON s.audit_id = a.audit_id
           WHERE a.respondent_id = %s
           ORDER BY a.started_at DESC
           LIMIT 6""",
        (r["respondent_id"],),
    )

    return {
        "audit": audit,
        "respondent": r,
        "team_name": team,
        "company_name": company.replace("Demo: ", "") if company else None,
        "industry_name": industry_name,
        "scores_100": scores_100,
        "bands": bands,
        "bands_by_dim": bands_by_dim,
        "eq_identity": eq_identity,
        "archetype_name": audit.get("archetype_name"),
        "archetype_description": audit.get("archetype_description"),
        "archetype_code": audit.get("archetype_code"),
        "confidence": audit.get("confidence") or 0.0,
        "history": history,
    }


def _esc(v: object) -> str:
    return _html.escape(str(v)) if v is not None else ""


# ---------------------------------------------------------------------------
# CSS -- matches the sample's visual language: light card borders, coloured
# accents per trait, a band-coloured left rule on callouts, generous
# whitespace, Apple-system font stack.
# ---------------------------------------------------------------------------
_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: "Liberation Sans", -apple-system, system-ui, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
  font-size: 9.5pt;
  line-height: 1.42;
  color: #1C1C1E;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
@page { size: A4; margin: 13mm 15mm 11mm 15mm; }
.page { break-after: page; }
.page:last-child { break-after: avoid; }

/* ---- masthead ---- */
.masthead { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid #E5E5EA; padding-bottom: 7pt; margin-bottom: 9pt; }
.brand { font-size: 15pt; font-weight: 800; color: #1C1C1E; }
.brand .accent { color: #2FA84F; }
.brand-tag { font-size: 6.5pt; color: #8E8E93; letter-spacing: .04em; text-transform: uppercase; margin-top: 1pt; }
.brand-logo { height: 29pt; width: auto; display: block; }
.meta-row { display: flex; gap: 22pt; text-align: left; }
.meta-block .meta-label { font-size: 6pt; font-weight: 700; color: #8E8E93; letter-spacing: .06em; text-transform: uppercase; margin-bottom: 2pt; }
.meta-block .meta-value { font-size: 8.3pt; font-weight: 700; color: #1C1C1E; }

/* ---- breadcrumb (trait pages) ---- */
.eyebrow { font-size: 6.5pt; font-weight: 700; color: #8E8E93; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 3pt; }
h1.page-title { font-size: 16.5pt; font-weight: 800; margin-bottom: 6pt; }

/* ---- tag chip ---- */
.chip { display: inline-block; border: 1px solid #D1D8CF; color: #2FA84F; background: #F1F8F2; font-size: 6.6pt; font-weight: 700; letter-spacing: .03em; padding: 3px 8px; border-radius: 11px; margin: 0 5pt 5pt 0; }
.chip.neutral { border-color: #E5E5EA; color: #48484A; background: #F7F7F8; }

/* ---- page 1 layout ---- */
.cover-grid { display: grid; grid-template-columns: 1.05fr 0.95fr; gap: 18pt; }
.arch-tag-label { font-size: 6.6pt; font-weight: 700; color: #8E8E93; letter-spacing: .06em; text-transform: uppercase; }
.arch-name { font-size: 21pt; font-weight: 800; line-height: 1.1; margin: 4pt 0 7pt; }
.arch-desc { font-size: 9.8pt; line-height: 1.55; color: #3C3C43; margin-bottom: 10pt; }
.objective-row { margin-bottom: 12pt; }

.section-divider { border: 0; border-top: 1px solid #E5E5EA; margin: 12pt 0; }

.eqid-label { font-size: 6.6pt; font-weight: 700; color: #8E8E93; letter-spacing: .06em; text-transform: uppercase; margin-bottom: 3pt; }
.eqid-name { font-size: 14pt; font-weight: 800; margin-bottom: 5pt; }
.eqid-desc { font-size: 9.6pt; line-height: 1.5; color: #3C3C43; margin-bottom: 7pt; }

.confidential-box { background: #F1F8F2; border: 1px solid #D1E8D4; border-radius: 8px; padding: 9pt 11pt; font-size: 8.8pt; line-height: 1.5; color: #2E6B3A; margin-top: 10pt; }
.confidential-box b { color: #1C5128; }

/* score circle */
.score-panel { border: 1px solid #E5E5EA; border-radius: 10px; padding: 12pt 14pt; display: flex; gap: 12pt; align-items: center; border-left: 4px solid #2FA84F; margin-bottom: 12pt; }
.score-big { font-size: 34pt; font-weight: 800; color: #2FA84F; line-height: 1; }
.score-band-name { font-size: 12pt; font-weight: 800; margin-bottom: 2pt; }
.score-band-desc { font-size: 8.8pt; color: #636366; line-height: 1.4; }

.bars-label { font-size: 6.6pt; font-weight: 700; color: #8E8E93; letter-spacing: .04em; text-transform: uppercase; margin-bottom: 7pt; }
.bar-row { display: flex; align-items: center; gap: 7pt; margin-bottom: 7pt; }
.bar-name { font-size: 9pt; font-weight: 700; width: 108pt; flex-shrink: 0; }
.bar-track { flex: 1; height: 7pt; background: #F0F0F2; border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; }
.bar-score { font-size: 9.6pt; font-weight: 800; width: 20pt; text-align: right; flex-shrink: 0; }
.bar-band { font-size: 6.6pt; font-weight: 700; width: 58pt; text-align: right; flex-shrink: 0; letter-spacing: .02em; }

.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 8pt; margin: 7pt 0; }
.callout-mini { border-radius: 8px; padding: 8pt 10pt; }
.callout-mini.top { background: #F1F8F2; border: 1px solid #D1E8D4; }
.callout-mini.growth { background: #FFF6EC; border: 1px solid #F5DDB8; }
.callout-mini-label { font-size: 6.4pt; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 3pt; }
.callout-mini.top .callout-mini-label { color: #2E8B41; }
.callout-mini.growth .callout-mini-label { color: #C97A12; }
.callout-mini-trait { font-size: 9.6pt; font-weight: 800; margin-bottom: 2pt; }
.callout-mini-score { font-size: 7pt; color: #636366; margin-bottom: 4pt; }
.callout-mini-text { font-size: 8.8pt; line-height: 1.45; color: #3C3C43; }

.contains-label { font-size: 6.6pt; font-weight: 700; color: #8E8E93; letter-spacing: .06em; text-transform: uppercase; margin: 12pt 0 6pt; }
.contains-list { list-style: none; }
.contains-list li { font-size: 9.2pt; line-height: 1.5; padding-left: 13pt; position: relative; margin-bottom: 3pt; }
.contains-list li::before { content: ""; position: absolute; left: 0; top: 6pt; width: 7pt; height: 2px; background: #2FA84F; }

.legend-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4pt; margin-top: 12pt; }
.legend-cell { border: 1px solid #E5E5EA; border-radius: 7px; padding: 6pt 3pt; text-align: center; }
.legend-cell.active { border-color: #2FA84F; background: #F1F8F2; }
.legend-cell-name { font-size: 6.2pt; font-weight: 800; letter-spacing: .04em; color: #8E8E93; }
.legend-cell.active .legend-cell-name { color: #2E8B41; }
.legend-cell-range { font-size: 9.6pt; font-weight: 800; margin-top: 1pt; white-space: nowrap; }

/* ---- trait pages ---- */
.trait-grid { display: grid; grid-template-columns: 92pt 1fr; gap: 13pt; }
.trait-side { }
.trait-score-num { font-size: 25pt; font-weight: 800; line-height: 1; }
.trait-score-denom { font-size: 8pt; color: #8E8E93; margin-bottom: 6pt; }
.trait-track { height: 5pt; background: #F0F0F2; border-radius: 3px; overflow: hidden; margin-bottom: 8pt; }
.trait-track-fill { height: 100%; border-radius: 3px; }
.trait-band-label-sm { font-size: 6.4pt; font-weight: 700; color: #8E8E93; letter-spacing: .04em; text-transform: uppercase; }
.trait-band-name { font-size: 10.5pt; font-weight: 800; margin-top: 1pt; }

.lead-para { font-size: 8.9pt; line-height: 1.42; margin-bottom: 4pt; color: #262628; }

.ladder-label { font-size: 6.4pt; font-weight: 700; color: #8E8E93; letter-spacing: .06em; text-transform: uppercase; margin: 6pt 0 3pt; }
.ladder-row { display: flex; gap: 8pt; padding: 3pt 0; border-bottom: 1px solid #F2F2F3; align-items: flex-start; }
.ladder-row:last-child { border-bottom: none; }
.ladder-row.here { background: #F7FAF7; margin: 0 -6pt; padding: 3pt 6pt; border-radius: 6px; border-bottom-color: transparent; }
.ladder-band-name { width: 68pt; flex-shrink: 0; font-size: 7.4pt; font-weight: 800; letter-spacing: .02em; padding-top: 1pt; }
.ladder-here-tag { display: inline-block; font-size: 5.6pt; font-weight: 800; color: #fff; background: #2FA84F; padding: 1px 5px; border-radius: 5px; margin-top: 2pt; letter-spacing: .03em; }
.ladder-text { font-size: 8.3pt; line-height: 1.32; color: #3C3C43; }

.gap-strength-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7pt; margin: 6pt 0; }
.gs-box { border-radius: 7px; padding: 6pt 8pt; }
.gs-box.strength { background: #F1F8F2; border: 1px solid #D1E8D4; }
.gs-box.gap { background: #FFF6EC; border: 1px solid #F5DDB8; }
.gs-label { font-size: 6.4pt; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 3pt; }
.gs-box.strength .gs-label { color: #2E8B41; }
.gs-box.gap .gs-label { color: #C97A12; }
.gs-text { font-size: 8.2pt; line-height: 1.32; color: #3C3C43; }

.block-heading { font-size: 7.8pt; font-weight: 800; margin: 6pt 0 2pt; }
.block-text { font-size: 8.6pt; line-height: 1.36; color: #262628; margin-bottom: 2pt; }

.callout-rule { border-left: 3px solid; border-radius: 0 6px 6px 0; padding: 5pt 8pt; margin: 6pt 0; }
.callout-rule.where { border-color: #007AFF; background: #F0F6FF; }
.callout-rule.cost { border-color: #C97A12; background: #FFF8EF; }
.callout-rule.action { border-color: #2FA84F; background: #F1F8F2; }
.callout-rule-label { font-size: 6.4pt; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 3pt; }
.callout-rule.where .callout-rule-label { color: #0A5FD1; }
.callout-rule.cost .callout-rule-label { color: #C97A12; }
.callout-rule.action .callout-rule-label { color: #2E8B41; }
.callout-rule-text { font-size: 8.4pt; line-height: 1.34; color: #2E2E30; }

.conversation-box { background: #F7F7F8; border: 1px solid #E5E5EA; border-radius: 7px; padding: 6pt 8pt; margin: 6pt 0; }
.conversation-label { font-size: 6.4pt; font-weight: 700; color: #8E8E93; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 4pt; }
.conversation-text { font-size: 8.3pt; line-height: 1.32; font-style: italic; color: #3C3C43; }

/* ---- roadmap page ---- */
.roadmap-sub { font-size: 8.8pt; color: #636366; margin-bottom: 7pt; }
.week-card { border: 1px solid #E5E5EA; border-radius: 8px; padding: 6pt 10pt; margin-bottom: 5pt; display: flex; gap: 10pt; align-items: flex-start; }
.week-num-col { width: 26pt; flex-shrink: 0; text-align: center; }
.week-num-label { font-size: 6pt; font-weight: 700; color: #8E8E93; letter-spacing: .04em; }
.week-num { font-size: 14pt; font-weight: 800; }
.week-focus { font-size: 6.6pt; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 2pt; }
.week-title { font-size: 9.2pt; font-weight: 800; margin-bottom: 1pt; }
.week-desc { font-size: 8.3pt; line-height: 1.32; color: #3C3C43; }

.immediate-label { font-size: 6.4pt; font-weight: 700; color: #8E8E93; letter-spacing: .06em; text-transform: uppercase; margin: 8pt 0 5pt; }
.immediate-item { display: flex; gap: 8pt; margin-bottom: 5pt; align-items: flex-start; }
.immediate-num { width: 16pt; height: 16pt; border-radius: 4px; background: #1C1C1E; color: #fff; font-size: 8pt; font-weight: 800; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.immediate-title { font-size: 9pt; font-weight: 800; margin-bottom: 1pt; }
.immediate-trait { font-size: 6.4pt; font-weight: 700; color: #2FA84F; letter-spacing: .04em; text-transform: uppercase; margin-bottom: 2pt; }
.immediate-text { font-size: 8.2pt; line-height: 1.3; color: #3C3C43; }

.closing-line { text-align: center; font-size: 9.6pt; font-weight: 700; margin-top: 8pt; padding-top: 7pt; border-top: 1px solid #E5E5EA; }
.closing-line .grey { font-weight: 400; color: #8E8E93; font-style: italic; }

/* ---- glossary ---- */
.gloss-term { font-size: 9.2pt; font-weight: 800; margin-top: 4pt; margin-bottom: 2pt; }
.gloss-def { font-size: 9.2pt; line-height: 1.28; color: #3C3C43; }

"""


def _band_pill_colour(band: str) -> str:
    return BAND_HEX.get(band, "#8E8E93")


def _score_bar_row(dim: str, score: float, band: str) -> str:
    return (
        f'<div class="bar-row">'
        f'<div class="bar-name">{_esc(DIM_LABEL[dim])}</div>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{score:.0f}%;background:{TRAIT_HEX[dim]}"></div></div>'
        f'<div class="bar-score">{score:.0f}</div>'
        f'<div class="bar-band" style="color:{_band_pill_colour(band)}">{BAND_LABEL[band].upper()}</div>'
        f'</div>'
    )


def _legend_row(current_band_overall: str) -> str:
    cells = []
    for band in BAND_ORDER:
        active = " active" if band == current_band_overall else ""
        cells.append(
            f'<div class="legend-cell{active}">'
            f'<div class="legend-cell-name">{BAND_LABEL[band].upper()}</div>'
            f'<div class="legend-cell-range">{BAND_RANGE_LABEL[band]}</div>'
            f'</div>'
        )
    return f'<div class="legend-row">{"".join(cells)}</div>'


def _page1(ctx: dict, synthesis: dict) -> str:
    r = ctx["respondent"]
    scores = ctx["scores_100"]
    bands = ctx["bands"]
    name = r.get("name") or r.get("email") or f"Respondent {r['respondent_id']}"
    audit_date = ctx["audit"]["completed_at"] or ctx["audit"]["started_at"]
    date_str = audit_date.strftime("%d %B %Y") if audit_date else "-"
    subtitle_parts = [r.get("job_title"), ctx.get("company_name")]
    subtitle = ", ".join(p for p in subtitle_parts if p)

    overall = sum(scores.values()) / len(scores)
    overall_band = band_for(overall)

    ranked = sorted(DIM_ORDER, key=lambda d: scores[d])
    weakest, strongest = ranked[0], ranked[-1]

    eq_id = ctx.get("eq_identity")
    eq_content = EQ_IDENTITY_CONTENT.get(eq_id, {})
    eq_chips = "".join(f'<span class="chip">{_esc(c)}</span>' for c in eq_content.get("chips", []))

    objective = ARCHETYPE_OBJECTIVE.get(ctx.get("archetype_code"), "")

    bars = "".join(_score_bar_row(d, scores[d], bands[d]) for d in DIM_ORDER)
    contains_li = "".join(f"<li>{_esc(item)}</li>" for item in REPORT_CONTAINS)

    return f"""<div class="page">
  <div class="masthead">
    <div>
      <img src="{_LOGO_DATA_URI}" class="brand-logo" alt="Decipher">
    </div>
    <div class="meta-row">
      <div class="meta-block"><div class="meta-label">Prepared for</div><div class="meta-value">{_esc(name)}</div><div style="font-size:7.6pt;color:#636366;margin-top:2pt">{_esc(subtitle)}</div></div>
      <div class="meta-block"><div class="meta-label">Audit date</div><div class="meta-value">{_esc(date_str)}</div></div>
      <div class="meta-block"><div class="meta-label">Assessment</div><div class="meta-value">DNA Audit</div><div style="font-size:7.6pt;color:#636366;margin-top:2pt">34-question diagnostic</div></div>
    </div>
  </div>

  <div class="cover-grid">
    <div>
      <div class="arch-tag-label">Performance archetype</div>
      <div class="arch-name">{_esc(ctx.get('archetype_name') or '-')}</div>
      <div class="arch-desc">{_esc(synthesis.get('profile', ''))}</div>
      <div class="objective-row">{f'<span class="chip">{_esc(objective)}</span>' if objective else ''}</div>

      <hr class="section-divider">

      <div class="eqid-label">EQ identity type</div>
      <div class="eqid-name">{_esc(EQ_IDENTITY_LABEL.get(eq_id, eq_id or '-'))}</div>
      <div class="eqid-desc">{_esc(eq_content.get('strength', ''))}</div>
      <div>{eq_chips}</div>

      <div class="confidential-box"><b>Your results are confidential.</b> This report was prepared exclusively for {_esc(name)} and will not be shared with any employer or third party without your explicit consent.</div>
    </div>

    <div>
      <div class="score-panel">
        <div class="score-big">{overall:.0f}</div>
        <div>
          <div class="score-band-name" style="color:{_band_pill_colour(overall_band)}">{BAND_LABEL[overall_band]}</div>
          <div class="score-band-desc">Your composite score across all four communication traits.</div>
        </div>
      </div>

      <div class="bars-label">DNA audit scores | four traits, every conversation depends on them</div>
      {bars}

      <div class="two-col">
        <div class="callout-mini top">
          <div class="callout-mini-label">Top strength</div>
          <div class="callout-mini-trait">{_esc(DIM_LABEL[strongest])}</div>
          <div class="callout-mini-score">{scores[strongest]:.0f} / 100 &nbsp;|&nbsp; {BAND_LABEL[bands[strongest]]}</div>
          <div class="callout-mini-text">{_esc(get_trait_content(strongest, bands[strongest])['strength'])}</div>
        </div>
        <div class="callout-mini growth">
          <div class="callout-mini-label">Primary growth area</div>
          <div class="callout-mini-trait">{_esc(DIM_LABEL[weakest])}</div>
          <div class="callout-mini-score">{scores[weakest]:.0f} / 100 &nbsp;|&nbsp; {BAND_LABEL[bands[weakest]]}</div>
          <div class="callout-mini-text">{_esc(get_trait_content(weakest, bands[weakest])['gap'])}</div>
        </div>
      </div>

      <div class="contains-label">This report contains</div>
      <ul class="contains-list">{contains_li}</ul>

      {_legend_row(overall_band)}
    </div>
  </div>
</div>"""


def _trait_page(ctx: dict, dim: str, synthesis: dict) -> str:
    r = ctx["respondent"]
    name = r.get("name") or r.get("email") or f"Respondent {r['respondent_id']}"
    score = ctx["scores_100"][dim]
    band = ctx["bands"][dim]
    content = get_trait_content(dim, band)
    lead = synthesis.get(dim) or ""
    lead_paras = "".join(f'<p class="lead-para">{_esc(p.strip())}</p>' for p in lead.split("\n\n") if p.strip()) \
        or f'<p class="lead-para">{_esc(content["strength"])}</p>'

    ladder_rows = ""
    for b in BAND_ORDER:
        here = b == band
        row_cls = "ladder-row here" if here else "ladder-row"
        here_tag = '<div class="ladder-here-tag">YOU ARE HERE</div>' if here else ""
        ladder_rows += (
            f'<div class="{row_cls}">'
            f'<div class="ladder-band-name" style="color:{_band_pill_colour(b)}">{BAND_LABEL[b].upper()}{here_tag}</div>'
            f'<div class="ladder-text">{_esc(LADDER[dim][b])}</div>'
            f'</div>'
        )

    audit_date = ctx["audit"]["completed_at"] or ctx["audit"]["started_at"]
    date_str = audit_date.strftime("%d %B %Y") if audit_date else "-"

    return f"""<div class="page">
  <div class="masthead" style="padding-bottom:6pt;margin-bottom:10pt">
    <div class="brand" style="font-size:11pt">Decipher</div>
    <div style="font-size:7.6pt;color:#8E8E93">DNA Audit Report &nbsp;|&nbsp; {_esc(name)} &nbsp;|&nbsp; {_esc(date_str)}</div>
  </div>

  <div class="eyebrow">Trait analysis</div>
  <h1 class="page-title">{_esc(DIM_LABEL[dim])}</h1>

  <div class="trait-grid">
    <div class="trait-side">
      <div class="trait-band-label-sm">{_esc(DIM_LABEL[dim]).upper()}</div>
      <div class="trait-score-num" style="color:{TRAIT_HEX[dim]}">{score:.0f}</div>
      <div class="trait-score-denom">/100</div>
      <div class="trait-track"><div class="trait-track-fill" style="width:{score:.0f}%;background:{TRAIT_HEX[dim]}"></div></div>
      <div class="trait-band-label-sm">Performance band</div>
      <div class="trait-band-name" style="color:{_band_pill_colour(band)}">{BAND_LABEL[band]}</div>
    </div>

    <div>
      {lead_paras}

      <div class="ladder-label">The performance ladder</div>
      {ladder_rows}

      <div class="gap-strength-grid">
        <div class="gs-box strength"><div class="gs-label">Strength</div><div class="gs-text">{_esc(content['strength'])}</div></div>
        <div class="gs-box gap"><div class="gs-label">Gap</div><div class="gs-text">{_esc(content['gap'])}</div></div>
      </div>

      <div class="block-heading">{_esc(content['what_above_heading'])}</div>
      <p class="block-text">{_esc(content['what_above'])}</p>

      <div class="callout-rule where">
        <div class="callout-rule-label">Where you sit</div>
        <div class="callout-rule-text">{_esc(content['where_you_sit'])}</div>
      </div>

      <div class="block-heading">The commercial cost</div>
      <p class="block-text">{_esc(content['commercial_cost'])}</p>

      <div class="conversation-box">
        <div class="conversation-label">What this looks like in a real conversation</div>
        <div class="conversation-text">{_esc(content['conversation_example'])}</div>
      </div>

      <div class="callout-rule action">
        <div class="callout-rule-label">Your next action</div>
        <div class="callout-rule-text">{_esc(content['next_action'])}</div>
      </div>
    </div>
  </div>
</div>"""


def _roadmap_page(ctx: dict) -> str:
    r = ctx["respondent"]
    name = r.get("name") or r.get("email") or f"Respondent {r['respondent_id']}"
    scores = ctx["scores_100"]
    bands = ctx["bands"]
    ranked = sorted(DIM_ORDER, key=lambda d: scores[d])
    weakest, strongest = ranked[0], ranked[-1]
    week_traits = ranked[:3]  # 3 lowest-scoring traits get their own week

    week_cards = ""
    for i, dim in enumerate(week_traits, 1):
        content = get_trait_content(dim, bands[dim])
        # Reuse next_action as the week's focus content, first sentence as a title cue.
        title = content["next_action"].split(".")[0].strip()
        week_cards += (
            f'<div class="week-card">'
            f'<div class="week-num-col"><div class="week-num-label">WEEK</div><div class="week-num">{i}</div></div>'
            f'<div><div class="week-focus" style="color:{TRAIT_HEX[dim]}">Focus: {_esc(DIM_LABEL[dim]).upper()}</div>'
            f'<div class="week-title">{_esc(title)}</div>'
            f'<div class="week-desc">{_esc(content["next_action"])}</div></div>'
            f'</div>'
        )
    week_cards += (
        '<div class="week-card">'
        '<div class="week-num-col"><div class="week-num-label">WEEK</div><div class="week-num">4</div></div>'
        '<div><div class="week-focus" style="color:#636366">FOCUS: INTEGRATION</div>'
        '<div class="week-title">Run all three simultaneously</div>'
        f'<div class="week-desc">Apply the previous three weeks\' actions in the same call. Note where the gaps still surface. This is the week you find out what has stuck.</div></div>'
        '</div>'
    )

    immediate_items = ""
    for i, dim in enumerate(week_traits, 1):
        content = get_trait_content(dim, bands[dim])
        title = content["next_action"].split(".")[0].strip()
        immediate_items += (
            f'<div class="immediate-item">'
            f'<div class="immediate-num">{i}</div>'
            f'<div><div class="immediate-title">{_esc(title)}</div>'
            f'<div class="immediate-trait" style="color:{TRAIT_HEX[dim]}">{_esc(DIM_LABEL[dim]).upper()}</div>'
            f'<div class="immediate-text">{_esc(content["next_action"])}</div></div>'
            f'</div>'
        )

    strongest_content = get_trait_content(strongest, bands[strongest])
    weakest_content = get_trait_content(weakest, bands[weakest])

    return f"""<div class="page">
  <div class="masthead" style="padding-bottom:6pt;margin-bottom:10pt">
    <div class="brand" style="font-size:11pt">Decipher</div>
    <div style="font-size:7.6pt;color:#8E8E93">DNA Audit Report &nbsp;|&nbsp; {_esc(name)}</div>
  </div>

  <div class="eyebrow">Development roadmap</div>
  <h1 class="page-title">30-Day Action Plan</h1>
  <div class="roadmap-sub">Personalised for {_esc(name)} &nbsp;|&nbsp; {_esc(ctx.get('archetype_name') or '')}</div>

  <div class="two-col">
    <div class="callout-mini top">
      <div class="callout-mini-label">Top strength</div>
      <div class="callout-mini-trait">{_esc(DIM_LABEL[strongest])}</div>
      <div class="callout-mini-score">{scores[strongest]:.0f} / 100 &nbsp;|&nbsp; {BAND_LABEL[bands[strongest]]}</div>
      <div class="callout-mini-text">{_esc(strongest_content['strength'])}</div>
    </div>
    <div class="callout-mini growth">
      <div class="callout-mini-label">Primary growth area</div>
      <div class="callout-mini-trait">{_esc(DIM_LABEL[weakest])}</div>
      <div class="callout-mini-score">{scores[weakest]:.0f} / 100 &nbsp;|&nbsp; {BAND_LABEL[bands[weakest]]}</div>
      <div class="callout-mini-text">{_esc(weakest_content['gap'])}</div>
    </div>
  </div>

  <div class="contains-label">Four-week focus plan</div>
  {week_cards}

  <div class="immediate-label">3 immediate actions</div>
  {immediate_items}

  <div class="closing-line">The gap between Performing and Elite is not talent. <span class="grey">It is repetition under real conditions. This report tells you exactly where to focus. What happens next is up to you.</span></div>
</div>"""


_GLOSSARY_TERMS = [
    ("DNA Audit", "Decipher's diagnostic assessment. A 34-question instrument that measures the four communication traits shaping every sales conversation, and places you within four performance bands."),
    ("Overall DNA Score", "Your composite score across all four traits, out of 100. It reflects your all-round communication effectiveness rather than any single skill, and sets your overall performance band."),
    ("Cognitive Empathy", "The ability to read what a buyer is thinking and feeling, including what they leave unsaid, and to diagnose the source of their hesitation rather than only sensing it."),
    ("Emotional Intelligence", "The ability to read the emotional climate of a room and shape it, distinguishing what a buyer says they need from what they privately fear, and adjusting in response."),
    ("Pressure Composure", "How you respond when a buyer applies pressure on price, timing or competitors: whether you pause and question, or default to defending and discounting."),
    ("Narrative Persuasion", "The ability to turn information into a narrative a buyer remembers and repeats, framed around the client as the hero rather than the product."),
    ("Performance Bands", "The four levels each trait is scored against: Developing (0-39), Practising (40-64), Performing (65-84) and Elite (85-100). They describe current behaviour, not potential."),
    ("Performance Ladder", "The four-band progression shown for each trait. It marks where you currently sit and describes, in concrete behaviour, what the bands below and above look like."),
    ("Performance Archetype", "A summary of your overall communication style, drawn from the pattern across your four trait scores. It captures how buyers tend to experience you."),
    ("EQ Identity Type", "A description of your most natural emotional-intelligence move in live conversations: the instinct you reach for most when reading a room."),
    ("Strength & Gap", "For each trait, the behaviour you already do well (Strength) and the single most valuable behaviour to develop next (Gap)."),
    ("Development Roadmap", "Your personalised 30-day plan: a week-by-week focus and a set of immediate actions, sequenced to close your primary gap first."),
]


def _glossary_page(ctx: dict) -> str:
    r = ctx["respondent"]
    name = r.get("name") or r.get("email") or f"Respondent {r['respondent_id']}"
    terms = "".join(f'<div class="gloss-term">{_esc(t)}</div><div class="gloss-def">{_esc(d)}</div>' for t, d in _GLOSSARY_TERMS)

    eq_terms = "".join(
        f'<div class="gloss-term">{_esc(EQ_IDENTITY_LABEL[k])}</div>'
        f'<div class="gloss-def">{_esc(EQ_IDENTITY_CONTENT[k]["strength"])}</div>'
        for k in ("regulator", "edge_builder", "observer", "namer")
    )

    return f"""<div class="page">
  <div class="eyebrow">Reference</div>
  <h1 class="page-title">Glossary of Terms</h1>
  <p style="font-size:8.4pt;color:#636366;margin-bottom:5pt">The key terms used throughout your DNA Audit report, defined. Every score, band and trait in this report maps back to one of the definitions below.</p>
  {terms}
  {eq_terms}
</div>"""


def _build_html(ctx: dict, synthesis: dict) -> str:
    pages = [_page1(ctx, synthesis)]
    for dim in DIM_ORDER:
        pages.append(_trait_page(ctx, dim, synthesis))
    pages.append(_roadmap_page(ctx))
    pages.append(_glossary_page(ctx))

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><style>{_CSS}</style></head>
<body>
{''.join(pages)}
</body>
</html>"""


def _render_pdf(html: str, audit_id: int) -> bytes:
    from playwright.sync_api import sync_playwright

    footer = (
        f'<div style="font-family:sans-serif;font-size:7px;color:#8E8E93;'
        f'text-align:center;width:100%;padding:0 18mm">'
        f'decipher.com.au &nbsp;&middot;&nbsp; Confidential individual report'
        f' &nbsp;&middot;&nbsp; Audit #{audit_id}'
        f' &nbsp;&middot;&nbsp; Page <span class="pageNumber"></span>'
        f' of <span class="totalPages"></span>'
        f'</div>'
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="domcontentloaded")
            pdf_bytes = page.pdf(
                format="A4", print_background=True, display_header_footer=False,
                header_template="<span></span>", footer_template="",
                margin={"top": "15mm", "bottom": "15mm", "left": "18mm", "right": "18mm"},
            )
        finally:
            browser.close()
    return pdf_bytes


def generate_report(audit_id: int) -> dict:
    """Render the report, persist to disk and the reports table.
    Same signature/side effects as the live app/dna_report.py.
    """
    ctx = _load_context(audit_id)
    r = ctx["respondent"]

    synthesis = _get_synthesis(ctx)
    html = _build_html(ctx, synthesis)
    pdf_bytes = _render_pdf(html, audit_id)

    fname = (
        f"respondent_{r['respondent_id']}_audit_{audit_id}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )
    pdf_path = REPORT_DIR / fname
    pdf_path.write_bytes(pdf_bytes)

    with conn() as cdb, cdb.cursor() as cur:
        cur.execute("SELECT COALESCE(max(version), 0) + 1 FROM reports WHERE audit_id = %s", (audit_id,))
        version = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO reports (audit_id, pdf_path, version, recipient_email)
               VALUES (%s, %s, %s, %s) RETURNING report_id""",
            (audit_id, str(pdf_path), version, r.get("email")),
        )
        report_id = cur.fetchone()[0]
        cur.execute(
            "UPDATE audits SET status = 'reported' WHERE audit_id = %s AND status IN ('scored','completed')",
            (audit_id,),
        )

    event("audit.reported", subject_id=str(audit_id),
          payload={"report_id": report_id, "version": version, "pdf_path": str(pdf_path)})

    return {"report_id": report_id, "pdf_path": str(pdf_path), "version": version}
