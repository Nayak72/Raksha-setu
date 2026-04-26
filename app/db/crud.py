"""
Async CRUD helpers that wrap the Supabase PostgREST client.

Every function is non-blocking and returns typed dicts / lists.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import partial
from typing import Any, Optional
from uuid import UUID

import structlog

from app.db.supabase_client import get_supabase

logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────
# Utility: run sync Supabase calls in a thread
# ─────────────────────────────────────────────
async def _run_sync(func, *args, **kwargs) -> Any:
    """Execute a synchronous supabase-py call without blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


# ─────────────────────────────────────────────
# Zones
# ─────────────────────────────────────────────
async def insert_zone(lat: float, lon: float, risk_score: float = 0.0) -> dict:
    sb = get_supabase()
    row = {"lat": lat, "lon": lon, "risk_score": risk_score}
    result = await _run_sync(
        lambda r=row: sb.table("zones").insert(r).execute()
    )
    logger.info("db.zone_inserted", lat=lat, lon=lon)
    return result.data[0] if result.data else {}


async def get_zone(zone_id: str | UUID) -> Optional[dict]:
    sb = get_supabase()
    zid = str(zone_id)
    try:
        result = await _run_sync(
            lambda z=zid: sb.table("zones").select("*").eq("id", z).single().execute()
        )
        return result.data
    except Exception:
        # .single() raises when zero or multiple rows are returned
        logger.warning("db.get_zone_failed", zone_id=zid)
        return None


async def update_zone_risk(zone_id: str | UUID, risk_score: float) -> dict:
    sb = get_supabase()
    zid = str(zone_id)
    payload = {"risk_score": risk_score}
    result = await _run_sync(
        lambda p=payload, z=zid: sb.table("zones").update(p).eq("id", z).execute()
    )
    logger.info("db.zone_risk_updated", zone_id=zid, risk=risk_score)
    return result.data[0] if result.data else {}


async def list_zones() -> list[dict]:
    sb = get_supabase()
    result = await _run_sync(
        lambda: sb.table("zones").select("*").order("risk_score", desc=True).execute()
    )
    return result.data or []


# ─────────────────────────────────────────────
# Detections
# ─────────────────────────────────────────────
async def insert_detection(zone_id: UUID, count: int, metadata: Optional[dict] = None) -> dict:
    sb = get_supabase()
    payload: dict[str, Any] = {
        "zone_id": str(zone_id),
        "count": count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if metadata:
        payload["metadata"] = metadata
    result = await _run_sync(
        lambda p=payload: sb.table("detections").insert(p).execute()
    )
    logger.info("db.detection_inserted", zone_id=str(zone_id), count=count)
    return result.data[0] if result.data else {}


async def list_detections(zone_id: Optional[UUID] = None, limit: int = 50) -> list[dict]:
    sb = get_supabase()
    def _query():
        q = sb.table("detections").select("*").order("timestamp", desc=True).limit(limit)
        if zone_id:
            q = q.eq("zone_id", str(zone_id))
        return q.execute()
    result = await _run_sync(_query)
    return result.data or []


# ─────────────────────────────────────────────
# Alerts
# ─────────────────────────────────────────────
async def insert_alert(zone: str, message: str, severity: str) -> dict:
    sb = get_supabase()
    payload = {
        "zone": zone,
        "message": message,
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    result = await _run_sync(
        lambda p=payload: sb.table("alerts").insert(p).execute()
    )
    logger.info("db.alert_inserted", zone=zone, severity=severity)
    return result.data[0] if result.data else {}


async def list_alerts(limit: int = 50) -> list[dict]:
    sb = get_supabase()
    result = await _run_sync(
        lambda: sb.table("alerts").select("*").order("timestamp", desc=True).limit(limit).execute()
    )
    return result.data or []


# ─────────────────────────────────────────────
# Acknowledgments
# ─────────────────────────────────────────────
async def insert_acknowledgment(device_id: str, alert_id: str | UUID, status: str = "received") -> dict:
    sb = get_supabase()
    payload = {
        "device_id": device_id,
        "alert_id": str(alert_id),
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    result = await _run_sync(
        lambda p=payload: sb.table("acknowledgments").insert(p).execute()
    )
    logger.info("db.ack_inserted", device_id=device_id, alert_id=str(alert_id))
    return result.data[0] if result.data else {}


# ─────────────────────────────────────────────
# Volunteers
# ─────────────────────────────────────────────
async def list_available_volunteers(limit: int = 20) -> list[dict]:
    sb = get_supabase()
    result = await _run_sync(
        lambda: sb.table("volunteers")
        .select("*")
        .eq("status", "available")
        .order("skill_level", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


async def update_volunteer_status(volunteer_id: str | UUID, status: str) -> dict:
    sb = get_supabase()
    payload: dict[str, Any] = {"status": status}
    if status == "dispatched":
        payload["last_assigned_at"] = datetime.now(timezone.utc).isoformat()
    vid = str(volunteer_id)
    result = await _run_sync(
        lambda p=payload, v=vid: sb.table("volunteers").update(p).eq("id", v).execute()
    )
    logger.info("db.volunteer_updated", id=vid, status=status)
    return result.data[0] if result.data else {}


# ─────────────────────────────────────────────
# Shelters
# ─────────────────────────────────────────────
async def list_shelters_with_beds(min_beds: int = 1) -> list[dict]:
    sb = get_supabase()
    result = await _run_sync(
        lambda: sb.table("shelters")
        .select("*")
        .gte("available_beds", min_beds)
        .order("available_beds", desc=True)
        .execute()
    )
    return result.data or []


async def decrement_shelter_beds(shelter_id: UUID, count: int = 1) -> dict:
    """Atomically decrement available_beds via an RPC call."""
    sb = get_supabase()
    params = {"p_shelter_id": str(shelter_id), "p_count": count}
    result = await _run_sync(
        lambda p=params: sb.rpc("decrement_beds", p).execute()
    )
    logger.info("db.shelter_beds_decremented", id=str(shelter_id), by=count)
    return result.data if result.data else {}


# ─────────────────────────────────────────────
# Aggregate counts (for /status)
# ─────────────────────────────────────────────
async def get_counts() -> dict:
    """Fetch aggregate counts for the system status endpoint."""
    sb = get_supabase()

    try:
        zones, volunteers, shelters, alerts = await asyncio.gather(
            _run_sync(lambda: sb.table("zones").select("*", count="exact").execute()),
            _run_sync(lambda: sb.table("volunteers").select("*", count="exact").execute()),
            _run_sync(lambda: sb.table("shelters").select("*", count="exact").execute()),
            _run_sync(lambda: sb.table("alerts").select("*", count="exact").execute()),
        )

        available_vols = [v for v in (volunteers.data or []) if v.get("status") == "available"]
        total_beds = sum(s.get("available_beds", 0) for s in (shelters.data or []))

        return {
            "active_zones": (zones.count if zones.count is not None else len(zones.data or [])),
            "total_volunteers": (volunteers.count if volunteers.count is not None else len(volunteers.data or [])),
            "available_volunteers": len(available_vols),
            "total_shelters": (shelters.count if shelters.count is not None else len(shelters.data or [])),
            "available_beds": total_beds,
            "pending_alerts": (alerts.count if alerts.count is not None else len(alerts.data or [])),
        }
    except Exception as exc:
        logger.warning("db.get_counts_failed", error=str(exc))
        return {
            "active_zones": 0,
            "total_volunteers": 0,
            "available_volunteers": 0,
            "total_shelters": 0,
            "available_beds": 0,
            "pending_alerts": 0,
        }
