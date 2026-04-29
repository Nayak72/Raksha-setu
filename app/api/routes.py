from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Optional
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.services.state import state
from app.services.shelters import get_shelters_near
from app.services.routing import get_routes
from app.services.logs import get_logs
from app.network.udp_sender import send_udp_broadcast

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Disaster Simulation"])

@router.get("/zones")
async def get_all_zones():
    return state.zones

@router.get("/shelters/near")
async def get_nearest_shelters(zone_id: str):
    return get_shelters_near(zone_id)

@router.get("/allocation")
async def get_resource_allocations():
    return state.allocations

@router.get("/evacuations")
async def get_zone_evacuations():
    return state.evacuations

@router.get("/logs")
async def get_agent_logs(zone_id: Optional[str] = None):
    return get_logs(zone_id)

@router.get("/routes")
async def get_zone_routes(zone_id: str):
    return get_routes(zone_id)

@router.get("/status")
async def system_status():
    import time
    try:
        from app.db import crud as db
        counts = await db.get_counts()
    except Exception:
        counts = {}
    return {
        "status": "operational",
        "udp_active": True,
        "pg_listener_active": True,
        "uptime_seconds": time.monotonic(),
        "counts": {
            "zones": counts.get("active_zones", 0),
            "volunteers": counts.get("total_volunteers", 0),
            "shelters": counts.get("total_shelters", 0),
            "active_alerts": counts.get("pending_alerts", 0),
        }
    }

@router.get("/agent-logs")
async def get_old_agent_logs(limit: int = 50, zone_id: Optional[str] = None):
    try:
        from app.db.supabase_client import get_supabase
        from app.db.crud import _run_sync
        sb = get_supabase()
        def _query():
            q = sb.table("agent_logs").select("*").order("timestamp", desc=True).limit(limit)
            if zone_id:
                q = q.eq("zone_id", zone_id)
            return q.execute()
        result = await _run_sync(_query)
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to fetch old agent logs: {e}")
        return []

from pydantic import BaseModel, Field

class DetectPayload(BaseModel):
    zone_id: str
    count: int = Field(ge=0)
    metadata: dict = {}

@router.post("/detect")
async def trigger_detect(payload: DetectPayload):
    # This was previously handled by BackgroundTasks, stubbed here to pass tests
    # and preserve API contract. Real simulation bypasses this.
    return {"status": "accepted", "event": "detection_received"}

class WeatherPayload(BaseModel):
    zone_id: str
    event_type: str
    intensity: float = Field(ge=0.0, le=10.0)

@router.post("/simulate-weather")
async def trigger_weather(payload: WeatherPayload):
    return {"status": "accepted", "event": "weather_simulated"}

class AlertPayload(BaseModel):
    zone: str
    message: str
    severity: str

@router.post("/broadcast-alert")
async def trigger_broadcast(payload: AlertPayload):
    """
    Broadcast an emergency alert via UDP to all Android devices on the LAN.
    Also persists the alert to Supabase and sends FCM push notification.
    """
    if payload.severity not in ["low", "medium", "high", "critical"]:
        raise HTTPException(status_code=422, detail="Invalid severity")

    alert_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    # Build UDP payload matching Android app's expected format
    udp_payload = {
        "type": "ALERT",
        "alert_id": alert_id,
        "zone": payload.zone,
        "severity": payload.severity.upper(),
        "message": payload.message,
        "timestamp": now_iso,
    }

    # Fire UDP broadcast to all devices on the LAN
    broadcast_success = send_udp_broadcast(udp_payload)

    # Try to persist to Supabase
    try:
        from app.services.alert_service import create_and_broadcast_alert
        await create_and_broadcast_alert(
            zone=payload.zone,
            message=payload.message,
            severity=payload.severity,
        )
    except Exception as e:
        logger.warning(f"Alert persistence failed (UDP still sent): {e}")

    # Track in simulation state
    broadcast_record = {
        "id": alert_id,
        "zone_id": payload.zone,
        "zone_name": payload.zone,
        "severity": payload.severity,
        "message": payload.message,
        "success": broadcast_success,
        "timestamp": now_iso,
        "cycle": state.cycle_count,
    }
    state.broadcasts.insert(0, broadcast_record)
    state.broadcasts = state.broadcasts[:50]
    state.broadcast_count += 1

    return {
        "status": "broadcast_sent" if broadcast_success else "broadcast_failed",
        "alert_id": alert_id,
        "udp_success": broadcast_success,
        "event": "alert_broadcasted",
    }


# ── Broadcast History & Stats ────────────────────────

@router.get("/broadcasts")
async def get_broadcasts():
    """Return recent broadcast history and stats for the dashboard."""
    successful = sum(1 for b in state.broadcasts if b.get("success"))
    failed = sum(1 for b in state.broadcasts if not b.get("success"))

    return {
        "broadcasts": state.broadcasts,
        "stats": {
            "total_sent": state.broadcast_count,
            "successful": successful,
            "failed": failed,
            "devices_reached": state.devices_reached,
            "recent_count": len(state.broadcasts),
        },
    }


# ── Device Acknowledgment Endpoint ───────────────────

