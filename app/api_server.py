"""Decipher FastAPI surface (spec §6).

All endpoints DB-driven. No hardcoded numbers. Magic-link auth + JWT roles
land at M5; the prototype currently treats the operator as the implied caller.
"""
from __future__ import annotations
# S104: preview-only verification build for deploy-boundary 502 repro (no functional change)
# S105: preview-only build to reproduce deploy-boundary 502 hang (no functional change)

import hashlib
import io
import json
import logging
import os
import zipfile
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt as _jwt
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from .db import conn, event, rows, scalar
from app.admin_bootstrap import bootstrap_admin_password

log = logging.getLogger(__name__)


@asynccontextmanager
def _run_backup() -> None:
    """S092: Run pg_backup.sh shell script from the scheduler."""
    import subprocess
    script = Path(__file__).parent.parent / "scripts" / "pg_backup.sh"
    result = subprocess.run([str(script)], capture_output=True, text=True, timeout=120)
    if result.returncode == 0:
        log.info("pg_backup: %s", result.stdout.strip().splitlines()[-1] if result.stdout else "done")
        event("db.backup_complete", actor="system", payload={"stdout": result.stdout[-500:]})
    else:
        log.error("pg_backup failed: %s", result.stderr[:500])
        event("db.backup_failed", severity="error", actor="system",
              payload={"stderr": result.stderr[:500]})


async def _lifespan(app: FastAPI):
    from app.cohort_jobs import run_snapshot, run_pattern_hunt
    bootstrap_admin_password()
    scheduler = BackgroundScheduler(timezone="Australia/Sydney")
    scheduler.add_job(run_snapshot,     "cron", hour=2,  minute=0,  id="cohort_snapshot")
    scheduler.add_job(run_pattern_hunt, "cron", hour=3,  minute=0,  day_of_week="mon", id="pattern_hunt")
    scheduler.add_job(_run_backup,      "cron", hour=2,  minute=30, id="pg_backup")
    scheduler.start()
    log.info("APScheduler started (snapshot 02:00, backup 02:30, pattern Mon 03:00 AEST)")
    yield
    scheduler.shutdown(wait=False)


def _active_taxonomy_id() -> int:
    """Resolve the currently active archetype taxonomy id. Cached at module
    scope after first call. Falls back to 1 if none is flagged active.
    """
    if not hasattr(_active_taxonomy_id, "_cache"):
        row = scalar("SELECT taxonomy_id FROM archetype_taxonomies WHERE is_active = TRUE ORDER BY taxonomy_id DESC LIMIT 1")
        _active_taxonomy_id._cache = int(row) if row else 1  # type: ignore[attr-defined]
    return _active_taxonomy_id._cache  # type: ignore[attr-defined]

app = FastAPI(title="Decipher", version="0.3.0", lifespan=_lifespan)

# CORS: defaults to localhost dev origins; set DECIPHER_WEB_ORIGIN (comma-separated)
# in production to restrict to the actual site domain.
_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "DECIPHER_WEB_ORIGIN",
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:55173,http://localhost:55173",
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ---------------------------------------------------------------------------
# Health + bootstrap
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        with conn() as c, c.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "db": False, "error": str(exc)}
    return {
        "status": "ok", "db": db_ok, "service": "decipher-api",
        "version": app.version, "now": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/version")
def api_version() -> dict[str, Any]:
    """Build / deployment metadata."""
    return {
        "version":    app.version,
        "build_date": os.getenv("BUILD_DATE", "dev"),
        "git_sha":    os.getenv("GIT_SHA", "dev"),
    }


@app.get("/api/health/scoring")
def health_scoring(request: Request) -> dict[str, Any]:
    """Snapshot of the scoring + report chain. Surfaced in Settings as
    a quick at-a-glance check that taxonomy, narratives, audits, reports
    and email delivery are all wired correctly.
    """
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me or me[0]["role"] != "admin":
        raise HTTPException(403, "admin only")
    taxonomy = rows(
        """SELECT taxonomy_id, name,
                  (SELECT count(*) FROM archetypes ar WHERE ar.taxonomy_id = t.taxonomy_id)::int AS n_archetypes,
                  (SELECT count(*) FROM archetypes ar WHERE ar.taxonomy_id = t.taxonomy_id AND description IS NOT NULL)::int AS n_described
             FROM archetype_taxonomies t
            WHERE is_active = TRUE
            ORDER BY taxonomy_id DESC LIMIT 1"""
    )
    narratives = rows(
        """SELECT dimension, count(*)::int AS n
             FROM narrative_library
            WHERE taxonomy_code = 'media_sales_v1'
            GROUP BY dimension ORDER BY dimension"""
    )
    counts = rows(
        """SELECT
              (SELECT count(*) FROM audits WHERE audit_version_id = 3)::int                                        AS v2_audits,
              (SELECT count(*) FROM audit_scores s JOIN audits a USING(audit_id) WHERE a.audit_version_id = 3)::int AS v2_scored,
              (SELECT count(*) FROM reports r JOIN audits a USING(audit_id) WHERE a.audit_version_id = 3)::int      AS v2_reports,
              (SELECT count(*) FROM reports r WHERE delivered_at IS NOT NULL)::int                                  AS reports_delivered,
              (SELECT count(*) FROM audits a LEFT JOIN reports r ON r.audit_id = a.audit_id
                WHERE a.status = 'reported' AND r.report_id IS NULL)::int                                           AS orphan_reported,
              (SELECT to_char(max(generated_at), 'YYYY-MM-DD HH24:MI') FROM reports)                                AS last_report,
              (SELECT to_char(max(delivered_at), 'YYYY-MM-DD HH24:MI') FROM reports)                                AS last_delivery""",
    )[0]
    questions = scalar("SELECT count(*) FROM questions WHERE audit_version_id = 3")
    mail_host = os.environ.get("DECIPHER_MAIL_HOST", "127.0.0.1")
    mail_port = int(os.environ.get("DECIPHER_MAIL_PORT", "1025"))

    return {
        "active_taxonomy":   taxonomy[0] if taxonomy else None,
        "questions_v2":      int(questions or 0),
        "narratives":        {n["dimension"]: n["n"] for n in narratives},
        "audits":            counts,
        "mailpit":           {"host": mail_host, "port": mail_port},
        "checked_at":        datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/bootstrap")
def bootstrap(request: Request) -> dict[str, Any]:
    counts = {
        "respondents":  scalar("SELECT count(*) FROM respondents WHERE role='sales_person'") or 0,
        "operators":    scalar("SELECT count(*) FROM respondents WHERE role='admin'") or 0,
        "executives":   scalar("SELECT count(*) FROM respondents WHERE role='sales_director'") or 0,
        "audits":       scalar("SELECT count(*) FROM audits") or 0,
        "audits_today": scalar(
            "SELECT count(*) FROM audits WHERE started_at::date = current_date"
        ) or 0,
        "audits_month": scalar(
            "SELECT count(*) FROM audits "
            "WHERE date_trunc('month', started_at) = date_trunc('month', current_date)"
        ) or 0,
        "reports":      scalar("SELECT count(*) FROM reports") or 0,
        "patterns_doubt_passed":
                        scalar("SELECT count(*) FROM pattern_library WHERE doubt_passed=TRUE") or 0,
        "industries":   scalar("SELECT count(*) FROM industries") or 0,
        "bespoke_clients": scalar("SELECT count(*) FROM bespoke_clients") or 0,
        "teams":        scalar("SELECT count(*) FROM teams") or 0,
        "companies":    scalar("SELECT count(*) FROM companies") or 0,
        "events_24h":   scalar(
            "SELECT count(*) FROM events_log WHERE occurred_at > now() - interval '24 hours'"
        ) or 0,
    }
    pipeline = scalar(
        "SELECT coalesce(sum(estimated_value), 0) FROM bespoke_clients WHERE status='active'"
    ) or 0
    active = rows(
        "SELECT taxonomy_id, name FROM archetype_taxonomies WHERE is_active=TRUE LIMIT 1"
    )
    # Resolve caller from JWT; fallback to seeded admin while unauthenticated.
    caller = _caller_from_request(request)
    if caller:
        me_row = rows(
            "SELECT respondent_id, email, name, role FROM respondents WHERE respondent_id = %s",
            (int(caller["sub"]),),
        )
    else:
        me_row = rows(
            "SELECT respondent_id, email, name, role FROM respondents "
            "WHERE role = 'admin' ORDER BY respondent_id LIMIT 1"
        )

    # 14-day sparkline series for top-of-screen metrics. One row per day,
    # zero-filled. DB-driven; no fabrication.
    spark_audits = rows(
        """WITH days AS (
              SELECT generate_series(current_date - 13, current_date, '1 day')::date AS d
            )
            SELECT days.d AS day,
                   coalesce(count(a.audit_id), 0)::int AS n
              FROM days
         LEFT JOIN audits a ON a.started_at::date = days.d
             GROUP BY days.d
             ORDER BY days.d"""
    )
    spark_reports = rows(
        """WITH days AS (
              SELECT generate_series(current_date - 13, current_date, '1 day')::date AS d
            )
            SELECT days.d AS day,
                   coalesce(count(r.report_id), 0)::int AS n
              FROM days
         LEFT JOIN reports r ON r.generated_at::date = days.d
             GROUP BY days.d
             ORDER BY days.d"""
    )
    spark_respondents = rows(
        """WITH days AS (
              SELECT generate_series(current_date - 13, current_date, '1 day')::date AS d
            )
            SELECT days.d AS day,
                   (SELECT count(*) FROM respondents
                     WHERE created_at::date <= days.d AND role = 'sales_person')::int AS n
              FROM days
             ORDER BY days.d"""
    )
    spark_events = rows(
        """WITH days AS (
              SELECT generate_series(current_date - 13, current_date, '1 day')::date AS d
            )
            SELECT days.d AS day,
                   coalesce(count(e.id), 0)::int AS n
              FROM days
         LEFT JOIN events_log e ON e.occurred_at::date = days.d
             GROUP BY days.d
             ORDER BY days.d"""
    )
    spark_companies = rows(
        """WITH days AS (
              SELECT generate_series(current_date - 13, current_date, '1 day')::date AS d
            )
            SELECT days.d AS day,
                   (SELECT count(*) FROM companies
                     WHERE created_at::date <= days.d)::int AS n
              FROM days
             ORDER BY days.d"""
    )
    spark_teams = rows(
        """WITH days AS (
              SELECT generate_series(current_date - 13, current_date, '1 day')::date AS d
            )
            SELECT days.d AS day,
                   (SELECT count(*) FROM teams
                     WHERE created_at::date <= days.d)::int AS n
              FROM days
             ORDER BY days.d"""
    )
    spark_pipeline = rows(
        """WITH days AS (
              SELECT generate_series(current_date - 13, current_date, '1 day')::date AS d
            )
            SELECT days.d AS day,
                   (SELECT coalesce(sum(estimated_value), 0)::int
                      FROM bespoke_clients
                     WHERE status='active' AND created_at::date <= days.d) AS n
              FROM days
             ORDER BY days.d"""
    )
    sparks = {
        "audits":      [int(r["n"]) for r in spark_audits],
        "reports":     [int(r["n"]) for r in spark_reports],
        "respondents": [int(r["n"]) for r in spark_respondents],
        "events":      [int(r["n"]) for r in spark_events],
        "companies":   [int(r["n"]) for r in spark_companies],
        "teams":       [int(r["n"]) for r in spark_teams],
        "pipeline":    [int(r["n"]) for r in spark_pipeline],
    }
    # 30-day mean per-dimension scores (S031).
    _dm = rows(
        """SELECT round((avg(s.cognitive_empathy)  * 100)::numeric, 1)::float AS cognitive_empathy,
                  round((avg(s.eq)                 * 100)::numeric, 1)::float AS eq,
                  round((avg(s.pressure_composure) * 100)::numeric, 1)::float AS pressure_composure,
                  round((avg(s.storytelling)       * 100)::numeric, 1)::float AS storytelling,
                  count(*)::int                                                AS n_scored
             FROM audit_scores s
             JOIN audits a ON a.audit_id = s.audit_id
            WHERE a.started_at > now() - interval '30 days'"""
    )
    _dmr = _dm[0] if _dm else {}
    dim_means_30d = {
        "cognitive_empathy":  float(_dmr.get("cognitive_empathy")  or 0),
        "eq":                 float(_dmr.get("eq")                 or 0),
        "pressure_composure": float(_dmr.get("pressure_composure") or 0),
        "storytelling":       float(_dmr.get("storytelling")       or 0),
        "n_scored":           int(_dmr.get("n_scored")             or 0),
    }
    return {
        "ports": {
            "db":   os.getenv("DECIPHER_DB_PORT"),
            "api":  os.getenv("DECIPHER_API_PORT"),
            "web":  os.getenv("DECIPHER_WEB_PORT"),
            "mail": os.getenv("DECIPHER_MAIL_PORT"),
        },
        "counts": counts,
        "pipeline_aud": float(pipeline),
        "archetype_taxonomy_active": active[0] if active else None,
        "me": me_row[0] if me_row else None,
        "sparks": sparks,
        "dim_means_30d": dim_means_30d,
        "roles": [
            {"code": "admin",               "label": "Admin"},
            {"code": "ceo",                 "label": "CEO"},
            {"code": "sales_director",      "label": "Sales Director"},
            {"code": "hr",                  "label": "HR"},
            {"code": "learning_development","label": "Learning & Development"},
            {"code": "sales_person",        "label": "Sales Person"},
        ],
        "served_at": datetime.utcnow().isoformat() + "Z",
    }


# ---------------------------------------------------------------------------
# Events + reference
# ---------------------------------------------------------------------------


@app.get("/api/events")
def recent_events(request: Request, limit: int = 200) -> dict[str, Any]:
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me or me[0]["role"] not in ("admin", "ceo"):
        raise HTTPException(403, "admin or ceo only")
    limit = max(1, min(limit, 1000))
    data = rows(
        "SELECT id, occurred_at, actor, action, severity, subject_id, payload "
        "FROM events_log ORDER BY occurred_at DESC LIMIT %s",
        (limit,),
    )
    return {"events": data, "count": len(data)}


class IndustryCreate(BaseModel):
    code:         str
    name:         str
    description:  str | None = None


@app.post("/api/industries")
def industries_create(body: IndustryCreate, request: Request) -> dict[str, Any]:
        caller = _caller_from_request(request)
        if not caller:
                raise HTTPException(401, "not authenticated")
    me = rows("SELECT role FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me or me[0]["role"] != "admin":
        raise HTTPException(403, "only admin can add industries")
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO industries (code, name, description)
               VALUES (%s, %s, %s)
               ON CONFLICT (code) DO UPDATE SET
                  name = EXCLUDED.name,
                  description = EXCLUDED.description
               RETURNING industry_id""",
            (body.code.lower().strip(), body.name.strip(), body.description),
        )
        iid = cur.fetchone()[0]
    return {"ok": True, "industry_id": iid}


# ---------------------------------------------------------------------------
# Team + individual gap analysis
# ---------------------------------------------------------------------------


@app.get("/api/teams/{team_id}/gap-analysis")
def team_gap_analysis(team_id: int, request: Request) -> dict[str, Any]:
    _require_team_access(request, team_id)
    """Gap analysis for a team: weakest dimension, distance from each band
    boundary, sub-segments (top vs bottom quartile), and remediation
    suggestions per dimension."""
    _team_or_404(team_id)
    means = rows(
        """SELECT avg(s.cognitive_empathy)   AS ce,
                  avg(s.eq)                  AS eq,
                  avg(s.pressure_composure)  AS pc,
                  avg(s.storytelling)        AS st,
                  count(*)                   AS n
             FROM audit_scores s
             JOIN audits a USING (audit_id)
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s
            AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                WHERE aa.respondent_id = r.respondent_id
                ORDER BY aa.started_at DESC LIMIT 1)
            AND r.role = 'sales_person'""",
        (team_id,),
    )[0]
    dims = [
        ("cognitive_empathy",   "Cognitive Empathy",   means["ce"]),
        ("eq",                  "Emotional Intelligence", means["eq"]),
        ("pressure_composure",  "Pressure Composure",  means["pc"]),
        ("storytelling",        "Storytelling",        means["st"]),
    ]
    # Cohort baseline (global mean)
    coh = rows(
        """SELECT avg(cognitive_empathy) AS ce, avg(eq) AS eq,
                  avg(pressure_composure) AS pc, avg(storytelling) AS st
             FROM audit_scores"""
    )[0]
    cohort_map = {
        "cognitive_empathy":   coh["ce"], "eq": coh["eq"],
        "pressure_composure":  coh["pc"], "storytelling": coh["st"],
    }
    BAND_BOUNDS = {"elite": 0.85, "performing": 0.65, "practising": 0.40, "developing": 0.0}
    def band_for(v):
        if v is None: return "unknown"
        if v >= 0.85: return "elite"
        if v >= 0.65: return "performing"
        if v >= 0.40: return "practising"
        return "developing"

    gaps = []
    for key, label, val in dims:
        v = float(val) if val is not None else None
        cohort_v = float(cohort_map[key]) if cohort_map[key] is not None else None
        gap_to_elite      = (0.85 - v) * 100 if v is not None else None
        gap_to_performing = (0.65 - v) * 100 if v is not None else None
        delta_vs_cohort   = (v - cohort_v) * 100 if (v is not None and cohort_v is not None) else None
        gaps.append({
            "dimension": key, "label": label,
            "score_100": round(v * 100, 1) if v is not None else None,
            "band": band_for(v),
            "cohort_100": round(cohort_v * 100, 1) if cohort_v is not None else None,
            "delta_vs_cohort_100": round(delta_vs_cohort, 1) if delta_vs_cohort is not None else None,
            "gap_to_elite_pts":   round(gap_to_elite, 1) if gap_to_elite is not None else None,
            "gap_to_performing_pts": round(gap_to_performing, 1) if gap_to_performing is not None else None,
        })
    gaps.sort(key=lambda g: g["score_100"] if g["score_100"] is not None else 0)

    # Top + bottom quartile reps in this team
    top_bottom = rows(
        """WITH overall AS (
              SELECT r.respondent_id, r.name, r.email, r.consent_share_individual,
                     (s.cognitive_empathy + s.eq + s.pressure_composure + s.storytelling) / 4.0 AS sc
                FROM audit_scores s
                JOIN audits a USING (audit_id)
                JOIN respondents r ON r.respondent_id = a.respondent_id
               WHERE r.team_id = %s
               AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                   WHERE aa.respondent_id = r.respondent_id
                   ORDER BY aa.started_at DESC LIMIT 1)
               AND r.role = 'sales_person'
           )
           SELECT * FROM overall ORDER BY sc DESC""",
        (team_id,),
    )
    n = len(top_bottom)
    q = max(1, n // 4)
    top_q    = top_bottom[:q]
    bottom_q = top_bottom[-q:][::-1] if n >= 2 else []

    return {
        "n_respondents": int(means["n"] or 0),
        "gaps": gaps,
        "weakest_dimension": gaps[0] if gaps else None,
        "strongest_dimension": gaps[-1] if gaps else None,
        "top_quartile":    [{
            "respondent_id": r["respondent_id"],
            "name":  r["name"] if r["consent_share_individual"] else "Anonymised",
            "email": r["email"] if r["consent_share_individual"] else "anonymised",
            "score_100": round(float(r["sc"]) * 100, 1) if r["sc"] is not None else None,
        } for r in top_q],
        "bottom_quartile": [{
            "respondent_id": r["respondent_id"],
            "name":  r["name"] if r["consent_share_individual"] else "Anonymised",
            "email": r["email"] if r["consent_share_individual"] else "anonymised",
            "score_100": round(float(r["sc"]) * 100, 1) if r["sc"] is not None else None,
        } for r in bottom_q],
    }


@app.get("/api/respondents/{respondent_id}/gap-analysis")
def respondent_gap_analysis(respondent_id: int) -> dict[str, Any]:
    """Per-respondent gap analysis vs. their team mean and cohort mean."""
    r = rows(
        "SELECT respondent_id, team_id FROM respondents WHERE respondent_id = %s",
        (respondent_id,),
    )
    if not r:
        raise HTTPException(404, "respondent not found")
    rec = r[0]
    latest = rows(
        """SELECT s.cognitive_empathy, s.eq, s.pressure_composure, s.storytelling,
                  a.completed_at
             FROM audit_scores s
             JOIN audits a USING (audit_id)
            WHERE a.respondent_id = %s
            ORDER BY a.completed_at DESC LIMIT 1""",
        (respondent_id,),
    )
    if not latest:
        return {"latest": None, "gaps": []}
    s = latest[0]
    team_means = rows(
        """SELECT avg(s.cognitive_empathy) AS ce, avg(s.eq) AS eq,
                  avg(s.pressure_composure) AS pc, avg(s.storytelling) AS st
             FROM audit_scores s
             JOIN audits a USING (audit_id)
             JOIN respondents r ON r.respondent_id = a.respondent_id
                        WHERE r.team_id = %s
                                      AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                                                                       WHERE aa.respondent_id = r.respondent_id
                                                                                                        ORDER BY aa.started_at DESC LIMIT 1)"""
        (rec["team_id"],),
    )[0]
    cohort_means = rows(
                    """SELECT avg(s.cognitive_empathy) AS ce, avg(s.eq) AS eq,
                                  avg(s.pressure_composure) AS pc, avg(s.storytelling) AS st
                                                FROM audit_scores s
                                                              JOIN audits a USING (audit_id)
                                                                            WHERE a.audit_id = (SELECT aa.audit_id FROM audits aa
                                                                                                               WHERE aa.respondent_id = a.respondent_id
                                                                                                                                                  ORDER BY aa.started_at DESC LIMIT 1)"""
    )[0]

    def band(v):
        if v is None: return "unknown"
        if v >= 0.85: return "elite"
        if v >= 0.65: return "performing"
        if v >= 0.40: return "practising"
        return "developing"

    dims = [
        ("cognitive_empathy", "Cognitive Empathy", s["cognitive_empathy"], team_means["ce"], cohort_means["ce"]),
        ("eq", "Emotional Intelligence", s["eq"], team_means["eq"], cohort_means["eq"]),
        ("pressure_composure", "Pressure Composure", s["pressure_composure"], team_means["pc"], cohort_means["pc"]),
        ("storytelling", "Storytelling", s["storytelling"], team_means["st"], cohort_means["st"]),
    ]
    gaps = []
    for key, label, v, tm, cm in dims:
        v = float(v) if v is not None else None
        tm = float(tm) if tm is not None else None
        cm = float(cm) if cm is not None else None
        gaps.append({
            "dimension": key, "label": label,
            "score_100": round(v * 100, 1) if v is not None else None,
            "band": band(v),
            "team_mean_100":    round(tm * 100, 1) if tm is not None else None,
            "cohort_mean_100":  round(cm * 100, 1) if cm is not None else None,
            "delta_vs_team_100":   round((v - tm) * 100, 1) if (v is not None and tm is not None) else None,
            "delta_vs_cohort_100": round((v - cm) * 100, 1) if (v is not None and cm is not None) else None,
            "gap_to_elite_pts":      round((0.85 - v) * 100, 1) if v is not None else None,
            "gap_to_performing_pts": round((0.65 - v) * 100, 1) if v is not None else None,
        })
    gaps_sorted = sorted(gaps, key=lambda g: g["score_100"] if g["score_100"] is not None else 0)
    return {
        "latest": {"completed_at": str(s["completed_at"])},
        "gaps": gaps,
        "weakest_dimension": gaps_sorted[0] if gaps_sorted else None,
        "strongest_dimension": gaps_sorted[-1] if gaps_sorted else None,
    }


@app.get("/api/industries")
def industries() -> dict[str, Any]:
    return {"industries": rows("SELECT * FROM industries ORDER BY code")}


_AI_SYSTEM_PROMPT = """\
You are the Decipher data assistant, embedded in the Decipher dashboard used by Steve, \
a media sales intelligence operator based in Australia.

