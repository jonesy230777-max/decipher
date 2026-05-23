"""M10 Squarespace bundle assembler.

Public entry point:
    generate_bundle(export_id) -- generate full zip, update DB row, return stats dict
"""
from __future__ import annotations

import io
import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from app.db import conn, event, rows, scalar

log = logging.getLogger(__name__)

HAIKU = "claude-haiku-4-5-20251001"

_COST_PER_M = {"input": 1.00, "output": 5.00}

_EXPORT_DIR = Path(os.getenv(
    "SQUARESPACE_EXPORT_DIR",
    str(Path(__file__).parent.parent / "_squarespace_exports"),
))


# ---------------------------------------------------------------------------
# Claude call helpers
# ---------------------------------------------------------------------------

def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _haiku_structured(prompt: str, schema: dict[str, Any], max_tokens: int = 6000) -> dict[str, Any]:
    cl = _client()
    resp = cl.messages.create(
        model=HAIKU,
        max_tokens=max_tokens,
        tools=[{
            "name": "bundle_content",
            "description": "Return structured Squarespace bundle content.",
            "input_schema": schema,
        }],
        tool_choice={"type": "tool", "name": "bundle_content"},
        messages=[{"role": "user", "content": prompt}],
    )
    input_tok  = resp.usage.input_tokens
    output_tok = resp.usage.output_tokens
    cost = (input_tok * _COST_PER_M["input"] + output_tok * _COST_PER_M["output"]) / 1_000_000
    event("claude_api_call", actor="system", payload={
        "model": HAIKU,
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "cost_usd": round(cost, 6),
        "context": "squarespace_export",
    })
    for block in resp.content:
        if block.type == "tool_use" and block.name == "bundle_content":
            return block.input  # type: ignore[return-value]
    raise RuntimeError("No bundle_content tool call in Haiku response")


# ---------------------------------------------------------------------------
# Content generation schemas
# ---------------------------------------------------------------------------

_PAGES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "home":                {"type": "string"},
        "dna_audit":           {"type": "string"},
        "training":            {"type": "string"},
        "consulting":          {"type": "string"},
        "industries_media":    {"type": "string"},
        "industries_pharma":   {"type": "string"},
        "industries_automotive": {"type": "string"},
        "industries_tech":     {"type": "string"},
        "bespoke":             {"type": "string"},
        "about":               {"type": "string"},
        "contact":             {"type": "string"},
        "seo_meta": {
            "type": "object",
            "description": "SEO meta per page slug: title (60 chars), description (155 chars), keywords",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "title":       {"type": "string"},
                    "description": {"type": "string"},
                    "keywords":    {"type": "string"},
                },
                "required": ["title", "description", "keywords"],
            },
        },
    },
    "required": ["home", "dna_audit", "training", "consulting",
                 "industries_media", "industries_pharma", "industries_automotive",
                 "industries_tech", "bespoke", "about", "contact", "seo_meta"],
}