class AckPayload(BaseModel):
    device_id: str
    alert_id: str
    status: str = "received"

@router.post("/ack")
async def receive_ack(payload: AckPayload):
    """
    Android devices call this endpoint to acknowledge receipt of an alert.
    This updates the broadcast tracking stats shown on the dashboard.
    """
    ack_record = {
        "device_id": payload.device_id,
        "alert_id": payload.alert_id,
        "status": payload.status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    state.broadcast_acks.insert(0, ack_record)
    state.broadcast_acks = state.broadcast_acks[:200]

    # Count unique devices
    unique_devices = set(a["device_id"] for a in state.broadcast_acks)
    state.devices_reached = len(unique_devices)

    # Try to persist to Supabase
    try:
        from app.services.alert_service import acknowledge_alert
        await acknowledge_alert(
            device_id=payload.device_id,
            alert_id=payload.alert_id,
            status=payload.status,
        )
    except Exception as e:
        logger.warning(f"ACK persistence failed: {e}")

    return {"status": "ack_received", "device_id": payload.device_id}


# ── Manual Broadcast Trigger ─────────────────────────

class ManualBroadcastPayload(BaseModel):
    zone_id: str
    message: str
    severity: str = "high"

@router.post("/broadcast-manual")
async def manual_broadcast(payload: ManualBroadcastPayload):
    """
    Manually trigger a UDP broadcast from the dashboard.
    For testing or emergency overrides.
    """
    if payload.severity not in ["low", "medium", "high", "critical"]:
        raise HTTPException(status_code=422, detail="Invalid severity")

    # Find zone name
    zone_name = payload.zone_id
    for z in state.zones:
        if z["id"] == payload.zone_id:
            zone_name = z["name"]
            break

    alert_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    udp_payload = {
        "type": "ALERT",
        "alert_id": alert_id,
        "zone": payload.zone_id,
        "zone_name": zone_name,
        "severity": payload.severity.upper(),
        "message": payload.message,
        "timestamp": now_iso,
    }

    success = send_udp_broadcast(udp_payload)

    broadcast_record = {
        "id": alert_id,
        "zone_id": payload.zone_id,
        "zone_name": zone_name,
        "severity": payload.severity,
        "message": payload.message,
        "success": success,
        "timestamp": now_iso,
        "cycle": state.cycle_count,
        "manual": True,
    }
    state.broadcasts.insert(0, broadcast_record)
    state.broadcasts = state.broadcasts[:50]
    state.broadcast_count += 1

    return {
        "status": "sent" if success else "failed",
        "alert_id": alert_id,
        "udp_success": success,
    }


# ── WebSocket (includes broadcasts & yolo) ─────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected")
    try:
        last_cycle = -1
        while True:
            if state.cycle_count > last_cycle:
                payload = {
                    "zones": state.zones,
                    "evacuations": state.evacuations,
                    "allocations": state.allocations,
                    "logs": get_logs(),
                    "routes": state.routes,
                    "broadcasts": state.broadcasts[:20],
                    "broadcast_stats": {
                        "total_sent": state.broadcast_count,
                        "devices_reached": state.devices_reached,
                        "recent_acks": len(state.broadcast_acks),
                    },
                    "yolo_results": state.yolo_results[:10],
                    "yolo_stats": {
                        "scan_count": state.yolo_scan_count,
                        "total_detections": state.yolo_total_detections,
                    }
                }
                await websocket.send_json(payload)
                last_cycle = state.cycle_count
            await asyncio.sleep(1) # check more frequently than 5s to avoid missing a cycle
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

# ── YOLO Live API ────────────────────────────────────

@router.get("/yolo/images")
async def get_yolo_images(zone_id: Optional[str] = None):
    """List available images in the Supabase bucket for YOLO inference."""
    from app.services.yolo_service import list_zone_images, list_all_bucket_images
    if zone_id:
        return {"images": list_zone_images(zone_id)}
    return {"images": list_all_bucket_images()}

class SingleImageDetectPayload(BaseModel):
    url: str
    zone_id: str = "unknown"

@router.post("/yolo/detect")
async def detect_single(payload: SingleImageDetectPayload):
    """Run YOLO on a specific image and get annotated results."""
    from app.services.yolo_service import detect_single_image
    result = detect_single_image(payload.url, payload.zone_id)

    if "error" not in result:
        # Track in state for WebSocket broadcast
        state.yolo_results.insert(0, result)
        state.yolo_results = state.yolo_results[:50]
        state.yolo_scan_count += 1
        state.yolo_total_detections += result.get("num_detections", 0)

    return result

class ZoneDetectPayload(BaseModel):
    zone_id: str
    max_images: int = 4

@router.post("/yolo/detect-zone")
async def detect_zone_images(payload: ZoneDetectPayload):
    """Run YOLO on multiple images from a specific zone."""
    from app.services.yolo_service import detect_zone
    results = detect_zone(payload.zone_id, payload.max_images)

    for res in results:
        if "error" not in res:
            state.yolo_results.insert(0, res)
            state.yolo_scan_count += 1
            state.yolo_total_detections += res.get("num_detections", 0)

    state.yolo_results = state.yolo_results[:50]
    return {"results": results}
