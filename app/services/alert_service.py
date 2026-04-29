"""
Alert Service – orchestrates alert creation, persistence, and UDP broadcast.

Single entry point: `create_and_broadcast_alert()`
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from app.db import crud as db
from app.network.udp_sender import send_udp_broadcast_async
from app.network.fcm_sender import send_fcm_alert_async

logger = structlog.get_logger(__name__)


async def create_and_broadcast_alert(
    zone: str,
    message: str,
    severity: str = "medium",
    **kwargs,
) -> dict[str, Any]:
    """
    1. Persist the alert in Supabase
    2. Broadcast via UDP to all devices on the LAN
    3. Send FCM push notification for closed apps

    Args:
        zone:       Zone identifier
        message:    Human-readable alert message
        severity:   low | medium | high | critical

    Returns:
        The persisted alert record.
    """
    # 1. Persist
    alert_record = await db.insert_alert(
        zone=zone,
        message=message,
        severity=severity,
    )

    # 2. Build UDP payload (mandatory format)
    alert_id = str(alert_record.get("id", uuid.uuid4()))
    payload = {
        "type": "ALERT",
        "alert_id": alert_id,
        "zone": zone,
        "severity": severity.upper(),
        "message": message,
        "timestamp": alert_record.get(
            "timestamp", datetime.now(timezone.utc).isoformat()
        ),
    }

    # 3. Broadcast via UDP
    success = await send_udp_broadcast_async(payload)

    # 4. Broadcast via FCM (Push Notification for closed apps)
    fcm_success = await send_fcm_alert_async(payload)

    if success or fcm_success:
        logger.info("alert_service.broadcast_success", zone=zone, severity=severity)
    else:
        logger.warning("alert_service.broadcast_failed", zone=zone)

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
