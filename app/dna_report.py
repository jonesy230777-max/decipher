"""3-page individual DNA audit report (media_sales_v1).

Page 1: Identity + headline scores + archetype + EQ identity
Page 2: Per-trait narratives from narrative_library (strength + action)
Page 3: Coaching priorities + audit history

`generate_report(audit_id)` writes a PDF to var/reports/ and inserts a row
into the reports table. Idempotent: bumps version on each call.
"""
from __future__ import annotations
import io
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

BAND_COLOUR = {
    "elite":      (0.20, 0.78, 0.35),
    "performing": (0.23, 0.51, 0.91),
    "practising": (0.89, 0.63, 0.23),
    "developing": (0.78, 0.24, 0.24),
}

EQ_IDENTITY_LABEL = {
    "regulator":    "Regulator",
    "edge_builder": "Edge Builder",
    "observer":     "Observer",
    "namer":        "Namer",
}


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

    return {
        "audit": audit,
        "respondent": r,
        "team_name": team,
        "company_name": company.replace("Demo: ", "") if company else None,
        "bands_by_dim": bands_by_dim,
        "narratives_by": narratives_by,
    }


def _draw_band_pill(c, x, y, band: str, w=22 * 2.83, h=10):
    from reportlab.lib import colors
    cr, cg, cb = BAND_COLOUR.get(band, (0.5, 0.5, 0.55))
    c.setFillColorRGB(cr, cg, cb)
    c.roundRect(x, y, w, h, 4, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(x + w / 2, y + 3, band.upper())


def _wrapped(c, body, x, y, max_chars=95, size=9, leading=12, colour=(0.30, 0.30, 0.35)) -> float:
    c.setFillColorRGB(*colour)
    c.setFont("Helvetica", size)
    words = body.split()
    line = ""
    for w in words:
        if len(line) + len(w) + 1 > max_chars:
            c.drawString(x, y, line)
            y -= leading
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        c.drawString(x, y, line)
        y -= leading
    return y


def generate_report(audit_id: int) -> dict:
    """Render the 3-page report, persist to disk + reports table.
    Returns { report_id, pdf_path, version }.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdf_canvas

    ctx = _load_context(audit_id)
    audit = ctx["audit"]
    r = ctx["respondent"]

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    margin = 18 * mm

    def footer(page_num: int):
        c.setFillColorRGB(0.55, 0.55, 0.60)
        c.setFont("Helvetica", 8)
        c.drawCentredString(W / 2, 12 * mm,
                            f"decipher.com.au · Confidential individual report · "
                            f"Audit #{audit_id} · Page {page_num}")

    # ===== Page 1 =====
    y = H - margin
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(margin, y, "Decipher DNA Audit")
    y -= 8
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.45, 0.45, 0.50)
    c.drawString(margin, y, "Media Sales DNA v1 · Individual report")
    y -= 22

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, r["name"] or r["email"] or f"Respondent {r['respondent_id']}")
    y -= 14
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.45, 0.45, 0.50)
    parts = [r.get("job_title"), ctx["team_name"], ctx["company_name"], r.get("email")]
    c.drawString(margin, y, " · ".join([p for p in parts if p]))
    y -= 20

    c.setStrokeColorRGB(0.85, 0.85, 0.87)
    c.line(margin, y, W - margin, y)
    y -= 18

    # Scores grid (2 x 2)
    box_w = (W - 2 * margin - 12) / 2
    box_h = 60
    for i, dim in enumerate(DIM_ORDER):
        col = i % 2
        row = i // 2
        bx = margin + col * (box_w + 12)
        by = y - row * (box_h + 10) - box_h

        score_0_1 = audit.get(dim) or 0.0
        score_100 = score_0_1 * 100.0
        band = ctx["bands_by_dim"].get(dim, {}).get("band", "-")

        c.setFillColorRGB(0.97, 0.97, 0.98)
        c.roundRect(bx, by, box_w, box_h, 6, fill=1, stroke=0)
        c.setStrokeColorRGB(0.88, 0.88, 0.90)
        c.roundRect(bx, by, box_w, box_h, 6, fill=0, stroke=1)

        c.setFillColorRGB(0.45, 0.45, 0.50)
        c.setFont("Helvetica", 9)
        c.drawString(bx + 10, by + box_h - 14, DIM_LABEL[dim].upper())

        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 26)
        c.drawString(bx + 10, by + 22, f"{score_100:.1f}")
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.55, 0.55, 0.60)
        c.drawString(bx + 10 + 50, by + 26, "/ 100")

        _draw_band_pill(c, bx + box_w - 70, by + 16, band, w=60, h=14)
    y -= 2 * (box_h + 10) + 8

    # Archetype panel (taller — includes one-line description)
    panel_h = 96
    c.setFillColorRGB(0.10, 0.34, 0.78)
    c.roundRect(margin, y - panel_h, W - 2 * margin, panel_h, 6, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 9)
    c.drawString(margin + 12, y - 16, "ARCHETYPE")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin + 12, y - 36, audit.get("archetype_name") or "-")

    raw = audit.get("raw_band_json") or {}
    if isinstance(raw, str):
        import json as _j
        raw = _j.loads(raw)
    eq_id = raw.get("eq_identity")
    conf = audit.get("confidence") or 0.0
    c.setFont("Helvetica", 9)
    c.drawString(margin + 12, y - 50,
                 f"Confidence {conf*100:.0f}%   ·   EQ identity: {EQ_IDENTITY_LABEL.get(eq_id, '-')}")

    desc = (audit.get("archetype_description") or "").strip()
    if desc:
        _wrapped(c, desc, margin + 12, y - 64, max_chars=110, size=9, leading=11,
                 colour=(1, 1, 1))
    y -= panel_h + 14

    # Method note
    c.setFillColorRGB(0.50, 0.50, 0.55)
    c.setFont("Helvetica-Oblique", 8)
    method = (
        "Scores are normalised to 0-100. Band thresholds: Elite 85+, "
        "Performing 65-84, Practising 40-64, Developing under 40. "
        "Archetype is derived from the two highest traits, with all-high "
        "and all-low special cases."
    )
    _wrapped(c, method, margin, y, max_chars=110, size=8, leading=10,
             colour=(0.50, 0.50, 0.55))

    footer(1)
    c.showPage()

    # ===== Page 2 — EQ identity + per-trait narrative =====
    y = H - margin
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Your EQ signature")
    y -= 18

    if eq_id:
        eq_narrative = ctx["narratives_by"].get(("eq_identity", eq_id))
        c.setFillColorRGB(0.10, 0.34, 0.78)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, EQ_IDENTITY_LABEL.get(eq_id, eq_id))
        y -= 14
        if eq_narrative:
            y = _wrapped(c, eq_narrative["strength"], margin, y, max_chars=110, size=9, leading=11)
            y -= 4
            c.setFillColorRGB(0.10, 0.34, 0.78)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(margin, y, "Action")
            y -= 12
            y = _wrapped(c, eq_narrative["action"], margin, y, max_chars=110, size=9, leading=11,
                         colour=(0.10, 0.34, 0.78))
        y -= 6
        c.setStrokeColorRGB(0.90, 0.90, 0.92)
        c.line(margin, y, W - margin, y)
        y -= 14

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Where you stand, trait by trait")
    y -= 22

    for dim in DIM_ORDER:
        band = ctx["bands_by_dim"].get(dim, {}).get("band")
        score_100 = (audit.get(dim) or 0.0) * 100.0
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, f"{DIM_LABEL[dim]}   {score_100:.1f}/100")
        _draw_band_pill(c, W - margin - 70, y - 2, band or "-", w=64, h=12)
        y -= 14

        n = ctx["narratives_by"].get((dim, band)) if band else None
        if n:
            c.setFillColorRGB(0.45, 0.45, 0.50)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(margin, y, "What this means")
            y -= 12
            y = _wrapped(c, n["strength"], margin, y, max_chars=110, size=9, leading=11)
            y -= 4
            c.setFillColorRGB(0.10, 0.34, 0.78)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(margin, y, "Action")
            y -= 12
            y = _wrapped(c, n["action"], margin, y, max_chars=110, size=9, leading=11,
                         colour=(0.10, 0.34, 0.78))
        else:
            c.setFillColorRGB(0.55, 0.55, 0.60)
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(margin, y, "(narrative pending)")
            y -= 12

        y -= 8
        c.setStrokeColorRGB(0.90, 0.90, 0.92)
        c.line(margin, y, W - margin, y)
        y -= 10

    footer(2)
    c.showPage()

    # ===== Page 3 — coaching priorities + audit history =====
    y = H - margin
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Coaching priorities")
    y -= 22

    # Rank traits ascending — weakest first is the coaching priority
    ranked = sorted(
        DIM_ORDER,
        key=lambda d: (audit.get(d) or 0.0),
    )
    c.setFillColorRGB(0.45, 0.45, 0.50)
    c.setFont("Helvetica", 9)
    c.drawString(margin, y,
                 "Address from weakest to strongest. Each 5-point lift compounds "
                 "across the funnel.")
    y -= 18

    for rank, dim in enumerate(ranked, 1):
        score_100 = (audit.get(dim) or 0.0) * 100.0
        band = ctx["bands_by_dim"].get(dim, {}).get("band") or "-"
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin, y, f"{rank}.  {DIM_LABEL[dim]}")
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.45, 0.45, 0.50)
        c.drawString(margin + 200, y, f"{score_100:.1f}/100 · {band}")
        y -= 14
        n = ctx["narratives_by"].get((dim, band))
        if n:
            y = _wrapped(c, n["action"], margin + 14, y, max_chars=104, size=9, leading=11)
        y -= 8

    y -= 6
    c.setStrokeColorRGB(0.85, 0.85, 0.87)
    c.line(margin, y, W - margin, y)
    y -= 14

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Audit history")
    y -= 16

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
    c.setFillColorRGB(0.45, 0.45, 0.50)
    c.setFont("Helvetica", 9)
    c.drawString(margin, y, "Date              Status     CE     EQ     PC     NP")
    y -= 12
    c.setFillColorRGB(0, 0, 0)
    for h in history:
        date = h["started_at"].strftime("%Y-%m-%d")
        ce = f"{(h['cognitive_empathy'] or 0)*100:5.1f}" if h["cognitive_empathy"] is not None else "  -  "
        eq = f"{(h['eq'] or 0)*100:5.1f}"               if h["eq"] is not None else "  -  "
        pc = f"{(h['pressure_composure'] or 0)*100:5.1f}" if h["pressure_composure"] is not None else "  -  "
        st = f"{(h['storytelling'] or 0)*100:5.1f}"     if h["storytelling"] is not None else "  -  "
        c.setFont("Helvetica", 9)
        c.drawString(margin, y, f"{date}        {h['status']:<10} {ce}  {eq}  {pc}  {st}")
        y -= 12

    footer(3)
    c.showPage()
    c.save()

    pdf_bytes = buf.getvalue()
    # filename + persist
    fname = f"respondent_{r['respondent_id']}_audit_{audit_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
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
