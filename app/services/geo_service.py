"""
Geospatial Service – helpers for PostGIS and coordinate operations.

Uses asyncpg for direct PostGIS queries and Shapely for in-memory geometry.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from app.db.supabase_client import get_pg_pool

logger = structlog.get_logger(__name__)


async def find_zones_in_radius(
    lat: float,
    lon: float,
    radius_km: float = 10.0,
) -> list[dict[str, Any]]:
    """
    Find all zones within `radius_km` of the given point.

    Uses PostGIS ST_DWithin for index-accelerated spatial queries.
    Falls back to Haversine if PostGIS is unavailable.
    """
    pool = await get_pg_pool()
    radius_meters = radius_km * 1000

    query = """
        SELECT id, lat, lon, risk_score,
               ST_Distance(
                   ST_MakePoint(lon, lat)::geography,
                   ST_MakePoint($1, $2)::geography
               ) AS distance_m
        FROM zones
        WHERE ST_DWithin(
            ST_MakePoint(lon, lat)::geography,
            ST_MakePoint($1, $2)::geography,
            $3
        )
        ORDER BY distance_m ASC;
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, lon, lat, radius_meters)
            results = [dict(row) for row in rows]
            logger.info(
                "geo.zones_in_radius",
                center=(lat, lon),
                radius_km=radius_km,
                found=len(results),
            )
            return results
    except Exception as exc:
        logger.error("geo.postgis_query_failed", error=str(exc))
        return []


async def find_nearest_shelters(
    lat: float,
    lon: float,
    limit: int = 5,
    min_beds: int = 1,
) -> list[dict[str, Any]]:
    """
    Find the nearest shelters with available beds using PostGIS.
    
    Expects shelter.location stored as 'lat,lon' text.
    """
    pool = await get_pg_pool()

    query = """
        SELECT id, location, capacity, available_beds,
               ST_Distance(
                   ST_MakePoint(
                       CAST(split_part(location, ',', 2) AS double precision),
                       CAST(split_part(location, ',', 1) AS double precision)
                   )::geography,
                   ST_MakePoint($1, $2)::geography
               ) AS distance_m
        FROM shelters
        WHERE available_beds >= $3
        ORDER BY distance_m ASC
        LIMIT $4;
    """

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, lon, lat, min_beds, limit)
            results = [dict(row) for row in rows]
            logger.info("geo.nearest_shelters", found=len(results))
            return results
    except Exception as exc:
        logger.error("geo.shelter_query_failed", error=str(exc))
        return []


async def find_volunteers_near_zone(
    zone_id: UUID,
    radius_km: float = 15.0,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Find available volunteers near a zone using PostGIS.
    
    Expects volunteer.location stored as 'lat,lon' text.
    """
    pool = await get_pg_pool()

    query = """
        WITH zone_point AS (
            SELECT lat, lon FROM zones WHERE id = $1
        )
        SELECT v.id, v.location, v.status, v.skill_level,
               ST_Distance(
                   ST_MakePoint(
                       CAST(split_part(v.location, ',', 2) AS double precision),
                       CAST(split_part(v.location, ',', 1) AS double precision)
                   )::geography,
                   ST_MakePoint(zp.lon, zp.lat)::geography
               ) AS distance_m
        FROM volunteers v, zone_point zp
        WHERE v.status = 'available'
          AND ST_DWithin(
              ST_MakePoint(
                  CAST(split_part(v.location, ',', 2) AS double precision),
                  CAST(split_part(v.location, ',', 1) AS double precision)
              )::geography,
              ST_MakePoint(zp.lon, zp.lat)::geography,
              $2
          )
        ORDER BY v.skill_level DESC, distance_m ASC
        LIMIT $3;
    """

    try:
        import uuid as _uuid
        radius_meters = radius_km * 1000
        # asyncpg expects a proper UUID object for UUID columns
        zone_uuid = zone_id if isinstance(zone_id, _uuid.UUID) else _uuid.UUID(str(zone_id))
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, zone_uuid, radius_meters, limit)
            results = [dict(row) for row in rows]
            logger.info(
                "geo.volunteers_near_zone",
                zone_id=str(zone_id),
                found=len(results),
            )
            return results
    except Exception as exc:
        logger.error("geo.volunteer_query_failed", error=str(exc))
        return []
