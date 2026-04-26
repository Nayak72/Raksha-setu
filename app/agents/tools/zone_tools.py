"""
RakshaSetu — MCP Zone Tools
LangChain tool interfaces for zone data and weather data retrieval.

Schema alignment:
  zones          → TEXT id, name, lat, lon, terrain_type, population_density
  weather_records → zone_id FK, rainfall_mm, wind_speed_kmh, humidity_pct,
                    temperature_c, severity, source
  detection_events → zone_id FK, crowd_density, flood_level, structural_damage,
                     fire_detected, vehicle_count, confidence
"""

import logging
from langchain_core.tools import tool
from app.db.supabase_client import get_supabase as get_supabase_client

logger = logging.getLogger("raksha.tools.zone")


@tool
def get_zone_data(zone_id: str) -> dict:
    """
    Fetch complete zone data from Supabase including the latest detection event.
    Returns zone metadata, terrain info, and the most recent detection readings.
    Use this tool to assess the current state of a disaster zone.
    """
    try:
        client = get_supabase_client()

        # 1. Fetch zone record
        zone_resp = (
            client.table("zones")
            .select("id, name, latitude, longitude, terrain_type, elevation_m, area_sq_km, population_density")
            .eq("id", zone_id)
            .single()
            .execute()
        )
        zone = zone_resp.data
        if not zone:
            return {"error": f"Zone {zone_id} not found", "zone_id": zone_id, "fallback": True}

        # 2. Fetch latest detection event for this zone
        det_resp = (
            client.table("detection_events")
            .select("crowd_density, flood_level, structural_damage, fire_detected, vehicle_count, confidence, timestamp")
            .eq("zone_id", zone_id)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        detection = (det_resp.data or [{}])[0] if det_resp.data else {}

        return {
            "zone_id": zone["id"],
            "name": zone["name"],
            "latitude": zone["latitude"],
            "longitude": zone["longitude"],
            "terrain_type": zone.get("terrain_type", "flat"),
            "elevation_m": zone.get("elevation_m", 0),
            "area_sq_km": zone.get("area_sq_km", 0),
            "population_density": zone.get("population_density", 0),
            "crowd_density": detection.get("crowd_density", 0.0),
            "flood_level": detection.get("flood_level", 0.0),
            "structural_damage": detection.get("structural_damage", 0.0),
            "fire_detected": detection.get("fire_detected", False),
            "vehicle_count": detection.get("vehicle_count", 0),
            "detection_confidence": detection.get("confidence", 0.0),
            "detection_timestamp": str(detection.get("timestamp", "")),
            "fallback": False,
        }

    except Exception as e:
        logger.error(f"get_zone_data failed for zone {zone_id}: {e}")
        return {
            "error": str(e),
            "zone_id": zone_id,
            "crowd_density": 0.0,
            "flood_level": 0.0,
            "structural_damage": 0.0,
            "fire_detected": False,
            "population_density": 0,
            "fallback": True,
        }


@tool
def get_weather_data(zone_id: str) -> dict:
    """
    Fetch the latest weather record for a given zone from the weather_records table.
    Returns rainfall, wind speed, humidity, temperature, and severity.
    Use this tool to evaluate environmental factors that could worsen a disaster.
    """
    try:
        client = get_supabase_client()

        resp = (
            client.table("weather_records")
            .select("rainfall_mm, wind_speed_kmh, humidity_pct, temperature_c, severity, source, timestamp")
            .eq("zone_id", zone_id)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        weather = (resp.data or [{}])[0] if resp.data else {}

        if not weather:
            return {
                "zone_id": zone_id,
                "rainfall_mm": 0.0,
                "wind_speed_kmh": 0.0,
                "humidity_pct": 0.0,
                "temperature_c": 30.0,
                "severity": "LOW",
                "source": "no_data",
                "fallback": True,
            }

        return {
            "zone_id": zone_id,
            "rainfall_mm": weather.get("rainfall_mm", 0.0),
            "wind_speed_kmh": weather.get("wind_speed_kmh", 0.0),
            "humidity_pct": weather.get("humidity_pct", 0.0),
            "temperature_c": weather.get("temperature_c", 30.0),
            "severity": weather.get("severity", "LOW"),
            "source": weather.get("source", "unknown"),
            "timestamp": str(weather.get("timestamp", "")),
            "fallback": False,
        }

    except Exception as e:
        logger.error(f"get_weather_data failed for zone {zone_id}: {e}")
        return {
            "zone_id": zone_id,
            "rainfall_mm": 0.0,
            "wind_speed_kmh": 0.0,
            "humidity_pct": 0.0,
            "temperature_c": 30.0,
            "severity": "LOW",
            "source": "error",
            "fallback": True,
        }
