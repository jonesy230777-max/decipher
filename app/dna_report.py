"""3-page individual DNA audit report (media_sales_v1).

Page 1: Identity + headline scores + archetype + EQ identity
Page 2: EQ signature + per-trait narratives from narrative_library
Page 3: Coaching priorities + audit history

`generate_report(audit_id)` renders HTML via Playwright Chromium to PDF,
writes to var/reports/, inserts a row into the reports table.
Idempotent: bumps version on each call.
"""
from __future__ import annotations

import html as _html
import json
import os
from datetime import datetime
from pathlib import Path

from app.db import conn, rows, scalar, event

REPORT_DIR = Path(os.getenv("DECIPHER_REPORT_DIR", "var/reports"))
REPORT_DIR.mkdir(parents=True, exist_ok=True)

DIM_LABEL = {
    "cognitive_empathy":  "Cognitive Empathy",
    "eq":                 "Emotional Intelligence",
    "pressure_composure": "Pressure Composure",
    "storytelling":       "Narrative Persuasion",
}
DIM_ORDER = ["cognitive_empathy", "eq", "pressure_composure", "storytelling"]

BAND_HEX = {
    "elite":      "#34C759",
    "performing": "#007AFF",
    "practising": "#FF9500",
    "developing": "#FF3B30",
}

EQ_IDENTITY_LABEL = {
    "regulator":    "Regulator",
    "edge_builder": "Edge Builder",
    "observer":     "Observer",
    "namer":        "Namer",
}

_NARRATIVE_SYSTEM_PROMPT = """\
You are writing the personal narrative section of a DNA Audit report for a media sales professional. \
The report is produced by Decipher, an Australian sales intelligence platform.

Your role is to write 3-5 sentences that synthesise this person's four dimension scores into a \
coherent, personal portrait. This should read like a skilled executive coach describing what they \
observe in this person's profile, not a scorecard or a feature list.

The four dimensions measured in this audit:

Cognitive Empathy: the ability to read and name what a buyer is feeling, to hold silence without \
filling it, and to ask calibrated questions rather than offer solutions prematurely. Elite performers \
use this to build trust inside the first two minutes of a call.

Emotional Intelligence: reading emotional dynamics and adapting approach to the individual buyer \
rather than following a script. Understanding that the stated objection is rarely the real one, \
and responding to what the buyer means, not what they say.

Pressure Composure: staying diagnostically calm under objection, rate challenges, and competitor \
comparisons. Replacing defensive reflexes with genuine inquiry. The ability to treat an objection \
as information rather than an attack.

Narrative Persuasion: structuring stories using the L.E.A.D. framework (Location, Emotion, Action, \
Direct quote) and S.T.A.R. moments (Specific, Tactical, Authentic, Relevant). Making numbers \
visceral rather than abstract. Ensuring the client is always the hero of the story.

Band thresholds (for your context, do not quote these labels verbatim in the output):
Elite (85 and above): this skill is a genuine competitive advantage; the person is ready to teach others.
Performing (65 to 84): the skill is reliable and ready for refinement.
Practising (40 to 64): the person is aware of the skill but applies it inconsistently.
Developing (under 40): foundational habits are still forming.

Writing rules:
- Write in second person throughout ("You", "Your").
- Australian English: practise, behaviour, recognise, colour, organisation.
- No em dashes. Use a comma or a full stop instead.
- No generic filler: no "unlock", "elevate", "seamless", "leverage", "empower", "game-changer", \
"tapestry", "delve", "in today's fast-paced world".
- No bro-sales clichés: no "close", "crush it", "killer instinct".
- Do not name the band labels (developing, practising, performing, elite) explicitly in the output. \
Describe the observed behaviour instead.
- Do not name the archetype; it appears separately in the report.
- Describe the pattern across all four dimensions: what does this particular combination say about \
how this person sells?
- If one dimension is an outlier relative to the others, name the commercial consequence. A \
storyteller who crumbles under pressure sells differently from an empathetic listener who cannot \
frame a narrative under load.
- End with exactly one sentence identifying the single highest-leverage development opportunity, or \
for profiles where all scores are above 85, the contribution opportunity.
- Plain text only. No markdown, no bullet points, no headings, no bold, no asterisks.
- Between 3 and 5 sentences total. No more, no fewer.
"""

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, system-ui, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
  font-size: 9pt;
  line-height: 1.45;
  color: #1C1C1E;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

