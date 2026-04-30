-- ============================================================
-- RakshaSetu – RAG Memory Tables (pgvector)
-- Run this in the Supabase SQL Editor AFTER 002_agent_logs.sql
-- ============================================================
--
-- These tables provide a PostgreSQL-backed fallback for RAG
-- queries using pgvector, complementing the ChromaDB store.
-- They enable SQL-level similarity search and structured querying.
--

-- Ensure pgvector extension is available (should be from 001)
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Weather History (pgvector) ──────────────────────────────
-- Stores weather events with their embeddings for similarity search.

CREATE TABLE IF NOT EXISTS weather_memory (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone_id         UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    severity        TEXT NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    rainfall_mm     DOUBLE PRECISION NOT NULL DEFAULT 0,
    wind_speed_kmh  DOUBLE PRECISION NOT NULL DEFAULT 0,
    humidity_pct    DOUBLE PRECISION NOT NULL DEFAULT 0,
    temperature_c   DOUBLE PRECISION NOT NULL DEFAULT 0,
    confidence      DOUBLE PRECISION NOT NULL DEFAULT 0,
    routing_decision TEXT,
    document_text   TEXT NOT NULL,           -- Human-readable text for the event
    embedding       vector(384),             -- Sentence-transformer embedding
    metadata        JSONB DEFAULT '{}',
    source          TEXT NOT NULL DEFAULT 'weather_agent',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_weather_memory_zone
    ON weather_memory (zone_id);
CREATE INDEX IF NOT EXISTS idx_weather_memory_severity
    ON weather_memory (severity);
CREATE INDEX IF NOT EXISTS idx_weather_memory_created
    ON weather_memory (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_memory_embedding
    ON weather_memory USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);


-- ── Detection History (pgvector) ────────────────────────────
-- Stores YOLO detection events with embeddings.

CREATE TABLE IF NOT EXISTS detection_memory (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone_id             UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    crowd_density       DOUBLE PRECISION NOT NULL DEFAULT 0,
    flood_level         DOUBLE PRECISION NOT NULL DEFAULT 0,
    structural_damage   DOUBLE PRECISION NOT NULL DEFAULT 0,
    fire_detected       BOOLEAN NOT NULL DEFAULT FALSE,
    vehicle_count       INTEGER NOT NULL DEFAULT 0,
    confidence          DOUBLE PRECISION NOT NULL DEFAULT 0,
    document_text       TEXT NOT NULL,
    embedding           vector(384),
    metadata            JSONB DEFAULT '{}',
    source              TEXT NOT NULL DEFAULT 'yolo_detection',
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_detection_memory_zone
    ON detection_memory (zone_id);
CREATE INDEX IF NOT EXISTS idx_detection_memory_created
    ON detection_memory (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_detection_memory_embedding
    ON detection_memory USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);


-- ── Zone Event Memory (pgvector) ────────────────────────────
-- Stores zone analysis decisions with embeddings.

CREATE TABLE IF NOT EXISTS zone_event_memory (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone_id             UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    decision            TEXT NOT NULL,
    weather_severity    TEXT,
    priority_score      DOUBLE PRECISION NOT NULL DEFAULT 0,
    document_text       TEXT NOT NULL,
    embedding           vector(384),
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_zone_event_memory_zone
    ON zone_event_memory (zone_id);
CREATE INDEX IF NOT EXISTS idx_zone_event_memory_decision
    ON zone_event_memory (decision);
CREATE INDEX IF NOT EXISTS idx_zone_event_memory_created
    ON zone_event_memory (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_zone_event_memory_embedding
    ON zone_event_memory USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);


-- ── RPC: Cosine similarity search for weather ───────────────
CREATE OR REPLACE FUNCTION match_weather_memory(
    query_embedding vector(384),
    match_count     INT DEFAULT 5,
    filter_zone_id  UUID DEFAULT NULL
)
RETURNS TABLE (
    id              UUID,
    zone_id         UUID,
    severity        TEXT,
    rainfall_mm     DOUBLE PRECISION,
    document_text   TEXT,
    similarity      DOUBLE PRECISION,
    created_at      TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        wm.id,
        wm.zone_id,
        wm.severity,
        wm.rainfall_mm,
        wm.document_text,
        1 - (wm.embedding <=> query_embedding) AS similarity,
        wm.created_at
    FROM weather_memory wm
    WHERE (filter_zone_id IS NULL OR wm.zone_id = filter_zone_id)
    ORDER BY wm.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- ── RPC: Cosine similarity search for detections ────────────
CREATE OR REPLACE FUNCTION match_detection_memory(
    query_embedding vector(384),
    match_count     INT DEFAULT 5,
    filter_zone_id  UUID DEFAULT NULL
)
RETURNS TABLE (
    id              UUID,
    zone_id         UUID,
    crowd_density   DOUBLE PRECISION,
    flood_level     DOUBLE PRECISION,
    document_text   TEXT,
    similarity      DOUBLE PRECISION,
    created_at      TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dm.id,
        dm.zone_id,
        dm.crowd_density,
        dm.flood_level,
        dm.document_text,
        1 - (dm.embedding <=> query_embedding) AS similarity,
        dm.created_at
    FROM detection_memory dm
    WHERE (filter_zone_id IS NULL OR dm.zone_id = filter_zone_id)
    ORDER BY dm.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- ── RPC: Cosine similarity search for zone events ───────────
CREATE OR REPLACE FUNCTION match_zone_event_memory(
    query_embedding vector(384),
    match_count     INT DEFAULT 5,
    filter_zone_id  UUID DEFAULT NULL
)
RETURNS TABLE (
    id              UUID,
    zone_id         UUID,
    decision        TEXT,
    priority_score  DOUBLE PRECISION,
    document_text   TEXT,
    similarity      DOUBLE PRECISION,
    created_at      TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        zem.id,
        zem.zone_id,
        zem.decision,
        zem.priority_score,
        zem.document_text,
        1 - (zem.embedding <=> query_embedding) AS similarity,
        zem.created_at
    FROM zone_event_memory zem
    WHERE (filter_zone_id IS NULL OR zem.zone_id = filter_zone_id)
    ORDER BY zem.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