Answer the user's question in 2-4 sentences using only the data context provided. \
Be direct and specific — cite actual numbers from the context. \
If the context does not contain enough information to answer, say so plainly and suggest \
which page would have the relevant data.

Writing rules:
- Australian English: behaviour, recognise, practise, organisation, colour.
- No em dashes. Use commas or full stops instead.
- No filler words: no "unlock", "leverage", "seamless", "game-changer", "empower", "delve".
- No bro-sales clichés: no "close", "crush it", "killer".
- Do not fabricate numbers. Every figure you cite must appear in the context below.
- Plain prose only. No bullet points, no markdown, no headings.\
"""


def _build_ai_context(page: str, team_id: Any, company_id: Any, audit_id: Any) -> str:
    """Pull page-relevant DB data and format it as a readable context block."""
    lines: list[str] = []

    # --- Global summary (always included) ---
    g = rows(
        """SELECT
             (SELECT count(*) FROM respondents WHERE role='sales_person')::int         AS n_reps,
             (SELECT count(*) FROM audits WHERE status IN ('scored','reported'))::int  AS n_scored,
             (SELECT count(*) FROM reports)::int                                       AS n_reports,
             (SELECT count(*) FROM (
                SELECT bc.audit_id FROM band_classifications bc
                  JOIN audits a USING (audit_id)
                 WHERE bc.band = 'developing'
                 GROUP BY bc.audit_id HAVING count(*) >= 2
             ) s)::int                                                                 AS at_risk,
             (SELECT count(*) FROM audit_scores
               WHERE cognitive_empathy >= 0.85 AND eq >= 0.85
                 AND pressure_composure >= 0.85 AND storytelling >= 0.85)::int        AS elite,
             (SELECT coalesce(sum(estimated_value),0)
                FROM bespoke_clients WHERE status='active')                            AS pipeline_aud"""
    )
    if g:
        r = g[0]
        lines.append(
            f"Global cohort: {r['n_reps']} sales reps, {r['n_scored']} scored audits, "
            f"{r['n_reports']} reports generated."
        )
        lines.append(
            f"At-risk reps (Developing in 2+ traits): {r['at_risk']}. "
            f"Elite performers (all 4 traits 85+): {r['elite']}. "
            f"Active bespoke pipeline: AUD ${float(r['pipeline_aud']):,.0f}."
        )

    # --- Top archetype ---
    top_arch = rows(
        """SELECT ar.name, count(*) AS n
             FROM archetype_assignments aa
             JOIN archetypes ar USING (archetype_id)
            WHERE aa.taxonomy_id = 2
            GROUP BY ar.name ORDER BY n DESC LIMIT 1"""
    )
    if top_arch:
        lines.append(f"Modal archetype: {top_arch[0]['name']} ({top_arch[0]['n']} respondents).")

    # --- 30-day dimension means ---
    dm = rows(
        """SELECT round((avg(s.cognitive_empathy)  * 100)::numeric, 1)::float AS ce,
                  round((avg(s.eq)                 * 100)::numeric, 1)::float AS eq,
                  round((avg(s.pressure_composure) * 100)::numeric, 1)::float AS pc,
                  round((avg(s.storytelling)       * 100)::numeric, 1)::float AS np
             FROM audit_scores s
             JOIN audits a ON a.audit_id = s.audit_id
            WHERE a.started_at > now() - interval '30 days'"""
    )
    if dm and dm[0]["ce"] is not None:
        d = dm[0]
        lines.append(
            f"30-day cohort means: Cognitive Empathy {d['ce']}, "
            f"Emotional Intelligence {d['eq']}, "
            f"Pressure Composure {d['pc']}, "
            f"Narrative Persuasion {d['np']} (all out of 100)."
        )

    # --- Team context ---
    if team_id:
        try:
            tid = int(team_id)
            t = rows("SELECT name, organisation FROM teams WHERE team_id = %s", (tid,))
            if t:
                lines.append(f"Current page: team '{t[0]['name']}' ({t[0]['organisation'] or ''}).")
            tm = rows(
                """SELECT round((avg(s.cognitive_empathy)  * 100)::numeric, 1)::float AS ce,
                          round((avg(s.eq)                 * 100)::numeric, 1)::float AS eq,
                          round((avg(s.pressure_composure) * 100)::numeric, 1)::float AS pc,
                          round((avg(s.storytelling)       * 100)::numeric, 1)::float AS np,
                          count(*)::int AS n
                     FROM audit_scores s
                     JOIN audits a USING (audit_id)
                     JOIN respondents r ON r.respondent_id = a.respondent_id
                                    WHERE r.team_id = %s
                                                      AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                                                                                           WHERE aa.respondent_id = r.respondent_id
                                                                                                                                ORDER BY aa.started_at DESC LIMIT 1)""",
                (tid,),
            )
            if tm and tm[0]["n"]:
                d = tm[0]
                lines.append(
                    f"Team scores ({d['n']} respondents): CE {d['ce']}, EQ {d['eq']}, "
                    f"PC {d['pc']}, NP {d['np']}."
                )
            t_risk = scalar(
                """SELECT count(*) FROM (
                     SELECT bc.audit_id FROM band_classifications bc
                       JOIN audits a USING (audit_id)
                       JOIN respondents r ON r.respondent_id = a.respondent_id
                                          WHERE r.team_id = %s AND bc.band = 'developing'
                                                                AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                                                                                                         WHERE aa.respondent_id = r.respondent_id
                                                                                                                                                  ORDER BY aa.started_at DESC LIMIT 1)
                      GROUP BY bc.audit_id HAVING count(*) >= 2
                   ) s""",
                (tid,),
            ) or 0
            t_elite = scalar(
                """SELECT count(*) FROM audit_scores s
                     JOIN audits a USING (audit_id)
                     JOIN respondents r ON r.respondent_id = a.respondent_id
                                      WHERE r.team_id = %s
                                                          AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                                                                                                 WHERE aa.respondent_id = r.respondent_id
                                                                                                                                        ORDER BY aa.started_at DESC LIMIT 1)
                      AND s.cognitive_empathy >= 0.85 AND s.eq >= 0.85
                      AND s.pressure_composure >= 0.85 AND s.storytelling >= 0.85""",
                (tid,),
            ) or 0
            lines.append(f"Team at-risk: {int(t_risk)}. Team elite: {int(t_elite)}.")
            weakest = rows(
                """SELECT bc.dimension, round((avg(bc.score))::numeric, 1)::float AS avg_score
                     FROM band_classifications bc
                     JOIN audits a USING (audit_id)
                     JOIN respondents r ON r.respondent_id = a.respondent_id
                                    WHERE r.team_id = %s
                                                      AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                                                                                           WHERE aa.respondent_id = r.respondent_id
                                                                                                                                ORDER BY aa.started_at DESC LIMIT 1)
                    GROUP BY bc.dimension ORDER BY avg_score LIMIT 1""",
                (tid,),
            )
            if weakest:
                lines.append(
                    f"Weakest team dimension: {weakest[0]['dimension'].replace('_',' ').title()} "
                    f"(avg {weakest[0]['avg_score']}/100)."
                )
        except (ValueError, TypeError):
            pass

    # --- Company context ---
    if company_id:
        try:
            cid = int(company_id)
            co = rows("SELECT name FROM companies WHERE company_id = %s", (cid,))
            if co:
                lines.append(f"Current page: company '{co[0]['name'].replace('Demo: ', '')}'.")
            n_teams = scalar("SELECT count(*) FROM teams WHERE company_id = %s", (cid,)) or 0
            n_reps = scalar(
                "SELECT count(*) FROM respondents WHERE company_id = %s AND role='sales_person'",
                (cid,),
            ) or 0
            lines.append(f"Company has {int(n_teams)} teams and {int(n_reps)} sales reps.")
        except (ValueError, TypeError):
            pass

    # --- Audit context ---
    if audit_id:
        try:
            aid = int(audit_id)
            a_rows = rows(
                """SELECT r.name, r.job_title, a.status,
                          s.cognitive_empathy, s.eq, s.pressure_composure, s.storytelling,
                          ar.name AS archetype_name
                     FROM audits a
                     JOIN respondents r ON r.respondent_id = a.respondent_id
                LEFT JOIN audit_scores s ON s.audit_id = a.audit_id
                LEFT JOIN archetype_assignments aa ON aa.audit_id = a.audit_id AND aa.taxonomy_id = 2
                LEFT JOIN archetypes ar ON ar.archetype_id = aa.archetype_id AND ar.taxonomy_id = 2
                    WHERE a.audit_id = %s""",
                (aid,),
            )
            if a_rows:
                ar = a_rows[0]
                name = ar["name"] or "Respondent"
                lines.append(
                    f"Current audit: {name} ({ar['job_title'] or 'Sales Rep'}), "
                    f"status {ar['status']}, archetype {ar['archetype_name'] or 'unassigned'}."
                )
                if ar["cognitive_empathy"] is not None:
                    lines.append(
                        f"Scores: CE {round(float(ar['cognitive_empathy'])*100,1)}, "
                        f"EQ {round(float(ar['eq'])*100,1)}, "
                        f"PC {round(float(ar['pressure_composure'])*100,1)}, "
                        f"NP {round(float(ar['storytelling'])*100,1)} (out of 100)."
                    )
        except (ValueError, TypeError):
            pass

    lines.append(f"Page: {page}.")
    return "\n".join(lines)


@app.post("/api/ai/ask")
def ai_ask(body: dict[str, Any], request: Request) -> dict[str, Any]:
    """AI assistant grounded in live DB data. Uses Claude Haiku for low latency."""
    from app.claude_client import complete_narrative, ClaudeCallError, HAIKU

    q = (body.get("q") or "").strip()
    page = body.get("page") or "/"
    team_id = body.get("team_id")
    company_id = body.get("company_id")
    audit_id = body.get("audit_id")
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows(
        "SELECT role, company_id FROM respondents WHERE respondent_id = %s",
        (int(caller["sub"]),),
    )
    if not me:
        raise HTTPException(401, "not authenticated")
    role, my_company_id = me[0]["role"], me[0]["company_id"]

    if team_id is not None:
        try:
            tid = int(team_id)
        except (ValueError, TypeError):
            raise HTTPException(400, "invalid team_id")
        _require_team_access(request, tid)
    if company_id is not None and role != "admin":
        try:
            cid = int(company_id)
        except (ValueError, TypeError):
            raise HTTPException(400, "invalid company_id")
        if role not in ("sales_director", "ceo", "hr", "learning_development") or my_company_id != cid:
            raise HTTPException(403, "forbidden")

    if not q:
        return {"answer": "Ask anything about this page's data. Try: 'who is at risk?', 'what is the weakest dimension?', 'how many elite performers?'."}

    context = _build_ai_context(page, team_id, company_id, audit_id)
    try:
        answer = complete_narrative(
            _AI_SYSTEM_PROMPT,
            f"Data context:\n{context}\n\nQuestion: {q}",
            model=HAIKU,
        )
    except ClaudeCallError as exc:
        event("ai_ask.error", severity="error", payload={"error": str(exc), "q": q})
        answer = "Unable to answer right now. Please try again in a moment."

    return {"answer": answer}


# Australian state / territory abbreviations -> full names. Two-way expansion
# so search('Victoria') matches 'VIC Sales Team' and search('VIC') matches
# anything labelled 'Victoria'. Add other equivalents here as needed.
REGION_SYNONYMS: dict[str, list[str]] = {
    "vic": ["victoria"],
    "victoria": ["vic"],
    "nsw": ["new south wales"],
    "new south wales": ["nsw"],
    "qld": ["queensland"],
    "queensland": ["qld"],
    "wa": ["western australia"],
    "western australia": ["wa"],
    "sa": ["south australia"],
    "south australia": ["sa"],
    "tas": ["tasmania"],
    "tasmania": ["tas"],
    "nt": ["northern territory"],
    "northern territory": ["nt"],
    "act": ["australian capital territory", "canberra"],
    "australian capital territory": ["act", "canberra"],
    "canberra": ["act"],
}


def _expand_query(q: str) -> list[str]:
    """Return the original query plus any region-synonym equivalents."""
    ql = q.lower().strip()
    out = {q}
    for key, alts in REGION_SYNONYMS.items():
        if key in ql:
            for alt in alts:
                out.add(ql.replace(key, alt))
        for alt in alts:
            if alt in ql:
                out.add(ql.replace(alt, key))
    return [s for s in out if s]


@app.get("/api/search")
def search(q: str = "", limit: int = 25) -> dict[str, Any]:
    """Global search with Australian region-synonym expansion."""
    q = (q or "").strip()
    if not q:
        return {"hits": []}
    variants = _expand_query(q)
    likes = [f"%{v}%" for v in variants]
    limit = max(1, min(limit, 100))
    hits: list[dict[str, Any]] = []
    # respondents
    for r in rows(
        """SELECT respondent_id AS id, name, email, role, team_id
             FROM respondents
            WHERE email ILIKE ANY(%s) OR name ILIKE ANY(%s) OR company ILIKE ANY(%s)
            ORDER BY name LIMIT %s""",
        (likes, likes, likes, limit),
    ):
        hits.append({
            "kind": "respondent",
            "label": r["name"] or r["email"],
            "sub": f"{r['email']} · {r['role']}",
            "href": f"/audits",
        })
    # audits by id (numeric)
    if q.isdigit():
        for r in rows("SELECT audit_id, status FROM audits WHERE audit_id = %s", (int(q),)):
            hits.append({
                "kind": "audit",
                "label": f"Audit #{r['audit_id']}",
                "sub": r["status"],
                "href": "/audits",
            })
    # bespoke
    for r in rows(
        "SELECT bespoke_client_id, client_name, unique_url_slug FROM bespoke_clients "
        "WHERE client_name ILIKE ANY(%s) OR unique_url_slug ILIKE ANY(%s) ORDER BY client_name LIMIT %s",
        (likes, likes, limit),
    ):
        hits.append({
            "kind": "bespoke",
            "label": r["client_name"],
            "sub": f"/audit/{r['unique_url_slug']}",
            "href": "/bespoke",
        })
    # promo codes
    for r in rows(
        "SELECT code, code_type, source_campaign FROM promo_codes "
        "WHERE code ILIKE ANY(%s) OR source_campaign ILIKE ANY(%s) ORDER BY code LIMIT %s",
        (likes, likes, limit),
    ):
        hits.append({
            "kind": "promo",
            "label": r["code"],
            "sub": f"{r['code_type']} · {r['source_campaign'] or ''}",
            "href": "/promo",
        })
    # industries
    for r in rows(
        "SELECT industry_id, code, name FROM industries "
        "WHERE code ILIKE ANY(%s) OR name ILIKE ANY(%s) ORDER BY name LIMIT %s",
        (likes, likes, limit),
    ):
        hits.append({
            "kind": "industry",
            "label": r["name"],
            "sub": r["code"],
            "href": "/industries",
        })
    # teams
    for r in rows(
        "SELECT team_id, name, organisation FROM teams "
        "WHERE name ILIKE ANY(%s) OR organisation ILIKE ANY(%s) ORDER BY name LIMIT %s",
        (likes, likes, limit),
    ):
        hits.append({
            "kind": "team",
            "label": r["name"],
            "sub": r["organisation"] or "",
            "href": f"/teams/{r['team_id']}",
        })
    # patterns
    for r in rows(
        "SELECT pattern_id, name, doubt_passed FROM pattern_library "
        "WHERE name ILIKE ANY(%s) ORDER BY name LIMIT %s",
        (likes, limit),
    ):
        hits.append({
            "kind": "pattern",
            "label": r["name"],
            "sub": "DOUBT-passed" if r["doubt_passed"] else "candidate",
            "href": "/cohort",
        })
    # events (action match)
    for r in rows(
        "SELECT id, action, severity FROM events_log "
        "WHERE action ILIKE ANY(%s) OR subject_id ILIKE ANY(%s) "
        "ORDER BY occurred_at DESC LIMIT %s",
        (likes, likes, limit),
    ):
        hits.append({
            "kind": "event",
            "label": r["action"],
            "sub": r["severity"],
            "href": "/events",
        })
    return {"q": q, "hits": hits[:limit * 2], "total": len(hits)}


@app.get("/api/archetypes")
def archetypes() -> dict[str, Any]:
    return {
        "taxonomies": rows("SELECT * FROM archetype_taxonomies ORDER BY taxonomy_id"),
        "archetypes": rows(
            "SELECT a.archetype_id, a.taxonomy_id, t.name AS taxonomy_name, "
            "a.code, a.name, a.description "
            "FROM archetypes a JOIN archetype_taxonomies t USING (taxonomy_id) "
            "ORDER BY a.taxonomy_id, a.archetype_id"
        ),
    }


# ---------------------------------------------------------------------------
# Audits
# ---------------------------------------------------------------------------


@app.get("/api/audits")
def audits_list(limit: int = 500, status: str | None = None,
                team_id: int | None = None, version: str | None = None) -> dict[str, Any]:
    """Audit list. Optional filter by status, team_id (strict scoping) or
    audit-version code (e.g. media_sales_v1, master_v1)."""
    where_parts: list[str] = []
    params: list[Any] = []
    if status:
        where_parts.append("a.status = %s")
        params.append(status)
    if team_id is not None:
        where_parts.append("r.team_id = %s")
        params.append(team_id)
    if version:
        where_parts.append("av.code = %s")
        params.append(version)
    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
    data = rows(
        f"""SELECT a.audit_id, a.status, a.started_at, a.completed_at,
                  r.email, r.name AS respondent_name, r.company, r.industry,
                  r.team_id, t.name AS team_name,
                  av.code AS audit_version_code, av.name AS audit_version_name,
                  s.cognitive_empathy, s.eq, s.pressure_composure, s.storytelling,
                  ar.code AS archetype_code, ar.name AS archetype_name,
                  aa.confidence AS archetype_confidence,
                  rep.report_id, rep.pdf_path
             FROM audits a
             JOIN respondents r ON r.respondent_id = a.respondent_id
             JOIN audit_versions av ON av.audit_version_id = a.audit_version_id
        LEFT JOIN teams t ON t.team_id = r.team_id
        LEFT JOIN audit_scores s ON s.audit_id = a.audit_id
        LEFT JOIN archetype_assignments aa ON aa.audit_id = a.audit_id
        LEFT JOIN archetypes ar ON ar.archetype_id = aa.archetype_id
        LEFT JOIN LATERAL (
            SELECT report_id, pdf_path FROM reports r2
             WHERE r2.audit_id = a.audit_id
             ORDER BY r2.version DESC LIMIT 1
        ) rep ON TRUE
            {where}
            ORDER BY a.started_at DESC
            LIMIT %s""",
        tuple(params + [max(1, min(limit, 2000))]),
    )
    return {"audits": data, "count": len(data)}


# ---------------------------------------------------------------------------
# Cohort
# ---------------------------------------------------------------------------


@app.get("/api/cohort/stats")
def cohort_stats(company_id: int | None = None,
                 team_id: int | None = None) -> dict[str, Any]:
    where = ["1=1"]
    params: list[Any] = []
    join_r = ""
    if company_id is not None or team_id is not None:
        join_r = " JOIN respondents r ON r.respondent_id = a.respondent_id"
        if company_id is not None:
            where.append("r.company_id = %s"); params.append(company_id)
        if team_id is not None:
            where.append("r.team_id = %s"); params.append(team_id)
    w = " AND ".join(where)

    totals = rows(
        f"""SELECT count(*) AS total_audits,
                   avg(s.cognitive_empathy) AS mean_cognitive_empathy,
                   avg(s.eq) AS mean_eq,
                   avg(s.pressure_composure) AS mean_pressure_composure,
                   avg(s.storytelling) AS mean_storytelling
              FROM audit_scores s
              JOIN audits a USING (audit_id){join_r}
             WHERE {w}""",
        tuple(params),
    )
    by_band = rows(
        f"""SELECT bc.dimension, bc.band, count(*) AS n
              FROM band_classifications bc
              JOIN audits a USING (audit_id){join_r}
             WHERE {w}
             GROUP BY bc.dimension, bc.band
             ORDER BY bc.dimension, bc.band""",
        tuple(params),
    )
    by_archetype = rows(
        f"""SELECT ar.code, ar.name, count(*) AS n
              FROM archetype_assignments aa
              JOIN archetypes ar USING (archetype_id)
              JOIN audits a ON a.audit_id = aa.audit_id{join_r}
             WHERE aa.taxonomy_id = %s AND {w}
             GROUP BY ar.code, ar.name
             ORDER BY n DESC""",
        (_active_taxonomy_id(), *params),
    )
    # Snapshots are pre-aggregated globally; for filtered views, fall back
    # to per-day recomputation from raw audits.
    if company_id is None and team_id is None:
        snapshots = rows(
            """SELECT snapshot_date, total_audits,
                      mean_cognitive_empathy, mean_eq,
                      mean_pressure_composure, mean_storytelling
                 FROM cohort_snapshots
                 ORDER BY snapshot_date"""
        )
    else:
        snapshots = rows(
            f"""SELECT a.started_at::date AS snapshot_date,
                       count(*)::int AS total_audits,
                       avg(s.cognitive_empathy) AS mean_cognitive_empathy,
                       avg(s.eq) AS mean_eq,
                       avg(s.pressure_composure) AS mean_pressure_composure,
                       avg(s.storytelling) AS mean_storytelling
                  FROM audit_scores s
                  JOIN audits a USING (audit_id){join_r}
                 WHERE {w}
                 GROUP BY a.started_at::date
                 ORDER BY a.started_at::date""",
            tuple(params),
        )

    return {
        "totals": totals[0] if totals else None,
        "by_band": by_band,
        "by_archetype": by_archetype,
        "trend": snapshots,
        "scope": {"company_id": company_id, "team_id": team_id},
    }


@app.get("/api/people")
def people_list(company_id: int | None = None,
                team_id: int | None = None,
                role: str | None = None,
                q: str | None = None,
                limit: int = 200) -> dict[str, Any]:
    where = ["r.role IN ('sales_person','sales_director','hr','learning_development','ceo')"]
    params: list[Any] = []
    if company_id is not None:
        where.append("r.company_id = %s"); params.append(company_id)
    if team_id is not None:
        where.append("r.team_id = %s"); params.append(team_id)
    if role:
        where.append("r.role = %s"); params.append(role)
    if q:
        where.append("(r.name ILIKE %s OR r.email ILIKE %s)")
        params.extend([f"%{q}%", f"%{q}%"])
    sql = f"""SELECT r.respondent_id, r.name, r.first_name, r.last_name,
                     r.email, r.mobile, r.job_title, r.role,
                     r.team_id, t.name AS team_name,
                     r.company_id, c.name AS company_name,
                     r.consent_share_individual,
                     (SELECT count(*) FROM audits a WHERE a.respondent_id = r.respondent_id)::int AS n_audits,
                     (SELECT max(a.completed_at) FROM audits a
                       WHERE a.respondent_id = r.respondent_id) AS last_audit_at,
                     (SELECT (s.cognitive_empathy + s.eq + s.pressure_composure + s.storytelling) / 4.0
                        FROM audits a
                        JOIN audit_scores s ON s.audit_id = a.audit_id
                       WHERE a.respondent_id = r.respondent_id
                       ORDER BY a.completed_at DESC NULLS LAST LIMIT 1) AS latest_overall
                FROM respondents r
           LEFT JOIN teams t ON t.team_id = r.team_id
           LEFT JOIN companies c ON c.company_id = r.company_id
               WHERE {' AND '.join(where)}
            ORDER BY r.name NULLS LAST, r.email
               LIMIT %s"""
    data = rows(sql, tuple(params) + (limit,))
    return {"people": data, "count": len(data)}


@app.get("/api/cohort/patterns")
def cohort_patterns(doubt_only: bool = False) -> dict[str, Any]:
    where = "WHERE doubt_passed = TRUE" if doubt_only else ""
    data = rows(
        f"""SELECT pattern_id, name, conditions_json, evidence_json,
                   hit_rate, n_observations, bh_p_value, oos_hit_rate,
                   robust, doubt_passed, discovered_at
              FROM pattern_library
              {where}
             ORDER BY doubt_passed DESC, hit_rate DESC NULLS LAST"""
    )
    return {"patterns": data, "count": len(data)}


def _require_admin(request: Request) -> dict:
    """Ensure the authenticated caller is an admin."""
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me or me[0]["role"] != "admin":
        raise HTTPException(403, "admin only")
    return me[0]

@app.post("/api/admin/cohort/snapshot")
def admin_run_snapshot(request: Request) -> dict[str, Any]:
    """Manually trigger a cohort snapshot (admin only)."""
    _require_admin(request)
    from app.cohort_jobs import run_snapshot
    return run_snapshot()


@app.post("/api/admin/cohort/pattern-hunt")
def admin_run_pattern_hunt(background_tasks: BackgroundTasks, request: Request) -> dict[str, Any]:
    """Manually trigger the pattern hunter in the background (admin only)."""
    _require_admin(request)
    from app.cohort_jobs import run_pattern_hunt
    background_tasks.add_task(run_pattern_hunt)
    return {"ok": True, "message": "Pattern hunt started in background. Check events log for results."}


@app.post("/api/admin/backup")
def admin_run_backup(background_tasks: BackgroundTasks, request: Request) -> dict[str, Any]:
    """S092: Manually trigger a Postgres backup (admin only)."""
    _require_admin(request)
    background_tasks.add_task(_run_backup)
    return {"ok": True, "message": "Backup started in background. Check events log for db.backup_complete."}


# ---------------------------------------------------------------------------
# Teams (executive dashboard data)
# ---------------------------------------------------------------------------


@app.get("/api/companies")
def companies_list(request: Request) -> dict[str, Any]:
    """All companies with rolled-up aggregates across their teams."""
    base = rows("SELECT company_id, name, industry FROM companies ORDER BY name")
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role, company_id FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me:
        raise HTTPException(401, "not authenticated")
    if me[0]["role"] != "admin":
        if me[0]["role"] in ("ceo", "hr") and me[0]["company_id"]:
            base = [c for c in base if c["company_id"] == me[0]["company_id"]]
        else:
            raise HTTPException(403, "forbidden")
    out: list[dict[str, Any]] = []
    for c in base:
        cid = c["company_id"]
        n_teams = scalar(
            "SELECT count(*) FROM teams WHERE company_id = %s", (cid,)
        ) or 0
        n_reps = scalar(
            "SELECT count(*) FROM respondents WHERE company_id = %s AND role='sales_person'",
            (cid,),
        ) or 0
        avg = scalar(
            """SELECT coalesce(avg(
                       (s.cognitive_empathy + s.eq + s.pressure_composure + s.storytelling) / 4.0
                     ), 0) * 100
                 FROM audit_scores s
                 JOIN audits a USING (audit_id)
                 JOIN respondents r ON r.respondent_id = a.respondent_id
                WHERE r.company_id = %s""",
            (cid,),
        ) or 0
        elite = scalar(
            """SELECT count(*) FROM audit_scores s
                 JOIN audits a USING (audit_id)
                 JOIN respondents r ON r.respondent_id = a.respondent_id
                WHERE r.company_id = %s
                  AND s.cognitive_empathy >= 0.85 AND s.eq >= 0.85
                  AND s.pressure_composure >= 0.85 AND s.storytelling >= 0.85""",
            (cid,),
        ) or 0
        at_risk = scalar(
            """SELECT count(*) FROM (
                 SELECT bc.audit_id FROM band_classifications bc
                   JOIN audits a USING (audit_id)
                   JOIN respondents r ON r.respondent_id = a.respondent_id
                  WHERE r.company_id = %s AND bc.band = 'developing'
                  GROUP BY bc.audit_id HAVING count(*) >= 2
               ) sub""",
            (cid,),
        ) or 0
        bands = {b: 0 for b in ("elite", "performing", "practising", "developing")}
        for r in rows(
            """SELECT bc.band, count(*) AS n
                 FROM band_classifications bc
                 JOIN audits a USING (audit_id)
                 JOIN respondents r ON r.respondent_id = a.respondent_id
                WHERE r.company_id = %s
                GROUP BY bc.band""",
            (cid,),
        ):
            bands[r["band"]] = int(r["n"])
        out.append({
            **c,
            "n_teams":         int(n_teams),
            "n_respondents":   int(n_reps),
            "avg_score_100":   round(float(avg), 1),
            "elite_count":     int(elite),
            "at_risk_count":   int(at_risk),
            "band_elite":      bands["elite"],
            "band_performing": bands["performing"],
            "band_practising": bands["practising"],
            "band_developing": bands["developing"],
        })
    return {"companies": out}


@app.get("/api/companies/{company_id}/teams")
def company_teams(company_id: int, request: Request) -> dict[str, Any]:
    """Teams under a single company. Strict per-company scoping."""
    _require_company_access(request, company_id)
    company = rows(
        "SELECT * FROM companies WHERE company_id = %s", (company_id,)
    )
    if not company:
        raise HTTPException(404, "company not found")
    teams = rows(
        """SELECT t.team_id, t.name, t.role_label, t.region,
                  t.contact_name, t.contact_email, t.contact_mobile,
                  (SELECT count(*) FROM respondents r
                     WHERE r.team_id = t.team_id AND r.role='sales_person') AS n_respondents,
                  -- Director (if any) of this team
                  (SELECT json_build_object(
                            'respondent_id', sd.respondent_id,
                            'name', sd.name, 'email', sd.email,
                            'mobile', sd.mobile, 'role', sd.role)
                     FROM respondents sd
                    WHERE sd.team_id = t.team_id
                      AND sd.role IN ('sales_director','learning_development')
                    ORDER BY (sd.role = 'sales_director') DESC, sd.created_at
                    LIMIT 1) AS director
             FROM teams t
            WHERE t.company_id = %s
            ORDER BY n_respondents DESC NULLS LAST, t.name""",
        (company_id,),
    )
    # Company-level execs (CEO, HR, L&D) — i.e. main contacts not pinned to a single team
    execs = rows(
        """SELECT respondent_id, name, first_name, last_name, email, mobile,
                  role, job_title, team_id
             FROM respondents
            WHERE company_id = %s
              AND role IN ('ceo','hr','learning_development','sales_director')
            ORDER BY
              CASE role
                WHEN 'ceo' THEN 1 WHEN 'hr' THEN 2
                WHEN 'learning_development' THEN 3
                WHEN 'sales_director' THEN 4 ELSE 5 END,
              name""",
        (company_id,),
    )
    return {"company": company[0], "teams": teams, "execs": execs}


@app.get("/api/teams")
def teams_list(request: Request) -> dict[str, Any]:
    """All teams the operator owns, each with per-team aggregates.

    Strict per-team scoping: every aggregate is filtered by team_id. Zero
    bleed between teams.
    """
    base = rows(
        """SELECT t.team_id, t.name, t.organisation, t.role_label,
                  t.region, t.country,
                  t.company_id, c.name AS company_name,
                  (SELECT count(*) FROM respondents r
                     WHERE r.team_id = t.team_id AND r.role='sales_person') AS n_respondents
             FROM teams t
        LEFT JOIN companies c ON c.company_id = t.company_id
            ORDER BY n_respondents DESC NULLS LAST, t.name"""
    )
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role, company_id FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me:
        raise HTTPException(401, "not authenticated")
    if me[0]["role"] != "admin":
        if me[0]["role"] in ("ceo", "hr") and me[0]["company_id"]:
            base = [t for t in base if t["company_id"] == me[0]["company_id"]]
        else:
            raise HTTPException(403, "forbidden")
    out: list[dict[str, Any]] = []
    for t in base:
        tid = t["team_id"]
        # Average across all 4 dimensions (× 100)
        avg = scalar(
            """SELECT coalesce(avg(
                       (s.cognitive_empathy + s.eq + s.pressure_composure + s.storytelling) / 4.0
                     ), 0) * 100
                 FROM audit_scores s
                 JOIN audits a USING (audit_id)
                 JOIN respondents r ON r.respondent_id = a.respondent_id
                WHERE r.team_id = %s
                AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                    WHERE aa.respondent_id = r.respondent_id
                    ORDER BY aa.started_at DESC LIMIT 1)
                AND r.role = 'sales_person'""",
            (tid,),
        ) or 0
        elite = scalar(
            """SELECT count(*) FROM audit_scores s
                 JOIN audits a USING (audit_id)
                 JOIN respondents r ON r.respondent_id = a.respondent_id
                WHERE r.team_id = %s
                  AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                      WHERE aa.respondent_id = r.respondent_id
                      ORDER BY aa.started_at DESC LIMIT 1)
                  AND r.role = 'sales_person'
                  AND s.cognitive_empathy >= 0.85 AND s.eq >= 0.85
                  AND s.pressure_composure >= 0.85 AND s.storytelling >= 0.85""",
            (tid,),
        ) or 0
        at_risk = scalar(
            """SELECT count(*) FROM (
                 SELECT bc.audit_id FROM band_classifications bc
                   JOIN audits a USING (audit_id)
                   JOIN respondents r ON r.respondent_id = a.respondent_id
                  WHERE r.team_id = %s AND bc.band = 'developing'
                  AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                      WHERE aa.respondent_id = r.respondent_id
                      ORDER BY aa.started_at DESC LIMIT 1)
                  AND r.role = 'sales_person'
                  GROUP BY bc.audit_id HAVING count(*) >= 2
               ) sub""",
            (tid,),
        ) or 0
        bands = {b: 0 for b in ("elite", "performing", "practising", "developing")}
        for r in rows(
            """SELECT bc.band, count(*) AS n
                 FROM band_classifications bc
                 JOIN audits a USING (audit_id)
                 JOIN respondents r ON r.respondent_id = a.respondent_id
                WHERE r.team_id = %s
                AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                    WHERE aa.respondent_id = r.respondent_id
                    ORDER BY aa.started_at DESC LIMIT 1)
                AND r.role = 'sales_person'
                GROUP BY bc.band""",
            (tid,),
        ):
            bands[r["band"]] = int(r["n"])
        modal_band = max(bands, key=lambda k: bands[k]) if any(bands.values()) else None
        out.append({
            **t,
            "n_respondents":   int(t["n_respondents"] or 0),
            "avg_score_100":   round(float(avg), 1),
            "elite_count":     int(elite),
            "at_risk_count":   int(at_risk),
            "modal_band":      modal_band,
            "band_elite":      bands["elite"],
            "band_performing": bands["performing"],
            "band_practising": bands["practising"],
            "band_developing": bands["developing"],
        })
    return {"teams": out}


def _team_or_404(team_id: int) -> dict:
    t = rows("SELECT * FROM teams WHERE team_id = %s", (team_id,))
    if not t:
        raise HTTPException(404, "team not found")
    return t[0]


def _require_team_access(request: Request, team_id: int) -> dict:
    """Ensure the authenticated caller may see this team's data.
    Admin sees every team. ceo/hr/learning_development are scoped to
    their own company (all teams in it). sales_director is scoped to
    their own team only. Anyone else, or no valid session, is refused."""
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows(
        "SELECT role, team_id, company_id FROM respondents WHERE respondent_id = %s",
        (int(caller["sub"]),),
    )
    if not me:
        raise HTTPException(401, "not authenticated")
    role = me[0]["role"]
    if role == "admin":
        return me[0]
    team = _team_or_404(team_id)
    if role == "sales_director":
        if me[0]["team_id"] == team_id:
            return me[0]
        raise HTTPException(403, "forbidden")
    if role in ("ceo", "hr", "learning_development"):
        if me[0]["company_id"] and me[0]["company_id"] == team.get("company_id"):
            return me[0]
        raise HTTPException(403, "forbidden")
    raise HTTPException(403, "forbidden")


def _require_company_access(request: Request, company_id: int) -> dict:
    # Admin sees every company; ceo/hr are scoped to their own company only.
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows(
        "SELECT role, company_id FROM respondents WHERE respondent_id = %s",
        (int(caller["sub"]),),
    )
    if not me:
        raise HTTPException(401, "not authenticated")
    role = me[0]["role"]
    if role == "admin":
        return me[0]
    if role in ("ceo", "hr"):
        if me[0]["company_id"] and me[0]["company_id"] == company_id:
            return me[0]
        raise HTTPException(403, "forbidden")
    raise HTTPException(403, "forbidden")
@app.get("/api/teams/{team_id}/overview")
def team_overview(team_id: int, request: Request) -> dict[str, Any]:
    _require_team_access(request, team_id)
    t = _team_or_404(team_id)
    director = rows(
        """SELECT respondent_id, name, email, role
             FROM respondents
            WHERE team_id = %s
              AND role IN ('sales_director','learning_development','ceo','hr')
            ORDER BY (role='sales_director') DESC, created_at ASC
            LIMIT 1""",
        (team_id,),
    )
    director_row = director[0] if director else None
    n = scalar(
        "SELECT count(*) FROM respondents WHERE team_id = %s AND role='sales_person'",
        (team_id,),
    ) or 0
    scores = rows(
        """SELECT avg(cognitive_empathy) AS ce, avg(eq) AS eq,
                  avg(pressure_composure) AS pc, avg(storytelling) AS st
             FROM audit_scores s
             JOIN audits a USING (audit_id)
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s
            AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                WHERE aa.respondent_id = r.respondent_id
                ORDER BY aa.started_at DESC LIMIT 1)
            AND r.role = 'sales_person'""",
        (team_id,),
    )[0]
    avg_overall = None
    if scores["ce"] is not None:
        avg_overall = (scores["ce"] + scores["eq"]
                       + scores["pc"] + scores["st"]) / 4.0
    elite_count = scalar(
        """SELECT count(*) FROM audit_scores s
             JOIN audits a USING (audit_id)
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s
              AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                                  WHERE aa.respondent_id = r.respondent_id
                                  ORDER BY aa.started_at DESC LIMIT 1)
              AND r.role = 'sales_person'
              AND s.cognitive_empathy >= 0.85 AND s.eq >= 0.85
              AND s.pressure_composure >= 0.85 AND s.storytelling >= 0.85""",
        (team_id,),
    ) or 0
    at_risk = scalar(
        """SELECT count(DISTINCT audit_id) FROM (
             SELECT bc.audit_id, count(*) AS n_dev
               FROM band_classifications bc
               JOIN audits a USING (audit_id)
               JOIN respondents r ON r.respondent_id = a.respondent_id
              WHERE r.team_id = %s AND bc.band = 'developing'
              AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                                  WHERE aa.respondent_id = r.respondent_id
                                  ORDER BY aa.started_at DESC LIMIT 1)
              AND r.role = 'sales_person'
              GROUP BY bc.audit_id
              HAVING count(*) >= 2
           ) sub""",
        (team_id,),
    ) or 0
    biggest_gap = None
    dims = {
        "Cognitive Empathy": scores["ce"],
        "EQ": scores["eq"],
        "Pressure Composure": scores["pc"],
        "Storytelling": scores["st"],
    }
    if any(v is not None for v in dims.values()):
        biggest_name, biggest_val = min(
            ((k, v) for k, v in dims.items() if v is not None),
            key=lambda kv: kv[1],
        )
        biggest_band = _band_for(biggest_val)
        biggest_gap = {
            "trait": biggest_name,
            "score_100": round(float(biggest_val) * 100, 1),
            "band": biggest_band,
        }
    return {
        "team": t,
        "month_label": datetime.utcnow().strftime("%B %Y"),
        "n_respondents": int(n),
        "team_average_score_100": (
            round(avg_overall * 100, 1) if avg_overall is not None else None
        ),
        "elite_performers": int(elite_count),
        "at_risk_reps": int(at_risk),
        "biggest_gap": biggest_gap,
        "director": director_row,
    }


def _band_for(score: float) -> str:
    if score >= 0.85: return "Elite"
    if score >= 0.65: return "Performing"
    if score >= 0.40: return "Practising"
    return "Developing"


@app.get("/api/teams/{team_id}/distribution")
def team_distribution(team_id: int, request: Request) -> dict[str, Any]:
    _require_team_access(request, team_id)
    _team_or_404(team_id)
    raw = rows(
        """SELECT bc.dimension, bc.band, count(*) AS n
             FROM band_classifications bc
             JOIN audits a USING (audit_id)
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s
              AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                                  WHERE aa.respondent_id = r.respondent_id
                                  ORDER BY aa.started_at DESC LIMIT 1)
              AND r.role = 'sales_person'
            GROUP BY bc.dimension, bc.band""",
        (team_id,),
    )
    order = ["cognitive_empathy", "eq", "pressure_composure", "storytelling"]
    out = []
    for dim in order:
        bands = {"elite": 0, "performing": 0, "practising": 0, "developing": 0}
        for r in raw:
            if r["dimension"] == dim:
                bands[r["band"]] = int(r["n"])
        out.append({
            "dimension": dim,
            "dimension_label": {
                "cognitive_empathy": "Cognitive Empathy",
                "eq": "EQ",
                "pressure_composure": "Pressure Composure",
                "storytelling": "Storytelling",
            }[dim],
            **bands,
            "total": sum(bands.values()),
        })
    return {"distribution": out}


@app.get("/api/teams/{team_id}/trait-averages")
def team_trait_averages(team_id: int, request: Request) -> dict[str, Any]:
    _require_team_access(request, team_id)
    _team_or_404(team_id)
    row = rows(
        """SELECT avg(cognitive_empathy) AS cognitive_empathy,
                  avg(eq) AS eq,
                  avg(pressure_composure) AS pressure_composure,
                  avg(storytelling) AS storytelling
             FROM audit_scores s
             JOIN audits a USING (audit_id)
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s
            AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                WHERE aa.respondent_id = r.respondent_id
                ORDER BY aa.started_at DESC LIMIT 1)
            AND r.role = 'sales_person'""",
        (team_id,),
    )[0]
    labels = {
        "cognitive_empathy": "Cognitive Empathy",
        "eq": "EQ",
        "pressure_composure": "Pressure Composure",
        "storytelling": "Storytelling",
    }
    out = []
    for k, v in row.items():
        if v is None:
            continue
        v = float(v)
        out.append({
            "trait": labels[k],
            "score_100": round(v * 100, 1),
            "band": _band_for(v),
        })
    return {"trait_averages": out}


@app.get("/api/teams/{team_id}/archetypes")
def team_archetypes(team_id: int, request: Request) -> dict[str, Any]:
    _require_team_access(request, team_id)
    _team_or_404(team_id)
    data = rows(
        """SELECT ar.code, ar.name, count(*) AS n
             FROM archetype_assignments aa
             JOIN archetypes ar USING (archetype_id)
             JOIN audits a ON a.audit_id = aa.audit_id
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s
            AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                WHERE aa.respondent_id = r.respondent_id
                ORDER BY aa.started_at DESC LIMIT 1)
            AND r.role = 'sales_person'
            GROUP BY ar.code, ar.name
            ORDER BY n DESC""",
        (team_id,),
    )
    return {"archetypes": data}


@app.get("/api/teams/{team_id}/interventions")
def team_interventions(team_id: int, request: Request) -> dict[str, Any]:
    _require_team_access(request, team_id)
    """Per spec §7B: top 3 at-risk segments by count + 1 pair-top-performers.

    M6 will swap this for Claude-API generated cards. The prototype derives
    cards directly from team data so the wireframe is true to the rendering
    pipeline (no fabrication: every number ties back to a band_classifications
    or audit_scores row).
    """
    _team_or_404(team_id)
    # Top 3 (dimension, developing-count) pairs
    dev = rows(
        """SELECT bc.dimension, count(*) AS n
             FROM band_classifications bc
             JOIN audits a USING (audit_id)
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s AND bc.band = 'developing'
            AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                WHERE aa.respondent_id = r.respondent_id
                ORDER BY aa.started_at DESC LIMIT 1)
            AND r.role = 'sales_person'
            GROUP BY bc.dimension
            ORDER BY n DESC
            LIMIT 3""",
        (team_id,),
    )
    label_for = {
        "cognitive_empathy": "Cognitive Empathy",
        "eq": "EQ",
        "pressure_composure": "Pressure Composure",
        "storytelling": "Storytelling",
    }
    intervention_for = {
        "cognitive_empathy":
            "Run buyer-state reading drills (paired role plays, video review). "
            "Pair each rep with an Edge-Builder peer in cohort for 4 weeks.",
        "eq":
            "Module: regulating under tension. Add weekly breath + reframe drill before "
            "Tuesday pipeline call. Aim is calmer answers under pricing pressure.",
        "pressure_composure":
            "High-stakes simulation. Run mock close-out calls with rolling objections, "
            "score with a senior rep, debrief same day.",
        "storytelling":
            "Three-act narrative pattern, applied to their top three current deals. "
            "Coach until every rep can land a 60-second buyer-context story cold.",
    }
    out = []
    for d in dev:
        out.append({
            "headline":
                f"{int(d['n'])} reps, {label_for[d['dimension']]} (Developing)",
            "body":
                f"{int(d['n'])} reps score below 40/100 on {label_for[d['dimension']]}. "
                f"{intervention_for[d['dimension']]}",
            "kind": "at_risk",
        })
    # Pair top performers
    elite = scalar(
        """SELECT count(*) FROM audit_scores s
             JOIN audits a USING (audit_id)
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s
              AND a.audit_id = (SELECT aa.audit_id FROM audits aa
                  WHERE aa.respondent_id = r.respondent_id
                  ORDER BY aa.started_at DESC LIMIT 1)
              AND r.role = 'sales_person'
              AND s.cognitive_empathy >= 0.85 AND s.eq >= 0.85
              AND s.pressure_composure >= 0.85 AND s.storytelling >= 0.85""",
        (team_id,),
    ) or 0
    if int(elite) > 0:
        leverage_headline = f"Pair your top {int(elite)} Elite performers"
        leverage_body = (
            "Pair each Elite rep with two at-risk reps as in-quarter coaches. "
            "Light load on the Elites, fast lift for the cohort, and you bank "
            "ROI evidence for the re-audit at 3 months."
        )
    else:
        leverage_headline = "Build your first Elite performers"
        leverage_body = (
            "No reps currently score 85+ across all four traits. "
            "Focus the top quartile on closing their biggest single gap -- "
            "one trait to Elite creates a coaching anchor for the rest of the team."
        )
    out.append({"headline": leverage_headline, "body": leverage_body, "kind": "leverage"})
    return {"interventions": out}


@app.get("/api/teams/{team_id}/export.pdf")
def team_export_pdf(team_id: int, request: Request) -> StreamingResponse:
    _require_team_access(request, team_id)
    """Multi-page executive summary PDF. Includes:
      Page 1: Header, director, KPI strip, distribution, trait averages
      Page 2: Archetype breakdown, every intervention (full bodies)
      Page 3+: Full team roster (consent-gated identity)
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdf_canvas

    t = _team_or_404(team_id)
    overview = team_overview(team_id)
    distribution = team_distribution(team_id)["distribution"]
    trait_avg    = team_trait_averages(team_id)["trait_averages"]
    archetypes   = team_archetypes(team_id)["archetypes"]
    interventions = team_interventions(team_id)["interventions"]
    roster        = team_roster(team_id)["roster"]
    director      = overview.get("director")
    company_name  = None
    if t.get("company_id"):
        cr = rows("SELECT name FROM companies WHERE company_id = %s", (t["company_id"],))
        if cr:
            company_name = cr[0]["name"].replace("Demo: ", "")

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    margin = 18 * mm
    y = [H - margin]
    page_num = [1]

    def new_page():
        # Footer on the current page before turning
        c.setFillColorRGB(0.55, 0.55, 0.60)
        c.setFont("Helvetica", 8)
        c.drawCentredString(
            W / 2, 12 * mm,
            f"decipher.com.au · Confidential, For "
            f"{t.get('role_label') or 'Executive'} Use Only · "
            f"{overview['month_label']} · Page {page_num[0]}",
        )
        c.showPage()
        page_num[0] += 1
        y[0] = H - margin

    def ensure_room(h):
        if y[0] - h < 25 * mm:
            new_page()

    def text(s, size=10, bold=False, colour=(0, 0, 0), x=margin):
        ensure_room(size + 4)
        c.setFillColorRGB(*colour)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(x, y[0], s)
        y[0] -= size + 4

    def wrapped(body, size=9, max_chars=110, indent="     ", colour=(0.4, 0.4, 0.45)):
        words = body.split()
        line = ""
        for w in words:
            if len(line) + len(w) + 1 > max_chars:
                text(indent + line, size=size, colour=colour)
                line = w
            else:
                line = (line + " " + w).strip()
        if line:
            text(indent + line, size=size, colour=colour)

    def hr():
        ensure_room(8)
        c.setStrokeColorRGB(0.85, 0.85, 0.87)
        c.line(margin, y[0], W - margin, y[0])
        y[0] -= 8

    # ===================================================================
    # PAGE 1 - Header / director / KPI strip / distribution / trait avg
    # ===================================================================
    text(f"{t['name']} · Decipher DNA Audit", size=18, bold=True)
    sub = f"{t.get('role_label') or 'Executive'} Dashboard, " \
          f"{overview['n_respondents']} Respondents · {overview['month_label']}"
    text(sub, size=10, colour=(0.4, 0.4, 0.45))
    if company_name:
        text(f"Company: {company_name}", size=10, colour=(0.4, 0.4, 0.45))
    if director:
        director_line = f"Director: {director.get('name') or director.get('email')} · {director.get('email')}"
        text(director_line, size=10, colour=(0.4, 0.4, 0.45))
    if t.get("region") or t.get("country"):
        text(f"Region: {t.get('region') or '-'} · {t.get('country') or 'Australia'}",
             size=10, colour=(0.4, 0.4, 0.45))
    hr()

    # KPI line
    biggest_gap_line = (
        f"{overview['biggest_gap']['trait']} {overview['biggest_gap']['score_100']}/100 "
        f"({overview['biggest_gap']['band']})"
        if overview.get("biggest_gap") else "-"
    )
    text(
        f"Team avg {overview['team_average_score_100']}/100   "
        f"Elite {overview['elite_performers']}   "
        f"At-risk {overview['at_risk_reps']}   "
        f"Biggest gap: {biggest_gap_line}",
        size=11, bold=True,
    )
    y[0] -= 4
    hr()

    # Distribution
    text("Score distribution by band", size=12, bold=True)
    band_colours = {
        "elite":      (0.20, 0.78, 0.35),
        "performing": (0.23, 0.51, 0.91),
        "practising": (0.89, 0.63, 0.23),
        "developing": (0.78, 0.24, 0.24),
    }
    bar_x = margin
    bar_w = W - 2 * margin
    for d in distribution:
        text(d["dimension_label"], size=10, bold=True)
        bar_h = 12
        y[0] -= 2
        ensure_room(bar_h + 12)
        total = d["total"] or 1
        offset = 0
        for band in ("elite", "performing", "practising", "developing"):
            seg = (d.get(band, 0) / total) * bar_w
            r, g, b = band_colours[band]
            c.setFillColorRGB(r, g, b)
            c.rect(bar_x + offset, y[0] - bar_h, seg, bar_h, fill=1, stroke=0)
            offset += seg
        c.setFillColorRGB(0.6, 0.6, 0.65)
        c.setFont("Helvetica", 8)
        c.drawString(
            bar_x, y[0] - bar_h - 11,
            f"Elite {d.get('elite',0)} · Performing {d.get('performing',0)} · "
            f"Practising {d.get('practising',0)} · Developing {d.get('developing',0)}",
        )
        y[0] -= bar_h + 16

    hr()
    # Trait averages
    text("Team trait averages", size=12, bold=True)
    for tr in trait_avg:
        text(f"  {tr['trait']:28} {tr['score_100']:>5} /100   ({tr['band']})", size=10)

    # ===================================================================
    # PAGE 2 - Archetype breakdown + every intervention with full body
    # ===================================================================
    new_page()
    text("Archetype breakdown", size=14, bold=True)
    arch_total = sum(a["n"] for a in archetypes) or 1
    for a in archetypes:
        pct = (a["n"] / arch_total) * 100
        text(f"  {a['name']:28} {a['n']:>4}  ({pct:.1f}%)", size=10)
    y[0] -= 6
    hr()

    text("Priority coaching interventions", size=14, bold=True)
    if not interventions:
        text("  (none yet)", size=10, colour=(0.4, 0.4, 0.45))
    for it in interventions:
        ensure_room(40)
        tone = (0.20, 0.78, 0.35) if it.get("kind") == "leverage" else (0.78, 0.24, 0.24)
        c.setFillColorRGB(*tone)
        c.rect(margin - 4, y[0] - 2, 3, 14, fill=1, stroke=0)
        text(f"  {it['headline']}", size=11, bold=True)
        wrapped(it["body"], size=10, indent="     ")
        y[0] -= 4

    # ===================================================================
    # PAGE 3+ - Full team roster (consent-gated identity)
    # ===================================================================
    new_page()
    text(f"Team roster ({len(roster)} respondents)", size=14, bold=True)
    text("Anonymised rows have not consented to share individual identity.",
         size=9, colour=(0.4, 0.4, 0.45))
    y[0] -= 4

    # Table header
    cols = [("Name", 0), ("Email", 95), ("Archetype", 270),
            ("CE", 360), ("EQ", 390), ("PC", 420), ("ST", 450), ("Overall", 490)]
    c.setFillColorRGB(0.3, 0.3, 0.35)
    c.setFont("Helvetica-Bold", 9)
    for lbl, dx in cols:
        c.drawString(margin + dx, y[0], lbl)
    y[0] -= 12
    c.setStrokeColorRGB(0.85, 0.85, 0.87)
    c.line(margin, y[0] + 4, W - margin, y[0] + 4)

    def fmt(v):
        return f"{int(v * 100)}" if v is not None else "·"

    for r in roster:
        ensure_room(14)
        c.setFillColorRGB(0.10, 0.10, 0.12)
        c.setFont("Helvetica", 9)
        c.drawString(margin + 0,   y[0], (r.get("name") or "-")[:28])
        c.setFillColorRGB(0.45, 0.45, 0.48)
        c.drawString(margin + 95,  y[0], (r.get("email") or "-")[:40])
        c.setFillColorRGB(0.10, 0.10, 0.12)
        c.drawString(margin + 270, y[0], (r.get("archetype_name") or "-")[:14])
        c.drawString(margin + 360, y[0], fmt(r.get("cognitive_empathy")))
        c.drawString(margin + 390, y[0], fmt(r.get("eq")))
        c.drawString(margin + 420, y[0], fmt(r.get("pressure_composure")))
        c.drawString(margin + 450, y[0], fmt(r.get("storytelling")))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin + 490, y[0], fmt(r.get("overall")))
        y[0] -= 12

    # Footer for the final page
    new_page()
    # Pop the blank page we just created
    page_num[0] -= 1

    c.save()
    buf.seek(0)
    fname = f"{t['name'].lower().replace(' ', '-')}-decipher-{datetime.utcnow().strftime('%Y-%m')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ---------------------------------------------------------------------------
