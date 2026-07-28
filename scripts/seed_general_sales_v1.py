"""Seed the General Sales DNA Audit v1 questions from the canonical brief.

Source of truth: reference_docs/general_sales_v1_full.json
- Correct per-option 1-5 scores (calibrated, not positional)
- Correct trait-per-question mapping (trait_by_qnum)
- Writes the response_meta format that dna_scoring.py reads:
  options_meta: [{letter, text, score}] for scored questions
  options_meta: [{letter, text, identity}] for eq_identity questions
  kind: "scored" | "identity"
  canonical_trait: str

Same scoring engine as media_sales_v1 (dna_scoring.py is version-agnostic,
it only ever joins questions -> audits via audit_version_id). This script
just seeds a second, industry-neutral question bank under a new version
code so both audits can run side by side.

Idempotent. Re-running replaces this version's questions in place.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from app.db import conn

REPO = Path(__file__).resolve().parents[1]
DATA = json.loads((REPO / "reference_docs" / "general_sales_v1_full.json").read_text())

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
        "source_form": "general_sales_dna_v1",
    }
    if trait != "eq_identity":
        meta["scoring"] = [opt.get("score", 0) for opt in q["options"]]
    return meta


def main() -> None:
    os.environ.setdefault("DECIPHER_DB_PORT", "55432")

    with conn() as c, c.cursor() as cur:
        cur.execute(
            """INSERT INTO audit_versions (code, name, is_active)
               VALUES ('general_sales_v1', 'General Sales DNA Audit', TRUE)
               ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
               RETURNING audit_version_id"""
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

    print(f"Seeded general_sales_v1 (audit_version_id={version_id}) with {len(QUESTIONS)} questions.")
    print(f"  EQ Identity questions: {eq_identity_count}")
    print(f"  Scored questions: {len(QUESTIONS) - eq_identity_count}")


if __name__ == "__main__":
    main()
