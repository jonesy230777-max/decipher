"""Headless Chromium fetch of Apple HIG pages to local text mirror.

Per spec §9 and rule 9: we must read the live HIG, not guess.
Pages are JS-rendered, so we render then dump inner_text.

Mirrors land at compliance/hig_mirror/<slug>.txt.
"""
from __future__ import annotations

from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
MIRROR_DIR = ROOT / "hig_mirror"
MIRROR_DIR.mkdir(exist_ok=True)

PAGES = {
    # Foundations
    "foundations-typography":    "typography",
    "foundations-color":         "color",
    "foundations-layout":        "layout",
    "foundations-materials":     "materials",
    "foundations-motion":        "motion",
    "foundations-accessibility": "accessibility",
    "foundations-dark-mode":     "dark-mode",
    # Components I'm using
    "components-buttons":        "buttons",
    "components-lists-and-tables": "lists-and-tables",
    "components-navigation-bars":  "navigation-bars",
    "components-tab-bars":         "tab-bars",
    "components-toolbars":         "toolbars",
    "components-segmented-controls": "segmented-controls",
    "components-charts":         "charts",
    "components-labels":         "labels",
    # Patterns
    "patterns-loading":          "loading",
    "patterns-feedback":         "feedback",
}

BASE = "https://developer.apple.com/design/human-interface-guidelines/"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        for slug, path in PAGES.items():
            url = BASE + path
            try:
                page.goto(url, wait_until="networkidle", timeout=20_000)
            except Exception as exc:
                print(f"  FAIL {slug}: {exc}")
                continue
            page.wait_for_timeout(800)
            # Grab main content
            text = page.locator("main").inner_text() if page.locator("main").count() else page.inner_text("body")
            (MIRROR_DIR / f"{slug}.txt").write_text(text)
            print(f"  OK   {slug}  ({len(text):>6} chars)")
        browser.close()


if __name__ == "__main__":
    main()