_PRODUCT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "audit_intro":         {"type": "string"},
        "audit_post_payment":  {"type": "string"},
        "dimension_intros":    {"type": "string"},
        "audit_progress":      {"type": "string"},
        "audit_completion":    {"type": "string"},
        "email_receipt":       {"type": "string"},
        "email_report_delivery": {"type": "string"},
        "email_nudge_day7":    {"type": "string"},
        "email_reaudit_day90": {"type": "string"},
        "pdf_cover":           {"type": "string"},
        "pdf_dimension_explainers": {"type": "string"},
        "pdf_archetype_profiles": {"type": "string"},
        "pdf_band_descriptors": {"type": "string"},
        "pdf_closing":         {"type": "string"},
    },
    "required": [
        "audit_intro", "audit_post_payment", "dimension_intros",
        "audit_progress", "audit_completion",
        "email_receipt", "email_report_delivery", "email_nudge_day7", "email_reaudit_day90",
        "pdf_cover", "pdf_dimension_explainers", "pdf_archetype_profiles",
        "pdf_band_descriptors", "pdf_closing",
    ],
}


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _pages_prompt(voice: str, n_audits: int, industries: list[str]) -> str:
    return f"""You are writing Squarespace page copy for Decipher, a sales-intelligence platform.
Decipher diagnoses sales professionals across four dimensions: Cognitive Empathy, EQ, Pressure Composure, and Storytelling.

BRAND VOICE (follow this exactly):
{voice}

LIVE CONTEXT:
- {n_audits} sales professionals have completed the DNA Audit
- Industries served: {", ".join(industries) if industries else "Media Sales, Pharma, Automotive, Technology"}

TASK: Write Squarespace page copy (markdown) for each page listed below.
Each page: 120-180 words. Plain Australian English. No em dashes. No AI filler words.
The DNA Audit costs AUD $497 (one-time). The Trojan horse is the audit; the real value is in consulting and training.

Pages to write:
- home: main value proposition and CTA
- dna_audit: what the audit is, the four dimensions, the archetype output, the PDF report
- training: group training programmes based on dimension gaps
- consulting: bespoke consulting engagements, team diagnostics
- industries_media: media sales specific framing
- industries_pharma: pharma rep specific framing
- industries_automotive: automotive dealer/fleet specific framing
- industries_tech: tech/SaaS sales specific framing
- bespoke: custom audit engagements for enterprise clients
- about: Steve's background and Decipher's origin story (diagnose before prescribe)
- contact: contact page copy

Also generate seo_meta for each page slug (home, dna_audit, training, consulting, bespoke, about, contact,
industries_media, industries_pharma, industries_automotive, industries_tech).
"""


def _product_prompt(voice: str) -> str:
    return f"""You are writing product copy for Decipher, a sales-intelligence platform.

BRAND VOICE (follow this exactly):
{voice}

The four dimensions are: Cognitive Empathy, EQ, Pressure Composure, Storytelling.
There are four bands: Developing, Practising, Performing, Elite.
The audit is 47 questions. It costs AUD $497.

TASK: Write copy (markdown) for these product surfaces. 80-120 words each. Plain Australian English. No em dashes.

- audit_intro: intro screen before the respondent starts the audit
- audit_post_payment: confirmation screen shown after payment, before the audit starts
- dimension_intros: brief intro text shown before each of the four dimension sections
- audit_progress: progress encouragement copy shown mid-audit
- audit_completion: screen shown when the audit is submitted, before the report is ready
- email_receipt: payment receipt email body (include placeholder for amount/name)
- email_report_delivery: email body delivering the PDF report link
- email_nudge_day7: 7-day follow-up nudge email (have they read the report?)
- email_reaudit_day90: 90-day re-audit reminder email
- pdf_cover: cover page descriptor text (below the respondent's name and archetype)
- pdf_dimension_explainers: one paragraph explaining what each dimension measures
- pdf_archetype_profiles: brief description of the archetype classification system
- pdf_band_descriptors: what each band (Developing/Practising/Performing/Elite) means
- pdf_closing: closing page of the PDF report with next steps
"""


# ---------------------------------------------------------------------------
# Programmatic file generators
# ---------------------------------------------------------------------------

def _design_tokens() -> str:
    tokens = {
        "colour": {
            "accent":                "#007AFF",
            "accent_tint_bg":        "rgba(0,122,255,0.08)",
            "label":                 "#1C1C1E",
            "label_secondary":       "rgba(60,60,67,0.60)",
            "label_tertiary":        "rgba(60,60,67,0.30)",
            "bg_system":             "#FFFFFF",
            "bg_system_secondary":   "#F2F2F7",
            "separator":             "rgba(60,60,67,0.12)",
            "separator_opaque":      "#C6C6C8",
            "system_green":          "#34C759",
            "system_red":            "#FF3B30",
            "system_orange":         "#FF9500",
            "system_yellow":         "#FFCC00",
        },
        "radius": {
            "sm": "6px", "md": "10px", "lg": "14px", "xl": "20px",
        },
        "space": {
            "1": "4px", "2": "8px", "3": "12px", "4": "16px",
            "5": "24px", "6": "32px", "7": "48px", "8": "64px",
        },
        "type": {
            "large_title": "34px", "title_1": "28px", "title_2": "22px",
            "title_3": "20px", "headline": "17px", "body": "17px",
            "callout": "16px", "subheadline": "15px", "footnote": "13px",
            "caption_1": "12px", "caption_2": "11px",
        },
    }
    return json.dumps(tokens, indent=2)


