"""
Backend Auto-Simulation Service.

Runs as a background asyncio task inside the FastAPI server.
Every 5 seconds it generates a randomised disaster detection event,
triggers the full agent pipeline (triage → dispatch → notifier → MQTT),
and updates the Supabase tables so the frontend dashboard refreshes
automatically via Realtime subscriptions.
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timezone

import structlog

from app.db import crud as db
from app.db.listener import _run_graph_for_zone
from app.mqtt.client import mqtt_manager

logger = structlog.get_logger(__name__)

# ── Configuration ──────────────────────────────
INTERVAL_SECONDS = 12

_running = False
_task: asyncio.Task | None = None


async def _simulation_tick() -> None:
    """Execute one simulation cycle."""

    # 1. Pick a random zone from the database
    try:
        from app.db.supabase_client import get_supabase
        from app.db.crud import _run_sync

        sb = get_supabase()
        result = await _run_sync(
            lambda: sb.table("zones").select("id").execute()
        )
        zone_ids = [z["id"] for z in (result.data or [])]
    except Exception:
        zone_ids = []

    if not zone_ids:
        logger.warning("simulation.no_zones")
        return

    zone_id = random.choice(zone_ids)

    # 2. Generate realistic disaster telemetry
    crowd = random.randint(20, 200)
    flood_level = round(random.uniform(0.1, 0.9), 2)
    structural_damage = round(random.uniform(0.05, 0.7), 2)
    fire = random.choice([True, False, False])  # ~33% chance
    confidence = round(random.uniform(0.80, 0.99), 2)
    vehicle_count = random.randint(2, 40)

    metadata = {
        "flood_level": flood_level,
        "structural_damage": structural_damage,
        "fire_detected": fire,
        "confidence": confidence,
        "vehicle_count": vehicle_count,
        "source": random.choice(["drone_camera", "cctv", "satellite", "mobile_report"]),
    }

    # 3. Persist detection to Supabase
    try:
        record = await db.insert_detection(
            zone_id=uuid.UUID(zone_id),
            count=crowd,
            metadata=metadata,
        )
    except Exception as exc:
        logger.warning("simulation.insert_failed", error=str(exc))
        return

    # 4. Trigger the full agent pipeline (triage → dispatch → notifier)
    normalized_crowd = min(1.0, crowd / 100.0)
    event_data = {
        "zone_id": zone_id,
        "detection": {
            "crowd_density": normalized_crowd,
            "flood_level": flood_level,
            "structural_damage": structural_damage,
            "fire_detected": fire,
            "confidence": confidence,
            "vehicle_count": vehicle_count,
        },
    }

    try:
        await _run_graph_for_zone(zone_id, event_data)
    except Exception as exc:
        logger.warning("simulation.agent_pipeline_error", error=str(exc))

    logger.info(
        "simulation.tick",
        zone_id=zone_id,
        crowd=crowd,
        flood=flood_level,
        fire=fire,
    )


async def _simulation_loop() -> None:
    """Main loop – runs forever until cancelled."""
    logger.info("simulation.started", interval=INTERVAL_SECONDS)
    while _running:
        try:
            await _simulation_tick()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("simulation.tick_error", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)
    logger.info("simulation.stopped")


def start_simulation() -> None:
    """Start the background simulation loop."""
    global _running, _task
    if _running:
        return
    _running = True
    _task = asyncio.create_task(_simulation_loop())


async def stop_simulation() -> None:
    """Gracefully stop the simulation loop."""
    global _running, _task
    _running = False
    if _task:
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):
            pass
        _task = None
