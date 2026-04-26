"""
RakshaSetu — MQTT Client Module
Paho-MQTT publisher and subscriber for Mosquitto broker.
Designed for offline operation on laptop hotspot.
"""

import logging
import time
from typing import Callable

import paho.mqtt.client as mqtt
from app.config import settings

logger = logging.getLogger(__name__)


class MQTTPublisher:
    """
    MQTT Publisher for broadcasting disaster alerts.
    Connects to a Mosquitto broker (local or network).
    """

    def __init__(self):
        self.broker_host = settings.mqtt.broker_host
        self.broker_port = settings.mqtt.broker_port
        self.client_id = "raksha_setu_publisher"
        self.client = mqtt.Client(
            client_id=self.client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self._connected = False

        # Set credentials if provided
        if settings.mqtt.username:
            self.client.username_pw_set(settings.mqtt.username, settings.mqtt.password)

        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish

        # Attempt connection
        self._connect()

    def _connect(self):
        """Connect to the MQTT broker with retry logic."""
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                self.client.connect(self.broker_host, self.broker_port, keepalive=60)
                self.client.loop_start()
                time.sleep(1)  # Wait for connection
                if self._connected:
                    logger.info(f"MQTT Publisher connected to {self.broker_host}:{self.broker_port}")
                    return
            except Exception as e:
                logger.warning(f"MQTT connection attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(2)

        logger.error("MQTT Publisher failed to connect. Alerts will be logged only.")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self._connected = True
            logger.info("MQTT: Connected successfully")
        else:
            logger.error(f"MQTT: Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        self._connected = False
        logger.warning(f"MQTT: Disconnected (rc={rc})")

    def _on_publish(self, client, userdata, mid, rc=None, properties=None):
        logger.debug(f"MQTT: Message {mid} published")

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> bool:
        """
        Publish a message to an MQTT topic.

        Args:
            topic: MQTT topic (e.g., "alerts/zone/zone_001")
            payload: JSON string payload
            qos: Quality of Service (0, 1, or 2)
            retain: Whether to retain the message

        Returns:
            True if published successfully
        """
        if not self._connected:
            logger.warning(f"MQTT not connected. Logging alert: topic={topic}, payload={payload[:100]}")
            return False

        try:
            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            result.wait_for_publish(timeout=5)
            logger.info(f"MQTT published: topic={topic}, qos={qos}")
            return True
        except Exception as e:
            logger.error(f"MQTT publish failed: {e}")
            return False

    def disconnect(self):
        """Gracefully disconnect from the broker."""
        self.client.loop_stop()
        self.client.disconnect()
        self._connected = False
        logger.info("MQTT Publisher disconnected.")


class MQTTSubscriber:
    """
    MQTT Subscriber for listening to ACK messages and other topics.
    """

    def __init__(self, client_id: str = "raksha_setu_subscriber"):
        self.broker_host = settings.mqtt.broker_host
        self.broker_port = settings.mqtt.broker_port
        self.client = mqtt.Client(
            client_id=client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self._callbacks: dict[str, Callable] = {}
        self._connected = False

        if settings.mqtt.username:
            self.client.username_pw_set(settings.mqtt.username, settings.mqtt.password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self._connected = True
            logger.info("MQTT Subscriber connected.")
            # Re-subscribe to all registered topics
            for topic in self._callbacks:
                self.client.subscribe(topic)
        else:
            logger.error(f"MQTT Subscriber connection failed: rc={rc}")

    def _on_message(self, client, userdata, msg):
        """Route incoming messages to registered callbacks."""
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        logger.debug(f"MQTT received: topic={topic}")

        # Check for exact topic match
        if topic in self._callbacks:
            self._callbacks[topic](topic, payload)
        else:
            # Check wildcard matches
            for pattern, callback in self._callbacks.items():
                if mqtt.topic_matches_sub(pattern, topic):
                    callback(topic, payload)
                    break

    def subscribe(self, topic: str, callback: Callable[[str, str], None]):
        """
        Subscribe to a topic with a callback function.

        Args:
            topic: MQTT topic pattern (supports wildcards: +, #)
            callback: Function(topic, payload) called on message receipt
        """
        self._callbacks[topic] = callback
        if self._connected:
            self.client.subscribe(topic)
        logger.info(f"MQTT subscribed to: {topic}")

    def start(self):
        """Start the subscriber (connects and loops)."""
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
            logger.info(f"MQTT Subscriber started on {self.broker_host}:{self.broker_port}")
        except Exception as e:
            logger.error(f"MQTT Subscriber failed to start: {e}")

    def stop(self):
        """Stop the subscriber."""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT Subscriber stopped.")
