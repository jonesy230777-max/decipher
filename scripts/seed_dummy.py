"""Decipher dummy data seeder.

Per project rule 2, dummy rows are clearly marked: respondent emails end
``@demo.decipher.local``, every event payload carries ``{"dummy": true}``,
and labels include "DUMMY" where the operator might confuse them with real
data. Wipe with::

    docker exec -i decipher-db psql -U decipher -d decipher \
        -c "TRUNCATE respondents, teams, audits, audit_jobs, audit_scores,
                      archetype_assignments, band_classifications, responses,
                      reports, audit_score_vectors, cohort_snapshots,
                      pattern_library, promo_codes, bespoke_clients,
                      squarespace_exports, events_log, magic_link_tokens,
                      questions, audit_versions, brand_voice, industries,
                      archetype_taxonomies, archetypes RESTART IDENTITY CASCADE;"

Distributions match Steve's mock slide (spec §7B):
  Cognitive Empathy  Elite 18 / Performing 41 / Practising 28 / Developing 13
  EQ                 Elite 14 / Performing 39 / Practising 30 / Developing 17
  Pressure Composure Elite  9 / Performing 28 / Practising 39 / Developing 24
  Storytelling       Elite 11 / Performing 33 / Practising 35 / Developing 21
  Archetypes (taxonomy 1): Regulator 34 / Edge-Builder 27 / Observer 22 / Labeler 17
"""
from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta, timezone

from app.db import conn

random.seed(20260516)

# ---- distributions from Steve's slide -------------------------------------

DIM_DISTRIBUTIONS: dict[str, dict[str, int]] = {
    "cognitive_empathy":   {"elite": 18, "performing": 41, "practising": 28, "developing": 13},
    "eq":                  {"elite": 14, "performing": 39, "practising": 30, "developing": 17},
    "pressure_composure":  {"elite":  9, "performing": 28, "practising": 39, "developing": 24},
    "storytelling":        {"elite": 11, "performing": 33, "practising": 35, "developing": 21},
}
ARCHETYPE_COUNTS = {"regulator": 34, "edge_builder": 27, "observer": 22, "labeler": 17}

BAND_RANGES = {
    "developing": (0.00, 0.40),
    "practising": (0.40, 0.60),
    "performing": (0.60, 0.80),
    "elite":      (0.80, 1.00),
}
DIMENSIONS = list(DIM_DISTRIBUTIONS.keys())

FIRST_NAMES = [
    "Lina","Sam","Aisha","Jordan","Noah","Mia","Liam","Sara","Ethan","Zoe",
    "Aroha","Mateo","Ravi","Olivia","Jamal","Yuki","Anika","Lucas","Maya","Owen",
    "Priya","Nina","Felix","Kai","Aaliyah","Ben","Maeve","Theo","Sienna","Wren",
    "Ada","Cleo","Ezra","Ines","Jett","Kira","Leo","Maeko","Nova","Otis",
    "Pria","Quin","Rumi","Saoirse","Tariq","Uma","Vega","Wren","Xan","Yara",
]
LAST_NAMES = [
    "Patel","Nguyen","Chen","Lee","Singh","Khan","Brown","Smith","Wilson","Wright",
    "Kelly","Murphy","Williams","Davis","Walker","Hall","Young","King","Scott","Green",
    "Adams","Baker","Carter","Cooper","Diaz","Evans","Fisher","Garcia","Hughes","Ito",
    "Jensen","Kumar","Lopez","Morgan","Naidoo","Owens","Park","Quincy","Rao","Sato",
    "Tan","Ulrich","Vargas","Wong","Xu","Yamada","Zhao","Adeyemi","Begum","Cabrera",
]

# ---- helpers ---------------------------------------------------------------

def band_score(band: str) -> float:
    lo, hi = BAND_RANGES[band]
    # Stay 0.005 inside band edges so threshold rounding does not flip.
    return round(random.uniform(lo + 0.005, hi - 0.005), 4)


def assign_bands_for_team(n: int) -> dict[str, list[str]]:
    """Return per-dimension list of bands (length n) matching slide distribution."""
    out: dict[str, list[str]] = {}
    for dim, dist in DIM_DISTRIBUTIONS.items():
        bands: list[str] = []
        for band, count in dist.items():
            bands.extend([band] * count)
        if len(bands) < n:
            bands.extend(["practising"] * (n - len(bands)))
        bands = bands[:n]
        random.shuffle(bands)
        out[dim] = bands
    return out


