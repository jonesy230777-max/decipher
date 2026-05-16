"""Media Sales DNA scoring engine (media_sales_v1).

`score_audit(audit_id)` reads responses, computes per-trait scores 0-100,
bands them, identifies the EQ identity from the 3 identity questions, and
assigns one of the 8 archetypes from the top-2 traits (with all-high /
all-low special cases). Persists to audit_scores + band_classifications +
archetype_assignments. Idempotent.
"""
from __future__ import annotations
import json
from typing import Iterable

from app.db import conn, event

# Canonical trait → DB column in audit_scores (narrative_persuasion → storytelling)
TRAIT_TO_COL = {
    "cognitive_empathy":   "cognitive_empathy",
    "eq":                  "eq",
    "pressure_composure":  "pressure_composure",
    "narrative_persuasion":"storytelling",
}
TRAIT_TO_DIM = {
    "cognitive_empathy":   "cognitive_empathy",
    "eq":                  "eq",
    "pressure_composure":  "pressure_composure",
    "narrative_persuasion":"storytelling",
}
DIM_HUMAN = {
    "cognitive_empathy":   "Cognitive Empathy",
    "eq":                  "EQ",
    "pressure_composure":  "Pressure Composure",
    "storytelling":        "Narrative Persuasion",
    "narrative_persuasion":"Narrative Persuasion",
}

# 0-100 lower bounds per canonical brief
BAND_THRESHOLDS = [("elite", 85), ("performing", 65), ("practising", 40), ("developing", 0)]

# top1 / top2 (sorted alphabetical for canonical match) → archetype name
# The archetype table is bidirectional (top1 ↔ top2 are unordered for matching).
ARCHETYPE_BY_PAIR = {
    frozenset(["cognitive_empathy", "eq"]):                "The Trust Architect",
    frozenset(["cognitive_empathy", "narrative_persuasion"]): "The Story Listener",
    frozenset(["cognitive_empathy", "pressure_composure"]):   "The Calm Diagnostician",
    frozenset(["eq", "narrative_persuasion"]):              "The Strategic Empath",
    frozenset(["eq", "pressure_composure"]):                "The Composed Reader",
    frozenset(["pressure_composure", "narrative_persuasion"]): "The Confident Storyteller",
}
ELITE_OPERATOR = "The Elite Operator"
RAW_MATERIAL   = "The Raw Material"


def _band_for(score_100: float) -> str:
    for band, lower in BAND_THRESHOLDS:
        if score_100 >= lower:
            return band
    return "developing"


def _normalise(scores_1_to_5: Iterable[float]) -> float:
    """Mean of 1-5 scores → 0-100. (mean - 1) / 4 * 100."""
    vals = [float(s) for s in scores_1_to_5]
    if not vals:
        return 0.0
    mean = sum(vals) / len(vals)
    return max(0.0, min(100.0, ((mean - 1.0) / 4.0) * 100.0))


def _score_from_response(answer_value, answer_text: str | None, options_meta: list[dict]) -> int | None:
    """Resolve a response back to its canonical 1-5 score.

    Match priority:
      1. answer_value is an integer index (0-based) into options_meta
      2. answer_text matches options_meta[i].text
    Returns None if neither resolves (caller skips).
    """
    if answer_value is not None:
        try:
            i = int(round(float(answer_value)))
            if 0 <= i < len(options_meta) and "score" in options_meta[i]:
                return int(options_meta[i]["score"])
        except (TypeError, ValueError):
            pass
    if answer_text:
        for opt in options_meta:
            if opt.get("text") == answer_text and "score" in opt:
                return int(opt["score"])
    return None


def _identity_from_response(answer_value, answer_text: str | None, options_meta: list[dict]) -> str | None:
    if answer_value is not None:
        try:
            i = int(round(float(answer_value)))
            if 0 <= i < len(options_meta):
                return options_meta[i].get("identity")
        except (TypeError, ValueError):
            pass
    if answer_text:
        for opt in options_meta:
            if opt.get("text") == answer_text:
                return opt.get("identity")
    return None


def _pick_archetype(scores_100: dict[str, float]) -> tuple[str, float, bool]:
    """Return (archetype_name, confidence_0_1, tiebreak_applied)."""
    vals = [scores_100[t] for t in ("cognitive_empathy", "eq", "pressure_composure", "narrative_persuasion")]
    if all(v >= 85 for v in vals):
        return ELITE_OPERATOR, min(vals) / 100.0, False
    if all(v < 40 for v in vals):
        return RAW_MATERIAL, (100.0 - max(vals)) / 100.0, False

    ranked = sorted(scores_100.items(), key=lambda kv: kv[1], reverse=True)
    top1_trait, top1_score = ranked[0]
    top2_trait, top2_score = ranked[1]
    third_score = ranked[2][1]

    tiebreak = abs(top2_score - third_score) < 1e-6
    archetype = ARCHETYPE_BY_PAIR.get(frozenset([top1_trait, top2_trait]), ELITE_OPERATOR)

    spread = (top1_score + top2_score) / 2.0 - sum(s for _, s in ranked[2:]) / max(1, len(ranked) - 2)
    confidence = max(0.0, min(1.0, 0.5 + spread / 100.0))
    return archetype, confidence, tiebreak


