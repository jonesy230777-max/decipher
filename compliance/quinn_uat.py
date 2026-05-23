"""S091: Quinn vision-model UAT pass.

Sends each screenshot from the most recent HIG audit run to Claude Haiku
(vision) and asks it to flag any visual regressions, HIG violations, or
usability issues. Appends a UAT section to the most recent audit report.

Usage:
    python3 compliance/quinn_uat.py
    python3 compliance/quinn_uat.py compliance/screenshots/2026-05-23_081810/

Quinn checks for:
- Broken/missing layout (blank sections, overflow, cut-off content)
- Typography violations (wrong weights, sizes, colours)
- Colour system violations (wrong accent use, low contrast)
- Em-dashes in rendered text
- Placeholder / lorem ipsum / DUMMY content visible to user
- Missing key UI elements (headers, data, buttons)
"""
from __future__ import annotations

import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent.parent

QUINN_SYSTEM = """\
You are Quinn, a visual QA specialist for the Decipher sales-intelligence dashboard.

Your job is to review a screenshot of a dashboard page and flag any issues.

Check for:
1. Blank or broken sections (missing data, spinners stuck, grey boxes where content should be)
2. Typography problems (inconsistent weights, sizes that look wrong)
3. Colour issues (low contrast, wrong colour usage, unstyled text)
4. Em-dashes (the — character) in any visible text
5. AI filler words in visible text: unlock, elevate, seamless, delve, tapestry, leverage, empower
6. Placeholder text: "DUMMY", "lorem ipsum", "placeholder", "TODO", "coming soon"
7. Missing critical UI elements that should appear on this page
8. Overflow or truncation that hides important content
9. Layout broken at 1920px wide

Respond in this JSON schema only, no extra text:
{
  "issues": [
    {"severity": "error|warning|info", "description": "..."}
  ],
  "overall": "pass|warn|fail",
  "summary": "one sentence"
}

If there are no issues, return {"issues": [], "overall": "pass", "summary": "Page looks correct."}.
"""

_PAGE_CONTEXT = {
    "mission":       "Mission Control dashboard: shows KPI strip (audits, respondents, reports, events), search bar, 14-day sparklines for each metric.",
    "audits":        "Audits list: sortable table of audit records with respondent name, status, scores, and date.",
    "funnel":        "Funnel page: stage counts (Invited, Started, Completed, Scored, Reported) with 14-day trend bars.",
    "cohort":        "Cohort Insights: band distribution chart, pattern library table with DOUBT-passed patterns.",
    "companies":     "Companies list: table of company names, industry, team count, respondent count.",
    "company_atlas": "Company detail: Atlas Media Group with team list and respondent breakdown.",
    "teams":         "Teams list: table of sales teams with aggregate scores.",
    "people":        "People list: searchable table of respondents.",
    "team_exec":     "Executive dashboard: Sales Director view with team averages, elite count, at-risk count, interventions, roster.",
    "respondent":    "Respondent detail: Grant Smith profile with scores, bands, archetype, audit history.",
    "audit_take":    "Audit intake page: start screen for media sales DNA audit, shows first name field and payment CTA.",
    "industries":    "Industries admin table: list of industry codes, names, audit version assignments.",
    "bespoke":       "Bespoke clients page: list of custom audit engagements with pipeline value.",
    "promo":         "Promo Codes page: table of promo codes with discount, uses, expiry.",
    "squarespace":   "Squarespace Export page: file tree preview, history list, Download Bundle button.",
    "events":        "Events log: sortable table of system events with action, actor, severity, timestamp.",
    "settings":      "Settings page: role permissions matrix, user list.",
}


def _encode_image(path: Path) -> str:
    return base64.standard_b64encode(path.read_bytes()).decode()


def _quinn_review(client: anthropic.Anthropic, slug: str, img_path: Path) -> dict:
    context = _PAGE_CONTEXT.get(slug, f"Page: {slug}")
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=QUINN_SYSTEM,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Page context: {context}\n\nReview this screenshot:",
                },
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": _encode_image(img_path),
                    },
                },
            ],
        }],
    )
    raw = resp.content[0].text.strip()
    # Strip markdown code fences if Claude wrapped it
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"issues": [{"severity": "error", "description": f"Quinn parse error: {raw[:200]}"}],
                "overall": "warn", "summary": "Could not parse Quinn response."}


def run_quinn(screenshot_dir: Path | None = None) -> Path:
    # Find most recent screenshot directory if not specified
    if screenshot_dir is None:
        shot_dirs = sorted((ROOT / "compliance" / "screenshots").iterdir())
        if not shot_dirs:
            raise FileNotFoundError("No screenshot directories found under compliance/screenshots/")
        screenshot_dir = shot_dirs[-1]

    run_tag = screenshot_dir.name
    # Find matching audit report
    report_path = ROOT / "compliance" / f"hig_audit_{run_tag}.md"

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    shots = sorted(screenshot_dir.glob("*.png"))
    print(f"Quinn UAT: {len(shots)} screenshots from {run_tag}")

    results: list[dict] = []
    total_cost = 0.0
    for shot in shots:
        slug = shot.stem
        print(f"  -> {slug:14s}", end=" ", flush=True)
        r = _quinn_review(client, slug, shot)
        r["slug"] = slug
        r["screenshot"] = str(shot.relative_to(ROOT))
        results.append(r)
        # Approximate cost: haiku vision ~$0.001 per screenshot
        total_cost += 0.0008
        print(r["overall"])

    # Tally
    errors   = sum(1 for r in results if r["overall"] == "fail")
    warnings = sum(1 for r in results if r["overall"] == "warn")
    passes   = sum(1 for r in results if r["overall"] == "pass")
    issue_count = sum(len(r.get("issues", [])) for r in results)
    overall = "PASS ✓" if errors == 0 and warnings == 0 else ("FAIL ✗" if errors > 0 else "WARN ⚠")

    # Build Quinn section markdown
    lines: list[str] = [
        "",
        "---",
        "",
        f"## Quinn Vision UAT — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"- Screenshsots reviewed: {len(shots)}",
        f"- Pass: **{passes}** · Warn: **{warnings}** · Fail: **{errors}**",
        f"- Total issues flagged: **{issue_count}**",
        f"- Estimated Claude cost: USD ${total_cost:.4f}",
        f"- Quinn overall: **{overall}**",
        "",
    ]
    for r in results:
        icon = {"pass": "✓", "warn": "⚠", "fail": "✗"}.get(r["overall"], "?")
        lines.append(f"### {icon} {r['slug']} — {r.get('summary', '')}")
        if r.get("issues"):
            for issue in r["issues"]:
                sev = issue.get("severity", "info")
                lines.append(f"- **{sev}**: {issue.get('description', '')}")
        lines.append("")

    # Append to existing audit report if it exists, otherwise create standalone
    quinn_section = "\n".join(lines)
    if report_path.exists():
        with open(report_path, "a") as f:
            f.write(quinn_section)
        print(f"\nAppended Quinn UAT to: {report_path}")
    else:
        standalone = ROOT / "compliance" / f"quinn_uat_{run_tag}.md"
        standalone.write_text(f"# Quinn UAT — {run_tag}\n{quinn_section}")
        print(f"\nWrote standalone report: {standalone}")
        report_path = standalone

    print(f"Quinn overall: {overall}")
    return report_path


if __name__ == "__main__":
    shot_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    run_quinn(shot_dir)
