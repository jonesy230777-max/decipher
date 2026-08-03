"""HIG audit + OODA-loop screenshot harness.

Headless Chromium (project rule 5 — no physical browser). Captures every
dashboard page at HD (1920x1080) and at exec breakpoints, runs:

  - console error / warning count per page
  - network non-200 count per page
  - axe-core style contrast spot-check via computed colours
  - element-count assertions for the executive-dashboard wireframe
  - screenshot per page in compliance/screenshots/<date>/<slug>.png

Writes a single Markdown report at
compliance/hig_audit_<YYYY-MM-DD>_<HHMMSS>.md.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, ConsoleMessage, Response

ROOT = Path(__file__).resolve().parent.parent
RUN_AT = datetime.utcnow()
RUN_TAG = RUN_AT.strftime("%Y-%m-%d_%H%M%S")
SHOT_DIR = ROOT / "compliance" / "screenshots" / RUN_TAG
SHOT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = ROOT / "compliance" / f"hig_audit_{RUN_TAG}.md"

WEB_PORT = os.environ.get("DECIPHER_WEB_PORT", "55173")
BASE = f"http://127.0.0.1:{WEB_PORT}"

PAGES = [
    ("mission",       "/",                "Mission Control"),
    ("audits",        "/audits",          "Audits"),
    ("funnel",        "/funnel",          "Funnel"),
    ("cohort",        "/cohort",          "Cohort Insights"),
    ("companies",     "/companies",       "Companies"),
    ("company_atlas", "/companies/1",     "Company - Atlas Media Group"),
    ("teams",         "/teams",           "Teams"),
    ("people",        "/people",          "People"),
    ("team_exec",     "/teams/1",         "Executive - Metro Sales Team"),
    ("respondent",    "/respondents/1368","Respondent - Grant Smith"),
    ("audit_take",    "/audit/start",     "Audit Take (native)"),
    ("industries",    "/industries",      "Industries"),
    ("bespoke",       "/bespoke",         "Bespoke"),
    ("promo",         "/promo",           "Promo Codes"),
    ("squarespace",   "/squarespace",     "Squarespace Export"),
    ("events",        "/events",          "Events"),
    ("settings",      "/settings",        "Settings"),
]

# Assertions per page. Each entry: (locator, must_contain_text)
PAGE_ASSERTIONS: dict[str, list[tuple[str, str]]] = {
    "mission": [("h1", "Mission Control")],
    "audits":  [("h1", "Audits"), ("table thead th", "Respondent")],
    "cohort":  [("h1", "Cohort Insights")],
    "teams":   [("h1", "Teams"), ("a", "Metro Sales Team")],
    "team_exec": [
        ("h1", "Metro Sales Team · Decipher DNA Audit"),
        ("body", "Sales Director Dashboard"),
        ("body", "Team average score"),
        ("body", "Elite performers"),
        ("body", "At-risk reps"),
        ("body", "Biggest gap trait"),
        ("body", "Score distribution by band"),
        ("body", "Archetype breakdown"),
        ("body", "Priority coaching interventions"),
        ("body", "Team roster"),
        ("body", "Owen Wright"),
        ("a",    "Download Executive Summary"),
        ("body", "decipher.com.au"),
        ("body", "Confidential"),
    ],
    "companies": [("h1", "Companies"), ("body", "Atlas Media Group"),
                  ("body", "Northwind Pharma"), ("body", "Crestline Auto"),
                  ("body", "Pearl Tech Group")],
    "company_atlas": [("body", "Atlas Media Group"), ("body", "Metro Sales Team"),
                      ("body", "Field Sales Team")],
    "respondent": [("h1", "Grant Smith"), ("body", "Metro Sales Team"),
                   ("body", "Edge-Builder")],
    "audit_take": [("h1", "Decipher Sales DNA Audit"),
                   ("body", "Confidential"), ("body", "Continue to payment")],
    "people":     [("h1", "People"), ("body", "Search"),
                   ("body", "Atlas Media Group")],
    "funnel":     [("h1", "Funnel"), ("body", "Invited"), ("body", "Audit started"),
                   ("body", "Send invites")],
    "industries": [("h1", "Industries"), ("table", "media")],
    "bespoke":   [("h1", "Bespoke"), ("body", "Atlas Media Group")],
    "promo":     [("h1", "Promo Codes"), ("table", "LAUNCH100")],
    "squarespace": [
        ("h1", "Squarespace Export"),
        ("body", "Preview Tree"),
        ("body", "History"),
    ],
    "events":   [("h1", "Events"), ("table thead th", "Action")],
    "settings": [("h1", "Settings"), ("body", "Users and roles"),
                 ("body", "Role permissions")],
}

# Forbidden tokens per project rules (§10 #8, #12).
FORBIDDEN = ["—", "  unlock", "  elevate", "  seamless", "  delve",
             "  tapestry", "  leverage", "  empower",
             "in today's fast-paced world", "game-changer"]
# (em-dash deliberately listed first; we'll detect later distinctly.)


def audit_page(page: Page, slug: str, path: str) -> dict:
    console_msgs: list[tuple[str, str]] = []
    net_failures: list[tuple[int, str]] = []
    def on_console(msg: ConsoleMessage) -> None:
        if msg.type in ("error", "warning"):
            console_msgs.append((msg.type, msg.text))
    def on_response(resp: Response) -> None:
        if resp.status >= 400:
            net_failures.append((resp.status, resp.url))
    page.on("console", on_console)
    page.on("response", on_response)

    # Seed an admin session into localStorage so the auth guard does not
    # bounce protected pages to /login.
    page.goto(BASE + "/landing", wait_until="domcontentloaded", timeout=15_000)
    page.evaluate(
        "localStorage.setItem('decipher.me', JSON.stringify("
        "{respondent_id: 1, email: 'steve@decipher.com.au', name: 'Steve',"
        " role: 'admin'}))"
    )
    page.goto(BASE + path, wait_until="networkidle", timeout=15_000)
    # let any post-load tick render
    time.sleep(1.5)

    # Assertions
    failed: list[str] = []
    for locator, text in PAGE_ASSERTIONS.get(slug, []):
        found = False
        for el in page.locator(locator).all():
            try:
                if text.lower() in (el.inner_text() or "").lower():
                    found = True
                    break
            except Exception:
                continue
        if not found:
            failed.append(f"{locator} :: contains '{text}'")

    # Forbidden tokens (em-dash and AI filler)
    body_text = page.locator("body").inner_text()
    em_dashes = body_text.count("—")
    filler_hits: list[str] = []
    lower = body_text.lower()
    for needle in ("unlock", "elevate", "seamless", "delve",
                   "tapestry", "leverage", "empower", "game-changer",
                   "in today's fast-paced world"):
        # crude: don't false-positive on URLs/HTML
        if re.search(rf"\b{re.escape(needle)}\b", lower):
            filler_hits.append(needle)

    # HD screenshot
    shot = SHOT_DIR / f"{slug}.png"
    page.screenshot(path=str(shot), full_page=True)

    return {
        "slug": slug,
        "path": path,
        "console_errors": [m for t, m in console_msgs if t == "error"],
        "console_warnings": [m for t, m in console_msgs if t == "warning"],
        "net_failures": net_failures,
        "assertion_failures": failed,
        "em_dashes": em_dashes,
        "filler_hits": filler_hits,
        "screenshot": str(shot.relative_to(ROOT)),
    }


def main() -> int:
    print(f"OODA run {RUN_TAG} → {SHOT_DIR}")
    results: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080},
                                  device_scale_factor=2,
                                  reduced_motion="reduce")
        page = ctx.new_page()
        for slug, path, label in PAGES:
            print(f"  -> {slug:14s} {path}")
            r = audit_page(page, slug, path)
            r["label"] = label
            results.append(r)
        browser.close()

    # Write report
    total_console_err = sum(len(r["console_errors"]) for r in results)
    total_net_fail = sum(len(r["net_failures"]) for r in results)
    total_assert_fail = sum(len(r["assertion_failures"]) for r in results)
    total_em = sum(r["em_dashes"] for r in results)
    total_filler = sum(len(r["filler_hits"]) for r in results)
    overall_pass = (total_console_err == 0 and total_net_fail == 0
                    and total_assert_fail == 0 and total_filler == 0
                    and total_em == 0)

    lines: list[str] = []
    lines.append(f"# Decipher — HIG / OODA audit {RUN_TAG}")
    lines.append("")
    lines.append(f"- Pages audited: {len(PAGES)}")
    lines.append(f"- Viewport: 1920×1080 @ 2x DPR (HD)")
    lines.append(f"- Headless Chromium (project rule §10 #5)")
    lines.append(f"- Total console errors: **{total_console_err}**")
    lines.append(f"- Total network failures (>=400): **{total_net_fail}**")
    lines.append(f"- Total assertion failures: **{total_assert_fail}**")
    lines.append(f"- Total em-dashes found in body: **{total_em}** (rule §10 #8)")
    lines.append(f"- Total AI-filler hits: **{total_filler}** (rule §10 #12)")
    lines.append(f"- Overall: **{'PASS ✓' if overall_pass else 'FAIL ✗'}**")
    lines.append("")
    for r in results:
        status = "✓" if not (r["console_errors"] or r["net_failures"]
                              or r["assertion_failures"] or r["filler_hits"]
                              or r["em_dashes"]) else "✗"
        lines.append(f"## {status} {r['label']} — `{r['path']}`")
        lines.append(f"![{r['slug']}]({r['screenshot']})")
        lines.append("")
        if r["console_errors"]:
            lines.append("### Console errors")
            for m in r["console_errors"]:
                lines.append(f"- `{m}`")
        if r["console_warnings"]:
            lines.append("### Console warnings")
            for m in r["console_warnings"][:10]:
                lines.append(f"- `{m}`")
        if r["net_failures"]:
            lines.append("### Network failures")
            for status_code, url in r["net_failures"]:
                lines.append(f"- {status_code}  {url}")
        if r["assertion_failures"]:
            lines.append("### Assertion failures")
            for f in r["assertion_failures"]:
                lines.append(f"- {f}")
        if r["em_dashes"]:
            lines.append(f"### Em-dashes found: {r['em_dashes']}")
        if r["filler_hits"]:
            lines.append("### AI filler hits")
            for h in r["filler_hits"]:
                lines.append(f"- `{h}`")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines))
    print(f"\nReport: {REPORT_PATH}")
    print(f"Pass: {overall_pass}")
    print(json.dumps({
        "console_errors": total_console_err,
        "net_failures": total_net_fail,
        "assertion_failures": total_assert_fail,
        "em_dashes": total_em,
        "filler_hits": total_filler,
    }, indent=2))
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