# Audit invites (send invite from within the dashboard)
# ---------------------------------------------------------------------------

import secrets
import smtplib
from email.message import EmailMessage


class InviteIn(BaseModel):
    email:      str
    first_name: str | None = None
    last_name:  str | None = None
    mobile:     str | None = None
    team_id:    int | None = None
    company_id: int | None = None
    notes:      str | None = None
    audit_version_code: str = "media_sales_v1"


def _resolve_caller_role(invited_by_email: str | None, invited_by_role: str | None) -> str:
    """Prototype permission resolver. Real auth lands in M5.
    Trusts the caller's claimed role only if their email matches a
    real respondent record with that role; otherwise falls back to
    sales_person (least privilege)."""
    if invited_by_email:
        r = rows("SELECT role FROM respondents WHERE email = %s", (invited_by_email,))
        if r:
            return r[0]["role"]
    return "sales_person"


def _send_invite_email(to_email: str, first_name: str | None, link: str) -> None:
    """Drop an HTML invite into Mailpit (local SMTP). Steve sends from
    his real Gmail later; project rule 17 forbids sending from his
    account via tooling."""
    host = os.environ.get("DECIPHER_MAIL_HOST", "127.0.0.1")
    port = int(os.environ.get("DECIPHER_MAIL_PORT", "1025"))
    msg = EmailMessage()
    msg["From"] = "noreply@decipher.com.au"
    msg["To"] = to_email
    msg["Subject"] = "Your Decipher DNA Audit invite"
    name = first_name or "there"
    msg.set_content(
        f"Hi {name},\n\nYou've been invited to take the Decipher DNA "
        f"Audit. It takes 15 minutes.\n\nStart here: {link}\n\n"
        f"This link is personal to you and expires in 30 days."
    )
    msg.add_alternative(
        f"""<html><body style='font-family:-apple-system,sans-serif;color:#1c1c1e'>
        <p>Hi {name},</p>
        <p>You've been invited to take the <strong>Decipher DNA Audit</strong>.
        It takes about 15 minutes.</p>
        <p><a href='{link}' style='background:#1B8A4F;color:#fff;padding:12px 18px;
        text-decoration:none;border-radius:6px;font-weight:600;'>Start the audit</a></p>
        <p style='color:#636366;font-size:12px;'>This link is personal to you and
        expires in 30 days.</p>
        </body></html>""",
        subtype="html",
    )
    with smtplib.SMTP(host, port, timeout=5) as s:
        s.send_message(msg)


