"""Seed the Retail Media Sales DNA Audit v1 questions.

Source of truth: reference_docs/retail_media_v1_full.json
- Correct per-option 1-5 scores (calibrated, not positional)
- Correct trait-per-question mapping (trait field per question)
- Writes the response_meta format that dna_scoring.py reads:
    options_meta: [{letter, text, score}] for scored questions
    options_meta: [{letter, text, identity}] for eq_identity questions
    kind: "scored" | "identity"
    canonical_trait: str

Modelled directly on scripts/seed_charity_fundraising_v1.py, same schema,
same TRAIT_TO_DIM keys (cognitive_empathy, eq, eq_bonus, pressure_composure,
narrative_persuasion, eq_identity), same 31 scored + 3 eq_identity shape
(here: 24 core-trait + 7 eq_bonus + 3 eq_identity = 34).
Registers as a new, fifth audit_versions row. Does not touch media_sales_v1,
generic_sales_v2, general_sales_v1, or charity_fundraising_v1.

Also upserts a new industries row (code 'retail_media') and links it via
audit_versions.industry_id, same pattern as charity_fundraising_v1. Without
this, app/dna_report.py and dna_report_v2.py's industry_name lookup (JOIN
industries ON industry_id) returns NULL and the Claude narrative prompt
silently defaults to "Media" for every retail media respondent, per
_narrative_system_prompt's `industry_name or "media"` fallback -- which
would happen to read plausibly for this audience by coincidence, but should
still be set explicitly so reports correctly reference retail media,
category managers, and trading terms rather than generic media sales.

Idempotent. Re-running replaces this version's questions in place.

After running this script, dashboard/src/pages/AuditTake.tsx still needs a
small manual patch to surface 'Retail Media Sales' in the Audit type
dropdown -- see retail_media_v1_AuditTake_patch.diff alongside this file.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from app.db import conn

REPO = Path(__file__).resolve().parents[1]
DATA = json.loads((REPO / "reference_docs" / "retail_media_v1_full.json").read_text())

QUESTIONS = DATA["questions"]

TRAIT_TO_DIM = {
    "cognitive_empathy": "cognitive_empathy",
    "eq": "eq",
    "eq_bonus": "eq",
    "pressure_composure": "pressure_composure",
    "narrative_persuasion": "storytelling",
    "eq_identity": "eq",
}


def _build_response_meta(q: dict) -> dict:
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
        "kind": "identity" if trait == "eq_identity" else "scored",
        "canonical_trait": trait,
        "options_meta": options_meta,
        "source_form": "retail_media_v1",
    }
    if trait != "eq_identity":
        meta["scoring"] = [opt.get("score", 0) for opt in q["options"]]
    return meta


def main() -> None:
    os.environ.setdefault("DECIPHER_DB_PORT", "55432")

    with conn() as c, c.cursor() as cur:
        cur.execute(
            """INSERT INTO industries (code, name, description)
               VALUES (%s, %s, %s)
               ON CONFLICT (code) DO UPDATE SET
                  name = EXCLUDED.name,
                  description = EXCLUDED.description
               RETURNING industry_id""",
            (
                "retail_media",
                "Retail Media",
                "Reps selling retail media networks (onsite, in-store, "
                "sponsored placements) to brands, media agencies, and "
                "trade/shopper marketing teams.",
            ),
        )
        industry_id = cur.fetchone()[0]

        cur.execute(
            """INSERT INTO audit_versions (code, name, is_active, industry_id)
               VALUES ('retail_media_v1', 'Retail Media Sales DNA Audit', TRUE, %s)
               ON CONFLICT (code) DO UPDATE SET
                  name = EXCLUDED.name,
                  industry_id = EXCLUDED.industry_id
               RETURNING audit_version_id""",
            (industry_id,),
        )
        version_id = cur.fetchone()[0]

        cur.execute("DELETE FROM questions WHERE audit_version_id = %s", (version_id,))

        eq_identity_count = 0
        for seq, q in enumerate(QUESTIONS, start=1):
            trait = q["trait"]
            dim = TRAIT_TO_DIM[trait]
            meta = _build_response_meta(q)

            if trait == "eq_identity":
                eq_identity_count += 1

            cur.execute(
                """INSERT INTO questions
                       (audit_version_id, sequence, dimension, archetype_signal,
                        weight, prompt, response_type, response_meta)
                   VALUES (%s, %s, %s, %s, 1.0, %s, 'choice', %s::jsonb)""",
                (
                    version_id,
                    seq,
                    dim,
                    "identity_grid" if trait == "eq_identity" else None,
                    q["prompt"],
                    json.dumps(meta),
                ),
            )

        print(f"Seeded retail_media_v1 (audit_version_id={version_id}) with {len(QUESTIONS)} questions.")
        print(f"  Industry: retail_media (industry_id={industry_id})")
        print(f"  EQ Identity questions: {eq_identity_count}")
        print(f"  Scored questions: {len(QUESTIONS) - eq_identity_count}")


if __name__ == "__main__":
    main()
