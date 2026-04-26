"""
RakshaSetu — Notifier Agent Tools
Tool functions for MQTT broadcasting and ACK management.
"""

import json
from langchain_core.tools import tool
from app.agents.notifier.mqtt_client import MQTTPublisher
from app.agents.notifier.ack_manager import ACKManager

# Lazy-initialized instances
_publisher = None
_ack_manager = None


def _get_publisher():
    global _publisher
    if _publisher is None:
        _publisher = MQTTPublisher()
    return _publisher


def _get_ack_manager():
    global _ack_manager
    if _ack_manager is None:
        _ack_manager = ACKManager()
    return _ack_manager


@tool
def broadcast_alert(topic: str, message: str, qos: int = 0) -> str:
    """
    Broadcast an alert message via MQTT.

    Args:
        topic: MQTT topic (e.g., 'alerts/zone/zone_001', 'alerts/global')
        message: Alert message (JSON string)
        qos: Quality of Service level (0, 1, or 2)

    Returns:
        JSON with publication status.
    """
    publisher = _get_publisher()
    success = publisher.publish(topic, message, qos=qos)
    return json.dumps({
        "topic": topic,
        "status": "sent" if success else "failed",
        "qos": qos,
    })


@tool
def get_ack_status(alert_id: str) -> str:
    """
    Check the acknowledgement status of a specific alert.

    Args:
        alert_id: The alert ID to check.

    Returns:
        JSON with ACK status (acked, pending, or unknown).
    """
    ack_manager = _get_ack_manager()
    status = ack_manager.get_status(alert_id)
    return json.dumps(status)


@tool
def retry_broadcast(alert_id: str) -> str:
    """
    Manually retry broadcasting an unacknowledged alert.

    Args:
        alert_id: The alert ID to retry.

    Returns:
        JSON with retry result.
    """
    ack_manager = _get_ack_manager()
    status = ack_manager.get_status(alert_id)

    if status["status"] == "acked":
        return json.dumps({"alert_id": alert_id, "result": "already_acked"})

    if status["status"] == "pending":
        # In production, would re-publish the original message
        return json.dumps({
            "alert_id": alert_id,
            "result": "retry_scheduled",
            "retries_so_far": status.get("retries", 0),
        })

    return json.dumps({"alert_id": alert_id, "result": "not_found"})


# Tool list for the Notifier Agent
NOTIFIER_TOOLS = [broadcast_alert, get_ack_status, retry_broadcast]
