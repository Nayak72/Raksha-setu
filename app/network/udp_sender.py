"""
RakshaSetu — UDP Broadcast Sender

Replaces MQTT with direct UDP broadcast for offline, LAN-based alert delivery.
All connected Android devices on the same WiFi/hotspot will receive alerts instantly.

Usage:
    from app.network.udp_sender import send_udp_broadcast
    send_udp_broadcast(alert_payload_dict)
"""

import json
import logging
import socket
from typing import Any

logger = logging.getLogger(__name__)

# Default UDP broadcast configuration
UDP_BROADCAST_IP = "<broadcast>"
UDP_BROADCAST_PORT = 5005


def _get_local_ip() -> str:
    """Detect the local IP address of the server (hotspot host)."""
    try:
        # Create a dummy socket to determine the outbound IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def send_udp_broadcast(
    payload: dict[str, Any],
    port: int = UDP_BROADCAST_PORT,
    broadcast_ip: str = UDP_BROADCAST_IP,
) -> bool:
    """
    Broadcast a JSON-encoded alert payload via UDP to all devices on the LAN.

    The server_ip is injected automatically so Android devices know where
    to send HTTP ACK requests without manual configuration.

    Args:
        payload:      Alert data dict (will be JSON-serialised).
        port:         UDP port to broadcast on (default: 5005).
        broadcast_ip: Broadcast address (default: 255.255.255.255).

    Returns:
        True if the broadcast was sent successfully.
    """
    sock = None
    try:
        # Inject server IP so the Android app knows the ACK endpoint
        local_ip = _get_local_ip()
        payload["server_ip"] = local_ip

        message = json.dumps(payload).encode("utf-8")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind((local_ip, 0)) # Ensure Windows routes broadcast out the correct interface
        sock.sendto(message, ("255.255.255.255", port))

        logger.info(
            f"UDP broadcast sent to {broadcast_ip}:{port} "
            f"({len(message)} bytes, alert_id={payload.get('alert_id', 'N/A')})"
        )
        return True

    except Exception as e:
        logger.error(f"UDP broadcast failed: {e}")
        return False

    finally:
        if sock:
            sock.close()


async def send_udp_broadcast_async(
    payload: dict[str, Any],
    port: int = UDP_BROADCAST_PORT,
    broadcast_ip: str = UDP_BROADCAST_IP,
) -> bool:
    """
    Async wrapper around send_udp_broadcast for use in async contexts.
    Runs the blocking socket call in an executor.
    """
    import asyncio

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, lambda: send_udp_broadcast(payload, port, broadcast_ip)
    )
