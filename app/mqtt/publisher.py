"""
High-level MQTT publish helpers.

Wraps `mqtt_manager.publish()` with domain-specific convenience functions.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.mqtt.client import mqtt_manager

logger = structlog.get_logger(__name__)


async def publish_alert(
    topic: str,
    payload: dict[str, Any],
    qos: int = 1,
) -> bool:
    """
    Publish a disaster alert to the MQTT broker.

    Args:
        topic:   e.g. "alerts/zone-1" or "alerts/broadcast"
        payload: Alert data dict (will be JSON-serialised)
        qos:     Quality of Service level (0, 1, or 2)

    Returns:
        True if the message was queued successfully.
    """
    logger.info("mqtt.publish_alert", topic=topic, severity=payload.get("severity"))
    return await mqtt_manager.publish(topic, payload, qos=qos)


async def publish_volunteer_dispatch(
    volunteer_id: str,
    zone_id: str,
    instructions: str,
    qos: int = 1,
) -> bool:
    """Notify a volunteer device of a new dispatch assignment."""
    topic = f"dispatch/volunteer/{volunteer_id}"
    payload = {
        "type": "dispatch",
        "volunteer_id": volunteer_id,
        "zone_id": zone_id,
        "instructions": instructions,
    }
    logger.info("mqtt.publish_dispatch", volunteer=volunteer_id, zone=zone_id)
    return await mqtt_manager.publish(topic, payload, qos=qos)


async def publish_shelter_update(
    shelter_id: str,
    available_beds: int,
    qos: int = 0,
) -> bool:
    """Broadcast updated shelter capacity."""
    topic = f"shelters/{shelter_id}/status"
    payload = {
        "type": "shelter_update",
        "shelter_id": shelter_id,
        "available_beds": available_beds,
    }
    return await mqtt_manager.publish(topic, payload, qos=qos)


async def publish_system_event(
    event_type: str,
    data: dict[str, Any],
    qos: int = 0,
) -> bool:
    """Publish a generic system event for monitoring."""
    topic = f"system/{event_type}"
    return await mqtt_manager.publish(topic, data, qos=qos)
