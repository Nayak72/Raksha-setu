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
    name        TEXT NOT NULL DEFAULT 'Unknown Zone',
    disaster_type TEXT NOT NULL DEFAULT 'unknown',
    lat         DOUBLE PRECISION NOT NULL,
    lon         DOUBLE PRECISION NOT NULL,
    risk_score  DOUBLE PRECISION NOT NULL DEFAULT 0.0
        CHECK (risk_score >= 0.0 AND risk_score <= 10.0),
    geom        GEOMETRY(Point, 4326),
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_zones_geom ON zones USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_zones_risk  ON zones (risk_score DESC);

-- ── Trigger: Auto-populate geom from lat/lon ─
CREATE OR REPLACE FUNCTION zones_set_geom()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geom := ST_SetSRID(ST_MakePoint(NEW.lon, NEW.lat), 4326);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_zones_set_geom ON zones;
CREATE TRIGGER trg_zones_set_geom
    BEFORE INSERT OR UPDATE OF lat, lon ON zones
    FOR EACH ROW
    EXECUTE FUNCTION zones_set_geom();

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
-- 7 zones across coastal Karnataka matching the simulation engine
INSERT INTO zones (id, name, disaster_type, lat, lon, risk_score) VALUES
    ('11111111-1111-4111-8111-111111111111', 'Mangalore Coastal Flood Zone', 'flood', 12.8698, 74.8431, 3.5),
    ('22222222-2222-4222-8222-222222222222', 'Udupi-Malpe Cyclone Zone', 'cyclone', 13.3500, 74.7069, 2.5),
    ('33333333-3333-4333-8333-333333333333', 'Karwar Storm Surge Zone', 'storm', 14.8024, 74.1293, 4.0),
    ('44444444-4444-4444-8444-444444444444', 'Chikkamagaluru Landslide Zone', 'landslide', 13.1325, 75.6404, 3.0),
    ('55555555-5555-4555-8555-555555555555', 'DK-Puttur Flood Zone', 'flood', 12.7590, 75.2039, 2.0),
    ('66666666-6666-4666-8666-666666666666', 'Ankola Cyclone Zone', 'cyclone', 14.6600, 74.3039, 2.8),
    ('77777777-7777-4777-8777-777777777777', 'Sringeri Landslide Zone', 'landslide', 13.4186, 75.2590, 3.2)
ON CONFLICT DO NOTHING;

INSERT INTO volunteers (location, status, skill_level) VALUES
    ('12.8698,74.8431', 'available', 4),
    ('12.8750,74.8800', 'available', 3),
    ('13.3500,74.7069', 'available', 5),
    ('14.8024,74.1293', 'available', 2),
    ('13.1325,75.6404', 'available', 3),
    ('12.7590,75.2039', 'available', 4),
    ('14.6600,74.3039', 'dispatched', 3),
    ('13.4186,75.2590', 'available', 1)
ON CONFLICT DO NOTHING;

INSERT INTO shelters (location, capacity, available_beds) VALUES
    ('12.8750,74.8800', 1200, 950),    -- Mangalore Town Hall
    ('13.3400,74.7400', 900, 700),     -- Udupi Town Hall
    ('14.8100,74.1500', 1000, 800),    -- Karwar Stadium
    ('13.1400,75.6100', 500, 380),     -- Mudigere Govt College
    ('12.7650,75.2200', 750, 600),     -- Puttur Town Hall
    ('14.6700,74.3200', 650, 500),     -- Ankola High School
    ('13.4250,75.2300', 450, 350)      -- Sringeri Community Hall
ON CONFLICT DO NOTHING;
