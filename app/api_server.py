"""Decipher FastAPI surface (spec §6).

All endpoints DB-driven. No hardcoded numbers. Magic-link auth + JWT roles
land at M5; M2 ships /api/health + bootstrap context (ports + counts) only.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import conn, event, rows, scalar

app = FastAPI(title="Decipher", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Container + DB health. No auth."""
    try:
        with conn() as c, c.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "db": False, "error": str(exc)}
    return {
        "status": "ok",
        "db": db_ok,
        "service": "decipher-api",
        "version": app.version,
        "now": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/bootstrap")
def bootstrap() -> dict[str, Any]:
    """Initial dashboard payload: resolved ports + table counts + active taxonomy.

    DB-driven. No hardcoded numbers. Used by Mission Control's header strip and
    by the empty-state copy on every page.
    """
    counts = {
        "respondents":  scalar("SELECT count(*) FROM respondents WHERE role = 'respondent'") or 0,
        "operators":    scalar("SELECT count(*) FROM respondents WHERE role = 'operator'") or 0,
        "audits":       scalar("SELECT count(*) FROM audits") or 0,
        "audits_today": scalar("SELECT count(*) FROM audits WHERE started_at::date = current_date") or 0,
        "audits_month": scalar(
            "SELECT count(*) FROM audits "
            "WHERE date_trunc('month', started_at) = date_trunc('month', current_date)"
        ) or 0,
        "reports":      scalar("SELECT count(*) FROM reports") or 0,
        "patterns_doubt_passed":
                        scalar("SELECT count(*) FROM pattern_library WHERE doubt_passed = TRUE") or 0,
        "industries":   scalar("SELECT count(*) FROM industries") or 0,
        "bespoke_clients": scalar("SELECT count(*) FROM bespoke_clients") or 0,
        "events_24h":   scalar(
            "SELECT count(*) FROM events_log WHERE occurred_at > now() - interval '24 hours'"
        ) or 0,
    }
    active = rows(
        "SELECT taxonomy_id, name FROM archetype_taxonomies WHERE is_active = TRUE LIMIT 1"
    )
    return {
        "ports": {
            "db":   os.getenv("DECIPHER_DB_PORT"),
            "api":  os.getenv("DECIPHER_API_PORT"),
            "web":  os.getenv("DECIPHER_WEB_PORT"),
            "mail": os.getenv("DECIPHER_MAIL_PORT"),
        },
        "counts": counts,
        "archetype_taxonomy_active": active[0] if active else None,
        "served_at": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/events")
def recent_events(limit: int = 50) -> dict[str, Any]:
    limit = max(1, min(limit, 500))
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
