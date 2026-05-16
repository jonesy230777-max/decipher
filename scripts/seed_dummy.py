"""Decipher dummy data seeder. Multi-company / multi-team build.

Per project rule 2, dummy rows are marked: respondent emails end
``@demo.decipher.local``, event payloads carry ``{"dummy": true}``, labels
include "Demo" where they could be confused with real clients.

Companies and their teams (CLAUDE.md role taxonomy + sales-org realism):

    Demo: Atlas Media Group
      NSW Sales Team               100 reps   strong  (Owen Wright, Sales Director)
      VIC Sales Team                60 reps   mid
      Atlas Media L&D Pilot         20 reps   mixed

    Demo: Northwind Pharma
      Northwind Pharma Sales        40 reps   at-risk
      Northwind Hospital Sales      28 reps   mid
      Northwind Retail Pharmacy     22 reps   mid

    Demo: Crestline Auto
      Crestline Auto Field          25 reps   weak
      Crestline Dealer Network      30 reps   mid
      Crestline Fleet & EV          18 reps   strong

    Demo: Pearl Tech Group
      Pearl Enterprise Sales        35 reps   strong
      Pearl SMB Sales               24 reps   mid

Strict scoping: every respondent has exactly one team_id (or NULL for
standalones). Endpoints filter on team_id / company_id; zero data bleeds
between teams or companies.
"""
from __future__ import annotations

import json
import os
import random
from datetime import datetime, timedelta, timezone

from app.db import conn

random.seed(20260516)

BAND_RANGES = {
    "developing": (0.00, 0.40),
    "practising": (0.40, 0.60),
    "performing": (0.60, 0.80),
    "elite":      (0.80, 1.00),
}
DIMENSIONS = ["cognitive_empathy", "eq", "pressure_composure", "storytelling"]
ARCHETYPE_CODES = ["regulator", "edge_builder", "observer", "labeler"]

