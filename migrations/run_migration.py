"""
Drop old tables and recreate with the correct RakshaSethu schema.
The pre-existing tables have incompatible column names and types.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


async def run_migration():
    host = os.getenv("SUPABASE_DB_HOST", "localhost").strip()
    port = os.getenv("SUPABASE_DB_PORT", "5432").strip()
    user = os.getenv("SUPABASE_DB_USER", "postgres").strip()
    password = os.getenv("SUPABASE_DB_PASSWORD", "").strip()
    dbname = os.getenv("SUPABASE_DB_NAME", "postgres").strip()
    
    import urllib.parse
    encoded_password = urllib.parse.quote(password)
    
    dsn = os.getenv("DATABASE_URL", f"postgresql://{user}:{encoded_password}@{host}:{port}/{dbname}")
    
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    conn = await asyncpg.connect(dsn, statement_cache_size=0, ssl=ssl_context)

    # 1. Drop old tables in dependency order
    drop_stmts = [
        "DROP TABLE IF EXISTS acknowledgments CASCADE",
        "DROP TABLE IF EXISTS detections CASCADE",
        "DROP TABLE IF EXISTS alerts CASCADE",
        "DROP TABLE IF EXISTS documents CASCADE",
        "DROP TABLE IF EXISTS volunteers CASCADE",
        "DROP TABLE IF EXISTS shelters CASCADE",
        "DROP TABLE IF EXISTS zones CASCADE",
    ]

    print("--- Dropping old tables ---")
    for stmt in drop_stmts:
        await conn.execute(stmt)
        table = stmt.split("EXISTS ")[1].split(" ")[0]
        print(f"  Dropped: {table}")

    # 2. Create tables with correct schema
    create_stmts = [
        # Zones
        ("""CREATE TABLE zones (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name TEXT NOT NULL DEFAULT 'Unknown Zone',
            disaster_type TEXT NOT NULL DEFAULT 'unknown',
            lat DOUBLE PRECISION NOT NULL,
            lon DOUBLE PRECISION NOT NULL,
            risk_score DOUBLE PRECISION NOT NULL DEFAULT 0.0
                CHECK (risk_score >= 0.0 AND risk_score <= 10.0),
            created_at TIMESTAMPTZ DEFAULT now()
        )""", "zones"),
        ("CREATE INDEX idx_zones_risk ON zones (risk_score DESC)", "idx_zones_risk"),

        # Volunteers
        ("""CREATE TABLE volunteers (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            location TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'available'
                CHECK (status IN ('available', 'dispatched', 'offline')),
            skill_level INTEGER NOT NULL DEFAULT 1
                CHECK (skill_level >= 1 AND skill_level <= 5),
            last_assigned_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now()
        )""", "volunteers"),
        ("CREATE INDEX idx_volunteers_status ON volunteers (status)", "idx_vol_status"),
        ("CREATE INDEX idx_volunteers_skill ON volunteers (skill_level DESC)", "idx_vol_skill"),

        # Shelters
        ("""CREATE TABLE shelters (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            location TEXT NOT NULL,
            capacity INTEGER NOT NULL CHECK (capacity >= 0),
            available_beds INTEGER NOT NULL CHECK (available_beds >= 0),
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT beds_lte_capacity CHECK (available_beds <= capacity)
        )""", "shelters"),
        ("CREATE INDEX idx_shelters_beds ON shelters (available_beds DESC)", "idx_shelters_beds"),

        # Detections
        ("""CREATE TABLE detections (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            zone_id UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
            count INTEGER NOT NULL CHECK (count >= 0),
            metadata JSONB,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
        )""", "detections"),
        ("CREATE INDEX idx_detections_zone ON detections (zone_id)", "idx_det_zone"),
        ("CREATE INDEX idx_detections_timestamp ON detections (timestamp DESC)", "idx_det_ts"),

        # Alerts
        ("""CREATE TABLE alerts (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            zone TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'medium'
                CHECK (severity IN ('low', 'medium', 'high', 'critical')),
            timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
        )""", "alerts"),
        ("CREATE INDEX idx_alerts_severity ON alerts (severity)", "idx_alerts_sev"),
        ("CREATE INDEX idx_alerts_timestamp ON alerts (timestamp DESC)", "idx_alerts_ts"),

        # Acknowledgments
        ("""CREATE TABLE acknowledgments (
            device_id TEXT NOT NULL,
            alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
            status TEXT NOT NULL DEFAULT 'received'
                CHECK (status IN ('received', 'read', 'acted')),
            timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (device_id, alert_id)
        )""", "acknowledgments"),
        ("CREATE INDEX idx_ack_alert ON acknowledgments (alert_id)", "idx_ack_alert"),

        # Documents (RAG / pgvector)
        ("""CREATE TABLE documents (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            content TEXT NOT NULL,
            embedding vector(384),
            metadata JSONB DEFAULT '{}',
            doc_type TEXT NOT NULL DEFAULT 'general',
            created_at TIMESTAMPTZ DEFAULT now()
        )""", "documents"),
        ("CREATE INDEX idx_documents_type ON documents (doc_type)", "idx_doc_type"),
    ]

    print("\n--- Creating tables ---")
    for stmt, name in create_stmts:
        try:
            await conn.execute(stmt)
            print(f"  Created: {name}")
        except Exception as e:
            print(f"  ERROR creating {name}: {e}")

    # 3. Functions and triggers
    print("\n--- Functions & Triggers ---")
    funcs = [
        ("""CREATE OR REPLACE FUNCTION decrement_beds(
            p_shelter_id UUID, p_count INTEGER DEFAULT 1
        ) RETURNS VOID AS $$
        BEGIN
            UPDATE shelters SET available_beds = GREATEST(0, available_beds - p_count)
            WHERE id = p_shelter_id;
        END; $$ LANGUAGE plpgsql""", "decrement_beds"),

        ("""CREATE OR REPLACE FUNCTION notify_new_detection()
        RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify('new_detection',
                json_build_object('id', NEW.id, 'zone_id', NEW.zone_id, 'count', NEW.count)::text
            );
            RETURN NEW;
        END; $$ LANGUAGE plpgsql""", "notify_new_detection"),

        ("DROP TRIGGER IF EXISTS trg_new_detection ON detections", "drop_old_trigger"),

        ("""CREATE TRIGGER trg_new_detection
            AFTER INSERT ON detections FOR EACH ROW
            EXECUTE FUNCTION notify_new_detection()""", "trg_new_detection"),
    ]
    for stmt, name in funcs:
        await conn.execute(stmt)
        print(f"  Created: {name}")

    # 4. Seed data
    print("\n--- Seeding data ---")
    seeds = [
        ("""INSERT INTO zones (id, name, disaster_type, lat, lon, risk_score) VALUES
            ('11111111-1111-4111-8111-111111111111', 'Mangalore', 'flood', 12.8698, 74.8431, 3.5),
            ('22222222-2222-4222-8222-222222222222', 'Udupi-Malpe', 'cyclone', 13.3500, 74.7069, 2.5),
            ('33333333-3333-4333-8333-333333333333', 'Karwar', 'storm', 14.8024, 74.1293, 4.0),
            ('44444444-4444-4444-8444-444444444444', 'Chikkamagaluru', 'landslide', 13.1325, 75.6404, 3.0),
            ('55555555-5555-4555-8555-555555555555', 'DK-Puttur', 'flood', 12.7590, 75.2039, 2.0),
            ('66666666-6666-4666-8666-666666666666', 'Ankola', 'cyclone', 14.6600, 74.3039, 2.8),
            ('77777777-7777-4777-8777-777777777777', 'Sringeri', 'landslide', 13.4186, 75.2590, 3.2)""", "zones"),

        ("""INSERT INTO volunteers (location, status, skill_level) VALUES
            ('12.8698,74.8431', 'available', 4),
            ('12.8750,74.8800', 'available', 3),
            ('13.3500,74.7069', 'available', 5),
            ('14.8024,74.1293', 'available', 2),
            ('13.1325,75.6404', 'available', 3),
            ('12.7590,75.2039', 'available', 4),
            ('14.6600,74.3039', 'dispatched', 3),
            ('13.4186,75.2590', 'available', 1)""", "volunteers"),

        ("""INSERT INTO shelters (location, capacity, available_beds) VALUES
            ('12.8750,74.8800', 1200, 950),
            ('13.3400,74.7400', 900, 700),
            ('14.8100,74.1500', 1000, 800),
            ('13.1400,75.6100', 500, 380),
            ('12.7650,75.2200', 750, 600),
            ('14.6700,74.3200', 650, 500),
            ('13.4250,75.2300', 450, 350)""", "shelters"),
    ]
    for stmt, name in seeds:
        await conn.execute(stmt)
        count = await conn.fetchval(f"SELECT count(*) FROM {name}")
        print(f"  Seeded {name}: {count} rows")

    # 5. Verify
    print("\n--- Final verification ---")
    for table in ["zones", "volunteers", "shelters", "detections", "alerts", "acknowledgments", "documents"]:
        count = await conn.fetchval(f"SELECT count(*) FROM {table}")
        cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = $1 ORDER BY ordinal_position",
            table,
        )
        col_names = [c["column_name"] for c in cols]
        print(f"  {table}: {count} rows, columns: {col_names}")

    await conn.close()
    print("\n✅ Migration complete!")


if __name__ == "__main__":
    asyncio.run(run_migration())
