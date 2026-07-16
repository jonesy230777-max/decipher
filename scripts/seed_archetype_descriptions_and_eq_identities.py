"""Fill in archetype descriptions for taxonomy_id=2 (media_sales_v1) and
add the 4 EQ-identity narrative blocks to narrative_library (dimension='eq_identity').

Idempotent. Re-running just upserts.
"""
from __future__ import annotations
import os

os.environ.setdefault("DECIPHER_DB_PORT", "55432")

from app.db import conn  # noqa: E402

ARCHETYPE_DESCRIPTIONS = {
    "trust_architect": (
        "Top traits: Cognitive Empathy + EQ. Buyers feel heard inside the first "
        "two minutes. Reads quiet rooms by labelling the unspoken concern, then "
        "lets silence do the work. Builds the relationship that closes the deal."
    ),
    "story_listener": (
        "Top traits: Cognitive Empathy + Narrative Persuasion. Listens past the "
        "literal answer to the story underneath, then mirrors it back as a "
        "frame the buyer recognises as their own. Persuasion feels like agreement."
    ),
    "calm_diagnostician": (
        "Top traits: Cognitive Empathy + Pressure Composure. The diagnostician "
        "buyers trust under load. Holds the room when the conversation tightens, "
        "and asks one clarifying question instead of three reassuring ones."
    ),
    "strategic_empath": (
        "Top traits: EQ + Narrative Persuasion. Uses emotional information as a "
        "lever, not a destination. Names the feeling, then reframes it into the "
        "story that moves the buyer one step forward."
    ),
    "composed_reader": (
        "Top traits: EQ + Pressure Composure. Reads emotion accurately even when "
        "the buyer is stressed, then meets it with steady pace and clear "
        "language. Brings the temperature down without losing momentum."
    ),
    "confident_storyteller": (
        "Top traits: Pressure Composure + Narrative Persuasion. Owns the room "
        "with a clean narrative arc, especially when the stakes climb. The "
        "story lands because the messenger never wobbles."
    ),
    "elite_operator": (
        "All four traits above 85. Operates with full range: hears, holds, "
        "frames, and converts. Pair with a developing rep for 4 weeks and "
        "expect measurable lift at the 90-day re-audit."
    ),
    "raw_material": (
        "All four traits below 40. Coaching priority. Strong technical product "
        "knowledge in most cases, with the four conversation skills still to "
        "be built. Start with reflective listening and one named emotion per "
        "call."
    ),
}

EQ_IDENTITY_NARRATIVES = {
    "regulator": {
        "strength": (
            "Your EQ signature is the Regulator. Under pressure you stay logical, "
            "your judgement does not get cloudy when the room heats up, and "
            "buyers trust the steadiness you bring. You are the rep clients call "
            "first when something has gone wrong elsewhere."
        ),
        "action": (
            "Practise one deliberate emotional acknowledgement per difficult call "
            "this week. Your composure is an asset; pair it with one labelled "
            "feeling and the buyer feels both safe and seen."
        ),
    },
    "edge_builder": {
        "strength": (
            "Your EQ signature is the Edge Builder. You treat the buyer's "
            "emotion as commercial information, not noise. The signal you pick "
            "up about hesitation, irritation, or quiet excitement is the lever "
            "that informs your next move."
        ),
        "action": (
            "Audit the last five deals you lost. For each, write one emotional "
            "lever the buyer telegraphed that you did not use. Take one of "
            "those levers into your next live call."
        ),
    },
    "observer": {
        "strength": (
            "Your EQ signature is the Observer. You notice the emotional "
            "temperature before anyone names it: the slight pause, the change "
            "of pace, the buyer who has gone polite when they were warm two "
            "minutes ago. You see the shift first."
        ),
        "action": (
            "Translate one observation into a spoken acknowledgement per call. "
            "Seeing it is half the work; the other half is letting the buyer "
            "hear that you saw it, so they do not have to perform."
        ),
    },
    "labeler": {
        "strength": (
            "Your EQ signature is the Labeler. You will say the awkward thing "
            "out loud when others rush past it. Buyers find this disarming, "
            "and it shortens the distance from objection to honest answer."
        ),
        "action": (
            "Pace yourself: name the emotion early, then hold. Resist the urge "
            "to immediately solve. The 8-second silence after a well-placed "
            "label is where the buyer's real concern emerges."
        ),
    },
}


def main() -> None:
    with conn() as c, c.cursor() as cur:
        for code, desc in ARCHETYPE_DESCRIPTIONS.items():
            cur.execute(
                "UPDATE archetypes SET description = %s WHERE taxonomy_id = 2 AND code = %s",
                (desc, code),
            )
        cur.execute("SELECT count(*) FROM archetypes WHERE taxonomy_id=2 AND description IS NOT NULL")
        n_arch = cur.fetchone()[0]

        for ident, payload in EQ_IDENTITY_NARRATIVES.items():
            cur.execute(
                """INSERT INTO narrative_library (taxonomy_code, dimension, band, strength, action)
                     VALUES ('media_sales_v1', 'eq_identity', %s, %s, %s)
                ON CONFLICT (taxonomy_code, dimension, band) DO UPDATE
                  SET strength = EXCLUDED.strength, action = EXCLUDED.action""",
                (ident, payload["strength"], payload["action"]),
            )
        cur.execute("SELECT count(*) FROM narrative_library WHERE dimension='eq_identity'")
        n_eq = cur.fetchone()[0]

        print(f"archetypes (taxonomy 2) described: {n_arch}/8")
        print(f"eq_identity narratives:           {n_eq}/4")


if __name__ == "__main__":
    main()