def _hig_notes() -> str:
    return """# HIG Design Notes — Decipher Squarespace Bundle

## Typography
- Large Title (34pt) for page heroes.
- Title 1 (28pt) for section headers.
- Body (17pt, regular) for all paragraph text.
- Footnote (13pt) for metadata and secondary info.
- All weights: use system font stack (SF Pro on Apple, system-ui elsewhere).

## Colour
- Accent blue #007AFF for primary CTAs only.
- Never use raw black — use label colour (semantic).
- System red/green/orange for status indicators only.

## Spacing
- 8pt grid throughout. Minimum touch target 44pt.
- Section padding: 64px top/bottom on desktop, 32px mobile.

## No em dashes. No bold headers with ":" colons decoratively.
## Australian English spelling throughout.
"""


def _images_brief() -> str:
    return """# Image Brief — Decipher Squarespace Bundle

## Style
- Photography: candid, meeting-room, authentic. No posed stock-photo smiles.
- Colour grading: desaturated, cool-blue tones consistent with brand palette.
- No AI-generated faces.

## Per-page requirements
- **home**: Hero — two professionals in conversation, one listening intently.
- **dna_audit**: Graphic showing the four radar dimensions (Cognitive Empathy, EQ, Pressure Composure, Storytelling).
- **training**: Small-group workshop setting.
- **consulting**: One-to-one whiteboard session.
- **industries/***: Context-appropriate: GP consultation (pharma), showroom (automotive), broadcast studio (media), laptop/SaaS (tech).
- **about**: Headshot of Steve Jones, informal office backdrop.
- **bespoke**: Enterprise boardroom, overhead whiteboard shot.
"""


