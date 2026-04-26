"""
RakshaSetu — MCP Communications Tools
LangChain tool interfaces for alert broadcasting (MQTT + Supabase) and
acknowledgment tracking (acknowledgments table + MQTT).

Schema alignment:
  alerts          → zone_id TEXT FK, severity, message, topic,
                     delivery_status, retry_count, acked_at
  acknowledgments → device_id, alert_id FK, status ('received','read','acted')
"""

import time
import logging
from langchain_core.tools import tool
from app.db.supabase_client import get_supabase as get_supabase_client
from app.mqtt.client import mqtt_manager as get_mqtt_manager

logger = logging.getLogger("raksha.tools.comms")


@tool
def broadcast_alert(zone_id: str, topic: str, message: str, severity: str = "MEDIUM") -> dict:
    """
    Broadcast an alert for a disaster zone.
    Writes to the Supabase alerts table AND publishes to MQTT for real-time delivery.
    Severity must be one of: LOW, MEDIUM, HIGH, CRITICAL.
    Use this tool when a zone needs an emergency alert broadcast.
    """
    try:
        mqtt_mgr = get_mqtt_manager()
        client = get_supabase_client()

        # Normalize severity
        severity = severity.upper()
        if severity not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            severity = "MEDIUM"

        # 1. Persist to Supabase alerts table
        db_response = (
            client.table("alerts")
            .insert({
                "zone_id": zone_id,
                "severity": severity,
                "message": message,
                "topic": topic,
                "delivery_status": "sent",
                "retry_count": 0,
            })
            .execute()
        )
        db_record = (db_response.data or [{}])[0]
        alert_id = db_record.get("id")
        db_persisted = alert_id is not None

        # 2. Publish to MQTT for real-time delivery
        mqtt_success = mqtt_mgr.publish_alert(
            zone_id=zone_id,
            topic=topic,
            message=message,
        )

        # 3. Update delivery status
        if db_persisted:
            status = "delivered" if mqtt_success else "sent"
            client.table("alerts").update(
                {"delivery_status": status}
            ).eq("id", alert_id).execute()

        # 4. Clear previous MQTT acks (new broadcast cycle)
        mqtt_mgr.clear_acks(zone_id)

        return {
            "zone_id": zone_id,
            "alert_id": alert_id,
            "topic": topic,
            "message": message,
            "severity": severity,
            "mqtt_delivered": mqtt_success,
            "db_persisted": db_persisted,
            "delivery_status": "delivered" if mqtt_success else "sent",
            "timestamp": time.time(),
            "fallback": False,
        }

    except Exception as e:
        logger.error(f"broadcast_alert failed for zone {zone_id}: {e}")
        return {
            "zone_id": zone_id,
            "alert_id": None,
            "topic": topic,
            "message": message,
            "severity": severity,
            "mqtt_delivered": False,
            "db_persisted": False,
            "delivery_status": "failed",
            "timestamp": time.time(),
            "fallback": True,
            "error": str(e),
        }


@tool
def get_ack_status(zone_id: str) -> dict:
    """
    Check acknowledgment status for alerts sent to a zone.
    Queries the acknowledgments table for the most recent alert in this zone,
    and also checks the MQTT ack store for real-time acks.
    Use this tool to decide whether to retry broadcasting.
    """
    try:
        client = get_supabase_client()
        mqtt_mgr = get_mqtt_manager()

        # 1. Find the most recent alert for this zone
        alert_resp = (
            client.table("alerts")
            .select("id, delivery_status, retry_count")
            .eq("zone_id", zone_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        latest_alert = (alert_resp.data or [{}])[0] if alert_resp.data else {}
        alert_id = latest_alert.get("id")

        # 2. Count acknowledgments from the acknowledgments table
        db_ack_count = 0
        if alert_id:
            ack_resp = (
                client.table("acknowledgments")
                .select("device_id", count="exact")
                .eq("alert_id", alert_id)
                .execute()
            )
            db_ack_count = ack_resp.count or 0

        # 3. Also check MQTT real-time acks
        mqtt_ack_count = mqtt_mgr.get_ack_count(zone_id)

        # 4. Total ack count (DB + MQTT, deduplicated by taking max)
        total_acks = max(db_ack_count, mqtt_ack_count)

        # 5. Estimate total recipients (all volunteers + shelters)
        vol_resp = (
            client.table("volunteers")
            .select("id", count="exact")
            .execute()
        )
        shelter_resp = (
            client.table("shelters")
            .select("id", count="exact")
            .eq("is_active", True)
            .execute()
        )
        total_recipients = (vol_resp.count or 0) + (shelter_resp.count or 0)

        ack_rate = (total_acks / total_recipients * 100) if total_recipients > 0 else 0.0
        retry_count = latest_alert.get("retry_count", 0)

        return {
            "zone_id": zone_id,
            "alert_id": alert_id,
            "ack_count": total_acks,
            "total_recipients": total_recipients,
            "ack_rate": round(ack_rate, 1),
            "retry_needed": ack_rate < 50.0,
            "current_retry_count": retry_count,
            "delivery_status": latest_alert.get("delivery_status", "unknown"),
            "mqtt_connected": mqtt_mgr.is_connected,
            "fallback": False,
        }

    except Exception as e:
        logger.error(f"get_ack_status failed for zone {zone_id}: {e}")
        return {
            "zone_id": zone_id,
            "alert_id": None,
            "ack_count": 0,
            "total_recipients": 0,
            "ack_rate": 0.0,
            "retry_needed": False,
            "current_retry_count": 0,
            "delivery_status": "error",
            "mqtt_connected": False,
            "fallback": True,
            "error": str(e),
        }