def _enqueue_email_job(audit_id: int, report_id: int, pdf_path: str) -> int:
    """Insert an email job into audit_jobs. Returns the new job_id."""
    import json as _json
    with conn() as c, c.cursor() as cur:
        cur.execute(
            """INSERT INTO audit_jobs (audit_id, job_type, payload)
               VALUES (%s, 'email', %s::jsonb)
               RETURNING job_id""",
            (audit_id, _json.dumps({"report_id": report_id, "pdf_path": pdf_path})),
        )
        return cur.fetchone()[0]


@app.post("/api/audit/invite")
def audit_invite(body: InviteIn, background_tasks: BackgroundTasks, request: Request) -> dict[str, Any]:
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role, email FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me:
        raise HTTPException(401, "not authenticated")
    caller_role = me[0]["role"]
    if caller_role not in INVITE_ROLES:
        raise HTTPException(
            403,
            f"role '{caller_role}' cannot send audit invites. "
            f"Allowed: {sorted(INVITE_ROLES)}",
        )
    # Find or upsert respondent
    existing = rows("SELECT respondent_id FROM respondents WHERE email = %s",
                    (body.email,))
    name = " ".join([n for n in (body.first_name, body.last_name) if n]) or None
    if existing:
        rid = existing[0]["respondent_id"]
        with conn() as c:
            cur = c.cursor()
            cur.execute(
                """UPDATE respondents
                      SET first_name = COALESCE(%s, first_name),
                          last_name  = COALESCE(%s, last_name),
                          mobile     = COALESCE(%s, mobile),
                          team_id    = COALESCE(%s, team_id),
                          company_id = COALESCE(%s, company_id),
                          name       = COALESCE(%s, name)
                    WHERE respondent_id = %s""",
                (body.first_name, body.last_name, body.mobile,
                 body.team_id, body.company_id, name, rid),
            )
    else:
        with conn() as c:
            cur = c.cursor()
            cur.execute(
                """INSERT INTO respondents
                       (email, name, first_name, last_name, mobile, team_id,
                        company_id, role, source)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,'sales_person','invite')
                   RETURNING respondent_id""",
                (body.email, name, body.first_name, body.last_name,
                 body.mobile, body.team_id, body.company_id),
            )
            rid = cur.fetchone()[0]

    token = secrets.token_urlsafe(32)
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO audit_invites
                   (respondent_id, email, first_name, last_name, mobile,
                    team_id, company_id, audit_version_code, token_hash,
                    invited_by_email, notes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING invite_id, sent_at, expires_at""",
            (rid, body.email, body.first_name, body.last_name, body.mobile,
         body.team_id, body.company_id, body.audit_version_code,
                          token, me[0]["email"], body.notes),
        )
        invite = cur.fetchone()
        invite_id, sent_at, expires_at = invite

    web_port = os.environ.get("DECIPHER_WEB_PORT", "55173")
    base_url = os.environ.get("DECIPHER_PUBLIC_URL", f"http://127.0.0.1:{web_port}")
    link = f"{base_url}/audit/start?invite={token}"
    delivered = True; err = None; background_tasks.add_task(_send_invite_email, body.email, body.first_name, link)

    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO events_log (actor, action, severity, subject_id, payload)
               VALUES ('admin', 'audit.invited', %s, %s, %s::jsonb)""",
            ("info" if delivered else "warning",
             str(invite_id),
             json.dumps({"email": body.email, "delivered": delivered,
                         "team_id": body.team_id, "error": err,
                         "link": link})),
        )
    return {
        "ok": True, "invite_id": invite_id, "respondent_id": rid,
        "link": link, "delivered": delivered, "error": err,
        "sent_at": str(sent_at), "expires_at": str(expires_at),
    }