def _readme(export_id: int, generated_at: datetime, n_files: int) -> str:
    return f"""# Decipher Squarespace Bundle

Export ID: {export_id}
Generated: {generated_at.strftime('%Y-%m-%d %H:%M UTC')}
Files: {n_files}

## Structure

```
pages/            Squarespace page copy (markdown)
pages/industries/ Industry-specific page copy
seo/              SEO meta tags (JSON)
design/           Design tokens and HIG notes
audit_app/        In-platform copy (intro, completion, progress)
audit_app/emails/ Transactional email templates
pdf_report/       PDF report section copy and descriptors
voice/            Brand voice reference
README.md         This file
```

## How to use

1. Upload each `pages/*.md` file to the corresponding Squarespace page via the Rich Text editor.
2. Apply `design/tokens.json` values to the Squarespace Style Editor.
3. Use `seo/meta.json` for SEO settings in Squarespace > Pages > Settings > SEO.
4. The `audit_app/` and `pdf_report/` files are for developer reference only.

## Brand voice

Always refer to `voice/brand_voice.md` before writing any copy.
Diagnose before prescribe.
"""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_bundle(export_id: int) -> dict[str, Any]:
    """Generate the full Squarespace bundle, write zip to disk, update DB row."""
    _EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Pull live context from DB
    voice_row = scalar("SELECT voice_md FROM brand_voice WHERE id = 1") or ""
    n_audits  = scalar("SELECT count(*) FROM audits WHERE status IN ('scored','reported')") or 0
    ind_rows  = rows("SELECT name FROM industries ORDER BY name")
    industries = [r["name"] for r in ind_rows]

    log.info("squarespace: generating bundle %d (%d audits, %d industries)", export_id, n_audits, len(industries))

    # Two Claude Haiku calls
    pages_data   = _haiku_structured(_pages_prompt(voice_row, n_audits, industries), _PAGES_SCHEMA, max_tokens=7000)
    product_data = _haiku_structured(_product_prompt(voice_row), _PRODUCT_SCHEMA, max_tokens=5000)

    # Assemble files dict: path -> content
    now = datetime.now(timezone.utc)
    files: dict[str, str] = {}

    # Pages
    page_map = {
        "pages/home.md":                  pages_data.get("home", ""),
        "pages/dna_audit.md":             pages_data.get("dna_audit", ""),
        "pages/training.md":              pages_data.get("training", ""),
        "pages/consulting.md":            pages_data.get("consulting", ""),
        "pages/industries/media.md":      pages_data.get("industries_media", ""),
        "pages/industries/pharma.md":     pages_data.get("industries_pharma", ""),
        "pages/industries/automotive.md": pages_data.get("industries_automotive", ""),
        "pages/industries/tech.md":       pages_data.get("industries_tech", ""),
        "pages/bespoke.md":               pages_data.get("bespoke", ""),
        "pages/about.md":                 pages_data.get("about", ""),
        "pages/contact.md":               pages_data.get("contact", ""),
    }
    files.update(page_map)

    # SEO meta
    seo_meta = pages_data.get("seo_meta", {})
    files["seo/meta.json"] = json.dumps(seo_meta, indent=2)

    # Design
    files["design/tokens.json"]    = _design_tokens()
    files["design/hig_notes.md"]   = _hig_notes()
    files["design/images_brief.md"] = _images_brief()

    # Audit app
    files["audit_app/intro.md"]            = product_data.get("audit_intro", "")
    files["audit_app/post_payment.md"]     = product_data.get("audit_post_payment", "")
    files["audit_app/dimension_intros.md"] = product_data.get("dimension_intros", "")
    files["audit_app/progress.md"]         = product_data.get("audit_progress", "")
    files["audit_app/completion.md"]       = product_data.get("audit_completion", "")

    # Emails
    files["audit_app/emails/receipt.md"]        = product_data.get("email_receipt", "")
    files["audit_app/emails/report_delivery.md"] = product_data.get("email_report_delivery", "")
    files["audit_app/emails/nudge_day7.md"]     = product_data.get("email_nudge_day7", "")
    files["audit_app/emails/reaudit_day90.md"]  = product_data.get("email_reaudit_day90", "")

    # PDF report
    files["pdf_report/cover.md"]                = product_data.get("pdf_cover", "")
    files["pdf_report/dimension_explainers.md"] = product_data.get("pdf_dimension_explainers", "")
    files["pdf_report/archetype_profiles.md"]   = product_data.get("pdf_archetype_profiles", "")
    files["pdf_report/band_descriptors.md"]     = product_data.get("pdf_band_descriptors", "")
    files["pdf_report/closing.md"]              = product_data.get("pdf_closing", "")

    # Voice + README
    files["voice/brand_voice.md"] = voice_row
    files["README.md"]            = _readme(export_id, now, len(files) + 1)

    # Build zip
    bundle_path = _EXPORT_DIR / f"squarespace_export_{export_id}_{now.strftime('%Y-%m-%d_%H%M%S')}.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    zip_bytes = buf.getvalue()
    bundle_path.write_bytes(zip_bytes)

    file_count  = len(files)
    size_bytes  = len(zip_bytes)

    # Pull total cost from events_log (the two haiku calls above logged themselves)
    cost_rows = rows(
        """SELECT COALESCE(SUM((payload->>'cost_usd')::float), 0) AS total
             FROM events_log
            WHERE action = 'claude_api_call'
              AND payload->>'context' = 'squarespace_export'
              AND occurred_at >= now() - interval '5 minutes'"""
    )
    cost_usd = round(float(cost_rows[0]["total"]) if cost_rows else 0.0, 4)

    summary = (
        f"Export {now.strftime('%Y-%m-%d %H:%M')}: "
        f"{file_count} files -- pages + seo + design + audit_app + pdf_report + voice"
    )

    # Update the DB row
    with conn() as c, c.cursor() as cur:
        cur.execute(
            """UPDATE squarespace_exports
                  SET bundle_path = %s,
                      file_count  = %s,
                      size_bytes  = %s,
                      summary     = %s,
                      cost_usd    = %s
                WHERE export_id = %s""",
            (str(bundle_path), file_count, size_bytes, summary, cost_usd, export_id),
        )

    event("squarespace.bundle_generated", payload={
        "export_id": export_id,
        "file_count": file_count,
        "size_bytes": size_bytes,
        "cost_usd": cost_usd,
    })
    log.info("squarespace bundle %d done: %d files, %d bytes", export_id, file_count, size_bytes)
    return {
        "export_id":  export_id,
        "file_count": file_count,
        "size_bytes": size_bytes,
        "cost_usd":   cost_usd,
        "summary":    summary,
        "bundle_path": str(bundle_path),
    }
