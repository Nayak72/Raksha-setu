"""
RakshaSetu — Notifier Agent Tools
Tool functions for UDP broadcasting and ACK management.
"""

import json
from langchain_core.tools import tool
from app.network.udp_sender import send_udp_broadcast


@tool
def broadcast_alert(zone_id: str, message: str, severity: str = "medium") -> str:
    """
    Broadcast an alert message via UDP to all Android devices on the LAN.

    Args:
        zone_id: Zone identifier
        message: Alert message content
        severity: Alert severity (low, medium, high, critical)

    Returns:
        JSON with broadcast status.
    """
    payload = {
        "type": "ALERT",
        "zone": zone_id,
        "message": message,
        "severity": severity.upper(),
    }
    success = send_udp_broadcast(payload)
    return json.dumps({
        "zone": zone_id,
        "status": "sent" if success else "failed",
        "channel": "udp_broadcast",
        "severity": severity,
    })


@tool
def get_ack_status(alert_id: str) -> str:
    """
    Check the acknowledgement status of a specific alert from the simulation state.

    Args:
        alert_id: The alert ID to check.

    Returns:
        JSON with ACK status.
    """
    from app.services.state import state
    matching_acks = [a for a in state.broadcast_acks if a.get("alert_id") == alert_id]
    if matching_acks:
        return json.dumps({
            "alert_id": alert_id,
            "status": "acked",
            "ack_count": len(matching_acks),
            "devices": [a["device_id"] for a in matching_acks],
        })
    return json.dumps({
        "alert_id": alert_id,
        "status": "pending",
        "ack_count": 0,
    })


@tool
def retry_broadcast(alert_id: str) -> str:
    """
    Retry broadcasting an unacknowledged alert via UDP.

    Args:
        alert_id: The alert ID to retry.

    Returns:
        JSON with retry result.
    """
    from app.services.state import state

    # Find the original broadcast
    broadcast = next((b for b in state.broadcasts if b.get("id") == alert_id), None)
    if not broadcast:
        return json.dumps({"alert_id": alert_id, "result": "not_found"})

    # Check if already acknowledged
    acks = [a for a in state.broadcast_acks if a.get("alert_id") == alert_id]
    if acks:
        return json.dumps({"alert_id": alert_id, "result": "already_acked", "ack_count": len(acks)})

    # Retry the broadcast
    payload = {
        "type": "ALERT",
        "alert_id": alert_id,
        "zone": broadcast.get("zone_id", "unknown"),
        "severity": broadcast.get("severity", "medium").upper(),
        "message": broadcast.get("message", "Retry alert"),
    }
    success = send_udp_broadcast(payload)

    return json.dumps({
        "alert_id": alert_id,
        "result": "retry_sent" if success else "retry_failed",
    })


# Tool list for the Notifier Agent
NOTIFIER_TOOLS = [broadcast_alert, get_ack_status, retry_broadcast]
