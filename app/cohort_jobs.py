"""M9 cohort intelligence jobs.

Two public entry points:
  run_snapshot()   -- S080: compute today's cohort snapshot and upsert to cohort_snapshots
  run_pattern_hunt() -- S081: 2-3 condition grid search with DOUBT gate, inserts to pattern_library

Both are safe to call repeatedly (idempotent snapshot, duplicate-protected patterns).
Scheduled via APScheduler wired into the FastAPI lifespan.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from itertools import combinations
from typing import Any

import numpy as np
from scipy import stats as scipy_stats

from app.db import conn, event, rows, scalar

log = logging.getLogger(__name__)

DIMS = ["cognitive_empathy", "eq", "pressure_composure", "storytelling"]
DIM_LABEL = {
    "cognitive_empathy":  "Cognitive Empathy",
    "eq":                 "EQ",
    "pressure_composure": "Pressure Composure",
    "storytelling":       "Storytelling",
}

# DOUBT gate thresholds (spec §S081)
DOUBT_MIN_HIT_RATE   = 0.60
DOUBT_MAX_BH_P       = 0.01
DOUBT_MIN_OOS_RATE   = 0.50
DOUBT_ROBUST_MARGIN  = 0.10
MIN_OBSERVATIONS     = 20   # skip patterns with too few examples


# ---------------------------------------------------------------------------
# S080 — Nightly cohort snapshot
# ---------------------------------------------------------------------------

def run_snapshot() -> dict[str, Any]:
    """Compute today's cohort aggregate and upsert into cohort_snapshots."""
    today = date.today()

    totals = rows(
        """SELECT count(*) AS n,
                  avg(cognitive_empathy)  AS ce,
                  avg(eq)                AS eq,
                  avg(pressure_composure) AS pc,
                  avg(storytelling)       AS st
             FROM audit_scores s
             JOIN audits a USING (audit_id)
            WHERE a.status IN ('scored','reported')"""
    )[0]

    band_dist = rows(
        """SELECT bc.dimension, bc.band, count(*) AS n
             FROM band_classifications bc
             JOIN audits a USING (audit_id)
            WHERE a.status IN ('scored','reported')
            GROUP BY bc.dimension, bc.band"""
    )
    band_json: dict[str, dict[str, int]] = {}
    for r in band_dist:
        band_json.setdefault(r["dimension"], {})[r["band"]] = int(r["n"])

    arch_dist = rows(
        """SELECT ar.code, ar.name, count(*) AS n
             FROM archetype_assignments aa
             JOIN archetypes ar USING (archetype_id)
             JOIN audits a ON a.audit_id = aa.audit_id
            WHERE aa.taxonomy_id = 2 AND a.status IN ('scored','reported')
            GROUP BY ar.code, ar.name"""
    )
    arch_json = {r["code"]: int(r["n"]) for r in arch_dist}

    with conn() as c, c.cursor() as cur:
        cur.execute(
            """INSERT INTO cohort_snapshots
                   (snapshot_date, total_audits,
                    mean_cognitive_empathy, mean_eq,
                    mean_pressure_composure, mean_storytelling,
                    band_distribution_json, archetype_distribution_json,
                    computed_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (snapshot_date) DO UPDATE SET
                   total_audits            = EXCLUDED.total_audits,
                   mean_cognitive_empathy  = EXCLUDED.mean_cognitive_empathy,
                   mean_eq                 = EXCLUDED.mean_eq,
                   mean_pressure_composure = EXCLUDED.mean_pressure_composure,
                   mean_storytelling       = EXCLUDED.mean_storytelling,
                   band_distribution_json  = EXCLUDED.band_distribution_json,
                   archetype_distribution_json = EXCLUDED.archetype_distribution_json,
                   computed_at             = EXCLUDED.computed_at""",
            (
                today,
                int(totals["n"]),
                float(totals["ce"] or 0),
                float(totals["eq"] or 0),
                float(totals["pc"] or 0),
                float(totals["st"] or 0),
                json.dumps(band_json),
                json.dumps(arch_json),
                datetime.now(timezone.utc),
            ),
        )

    event("cohort.snapshot", payload={"date": str(today), "total_audits": int(totals["n"])})
    log.info("cohort snapshot done: %s (%d audits)", today, totals["n"])
    return {"date": str(today), "total_audits": int(totals["n"])}


# ---------------------------------------------------------------------------
# S081 — Pattern hunter with DOUBT gate
# ---------------------------------------------------------------------------