def score_audit(audit_id: int) -> dict:
    """Score one audit. Idempotent: upserts audit_scores / band_classifications /
    archetype_assignments. Returns a summary dict.
    """
    with conn() as c, c.cursor() as cur:
        cur.execute(
            """SELECT q.sequence, q.response_meta, r.answer_value, r.answer_text
                 FROM questions q
                 JOIN audits a   ON a.audit_version_id = q.audit_version_id
                 LEFT JOIN responses r ON r.question_id = q.question_id AND r.audit_id = a.audit_id
                WHERE a.audit_id = %s
                ORDER BY q.sequence""",
            (audit_id,),
        )
        rows = cur.fetchall()
        if not rows:
            raise ValueError(f"audit {audit_id} has no questions/responses")

        per_trait: dict[str, list[int]] = {
            "cognitive_empathy": [],
            "eq": [],
            "pressure_composure": [],
            "narrative_persuasion": [],
        }
        identity_votes: dict[str, int] = {}
        unanswered = 0

        for sequence, meta, ans_val, ans_text in rows:
            if meta is None:
                continue
            kind = meta.get("kind", "scored")
            options_meta = meta.get("options_meta") or []
            canonical_trait = meta.get("canonical_trait")

            if ans_val is None and (ans_text is None or ans_text == ""):
                unanswered += 1
                continue

            if kind == "identity":
                ident = _identity_from_response(ans_val, ans_text, options_meta)
                if ident:
                    identity_votes[ident] = identity_votes.get(ident, 0) + 1
                continue

            score_1_5 = _score_from_response(ans_val, ans_text, options_meta)
            if score_1_5 is None:
                continue

            target = canonical_trait
            if target == "eq_bonus":
                target = "eq"
            if target in per_trait:
                per_trait[target].append(score_1_5)

        scores_100 = {trait: _normalise(vals) for trait, vals in per_trait.items()}
        scores_0_1 = {trait: round(v / 100.0, 4) for trait, v in scores_100.items()}

        bands = {TRAIT_TO_DIM[t]: _band_for(scores_100[t]) for t in per_trait}

        eq_identity = None
        if identity_votes:
            eq_identity = max(identity_votes.items(), key=lambda kv: kv[1])[0]

        archetype_name, confidence, tiebreak = _pick_archetype(scores_100)

        raw_band_json = {
            "scores_100": scores_100,
            "bands": bands,
            "eq_identity": eq_identity,
            "identity_votes": identity_votes,
            "unanswered": unanswered,
        }

        cur.execute(
            """INSERT INTO audit_scores (audit_id, cognitive_empathy, eq, pressure_composure, storytelling, raw_band_json)
                 VALUES (%s, %s, %s, %s, %s, %s::jsonb)
               ON CONFLICT (audit_id) DO UPDATE SET
                 cognitive_empathy = EXCLUDED.cognitive_empathy,
                 eq                = EXCLUDED.eq,
                 pressure_composure= EXCLUDED.pressure_composure,
                 storytelling      = EXCLUDED.storytelling,
                 raw_band_json     = EXCLUDED.raw_band_json,
                 computed_at       = now()""",
            (audit_id,
             scores_0_1["cognitive_empathy"],
             scores_0_1["eq"],
             scores_0_1["pressure_composure"],
             scores_0_1["narrative_persuasion"],
             json.dumps(raw_band_json)),
        )

        cur.execute("DELETE FROM band_classifications WHERE audit_id = %s", (audit_id,))
        for trait, score_100 in scores_100.items():
            cur.execute(
                """INSERT INTO band_classifications (audit_id, dimension, band, score)
                     VALUES (%s, %s, %s, %s)""",
                (audit_id, TRAIT_TO_DIM[trait], bands[TRAIT_TO_DIM[trait]], round(score_100, 2)),
            )

        cur.execute(
            """SELECT archetype_id, description FROM archetypes
                WHERE taxonomy_id = 2 AND name = %s""",
            (archetype_name,),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"archetype not seeded: {archetype_name}")
        archetype_id = row[0]
        archetype_description = row[1]

        cur.execute(
            """INSERT INTO archetype_assignments (audit_id, taxonomy_id, archetype_id, confidence, tiebreak_applied)
                 VALUES (%s, 2, %s, %s, %s)
               ON CONFLICT (audit_id) DO UPDATE SET
                 taxonomy_id      = EXCLUDED.taxonomy_id,
                 archetype_id     = EXCLUDED.archetype_id,
                 confidence       = EXCLUDED.confidence,
                 tiebreak_applied = EXCLUDED.tiebreak_applied,
                 assigned_at      = now()""",
            (audit_id, archetype_id, round(confidence, 4), tiebreak),
        )

        cur.execute(
            "UPDATE audits SET status = 'scored', completed_at = COALESCE(completed_at, now()) WHERE audit_id = %s AND status IN ('completed','in_progress')",
            (audit_id,),
        )

    event("audit.scored", subject_id=str(audit_id), payload={
        "scores_100": {k: round(v, 1) for k, v in scores_100.items()},
        "bands": bands,
        "eq_identity": eq_identity,
        "archetype": archetype_name,
        "confidence": round(confidence, 3),
        "tiebreak": tiebreak,
        "unanswered": unanswered,
    })

    return {
        "audit_id": audit_id,
        "scores_100": scores_100,
        "bands": bands,
        "eq_identity": eq_identity,
        "archetype": archetype_name,
        "archetype_description": archetype_description,
        "confidence": confidence,
        "tiebreak_applied": tiebreak,
        "unanswered": unanswered,
    }