@app.get("/api/audit/invites")
def list_invites(request: Request, team_id: int | None = None, company_id: int | None = None,
                  limit: int = 100) -> dict[str, Any]:
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role, team_id, company_id FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me:
        raise HTTPException(401, "not authenticated")
    caller_role = me[0]["role"]
    if caller_role == "admin":
        pass
    elif caller_role == "sales_director":
        team_id = me[0]["team_id"]
        company_id = None
    elif caller_role in ("ceo", "hr", "learning_development"):
        company_id = me[0]["company_id"]
        team_id = None
    else:
        raise HTTPException(403, "forbidden")
    where = ["1=1"]
    params: list[Any] = []
    if team_id is not None:
        where.append("team_id = %s"); params.append(team_id)
    if company_id is not None:
        where.append("company_id = %s"); params.append(company_id)
    sql = f"""SELECT invite_id, email, first_name, last_name, mobile, team_id,
                     company_id, sent_at, expires_at, accepted_at, audit_id
                FROM audit_invites
               WHERE {' AND '.join(where)}
            ORDER BY sent_at DESC
               LIMIT %s"""
    return {"invites": rows(sql, tuple(params) + (limit,))}


# ---------------------------------------------------------------------------
# Mission Control aggregates (time series + region + top archetypes)
# ---------------------------------------------------------------------------


@app.get("/api/mission/series")
def mission_series(days: int = 30) -> dict[str, Any]:
    series = rows(
        """WITH dates AS (
              SELECT generate_series(
                (now()::date - (%s - 1) * interval '1 day'),
                now()::date,
                interval '1 day'
              )::date AS day
           ),
           per_day AS (
              SELECT a.started_at::date AS day,
                     count(*)::int AS n_audits,
                     count(DISTINCT r.audit_id)::int AS n_reports,
                     avg((s.cognitive_empathy+s.eq+s.pressure_composure+s.storytelling)/4.0) * 100
                       AS mean_overall
                FROM audits a
           LEFT JOIN audit_scores s ON s.audit_id = a.audit_id
           LEFT JOIN reports r ON r.audit_id = a.audit_id
               WHERE a.started_at > now() - (%s || ' days')::interval
            GROUP BY a.started_at::date
           )
           SELECT to_char(d.day, 'YYYY-MM-DD') AS day,
                  COALESCE(p.n_audits, 0) AS n_audits,
                  COALESCE(p.n_reports, 0) AS n_reports,
                  COALESCE(round(p.mean_overall::numeric, 1), 0) AS mean_overall
             FROM dates d
        LEFT JOIN per_day p ON p.day = d.day
            ORDER BY d.day""",
        (days, str(days)),
    )
    return {"series": series, "days": days}


@app.get("/api/mission/by-region")
def mission_by_region() -> dict[str, Any]:
    data = rows(
        """SELECT COALESCE(t.region, 'Unset') AS region,
                  count(DISTINCT t.team_id)::int AS teams,
                  count(DISTINCT r.respondent_id) FILTER (WHERE r.role = 'sales_person')::int AS reps,
                  COALESCE(round((avg(
                    (s.cognitive_empathy+s.eq+s.pressure_composure+s.storytelling)/4.0
                  ) FILTER (WHERE r.role = 'sales_person'))::numeric * 100, 1), 0) AS avg_overall
             FROM teams t
        LEFT JOIN respondents r ON r.team_id = t.team_id
        LEFT JOIN audits a ON a.respondent_id = r.respondent_id
                           AND a.audit_id = (SELECT la.audit_id FROM audits la
                                               WHERE la.respondent_id = r.respondent_id
                                               ORDER BY la.started_at DESC LIMIT 1)
        LEFT JOIN audit_scores s ON s.audit_id = a.audit_id
         GROUP BY COALESCE(t.region, 'Unset')
         ORDER BY reps DESC NULLS LAST"""
    )
    return {"regions": data}


@app.get("/api/mission/top-archetypes")
def mission_top_archetypes() -> dict[str, Any]:
    data = rows(
        """SELECT ar.name, count(*)::int AS n
             FROM archetype_assignments aa
             JOIN archetypes ar ON ar.archetype_id = aa.archetype_id
             JOIN audits a ON a.audit_id = aa.audit_id
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.role = 'sales_person'
              AND a.audit_id = (SELECT la.audit_id FROM audits la
                                  WHERE la.respondent_id = r.respondent_id
                                  ORDER BY la.started_at DESC LIMIT 1)
         GROUP BY ar.name
         ORDER BY n DESC
            LIMIT 8"""
    )
    return {"archetypes": data}


@app.get("/api/mission/dim-means")
def mission_dim_means(days: int = 30) -> dict[str, Any]:
    """Mean score per dimension for the requested window. Used by Mission Control
    when the operator selects a time range other than the 30-day bootstrap default.
    """
    days = max(1, min(days, 3650))
    r = rows(
        """SELECT round((avg(s.cognitive_empathy)  * 100)::numeric, 1)::float AS cognitive_empathy,
                  round((avg(s.eq)                 * 100)::numeric, 1)::float AS eq,
                  round((avg(s.pressure_composure) * 100)::numeric, 1)::float AS pressure_composure,
                  round((avg(s.storytelling)       * 100)::numeric, 1)::float AS storytelling,
                  count(*)::int                                                AS n_scored
             FROM audit_scores s
             JOIN audits a ON a.audit_id = s.audit_id
            WHERE a.started_at > now() - (%s || ' days')::interval""",
        (str(days),),
    )
    rec = r[0] if r else {}
    return {
        "cognitive_empathy":  float(rec.get("cognitive_empathy")  or 0),
        "eq":                 float(rec.get("eq")                 or 0),
        "pressure_composure": float(rec.get("pressure_composure") or 0),
        "storytelling":       float(rec.get("storytelling")       or 0),
        "n_scored":           int(rec.get("n_scored")             or 0),
        "days":               days,
    }


# ---------------------------------------------------------------------------
# Funnel: invited -> started -> completed -> scored -> reported
# ---------------------------------------------------------------------------


@app.get("/api/funnel")
def funnel(team_id: int | None = None, company_id: int | None = None,
           days: int = 30) -> dict[str, Any]:
    """Pipeline of audit-takers across the funnel stages."""
    scope_invite: list[str] = ["sent_at > now() - (%s || ' days')::interval"]
    scope_audit:  list[str] = ["a.started_at > now() - (%s || ' days')::interval"]
    params_inv: list[Any] = [str(days)]
    params_aud: list[Any] = [str(days)]
    if team_id is not None:
        scope_invite.append("team_id = %s"); params_inv.append(team_id)
        scope_audit.append("r.team_id = %s"); params_aud.append(team_id)
    if company_id is not None:
        scope_invite.append("company_id = %s"); params_inv.append(company_id)
        scope_audit.append("r.company_id = %s"); params_aud.append(company_id)
    inv_where = " AND ".join(scope_invite)
    aud_where = " AND ".join(scope_audit)

    invited   = scalar(f"SELECT count(*) FROM audit_invites WHERE {inv_where}", tuple(params_inv)) or 0
    accepted  = scalar(f"SELECT count(*) FROM audit_invites WHERE accepted_at IS NOT NULL AND {inv_where}", tuple(params_inv)) or 0
    started   = scalar(
        f"""SELECT count(*) FROM audits a
              JOIN respondents r ON r.respondent_id = a.respondent_id
             WHERE {aud_where}""",
        tuple(params_aud),
    ) or 0
    completed = scalar(
        f"""SELECT count(*) FROM audits a
              JOIN respondents r ON r.respondent_id = a.respondent_id
             WHERE a.status IN ('completed','scored','reported')
               AND {aud_where}""",
        tuple(params_aud),
    ) or 0
    scored    = scalar(
        f"""SELECT count(*) FROM audits a
              JOIN respondents r ON r.respondent_id = a.respondent_id
             WHERE a.status IN ('scored','reported') AND {aud_where}""",
        tuple(params_aud),
    ) or 0
    reported  = scalar(
        f"""SELECT count(*) FROM audits a
              JOIN respondents r ON r.respondent_id = a.respondent_id
             WHERE a.status = 'reported' AND {aud_where}""",
        tuple(params_aud),
    ) or 0

    # Most recent invites, with whether they have been accepted/converted
    inv_rows = rows(
        f"""SELECT invite_id, email, first_name, last_name, team_id, company_id,
                   sent_at, expires_at, accepted_at, audit_id, invited_by_email
              FROM audit_invites
             WHERE {inv_where}
          ORDER BY sent_at DESC
             LIMIT 100""",
        tuple(params_inv),
    )

    return {
        "stages": [
            {"key": "invited",   "label": "Invited",         "n": int(invited)},
            {"key": "accepted",  "label": "Invite opened",   "n": int(accepted)},
            {"key": "started",   "label": "Audit started",   "n": int(started)},
            {"key": "completed", "label": "Audit completed", "n": int(completed)},
            {"key": "scored",    "label": "Scored",          "n": int(scored)},
            {"key": "reported",  "label": "Report sent",     "n": int(reported)},
        ],
        "invite_roles": sorted(INVITE_ROLES),
        "recent_invites": inv_rows,
        "team_id": team_id, "company_id": company_id, "days": days,
    }


class BulkInviteIn(BaseModel):
    team_id:          int | None = None
    company_id:       int | None = None
    audit_version_code: str = "media_sales_v1"
    only_unaudited:   bool = True


@app.post("/api/audit/invite/bulk")
def audit_invite_bulk(body: BulkInviteIn, background_tasks: BackgroundTasks, request: Request) -> dict[str, Any]:
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role, email FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me:
        raise HTTPException(401, "not authenticated")
    caller_role = me[0]["role"]
    if caller_role not in INVITE_ROLES:
        raise HTTPException(403, f"role '{caller_role}' cannot send audit invites")
    where = ["r.role = 'sales_person'"]
    params: list[Any] = []
    if body.team_id is not None:
        where.append("r.team_id = %s"); params.append(body.team_id)
    if body.company_id is not None:
        where.append("r.company_id = %s"); params.append(body.company_id)
    if body.only_unaudited:
        where.append(
            "NOT EXISTS (SELECT 1 FROM audits a WHERE a.respondent_id = r.respondent_id "
            "AND a.status IN ('completed','scored','reported'))"
        )
    targets = rows(
        f"""SELECT respondent_id, email, first_name, last_name, mobile,
                   team_id, company_id
              FROM respondents r
             WHERE {' AND '.join(where)}
             ORDER BY r.respondent_id LIMIT 200""",
        tuple(params),
    )
    sent = 0
    failed = 0
    errors: list[dict[str, Any]] = []
    for t in targets:
        try:
            audit_invite(InviteIn(
                email=t["email"], first_name=t["first_name"],
                last_name=t["last_name"], mobile=t["mobile"],
                team_id=t["team_id"], company_id=t["company_id"],
            invited_by_email=me[0]["email"],
                invited_by_role=caller_role,
                audit_version_code=body.audit_version_code,
            ), background_tasks, request)
            sent += 1
        except HTTPException:
            raise
        except Exception as exc:
            failed += 1
            errors.append({"email": t["email"], "error": str(exc)})
    return {"ok": True, "sent": sent, "failed": failed, "targets": len(targets), "errors": errors}


# ---------------------------------------------------------------------------
# Squarespace export generation (real)
# ---------------------------------------------------------------------------


@app.post("/api/squarespace/generate")
def squarespace_generate() -> dict[str, Any]:
    """S060: Generate a new Squarespace export bundle via Claude Haiku.
    Inserts a stub row first, then calls exports.generate_bundle() which
    populates all files, writes the zip to disk, and updates the row."""
    from app.exports import generate_bundle
    now = datetime.now(timezone.utc)
    placeholder_summary = f"Generating export {now.strftime('%Y-%m-%d %H:%M')}..."
    with conn() as c, c.cursor() as cur:
        cur.execute(
            """INSERT INTO squarespace_exports
                   (generated_at, bundle_path, file_count, size_bytes,
                    summary, cost_usd)
               VALUES (%s,%s,%s,%s,%s,%s)
               RETURNING export_id""",
            (now, "", 0, 0, placeholder_summary, 0.0),
        )
        eid = cur.fetchone()[0]
    result = generate_bundle(eid)
    return {"ok": True, "export_id": eid, "generated_at": str(now),
            "summary": result["summary"], "file_count": result["file_count"],
            "size_bytes": result["size_bytes"], "cost_usd": result["cost_usd"]}