def assign_archetypes(n: int) -> list[str]:
    out: list[str] = []
    for code, count in ARCHETYPE_COUNTS.items():
        out.extend([code] * count)
    if len(out) < n:
        out.extend(["regulator"] * (n - len(out)))
    out = out[:n]
    random.shuffle(out)
    return out


def _vec(scores: dict[str, float], extras: tuple[float, float, float, float]) -> str:
    """Format 8-dim pgvector literal: 4 dimensions + 4 derived."""
    arr = [scores[d] for d in DIMENSIONS] + list(extras)
    return "[" + ",".join(f"{v:.6f}" for v in arr) + "]"


def main() -> None:
    os.environ.setdefault("DECIPHER_DB_PORT", "55432")
    now = datetime.now(timezone.utc)

    with conn() as c:
        cur = c.cursor()

        # Re-baseline dummy rows (idempotent run). Wipe respondent / team /
        # audit-ish tables only; preserve seeded archetype taxonomies, archetypes,
        # industries, brand_voice, and the operator (Steve).
        cur.execute("DELETE FROM audit_jobs")
        cur.execute("DELETE FROM reports")
        cur.execute("DELETE FROM band_classifications")
        cur.execute("DELETE FROM archetype_assignments")
        cur.execute("DELETE FROM audit_score_vectors")
        cur.execute("DELETE FROM audit_scores")
        cur.execute("DELETE FROM responses")
        cur.execute("DELETE FROM audits")
        cur.execute("DELETE FROM cohort_snapshots")
        cur.execute("DELETE FROM pattern_library")
        cur.execute("DELETE FROM promo_codes")
        cur.execute("DELETE FROM squarespace_exports")
        cur.execute("DELETE FROM bespoke_clients WHERE client_name LIKE 'DUMMY%' OR client_name LIKE 'Demo%'")
        cur.execute("DELETE FROM respondents WHERE role = 'respondent' OR role = 'executive'")
        cur.execute("DELETE FROM teams")
        cur.execute("DELETE FROM questions")
        cur.execute("DELETE FROM events_log WHERE payload->>'dummy' = 'true' OR actor = 'seed_dummy'")
        # Reset the master audit version's industry/bespoke link too:
        cur.execute("UPDATE audit_versions SET industry_id = NULL, bespoke_client_id = NULL WHERE code='master_v1'")

        # ---- 47 placeholder questions on master_v1 ------------------------
        cur.execute("SELECT audit_version_id FROM audit_versions WHERE code='master_v1'")
        master_v_id = cur.fetchone()[0]
        per_dim = {
            "cognitive_empathy": 12,
            "eq": 12,
            "pressure_composure": 12,
            "storytelling": 11,  # 12+12+12+11 = 47
        }
        seq = 0
        question_ids: dict[str, list[int]] = {d: [] for d in DIMENSIONS}
        for dim, n_q in per_dim.items():
            for i in range(n_q):
                seq += 1
                archetype_signal = None
                # 3 archetype-signal questions (spec §4)
                if dim == "eq" and i in (0, 4, 8):
                    archetype_signal = ["regulator", "edge_builder", "observer"][i // 4]
                cur.execute(
                    """INSERT INTO questions
                           (audit_version_id, sequence, dimension, archetype_signal,
                            weight, prompt, response_type)
                       VALUES (%s,%s,%s,%s,%s,%s,'likert_5') RETURNING question_id""",
                    (master_v_id, seq, dim, archetype_signal, 1.0,
                     f"DUMMY Q{seq:02d} — {dim} prompt {i+1}"),
                )
                question_ids[dim].append(cur.fetchone()[0])

        # ---- 4 industries already seeded; add 2 bespoke clients ----------
        cur.execute(
            """INSERT INTO bespoke_clients
                   (client_name, custom_audit_version_id, brand_assets_json,
                    unique_url_slug, estimated_value, status)
               VALUES (%s,NULL,%s::jsonb,%s,%s,%s) RETURNING bespoke_client_id""",
            ("Demo: Atlas Media Group",
             json.dumps({"dummy": True, "primary_colour": "#0a3d62"}),
             "atlas-media-q3", 42000.0, "active"),
        )
        atlas_id = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO bespoke_clients
                   (client_name, custom_audit_version_id, brand_assets_json,
                    unique_url_slug, estimated_value, status)
               VALUES (%s,NULL,%s::jsonb,%s,%s,%s) RETURNING bespoke_client_id""",
            ("Demo: Northwind Pharma",
             json.dumps({"dummy": True, "primary_colour": "#3a5a40"}),
             "northwind-pharma-2026", 28500.0, "active"),
        )
        cur.execute(
            """INSERT INTO bespoke_clients
                   (client_name, custom_audit_version_id, brand_assets_json,
                    unique_url_slug, estimated_value, status)
               VALUES (%s,NULL,%s::jsonb,%s,%s,%s) RETURNING bespoke_client_id""",
            ("Demo: Crestline Auto",
             json.dumps({"dummy": True, "primary_colour": "#7c2d12"}),
             "crestline-auto-pilot", 18000.0, "draft"),
        )

        # ---- promo codes -------------------------------------------------
        promo_rows = [
            ("LAUNCH100", "free", 100.0, 25, "launch_campaign"),
            ("ATLAS50",   "discount", 50.0, 50, "atlas_partnership"),
            ("PHARMA25",  "discount", 25.0, 200, "pharma_outreach"),
            ("COMP-2026", "free", 100.0, 10, "comped_individuals"),
            ("REAUDIT",   "discount", 30.0, 1000, "reaudit_repeat"),
        ]
        for code, t, pct, n, src in promo_rows:
            cur.execute(
                """INSERT INTO promo_codes (code, code_type, discount_pct,
                                            uses_remaining, valid_until, source_campaign)
                   VALUES (%s,%s,%s,%s, now() + interval '180 days', %s)""",
                (code, t, pct, n, src),
            )

        # ---- 1 executive team (NSW Sales Team) ---------------------------
        cur.execute(
            """INSERT INTO teams (name, organisation, role_label)
               VALUES (%s,%s,%s) RETURNING team_id""",
            ("NSW Sales Team", "Demo: Atlas Media Group", "Head of Sales"),
        )
        team_id = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO respondents (email, name, company, industry, role,
                                        team_id, consent_share_individual)
               VALUES (%s,%s,%s,%s,'executive',%s,FALSE) RETURNING respondent_id""",
            ("alex.exec@demo.decipher.local", "Alex Carmichael",
             "Demo: Atlas Media Group", "media", team_id),
        )
        exec_id = cur.fetchone()[0]

        # ---- 100 respondents in the team --------------------------------
        n_team = 100
        bands_per_dim = assign_bands_for_team(n_team)
        archetypes_seq = assign_archetypes(n_team)
        cur.execute("SELECT archetype_id, code FROM archetypes WHERE taxonomy_id = 1")
        archetype_map = {code: aid for aid, code in cur.fetchall()}
        cur.execute("SELECT industry_id, code FROM industries")
        industry_map = {code: iid for iid, code in cur.fetchall()}
        industries_pool = ["media", "media", "media", "tech", "pharma"]  # mostly media

        for i in range(n_team):
            fn = FIRST_NAMES[i % len(FIRST_NAMES)]
            ln = LAST_NAMES[(i * 7) % len(LAST_NAMES)]
            email = f"rep{i+1:03d}.{fn.lower()}.{ln.lower()}@demo.decipher.local"
            industry = industries_pool[i % len(industries_pool)]
            cur.execute(
                """INSERT INTO respondents (email, name, company, industry, role,
                                            team_id, consent_share_individual)
                   VALUES (%s,%s,%s,%s,'respondent',%s,%s) RETURNING respondent_id""",
                (email, f"{fn} {ln}", "Demo: Atlas Media Group", industry,
                 team_id, i % 7 == 0),  # ~14% consent
            )
            rid = cur.fetchone()[0]

            # Build the audit
            started = now - timedelta(days=random.randint(2, 28),
                                      hours=random.randint(0, 23))
            completed = started + timedelta(minutes=random.randint(7, 18))
            status = random.choices(
                ["reported", "scored", "completed", "in_progress"],
                weights=[80, 8, 5, 7],
            )[0]

            cur.execute(
                """INSERT INTO audits (respondent_id, audit_version_id, status,
                                       started_at, completed_at, promo_code)
                   VALUES (%s,%s,%s,%s,%s,%s) RETURNING audit_id""",
                (rid, master_v_id, status, started,
                 completed if status != "in_progress" else None,
                 random.choice([None, None, None, "LAUNCH100"])),
            )
            audit_id = cur.fetchone()[0]

            if status == "in_progress":
                # only some responses filled, no scoring
                for dim in DIMENSIONS:
                    for qid in question_ids[dim][:random.randint(2, 8)]:
                        cur.execute(
                            """INSERT INTO responses (audit_id, question_id,
                                                      answer_value, response_ms)
                               VALUES (%s,%s,%s,%s)""",
                            (audit_id, qid, random.randint(1, 5),
                             random.randint(2500, 18000)),
                        )
                continue

            # Completed / scored / reported: all 47 responses + scores
            for dim in DIMENSIONS:
                for qid in question_ids[dim]:
                    cur.execute(
                        """INSERT INTO responses (audit_id, question_id,
                                                  answer_value, response_ms)
                           VALUES (%s,%s,%s,%s)""",
                        (audit_id, qid, random.randint(1, 5),
                         random.randint(2500, 18000)),
                    )

            scores = {dim: band_score(bands_per_dim[dim][i]) for dim in DIMENSIONS}
            cur.execute(
                """INSERT INTO audit_scores
                       (audit_id, cognitive_empathy, eq, pressure_composure,
                        storytelling, raw_band_json, computed_at)
                   VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s)""",
                (audit_id,
                 scores["cognitive_empathy"], scores["eq"],
                 scores["pressure_composure"], scores["storytelling"],
                 json.dumps({d: bands_per_dim[d][i] for d in DIMENSIONS}),
                 completed),
            )
            for dim in DIMENSIONS:
                cur.execute(
                    """INSERT INTO band_classifications (audit_id, dimension, band, score)
                       VALUES (%s,%s,%s,%s)""",
                    (audit_id, dim, bands_per_dim[dim][i], scores[dim]),
                )
            arc_code = archetypes_seq[i]
            cur.execute(
                """INSERT INTO archetype_assignments
                       (audit_id, taxonomy_id, archetype_id, confidence,
                        tiebreak_applied, assigned_at)
                   VALUES (%s,1,%s,%s,%s,%s)""",
                (audit_id, archetype_map[arc_code],
                 round(random.uniform(0.62, 0.96), 3),
                 random.random() < 0.05, completed),
            )
            cur.execute(
                """INSERT INTO audit_score_vectors (audit_id, vec)
                   VALUES (%s, %s::vector)""",
                (audit_id, _vec(scores, (
                    round(random.uniform(0.6, 0.95), 3),  # consistency
                    round(random.uniform(0.1, 0.8), 3),  # response_time_variance
                    round(random.uniform(0.2, 0.7), 3),  # extremity
                    round(random.uniform(0.3, 0.8), 3),  # sentiment
                ))),
            )

            if status == "reported":
                pdf_path = f"/data/reports/dummy_audit_{audit_id}_v1.pdf"
                cur.execute(
                    """INSERT INTO reports (audit_id, pdf_path, generated_at,
                                            version, claude_model_used,
                                            input_tokens, output_tokens, cost_usd)
                       VALUES (%s,%s,%s,1,'claude-opus-4-7',%s,%s,%s)""",
                    (audit_id, pdf_path, completed + timedelta(minutes=1),
                     random.randint(3500, 4800),
                     random.randint(1100, 1900),
                     round(random.uniform(0.07, 0.18), 4)),
                )

        # ---- 25 standalone respondents (no team) -------------------------
        for i in range(25):
            fn = FIRST_NAMES[(i * 3) % len(FIRST_NAMES)]
            ln = LAST_NAMES[(i * 11) % len(LAST_NAMES)]
            email = f"solo{i+1:03d}@demo.decipher.local"
            cur.execute(
                """INSERT INTO respondents (email, name, industry, role)
                   VALUES (%s,%s,%s,'respondent') RETURNING respondent_id""",
                (email, f"{fn} {ln}", random.choice(["tech","media","automotive","pharma"])),
            )
            rid = cur.fetchone()[0]
            started = now - timedelta(days=random.randint(0, 14))
            completed = started + timedelta(minutes=random.randint(6, 15))
            cur.execute(
                """INSERT INTO audits (respondent_id, audit_version_id, status,
                                       started_at, completed_at)
                   VALUES (%s,%s,'reported',%s,%s) RETURNING audit_id""",
                (rid, master_v_id, started, completed),
            )
            audit_id = cur.fetchone()[0]
            for dim in DIMENSIONS:
                for qid in question_ids[dim]:
                    cur.execute(
                        """INSERT INTO responses (audit_id, question_id,
                                                  answer_value, response_ms)
                           VALUES (%s,%s,%s,%s)""",
                        (audit_id, qid, random.randint(1, 5),
                         random.randint(2500, 18000)),
                    )
            scores = {d: round(random.uniform(0.35, 0.92), 4) for d in DIMENSIONS}
            cur.execute(
                """INSERT INTO audit_scores
                       (audit_id, cognitive_empathy, eq, pressure_composure,
                        storytelling, raw_band_json, computed_at)
                   VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s)""",
                (audit_id,
                 scores["cognitive_empathy"], scores["eq"],
                 scores["pressure_composure"], scores["storytelling"],
                 json.dumps({d: "performing" for d in DIMENSIONS}),
                 completed),
            )
            for dim in DIMENSIONS:
                s = scores[dim]
                band = ("elite" if s >= 0.8 else "performing" if s >= 0.6
                        else "practising" if s >= 0.4 else "developing")
                cur.execute(
                    """INSERT INTO band_classifications (audit_id, dimension, band, score)
                       VALUES (%s,%s,%s,%s)""",
                    (audit_id, dim, band, s),
                )
            arc_code = random.choice(list(archetype_map.keys()))
            cur.execute(
                """INSERT INTO archetype_assignments
                       (audit_id, taxonomy_id, archetype_id, confidence, assigned_at)
                   VALUES (%s,1,%s,%s,%s)""",
                (audit_id, archetype_map[arc_code],
                 round(random.uniform(0.55, 0.93), 3), completed),
            )
            cur.execute(
                """INSERT INTO audit_score_vectors (audit_id, vec)
                   VALUES (%s, %s::vector)""",
                (audit_id, _vec(scores,
                    (round(random.uniform(0.5, 0.95), 3),
                     round(random.uniform(0.1, 0.8), 3),
                     round(random.uniform(0.2, 0.7), 3),
                     round(random.uniform(0.3, 0.8), 3)))),
            )

        # ---- cohort snapshots (last 14 days) ----------------------------
        for d in range(14):
            day = (now - timedelta(days=13 - d)).date()
            cur.execute(
                """SELECT count(*),
                          avg(cognitive_empathy), avg(eq),
                          avg(pressure_composure), avg(storytelling)
                     FROM audit_scores s
                     JOIN audits a USING (audit_id)
                    WHERE a.completed_at::date <= %s""",
                (day,),
            )
            n, ce, eq, pc, st = cur.fetchone()
            cur.execute(
                """INSERT INTO cohort_snapshots
                       (snapshot_date, total_audits,
                        mean_cognitive_empathy, mean_eq,
                        mean_pressure_composure, mean_storytelling,
                        band_distribution_json, archetype_distribution_json)
                   VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                   ON CONFLICT (snapshot_date) DO UPDATE
                     SET total_audits = EXCLUDED.total_audits,
                         mean_cognitive_empathy = EXCLUDED.mean_cognitive_empathy,
                         mean_eq = EXCLUDED.mean_eq,
                         mean_pressure_composure = EXCLUDED.mean_pressure_composure,
                         mean_storytelling = EXCLUDED.mean_storytelling""",
                (day, int(n or 0),
                 float(ce or 0), float(eq or 0),
                 float(pc or 0), float(st or 0),
                 json.dumps({"dummy": True}),
                 json.dumps({"dummy": True})),
            )

        # ---- pattern_library (4 DOUBT-passed + 6 candidates) -------------
        patterns = [
            ("Media + low EQ → low storytelling",
             {"all": [{"industry":"media"},
                      {"dim":"eq","op":"<","val":0.5},
                      {"dim":"storytelling","op":"<","val":0.5}]},
             0.78, 92, 0.0008, 0.71, True),
            ("Low pressure composure + low cognitive empathy → Developing storytelling",
             {"all": [{"dim":"pressure_composure","op":"<","val":0.5},
                      {"dim":"cognitive_empathy","op":"<","val":0.5},
                      {"dim":"storytelling","band":"developing"}]},
             0.84, 47, 0.0002, 0.79, True),
            ("Elite cognitive empathy + Elite EQ → Edge-Builder archetype",
             {"all": [{"dim":"cognitive_empathy","band":"elite"},
                      {"dim":"eq","band":"elite"},
                      {"archetype":"edge_builder"}]},
             0.71, 38, 0.0014, 0.66, True),
            ("Tech industry + high storytelling → Observer archetype",
             {"all": [{"industry":"tech"},
                      {"dim":"storytelling","op":">","val":0.7},
                      {"archetype":"observer"}]},
             0.69, 31, 0.0033, 0.61, True),
            ("Practising EQ + low pressure composure → at-risk under stress",
             {"all": [{"dim":"eq","band":"practising"},
                      {"dim":"pressure_composure","op":"<","val":0.45}]},
             0.62, 56, 0.012, 0.49, False),
            ("Storytelling Elite + cognitive empathy Performing+ → Trust Architect (taxonomy 2)",
             {"all": [{"dim":"storytelling","band":"elite"},
                      {"dim":"cognitive_empathy","op":">=","val":0.6}]},
             0.58, 22, 0.041, 0.41, False),
        ]
        for name, cond, hit, n, p, oos, passed in patterns:
            cur.execute(
                """INSERT INTO pattern_library
                       (name, conditions_json, evidence_json, hit_rate,
                        n_observations, bh_p_value, oos_hit_rate, robust,
                        doubt_passed)
                   VALUES (%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s)""",
                (name, json.dumps(cond),
                 json.dumps({"dummy": True, "method": "weekly grid"}),
                 hit, n, p, oos, passed, passed),
            )

        # ---- squarespace exports (3 historical) --------------------------
        os.makedirs("/Users/max/Documents/Decipher/_squarespace_exports", exist_ok=True)
        for i, days_ago in enumerate([7, 4, 1]):
            ts = now - timedelta(days=days_ago)
            bundle = f"/data/exports/squarespace_export_{ts.strftime('%Y-%m-%d')}.zip"
            cur.execute(
                """INSERT INTO squarespace_exports
                       (generated_at, bundle_path, file_count, size_bytes,
                        summary, cost_usd)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (ts, bundle, 47 + i,
                 1_200_000 + i * 50_000,
                 f"DUMMY export v{i+1}: pages + seo + design + audit_app + pdf_report + voice",
                 round(random.uniform(0.18, 0.32), 4)),
            )

        # ---- events_log (~80 entries spread across last 72h) -------------
        actions = [
            ("info",    "audit.started",        "audit"),
            ("info",    "audit.completed",      "audit"),
            ("info",    "audit.scored",         "audit"),
            ("info",    "report.generated",     "report"),
            ("info",    "email.sent",           "report"),
            ("info",    "claude.api_call",      "report"),
            ("info",    "promo.redeemed",       "promo"),
            ("info",    "stripe.checkout.completed", "payment"),
            ("info",    "squarespace.exported", "export"),
            ("warning", "quality_gate.flagged_straight_liner", "audit"),
            ("warning", "archetype.tiebreak_applied", "audit"),
            ("error",   "email.bounce",         "report"),
        ]
        for _ in range(80):
            sev, action, kind = random.choice(actions)
            occurred = now - timedelta(
                hours=random.uniform(0, 72),
            )
            payload = {"dummy": True, "kind": kind}
            if action == "claude.api_call":
                payload.update({
                    "model": random.choice(["claude-opus-4-7", "claude-haiku-4-5-20251001"]),
                    "input_tokens": random.randint(800, 4500),
                    "output_tokens": random.randint(250, 1800),
                    "cost_usd": round(random.uniform(0.005, 0.12), 4),
                })
            cur.execute(
                """INSERT INTO events_log (occurred_at, actor, action, severity,
                                           subject_id, payload)
                   VALUES (%s, 'seed_dummy', %s, %s, %s, %s::jsonb)""",
                (occurred, action, sev,
                 f"{kind}-{random.randint(1, 999):03d}",
                 json.dumps(payload)),
            )

        # ---- final counts -------------------------------------------------
        cur.execute("SELECT count(*) FROM respondents WHERE role='respondent'"); r = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM audits"); a = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM reports"); rep = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM pattern_library WHERE doubt_passed=TRUE"); p_ok = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM teams"); t = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM bespoke_clients"); b = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM promo_codes"); pc = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM squarespace_exports"); sx = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM events_log"); e = cur.fetchone()[0]

    print(f"Seeded:")
    print(f"  respondents:           {r}")
    print(f"  audits:                {a}")
    print(f"  reports:               {rep}")
    print(f"  teams:                 {t}")
    print(f"  bespoke_clients:       {b}")
    print(f"  promo_codes:           {pc}")
    print(f"  pattern_library OK:    {p_ok}")
    print(f"  squarespace_exports:   {sx}")
    print(f"  events_log:            {e}")


if __name__ == "__main__":
    main()