@page { size: A4; }

.page {
  break-after: page;
  padding-bottom: 8mm;
}
.page:last-child { break-after: avoid; }

h1 {
  font-size: 20pt;
  font-weight: 700;
  line-height: 1.1;
  margin-bottom: 2pt;
}
.subtitle { font-size: 9pt; color: #636366; margin-bottom: 8pt; }

hr {
  border: 0;
  border-top: 1px solid #E5E5EA;
  margin: 8pt 0;
}

.respondent-name { font-size: 15pt; font-weight: 700; margin: 6pt 0 2pt; }
.respondent-meta { font-size: 8.5pt; color: #636366; margin-bottom: 10pt; }

/* Score grid */
.score-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 7pt;
  margin-bottom: 10pt;
}
.score-card {
  background: #F2F2F7;
  border-radius: 8px;
  padding: 9pt 11pt;
}
.sc-label {
  font-size: 6.5pt;
  font-weight: 600;
  color: #636366;
  letter-spacing: 0.05em;
  margin-bottom: 4pt;
}
.sc-row { display: flex; align-items: baseline; gap: 3pt; }
.sc-value { font-size: 22pt; font-weight: 700; }
.sc-denom { font-size: 8pt; color: #8E8E93; }
.sc-pill { margin-left: auto; align-self: center; }

/* Band pill */
.pill {
  display: inline-block;
  color: #fff;
  font-size: 6.5pt;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 10px;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

/* Archetype panel */
.archetype-panel {
  background: #1A57C7;
  color: #fff;
  border-radius: 8px;
  padding: 12pt 14pt;
  margin-bottom: 10pt;
}
.arch-label {
  font-size: 6.5pt;
  font-weight: 600;
  letter-spacing: 0.06em;
  opacity: 0.75;
  margin-bottom: 3pt;
}
.arch-name { font-size: 17pt; font-weight: 700; margin-bottom: 3pt; }
.arch-meta { font-size: 8pt; opacity: 0.85; margin-bottom: 6pt; }
.arch-desc { font-size: 8.5pt; opacity: 0.92; line-height: 1.5; }

.method-note {
  font-size: 7.5pt;
  color: #8E8E93;
  font-style: italic;
  line-height: 1.4;
  margin-top: 6pt;
}

/* Page 2 */
.section-heading { font-size: 14pt; font-weight: 700; margin: 0 0 7pt; }

.eq-panel {
  background: #F2F2F7;
  border-radius: 8px;
  padding: 11pt 13pt;
  margin-bottom: 10pt;
}
.eq-type-name {
  font-size: 11pt;
  font-weight: 700;
  color: #1A57C7;
  margin-bottom: 5pt;
}
.eq-panel p { font-size: 8.5pt; line-height: 1.5; margin-bottom: 4pt; }

.trait-section {
  margin-bottom: 8pt;
  padding-bottom: 8pt;
  border-bottom: 1px solid #E5E5EA;
}
.trait-section:last-child { border-bottom: none; margin-bottom: 0; }

.trait-hd {
  display: flex;
  align-items: baseline;
  gap: 5pt;
  margin-bottom: 3pt;
  flex-wrap: wrap;
}
.trait-name { font-size: 11pt; font-weight: 700; }
.score-inline { font-size: 8.5pt; color: #636366; }

.what-label {
  font-size: 8pt;
  font-weight: 600;
  color: #636366;
  margin: 3pt 0 2pt;
}
.strength-text { font-size: 8.5pt; line-height: 1.5; margin-bottom: 3pt; }
.action-label { font-size: 8pt; font-weight: 700; color: #1A57C7; margin-bottom: 2pt; }
.action-text { font-size: 8.5pt; color: #1A57C7; line-height: 1.5; }
.no-narrative { font-size: 8pt; color: #8E8E93; font-style: italic; }

/* Page 3 */
.hint { font-size: 8.5pt; color: #636366; margin-bottom: 10pt; }

.priority-item { margin-bottom: 7pt; }
.priority-hd { display: flex; align-items: baseline; gap: 5pt; margin-bottom: 2pt; }
.priority-rank { font-size: 10pt; font-weight: 700; color: #8E8E93; min-width: 14pt; }
.priority-name { font-size: 10pt; font-weight: 700; }
.priority-score { font-size: 8.5pt; color: #636366; margin-left: auto; }
.priority-action { font-size: 8.5pt; line-height: 1.5; padding-left: 14pt; }

.history-table { width: 100%; border-collapse: collapse; font-size: 8.5pt; margin-top: 6pt; }
.history-table th {
  font-weight: 600;
  color: #636366;
  text-align: left;
  padding: 4pt 0;
  border-bottom: 1px solid #E5E5EA;
}
.history-table td {
  padding: 4pt 0;
  border-bottom: 1px solid #F2F2F7;
  color: #3C3C43;
}

/* Claude narrative */
.narrative-section {
  border-left: 3px solid #1A57C7;
  background: #F0F5FF;
  border-radius: 0 6px 6px 0;
  padding: 8pt 11pt;
  margin-bottom: 10pt;
}
.narrative-label {
  font-size: 6.5pt;
  font-weight: 600;
  color: #1A57C7;
  letter-spacing: 0.05em;
  margin-bottom: 4pt;
}
.narrative-text { font-size: 9pt; line-height: 1.55; }
"""


def _load_context(audit_id: int) -> dict:
    a = rows(
        """SELECT a.audit_id, a.respondent_id, a.audit_version_id, a.started_at, a.completed_at,
                  s.cognitive_empathy, s.eq, s.pressure_composure, s.storytelling, s.raw_band_json,
                  aa.confidence, ar.name AS archetype_name, ar.description AS archetype_description,
                  ar.code AS archetype_code
             FROM audits a
        LEFT JOIN audit_scores s ON s.audit_id = a.audit_id
        LEFT JOIN archetype_assignments aa ON aa.audit_id = a.audit_id
        LEFT JOIN archetypes ar ON ar.archetype_id = aa.archetype_id
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

    bands = rows(
        "SELECT dimension, band, score FROM band_classifications WHERE audit_id = %s",
        (audit_id,),
    )
    bands_by_dim = {b["dimension"]: b for b in bands}

    narratives = rows(
        """SELECT dimension, band, strength, action
             FROM narrative_library
            WHERE taxonomy_code = 'media_sales_v1'""",
    )
    narratives_by = {(n["dimension"], n["band"]): n for n in narratives}

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
        "bands_by_dim": bands_by_dim,
        "narratives_by": narratives_by,
        "history": history,
    }


def _build_user_turn(ctx: dict) -> str:
    audit = ctx["audit"]
    r = ctx["respondent"]

    name = r.get("name") or r.get("first_name") or "this respondent"
    scores = {dim: (audit.get(dim) or 0.0) * 100.0 for dim in DIM_ORDER}
    bands = {dim: ctx["bands_by_dim"].get(dim, {}).get("band", "unknown") for dim in DIM_ORDER}

    raw_band = audit.get("raw_band_json") or {}
    if isinstance(raw_band, str):
        raw_band = json.loads(raw_band)
    eq_id = raw_band.get("eq_identity")
    eq_label = EQ_IDENTITY_LABEL.get(eq_id, eq_id or "unknown")

    lines = [
        f"Respondent: {name}",
        f"Role: {r.get('job_title') or 'Media sales professional'}",
        "",
        "Dimension scores:",
    ]
    for dim in DIM_ORDER:
        lines.append(f"  {DIM_LABEL[dim]}: {scores[dim]:.1f}/100")
    lines += [
        "",
        f"Archetype: {audit.get('archetype_name') or 'unknown'}",
        f"EQ identity: {eq_label}",
        "",
        "Write the personal narrative paragraph for this profile.",
    ]
    return "\n".join(lines)


def _esc(v: object) -> str:
    return _html.escape(str(v)) if v is not None else ""


def _fmt_score(v: object) -> str:
    return f"{float(v) * 100:.1f}" if v is not None else "-"


def _pill(band: str) -> str:
    colour = BAND_HEX.get(band, "#8E8E93")
    label = band.upper() if band and band not in ("-", "") else "-"
    return f'<span class="pill" style="background:{colour}">{_esc(label)}</span>'


def _score_card(dim: str, score_100: float, band: str) -> str:
    label = DIM_LABEL.get(dim, dim).upper()
    return (
        f'<div class="score-card">'
        f'<div class="sc-label">{_esc(label)}</div>'
        f'<div class="sc-row">'
        f'<span class="sc-value">{score_100:.1f}</span>'
        f'<span class="sc-denom">/100</span>'
        f'<span class="sc-pill">{_pill(band)}</span>'
        f'</div></div>'
    )


def _trait_section(dim: str, score_100: float, band: str, narrative: dict | None) -> str:
    label = DIM_LABEL.get(dim, dim)
    strength = narrative.get("strength", "") if narrative else ""
    action = narrative.get("action", "") if narrative else ""

    strength_block = (
        f'<div class="what-label">What this means</div>'
        f'<p class="strength-text">{_esc(strength)}</p>'
        if strength
        else '<p class="no-narrative">Narrative pending.</p>'
    )
    action_block = (
        f'<div class="action-label">Action</div>'
        f'<p class="action-text">{_esc(action)}</p>'
        if action
        else ""
    )
    return (
        f'<div class="trait-section">'
        f'<div class="trait-hd">'
        f'<span class="trait-name">{_esc(label)}</span>'
        f'<span class="score-inline">{score_100:.1f}/100</span>'
        f'{_pill(band)}'
        f'</div>'
        f'{strength_block}{action_block}'
        f'</div>'
    )


def _build_html(ctx: dict, audit_id: int, claude_narrative: str = "") -> str:
    audit = ctx["audit"]
    r = ctx["respondent"]

    name = r.get("name") or r.get("email") or f"Respondent {r['respondent_id']}"
    subtitle_parts = [r.get("job_title"), ctx.get("team_name"), ctx.get("company_name"), r.get("email")]
    subtitle = " · ".join(p for p in subtitle_parts if p)

    scores = {dim: (audit.get(dim) or 0.0) * 100.0 for dim in DIM_ORDER}
    bands = {dim: ctx["bands_by_dim"].get(dim, {}).get("band", "-") for dim in DIM_ORDER}

    raw_band = audit.get("raw_band_json") or {}
    if isinstance(raw_band, str):
        raw_band = json.loads(raw_band)
    eq_id = raw_band.get("eq_identity")
    conf_str = f"{(audit.get('confidence') or 0.0) * 100:.0f}%"
    eq_label = EQ_IDENTITY_LABEL.get(eq_id, eq_id or "-")
    archetype_name = audit.get("archetype_name") or "-"
    archetype_desc = audit.get("archetype_description") or ""

    # --- Page 1 ---
    score_cards = "".join(_score_card(dim, scores[dim], bands[dim]) for dim in DIM_ORDER)

    narrative_block = (
        f'<div class="narrative-section">'
        f'<div class="narrative-label">YOUR PROFILE</div>'
        f'<p class="narrative-text">{_esc(claude_narrative)}</p>'
        f'</div>'
        if claude_narrative.strip()
        else ""
    )

    arch_desc_block = f'<p class="arch-desc">{_esc(archetype_desc)}</p>' if archetype_desc else ""

    method_note = (
        "Scores are normalised to 0-100. Band thresholds: Elite 85+, Performing 65-84, "
        "Practising 40-64, Developing under 40. Archetype is derived from the two highest "
        "traits, with all-high and all-low special cases."
    )

    # --- Page 2: EQ section ---
    eq_section = ""
    if eq_id:
        eq_narr = ctx["narratives_by"].get(("eq_identity", eq_id))
        eq_strength = _esc(eq_narr["strength"]) if eq_narr and eq_narr.get("strength") else ""
        eq_action = _esc(eq_narr["action"]) if eq_narr and eq_narr.get("action") else ""
        eq_section = (
            f'<div class="section-heading">Your EQ signature</div>'
            f'<div class="eq-panel">'
            f'<div class="eq-type-name">{_esc(eq_label)}</div>'
            + (f"<p>{eq_strength}</p>" if eq_strength else "")
            + (f'<div class="action-label">Action</div><p class="action-text">{eq_action}</p>' if eq_action else "")
            + f'</div><hr>'
        )

    trait_sections = "".join(
        _trait_section(
            dim, scores[dim], bands[dim],
            ctx["narratives_by"].get((dim, bands[dim])) if bands[dim] != "-" else None,
        )
        for dim in DIM_ORDER
    )

    # --- Page 3: coaching priorities ---
    ranked = sorted(DIM_ORDER, key=lambda d: scores[d])
    priority_items = ""
    for rank, dim in enumerate(ranked, 1):
        band = bands[dim]
        n = ctx["narratives_by"].get((dim, band)) if band != "-" else None
        action_text = _esc(n["action"]) if n and n.get("action") else ""
        action_p = f'<p class="priority-action">{action_text}</p>' if action_text else ""
        priority_items += (
            f'<div class="priority-item">'
            f'<div class="priority-hd">'
            f'<span class="priority-rank">{rank}.</span>'
            f'<span class="priority-name">{_esc(DIM_LABEL.get(dim, dim))}</span>'
            f'<span class="priority-score">{scores[dim]:.1f}/100 · {band}</span>'
            f'</div>{action_p}</div>'
        )

    # --- Page 3: audit history ---
    history_rows_html = ""
    for h in ctx["history"]:
        date = h["started_at"].strftime("%Y-%m-%d")
        history_rows_html += (
            f"<tr>"
            f"<td>{date}</td>"
            f"<td>{_esc(h['status'])}</td>"
            f"<td>{_fmt_score(h['cognitive_empathy'])}</td>"
            f"<td>{_fmt_score(h['eq'])}</td>"
            f"<td>{_fmt_score(h['pressure_composure'])}</td>"
            f"<td>{_fmt_score(h['storytelling'])}</td>"
            f"</tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>{_CSS}</style>
</head>
<body>

<div class="page">
  <h1>Decipher DNA Audit</h1>
  <div class="subtitle">Media Sales DNA v1 &nbsp;&middot;&nbsp; Individual report</div>
  <hr>
  <div class="respondent-name">{_esc(name)}</div>
  <div class="respondent-meta">{_esc(subtitle)}</div>
  <div class="score-grid">{score_cards}</div>
  {narrative_block}
  <div class="archetype-panel">
    <div class="arch-label">ARCHETYPE</div>
    <div class="arch-name">{_esc(archetype_name)}</div>
    <div class="arch-meta">Confidence {_esc(conf_str)} &nbsp;&middot;&nbsp; EQ identity: {_esc(eq_label)}</div>
    {arch_desc_block}
  </div>
  <p class="method-note">{_esc(method_note)}</p>
</div>

<div class="page">
  {eq_section}
  <div class="section-heading">Where you stand, trait by trait</div>
  {trait_sections}
</div>

<div class="page">
  <div class="section-heading">Coaching priorities</div>
  <p class="hint">Address from weakest to strongest. Each 5-point lift compounds across the funnel.</p>
  {priority_items}
  <hr style="margin-top:12pt">
  <div class="section-heading" style="margin-top:10pt">Audit history</div>
  <table class="history-table">
    <thead>
      <tr><th>Date</th><th>Status</th><th>CE</th><th>EQ</th><th>PC</th><th>NP</th></tr>
    </thead>
    <tbody>{history_rows_html}</tbody>
  </table>
</div>

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
                format="A4",
                print_background=True,
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=footer,
                margin={"top": "15mm", "bottom": "15mm", "left": "18mm", "right": "18mm"},
            )
        finally:
            browser.close()
    return pdf_bytes


def generate_report(audit_id: int) -> dict:
    """Render the 3-page PDF, persist to disk and the reports table.
    Returns { report_id, pdf_path, version }.
    """
    from app.claude_client import complete_narrative, ClaudeCallError

    ctx = _load_context(audit_id)
    r = ctx["respondent"]

    claude_narrative = ""
    try:
        claude_narrative = complete_narrative(
            _NARRATIVE_SYSTEM_PROMPT,
            _build_user_turn(ctx),
        )
    except ClaudeCallError as exc:
        event("claude_api_call", severity="error", subject_id=str(audit_id),
              payload={"error": str(exc), "step": "narrative"})

    html = _build_html(ctx, audit_id, claude_narrative=claude_narrative)
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
                 VALUES (%s, %s, %s, %s)
              RETURNING report_id""",
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
