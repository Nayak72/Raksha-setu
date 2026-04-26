"""
Alert Service – orchestrates alert creation, persistence, and MQTT broadcast.

Single entry point: `create_and_broadcast_alert()`
"""

from __future__ import annotations

from typing import Any

import structlog

from app.db import crud as db
from app.mqtt.publisher import publish_alert

logger = structlog.get_logger(__name__)


async def create_and_broadcast_alert(
    zone: str,
    message: str,
    severity: str = "medium",
    mqtt_topic: str | None = None,
    qos: int = 1,
) -> dict[str, Any]:
    """
    1. Persist the alert in Supabase
    2. Broadcast via MQTT to the appropriate topic

    Args:
        zone:       Zone identifier
        message:    Human-readable alert message
        severity:   low | medium | high | critical
        mqtt_topic: Override topic (defaults to "alerts/{zone}")
        qos:        MQTT QoS level

    Returns:
        The persisted alert record.
    """
    # 1. Persist
    alert_record = await db.insert_alert(
        zone=zone,
        message=message,
        severity=severity,
    )

    # 2. Build MQTT payload
    topic = mqtt_topic or f"alerts/{zone}"
    payload = {
        "alert_id": alert_record.get("id", "unknown"),
        "zone": zone,
        "message": message,
        "severity": severity,
        "timestamp": alert_record.get("timestamp", ""),
    }

    # 3. Broadcast
    success = await publish_alert(topic=topic, payload=payload, qos=qos)

    if success:
        logger.info("alert_service.broadcast_success", zone=zone, severity=severity)
    else:
        logger.warning("alert_service.broadcast_failed", zone=zone, topic=topic)

    return alert_record


async def acknowledge_alert(
    device_id: str,
    alert_id: str,
    status: str = "received",
) -> dict[str, Any]:
    """Record a device's acknowledgment of an alert."""
    ack = await db.insert_acknowledgment(
        device_id=device_id,
        alert_id=alert_id,
        status=status,
    )
    logger.info(
        "alert_service.acknowledged",
        device_id=device_id,
        alert_id=alert_id,
        status=status,
    )
    return ack