# Per-team plan. Each entry: dim distribution (band counts sum to n_reps),
# archetype distribution, share of in-progress (vs reported).
TEAM_PLAN = [
    {
        "name": "NSW Sales Team",
        "organisation": "Demo: Atlas Media Group",
        "role_label": "Sales Director",
        "industry": "media",
        "n_reps": 100,
        "dim_distribution": {
            "cognitive_empathy":  {"elite": 18, "performing": 41, "practising": 28, "developing": 13},
            "eq":                 {"elite": 14, "performing": 39, "practising": 30, "developing": 17},
            "pressure_composure": {"elite":  9, "performing": 28, "practising": 39, "developing": 24},
            "storytelling":       {"elite": 11, "performing": 33, "practising": 35, "developing": 21},
        },
        "archetype_counts": {"regulator": 34, "edge_builder": 27, "observer": 22, "labeler": 17},
        "exec_email": "owen.wright@demo.decipher.local",
        "exec_name": "Owen Wright",
    },
    {
        "name": "VIC Sales Team",
        "organisation": "Demo: Atlas Media Group",
        "role_label": "Sales Director",
        "industry": "media",
        "n_reps": 60,
        "dim_distribution": {
            "cognitive_empathy":  {"elite":  8, "performing": 22, "practising": 22, "developing":  8},
            "eq":                 {"elite":  7, "performing": 20, "practising": 23, "developing": 10},
            "pressure_composure": {"elite":  5, "performing": 18, "practising": 25, "developing": 12},
            "storytelling":       {"elite":  6, "performing": 19, "practising": 24, "developing": 11},
        },
        "archetype_counts": {"regulator": 20, "edge_builder": 16, "observer": 14, "labeler": 10},
        "exec_email": "mei.exec@demo.decipher.local",
        "exec_name": "Mei Bennett",
    },
    {
        "name": "Northwind Pharma Sales",
        "organisation": "Demo: Northwind Pharma",
        "role_label": "VP Sales",
        "industry": "pharma",
        "n_reps": 40,
        "dim_distribution": {
            "cognitive_empathy":  {"elite":  2, "performing":  9, "practising": 17, "developing": 12},
            "eq":                 {"elite":  3, "performing": 10, "practising": 18, "developing":  9},
            "pressure_composure": {"elite":  1, "performing":  7, "practising": 18, "developing": 14},
            "storytelling":       {"elite":  2, "performing":  8, "practising": 18, "developing": 12},
        },
        "archetype_counts": {"regulator": 16, "edge_builder":  8, "observer": 10, "labeler":  6},
        "exec_email": "tara.exec@demo.decipher.local",
        "exec_name": "Tara Holm",
    },
    {
        "name": "Northwind Hospital Sales",
        "organisation": "Demo: Northwind Pharma",
        "role_label": "Sales Director",
        "industry": "pharma",
        "n_reps": 28,
        "dim_distribution": {
            "cognitive_empathy":  {"elite":  3, "performing": 10, "practising": 10, "developing":  5},
            "eq":                 {"elite":  4, "performing": 11, "practising":  9, "developing":  4},
            "pressure_composure": {"elite":  2, "performing":  9, "practising": 11, "developing":  6},
            "storytelling":       {"elite":  3, "performing":  9, "practising": 11, "developing":  5},
        },
        "archetype_counts": {"regulator": 10, "edge_builder":  7, "observer":  7, "labeler":  4},
        "exec_email": "ravi.hospital@demo.decipher.local",
        "exec_name": "Ravi Subramanian",
    },
    {
        "name": "Northwind Retail Pharmacy",
        "organisation": "Demo: Northwind Pharma",
        "role_label": "Sales Director",
        "industry": "pharma",
        "n_reps": 22,
        "dim_distribution": {
            "cognitive_empathy":  {"elite":  2, "performing":  7, "practising":  9, "developing":  4},
            "eq":                 {"elite":  2, "performing":  8, "practising":  8, "developing":  4},
            "pressure_composure": {"elite":  1, "performing":  6, "practising":  9, "developing":  6},
            "storytelling":       {"elite":  2, "performing":  7, "practising":  9, "developing":  4},
        },
        "archetype_counts": {"regulator":  7, "edge_builder":  5, "observer":  6, "labeler":  4},
        "exec_email": "lina.retail@demo.decipher.local",
        "exec_name": "Lina Ortega",
    },
    {
        "name": "Crestline Auto Field",
        "organisation": "Demo: Crestline Auto",
        "role_label": "Sales Director",
        "industry": "automotive",
        "n_reps": 25,
        "dim_distribution": {
            "cognitive_empathy":  {"elite":  1, "performing":  5, "practising": 10, "developing":  9},
            "eq":                 {"elite":  1, "performing":  6, "practising": 10, "developing":  8},
            "pressure_composure": {"elite":  0, "performing":  4, "practising": 11, "developing": 10},
            "storytelling":       {"elite":  1, "performing":  5, "practising": 10, "developing":  9},
        },
        "archetype_counts": {"regulator":  8, "edge_builder":  6, "observer":  7, "labeler":  4},
        "exec_email": "ben.exec@demo.decipher.local",
        "exec_name": "Ben Caruso",
    },
    {
        "name": "Crestline Dealer Network",
        "organisation": "Demo: Crestline Auto",
        "role_label": "Sales Director",
        "industry": "automotive",
        "n_reps": 30,
        "dim_distribution": {
            "cognitive_empathy":  {"elite":  3, "performing": 11, "practising": 11, "developing":  5},
            "eq":                 {"elite":  4, "performing": 11, "practising": 10, "developing":  5},
            "pressure_composure": {"elite":  2, "performing":  9, "practising": 12, "developing":  7},
            "storytelling":       {"elite":  3, "performing": 10, "practising": 12, "developing":  5},
        },
        "archetype_counts": {"regulator": 11, "edge_builder":  8, "observer":  7, "labeler":  4},
        "exec_email": "kai.dealer@demo.decipher.local",
        "exec_name": "Kai Andersen",
    },
    {
        "name": "Crestline Fleet & EV",
        "organisation": "Demo: Crestline Auto",
        "role_label": "Sales Director",
        "industry": "automotive",
        "n_reps": 18,
        "dim_distribution": {
            "cognitive_empathy":  {"elite":  4, "performing":  8, "practising":  5, "developing":  1},
            "eq":                 {"elite":  3, "performing":  8, "practising":  6, "developing":  1},
            "pressure_composure": {"elite":  2, "performing":  7, "practising":  7, "developing":  2},
            "storytelling":       {"elite":  3, "performing":  8, "practising":  6, "developing":  1},
        },
        "archetype_counts": {"regulator":  4, "edge_builder":  7, "observer":  5, "labeler":  2},
        "exec_email": "nova.ev@demo.decipher.local",
        "exec_name": "Nova Petrakis",
    },
    {
        "name": "Pearl Enterprise Sales",
        "organisation": "Demo: Pearl Tech Group",
        "role_label": "Sales Director",
        "industry": "tech",
        "n_reps": 35,
        "dim_distribution": {
            "cognitive_empathy":  {"elite":  8, "performing": 16, "practising":  8, "developing":  3},
            "eq":                 {"elite":  7, "performing": 15, "practising":  9, "developing":  4},
            "pressure_composure": {"elite":  5, "performing": 13, "practising": 11, "developing":  6},
            "storytelling":       {"elite":  6, "performing": 14, "practising": 10, "developing":  5},
        },
        "archetype_counts": {"regulator": 10, "edge_builder": 13, "observer":  8, "labeler":  4},
        "exec_email": "felix.enterprise@demo.decipher.local",
        "exec_name": "Felix Marchetti",
    },
    {
        "name": "Pearl SMB Sales",
        "organisation": "Demo: Pearl Tech Group",
        "role_label": "Sales Director",
        "industry": "tech",
        "n_reps": 24,
        "dim_distribution": {
            "cognitive_empathy":  {"elite":  3, "performing":  9, "practising":  9, "developing":  3},
            "eq":                 {"elite":  3, "performing": 10, "practising":  8, "developing":  3},
            "pressure_composure": {"elite":  2, "performing":  8, "practising": 10, "developing":  4},
            "storytelling":       {"elite":  3, "performing":  9, "practising":  9, "developing":  3},
        },
        "archetype_counts": {"regulator":  8, "edge_builder":  7, "observer":  6, "labeler":  3},
        "exec_email": "maya.smb@demo.decipher.local",
        "exec_name": "Maya Lindqvist",
    },
    {
        "name": "Atlas Media L&D Pilot",
        "organisation": "Demo: Atlas Media Group",
        "role_label": "Learning & Development",
        "industry": "media",
        "n_reps": 20,
        "dim_distribution": {
            "cognitive_empathy":  {"elite":  4, "performing":  8, "practising":  6, "developing":  2},
            "eq":                 {"elite":  3, "performing":  7, "practising":  7, "developing":  3},
            "pressure_composure": {"elite":  2, "performing":  6, "practising":  8, "developing":  4},
            "storytelling":       {"elite":  3, "performing":  7, "practising":  7, "developing":  3},
        },
        "archetype_counts": {"regulator":  6, "edge_builder":  6, "observer":  5, "labeler":  3},
        "exec_email": "priya.exec@demo.decipher.local",
        "exec_name": "Priya Ranjan",
        "exec_role": "learning_development",
    },
]

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


