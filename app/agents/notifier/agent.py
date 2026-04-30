"""
RakshaSetu Phase 4 — Notifier Agent (LangGraph Node)
Enhanced with UDP broadcast delivery, routing_decision, retry self-loop,
and execution trace.

Decision Logic:
  LOW → dashboard only (no broadcast)
  MEDIUM → UDP broadcast to zone devices
  CRITICAL → UDP broadcast with repeated delivery + FCM push

Routing decisions:
  delivered     → feedback (check response effectiveness)
  critical_retry → notifier (self-loop for CRITICAL retry)
  delivery_failed → supervisor (complete failure)
"""


import logging
import uuid
from datetime import datetime, timezone
from langchain_core.messages import HumanMessage, SystemMessage

from app.shared.state import AgentState
from app.shared.utils import get_llm, from_json
from app.shared.tracer import trace_entry, trace_exit
from app.agents.notifier.prompts import NOTIFIER_SYSTEM_PROMPT
from app.network.udp_sender import send_udp_broadcast

logger = logging.getLogger(__name__)


def notifier_node(state: AgentState) -> dict:
    """
    LangGraph node: Notifier Agent.
    Reads zone_analysis + resource_plan, broadcasts alerts via UDP to Android devices.
    Returns routing_decision for non-linear graph.
    """
    zone_id = state["zone_id"]
    zone_analysis = state.get("zone_analysis", {})
    weather_data = state.get("weather_data", {})
    resource_plan = state.get("resource_plan", {})
    retry_count = state.get("notification_retry_count", 0)
    reasoning_steps = []
    tools_used = []

    trace = trace_entry("notifier", state)

    decision = zone_analysis.get("decision", "MONITOR")
    priority = zone_analysis.get("priority_score", 0.0)
    weather_severity = weather_data.get("severity", "LOW")

    logger.info(f"📢 Notifier Agent started for zone: {zone_id} (retry #{retry_count})")

    # ==================================================================
    # Step 1: Evaluate severity → determine notification level
    # ==================================================================
    reasoning_steps.append("Step 1: Evaluating notification severity level.")

    llm = get_llm()
    eval_input = f"""
Zone: {zone_id}
Zone decision: {decision}
Priority score: {priority}
Weather severity: {weather_severity}
Resource escalation needed: {resource_plan.get('escalation_needed', False)}
Notification retry count: {retry_count}

Determine the notification strategy. Respond with JSON:
{{
    "notification_level": "<LOW|MEDIUM|CRITICAL>",
    "message": "<the alert message to broadcast>",
    "reasoning": "<why this level>"
}}
"""
    try:
        response = llm.invoke([
            SystemMessage(content=NOTIFIER_SYSTEM_PROMPT),
            HumanMessage(content=eval_input),
        ])
        notification_plan = from_json(response.content)
    except Exception as e:
        logger.warning(f"   LLM notification planning failed: {e}")
        level_map = {
            "EVACUATE": "CRITICAL",
            "DEPLOY_RESOURCES": "MEDIUM",
            "ALERT": "MEDIUM",
            "MONITOR": "LOW",
            "STANDBY": "LOW",
        }
        notification_plan = {
            "notification_level": level_map.get(decision, "LOW"),
            "message": f"[{decision}] Zone {zone_id}: Weather severity {weather_severity}, priority {priority:.2f}",
            "reasoning": "Fallback: mapped from zone decision",
        }

    level = notification_plan.get("notification_level", "LOW")
    message = notification_plan.get("message", f"Alert for zone {zone_id}")
    reasoning_steps.append(f"  → Notification level: {level}")
    reasoning_steps.append(f"  → Reasoning: {notification_plan.get('reasoning', 'N/A')}")

    # ==================================================================
    # Step 2: Determine broadcast channels based on level
    # ==================================================================
    reasoning_steps.append("Step 2: Selecting broadcast channels.")

    channels = []
    if level == "LOW":
        channels = []
        reasoning_steps.append("  → LOW severity: dashboard notification only, no UDP broadcast.")
    elif level == "MEDIUM":
        channels = [f"udp/zone/{zone_id}"]
        reasoning_steps.append(f"  → MEDIUM severity: UDP broadcast to zone {zone_id}")
    elif level == "CRITICAL":
        channels = ["udp/global", "udp/critical", f"udp/zone/{zone_id}"]
        reasoning_steps.append("  → CRITICAL severity: broadcasting to global + critical + zone channels.")

    # ==================================================================
    # Step 3: Send UDP Broadcast to Android devices
    # ==================================================================
    delivery_status = "dashboard_only"
    publish_failed = False

    if channels:
        reasoning_steps.append("Step 3: Sending UDP broadcast to Android devices.")
        tools_used.append("udp_broadcast")

        alert_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        # Build the UDP payload matching the Android app's expected format
        udp_payload = {
            "type": "ALERT",
            "alert_id": alert_id,
            "zone": zone_id,
            "severity": level.upper(),
            "message": message,
            "channels": ",".join(channels),
            "timestamp": now_iso,
        }

        # Fire the UDP broadcast
        broadcast_success = send_udp_broadcast(udp_payload)

        if broadcast_success:
            reasoning_steps.append(f"  → UDP broadcast sent successfully (alert_id={alert_id[:8]}...)")
            delivery_status = "sent"
        else:
            reasoning_steps.append(f"  → FAILED to send UDP broadcast")
            publish_failed = True
            if level == "CRITICAL":
                delivery_status = "partial_failure"
            else:
                delivery_status = "failed"

        # For CRITICAL alerts, also try FCM push for devices not on LAN
        if level == "CRITICAL":
            try:
                from app.network.fcm_sender import send_fcm_alert_async
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, schedule the FCM send
                    asyncio.create_task(send_fcm_alert_async(udp_payload))
                    reasoning_steps.append("  → FCM push notification scheduled for offline devices.")
                    tools_used.append("fcm_push")
            except Exception as e:
                reasoning_steps.append(f"  → FCM push failed (UDP still sent): {e}")

    # ==================================================================
    # Step 4: Store alert in DB via Supabase
    # ==================================================================
    reasoning_steps.append("Step 4: Persisting alert to database.")
    try:
        from app.db.supabase_client import get_supabase
        sb = get_supabase()
        alert_row = {
            "zone": zone_id,
            "message": message,
            "severity": level.lower(),
        }
        sb.table("alerts").insert(alert_row).execute()
        reasoning_steps.append("  → Alert stored in database.")
    except Exception as e:
        reasoning_steps.append(f"  → Failed to store alert in DB: {e}")
        logger.warning(f"   DB alert storage failed: {e}")

    # ==================================================================
    # Step 5: Determine routing decision (Phase 4 — non-linear)
    # ==================================================================
    reasoning_steps.append("Step 5: Determining routing decision for non-linear graph.")

    if publish_failed and delivery_status == "failed":
        routing_decision = "delivery_failed"
        reasoning_steps.append("  → Delivery FAILED → routing to supervisor")
    elif level == "CRITICAL" and retry_count == 0 and delivery_status == "partial_failure":
        routing_decision = "critical_retry"
        reasoning_steps.append("  → CRITICAL partial failure → self-retry")
    else:
        routing_decision = "delivered"
        reasoning_steps.append("  → Delivered → routing to feedback")

    notification_result = {
        "topic": ",".join(channels) if channels else "dashboard",
        "reasoning_steps": reasoning_steps,
        "tools_used": tools_used,
        "delivery_status": delivery_status,
        "confidence": 0.85 if delivery_status == "sent" else 0.5,
        "routing_decision": routing_decision,
    }

    confidence = notification_result["confidence"]
    trace_exit(trace, decision=f"level={level},status={delivery_status}",
               confidence=confidence, routed_to=routing_decision)

    logger.info(
        f"📢 Notifier complete → level={level}, status={delivery_status}, route={routing_decision}"
    )

    return {
        "notification_result": notification_result,
        "notification_retry_count": retry_count + 1 if routing_decision == "critical_retry" else retry_count,
        "execution_trace": [trace],
        "routing_history": [],
        "messages": [HumanMessage(content=f"Notification complete for {zone_id}: level={level}")],
    }
