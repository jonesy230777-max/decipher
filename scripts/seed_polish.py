"""Polish pass on top of seed_dummy:

  * Mark 8 of the team's high-cognitive-empathy respondents as elite-across-all-4
    so the executive ELITE PERFORMERS KPI reads a real number.
  * Backdate 5 audits to today (so 'audits today' is non-zero).
  * Backdate 2 audits to right now so they're freshly completed.

Idempotent: each pass simply re-applies the same UPDATEs.
"""
from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone

from app.db import conn

random.seed(20260516)
os.environ.setdefault("DECIPHER_DB_PORT", "55432")


def main() -> None:
    now = datetime.now(timezone.utc)
    with conn() as c, c.cursor() as cur:
        # 1) Lift 8 audits to genuinely Elite across all 4 traits (score >= 0.88).
        cur.execute(
            """SELECT a.audit_id
                 FROM audits a
                 JOIN respondents r ON r.respondent_id = a.respondent_id
                 JOIN audit_scores s USING (audit_id)
                WHERE r.team_id = 1 AND a.status = 'reported'
             ORDER BY (s.cognitive_empathy + s.eq + s.pressure_composure + s.storytelling) DESC
                LIMIT 8"""
        )
        elite_ids = [r[0] for r in cur.fetchall()]
        for aid in elite_ids:
            cur.execute(
                """UPDATE audit_scores
                      SET cognitive_empathy = %s, eq = %s,
                          pressure_composure = %s, storytelling = %s
                    WHERE audit_id = %s""",
                (round(random.uniform(0.88, 0.96), 4),
                 round(random.uniform(0.88, 0.96), 4),
                 round(random.uniform(0.88, 0.96), 4),
                 round(random.uniform(0.88, 0.96), 4),
                 aid),
            )
            cur.execute("DELETE FROM band_classifications WHERE audit_id = %s", (aid,))
            for dim in ("cognitive_empathy", "eq", "pressure_composure", "storytelling"):
                cur.execute(
                    """INSERT INTO band_classifications (audit_id, dimension, band, score)
                       VALUES (%s, %s, 'elite', %s)""",
                    (aid, dim, round(random.uniform(0.88, 0.96), 4)),
                )

        # 2) Backdate 5 audits to today (still completed) so 'audits today' > 0.
        cur.execute(
            """UPDATE audits
                  SET started_at = (now() - (random() * interval '8 hours')),
                      completed_at = (now() - (random() * interval '3 hours'))
                WHERE audit_id IN (
                    SELECT audit_id FROM audits
                     WHERE status = 'reported'
                     ORDER BY started_at DESC OFFSET 12 LIMIT 5
                )"""
        )

        # 3) Two audits started today and still in_progress (fresh activity).
        cur.execute(
            """UPDATE audits
                  SET status = 'in_progress',
                      started_at = (now() - (random() * interval '45 minutes')),
                      completed_at = NULL
                WHERE audit_id IN (
                    SELECT audit_id FROM audits
                     WHERE status = 'in_progress'
                     ORDER BY audit_id LIMIT 2
                )"""
        )

        # 4) Add a handful of brand-new events to the log.
        for offset_min in (5, 12, 27, 41, 58):
            cur.execute(
                """INSERT INTO events_log (occurred_at, actor, action, severity,
                                           subject_id, payload)
                   VALUES (%s, 'seed_dummy', %s, 'info', %s,
                           '{"dummy": true}'::jsonb)""",
                (now - timedelta(minutes=offset_min),
                 random.choice([
                    "audit.started", "audit.completed", "audit.scored",
                    "report.generated", "email.sent",
                 ]),
                 f"audit-{random.randint(1, 999):03d}"),
            )

        # Print resulting counts.
        cur.execute("SELECT count(*) FROM audits WHERE started_at::date = current_date")
        n_today = cur.fetchone()[0]
        cur.execute(
            """SELECT count(*) FROM audit_scores s
                 JOIN audits a USING (audit_id)
                 JOIN respondents r ON r.respondent_id = a.respondent_id
                WHERE r.team_id = 1
                  AND s.cognitive_empathy >= 0.85 AND s.eq >= 0.85
                  AND s.pressure_composure >= 0.85 AND s.storytelling >= 0.85"""
        )
        n_elite = cur.fetchone()[0]
    print(f"polish: audits today = {n_today}, elite (NSW) = {n_elite}")


if __name__ == "__main__":
    main()
