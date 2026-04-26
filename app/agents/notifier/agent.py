"""
RakshaSetu Phase 4 — Notifier Agent (LangGraph Node)
Enhanced with routing_decision, retry self-loop, and execution trace.

Decision Logic:
  LOW → dashboard only (no MQTT)
  MEDIUM → publish to alerts/zone/{zone_id}
  CRITICAL → publish to alerts/global + alerts/critical + repeated broadcast

Routing decisions:
  delivered     → feedback (check response effectiveness)
  critical_retry → notifier (self-loop for CRITICAL retry)
  delivery_failed → supervisor (complete failure)
"""

import json
import logging
from langchain_core.messages import HumanMessage, SystemMessage

from app.shared.state import AgentState
from app.shared.utils import get_llm, from_json
from app.shared.tracer import trace_entry, trace_exit
from app.agents.notifier.mqtt_client import MQTTPublisher
from app.agents.notifier.ack_manager import ACKManager
from app.agents.notifier.prompts import NOTIFIER_SYSTEM_PROMPT
from app.db.connection import execute_query

logger = logging.getLogger(__name__)

# Singleton MQTT instances
_mqtt_publisher = None
_ack_manager = None


def _get_mqtt():
    global _mqtt_publisher
    if _mqtt_publisher is None:
        _mqtt_publisher = MQTTPublisher()
    return _mqtt_publisher


def _get_ack_manager():
    global _ack_manager
    if _ack_manager is None:
        _ack_manager = ACKManager()
    return _ack_manager


def notifier_node(state: AgentState) -> dict:
    """
    LangGraph node: Notifier Agent.
    Reads zone_analysis + resource_plan, broadcasts alerts via MQTT.
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
    # Step 2: Choose MQTT topic based on level
    # ==================================================================
    reasoning_steps.append("Step 2: Selecting MQTT topic(s).")

    topics = []
    if level == "LOW":
        topics = []
        reasoning_steps.append("  → LOW severity: dashboard notification only, no MQTT broadcast.")
    elif level == "MEDIUM":
        topics = [f"alerts/zone/{zone_id}"]
        reasoning_steps.append(f"  → MEDIUM severity: publishing to alerts/zone/{zone_id}")
    elif level == "CRITICAL":
        topics = ["alerts/global", "alerts/critical", f"alerts/zone/{zone_id}"]
        reasoning_steps.append("  → CRITICAL severity: broadcasting to global + critical + zone topics.")

    # ==================================================================
    # Step 3: Publish alerts via MQTT
    # ==================================================================
    delivery_status = "dashboard_only"
    publish_failed = False

    if topics:
        reasoning_steps.append("Step 3: Publishing alerts via MQTT.")
        mqtt = _get_mqtt()
        tools_used.append("broadcast_alert")

        alert_payload = json.dumps({
            "zone_id": zone_id,
            "level": level,
            "message": message,
            "decision": decision,
            "weather_severity": weather_severity,
            "priority": priority,
        })

        publish_success = True
        for topic in topics:
            try:
                mqtt.publish(topic, alert_payload, qos=1 if level == "CRITICAL" else 0)
                reasoning_steps.append(f"  → Published to {topic}")
            except Exception as e:
                reasoning_steps.append(f"  → FAILED to publish to {topic}: {e}")
                publish_success = False

        if publish_success:
            delivery_status = "sent"
        elif not publish_success and level == "CRITICAL":
            delivery_status = "partial_failure"
            publish_failed = True
        else:
            delivery_status = "failed"
            publish_failed = True

    # ==================================================================
    # Step 4: Store alert in DB
    # ==================================================================
    reasoning_steps.append("Step 4: Persisting alert to database.")
    try:
        execute_query(
            """
            INSERT INTO alerts (zone_id, severity, message, topic, delivery_status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (zone_id, level, message, ",".join(topics) if topics else "dashboard", delivery_status),
            fetch=False,
        )
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
        "topic": ",".join(topics) if topics else "dashboard",
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
