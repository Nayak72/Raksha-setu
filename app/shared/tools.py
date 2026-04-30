"""
RakshaSetu — Shared Tool Functions
Reusable @tool-decorated functions for multiple agents.
"""

import json
import random
from datetime import datetime
from langchain_core.tools import tool
from app.db.connection import execute_query


# ============================================================
# WEATHER TOOLS
# ============================================================

@tool
def get_previous_weather(zone_id: str) -> str:
    """
    Retrieve the most recent weather record for a given zone.
    Returns JSON with rainfall_mm, wind_speed_kmh, humidity_pct, temperature_c, severity.
    """
    try:
        rows = execute_query(
            """
            SELECT rainfall_mm, wind_speed_kmh, humidity_pct, temperature_c, severity, source,
                   timestamp AT TIME ZONE 'UTC' as timestamp
            FROM weather_records
            WHERE zone_id = %s
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (zone_id,),
        )
        if rows:
            row = rows[0]
            row["timestamp"] = str(row["timestamp"])
            return json.dumps(row)
        return json.dumps({"error": "No weather data found", "zone_id": zone_id})
    except Exception as e:
        return json.dumps({"error": str(e), "zone_id": zone_id})


@tool
def get_zone_geography(zone_id: str) -> str:
    """
    Retrieve geographic/terrain data for a zone.
    Returns JSON with terrain_type, elevation_m, area_sq_km, latitude, longitude, population_density.
    """
    try:
        rows = execute_query(
            """
            SELECT name, terrain_type, elevation_m, area_sq_km,
                   latitude, longitude, population_density
            FROM zones
            WHERE id = %s
            """,
            (zone_id,),
        )
        if rows:
            return json.dumps(rows[0])
        return json.dumps({"error": "Zone not found", "zone_id": zone_id})
    except Exception as e:
        return json.dumps({"error": str(e), "zone_id": zone_id})


# ============================================================
# ZONE HISTORY TOOLS
# ============================================================

@tool
def get_zone_history(zone_id: str) -> str:
    """
    Retrieve the recent incident/detection history for a zone.
    Returns the last 10 detection events as JSON.
    """
    try:
        rows = execute_query(
            """
            SELECT crowd_density, flood_level, structural_damage,
                   fire_detected, vehicle_count, confidence,
                   timestamp AT TIME ZONE 'UTC' as timestamp
            FROM detection_events
            WHERE zone_id = %s
            ORDER BY timestamp DESC
            LIMIT 10
            """,
            (zone_id,),
        )
        for row in rows:
            row["timestamp"] = str(row["timestamp"])
        return json.dumps(rows)
    except Exception as e:
        return json.dumps({"error": str(e), "zone_id": zone_id})


@tool
def get_weather_trend(zone_id: str, hours: int = 24) -> str:
    """
    Retrieve weather trend data for a zone over the last N hours.
    Returns a list of weather records as JSON.
    """
    try:
        rows = execute_query(
            """
            SELECT rainfall_mm, wind_speed_kmh, humidity_pct,
                   temperature_c, severity,
                   timestamp AT TIME ZONE 'UTC' as timestamp
            FROM weather_records
            WHERE zone_id = %s
              AND timestamp >= NOW() - (%s * INTERVAL '1 hour')
            ORDER BY timestamp ASC
            """,
            (zone_id, hours),
        )
        for row in rows:
            row["timestamp"] = str(row["timestamp"])
        return json.dumps(rows)
    except Exception as e:
        return json.dumps({"error": str(e), "zone_id": zone_id})


# ============================================================
# RESOURCE TOOLS
# ============================================================

@tool
def get_shelters(zone_id: str, radius_km: float = 10.0) -> str:
    """
    Find shelters near a zone using PostGIS ST_Distance.
    Returns shelters within radius_km, sorted by distance.
    """
    try:
        rows = execute_query(
            """
            SELECT s.id, s.name, s.capacity, s.current_occupancy,
                   s.shelter_type, s.is_active,
                   ST_Distance(s.geom, z.geom) AS distance_m
            FROM shelters s, zones z
            WHERE z.id = %s
              AND s.is_active = TRUE
              AND ST_DWithin(s.geom, z.geom, %s)
            ORDER BY distance_m ASC
            """,
            (zone_id, radius_km * 1000),  # Convert km to meters
        )
        return json.dumps(rows)
    except Exception as e:
        return json.dumps({"error": str(e), "zone_id": zone_id})


@tool
def get_available_volunteers(zone_id: str, skill_type: str = "any") -> str:
    """
    Find available volunteers near a zone, optionally filtered by skill.
    Returns volunteers sorted by distance.
    """
    try:
        skill_filter = ""
        params = [zone_id]
        if skill_type != "any":
            skill_filter = "AND v.skill_type = %s"
            params.append(skill_type)

        rows = execute_query(
            f"""
            SELECT v.id, v.name, v.skill_type, v.current_workload, v.max_workload,
                   ST_Distance(v.geom, z.geom) AS distance_m
            FROM volunteers v, zones z
            WHERE z.id = %s
              AND v.is_available = TRUE
              AND v.current_workload < v.max_workload
              {skill_filter}
            ORDER BY distance_m ASC
            """,
            tuple(params),
        )
        return json.dumps(rows)
    except Exception as e:
        return json.dumps({"error": str(e), "zone_id": zone_id})


@tool
def update_assignments(assignments_json: str) -> str:
    """
    Create new resource assignments atomically.
    Input: JSON string with list of {zone_id, volunteer_id?, shelter_id?, assignment_type}.
    Uses row locking to prevent conflicts.
    """
    try:
        assignments = json.loads(assignments_json)
        results = []

        from app.db.connection import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                for a in assignments:
                    # Lock volunteer/shelter row to prevent concurrent assignment
                    if a.get("volunteer_id"):
                        cur.execute(
                            "SELECT id FROM volunteers WHERE id = %s FOR UPDATE",
                            (a["volunteer_id"],),
                        )
                        cur.execute(
                            "UPDATE volunteers SET current_workload = current_workload + 1 WHERE id = %s",
                            (a["volunteer_id"],),
                        )

                    if a.get("shelter_id"):
                        cur.execute(
                            "SELECT id FROM shelters WHERE id = %s FOR UPDATE",
                            (a["shelter_id"],),
                        )
                        cur.execute(
                            "UPDATE shelters SET current_occupancy = current_occupancy + 1 WHERE id = %s",
                            (a["shelter_id"],),
                        )

                    cur.execute(
                        """
                        INSERT INTO assignments (zone_id, volunteer_id, shelter_id, assignment_type, status)
                        VALUES (%s, %s, %s, %s, 'active')
                        RETURNING id
                        """,
                        (
                            a["zone_id"],
                            a.get("volunteer_id"),
                            a.get("shelter_id"),
                            a.get("assignment_type", "volunteer"),
                        ),
                    )
                    result = cur.fetchone()
                    results.append({"assignment_id": result[0], **a})

        return json.dumps({"status": "success", "assignments": results})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============================================================
# MOCK YOLO DETECTION
# ============================================================

def generate_mock_detection(zone_id: str) -> dict:
    """
    Generate realistic mock YOLO detection data for a zone.
    Stochastic — each call produces different values.
    """
    # Zone-specific base parameters (simulate different risk levels)
    zone_risk_profiles = {
        "zone_001": {"crowd": 0.3, "flood": 0.15, "damage": 0.05},
        "zone_002": {"crowd": 0.5, "flood": 0.35, "damage": 0.15},
        "zone_003": {"crowd": 0.8, "flood": 0.70, "damage": 0.30},
        "zone_004": {"crowd": 0.2, "flood": 0.05, "damage": 0.02},
        "zone_005": {"crowd": 0.1, "flood": 0.08, "damage": 0.01},
    }

    profile = zone_risk_profiles.get(
        zone_id, {"crowd": 0.3, "flood": 0.2, "damage": 0.1}
    )

    # Add stochastic noise
    noise = lambda base: max(0, min(1, base + random.gauss(0, 0.15)))

    return {
        "zone_id": zone_id,
        "timestamp": datetime.utcnow().isoformat(),
        "crowd_density": round(noise(profile["crowd"]), 3),
        "flood_level": round(noise(profile["flood"]), 3),
        "structural_damage": round(noise(profile["damage"]), 3),
        "fire_detected": random.random() < 0.05,  # 5% chance
        "vehicle_count": max(0, int(random.gauss(10, 5))),
        "confidence": round(random.uniform(0.80, 0.98), 3),
    }
