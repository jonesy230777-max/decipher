"""Decipher FastAPI surface (spec §6).

All endpoints DB-driven. No hardcoded numbers. Magic-link auth + JWT roles
land at M5; the prototype currently treats the operator as the implied caller.
"""
from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .db import conn, rows, scalar

app = FastAPI(title="Decipher", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "version": app.version, "now": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/bootstrap")
def bootstrap() -> dict[str, Any]:
    counts = {
        "respondents":  scalar("SELECT count(*) FROM respondents WHERE role='respondent'") or 0,
        "operators":    scalar("SELECT count(*) FROM respondents WHERE role='operator'") or 0,
        "executives":   scalar("SELECT count(*) FROM respondents WHERE role='executive'") or 0,
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
        "served_at": datetime.utcnow().isoformat() + "Z",
    }


# ---------------------------------------------------------------------------
# Events + reference
# ---------------------------------------------------------------------------


@app.get("/api/events")
def recent_events(limit: int = 200) -> dict[str, Any]:
    limit = max(1, min(limit, 1000))
    data = rows(
        "SELECT id, occurred_at, actor, action, severity, subject_id, payload "
        "FROM events_log ORDER BY occurred_at DESC LIMIT %s",
        (limit,),
    )
    return {"events": data, "count": len(data)}


@app.get("/api/industries")
def industries() -> dict[str, Any]:
    return {"industries": rows("SELECT * FROM industries ORDER BY code")}


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
def audits_list(limit: int = 200, status: str | None = None) -> dict[str, Any]:
    where = ""
    params: tuple = ()
    if status:
        where = "WHERE a.status = %s"
        params = (status,)
    data = rows(
        f"""SELECT a.audit_id, a.status, a.started_at, a.completed_at,
                  r.email, r.name AS respondent_name, r.company, r.industry,
                  s.cognitive_empathy, s.eq, s.pressure_composure, s.storytelling,
                  ar.code AS archetype_code, ar.name AS archetype_name,
                  aa.confidence AS archetype_confidence,
                  rep.report_id, rep.pdf_path
             FROM audits a
             JOIN respondents r ON r.respondent_id = a.respondent_id
        LEFT JOIN audit_scores s ON s.audit_id = a.audit_id
        LEFT JOIN archetype_assignments aa ON aa.audit_id = a.audit_id
        LEFT JOIN archetypes ar ON ar.archetype_id = aa.archetype_id
        LEFT JOIN reports rep ON rep.audit_id = a.audit_id AND rep.version = 1
            {where}
            ORDER BY a.started_at DESC
            LIMIT %s""",
        params + (max(1, min(limit, 1000)),),
    )
    return {"audits": data, "count": len(data)}


# ---------------------------------------------------------------------------
# Cohort
# ---------------------------------------------------------------------------


@app.get("/api/cohort/stats")
def cohort_stats() -> dict[str, Any]:
    totals = rows(
        """SELECT count(*) AS total_audits,
                  avg(cognitive_empathy) AS mean_cognitive_empathy,
                  avg(eq) AS mean_eq,
                  avg(pressure_composure) AS mean_pressure_composure,
                  avg(storytelling) AS mean_storytelling
             FROM audit_scores"""
    )
    by_band = rows(
        """SELECT dimension, band, count(*) AS n
             FROM band_classifications
             GROUP BY dimension, band
             ORDER BY dimension, band"""
    )
    by_archetype = rows(
        """SELECT ar.code, ar.name, count(*) AS n
             FROM archetype_assignments aa
             JOIN archetypes ar USING (archetype_id)
             WHERE aa.taxonomy_id = 1
             GROUP BY ar.code, ar.name
             ORDER BY n DESC"""
    )
    snapshots = rows(
        """SELECT snapshot_date, total_audits,
                  mean_cognitive_empathy, mean_eq,
                  mean_pressure_composure, mean_storytelling
             FROM cohort_snapshots
             ORDER BY snapshot_date"""
    )
    return {
        "totals": totals[0] if totals else None,
        "by_band": by_band,
        "by_archetype": by_archetype,
        "trend": snapshots,
    }


@app.get("/api/cohort/patterns")
def cohort_patterns() -> dict[str, Any]:
    data = rows(
        """SELECT pattern_id, name, conditions_json, hit_rate, n_observations,
                  bh_p_value, oos_hit_rate, robust, doubt_passed, discovered_at
             FROM pattern_library
             ORDER BY doubt_passed DESC, hit_rate DESC NULLS LAST"""
    )
    return {"patterns": data, "count": len(data)}


# ---------------------------------------------------------------------------
# Teams (executive dashboard data)
# ---------------------------------------------------------------------------


@app.get("/api/teams")
def teams_list() -> dict[str, Any]:
    data = rows(
        """SELECT t.team_id, t.name, t.organisation, t.role_label,
                  count(r.respondent_id) AS n_respondents
             FROM teams t
        LEFT JOIN respondents r ON r.team_id = t.team_id AND r.role='respondent'
             GROUP BY t.team_id
             ORDER BY t.name"""
    )
    return {"teams": data}


def _team_or_404(team_id: int) -> dict:
    t = rows("SELECT * FROM teams WHERE team_id = %s", (team_id,))
    if not t:
        raise HTTPException(404, "team not found")
    return t[0]


@app.get("/api/teams/{team_id}/overview")
def team_overview(team_id: int) -> dict[str, Any]:
    t = _team_or_404(team_id)
    n = scalar(
        "SELECT count(*) FROM respondents WHERE team_id = %s AND role='respondent'",
        (team_id,),
    ) or 0
    scores = rows(
        """SELECT avg(cognitive_empathy) AS ce, avg(eq) AS eq,
                  avg(pressure_composure) AS pc, avg(storytelling) AS st
             FROM audit_scores s
             JOIN audits a USING (audit_id)
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s""",
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
    }


def _band_for(score: float) -> str:
    if score >= 0.80: return "Elite"
    if score >= 0.60: return "Performing"
    if score >= 0.40: return "Practising"
    return "Developing"


@app.get("/api/teams/{team_id}/distribution")
def team_distribution(team_id: int) -> dict[str, Any]:
    _team_or_404(team_id)
    raw = rows(
        """SELECT bc.dimension, bc.band, count(*) AS n
             FROM band_classifications bc
             JOIN audits a USING (audit_id)
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s
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
def team_trait_averages(team_id: int) -> dict[str, Any]:
    _team_or_404(team_id)
    row = rows(
        """SELECT avg(cognitive_empathy) AS cognitive_empathy,
                  avg(eq) AS eq,
                  avg(pressure_composure) AS pressure_composure,
                  avg(storytelling) AS storytelling
             FROM audit_scores s
             JOIN audits a USING (audit_id)
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s""",
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
def team_archetypes(team_id: int) -> dict[str, Any]:
    _team_or_404(team_id)
    data = rows(
        """SELECT ar.code, ar.name, count(*) AS n
             FROM archetype_assignments aa
             JOIN archetypes ar USING (archetype_id)
             JOIN audits a ON a.audit_id = aa.audit_id
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s
            GROUP BY ar.code, ar.name
            ORDER BY n DESC""",
        (team_id,),
    )
    return {"archetypes": data}


@app.get("/api/teams/{team_id}/interventions")
def team_interventions(team_id: int) -> dict[str, Any]:
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
                f"This segment scores below 0.40 on {label_for[d['dimension']]}. "
                f"{intervention_for[d['dimension']]}",
            "kind": "at_risk",
        })
    # Pair top performers
    elite = scalar(
        """SELECT count(*) FROM audit_scores s
             JOIN audits a USING (audit_id)
             JOIN respondents r ON r.respondent_id = a.respondent_id
            WHERE r.team_id = %s
              AND s.cognitive_empathy >= 0.80 AND s.eq >= 0.80
              AND s.pressure_composure >= 0.80 AND s.storytelling >= 0.80""",
        (team_id,),
    ) or 0
    out.append({
        "headline": f"Pair your top {int(elite)} Elite performers",
        "body":
            "Pair each Elite rep with two at-risk reps as in-quarter coaches. "
            "Light load on the Elites, fast lift for the cohort, and you bank "
            "ROI evidence for the re-audit at 3 months.",
        "kind": "leverage",
    })
    return {"interventions": out}


@app.get("/api/teams/{team_id}/audits")
def team_audits(team_id: int) -> dict[str, Any]:
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


@app.get("/api/promo-codes")
def promo_codes_list() -> dict[str, Any]:
    return {"promo_codes": rows(
        """SELECT code, code_type, discount_pct, uses_remaining,
                  valid_until, source_campaign, created_at
             FROM promo_codes ORDER BY created_at DESC"""
    )}


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


@app.get("/api/squarespace/exports/{export_id}/download")
def squarespace_export_download(export_id: int) -> StreamingResponse:
    r = rows("SELECT * FROM squarespace_exports WHERE export_id = %s", (export_id,))
    if not r:
        raise HTTPException(404, "export not found")
    export = r[0]

    # M10 will serve the actual on-disk bundle. Today, build a placeholder zip
    # in-memory so the Download Bundle button delivers a real file end-to-end.
    voice = scalar("SELECT voice_md FROM brand_voice WHERE id = 1") or ""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.md",
                    f"# Decipher Squarespace Bundle (DUMMY)\n\n"
                    f"Export id: {export_id}\n"
                    f"Generated: {export['generated_at']}\n"
                    f"Summary: {export['summary']}\n\n"
                    f"Real bundle assembly lands in M10.")
        zf.writestr("voice/brand_voice.md", voice)
        for path in _SQUARESPACE_FILE_TREE:
            if path in ("README.md", "voice/brand_voice.md"):
                continue
            zf.writestr(path, f"# DUMMY placeholder for {path}\n")
        zf.writestr("design/tokens.json", json.dumps({"dummy": True}, indent=2))
    buf.seek(0)
    fname = os.path.basename(export["bundle_path"]) or f"squarespace_export_{export_id}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
