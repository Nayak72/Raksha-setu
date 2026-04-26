"""
RakshaSetu — ACK Manager
Tracks alert delivery acknowledgements from field devices.
Handles retry logic for unacknowledged alerts.

ACK protocol:
- Alerts published to alerts/zone/{zone_id} or alerts/global
- Devices ACK by publishing to alerts/ack/{device_id}
- ACK payload includes alert_id
"""

import json
import logging
import time
import threading
from datetime import datetime
from typing import Optional

from app.agents.notifier.mqtt_client import MQTTSubscriber
from app.db.connection import execute_query

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_INTERVAL_SECONDS = 30


class ACKManager:
    """
    Manages alert acknowledgements from field devices.
    Listens on alerts/ack/# for ACK messages and updates DB.
    """

    def __init__(self):
        self._pending_alerts: dict[str, dict] = {}  # alert_id → {topic, payload, retries, timestamp}
        self._acked_alerts: set[str] = set()
        self._subscriber: Optional[MQTTSubscriber] = None
        self._running = False

    def start_listener(self):
        """Start the ACK listener on alerts/ack/#."""
        if self._subscriber is not None:
            return

        self._subscriber = MQTTSubscriber(client_id="raksha_setu_ack_listener")
        self._subscriber.subscribe("alerts/ack/#", self._handle_ack)
        self._subscriber.start()
        self._running = True
        logger.info("ACK Manager listener started on alerts/ack/#")

        # Start retry thread
        retry_thread = threading.Thread(target=self._retry_loop, daemon=True)
        retry_thread.start()

    def _handle_ack(self, topic: str, payload: str):
        """Handle incoming ACK message from a device."""
        try:
            ack_data = json.loads(payload)
            alert_id = ack_data.get("alert_id")
            device_id = topic.split("/")[-1]  # alerts/ack/{device_id}

            if alert_id:
                self._acked_alerts.add(alert_id)
                if alert_id in self._pending_alerts:
                    del self._pending_alerts[alert_id]

                logger.info(f"ACK received: alert_id={alert_id}, device={device_id}")

                # Update DB
                try:
                    execute_query(
                        """
                        UPDATE alerts
                        SET delivery_status = 'acked', acked_at = NOW()
                        WHERE id = %s
                        """,
                        (alert_id,),
                        fetch=False,
                    )
                except Exception as e:
                    logger.warning(f"Failed to update ACK in DB: {e}")
        except Exception as e:
            logger.warning(f"Invalid ACK message on {topic}: {e}")

    def track_alert(self, alert_id: str, topic: str, payload: str):
        """Register an alert for ACK tracking."""
        self._pending_alerts[alert_id] = {
            "topic": topic,
            "payload": payload,
            "retries": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.info(f"ACK tracking started for alert: {alert_id}")

    def get_status(self, alert_id: str) -> dict:
        """Get the ACK status of a specific alert."""
        if alert_id in self._acked_alerts:
            return {"alert_id": alert_id, "status": "acked"}
        elif alert_id in self._pending_alerts:
            info = self._pending_alerts[alert_id]
            return {
                "alert_id": alert_id,
                "status": "pending",
                "retries": info["retries"],
                "timestamp": info["timestamp"],
            }
        return {"alert_id": alert_id, "status": "unknown"}

    def get_all_pending(self) -> list[dict]:
        """Get all pending (unacknowledged) alerts."""
        return [
            {"alert_id": aid, **info}
            for aid, info in self._pending_alerts.items()
        ]

    def _retry_loop(self):
        """Background thread that retries unacknowledged alerts."""
        while self._running:
            time.sleep(RETRY_INTERVAL_SECONDS)

            for alert_id, info in list(self._pending_alerts.items()):
                if info["retries"] >= MAX_RETRIES:
                    logger.warning(f"Alert {alert_id} exceeded max retries. Marking as failed.")
                    try:
                        execute_query(
                            "UPDATE alerts SET delivery_status = 'failed' WHERE id = %s",
                            (alert_id,),
                            fetch=False,
                        )
                    except Exception:
                        pass
                    del self._pending_alerts[alert_id]
                    continue

                # Retry broadcast
                info["retries"] += 1
                logger.info(
                    f"Retrying alert {alert_id} (attempt {info['retries']}/{MAX_RETRIES})"
                )
                # In production, would re-publish via MQTT here

    def stop(self):
        """Stop the ACK manager."""
        self._running = False
        if self._subscriber:
            self._subscriber.stop()
        logger.info("ACK Manager stopped.")
