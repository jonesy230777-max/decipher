"""Backfill scoring + report for all media_sales_v1 audits.

Picks every v2 audit (audit_version_id = 2) that has at least one response and
is missing either an audit_scores row or a reports row; runs score_audit() +
generate_report() in sequence. Idempotent.

Usage:
    PYTHONPATH=. .venv/bin/python scripts/backfill_scoring.py            # dry run
    PYTHONPATH=. .venv/bin/python scripts/backfill_scoring.py --apply    # do it
    PYTHONPATH=. .venv/bin/python scripts/backfill_scoring.py --apply --send-email
"""
from __future__ import annotations
import argparse
import os
import sys

os.environ.setdefault("DECIPHER_DB_PORT", "55432")

from app.db import rows, scalar  # noqa: E402


def find_candidates() -> list[dict]:
    return rows(
        """SELECT a.audit_id, a.respondent_id, a.status,
                  s.audit_id IS NOT NULL AS has_score,
                  EXISTS (SELECT 1 FROM reports r WHERE r.audit_id = a.audit_id) AS has_report,
                  (SELECT count(*) FROM responses r WHERE r.audit_id = a.audit_id) AS n_responses
             FROM audits a
        LEFT JOIN audit_scores s ON s.audit_id = a.audit_id
            WHERE a.audit_version_id = 2
            ORDER BY a.audit_id"""
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually run; without this flag, dry-run only.")
    parser.add_argument("--send-email", action="store_true", help="Also deliver via Mailpit.")
    args = parser.parse_args()

    required_qs = scalar("SELECT count(*) FROM questions WHERE audit_version_id = 2") or 34

    candidates = find_candidates()
    needs_work = [
        c for c in candidates
        if (not c["has_score"] or not c["has_report"]) and c["n_responses"] >= required_qs
    ]
    incomplete = [c for c in candidates if c["n_responses"] < required_qs]

    print(f"v2 audits total:           {len(candidates)}")
    print(f"already scored + reported: {sum(1 for c in candidates if c['has_score'] and c['has_report'])}")
    print(f"need backfill:             {len(needs_work)}")
    print(f"incomplete (skipped):      {len(incomplete)} (need {required_qs} responses)")

    if not args.apply:
        for c in needs_work[:10]:
            print(f"  would score: audit_id={c['audit_id']} responses={c['n_responses']}")
        if len(needs_work) > 10:
            print(f"  ... and {len(needs_work) - 10} more")
        print("\n(dry run; re-run with --apply to execute)")
        return

    from app.dna_scoring import score_audit
    from app.dna_report  import generate_report
    if args.send_email:
        from app.api_server import _send_report_email

    ok = 0
    failures: list[tuple[int, str]] = []
    for c in needs_work:
        aid = c["audit_id"]
        try:
            score_audit(aid)
            rep = generate_report(aid)
            if args.send_email:
                try:
                    _send_report_email(aid, rep["report_id"], rep["pdf_path"])
                except Exception as smtp_exc:
                    print(f"  audit {aid}: scored + reported, smtp failed: {smtp_exc}")
            ok += 1
        except Exception as exc:
            failures.append((aid, str(exc)))

    print(f"\nbackfilled: {ok}/{len(needs_work)}")
    if failures:
        print(f"failures:   {len(failures)}")
        for aid, msg in failures[:5]:
            print(f"  audit {aid}: {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