def _load_vectors() -> list[dict[str, Any]]:
    """Load all scored audits with their scores, bands, and archetype."""
    data = rows(
        """SELECT s.audit_id,
                  s.cognitive_empathy, s.eq, s.pressure_composure, s.storytelling,
                  bc_ce.band  AS band_ce,
                  bc_eq.band  AS band_eq,
                  bc_pc.band  AS band_pc,
                  bc_st.band  AS band_st,
                  ar.code     AS archetype_code,
                  i.code      AS industry_code
             FROM audit_scores s
             JOIN audits a USING (audit_id)
             JOIN audit_versions av ON av.audit_version_id = a.audit_version_id
        LEFT JOIN industries i ON i.industry_id = av.industry_id
        LEFT JOIN band_classifications bc_ce ON bc_ce.audit_id = s.audit_id AND bc_ce.dimension = 'cognitive_empathy'
        LEFT JOIN band_classifications bc_eq ON bc_eq.audit_id = s.audit_id AND bc_eq.dimension = 'eq'
        LEFT JOIN band_classifications bc_pc ON bc_pc.audit_id = s.audit_id AND bc_pc.dimension = 'pressure_composure'
        LEFT JOIN band_classifications bc_st ON bc_st.audit_id = s.audit_id AND bc_st.dimension = 'storytelling'
        LEFT JOIN archetype_assignments aa ON aa.audit_id = s.audit_id AND aa.taxonomy_id = 2
        LEFT JOIN archetypes ar ON ar.archetype_id = aa.archetype_id AND ar.taxonomy_id = 2
            WHERE a.status IN ('scored','reported')"""
    )
    return list(data)


def _matches(row: dict[str, Any], conditions: list[dict[str, Any]]) -> bool:
    """Test whether a data row satisfies all conditions."""
    band_col = {
        "cognitive_empathy": "band_ce", "eq": "band_eq",
        "pressure_composure": "band_pc", "storytelling": "band_st",
    }
    for c in conditions:
        if "industry" in c:
            if row.get("industry_code") != c["industry"]:
                return False
        elif "archetype" in c:
            if row.get("archetype_code") != c["archetype"]:
                return False
        elif "band" in c:
            dim = c["dim"]
            if row.get(band_col[dim]) != c["band"]:
                return False
        elif "op" in c:
            dim = c["dim"]
            val = float(row.get(dim) or 0)
            threshold = c["val"]
            if c["op"] == "<" and not (val < threshold):
                return False
            if c["op"] == ">" and not (val > threshold):
                return False
    return True


def _compute_hit_rate(data: list[dict], conditions: list[dict]) -> tuple[int, int]:
    """Return (hits, total) for rows matching conditions."""
    hits = total = 0
    for row in data:
        if _matches(row, conditions[:-1]):   # antecedent: all but last condition
            total += 1
            if _matches(row, conditions):    # full pattern
                hits += 1
    return hits, total


def _bh_p_value(hits: int, total: int) -> float:
    """Binomial test p-value (one-sided: more hits than chance at 0.5)."""
    if total == 0:
        return 1.0
    result = scipy_stats.binomtest(hits, total, p=0.5, alternative="greater")
    return float(result.pvalue)


