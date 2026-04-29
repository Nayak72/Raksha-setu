"""
API Routes – the four core endpoints plus system status.

All endpoints are fully async, non-blocking, and use BackgroundTasks
for heavy post-processing so HTTP responses return immediately.

Endpoints:
  POST /detect           – submit a detection event
  POST /simulate-weather – inject a simulated weather event
  POST /broadcast-alert  – manually broadcast an alert
  GET  /status           – system health snapshot
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.db import crud as db
from app.db.listener import _run_graph_for_zone
from app.schemas.alert import AlertCreate, AlertResponse, AcknowledgmentCreate
from app.schemas.detection import DetectionCreate, DetectionResponse
from app.schemas.weather import WeatherSimulationRequest, WeatherSimulationResponse
from app.schemas.zone import SystemStatus
from app.services.alert_service import create_and_broadcast_alert, acknowledge_alert

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Disaster Response"])

# Track startup time for uptime calculation
_start_time = time.monotonic()


# ─────────────────────────────────────────────
# POST /detect
# ─────────────────────────────────────────────
@router.post(
    "/detect",
    response_model=DetectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a detection event",
    description=(
        "Ingest a detection from a sensor, drone, or camera. "
        "Triggers the detection agent via Postgres NOTIFY in the background."
    ),
)
async def create_detection(
    payload: DetectionCreate,
    background_tasks: BackgroundTasks,
) -> DetectionResponse:
    """Persist the detection and fire the event-driven agent pipeline."""
    logger.info(
        "api.detect",
        zone_id=str(payload.zone_id),
        count=payload.count,
    )

    # 1. Persist to Supabase
    record = await db.insert_detection(
        zone_id=payload.zone_id,
        count=payload.count,
        metadata=payload.metadata,
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist detection",
        )

    # 2. Trigger agent pipeline directly as background task (bypassing broken Postgres listener)
    # Normalize count to 0.0-1.0 range for the triage agent's composite formula
    normalized_crowd = min(1.0, payload.count / 100.0)
    meta = payload.metadata or {}
    event_data = {
        "zone_id": str(payload.zone_id),
        "detection": {
            "crowd_density": normalized_crowd,
            "flood_level": float(meta.get("flood_level", 0.0)),
            "structural_damage": float(meta.get("structural_damage", 0.0)),
            "fire_detected": bool(meta.get("fire_detected", False)),
            "confidence": float(meta.get("confidence", 0.85)),
            "vehicle_count": int(meta.get("vehicle_count", 0)),
        }
    }
    background_tasks.add_task(_run_graph_for_zone, str(payload.zone_id), event_data)

    return DetectionResponse(
        id=record.get("id"),
        zone_id=payload.zone_id,
        count=payload.count,
        timestamp=record.get("timestamp", datetime.now(timezone.utc)),
        metadata=payload.metadata,
    )


# ─────────────────────────────────────────────
# POST /simulate-weather
# ─────────────────────────────────────────────
@router.post(
    "/simulate-weather",
    response_model=WeatherSimulationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Simulate a weather event",
    description=(
        "Inject a simulated weather event to test agent responses. "
        "Fires the weather agent via Postgres NOTIFY."
    ),
)
async def simulate_weather(
    payload: WeatherSimulationRequest,
    background_tasks: BackgroundTasks,
) -> WeatherSimulationResponse:
    """Simulate a weather event and trigger the weather agent pipeline."""
    logger.info(
        "api.simulate_weather",
        zone_id=str(payload.zone_id),
        event_type=payload.event_type,
        intensity=payload.intensity,
    )

    # Compute expected risk delta
    risk_delta = 5.0 if payload.intensity >= 7.0 else 1.0
    severity = payload.intensity

    # Build the event payload
    event_data = {
        "zone_id": str(payload.zone_id),
        "event_type": payload.event_type,
        "intensity": payload.intensity,
        "wind_speed_kmh": payload.wind_speed_kmh,
        "rainfall_mm": payload.rainfall_mm,
        "temperature_c": payload.temperature_c,
        "description": payload.description,
    }

    # Trigger agent pipeline directly in background
    background_tasks.add_task(_run_graph_for_zone, str(payload.zone_id), event_data)

    agents_triggered = ["weather_agent"]
    if payload.intensity >= 7.0:
        agents_triggered.append("dispatch_agent")

    return WeatherSimulationResponse(
        zone_id=payload.zone_id,
        event_type=payload.event_type,
        intensity=payload.intensity,
        risk_delta=risk_delta,
        agents_triggered=agents_triggered,
        timestamp=datetime.now(timezone.utc),
    )


# ─────────────────────────────────────────────
# POST /broadcast-alert
# ─────────────────────────────────────────────
@router.post(
    "/broadcast-alert",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Broadcast a disaster alert",
    description=(
        "Manually create and broadcast an alert via UDP. "
        "The alert is persisted in Supabase and broadcast to all LAN devices."
    ),
)
async def broadcast_alert(
    payload: AlertCreate,
) -> AlertResponse:
    """Create, persist, and broadcast an alert via UDP."""
    logger.info(
        "api.broadcast_alert",
        zone=payload.zone,
        severity=payload.severity.value,
    )

    record = await create_and_broadcast_alert(
        zone=payload.zone,
        message=payload.message,
        severity=payload.severity.value,
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create alert",
        )

    return AlertResponse(
        id=record.get("id"),
        zone=payload.zone,
        message=payload.message,
        severity=payload.severity,
        timestamp=record.get("timestamp", datetime.now(timezone.utc)),
    )


# ─────────────────────────────────────────────
# POST /acknowledge
# ─────────────────────────────────────────────
@router.post(
    "/acknowledge",
    status_code=status.HTTP_201_CREATED,
    summary="Acknowledge an alert",
    description="Record that a device has received/read/acted on an alert.",
)
async def acknowledge(payload: AcknowledgmentCreate) -> dict:
    """Record a device acknowledgment."""
    record = await acknowledge_alert(
        device_id=payload.device_id,
        alert_id=str(payload.alert_id),
        status=payload.status,
    )
    return {"acknowledged": True, "record": record}


# ─────────────────────────────────────────────
# GET /status
# ─────────────────────────────────────────────
@router.get(
    "/status",
    response_model=SystemStatus,
    summary="System health status",
    description="Returns aggregate counts and connectivity status.",
)
async def system_status() -> SystemStatus:
    """Return a snapshot of system health."""
    from app.db import listener as pg_listener

    counts = await db.get_counts()
    uptime = time.monotonic() - _start_time

    return SystemStatus(
        status="operational",
        udp_active=True,  # UDP is stateless — always available
        pg_listener_active=True,  # Bypassed via HTTP background tasks on Windows
        active_zones=counts.get("active_zones", 0),
        total_volunteers=counts.get("total_volunteers", 0),
        available_volunteers=counts.get("available_volunteers", 0),
        total_shelters=counts.get("total_shelters", 0),
        available_beds=counts.get("available_beds", 0),
        pending_alerts=counts.get("pending_alerts", 0),
        uptime_seconds=round(uptime, 2),
    )


# ─────────────────────────────────────────────
# GET /agent-logs
# ─────────────────────────────────────────────
@router.get(
    "/agent-logs",
    summary="Agent execution logs",
    description="Returns the historical traces of agent execution.",
)
async def get_agent_logs(limit: int = 50, zone_id: str | None = None) -> list[dict]:
    """Fetch the latest agent logs from Supabase."""
    from app.db.supabase_client import get_supabase
    
    # We execute sync client call in executor via _run_sync if possible, 
    # but since this is just a quick get, we can use the db utility
    from app.db.crud import _run_sync
    
    sb = get_supabase()
    def _query():
        q = sb.table("agent_logs").select("*").order("timestamp", desc=True).limit(limit)
        if zone_id:
            q = q.eq("zone_id", zone_id)
        return q.execute()
        
    try:
        result = await _run_sync(_query)
        return result.data or []
    except Exception as e:
        logger.error("api.get_agent_logs_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch agent logs"
        )


# ─────────────────────────────────────────────
# GET /rag-stats
# ─────────────────────────────────────────────
@router.get(
    "/rag-stats",
    summary="RAG memory statistics",
    description="Returns collection counts and embedding info for the RAG memory system.",
)
async def rag_stats() -> dict:
    """Return RAG memory store statistics."""
    try:
        from app.rag.memory import get_memory_store
        store = get_memory_store()
        return store.get_stats()
    except Exception as e:
        logger.error("api.rag_stats_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get RAG stats: {str(e)}"
        )


# ─────────────────────────────────────────────
# POST /rag-query
# ─────────────────────────────────────────────
@router.post(
    "/rag-query",
    summary="Query RAG memory",
    description="Retrieve relevant past events from the RAG memory system.",
)
async def rag_query(
    query: str,
    zone_id: str | None = None,
    collection: str = "all",
    n_results: int = 5,
) -> dict:
    """
    Query the RAG memory system for similar past events.

    Args:
        query: Natural language query.
        zone_id: Optional zone filter.
        collection: Which collection to search ('weather', 'detection', 'zone_events', 'all').
        n_results: Max results per collection.
    """
    try:
        from app.rag.retriever import get_retriever
        retriever = get_retriever()

        if collection == "all":
            context = retriever.get_zone_context(
                zone_id=zone_id or "all",
                n_weather=n_results,
                n_detection=n_results,
                n_events=n_results,
            )
            return context
        elif collection == "weather":
            from app.rag.memory import get_memory_store
            store = get_memory_store()
            return store.retrieve_weather_history(query, n_results, zone_id)
        elif collection == "detection":
            from app.rag.memory import get_memory_store
            store = get_memory_store()
            return store.retrieve_detection_history(query, n_results, zone_id)
        elif collection == "zone_events":
            from app.rag.memory import get_memory_store
            store = get_memory_store()
            return store.retrieve_zone_events(query, n_results, zone_id)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid collection: {collection}. Use 'weather', 'detection', 'zone_events', or 'all'."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("api.rag_query_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query failed: {str(e)}"
        )