@app.get("/api/respondents/{respondent_id}")
def respondent_detail(respondent_id: int, request: Request) -> dict[str, Any]:
    """Individual respondent drill-down.

    Identity (name/email/mobile) is gated by consent_share_individual.
    M5 JWT will extend this to also allow admin role unconditionally.
    """
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role, team_id, company_id FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me:
        raise HTTPException(401, "not authenticated")
    caller_role = me[0]["role"]
    r = rows(
        """SELECT respondent_id, email, name, first_name, last_name, mobile,
                  job_title, location, timezone,
                  company, industry, role,
                  team_id, company_id, consent_share_individual, created_at
             FROM respondents WHERE respondent_id = %s""",
        (respondent_id,),
    )
    if not r:
        raise HTTPException(404, "respondent not found")
    rec = r[0]
    if caller_role != "admin" and respondent_id != int(caller["sub"]):
        if caller_role == "sales_director" and me[0]["team_id"] == rec.get("team_id"):
            pass
        elif caller_role in ("ceo", "hr", "learning_development") and me[0]["company_id"] and me[0]["company_id"] == rec.get("company_id"):
            pass
        else:
            raise HTTPException(403, "forbidden")
    can_see_identity = bool(rec.get("consent_share_individual"))
    if not can_see_identity:
        for k in ("name", "email", "first_name", "last_name", "mobile"):
            rec[k] = "Anonymised" if k == "name" else "anonymised"

    audits = rows(
        """SELECT a.audit_id, a.status, a.started_at, a.completed_at,
                  s.cognitive_empathy, s.eq, s.pressure_composure, s.storytelling,
                  ar.name AS archetype_name, aa.confidence AS archetype_confidence,
                  rep.report_id, rep.pdf_path
             FROM audits a
        LEFT JOIN audit_scores s ON s.audit_id = a.audit_id
        LEFT JOIN archetype_assignments aa ON aa.audit_id = a.audit_id
        LEFT JOIN archetypes ar ON ar.archetype_id = aa.archetype_id
        LEFT JOIN LATERAL (
            SELECT report_id, pdf_path
              FROM reports r
             WHERE r.audit_id = a.audit_id
             ORDER BY r.version DESC
             LIMIT 1
        ) rep ON TRUE
            WHERE a.respondent_id = %s
            ORDER BY a.started_at DESC""",
        (respondent_id,),
    )

    bands_by_dim: dict[str, dict[str, Any]] = {}
    if audits:
        bcs = rows(
            "SELECT dimension, band, score FROM band_classifications WHERE audit_id = %s",
            (audits[0]["audit_id"],),
        )
        bands_by_dim = {b["dimension"]: b for b in bcs}

    team_name = None
    company_name = None
    if rec.get("team_id"):
        t = rows("SELECT name FROM teams WHERE team_id = %s", (rec["team_id"],))
        if t: team_name = t[0]["name"]
    if rec.get("company_id"):
        c = rows("SELECT name FROM companies WHERE company_id = %s", (rec["company_id"],))
        if c: company_name = c[0]["name"]

    return {
        "respondent": rec,
        "team_name": team_name,
        "company_name": company_name,
        "audits": audits,
        "bands_by_dim": bands_by_dim,
        "identity_visible": can_see_identity,
    }


@app.get("/api/teams/{team_id}/audits")
def team_audits(team_id: int, request: Request) -> dict[str, Any]:
    _require_team_access(request, team_id)
    _team_or_404(team_id)
    data = rows(
        """SELECT a.audit_id, a.status, a.started_at, a.completed_at,
                  CASE WHEN r.consent_share_individual THEN r.email
                       ELSE 'anonymised' END AS email,
                  CASE WHEN r.consent_share_individual THEN r.name
                       ELSE 'Anonymised' END AS respondent_name,
                  r.consent_share_individual,
                  s.cognitive_empathy, s.eq, s.pressure_composure, s.storytelling,
                  ar.name AS archetype_name
             FROM audits a
             JOIN respondents r ON r.respondent_id = a.respondent_id
        LEFT JOIN audit_scores s ON s.audit_id = a.audit_id
        LEFT JOIN archetype_assignments aa ON aa.audit_id = a.audit_id
        LEFT JOIN archetypes ar ON ar.archetype_id = aa.archetype_id
            WHERE r.team_id = %s
            ORDER BY a.started_at DESC""",
        (team_id,),
    )
    return {"audits": data}


# ---------------------------------------------------------------------------
# Bespoke + promo
# ---------------------------------------------------------------------------


@app.get("/api/bespoke")
def bespoke_list() -> dict[str, Any]:
    return {"bespoke": rows(
        """SELECT bespoke_client_id, client_name, unique_url_slug,
                  estimated_value, status, brand_assets_json, created_at
             FROM bespoke_clients ORDER BY created_at DESC"""
    )}


class BespokeCreateIn(BaseModel):
    client_name:     str
    brief:           str           # free-text brief Claude uses to generate questions
    industry_code:   str | None = None
    estimated_value: float | None = None
    primary_colour:  str | None = None  # hex, e.g. "#007AFF"


def _slugify(name: str) -> str:
    import re
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:60]


_BESPOKE_QUESTION_SCHEMA = {
    "type": "object",
    "required": ["questions"],
    "properties": {
        "questions": {
            "type": "array",
            "minItems": 10,
            "maxItems": 20,
            "items": {
                "type": "object",
                "required": ["sequence", "dimension", "prompt", "options"],
                "properties": {
                    "sequence":         {"type": "integer"},
                    "dimension":        {"type": "string", "enum": ["cognitive_empathy", "eq", "pressure_composure", "storytelling"]},
                    "archetype_signal": {"type": "string"},
                    "weight":           {"type": "number"},
                    "prompt":           {"type": "string"},
                    "options": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {
                            "type": "object",
                            "required": ["label", "value"],
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "number", "minimum": 0, "maximum": 1},
                            },
                        },
                    },
                },
            },
        }
    },
}


@app.post("/api/bespoke")
def bespoke_create(body: BespokeCreateIn, request: Request) -> dict[str, Any]:
    """S051: Ingest a client brief, use Claude to generate bespoke questions,
    create audit_version + bespoke_client, return the unique_url_slug."""
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    from app.claude_client import complete_structured, ClaudeCallError

    # Resolve industry
    industry_id: int | None = None
    industry_name = "sales"
    if body.industry_code:
        ind = rows("SELECT industry_id, name FROM industries WHERE code = %s", (body.industry_code,))
        if ind:
            industry_id = ind[0]["industry_id"]
            industry_name = ind[0]["name"]

    # Claude generates the questions
    prompt = (
        f"You are building a custom sales DNA audit for '{body.client_name}', "
        f"a company in the {industry_name} industry.\n\n"
        f"Client brief:\n{body.brief}\n\n"
        f"Generate 12-16 scenario-based multiple-choice questions that assess four dimensions: "
        f"cognitive_empathy, eq (emotional intelligence), pressure_composure, and storytelling. "
        f"Each question must have exactly 4 options with values 0.0 (worst), 0.33, 0.67, 1.0 (best). "
        f"Ground every question in the client's industry and context from the brief. "
        f"Sequence questions 1 through N. Weight each 1.0 unless there is a strong reason to weight differently. "
        f"Australian English throughout. No em dashes."
    )
    try:
        result = complete_structured(prompt, _BESPOKE_QUESTION_SCHEMA)
    except ClaudeCallError as exc:
        event("bespoke.claude_error", severity="error", payload={"error": str(exc), "client": body.client_name})
        raise HTTPException(502, f"Claude question generation failed: {exc}")

    questions = result.get("questions", [])
    if not questions:
        raise HTTPException(502, "Claude returned no questions")

    # Generate unique slug (append suffix if taken)
    base_slug = _slugify(body.client_name)
    slug = base_slug
    suffix = 1
    while rows("SELECT 1 FROM bespoke_clients WHERE unique_url_slug = %s", (slug,)):
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    brand_assets = {"primary_colour": body.primary_colour} if body.primary_colour else {}

    with conn() as c:
        cur = c.cursor()

        # Create audit_version
        cur.execute(
            """INSERT INTO audit_versions (code, name, industry_id, band_thresholds_json, is_active)
               VALUES (%s, %s, %s, %s, true)
               RETURNING audit_version_id""",
            (
                slug,
                f"{body.client_name} DNA Audit",
                industry_id,
                json.dumps({"elite": [0.85, 1.0], "performing": [0.65, 0.85],
                             "practising": [0.40, 0.65], "developing": [0.0, 0.40]}),
            ),
        )
        version_id = cur.fetchone()[0]

        # Create bespoke_client linked to the version
        cur.execute(
            """INSERT INTO bespoke_clients
                  (client_name, custom_audit_version_id, unique_url_slug, estimated_value, status, brand_assets_json)
               VALUES (%s, %s, %s, %s, 'draft', %s)
               RETURNING bespoke_client_id""",
            (body.client_name, version_id, slug, body.estimated_value, json.dumps(brand_assets)),
        )
        bespoke_id = cur.fetchone()[0]

        # Update audit_version to link back to bespoke_client
        cur.execute(
            "UPDATE audit_versions SET bespoke_client_id = %s WHERE audit_version_id = %s",
            (bespoke_id, version_id),
        )

        # Insert questions
        for q in questions:
            cur.execute(
                """INSERT INTO questions
                       (audit_version_id, sequence, dimension, archetype_signal,
                        weight, prompt, response_type, response_meta)
                   VALUES (%s,%s,%s,%s,%s,%s,'choice',%s)""",
                (
                    version_id,
                    q["sequence"],
                    q["dimension"],
                    q.get("archetype_signal"),
                    q.get("weight", 1.0),
                    q["prompt"],
                    json.dumps({"options": q["options"]}),
                ),
            )
        c.commit()

    event("bespoke.created", payload={
        "bespoke_client_id": bespoke_id,
        "client_name": body.client_name,
        "audit_version_id": version_id,
        "slug": slug,
        "n_questions": len(questions),
    })
    return {
        "ok": True,
        "bespoke_client_id": bespoke_id,
        "audit_version_id": version_id,
        "unique_url_slug": slug,
        "audit_url": f"/audit/{slug}",
        "n_questions": len(questions),
    }


@app.get("/api/promo-codes")
def promo_codes_list() -> dict[str, Any]:
    return {"promo_codes": rows(
        """SELECT code, code_type, discount_pct, uses_remaining,
                  valid_until, source_campaign, created_at
             FROM promo_codes ORDER BY created_at DESC"""
    )}


# ---------------------------------------------------------------------------
# Promo validation (S073/S074)
# ---------------------------------------------------------------------------

def _validate_promo(code: str) -> dict[str, Any]:
    """Validate a promo code. Returns dict with valid, discount_pct, code_type, error."""
    pc = rows(
        """SELECT code, code_type, discount_pct, uses_remaining, valid_until
             FROM promo_codes
            WHERE upper(code) = upper(%s)""",
        (code,),
    )
    if not pc:
        return {"valid": False, "error": "Promo code not found."}
    p = pc[0]
    if p["uses_remaining"] is not None and p["uses_remaining"] <= 0:
        return {"valid": False, "error": "This promo code has no uses remaining."}
    if p["valid_until"] and p["valid_until"] < datetime.now(timezone.utc):
        return {"valid": False, "error": "This promo code has expired."}
    return {
        "valid": True,
        "code": p["code"],
        "code_type": p["code_type"],
        "discount_pct": float(p["discount_pct"] or 0),
        "is_free": (p["code_type"] == "free" or float(p["discount_pct"] or 0) >= 100),
    }


def _decrement_promo(code: str) -> None:
    with conn() as c, c.cursor() as cur:
        cur.execute(
            """UPDATE promo_codes
                  SET uses_remaining = uses_remaining - 1
                WHERE upper(code) = upper(%s) AND uses_remaining > 0""",
            (code,),
        )


@app.get("/api/promo/validate")
def promo_validate(code: str) -> dict[str, Any]:
    """S073: Validate a promo code without consuming a use."""
    return _validate_promo(code)


# ---------------------------------------------------------------------------
# Stripe checkout (S070/S071)
# ---------------------------------------------------------------------------

_AUDIT_PRICE_CENTS = int(float(os.environ.get("AUDIT_PRICE_AUD", "497")) * 100)
_STRIPE_SUCCESS_URL = os.environ.get(
    "STRIPE_SUCCESS_URL", "http://localhost:55173/audit/start?session_id={CHECKOUT_SESSION_ID}"
)
_STRIPE_CANCEL_URL = os.environ.get("STRIPE_CANCEL_URL", "http://localhost:55173/audit")


def _stripe_client():
    import stripe as _stripe
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        raise HTTPException(503, "Stripe is not configured. Add STRIPE_SECRET_KEY to .env.")
    _stripe.api_key = key
    return _stripe


class CheckoutIn(BaseModel):
    email:        str
    name:         str | None = None
    first_name:   str | None = None
    last_name:    str | None = None
    job_title:    str | None = None
    promo_code:   str | None = None
    version_code: str | None = None
    industry_code: str | None = None


@app.post("/api/checkout/session")
def checkout_session(body: CheckoutIn) -> dict[str, Any]:
    """S070: Create a Stripe Checkout session (or bypass for 100% promo codes).

    Returns one of:
      { "free": true, "audit_id": N }          -- 100% promo, audit created immediately
      { "checkout_url": "https://stripe..." }   -- redirect the browser here
    """
    promo_result: dict[str, Any] | None = None
    if body.promo_code:
        promo_result = _validate_promo(body.promo_code)
        if not promo_result["valid"]:
            raise HTTPException(400, promo_result["error"])

    # S074: 100% discount → skip Stripe, create audit directly
    if promo_result and promo_result.get("is_free"):
        _decrement_promo(body.promo_code)  # type: ignore[arg-type]
        version_id = _resolve_audit_version(body.version_code, body.industry_code)
        first_default, last_default = _split_name(body.name)
        first = body.first_name or first_default
        last  = body.last_name  or last_default
        existing = rows("SELECT respondent_id FROM respondents WHERE email = %s", (body.email,))
        if existing:
            rid = existing[0]["respondent_id"]
        else:
            with conn() as c:
                cur = c.cursor()
                cur.execute(
                    """INSERT INTO respondents (email, name, first_name, last_name, job_title, role, source)
                       VALUES (%s,%s,%s,%s,%s,'sales_person','stripe_checkout')
                       RETURNING respondent_id""",
                    (body.email, body.name, first, last, body.job_title),
                )
                rid = cur.fetchone()[0]
        with conn() as c:
            cur = c.cursor()
            cur.execute(
                "INSERT INTO audits (respondent_id, audit_version_id, status) VALUES (%s,%s,'in_progress') RETURNING audit_id",
                (rid, version_id),
            )
            audit_id = cur.fetchone()[0]
        event("checkout.free", payload={"email": body.email, "promo": body.promo_code, "audit_id": audit_id})
        return {"free": True, "audit_id": audit_id}

    # Paid path -- create Stripe session
    stripe = _stripe_client()
    discount_pct = promo_result["discount_pct"] if promo_result else 0.0
    amount_cents = max(50, int(_AUDIT_PRICE_CENTS * (1 - discount_pct / 100)))

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "aud",
                "unit_amount": amount_cents,
                "product_data": {
                    "name": "Decipher DNA Audit",
                    "description": "Individual sales intelligence report. Delivered within 90 seconds of completion.",
                },
            },
            "quantity": 1,
        }],
        mode="payment",
        customer_email=body.email,
        success_url=_STRIPE_SUCCESS_URL,
        cancel_url=_STRIPE_CANCEL_URL,
        metadata={
            "email":         body.email,
            "name":          body.name or "",
            "first_name":    body.first_name or "",
            "last_name":     body.last_name or "",
            "job_title":     body.job_title or "",
            "promo_code":    body.promo_code or "",
            "version_code":  body.version_code or "",
            "industry_code": body.industry_code or "",
        },
    )
    if body.promo_code:
        _decrement_promo(body.promo_code)
    event("checkout.created", payload={"email": body.email, "amount_cents": amount_cents, "session_id": session.id})
    return {"checkout_url": session.url}


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request) -> dict[str, Any]:
    """S071: Handle Stripe events. Creates respondent + audit on checkout.session.completed."""
    stripe = _stripe_client()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    try:
        webhook_event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
    except Exception as exc:
        event("stripe.webhook.error", severity="error", payload={"error": str(exc)})
        raise HTTPException(400, f"Webhook signature verification failed: {exc}")

    if webhook_event["type"] == "checkout.session.completed":
        session = webhook_event["data"]["object"]
        meta = session.get("metadata", {})
        email = meta.get("email") or session.get("customer_email") or ""
        if not email:
            return {"ok": True}

        name       = meta.get("name") or None
        first_name = meta.get("first_name") or None
        last_name  = meta.get("last_name") or None
        job_title  = meta.get("job_title") or None
        version_code  = meta.get("version_code") or None
        industry_code = meta.get("industry_code") or None

        version_id = _resolve_audit_version(version_code, industry_code)
        first_default, last_default = _split_name(name)
        first = first_name or first_default
        last  = last_name  or last_default

        existing = rows("SELECT respondent_id FROM respondents WHERE email = %s", (email,))
        if existing:
            rid = existing[0]["respondent_id"]
        else:
            with conn() as c:
                cur = c.cursor()
                cur.execute(
                    """INSERT INTO respondents (email, name, first_name, last_name, job_title, role, source)
                       VALUES (%s,%s,%s,%s,%s,'sales_person','stripe_checkout')
                       RETURNING respondent_id""",
                    (email, name, first, last, job_title),
                )
                rid = cur.fetchone()[0]

        with conn() as c:
            cur = c.cursor()
            cur.execute(
                "INSERT INTO audits (respondent_id, audit_version_id, status) VALUES (%s,%s,'in_progress') RETURNING audit_id",
                (rid, version_id),
            )
            audit_id = cur.fetchone()[0]

        event("stripe.checkout.completed", payload={
            "email": email,
            "audit_id": audit_id,
            "session_id": session["id"],
            "amount_total": session.get("amount_total"),
        })

    return {"ok": True}


# ---------------------------------------------------------------------------
# Squarespace export
# ---------------------------------------------------------------------------

_SQUARESPACE_FILE_TREE = [
    "pages/home.md", "pages/dna_audit.md", "pages/training.md",
    "pages/consulting.md", "pages/industries/media.md",
    "pages/industries/pharma.md", "pages/industries/automotive.md",
    "pages/industries/tech.md", "pages/bespoke.md", "pages/about.md",
    "pages/contact.md",
    "seo/meta.json",
    "design/tokens.json", "design/hig_notes.md", "design/images_brief.md",
    "audit_app/intro.md", "audit_app/post_payment.md",
    "audit_app/dimension_intros.md", "audit_app/progress.md",
    "audit_app/completion.md",
    "audit_app/emails/receipt.md", "audit_app/emails/report_delivery.md",
    "audit_app/emails/nudge_day7.md", "audit_app/emails/reaudit_day90.md",
    "pdf_report/cover.md", "pdf_report/dimension_explainers.md",
    "pdf_report/archetype_profiles.md", "pdf_report/band_descriptors.md",
    "pdf_report/closing.md",
    "voice/brand_voice.md",
    "README.md",
]


@app.get("/api/squarespace/exports")
def squarespace_exports() -> dict[str, Any]:
    data = rows(
        """SELECT export_id, generated_at, bundle_path, file_count,
                  size_bytes, summary, cost_usd
             FROM squarespace_exports ORDER BY generated_at DESC"""
    )
    return {"exports": data, "file_tree": _SQUARESPACE_FILE_TREE}


@app.get("/api/squarespace/exports/{export_id}")
def squarespace_export_detail(export_id: int) -> dict[str, Any]:
    r = rows("SELECT * FROM squarespace_exports WHERE export_id = %s", (export_id,))
    if not r:
        raise HTTPException(404, "export not found")
    return {"export": r[0], "file_tree": _SQUARESPACE_FILE_TREE}


# ---------------------------------------------------------------------------
# User + roles management (Settings page)
# ---------------------------------------------------------------------------

VALID_ROLES = {"admin", "ceo", "sales_director", "hr",
               "learning_development", "sales_person"}

# Roles permitted to send audit invites + manage the funnel.
# CEO is read-only; Sales Person is self-serve only (can take audit, not send).
INVITE_ROLES = {"admin", "sales_director", "hr", "learning_development"}

# Capability levels: 'none' | 'read' | 'write' | 'both'
WRITE_LEVELS = {"write", "both"}


def _role_can(role: str, capability: str) -> bool:
    """Returns True if role has write-or-both level for the capability."""
    if role == "admin":
        return True
    r = rows(
        "SELECT level FROM role_permissions WHERE role = %s AND capability = %s",
        (role, capability),
    )
    if not r:
        return False
    return r[0]["level"] in WRITE_LEVELS


