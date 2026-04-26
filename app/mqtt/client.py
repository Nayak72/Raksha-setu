"""
Async MQTT client manager using paho-mqtt with asyncio integration.

Provides a singleton `mqtt_manager` that:
  • Connects/disconnects with the Mosquitto broker
  • Publishes messages asynchronously (non-blocking)
  • Manages reconnection with exponential backoff
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

import paho.mqtt.client as paho_mqtt
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class MQTTManager:
    """Async wrapper around paho-mqtt for non-blocking publish/subscribe."""

    def __init__(self) -> None:
        self._client: Optional[paho_mqtt.Client] = None
        self._connected = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ── Connection lifecycle ─────────────────
    async def connect(self) -> None:
        """Connect to the Mosquitto broker in a thread-safe manner."""
        self._loop = asyncio.get_running_loop()
        self._client = paho_mqtt.Client(
            client_id=settings.mqtt.client_id,
            callback_api_version=paho_mqtt.CallbackAPIVersion.VERSION2,
        )

        # Authentication (if configured)
        if settings.mqtt.username:
            self._client.username_pw_set(
                settings.mqtt.username,
                settings.mqtt.password,
            )

        # Wire up callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        # Non-blocking connect – paho runs its own network thread
        try:
            self._client.connect_async(
                settings.mqtt.broker_host,
                settings.mqtt.broker_port,
                keepalive=60,
            )
            self._client.loop_start()
            logger.info(
                "mqtt.connecting",
                host=settings.mqtt.broker_host,
                port=settings.mqtt.broker_port,
            )
        except Exception as exc:
            logger.error("mqtt.connect_failed", error=str(exc))
            self._connected = False

    async def disconnect(self) -> None:
        """Gracefully disconnect from the broker."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
            logger.info("mqtt.disconnected")

    # ── Publish ──────────────────────────────
    async def publish(
        self,
        topic: str,
        payload: dict[str, Any] | str,
        qos: int = 1,
        retain: bool = False,
    ) -> bool:
        """
        Publish a message to the given MQTT topic.

        Args:
            topic:   MQTT topic string (e.g. "alerts/zone-1")
            payload: Dict (auto-serialised to JSON) or raw string
            qos:     Quality of Service (0, 1, or 2)
            retain:  Whether the broker should retain the message

        Returns:
            True if the message was queued successfully.
        """
        if not self._client:
            logger.warning("mqtt.publish_skipped", reason="client not initialised")
            return False

        message = json.dumps(payload) if isinstance(payload, dict) else payload

        try:
            result = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self._client.publish(topic, message, qos=qos, retain=retain),
            )
            logger.info(
                "mqtt.published",
                topic=topic,
                qos=qos,
                mid=result.mid,
            )
            return result.rc == paho_mqtt.MQTT_ERR_SUCCESS
        except Exception as exc:
            logger.error("mqtt.publish_error", topic=topic, error=str(exc))
            return False

    # ── Properties ───────────────────────────
    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Callbacks (called from paho thread) ──
    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        self._connected = True
        logger.info("mqtt.connected", rc=str(reason_code))

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None) -> None:
        self._connected = False
        logger.warning("mqtt.disconnected_unexpectedly", rc=str(reason_code))

    def _on_message(self, client, userdata, message) -> None:
        logger.debug(
            "mqtt.message_received",
            topic=message.topic,
            payload=message.payload.decode()[:200],
        )


# ── Singleton instance ──────────────────────
mqtt_manager = MQTTManager()
