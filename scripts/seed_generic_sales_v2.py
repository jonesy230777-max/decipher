"""Seed the Hunter Sales DNA Audit v2 questions (38-question hunter-cycle
audit: cold call -> gatekeeper/discovery -> pressure/objections -> pitch/close).

Source of truth: reference_docs/generic_sales_v2_full.json, built from the
verbatim Google Doc "generic-sales-dna-audit-v2.md". Each question has 4
options (A-D); unlike general_sales_v1, EVERY option here carries both a
1-5 "score" (rescaled from the doc's 1-4 band: 1->1, 2->2, 3->4, 4->5) AND
an "identity" archetype tag (doc's R/E/O/L letters, mapped to the identity
codes actually used by the report pipeline -- app/dna_report.py and
app/trait_content.py's EQ_IDENTITY_LABEL/EQ_IDENTITY_CONTENT dicts:
    R -> regulator, E -> edge_builder, O -> observer, L -> namer
(NOT "labeler" -- that's an unused row in seed.sql's archetypes table;
nothing in the report/narrative pipeline reads it. "namer" is the string
every live consumer of eq_identity actually keys on.)

This means every one of the 38 responses both:
  1. Contributes its rescaled score to one of the 4 canonical traits
     (cognitive_empathy / eq / pressure_composure / narrative_persuasion), and
  2. Casts one plurality vote for the respondent's dominant EQ identity,
     surfaced via the existing eq_identity field/report glossary/narrative
     content -- the same mechanism general_sales_v1 uses for its 3
     dedicated identity_grid questions, just tallied across all 38 answers
     here instead of 3. This requires the small additive dna_scoring.py
     change (2026-08-02) that lets a "scored" question's matched option
     also register an identity vote; media_sales_v1/general_sales_v1/
     bespoke options have no "identity" key so that change is a no-op for
     them.

_build_response_meta below is identical to seed_general_sales_v1.py's --
it already handles a "score"+"identity" option correctly, since it checks
for each key independently. Reused rather than duplicated.

Same scoring engine as media_sales_v1 / general_sales_v1 (dna_scoring.py is
version-agnostic; it only ever joins questions -> audits via
audit_version_id). This script seeds a third question bank under a new
version code so all three audits run side by side.

Idempotent. Re-running replaces this version's questions in place.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from app.db import conn

REPO = Path(__file__).resolve().parents[1]
DATA = json.loads((REPO / "reference_docs" / "generic_sales_v2_full.json").read_text())

QUESTIONS = DATA["questions"]

TRAIT_TO_DIM = {
    "cognitive_empathy": "cognitive_empathy",
    "eq": "eq",
    "pressure_composure": "pressure_composure",
    "narrative_persuasion": "storytelling",
}


def _build_response_meta(q: dict) -> dict:
    """Same shape/logic as seed_general_sales_v1.py's helper -- an option
    can carry "score", "identity", or (new for this version) both."""
    trait = q["trait"]
    options_meta = []
    for opt in q["options"]:
        entry: dict = {"letter": opt["letter"], "text": opt["text"]}
        if "score" in opt:
            entry["score"] = opt["score"]
        if "identity" in opt:
            entry["identity"] = opt["identity"]
        options_meta.append(entry)

    meta: dict = {
        "options": [o["text"] for o in q["options"]],
        "kind": "scored",
        "canonical_trait": trait,
        "options_meta": options_meta,
        "source_form": "generic_sales_dna_v2",
        "scoring": [opt.get("score", 0) for opt in q["options"]],
    }
    return meta


def main() -> None:
    os.environ.setdefault("DECIPHER_DB_PORT", "55432")

    with conn() as c, c.cursor() as cur:
        cur.execute(
            """INSERT INTO audit_versions (code, name, is_active)
               VALUES ('generic_sales_v2', 'Hunter Sales DNA Audit', TRUE)
               ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
               RETURNING audit_version_id"""
        )
        version_id = cur.fetchone()[0]

        cur.execute("DELETE FROM questions WHERE audit_version_id = %s", (version_id,))

        for seq, q in enumerate(QUESTIONS, start=1):
            trait = q["trait"]
            dim = TRAIT_TO_DIM[trait]
            meta = _build_response_meta(q)

            cur.execute(
                """INSERT INTO questions
                   (audit_version_id, sequence, dimension, archetype_signal,
                    weight, prompt, response_type, response_meta)
                   VALUES (%s, %s, %s, %s, 1.0, %s, 'choice', %s::jsonb)""",
                (
                    version_id,
                    seq,
                    dim,
                    "identity_grid",
                    q["prompt"],
                    json.dumps(meta),
                ),
            )

    print(f"Seeded generic_sales_v2 (audit_version_id={version_id}) with {len(QUESTIONS)} questions.")
    print("  All 38 questions are dual-purpose: trait-scored AND identity-tagged.")


if __name__ == "__main__":
    main()