def band_score(band: str) -> float:
    lo, hi = BAND_RANGES[band]
    return round(random.uniform(lo + 0.005, hi - 0.005), 4)


def expand_dist(dist: dict[str, int], n: int) -> list[str]:
    out: list[str] = []
    for band, c in dist.items():
        out.extend([band] * c)
    if len(out) < n:
        out.extend(["practising"] * (n - len(out)))
    out = out[:n]
    random.shuffle(out)
    return out


def _vec(scores: dict[str, float]) -> str:
    arr = [scores[d] for d in DIMENSIONS] + [
        round(random.uniform(0.6, 0.95), 3),  # consistency
        round(random.uniform(0.1, 0.8), 3),  # response_time_variance
        round(random.uniform(0.2, 0.7), 3),  # extremity
        round(random.uniform(0.3, 0.8), 3),  # sentiment
    ]
    return "[" + ",".join(f"{v:.6f}" for v in arr) + "]"


def main() -> None:
    os.environ.setdefault("DECIPHER_DB_PORT", "55432")
    now = datetime.now(timezone.utc)

    with conn() as c:
        cur = c.cursor()

        # Wipe dependent rows then teams + sales_person + sales_director.
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
        cur.execute("DELETE FROM bespoke_clients WHERE client_name LIKE 'Demo%'")
        cur.execute(
            "DELETE FROM respondents WHERE role IN "
            "('sales_person','sales_director','hr','learning_development','ceo')"
        )
        cur.execute("DELETE FROM teams")
        cur.execute("DELETE FROM companies")
        cur.execute("DELETE FROM questions")
        # Reset sequences so team_id and other IDs start from 1 for stable URLs.
        cur.execute("ALTER SEQUENCE teams_team_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE companies_company_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE audits_audit_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE bespoke_clients_bespoke_client_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE squarespace_exports_export_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE pattern_library_pattern_id_seq RESTART WITH 1")
        cur.execute("ALTER SEQUENCE questions_question_id_seq RESTART WITH 1")

        # Companies first (parent of teams + respondents).
        cur.execute("INSERT INTO companies (name, industry) VALUES ('Demo: Atlas Media Group', 'media') RETURNING company_id")
        company_atlas = cur.fetchone()[0]
        cur.execute("INSERT INTO companies (name, industry) VALUES ('Demo: Northwind Pharma', 'pharma') RETURNING company_id")
        company_northwind = cur.fetchone()[0]
        cur.execute("INSERT INTO companies (name, industry) VALUES ('Demo: Crestline Auto', 'automotive') RETURNING company_id")
        company_crestline = cur.fetchone()[0]
        cur.execute("INSERT INTO companies (name, industry) VALUES ('Demo: Pearl Tech Group', 'tech') RETURNING company_id")
        company_pearl = cur.fetchone()[0]
        company_by_name = {
            "Demo: Atlas Media Group": company_atlas,
            "Demo: Northwind Pharma":  company_northwind,
            "Demo: Crestline Auto":    company_crestline,
            "Demo: Pearl Tech Group":  company_pearl,
        }
        cur.execute("DELETE FROM events_log WHERE payload->>'dummy' = 'true' OR actor = 'seed_dummy'")
        cur.execute(
            "UPDATE audit_versions SET industry_id = NULL, bespoke_client_id = NULL "
            "WHERE code='master_v1'"
        )

        # 47 questions on master_v1
        cur.execute("SELECT audit_version_id FROM audit_versions WHERE code='master_v1'")
        master_v_id = cur.fetchone()[0]
        per_dim = {"cognitive_empathy": 12, "eq": 12, "pressure_composure": 12, "storytelling": 11}
        seq = 0
        question_ids: dict[str, list[int]] = {d: [] for d in DIMENSIONS}
        for dim, n_q in per_dim.items():
            for i in range(n_q):
                seq += 1
                arch_signal = None
                if dim == "eq" and i in (0, 4, 8):
                    arch_signal = ["regulator", "edge_builder", "observer"][i // 4]
                cur.execute(
                    """INSERT INTO questions
                           (audit_version_id, sequence, dimension, archetype_signal,
                            weight, prompt, response_type)
                       VALUES (%s,%s,%s,%s,%s,%s,'likert_5') RETURNING question_id""",
                    (master_v_id, seq, dim, arch_signal, 1.0,
                     f"Demo question {seq:02d}: {dim} prompt {i+1}"),
                )
                question_ids[dim].append(cur.fetchone()[0])

        # bespoke clients
        bespoke_rows = [
            ("Demo: Atlas Media Group", "atlas-media-q3", 42000.0, "active", "#0a3d62"),
            ("Demo: Northwind Pharma",  "northwind-pharma-2026", 28500.0, "active", "#3a5a40"),
            ("Demo: Crestline Auto",    "crestline-auto-pilot", 18000.0, "draft",  "#7c2d12"),
        ]
        for name, slug, val, status, colour in bespoke_rows:
            cur.execute(
                """INSERT INTO bespoke_clients
                       (client_name, custom_audit_version_id, brand_assets_json,
                        unique_url_slug, estimated_value, status)
                   VALUES (%s,NULL,%s::jsonb,%s,%s,%s)""",
                (name, json.dumps({"dummy": True, "primary_colour": colour}),
                 slug, val, status),
            )

        # promo codes
        for code, t, pct, n, src in [
            ("LAUNCH100", "free", 100.0, 25, "launch_campaign"),
            ("ATLAS50",   "discount", 50.0, 50, "atlas_partnership"),
            ("PHARMA25",  "discount", 25.0, 200, "pharma_outreach"),
            ("COMP-2026", "free", 100.0, 10, "comped_individuals"),
            ("REAUDIT",   "discount", 30.0, 1000, "reaudit_repeat"),
        ]:
            cur.execute(
                """INSERT INTO promo_codes
                       (code, code_type, discount_pct, uses_remaining,
                        valid_until, source_campaign)
                   VALUES (%s,%s,%s,%s, now() + interval '180 days', %s)""",
                (code, t, pct, n, src),
            )

        cur.execute("SELECT archetype_id, code FROM archetypes WHERE taxonomy_id = 1")
        archetype_map = {code: aid for aid, code in cur.fetchall()}

        # Seed each team.
        for team_idx, plan in enumerate(TEAM_PLAN, start=1):
            cid = company_by_name[plan["organisation"]]
            cur.execute(
                """INSERT INTO teams (name, company_id, organisation, role_label)
                   VALUES (%s,%s,%s,%s) RETURNING team_id""",
                (plan["name"], cid, plan["organisation"], plan["role_label"]),
            )
            team_id = cur.fetchone()[0]

            # Executive (sales director or L&D head per role_label hint)
            exec_role = plan.get("exec_role", "sales_director")
            cur.execute(
                """INSERT INTO respondents
                       (email, name, company, industry, role, team_id, company_id,
                        consent_share_individual)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,FALSE)""",
                (plan["exec_email"], plan["exec_name"], plan["organisation"],
                 plan["industry"], exec_role, team_id, cid),
            )

            n = plan["n_reps"]
            bands_per_dim = {
                dim: expand_dist(plan["dim_distribution"][dim], n) for dim in DIMENSIONS
            }
            archetypes_seq: list[str] = []
            for code, cnt in plan["archetype_counts"].items():
                archetypes_seq.extend([code] * cnt)
            if len(archetypes_seq) < n:
                archetypes_seq.extend(["regulator"] * (n - len(archetypes_seq)))
            archetypes_seq = archetypes_seq[:n]
            random.shuffle(archetypes_seq)

            for i in range(n):
                fn = FIRST_NAMES[(i + team_idx * 3) % len(FIRST_NAMES)]
                ln = LAST_NAMES[(i * 7 + team_idx) % len(LAST_NAMES)]
                slug = plan["name"].lower().replace(" ", "")[:6]
                email = f"{slug}-rep{i+1:03d}.{fn.lower()}.{ln.lower()}@demo.decipher.local"
                cur.execute(
                    """INSERT INTO respondents
                           (email, name, company, industry, role, team_id, company_id,
                            consent_share_individual)
                       VALUES (%s,%s,%s,%s,'sales_person',%s,%s,%s)
                       RETURNING respondent_id""",
                    (email, f"{fn} {ln}", plan["organisation"], plan["industry"],
                     team_id, cid, i % 7 == 0),
                )
                rid = cur.fetchone()[0]

                started = now - timedelta(
                    days=random.randint(0, 28),
                    hours=random.randint(0, 23),
                )
                completed = started + timedelta(minutes=random.randint(7, 18))
                status = random.choices(
                    ["reported", "scored", "completed", "in_progress"],
                    weights=[82, 7, 5, 6],
                )[0]
                cur.execute(
                    """INSERT INTO audits
                           (respondent_id, audit_version_id, status,
                            started_at, completed_at, promo_code)
                       VALUES (%s,%s,%s,%s,%s,%s) RETURNING audit_id""",
                    (rid, master_v_id, status, started,
                     completed if status != "in_progress" else None,
                     random.choice([None, None, None, "LAUNCH100"])),
                )
                audit_id = cur.fetchone()[0]

                if status == "in_progress":
                    for dim in DIMENSIONS:
                        for qid in question_ids[dim][:random.randint(2, 8)]:
                            cur.execute(
                                """INSERT INTO responses
                                       (audit_id, question_id, answer_value, response_ms)
                                   VALUES (%s,%s,%s,%s)""",
                                (audit_id, qid, random.randint(1, 5),
                                 random.randint(2500, 18000)),
                            )
                    continue

                for dim in DIMENSIONS:
                    for qid in question_ids[dim]:
                        cur.execute(
                            """INSERT INTO responses
                                   (audit_id, question_id, answer_value, response_ms)
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
                        """INSERT INTO band_classifications
                               (audit_id, dimension, band, score)
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
                    "INSERT INTO audit_score_vectors (audit_id, vec) VALUES (%s, %s::vector)",
                    (audit_id, _vec(scores)),
                )
                if status == "reported":
                    pdf_path = f"/data/reports/dummy_audit_{audit_id}_v1.pdf"
                    cur.execute(
                        """INSERT INTO reports
                               (audit_id, pdf_path, generated_at, version,
                                claude_model_used, input_tokens, output_tokens, cost_usd)
                           VALUES (%s,%s,%s,1,'claude-opus-4-7',%s,%s,%s)""",
                        (audit_id, pdf_path, completed + timedelta(minutes=1),
                         random.randint(3500, 4800),
                         random.randint(1100, 1900),
                         round(random.uniform(0.07, 0.18), 4)),
                    )

        # Named fixture per user story: Grant Smith, sales_person in NSW Sales Team
        # (team_id=1, company=Atlas), consent=TRUE so the drill-down renders
        # name + email rather than "Anonymised". Mid-Performing profile.
        cur.execute(
            """INSERT INTO respondents
                   (email, name, company, industry, role, team_id, company_id,
                    consent_share_individual)
               VALUES ('grant.smith@demo.decipher.local','Grant Smith',
                       'Demo: Atlas Media Group','media','sales_person',
                       1, %s, TRUE)
               RETURNING respondent_id""",
            (company_atlas,),
        )
        grant_id = cur.fetchone()[0]
        g_started = now - timedelta(days=3, hours=4)
        g_completed = g_started + timedelta(minutes=12)
        cur.execute(
            """INSERT INTO audits
                   (respondent_id, audit_version_id, status,
                    started_at, completed_at)
               VALUES (%s,%s,'reported',%s,%s) RETURNING audit_id""",
            (grant_id, master_v_id, g_started, g_completed),
        )
        grant_audit_id = cur.fetchone()[0]
        for dim in DIMENSIONS:
            for qid in question_ids[dim]:
                cur.execute(
                    """INSERT INTO responses
                           (audit_id, question_id, answer_value, response_ms)
                       VALUES (%s,%s,%s,%s)""",
                    (grant_audit_id, qid, random.randint(3, 5),
                     random.randint(2800, 14000)),
                )
        grant_scores = {
            "cognitive_empathy": 0.68,
            "eq": 0.71,
            "pressure_composure": 0.58,
            "storytelling": 0.63,
        }
        cur.execute(
            """INSERT INTO audit_scores
                   (audit_id, cognitive_empathy, eq, pressure_composure,
                    storytelling, raw_band_json, computed_at)
               VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s)""",
            (grant_audit_id, grant_scores["cognitive_empathy"], grant_scores["eq"],
             grant_scores["pressure_composure"], grant_scores["storytelling"],
             json.dumps({"cognitive_empathy": "performing", "eq": "performing",
                         "pressure_composure": "practising", "storytelling": "performing"}),
             g_completed),
        )
        for dim, s in grant_scores.items():
            band = ("elite" if s >= 0.8 else "performing" if s >= 0.6
                    else "practising" if s >= 0.4 else "developing")
            cur.execute(
                "INSERT INTO band_classifications (audit_id, dimension, band, score) VALUES (%s,%s,%s,%s)",
                (grant_audit_id, dim, band, s),
            )
        cur.execute(
            """INSERT INTO archetype_assignments
                   (audit_id, taxonomy_id, archetype_id, confidence, assigned_at)
               VALUES (%s,1,%s,%s,%s)""",
            (grant_audit_id, archetype_map["edge_builder"], 0.81, g_completed),
        )
        cur.execute(
            "INSERT INTO audit_score_vectors (audit_id, vec) VALUES (%s, %s::vector)",
            (grant_audit_id, _vec(grant_scores)),
        )
        cur.execute(
            """INSERT INTO reports
                   (audit_id, pdf_path, generated_at, version,
                    claude_model_used, input_tokens, output_tokens, cost_usd)
               VALUES (%s,%s,%s,1,'claude-opus-4-7',4200,1450,0.124)""",
            (grant_audit_id, f"/data/reports/dummy_audit_{grant_audit_id}_v1.pdf",
             g_completed + timedelta(minutes=1)),
        )

        # 25 standalones (no team)
        for i in range(25):
            fn = FIRST_NAMES[(i * 3) % len(FIRST_NAMES)]
            ln = LAST_NAMES[(i * 11) % len(LAST_NAMES)]
            cur.execute(
                """INSERT INTO respondents
                       (email, name, industry, role)
                   VALUES (%s,%s,%s,'sales_person') RETURNING respondent_id""",
                (f"solo{i+1:03d}@demo.decipher.local", f"{fn} {ln}",
                 random.choice(["tech","media","automotive","pharma"])),
            )
            rid = cur.fetchone()[0]
            started = now - timedelta(days=random.randint(0, 14))
            completed = started + timedelta(minutes=random.randint(6, 15))
            cur.execute(
                """INSERT INTO audits
                       (respondent_id, audit_version_id, status,
                        started_at, completed_at)
                   VALUES (%s,%s,'reported',%s,%s) RETURNING audit_id""",
                (rid, master_v_id, started, completed),
            )
            audit_id = cur.fetchone()[0]
            for dim in DIMENSIONS:
                for qid in question_ids[dim]:
                    cur.execute(
                        """INSERT INTO responses
                               (audit_id, question_id, answer_value, response_ms)
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
                (audit_id, scores["cognitive_empathy"], scores["eq"],
                 scores["pressure_composure"], scores["storytelling"],
                 json.dumps({d: "performing" for d in DIMENSIONS}), completed),
            )
            for dim in DIMENSIONS:
                s = scores[dim]
                band = ("elite" if s >= 0.8 else "performing" if s >= 0.6
                        else "practising" if s >= 0.4 else "developing")
                cur.execute(
                    "INSERT INTO band_classifications (audit_id, dimension, band, score) VALUES (%s,%s,%s,%s)",
                    (audit_id, dim, band, s),
                )
            arc_code = random.choice(ARCHETYPE_CODES)
            cur.execute(
                """INSERT INTO archetype_assignments
                       (audit_id, taxonomy_id, archetype_id, confidence, assigned_at)
                   VALUES (%s,1,%s,%s,%s)""",
                (audit_id, archetype_map[arc_code],
                 round(random.uniform(0.55, 0.93), 3), completed),
            )
            cur.execute(
                "INSERT INTO audit_score_vectors (audit_id, vec) VALUES (%s, %s::vector)",
                (audit_id, _vec(scores)),
            )

        # 14-day cohort snapshots (global)
        for d in range(14):
            day = (now - timedelta(days=13 - d)).date()
            cur.execute(
                """SELECT count(*), avg(cognitive_empathy), avg(eq),
                          avg(pressure_composure), avg(storytelling)
                     FROM audit_scores s JOIN audits a USING (audit_id)
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
                   ON CONFLICT (snapshot_date) DO UPDATE SET
                     total_audits = EXCLUDED.total_audits,
                     mean_cognitive_empathy = EXCLUDED.mean_cognitive_empathy,
                     mean_eq = EXCLUDED.mean_eq,
                     mean_pressure_composure = EXCLUDED.mean_pressure_composure,
                     mean_storytelling = EXCLUDED.mean_storytelling""",
                (day, int(n or 0), float(ce or 0), float(eq or 0),
                 float(pc or 0), float(st or 0),
                 json.dumps({"dummy": True}), json.dumps({"dummy": True})),
            )

        # patterns
        for name, cond, hit, n, p, oos, passed in [
            ("Media + low EQ → low storytelling",
             {"all":[{"industry":"media"},{"dim":"eq","op":"<","val":0.5},{"dim":"storytelling","op":"<","val":0.5}]},
             0.78, 92, 0.0008, 0.71, True),
            ("Low pressure composure + low cognitive empathy → Developing storytelling",
             {"all":[{"dim":"pressure_composure","op":"<","val":0.5},{"dim":"cognitive_empathy","op":"<","val":0.5},{"dim":"storytelling","band":"developing"}]},
             0.84, 47, 0.0002, 0.79, True),
            ("Elite cognitive empathy + Elite EQ → Edge-Builder",
             {"all":[{"dim":"cognitive_empathy","band":"elite"},{"dim":"eq","band":"elite"},{"archetype":"edge_builder"}]},
             0.71, 38, 0.0014, 0.66, True),
            ("Tech industry + high storytelling → Observer",
             {"all":[{"industry":"tech"},{"dim":"storytelling","op":">","val":0.7},{"archetype":"observer"}]},
             0.69, 31, 0.0033, 0.61, True),
            ("Practising EQ + low pressure composure → at-risk under stress",
             {"all":[{"dim":"eq","band":"practising"},{"dim":"pressure_composure","op":"<","val":0.45}]},
             0.62, 56, 0.012, 0.49, False),
        ]:
            cur.execute(
                """INSERT INTO pattern_library
                       (name, conditions_json, evidence_json, hit_rate,
                        n_observations, bh_p_value, oos_hit_rate, robust, doubt_passed)
                   VALUES (%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s)""",
                (name, json.dumps(cond), json.dumps({"dummy": True}),
                 hit, n, p, oos, passed, passed),
            )

        # 3 squarespace exports
        os.makedirs("/Users/max/Documents/Decipher/_squarespace_exports", exist_ok=True)
        for i, days_ago in enumerate([7, 4, 1]):
            ts = now - timedelta(days=days_ago)
            cur.execute(
                """INSERT INTO squarespace_exports
                       (generated_at, bundle_path, file_count, size_bytes,
                        summary, cost_usd)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (ts, f"/data/exports/squarespace_export_{ts.strftime('%Y-%m-%d')}.zip",
                 47 + i, 1_200_000 + i * 50_000,
                 f"Demo export v{i+1}: pages + seo + design + audit_app + pdf_report + voice",
                 round(random.uniform(0.18, 0.32), 4)),
            )

        # 100 fresh events
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
        for _ in range(100):
            sev, action, kind = random.choice(actions)
            occurred = now - timedelta(hours=random.uniform(0, 72))
            payload: dict[str, Any] = {"dummy": True, "kind": kind}  # noqa: F821
            if action == "claude.api_call":
                payload.update({
                    "model": random.choice(["claude-opus-4-7", "claude-haiku-4-5-20251001"]),
                    "input_tokens": random.randint(800, 4500),
                    "output_tokens": random.randint(250, 1800),
                    "cost_usd": round(random.uniform(0.005, 0.12), 4),
                })
            cur.execute(
                """INSERT INTO events_log
                       (occurred_at, actor, action, severity, subject_id, payload)
                   VALUES (%s, 'seed_dummy', %s, %s, %s, %s::jsonb)""",
                (occurred, action, sev,
                 f"{kind}-{random.randint(1, 999):03d}",
                 json.dumps(payload)),
            )

        # Print summary
        cur.execute("SELECT count(*) FROM teams"); n_teams = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM respondents WHERE role='sales_person'"); n_reps = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM respondents WHERE role IN ('sales_director','learning_development')"); n_exec = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM audits"); n_aud = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM reports"); n_rep = cur.fetchone()[0]
    print(f"Multi-team seed complete:")
    print(f"  teams:           {n_teams}")
    print(f"  sales_person:    {n_reps}")
    print(f"  team execs:      {n_exec}")
    print(f"  audits:          {n_aud}")
    print(f"  reports:         {n_rep}")


# Need typing.Any for the local hint
from typing import Any  # noqa: E402

if __name__ == "__main__":
    main()