def _require_capability(role: str, capability: str) -> None:
    if not _role_can(role, capability):
        raise HTTPException(403, f"role '{role}' lacks write access to '{capability}'")


# ---------------------------------------------------------------------------
# Role permissions (admin-only management)
# ---------------------------------------------------------------------------


CAPABILITY_LABELS = {
    "page.mission":          ("Mission Control",     "page"),
    "page.funnel":           ("Funnel",              "page"),
    "page.audits":           ("Audits",              "page"),
    "page.cohort":           ("Cohort Insights",     "page"),
    "page.events":           ("Events",              "page"),
    "page.companies":        ("Companies",           "page"),
    "page.teams":            ("Teams",               "page"),
    "page.people":           ("People",              "page"),
    "page.industries":       ("Industries",          "page"),
    "page.bespoke":          ("Bespoke",             "page"),
    "page.promo":            ("Promo Codes",         "page"),
    "page.squarespace":      ("Squarespace Export",  "page"),
    "page.settings":         ("Settings",            "page"),
    "action.take_audit":          ("Take audit",                "action"),
    "action.send_invite":         ("Send audit invite",         "action"),
    "action.add_company":         ("Add company",               "action"),
    "action.add_team":            ("Add team",                  "action"),
    "action.add_person":          ("Add person",                "action"),
    "action.delete_person":       ("Delete person",             "action"),
    "action.manage_permissions":  ("Manage role permissions",   "action"),
}


@app.get("/api/permissions")
def permissions_list(request: Request) -> dict[str, Any]:
    _require_admin(request)
    data = rows("SELECT role, capability, level, relevant FROM role_permissions ORDER BY role, capability")
    # Materialise capabilities list with labels + group
    caps = [
        {"key": k, "label": v[0], "group": v[1]}
        for k, v in CAPABILITY_LABELS.items()
    ]
    return {
        "roles": sorted(VALID_ROLES),
        "capabilities": caps,
        "matrix": data,
        "levels": ["none", "read", "write", "both"],
    }


class PermissionPatch(BaseModel):
    level:        str        # 'none' | 'read' | 'write' | 'both'


@app.patch("/api/permissions/{role}/{capability}")
def permissions_patch(role: str, capability: str, body: PermissionPatch, request: Request) -> dict[str, Any]:
    if body.level not in ("none", "read", "write", "both"):
        raise HTTPException(400, "level must be one of: none / read / write / both")
    if role not in VALID_ROLES:
        raise HTTPException(400, f"unknown role: {role}")
    if capability not in CAPABILITY_LABELS:
        raise HTTPException(400, f"unknown capability: {capability}")
        caller = _caller_from_request(request)
        if not caller:
                raise HTTPException(401, "not authenticated")
        me = rows("SELECT role, email FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me or me[0]["role"] != "admin":
        raise HTTPException(403, "only admin can manage role permissions")
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO role_permissions (role, capability, level, updated_by, updated_at)
               VALUES (%s,%s,%s,%s, now())
               ON CONFLICT (role, capability) DO UPDATE
                  SET level = EXCLUDED.level,
                      updated_by = EXCLUDED.updated_by,
                      updated_at = now()""",
                        (role, capability, body.level, me[0]["email"]),
        )
        cur.execute(
            """INSERT INTO events_log (actor, action, severity, subject_id, payload)
               VALUES ('admin', 'permission.changed', 'info', %s, %s::jsonb)""",
            (f"{role}/{capability}",
                             json.dumps({"level": body.level, "actor": me[0]["email"]})),
        )
    return {"ok": True, "role": role, "capability": capability, "level": body.level}


# ---------------------------------------------------------------------------
# Auth (prototype). Real magic-link / JWT lands in M5.
# ---------------------------------------------------------------------------

import bcrypt as _bcrypt


def _verify_password(plain: str, stored_hash: str, stored_salt: str | None) -> bool:
    """Verify a password against its stored hash.

    Bcrypt hashes start with $2b$ and are self-contained (salt embedded).
    Legacy sha256 hashes (salt+plain → hexdigest) are accepted for existing
    accounts and transparently upgraded to bcrypt on next successful login.
    """
    if stored_hash.startswith("$2b$"):
        return _bcrypt.checkpw(plain.encode(), stored_hash.encode())
    import hashlib
    return hashlib.sha256(((stored_salt or "") + plain).encode()).hexdigest() == stored_hash


def _hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt(rounds=12)).decode()


# ---------------------------------------------------------------------------
# JWT session tokens (M5)
# ---------------------------------------------------------------------------

_JWT_SECRET = os.getenv("DECIPHER_JWT_SECRET", "decipher-dev-secret-change-in-prod")
_JWT_ALGO   = "HS256"
_JWT_TTL_DAYS = 7


def _issue_jwt(respondent_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    return _jwt.encode(
        {"sub": str(respondent_id), "role": role,
         "iat": now, "exp": now + timedelta(days=_JWT_TTL_DAYS)},
        _JWT_SECRET, algorithm=_JWT_ALGO,
    )


def _decode_jwt(token: str) -> dict:
    try:
        return _jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO])
    except _jwt.ExpiredSignatureError:
        raise HTTPException(401, "session expired")
    except _jwt.InvalidTokenError:
        raise HTTPException(401, "invalid token")


def _caller_from_request(request: Request) -> dict | None:
    """Return decoded JWT payload from Authorization: Bearer header, or None."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return _decode_jwt(auth[7:].strip())


class LoginIn(BaseModel):
    email:    str
    password: str


@app.post("/api/auth/login")
def auth_login(body: LoginIn) -> dict[str, Any]:
    r = rows(
        """SELECT respondent_id, email, name, first_name, last_name, role,
                  password_hash, password_salt
             FROM respondents WHERE email = %s""",
        (body.email.lower().strip(),),
    )
    if not r or not r[0].get("password_hash"):
        raise HTTPException(401, "invalid email or password")
    rec = r[0]
    if not _verify_password(body.password, rec["password_hash"], rec.get("password_salt")):
        raise HTTPException(401, "invalid email or password")
    # Upgrade legacy sha256 hash to bcrypt on first successful login.
    if not rec["password_hash"].startswith("$2b$"):
        new_hash = _hash_password(body.password)
        with conn() as c:
            c.cursor().execute(
                "UPDATE respondents SET password_hash = %s, password_salt = NULL WHERE respondent_id = %s",
                (new_hash, rec["respondent_id"]),
            )
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO events_log (actor, action, severity, subject_id, payload)
               VALUES ('auth', 'user.login', 'info', %s, %s::jsonb)""",
            (str(rec["respondent_id"]),
             json.dumps({"email": rec["email"], "role": rec["role"]})),
        )
    me_out = {
        "respondent_id": rec["respondent_id"],
        "email":         rec["email"],
        "name":          rec["name"],
        "first_name":    rec["first_name"],
        "last_name":     rec["last_name"],
        "role":          rec["role"],
    }
    return {"ok": True, "token": _issue_jwt(rec["respondent_id"], rec["role"]), "me": me_out}


@app.get("/api/auth/demo-credentials")
def auth_demo_credentials() -> dict[str, Any]:
    """Surface the seeded demo credentials on the login screen (dev only)."""
    if os.getenv("DECIPHER_ENV", "dev") != "dev":
        raise HTTPException(404, "not found")
    return {"credentials": [
        {"role": "Admin (Steve)",
         "email": "steve@decipher.com.au", "password": "Decipher2026!"},
        {"role": "Sales Director (Owen Wright, NSW Sales Team)",
         "email": "owen.wright@demo.decipher.local", "password": "Owen2026!"},
        {"role": "Sales Person (Grant Smith)",
         "email": "grant.smith@demo.decipher.local", "password": "Grant2026!"},
        {"role": "Learning & Development (Priya Ranjan)",
         "email": "priya.exec@demo.decipher.local", "password": "Priya2026!"},
        {"role": "VP Sales (Tara Holm, Northwind Pharma)",
         "email": "tara.exec@demo.decipher.local", "password": "Tara2026!"},
    ]}


# ---------------------------------------------------------------------------
# Magic-link auth (M5)
# ---------------------------------------------------------------------------

def _send_magic_link_email(to_email: str, first_name: str | None, link: str) -> None:
    """Drop a magic-link sign-in email into Mailpit (rule 17)."""
    host = os.environ.get("DECIPHER_MAIL_HOST", "127.0.0.1")
    port = int(os.environ.get("DECIPHER_MAIL_PORT", "1025"))
    msg = EmailMessage()
    msg["From"] = "noreply@decipher.com.au"
    msg["To"]   = to_email
    msg["Subject"] = "Your Decipher sign-in link"
    name = first_name or "there"
    msg.set_content(
        f"Hi {name},\n\nClick the link below to sign in to Decipher.\n\n"
        f"{link}\n\nThis link expires in 15 minutes and can only be used once.\n\n"
        f"If you did not request this, you can ignore this email."
    )
    msg.add_alternative(
        f"""<html><body style='font-family:-apple-system,sans-serif;color:#1c1c1e'>
<p>Hi {name},</p>
<p>Click below to sign in to <strong>Decipher</strong>.</p>
<p><a href='{link}' style='background:#1A57C7;color:#fff;padding:12px 18px;
text-decoration:none;border-radius:6px;font-weight:600;display:inline-block;'>Sign in to Decipher</a></p>
<p style='color:#636366;font-size:12px;'>This link expires in 15 minutes and can only be used once.
If you did not request this, you can ignore this email.</p>
</body></html>""",
        subtype="html",
    )
    with smtplib.SMTP(host, port, timeout=5) as s:
        s.send_message(msg)


class MagicLinkRequestIn(BaseModel):
    email: str


@app.post("/api/auth/magic-link/request")
def magic_link_request(body: MagicLinkRequestIn) -> dict[str, Any]:
    """Generate a one-time sign-in token and deliver it via Mailpit.
    Rate-limited to 10 requests per email per hour (spec §architecture).
    """
    email = body.email.lower().strip()
    r = rows(
        "SELECT respondent_id, email, name, first_name FROM respondents WHERE email = %s",
        (email,),
    )
    if not r:
        # Don't reveal whether email exists.
        return {"ok": True}
    rec = r[0]

    # Rate limit: max 10 magic-link requests per email per hour
    recent = scalar(
        """SELECT count(*) FROM magic_link_tokens mlt
             JOIN respondents res ON res.respondent_id = mlt.respondent_id
            WHERE res.email = %s
              AND mlt.expires_at > now() - interval '1 hour'""",
        (email,),
    ) or 0
    if int(recent) >= 10:
        raise HTTPException(429, "Too many magic-link requests. Try again in an hour.")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    with conn() as c, c.cursor() as cur:
        cur.execute(
            """INSERT INTO magic_link_tokens (token_hash, respondent_id, expires_at)
               VALUES (%s, %s, now() + interval '15 minutes')""",
            (token_hash, rec["respondent_id"]),
        )

    web_port = os.environ.get("DECIPHER_WEB_PORT", "5173")
    base_url = os.environ.get("DECIPHER_PUBLIC_URL", f"http://127.0.0.1:{web_port}")
    link = f"{base_url}/auth/magic-link?token={raw_token}"
    try:
        _send_magic_link_email(
            rec["email"],
            rec.get("first_name") or (rec.get("name") or "").split()[0] or None,
            link,
        )
    except Exception as exc:
        event("auth.magic_link_mail_failed", severity="error",
              subject_id=str(rec["respondent_id"]), payload={"error": str(exc)})
    event("auth.magic_link_requested", actor="api",
          subject_id=str(rec["respondent_id"]), payload={"email": rec["email"]})
    return {"ok": True}


@app.get("/api/auth/magic-link/consume")
def magic_link_consume(token: str) -> dict[str, Any]:
    """Verify a one-time token, mark it consumed, return a JWT session token."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    r = rows(
        """SELECT mlt.token_hash, mlt.respondent_id, mlt.expires_at, mlt.consumed_at,
                  res.email, res.name, res.first_name, res.last_name, res.role
             FROM magic_link_tokens mlt
             JOIN respondents res ON res.respondent_id = mlt.respondent_id
            WHERE mlt.token_hash = %s""",
        (token_hash,),
    )
    if not r:
        raise HTTPException(401, "invalid or expired sign-in link")
    rec = r[0]
    if rec["consumed_at"] is not None:
        raise HTTPException(401, "sign-in link already used")
    exp = rec["expires_at"]
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > exp:
        raise HTTPException(401, "sign-in link expired")

    with conn() as c, c.cursor() as cur:
        cur.execute(
            "UPDATE magic_link_tokens SET consumed_at = now() WHERE token_hash = %s",
            (token_hash,),
        )

    event("auth.magic_link_consumed", actor="api",
          subject_id=str(rec["respondent_id"]),
          payload={"email": rec["email"], "role": rec["role"]})

    return {
        "ok":    True,
        "token": _issue_jwt(rec["respondent_id"], rec["role"]),
        "me": {
            "respondent_id": rec["respondent_id"],
            "email":         rec["email"],
            "name":          rec["name"],
            "first_name":    rec["first_name"],
            "last_name":     rec["last_name"],
            "role":          rec["role"],
        },
    }


@app.get("/api/users")
def users_list(request: Request, role: str | None = None, team_id: int | None = None,
               company_id: int | None = None, q: str | None = None) -> dict[str, Any]:
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role, team_id, company_id FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me:
        raise HTTPException(401, "not authenticated")
    caller_role = me[0]["role"]
    if caller_role == "admin":
        pass
    elif caller_role == "sales_director":
        team_id = me[0]["team_id"]
        company_id = None
    elif caller_role in ("ceo", "hr", "learning_development"):
        company_id = me[0]["company_id"]
        team_id = None
    else:
        raise HTTPException(403, "forbidden")
    where = ["1=1"]
    params: list[Any] = []
    if role:
        where.append("r.role = %s"); params.append(role)
    if team_id is not None:
        where.append("r.team_id = %s"); params.append(team_id)
    if company_id is not None:
        where.append("r.company_id = %s"); params.append(company_id)
    if q:
        where.append("(r.email ILIKE %s OR r.name ILIKE %s)")
        params.extend([f"%{q}%", f"%{q}%"])
    sql = f"""SELECT r.respondent_id, r.email, r.name, r.role, r.team_id, r.company_id,
                     r.consent_share_individual, r.created_at,
                     t.name AS team_name, c.name AS company_name
                FROM respondents r
           LEFT JOIN teams t ON t.team_id = r.team_id
           LEFT JOIN companies c ON c.company_id = r.company_id
               WHERE {' AND '.join(where)}
            ORDER BY r.role, r.created_at DESC
               LIMIT 500"""
    data = rows(sql, tuple(params))
    counts = rows(
                f"SELECT role, count(*)::int AS n FROM respondents r WHERE {' AND '.join(where)} GROUP BY role ORDER BY role",
        tuple(params),
    )
    return {"users": data, "counts_by_role": counts, "valid_roles": sorted(VALID_ROLES)}


class UserPatch(BaseModel):
    role:                     str | None = None
    team_id:                  int | None = None
    company_id:               int | None = None
    name:                     str | None = None
    consent_share_individual: bool | None = None


@app.patch("/api/users/{respondent_id}")
def users_patch(respondent_id: int, body: UserPatch, request: Request) -> dict[str, Any]:
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role, team_id, company_id FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me:
        raise HTTPException(401, "not authenticated")
    caller_role = me[0]["role"]
    target = rows("SELECT team_id, company_id FROM respondents WHERE respondent_id = %s", (respondent_id,))
    if not target:
        raise HTTPException(404, "respondent not found")
    if caller_role == "admin":
        pass
    elif caller_role == "sales_director" and me[0]["team_id"] == target[0]["team_id"]:
        pass
    elif caller_role in ("ceo", "hr", "learning_development") and me[0]["company_id"] and me[0]["company_id"] == target[0]["company_id"]:
        pass
    else:
        raise HTTPException(403, "forbidden")
    if body.role is not None and caller_role != "admin":
        raise HTTPException(403, "only admin can change role")
    fields = []
    params: list[Any] = []
    if body.role is not None:
        if body.role not in VALID_ROLES:
            raise HTTPException(400, f"invalid role: {body.role}")
        fields.append("role = %s"); params.append(body.role)
    if body.team_id is not None:
        fields.append("team_id = %s"); params.append(body.team_id)
    if body.company_id is not None:
        fields.append("company_id = %s"); params.append(body.company_id)
    if body.name is not None:
        fields.append("name = %s"); params.append(body.name)
    if body.consent_share_individual is not None:
        fields.append("consent_share_individual = %s")
        params.append(body.consent_share_individual)
    if not fields:
        raise HTTPException(400, "no fields to update")
    params.append(respondent_id)
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            f"UPDATE respondents SET {', '.join(fields)} WHERE respondent_id = %s",
            tuple(params),
        )
        cur.execute(
            """INSERT INTO events_log (actor, action, severity, subject_id, payload)
               VALUES (%s, 'user.updated', 'info', %s, %s::jsonb)""",
            (caller_role, str(respondent_id), json.dumps(body.model_dump(exclude_none=True))),
        )
    return {"ok": True}


class UserCreate(BaseModel):
    email:        str
    name:         str | None = None
    role:         str
    team_id:      int | None = None
    company_id:   int | None = None
    actor_email:  str | None = None
    actor_role:   str | None = None


@app.post("/api/users")
def users_create(body: UserCreate, request: Request) -> dict[str, Any]:
    if body.role not in VALID_ROLES:
        raise HTTPException(400, f"invalid role: {body.role}")
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role, team_id, company_id FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me:
        raise HTTPException(401, "not authenticated")
    caller_role = me[0]["role"]
    _require_capability(caller_role, "action.add_person")
    if body.role == "admin" and caller_role != "admin":
        raise HTTPException(403, "only admin can create an admin account")
    if caller_role != "admin":
        body.company_id = me[0]["company_id"]
        if caller_role == "sales_director":
            body.team_id = me[0]["team_id"]
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO respondents (email, name, role, team_id, company_id, source)
               VALUES (%s,%s,%s,%s,%s,'admin_settings')
               ON CONFLICT (email) DO UPDATE SET
                  role = EXCLUDED.role,
                  team_id = COALESCE(EXCLUDED.team_id, respondents.team_id),
                  company_id = COALESCE(EXCLUDED.company_id, respondents.company_id),
                  name = COALESCE(EXCLUDED.name, respondents.name)
               RETURNING respondent_id""",
            (body.email, body.name, body.role, body.team_id, body.company_id),
        )
        rid = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO events_log (actor, action, severity, subject_id, payload)
               VALUES (%s, 'user.created', 'info', %s, %s::jsonb)""",
            (caller_role, str(rid), json.dumps(body.model_dump())),
        )
    return {"ok": True, "respondent_id": rid}


# ---------------------------------------------------------------------------
# Company + team mutations (Add Company / Add Team)
# ---------------------------------------------------------------------------


class CompanyCreate(BaseModel):
    name:           str
    industry:       str | None = None
    contact_name:   str | None = None
    contact_email:  str | None = None
    contact_mobile: str | None = None
    website:        str | None = None
    country:        str | None = "Australia"
    abn:            str | None = None


class PromoCreate(BaseModel):
    code:            str
    code_type:       str  # "free" | "discount"
    discount_pct:    float | None = None
    uses_remaining:  int | None = None
    valid_until:     str | None = None  # ISO date
    source_campaign: str | None = None


