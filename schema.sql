-- Decipher core schema (spec §3, architecture §4). DOUBLE PRECISION everywhere.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

------------------------------------------------------------------
-- Archetype taxonomies (BLOCKING decision D-006: 4 vs 8, switchable)
------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS archetype_taxonomies (
    taxonomy_id  INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    description  TEXT,
    is_active    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS archetypes (
    archetype_id BIGSERIAL PRIMARY KEY,
    taxonomy_id  INTEGER NOT NULL REFERENCES archetype_taxonomies(taxonomy_id),
    code         TEXT NOT NULL,
    name         TEXT NOT NULL,
    description  TEXT,
    UNIQUE (taxonomy_id, code)
);

------------------------------------------------------------------
-- Respondents + auth
------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS respondents (
    respondent_id BIGSERIAL PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    name          TEXT,
    company       TEXT,
    industry      TEXT,
    source        TEXT,
    promo_code    TEXT,
    role          TEXT NOT NULL DEFAULT 'sales_person'
                  CHECK (role IN ('admin','ceo','sales_director','hr','learning_development','sales_person')),
    team_id       BIGINT,
    consent_share_individual BOOLEAN NOT NULL DEFAULT FALSE,
    company_id    BIGINT REFERENCES companies(company_id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_respondents_team ON respondents (team_id);
CREATE INDEX IF NOT EXISTS idx_respondents_company ON respondents (company_id);

CREATE TABLE IF NOT EXISTS magic_link_tokens (
    token_hash    TEXT PRIMARY KEY,
    respondent_id BIGINT NOT NULL REFERENCES respondents(respondent_id),
    expires_at    TIMESTAMPTZ NOT NULL,
    consumed_at   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS companies (
    company_id   BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    industry     TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS teams (
    team_id      BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    company_id   BIGINT REFERENCES companies(company_id),
    organisation TEXT,                 -- legacy text mirror; kept for back-compat
    role_label   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_teams_company ON teams (company_id);

------------------------------------------------------------------
-- Audit versions, questions, audits, responses
------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS industries (
    industry_id   BIGSERIAL PRIMARY KEY,
    code          TEXT NOT NULL UNIQUE,
    name          TEXT NOT NULL,
    description   TEXT
);

CREATE TABLE IF NOT EXISTS audit_versions (
    audit_version_id BIGSERIAL PRIMARY KEY,
    code             TEXT NOT NULL UNIQUE,
    name             TEXT NOT NULL,
    industry_id      BIGINT REFERENCES industries(industry_id),
    bespoke_client_id BIGINT,
    band_thresholds_json JSONB NOT NULL DEFAULT
        '{"developing":[0.0,0.4],"practising":[0.4,0.6],"performing":[0.6,0.8],"elite":[0.8,1.0]}'::jsonb,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS questions (
    question_id      BIGSERIAL PRIMARY KEY,
    audit_version_id BIGINT NOT NULL REFERENCES audit_versions(audit_version_id),
    sequence         INTEGER NOT NULL,
    dimension        TEXT NOT NULL
                     CHECK (dimension IN ('cognitive_empathy','eq','pressure_composure','storytelling')),
    archetype_signal TEXT,
    weight           DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    prompt           TEXT NOT NULL,
    response_type    TEXT NOT NULL DEFAULT 'likert_5'
                     CHECK (response_type IN ('likert_5','likert_7','choice','free_text')),
    response_meta    JSONB,
    UNIQUE (audit_version_id, sequence)
);

CREATE TABLE IF NOT EXISTS audits (
    audit_id         BIGSERIAL PRIMARY KEY,
    respondent_id    BIGINT NOT NULL REFERENCES respondents(respondent_id),
    audit_version_id BIGINT NOT NULL REFERENCES audit_versions(audit_version_id),
    status           TEXT NOT NULL DEFAULT 'in_progress'
                     CHECK (status IN ('in_progress','completed','scored','reported','failed_quality_gate')),
    started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at     TIMESTAMPTZ,
    payment_ref      TEXT,
    promo_code       TEXT
);
CREATE INDEX IF NOT EXISTS idx_audits_status ON audits (status);

CREATE TABLE IF NOT EXISTS responses (
    response_id   BIGSERIAL PRIMARY KEY,
    audit_id      BIGINT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    question_id   BIGINT NOT NULL REFERENCES questions(question_id),
    answer_value  DOUBLE PRECISION,
    answer_text   TEXT,
    answered_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    response_ms   INTEGER,
    UNIQUE (audit_id, question_id)
);

CREATE TABLE IF NOT EXISTS audit_scores (
    audit_id            BIGINT PRIMARY KEY REFERENCES audits(audit_id) ON DELETE CASCADE,
    cognitive_empathy   DOUBLE PRECISION NOT NULL,
    eq                  DOUBLE PRECISION NOT NULL,
    pressure_composure  DOUBLE PRECISION NOT NULL,
    storytelling        DOUBLE PRECISION NOT NULL,
    raw_band_json       JSONB,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS archetype_assignments (
    audit_id     BIGINT PRIMARY KEY REFERENCES audits(audit_id) ON DELETE CASCADE,
    taxonomy_id  INTEGER NOT NULL REFERENCES archetype_taxonomies(taxonomy_id),
    archetype_id BIGINT NOT NULL REFERENCES archetypes(archetype_id),
    confidence   DOUBLE PRECISION NOT NULL,
    tiebreak_applied BOOLEAN NOT NULL DEFAULT FALSE,
    assigned_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS band_classifications (
    audit_id  BIGINT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    dimension TEXT NOT NULL,
    band      TEXT NOT NULL CHECK (band IN ('developing','practising','performing','elite')),
    score     DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (audit_id, dimension)
);

------------------------------------------------------------------
-- Reports
------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    report_id          BIGSERIAL PRIMARY KEY,
    audit_id           BIGINT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    pdf_path           TEXT NOT NULL,
    generated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    version            INTEGER NOT NULL DEFAULT 1,
    claude_model_used  TEXT,
    input_tokens       INTEGER,
    output_tokens      INTEGER,
    cost_usd           DOUBLE PRECISION,
    UNIQUE (audit_id, version)
);

------------------------------------------------------------------
-- Cohort analytics + pgvector
------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_score_vectors (
    audit_id  BIGINT PRIMARY KEY REFERENCES audits(audit_id) ON DELETE CASCADE,
    vec       vector(8) NOT NULL,
    -- 4 dimensions + 4 derived (consistency, response_time_variance, extremity, sentiment)
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_score_vectors_vec
    ON audit_score_vectors USING hnsw (vec vector_cosine_ops);

CREATE TABLE IF NOT EXISTS cohort_snapshots (
    snapshot_date         DATE PRIMARY KEY,
    total_audits          INTEGER NOT NULL,
    mean_cognitive_empathy DOUBLE PRECISION,
    mean_eq               DOUBLE PRECISION,
    mean_pressure_composure DOUBLE PRECISION,
    mean_storytelling     DOUBLE PRECISION,
    band_distribution_json JSONB,
    archetype_distribution_json JSONB,
    computed_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pattern_library (
    pattern_id      BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    conditions_json JSONB NOT NULL,
    evidence_json   JSONB,
    hit_rate        DOUBLE PRECISION,
    n_observations  INTEGER,
    bh_p_value      DOUBLE PRECISION,
    oos_hit_rate    DOUBLE PRECISION,
    robust          BOOLEAN,
    doubt_passed    BOOLEAN NOT NULL DEFAULT FALSE,
    discovered_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

------------------------------------------------------------------
-- Promo + bespoke
------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS promo_codes (
    code              TEXT PRIMARY KEY,
    code_type         TEXT NOT NULL CHECK (code_type IN ('free','discount')),
    discount_pct      DOUBLE PRECISION CHECK (discount_pct BETWEEN 0 AND 100),
    uses_remaining    INTEGER,
    valid_until       TIMESTAMPTZ,
    source_campaign   TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bespoke_clients (
    bespoke_client_id BIGSERIAL PRIMARY KEY,
    client_name       TEXT NOT NULL UNIQUE,
    custom_audit_version_id BIGINT REFERENCES audit_versions(audit_version_id),
    brand_assets_json JSONB,
    unique_url_slug   TEXT NOT NULL UNIQUE,
    estimated_value   DOUBLE PRECISION,
    status            TEXT NOT NULL DEFAULT 'draft'
                      CHECK (status IN ('draft','active','archived')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE audit_versions
    ADD CONSTRAINT fk_audit_versions_bespoke_client
    FOREIGN KEY (bespoke_client_id) REFERENCES bespoke_clients(bespoke_client_id);

------------------------------------------------------------------
-- Squarespace exports
------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS squarespace_exports (
    export_id     BIGSERIAL PRIMARY KEY,
    generated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    bundle_path   TEXT NOT NULL,
    file_count    INTEGER,
    size_bytes    BIGINT,
    summary       TEXT,
    cost_usd      DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS brand_voice (
    id           INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    voice_md     TEXT NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

------------------------------------------------------------------
-- Observability
------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events_log (
    id            BIGSERIAL PRIMARY KEY,
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor         TEXT,
    action        TEXT NOT NULL,
    severity      TEXT NOT NULL DEFAULT 'info'
                  CHECK (severity IN ('info','warning','error')),
    subject_id    TEXT,
    payload       JSONB
);
CREATE INDEX IF NOT EXISTS idx_events_log_occurred ON events_log (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_log_action ON events_log (action);

CREATE TABLE IF NOT EXISTS data_fetch_log (
    id           BIGSERIAL PRIMARY KEY,
    agent        TEXT NOT NULL,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ,
    status       TEXT NOT NULL,
    rows_written INTEGER,
    error        TEXT
);

------------------------------------------------------------------
-- Audit job queue (event-driven agents)
------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_jobs (
    job_id     BIGSERIAL PRIMARY KEY,
    audit_id   BIGINT NOT NULL REFERENCES audits(audit_id) ON DELETE CASCADE,
    job_type   TEXT NOT NULL CHECK (job_type IN ('score','report','reaudit_reminder','email')),
    status     TEXT NOT NULL DEFAULT 'queued'
               CHECK (status IN ('queued','running','done','error')),
    enqueued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    payload     JSONB,
    error       TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_jobs_queued
    ON audit_jobs (status, enqueued_at) WHERE status = 'queued';
