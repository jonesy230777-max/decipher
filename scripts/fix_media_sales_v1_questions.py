"""Repair media_sales_v1 (audit_version_id=2) questions to align with the
canonical brief: correct dimension per trait_by_qnum, and embed per-option
canonical 1-5 scores + EQ identity codes inside response_meta.

DB constraint maps `narrative_persuasion` → `storytelling` column/dimension.
EQ identity questions (EQ1-3) keep dimension='eq' (constraint allows it) but
response_meta.kind='identity' so scoring treats them as identity-only.

Run once. Idempotent.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

os.environ.setdefault("DECIPHER_DB_PORT", "55432")

from app.db import conn  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DATA = json.loads((REPO / "reference_docs/media_sales_v1_full.json").read_text())

QUESTIONS = DATA["questions"]
TRAIT_BY_QNUM = DATA["trait_by_qnum"]

# Canonical trait → DB dimension (narrative_persuasion stored as 'storytelling')
TRAIT_TO_DIM = {
    "cognitive_empathy":   "cognitive_empathy",
    "eq":                  "eq",
    "eq_bonus":            "eq",
    "pressure_composure":  "pressure_composure",
    "narrative_persuasion":"storytelling",
    "eq_identity":         "eq",
}


def build_response_meta(q: dict) -> dict:
    trait = q["trait"]
    options_meta = []
    for opt in q["options"]:
        entry = {"letter": opt["letter"], "text": opt["text"]}
        if "score" in opt:
            entry["score"] = opt["score"]
        if "identity" in opt:
            entry["identity"] = opt["identity"]
        options_meta.append(entry)

    meta: dict = {
        "options": [o["text"] for o in q["options"]],   # legacy: keep flat text array
        "kind": "identity" if trait == "eq_identity" else "scored",
        "canonical_trait": trait,
        "options_meta": options_meta,
        "source_form": "media_sales_dna_v1",
    }
    if trait != "eq_identity":
        meta["scoring"] = [opt.get("score", 0) for opt in q["options"]]
    return meta


def main() -> None:
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT question_id, sequence FROM questions WHERE audit_version_id=2 ORDER BY sequence")
        rows = cur.fetchall()
        if len(rows) != len(QUESTIONS):
            raise SystemExit(f"questions mismatch: DB has {len(rows)}, canonical has {len(QUESTIONS)}")

        updated = 0
        for (question_id, sequence), q in zip(rows, QUESTIONS):
            trait = q["trait"]
            dim = TRAIT_TO_DIM[trait]
            meta = build_response_meta(q)
            cur.execute(
                """UPDATE questions
                      SET dimension = %s,
                          prompt = %s,
                          response_type = 'choice',
                          response_meta = %s::jsonb
                    WHERE question_id = %s""",
                (dim, q["prompt"], json.dumps(meta), question_id),
            )
            updated += 1
        print(f"Updated {updated} questions for media_sales_v1 (audit_version_id=2)")


if __name__ == "__main__":
    main()