@app.post("/api/promo-codes")
def promo_create(body: PromoCreate, request: Request) -> dict[str, Any]:
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role, email FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me or me[0]["role"] != "admin":
        raise HTTPException(403, "admin only")
    if body.code_type not in ("free", "discount"):
        raise HTTPException(400, "code_type must be 'free' or 'discount'")
    pct = 100.0 if body.code_type == "free" else (body.discount_pct or 0)
    if body.code_type == "discount" and not (0 < pct <= 100):
        raise HTTPException(400, "discount_pct must be between 0 and 100")
    valid_until_ts = body.valid_until if body.valid_until else None
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO promo_codes
                   (code, code_type, discount_pct, uses_remaining,
                    valid_until, source_campaign)
               VALUES (%s, %s, %s, %s, %s::timestamptz, %s)
               ON CONFLICT (code) DO UPDATE SET
                  code_type = EXCLUDED.code_type,
                  discount_pct = EXCLUDED.discount_pct,
                  uses_remaining = EXCLUDED.uses_remaining,
                  valid_until = EXCLUDED.valid_until,
                  source_campaign = EXCLUDED.source_campaign
               RETURNING code, code_type, discount_pct, uses_remaining,
                         valid_until, source_campaign, created_at""",
            (body.code.upper(), body.code_type, pct, body.uses_remaining,
             valid_until_ts, body.source_campaign),
        )
        row = cur.fetchone()
        cur.execute(
            """INSERT INTO events_log (actor, action, severity, subject_id, payload)
               VALUES (%s, 'promo.created', 'info', %s, %s::jsonb)""",
            (me[0]["email"], body.code.upper(), json.dumps(body.model_dump())),
        )
    return {"ok": True, "promo": {
        "code": row[0], "code_type": row[1], "discount_pct": float(row[2]) if row[2] is not None else None,
        "uses_remaining": row[3], "valid_until": str(row[4]) if row[4] else None,
        "source_campaign": row[5], "created_at": str(row[6]),
    }}


@app.post("/api/companies")
def companies_create(body: CompanyCreate, request: Request) -> dict[str, Any]:
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me:
        raise HTTPException(401, "not authenticated")
    _require_capability(me[0]["role"], "action.add_company")
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO companies (name, industry, contact_name, contact_email,
                                      contact_mobile, website, country, abn)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (name) DO UPDATE SET
                  industry = EXCLUDED.industry,
                  contact_name = EXCLUDED.contact_name,
                  contact_email = EXCLUDED.contact_email,
                  contact_mobile = EXCLUDED.contact_mobile,
                  website = EXCLUDED.website,
                  country = EXCLUDED.country,
                  abn = EXCLUDED.abn
               RETURNING company_id""",
            (body.name, body.industry, body.contact_name, body.contact_email,
             body.contact_mobile, body.website, body.country, body.abn),
        )
        cid = cur.fetchone()[0]
    return {"ok": True, "company_id": cid}


class TeamCreate(BaseModel):
    name:           str
    company_id:     int
    role_label:     str | None = "Sales Director"
    region:         str | None = None   # NSW / VIC / QLD / WA / SA / TAS / ACT / NT / OS
    country:        str | None = "Australia"
    contact_name:   str | None = None
    contact_email:  str | None = None
    contact_mobile: str | None = None


@app.post("/api/teams")
def teams_create(body: TeamCreate, request: Request) -> dict[str, Any]:
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me:
        raise HTTPException(401, "not authenticated")
    _require_capability(me[0]["role"], "action.add_team")
    company = rows("SELECT name FROM companies WHERE company_id = %s", (body.company_id,))
    if not company:
        raise HTTPException(404, "company not found")
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO teams (name, company_id, organisation, role_label,
                                  region, country,
                                  contact_name, contact_email, contact_mobile)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING team_id""",
            (body.name, body.company_id, company[0]["name"], body.role_label,
             body.region, body.country,
             body.contact_name, body.contact_email, body.contact_mobile),
        )
        tid = cur.fetchone()[0]
    return {"ok": True, "team_id": tid}


# ---------------------------------------------------------------------------
# Team roster (Owen Wright -> Grant Smith drill-down user story)
# ---------------------------------------------------------------------------


@app.get("/api/teams/{team_id}/roster")
def team_roster(team_id: int, request: Request) -> dict[str, Any]:
    _require_team_access(request, team_id)
    """Roster of consented respondents in a team. Identity gated by consent.

    Non-consented respondents show up as "Anonymised" so the director can
    see they exist + their scores + band, but cannot drill into the
    individual page (the click-through is hidden client-side).
    """
    _team_or_404(team_id)
    data = rows(
        """SELECT r.respondent_id,
                  CASE WHEN r.consent_share_individual THEN r.name
                       ELSE 'Anonymised' END AS name,
                  CASE WHEN r.consent_share_individual THEN r.email
                       ELSE 'anonymised' END AS email,
                  r.consent_share_individual,
                  s.cognitive_empathy, s.eq, s.pressure_composure, s.storytelling,
                  (s.cognitive_empathy+s.eq+s.pressure_composure+s.storytelling) / 4.0 AS overall,
                  ar.name AS archetype_name,
                  a.completed_at AS latest_audit_at
             FROM respondents r
        LEFT JOIN LATERAL (
                  SELECT * FROM audits aa
                   WHERE aa.respondent_id = r.respondent_id
                   ORDER BY aa.started_at DESC LIMIT 1
                  ) a ON TRUE
        LEFT JOIN audit_scores s ON s.audit_id = a.audit_id
        LEFT JOIN archetype_assignments aa ON aa.audit_id = a.audit_id
        LEFT JOIN archetypes ar ON ar.archetype_id = aa.archetype_id
            WHERE r.team_id = %s AND r.role = 'sales_person'
            ORDER BY overall DESC NULLS LAST, name""",
        (team_id,),
    )
    return {"roster": data, "count": len(data)}


# ---------------------------------------------------------------------------
# Audit-take flow (native HIG survey route — replaces Google Form)
# ---------------------------------------------------------------------------


@app.get("/api/audit/versions/{code}/questions")
def audit_version_questions(code: str) -> dict[str, Any]:
    v = rows("SELECT audit_version_id, code, name FROM audit_versions WHERE code = %s", (code,))
    if not v:
        raise HTTPException(404, "audit version not found")
    qs = rows(
        """SELECT question_id, sequence, dimension, archetype_signal,
                  prompt, response_type, response_meta
             FROM questions WHERE audit_version_id = %s
            ORDER BY sequence""",
        (v[0]["audit_version_id"],),
    )
    return {"version": v[0], "questions": qs}


class AuditStartIn(BaseModel):
    email:         str
    name:          str | None = None
    first_name:    str | None = None
    last_name:     str | None = None
    mobile:        str | None = None
    job_title:     str | None = None
    company:       str | None = None
    version_code:  str | None = None   # explicit override; takes priority
    industry_code: str | None = None; team_id: int | None = None   # S050: resolve version by industry; team link tag
    token: str | None = None  # invite_token from the emailed link; required to claim a team_id


def _resolve_audit_version(version_code: str | None, industry_code: str | None) -> int:
    """Return audit_version_id. Industry → version lookup; falls back to media_sales_v1."""
    if version_code:
        v = rows("SELECT audit_version_id FROM audit_versions WHERE code = %s AND is_active", (version_code,))
        if v:
            return v[0]["audit_version_id"]
    if industry_code:
        v = rows(
            """SELECT av.audit_version_id FROM audit_versions av
                 JOIN industries i ON i.industry_id = av.industry_id
                WHERE i.code = %s AND av.is_active AND av.bespoke_client_id IS NULL
                ORDER BY av.created_at DESC LIMIT 1""",
            (industry_code,),
        )
        if v:
            return v[0]["audit_version_id"]
    # Default
    v = rows("SELECT audit_version_id FROM audit_versions WHERE code = 'media_sales_v1'")
    return v[0]["audit_version_id"]


def _split_name(full: str | None) -> tuple[str | None, str | None]:
    if not full:
        return (None, None)
    parts = full.strip().split()
    if not parts:
        return (None, None)
    if len(parts) == 1:
        return (parts[0], None)
    return (parts[0], " ".join(parts[1:]))


@app.post("/api/audit/start")
def audit_start(body: AuditStartIn) -> dict[str, Any]:
    email = body.email
    team_id = body.team_id
    version_code = body.version_code
    invite_row = None
    if body.token:
        inv = rows(
            "SELECT invite_id, email, team_id, audit_version_code, expires_at, accepted_at "
            "FROM audit_invites WHERE token_hash = %s",
            (body.token,),
        )
        if not inv:
            raise HTTPException(404, "This invite link is invalid.")
        invite_row = inv[0]
        if invite_row["accepted_at"] is not None:
            raise HTTPException(409, "This invite link has already been used.")
        if invite_row["expires_at"] and invite_row["expires_at"] < datetime.now(timezone.utc):
            raise HTTPException(410, "This invite link has expired.")
        email = invite_row["email"]
        team_id = invite_row["team_id"]
        version_code = invite_row["audit_version_code"] or version_code
    elif body.team_id is not None:
        raise HTTPException(401, "Starting an audit for a team requires a valid invite link.")
    version_id = _resolve_audit_version(version_code, body.industry_code)
    if not version_id:
        raise HTTPException(404, "audit version not found")

    # Resolve name components: explicit fields override the split fallback.
    first_default, last_default = _split_name(body.name)
    first = body.first_name or first_default
    last  = body.last_name  or last_default

    team_company_id = (rows("SELECT company_id FROM teams WHERE team_id = %s", (team_id,)) or [{"company_id": None}])[0]["company_id"] if team_id is not None else None; existing = rows("SELECT respondent_id, first_name, last_name, job_title, mobile FROM respondents WHERE email = %s", (email,))
    if existing:
        rid = existing[0]["respondent_id"]
        # Backfill standard contact fields (Rule 33) without overwriting non-empty values.
        with conn() as c, c.cursor() as cur:
            cur.execute(
                """UPDATE respondents
                      SET first_name = COALESCE(NULLIF(first_name,''), %s),
                          last_name  = COALESCE(NULLIF(last_name,''),  %s),
                          job_title  = COALESCE(NULLIF(job_title,''),  %s),
                          mobile     = COALESCE(NULLIF(mobile,''),     %s),
                          name       = COALESCE(NULLIF(name,''),       %s)
                    WHERE respondent_id = %s""",
                (first, last, body.job_title, body.mobile, body.name, rid),
            )
    else:
        with conn() as c:
            cur = c.cursor()
            cur.execute(
                """INSERT INTO respondents (email, name, first_name, last_name,
                                            mobile, job_title, company, role, source)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,'sales_person','native_audit')
                   RETURNING respondent_id""",
                (email, body.name, first, last, body.mobile,
                 body.job_title, body.company),
            )
            rid = cur.fetchone()[0]

    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO audits (respondent_id, audit_version_id, status) VALUES (%s,%s,'in_progress') RETURNING audit_id""", (rid, version_id), ); audit_id = cur.fetchone()[0]; cur.execute("UPDATE respondents SET team_id = COALESCE(%s, team_id), company_id = COALESCE(%s, company_id) WHERE respondent_id = %s", (team_id, team_company_id, rid))
        cur.execute(
            """INSERT INTO events_log (actor, action, severity, subject_id, payload)
               VALUES ('audit', 'audit.started', 'info', %s, %s::jsonb)""",
            (str(audit_id), json.dumps({"version_code": version_code, "via": "native"})),
        )
        if invite_row:
            cur.execute(
                "UPDATE audit_invites SET accepted_at = now(), audit_id = %s WHERE invite_id = %s",
                (audit_id, invite_row["invite_id"]),
            )
    return {"audit_id": audit_id, "respondent_id": rid}


class AuditAnswerIn(BaseModel):
    question_id:  int
    value:        int  # selected option index (0-based)
    elapsed_ms:   int | None = None


@app.post("/api/audit/{audit_id}/answer")
def audit_answer(audit_id: int, body: AuditAnswerIn) -> dict[str, Any]:
    a = rows("SELECT audit_id, status FROM audits WHERE audit_id = %s", (audit_id,))
    if not a:
        raise HTTPException(404, "audit not found")
    if a[0]["status"] not in ("in_progress", "completed"):
        raise HTTPException(400, f"audit status is {a[0]['status']}")
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO responses (audit_id, question_id, answer_value, response_ms)
               VALUES (%s,%s,%s,%s)""",
            (audit_id, body.question_id, body.value, body.elapsed_ms or 0),
        )
    return {"ok": True}


def _score_and_report(audit_id: int) -> None:
    """Background task: score, generate PDF, enqueue email job.

    Runs in a thread after the /complete response is sent. Errors are logged
    to events_log rather than raised (no HTTP context available here).
    """
    try:
        from app.dna_scoring import score_audit
        from app.dna_report  import generate_report
        score_audit(audit_id)
        report = generate_report(audit_id)
        _enqueue_email_job(audit_id, report["report_id"], report["pdf_path"])
        from app.email_dispatcher import send_report_email
        send_report_email(audit_id, report["report_id"], report["pdf_path"])
    except Exception as exc:
        event("audit.score_error", severity="error", subject_id=str(audit_id),
              payload={"error": str(exc)})


@app.post("/api/audit/{audit_id}/complete")
def audit_complete(audit_id: int, background_tasks: BackgroundTasks) -> dict[str, Any]:
    a = rows("SELECT audit_id, audit_version_id, status FROM audits WHERE audit_id = %s", (audit_id,))
    if not a:
        raise HTTPException(404, "audit not found")
    if a[0]["status"] in ("scored", "reported"):
        return {"ok": True, "audit_id": audit_id, "already_complete": True}

    # Completeness gate: every question on this version must have a response.
    coverage = rows(
        """SELECT q.question_id
             FROM questions q
        LEFT JOIN responses r ON r.question_id = q.question_id AND r.audit_id = %s
            WHERE q.audit_version_id = %s
              AND r.response_id IS NULL""",
        (audit_id, a[0]["audit_version_id"]),
    )
    if coverage:
        missing = [int(c["question_id"]) for c in coverage]
        raise HTTPException(
            status_code=400,
            detail={"code": "incomplete_audit",
                    "missing_count": len(missing),
                    "missing_question_ids": missing[:10],
                    "message": f"{len(missing)} question(s) still unanswered; cannot complete."},
        )

    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """UPDATE audits SET status='completed', completed_at = now()
                WHERE audit_id = %s""",
            (audit_id,),
        )
        cur.execute(
            """INSERT INTO events_log (actor, action, severity, subject_id, payload)
               VALUES ('audit', 'audit.completed', 'info', %s, '{"via":"native"}'::jsonb)""",
            (str(audit_id),),
        )

    # Enqueue scoring + report generation as a background task.
    # The client receives the response immediately; status transitions to
    # 'scored' -> 'reported' in the background thread.
    audit_version_id = a[0]["audit_version_id"]
    if audit_version_id == 3:
        background_tasks.add_task(_score_and_report, audit_id)
        return {"ok": True, "audit_id": audit_id, "status": "processing"}
    return {"ok": True, "audit_id": audit_id, "status": "completed"}


@app.post("/api/audit/{audit_id}/score")
def audit_score(audit_id: int, request: Request) -> dict[str, Any]:
    """Re-score an existing audit. Useful for backfills + after schema fixes."""
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me or me[0]["role"] != "admin":
        raise HTTPException(403, "admin only")
    a = rows("SELECT audit_version_id FROM audits WHERE audit_id = %s", (audit_id,))
    if not a:
        raise HTTPException(404, "audit not found")
    if a[0]["audit_version_id"] != 3:
        raise HTTPException(400, "scoring engine only supports media_sales_v1 (version 3)")
    from app.dna_scoring import score_audit
    from app.dna_report  import generate_report
    score  = score_audit(audit_id)
    report = generate_report(audit_id)
    email_job_id = _enqueue_email_job(audit_id, report["report_id"], report["pdf_path"])
    from app.email_dispatcher import send_report_email
    send_report_email(audit_id, report["report_id"], report["pdf_path"])
    return {
        "ok":          True,
        "audit_id":    audit_id,
        "archetype":             score["archetype"],
        "archetype_description": score.get("archetype_description"),
        "eq_identity":           score["eq_identity"],
        "scores_100":            {k: round(v, 1) for k, v in score["scores_100"].items()},
        "bands":                 score["bands"],
        "confidence":            round(score["confidence"], 3),
        "report":                report,
        "email_job_id":          email_job_id,
    }


@app.get("/api/reports/{report_id}/download")
def report_download(report_id: int, request: Request):
    r = rows("SELECT report_id, pdf_path, audit_id FROM reports WHERE report_id = %s", (report_id,))
    if not r:
        raise HTTPException(404, "report not found")
    caller = _caller_from_request(request)
    if not caller:
        raise HTTPException(401, "not authenticated")
    me = rows("SELECT role, team_id, company_id FROM respondents WHERE respondent_id = %s", (int(caller["sub"]),))
    if not me:
        raise HTTPException(401, "not authenticated")
    caller_role = me[0]["role"]
    if caller_role != "admin":
        owner = rows(
            "SELECT resp.respondent_id, resp.team_id, resp.company_id "
            "FROM audits a JOIN respondents resp ON resp.respondent_id = a.respondent_id "
            "WHERE a.audit_id = %s",
            (r[0]["audit_id"],),
        )
        if not owner:
            raise HTTPException(403, "forbidden")
        is_self = owner[0]["respondent_id"] == int(caller["sub"])
        is_team_match = caller_role == "sales_director" and me[0]["team_id"] == owner[0]["team_id"]
        is_company_match = caller_role in ("ceo", "hr", "learning_development") and me[0]["company_id"] and me[0]["company_id"] == owner[0]["company_id"]
        if not (is_self or is_team_match or is_company_match):
            raise HTTPException(403, "forbidden")
    path = r[0]["pdf_path"]
    if not path or not os.path.exists(path):
        raise HTTPException(410, "report file missing on disk")
    with open(path, "rb") as fh:
        data = fh.read()
    fname = os.path.basename(path)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.get("/api/squarespace/exports/{export_id}/download")
def squarespace_export_download(export_id: int) -> StreamingResponse:
    r = rows("SELECT * FROM squarespace_exports WHERE export_id = %s", (export_id,))
    if not r:
        raise HTTPException(404, "export not found")
    export = r[0]
    bundle_path = export.get("bundle_path", "")

    # Serve real on-disk bundle if it exists
    if bundle_path and os.path.isfile(bundle_path):
        fname = os.path.basename(bundle_path)
        def _stream():
            with open(bundle_path, "rb") as f:
                while chunk := f.read(65536):
                    yield chunk
        return StreamingResponse(
            _stream(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )

    # Fallback: build placeholder zip for legacy stub rows
    voice = scalar("SELECT voice_md FROM brand_voice WHERE id = 1") or ""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.md",
                    f"# Decipher Squarespace Bundle\n\n"
                    f"Export id: {export_id}\n"
                    f"Generated: {export['generated_at']}\n"
                    f"Note: regenerate this export to get real Claude-generated content.")
        zf.writestr("voice/brand_voice.md", voice)
        for path in _SQUARESPACE_FILE_TREE:
            if path in ("README.md", "voice/brand_voice.md"):
                continue
            zf.writestr(path, f"# Placeholder for {path} -- regenerate export for real content\n")
    buf.seek(0)
    fname = f"squarespace_export_{export_id}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.get("/api/squarespace/exports/{export_id}/files/{file_path:path}")
def squarespace_export_file(export_id: int, file_path: str) -> PlainTextResponse:
    """S061: Return the text content of a single file from the export zip for preview."""
    r = rows("SELECT bundle_path FROM squarespace_exports WHERE export_id = %s", (export_id,))
    if not r:
        raise HTTPException(404, "export not found")
    bundle_path = r[0].get("bundle_path", "")
    if not bundle_path or not os.path.isfile(bundle_path):
        raise HTTPException(404, "bundle not on disk -- regenerate this export")
    with zipfile.ZipFile(bundle_path, "r") as zf:
        try:
            content = zf.read(file_path).decode("utf-8")
        except KeyError:
            raise HTTPException(404, f"file not found in bundle: {file_path}")
    return PlainTextResponse(content)