def _oos_hit_rate(data: list[dict], conditions: list[dict]) -> float:
    """Hold out 20% randomly, compute hit rate on holdout."""
    rng = np.random.default_rng(seed=42)
    n = len(data)
    holdout_idx = set(rng.choice(n, size=max(1, n // 5), replace=False).tolist())
    holdout = [data[i] for i in holdout_idx]
    hits, total = _compute_hit_rate(holdout, conditions)
    return hits / total if total > 0 else 0.0


def _robust_check(data: list[dict], conditions: list[dict], base_rate: float) -> bool:
    """Bootstrap 100 samples; check hit rate stays >= base_rate - 0.10 in 90% of runs."""
    rng = np.random.default_rng(seed=123)
    n = len(data)
    passes = 0
    for _ in range(100):
        sample = [data[i] for i in rng.choice(n, size=n, replace=True).tolist()]
        hits, total = _compute_hit_rate(sample, conditions)
        rate = hits / total if total > 0 else 0.0
        if rate >= base_rate - DOUBT_ROBUST_MARGIN:
            passes += 1
    return passes >= 90


def _pattern_name(conditions: list[dict]) -> str:
    band_label = {
        "developing": "Developing", "practising": "Practising",
        "performing": "Performing", "elite": "Elite",
    }
    parts = []
    for c in conditions:
        if "industry" in c:
            parts.append(c["industry"].title() + " industry")
        elif "archetype" in c:
            parts.append(c["archetype"].replace("_", " ").title() + " archetype")
        elif "band" in c:
            parts.append(f"{DIM_LABEL.get(c['dim'], c['dim'])} {band_label.get(c['band'], c['band'])}")
        elif "op" in c:
            symbol = "low" if c["op"] == "<" else "high"
            parts.append(f"{symbol} {DIM_LABEL.get(c['dim'], c['dim'])}")
    return " + ".join(parts)


def run_pattern_hunt() -> dict[str, Any]:
    """Grid search over 2-3 condition combinations. Insert DOUBT-passed patterns."""
    data = _load_vectors()
    n = len(data)
    if n < MIN_OBSERVATIONS * 2:
        log.info("pattern hunt skipped: only %d audits", n)
        return {"skipped": True, "reason": "insufficient data", "n": n}

    # Build candidate condition atoms
    bands = ["developing", "practising", "performing", "elite"]
    thresholds = [0.40, 0.50, 0.65, 0.85]
    atoms: list[dict] = []

    for dim in DIMS:
        for band in bands:
            atoms.append({"dim": dim, "band": band})
        for t in thresholds:
            atoms.append({"op": "<", "dim": dim, "val": t})
            atoms.append({"op": ">", "dim": dim, "val": t})

    industries = list({r["industry_code"] for r in data if r.get("industry_code")})
    archetypes  = list({r["archetype_code"]  for r in data if r.get("archetype_code")})
    for ind in industries:
        atoms.append({"industry": ind})
    for arch in archetypes:
        atoms.append({"archetype": arch})

    # Existing pattern names to skip duplicates
    existing = {r["name"] for r in rows("SELECT name FROM pattern_library")}

    candidates: list[dict[str, Any]] = []
    # Try 2-atom and 3-atom combinations
    for size in (2, 3):
        for combo in combinations(atoms, size):
            conditions = list(combo)
            name = _pattern_name(conditions)
            if name in existing:
                continue

            hits, total = _compute_hit_rate(data, conditions)
            if total < MIN_OBSERVATIONS:
                continue
            hit_rate = hits / total

            if hit_rate < DOUBT_MIN_HIT_RATE:
                continue

            p_val = _bh_p_value(hits, total)
            oos = _oos_hit_rate(data, conditions)
            robust = _robust_check(data, conditions, hit_rate)

            doubt_passed = (
                p_val < DOUBT_MAX_BH_P
                and oos >= DOUBT_MIN_OOS_RATE
                and robust
            )

            candidates.append({
                "name":           name,
                "conditions":     conditions,
                "hit_rate":       round(hit_rate, 4),
                "n_observations": total,
                "bh_p_value":     round(p_val, 6),
                "oos_hit_rate":   round(oos, 4),
                "robust":         robust,
                "doubt_passed":   doubt_passed,
            })

    # BH correction across all candidates
    if candidates:
        p_vals = np.array([c["bh_p_value"] for c in candidates])
        m = len(p_vals)
        ranked = np.argsort(p_vals)
        bh_thresholds = (np.arange(1, m + 1) / m) * DOUBT_MAX_BH_P
        bh_mask = np.zeros(m, dtype=bool)
        for k in range(m - 1, -1, -1):
            if p_vals[ranked[k]] <= bh_thresholds[k]:
                bh_mask[ranked[:k + 1]] = True
                break
        for i, c in enumerate(candidates):
            if not bh_mask[i]:
                c["doubt_passed"] = False

    inserted = 0
    for c in candidates:
        name = c["name"]
        if name in existing:
            continue
        with conn() as db, db.cursor() as cur:
            cur.execute(
                """INSERT INTO pattern_library
                       (name, conditions_json, evidence_json, hit_rate, n_observations,
                        bh_p_value, oos_hit_rate, robust, doubt_passed, discovered_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (
                    name,
                    json.dumps({"all": c["conditions"]}),
                    json.dumps({"hit_rate": c["hit_rate"], "n": c["n_observations"]}),
                    c["hit_rate"],
                    c["n_observations"],
                    c["bh_p_value"],
                    c["oos_hit_rate"],
                    c["robust"],
                    c["doubt_passed"],
                    datetime.now(timezone.utc),
                ),
            )
        existing.add(name)
        inserted += 1

    doubt_count = sum(1 for c in candidates if c["doubt_passed"])
    event("cohort.pattern_hunt", payload={
        "n_audits": n,
        "candidates": len(candidates),
        "inserted": inserted,
        "doubt_passed": doubt_count,
    })
    log.info("pattern hunt done: %d candidates, %d inserted, %d DOUBT-passed",
             len(candidates), inserted, doubt_count)
    return {"n_audits": n, "candidates": len(candidates), "inserted": inserted, "doubt_passed": doubt_count}
