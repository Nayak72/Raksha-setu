-- ============================================================
-- RakshaSethu – Initial Database Migration
-- Run this in the Supabase SQL Editor
-- ============================================================

-- ── Enable Extensions ────────────────────────
CREATE EXTENSION IF NOT EXISTS postgis;          -- Geospatial
CREATE EXTENSION IF NOT EXISTS vector;           -- pgvector for RAG
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation

-- ── Zones ────────────────────────────────────
CREATE TABLE IF NOT EXISTS zones (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lat         DOUBLE PRECISION NOT NULL,
    lon         DOUBLE PRECISION NOT NULL,
    risk_score  DOUBLE PRECISION NOT NULL DEFAULT 0.0
        CHECK (risk_score >= 0.0 AND risk_score <= 10.0),
    geom        GEOMETRY(Point, 4326) GENERATED ALWAYS AS (
                    ST_SetSRID(ST_MakePoint(lon, lat), 4326)
                ) STORED,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_zones_geom ON zones USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_zones_risk  ON zones (risk_score DESC);

-- ── Volunteers ───────────────────────────────
CREATE TABLE IF NOT EXISTS volunteers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location        TEXT NOT NULL,  -- 'lat,lon' format
    status          TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available', 'dispatched', 'offline')),
    skill_level     INTEGER NOT NULL DEFAULT 1
        CHECK (skill_level >= 1 AND skill_level <= 5),
    last_assigned_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_volunteers_status ON volunteers (status);
CREATE INDEX IF NOT EXISTS idx_volunteers_skill  ON volunteers (skill_level DESC);

-- ── Shelters ─────────────────────────────────
CREATE TABLE IF NOT EXISTS shelters (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location        TEXT NOT NULL,  -- 'lat,lon' format
    capacity        INTEGER NOT NULL CHECK (capacity >= 0),
    available_beds  INTEGER NOT NULL CHECK (available_beds >= 0),
    created_at      TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT beds_lte_capacity CHECK (available_beds <= capacity)
);

CREATE INDEX IF NOT EXISTS idx_shelters_beds ON shelters (available_beds DESC);

-- ── Detections ───────────────────────────────
CREATE TABLE IF NOT EXISTS detections (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone_id     UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    count       INTEGER NOT NULL CHECK (count >= 0),
    metadata    JSONB,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_detections_zone      ON detections (zone_id);
CREATE INDEX IF NOT EXISTS idx_detections_timestamp  ON detections (timestamp DESC);

-- ── Alerts ───────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone        TEXT NOT NULL,
    message     TEXT NOT NULL,
    severity    TEXT NOT NULL DEFAULT 'medium'
        CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alerts_severity  ON alerts (severity);
CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts (timestamp DESC);

-- ── Acknowledgments ──────────────────────────
CREATE TABLE IF NOT EXISTS acknowledgments (
    device_id   TEXT NOT NULL,
    alert_id    UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'received'
        CHECK (status IN ('received', 'read', 'acted')),
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (device_id, alert_id)
);

CREATE INDEX IF NOT EXISTS idx_ack_alert ON acknowledgments (alert_id);

-- ── Documents (RAG / pgvector) ───────────────
CREATE TABLE IF NOT EXISTS documents (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content     TEXT NOT NULL,
    embedding   vector(384),  -- matches all-MiniLM-L6-v2 output dimension
    metadata    JSONB DEFAULT '{}',
    doc_type    TEXT NOT NULL DEFAULT 'general',
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_embedding
    ON documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents (doc_type);

-- ── RPC: Atomic bed decrement ────────────────
CREATE OR REPLACE FUNCTION decrement_beds(
    p_shelter_id UUID,
    p_count INTEGER DEFAULT 1
) RETURNS VOID AS $$
BEGIN
    UPDATE shelters
    SET available_beds = GREATEST(0, available_beds - p_count)
    WHERE id = p_shelter_id;
END;
$$ LANGUAGE plpgsql;

-- ── Trigger: NOTIFY on detection insert ──────
CREATE OR REPLACE FUNCTION notify_new_detection()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify(
        'new_detection',
        json_build_object(
            'id', NEW.id,
            'zone_id', NEW.zone_id,
            'count', NEW.count
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_new_detection ON detections;
CREATE TRIGGER trg_new_detection
    AFTER INSERT ON detections
    FOR EACH ROW
    EXECUTE FUNCTION notify_new_detection();

-- ── Seed data (optional – remove in production) ─
INSERT INTO zones (lat, lon, risk_score) VALUES
    (19.0760, 72.8777, 2.5),   -- Mumbai
    (28.6139, 77.2090, 1.0),   -- Delhi
    (13.0827, 80.2707, 3.0),   -- Chennai
    (22.5726, 88.3639, 2.0),   -- Kolkata
    (12.9716, 77.5946, 1.5)    -- Bangalore
ON CONFLICT DO NOTHING;

INSERT INTO volunteers (location, status, skill_level) VALUES
    ('19.0760,72.8777', 'available', 4),
    ('19.0800,72.8800', 'available', 3),
    ('28.6139,77.2090', 'available', 5),
    ('13.0827,80.2707', 'available', 2),
    ('22.5726,88.3639', 'available', 3),
    ('12.9716,77.5946', 'available', 4),
    ('19.0700,72.8700', 'dispatched', 3),
    ('28.6200,77.2100', 'available', 1)
ON CONFLICT DO NOTHING;

INSERT INTO shelters (location, capacity, available_beds) VALUES
    ('19.0800,72.8900', 200, 150),
    ('28.6200,77.2200', 300, 280),
    ('13.0900,80.2800', 150, 100),
    ('22.5800,88.3700', 250, 200),
    ('12.9800,77.6000', 180, 120)
ON CONFLICT DO NOTHING;
