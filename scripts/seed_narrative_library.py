"""Seed narrative_library for media_sales_v1 from canonical JSON.

Source: reference_docs/media_sales_v1_narratives.json
  - Strips em dashes on ingest (rule 8; replaces — and – with ' - ')
  - Maps narrative_persuasion -> storytelling (DB dimension name)
  - For any (dimension, band) pair absent from the JSON, calls Haiku via
    complete_structured to generate a strength/action pair
  - Idempotent: upserts on conflict

Usage:
    ANTHROPIC_API_KEY=sk-... python -m scripts.seed_narrative_library
    # Or without a key (canonical-only, no gap-fill):
    python -m scripts.seed_narrative_library
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DECIPHER_DB_PORT", "55432")

from app.db import conn  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
NARRATIVES_PATH = REPO / "reference_docs" / "media_sales_v1_narratives.json"

TAXONOMY_CODE = "media_sales_v1"

DIM_MAP = {
    "cognitive_empathy":   "cognitive_empathy",
    "eq":                  "eq",
    "pressure_composure":  "pressure_composure",
    "narrative_persuasion": "storytelling",
    "storytelling":        "storytelling",
}

DIM_LABELS = {
    "cognitive_empathy":  "Cognitive Empathy",
    "eq":                 "Emotional Intelligence",
    "pressure_composure": "Pressure Composure",
    "storytelling":       "Narrative Persuasion",
}

BANDS = ["developing", "practising", "performing", "elite"]

GENERATE_SCHEMA = {
    "type": "object",
    "properties": {
        "strength": {
            "type": "string",
            "description": (
                "2-4 sentences describing what this person does well at this band level. "
                "Second person ('You...'). Specific, no generic filler."
            ),
        },
        "action": {
            "type": "string",
            "description": (
                "1-3 sentences: one concrete action the person can take this week. "
                "Second person. Specific drill or habit, not general advice."
            ),
        },
    },
    "required": ["strength", "action"],
    "additionalProperties": False,
}


def _strip_dashes(text: str) -> str:
    """Replace em/en dashes with space-hyphen-space (rule 8: no em dashes).

    Handles surrounding whitespace so 'solve — which' and 'solve— which'
    both produce 'solve - which' without double spaces.
    """
    import re
    # \s* absorbs existing spaces around the dash
    text = re.sub(r"\s*—\s*", " - ", text)
    text = re.sub(r"\s*–\s*", "-", text)  # en-dash in ranges: 1–3 → 1-3
    return text


def _generate_via_haiku(dimension: str, band: str) -> dict[str, str]:
    """Call Haiku to generate a strength/action pair for a missing slot."""
    from app.claude_client import complete_structured, HAIKU

    dim_label = DIM_LABELS.get(dimension, dimension.replace("_", " ").title())
    prompt = (
        f"You are writing coaching narratives for a media sales DNA audit platform.\n\n"
        f"Write a strength observation and a specific coaching action for a media salesperson "
        f"whose {dim_label} score is in the '{band}' band.\n\n"
        f"Band definitions:\n"
        f"  developing: score < 40 (early stage, needs foundational habits)\n"
        f"  practising: 40-64 (aware, inconsistent application)\n"
        f"  performing: 65-84 (reliable, ready for refinement)\n"
        f"  elite: 85+ (competitive advantage, time to teach others)\n\n"
        f"Rules:\n"
        f"- Australian English (practise, behaviour, recognise)\n"
        f"- No em dashes, no generic filler words\n"
        f"- No bro-sales cliches\n"
        f"- The person is always the hero; never mention the product\n"
        f"- Strength: 2-4 sentences. Action: 1-3 sentences with one concrete weekly habit\n"
    )
    result = complete_structured(prompt, GENERATE_SCHEMA, model=HAIKU)
    result["strength"] = _strip_dashes(result["strength"])
    result["action"] = _strip_dashes(result["action"])
    return result


def main() -> None:
    raw = json.loads(NARRATIVES_PATH.read_text())

    # Normalise JSON keys to DB dimension names and strip dashes
    canonical: dict[str, dict[str, dict[str, str]]] = {}
    for json_dim, bands_data in raw.items():
        db_dim = DIM_MAP.get(json_dim)
        if db_dim is None:
            print(f"  WARNING: unknown dimension key '{json_dim}' in JSON, skipping", file=sys.stderr)
            continue
        canonical[db_dim] = {}
        for band, payload in bands_data.items():
            canonical[db_dim][band] = {
                "strength": _strip_dashes(payload["strength"]),
                "action":   _strip_dashes(payload["action"]),
            }

    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    if not has_key:
        print("ANTHROPIC_API_KEY not set; gap-fill via Haiku disabled (canonical rows only).")

    upserted = 0
    generated = 0
    with conn() as c, c.cursor() as cur:
        for dim in DIM_LABELS:
            for band in BANDS:
                if dim in canonical and band in canonical[dim]:
                    payload = canonical[dim][band]
                else:
                    if not has_key:
                        print(
                            f"  SKIP: no canonical row for ({dim}, {band}) and no API key",
                            file=sys.stderr,
                        )
                        continue
                    print(f"  Generating via Haiku: ({dim}, {band})...")
                    payload = _generate_via_haiku(dim, band)
                    generated += 1

                cur.execute(
                    """INSERT INTO narrative_library
                           (taxonomy_code, dimension, band, strength, action)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (taxonomy_code, dimension, band) DO UPDATE
                         SET strength = EXCLUDED.strength,
                             action   = EXCLUDED.action""",
                    (TAXONOMY_CODE, dim, band, payload["strength"], payload["action"]),
                )
                upserted += 1

        cur.execute(
            "SELECT count(*) FROM narrative_library WHERE taxonomy_code = %s",
            (TAXONOMY_CODE,),
        )
        total = cur.fetchone()[0]

    print(f"narrative_library ({TAXONOMY_CODE}): {upserted} upserted, {generated} generated via Haiku")
    print(f"  Total rows for this taxonomy: {total}")


if __name__ == "__main__":
    main()
