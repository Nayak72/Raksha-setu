"""
Postgres LISTEN/NOTIFY event listener.

Subscribes to channels and dispatches events to the agent system.
This is the core of the event-driven architecture – no polling.

Channels:
  • new_detection  – fired by a trigger on INSERT into detections
  • weather_update – fired by application code on weather simulation
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional, Dict

import asyncpg
import structlog

from app.db.supabase_client import get_pg_pool
from app.graph.workflow import compile_workflow
from app.shared.tools import generate_mock_detection
from app.services.yolo_service import analyze_zone_images

logger = structlog.get_logger(__name__)

_listener_connection: Optional[asyncpg.Connection] = None
_running = False

# Idempotency locks per zone
_zone_locks: Dict[str, asyncio.Lock] = {}

# Compile workflow once
_app = compile_workflow()

def _get_detection_data(zone_id: str) -> dict:
    """Try YOLO detection from Supabase bucket images, fall back to mock."""
    try:
        return analyze_zone_images(zone_id, max_images=3)
    except Exception as e:
        logger.warning("yolo.fallback_to_mock", zone=zone_id, error=str(e))
        return generate_mock_detection(zone_id)


async def _run_graph_for_zone(zone_id: str, trigger_event: dict):
    """Run the LangGraph workflow idempotently for a zone."""
    if zone_id not in _zone_locks:
        _zone_locks[zone_id] = asyncio.Lock()
        
    if _zone_locks[zone_id].locked():
        logger.info("graph.skipped", zone=zone_id, reason="already running")
        return

    async with _zone_locks[zone_id]:
        logger.info("graph.started", zone=zone_id)
        
        # Initial state setup
        initial_state = {
            "zone_id": zone_id,
            "detection_data": trigger_event.get("detection") or _get_detection_data(zone_id),
            "triage_result": None,
            "weather_data": None,
            "zone_analysis": None,
            "resource_plan": None,
            "notification_result": None,
            "feedback": None,
            "supervisor_decision": None,
            "feedback_loop_count": 0,
            "should_retrigger": False,
            "supervisor_interventions": 0,
            "weather_recheck_count": 0,
            "notification_retry_count": 0,
            "execution_trace": [],
            "routing_history": [],
            "messages": [],
        }

        # Proactively ingest detection data into RAG memory
        try:
            from app.rag.memory import get_memory_store
            detection = initial_state.get("detection_data", {})
            if detection:
                rag_store = get_memory_store()
                rag_store.ingest_detection_event(detection)
                logger.info("rag.detection_ingested", zone=zone_id)
        except Exception as e:
            logger.warning("rag.detection_ingest_failed", zone=zone_id, error=str(e))

        try:
            # Run graph asynchronously
            # Run in executor since app.invoke is sync (or we could use ainvoke if LangGraph is async)
            # We use ainvoke
            final_state = await _app.ainvoke(initial_state, config={"recursion_limit": 100})
            logger.info("graph.completed", zone=zone_id, trace_len=len(final_state.get("execution_trace", [])))
            
            # Persist execution log
            await _persist_execution_log(zone_id, final_state)
            
        except Exception as e:
            logger.error(f"graph.failed", zone=zone_id, error=str(e), exc_info=True)


async def _persist_execution_log(zone_id: str, state: dict):
    from app.db.supabase_client import get_supabase
    sb = get_supabase()
    
    # Store the trace into a new agent_logs table
    trace = state.get("execution_trace", [])
    if not trace:
        return
        
    node_to_state_key = {
        "weather_simulation": "weather_data",
        "zone_analyst": "zone_analysis",
        "resource_allocator": "resource_plan",
        "notifier": "notification_result",
        "feedback": "feedback",
        "supervisor": "supervisor_decision",
        "triage": "triage_result"
    }

    try:
        logs = []
        for entry in trace:
            node = entry.get("node")
            if node == "log_and_end":
                continue
                
            state_key = node_to_state_key.get(node)
            agent_data = state.get(state_key, {}) if state_key else {}
            
            logs.append({
                "zone_id": zone_id,
                "agent_name": node,
                "decision": entry.get("decision", ""),
                "reasoning_steps": agent_data.get("reasoning_steps", []),
                "tools_used": agent_data.get("tools_used", []),
                "confidence": entry.get("confidence", 0.0),
                "routing_decision": entry.get("routed_to", ""),
                "metadata": entry.get("state_snapshot", {})
            })
            
        if logs:
            sb.table("agent_logs").insert(logs).execute()
    except Exception as e:
        logger.error("persist_log_failed", error=str(e))


async def _dispatch_event(channel: str, payload: str) -> None:
    """Route an incoming Postgres notification to the correct agent."""
    logger.info("pg_notify.received", channel=channel, payload=payload[:200])

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        logger.error("pg_notify.invalid_json", payload=payload[:200])
        return

    zone_id = data.get("zone_id")
    if not zone_id:
        logger.warning("pg_notify.missing_zone_id", channel=channel)
        return

    # Trigger graph asynchronously
    asyncio.create_task(_run_graph_for_zone(zone_id, data))


async def start_pg_listener() -> None:
    global _listener_connection, _running

    try:
        pool = await get_pg_pool()
    except (OSError, Exception) as exc:
        logger.debug("pg_listener.connect_failed", error=str(exc),
                        hint="PG listener disabled — API still works fine")
        _running = False
        return

    _listener_connection = await pool.acquire()
    _running = True

    await _listener_connection.add_listener("new_detection", _on_notification)
    await _listener_connection.add_listener("weather_update", _on_notification)

    logger.info("pg_listener.subscribed", channels=["new_detection", "weather_update"])

    try:
        while _running:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("pg_listener.cancelled")
    finally:
        if _listener_connection:
            try:
                await _listener_connection.remove_listener("new_detection", _on_notification)
                await _listener_connection.remove_listener("weather_update", _on_notification)
                pool = await get_pg_pool()
                await pool.release(_listener_connection)
            except Exception:
                pass
            _listener_connection = None


def _on_notification(connection: asyncpg.Connection, pid: int, channel: str, payload: str) -> None:
    asyncio.create_task(_dispatch_event(channel, payload))


_ALLOWED_CHANNELS = {"new_detection", "weather_update"}

async def notify(channel: str, payload: dict) -> None:
    if channel not in _ALLOWED_CHANNELS:
        raise ValueError(f"Channel '{channel}' is not in the allowed list: {_ALLOWED_CHANNELS}")

    pool = await get_pg_pool()
    payload_json = json.dumps(payload)
    escaped = payload_json.replace("'", "''")
    async with pool.acquire() as conn:
        await conn.execute(f"NOTIFY {channel}, '{escaped}'")
    logger.info("pg_notify.sent", channel=channel)


async def stop_pg_listener() -> None:
    global _running
    _running = False
    logger.info("pg_listener.stopping_signal_sent")
