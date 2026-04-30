"""
RakshaSetu Phase 4 — Decision-Driven Router Functions
Seven router functions, one per agent output. Every transition in the graph
is decided by these functions — there are ZERO static edges.

Each router inspects the current state and returns the name of the next node.
LangGraph uses add_conditional_edges() to wire these into the graph.

Routers:
  1. route_from_triage      →  weather | analyst | log | supervisor
  2. route_from_weather     →  analyst | weather (recheck) | supervisor
  3. route_from_analyst     →  resources | notifier | log | supervisor
  4. route_from_resources   →  notifier | supervisor
  5. route_from_notifier    →  feedback | supervisor | notifier (retry)
  6. route_from_feedback    →  supervisor | analyst | notifier
  7. route_from_supervisor  →  log | resources | analyst | notifier
"""

import logging
from app.shared.state import AgentState

logger = logging.getLogger("raksha.routers")

# ── Loop Guard Constants ──────────────────────────────────────
MAX_WEATHER_RECHECKS = 2
MAX_NOTIFICATION_RETRIES = 2
MAX_FEEDBACK_LOOPS = 3
MAX_SUPERVISOR_INTERVENTIONS = 3


# ══════════════════════════════════════════════════════════════
# 1. TRIAGE ROUTER
# ══════════════════════════════════════════════════════════════

def route_from_triage(state: AgentState) -> str:
    """
    Routes from triage to the appropriate first processing agent.

    Possible targets:
      - weather_simulation: High severity → full pipeline
      - zone_analyst:       Medium severity → skip weather
      - log_and_end:        Low severity → no action
      - supervisor:         Data conflict → needs resolution
    """
    triage = state.get("triage_result", {})
    routing = triage.get("routing_decision", "medium_severity")
    zone_id = state.get("zone_id", "?")

    if routing == "high_severity":
        target = "weather_simulation"
    elif routing == "medium_severity":
        target = "zone_analyst"
    elif routing == "data_conflict":
        target = "supervisor"
    else:  # low_severity
        target = "log_and_end"

    logger.info(f"🔀 ROUTER [triage → {target}] zone={zone_id} routing={routing}")
    return target


# ══════════════════════════════════════════════════════════════
# 2. WEATHER ROUTER
# ══════════════════════════════════════════════════════════════

def route_from_weather(state: AgentState) -> str:
    """
    Routes from weather simulation based on weather analysis results.

    Possible targets:
      - zone_analyst:       Normal flow → proceed to analysis
      - weather_simulation: Needs recheck (anomaly in data)
      - supervisor:         Anomaly detected, cannot self-resolve
    """
    weather = state.get("weather_data", {})
    routing = weather.get("routing_decision", "proceed_to_analyst")
    recheck_count = state.get("weather_recheck_count", 0)
    zone_id = state.get("zone_id", "?")

    if routing == "needs_recheck" and recheck_count < MAX_WEATHER_RECHECKS:
        target = "weather_simulation"
        logger.info(f"🔁 ROUTER [weather → weather] RECHECK #{recheck_count + 1}")
    elif routing == "anomaly_detected" or (routing == "needs_recheck" and recheck_count >= MAX_WEATHER_RECHECKS):
        target = "supervisor"
        logger.info(f"⚠️ ROUTER [weather → supervisor] anomaly/max rechecks")
    else:
        target = "zone_analyst"

    logger.info(f"🔀 ROUTER [weather → {target}] zone={zone_id} routing={routing}")
    return target


# ══════════════════════════════════════════════════════════════
# 3. ZONE ANALYST ROUTER
# ══════════════════════════════════════════════════════════════

def route_from_analyst(state: AgentState) -> str:
    """
    Routes from zone analyst based on the analysis decision.

    Possible targets:
      - resource_allocator: EVACUATE or DEPLOY_RESOURCES → allocate resources
      - notifier:           ALERT → notify without resource allocation
      - log_and_end:        MONITOR or STANDBY → no action
      - supervisor:         Low confidence or conflicting analysis
    """
    analysis = state.get("zone_analysis", {})
    routing = analysis.get("routing_decision", "monitor")
    decision = analysis.get("decision", "MONITOR")
    confidence = analysis.get("confidence", 0.5)
    zone_id = state.get("zone_id", "?")

    if routing == "conflict" or confidence < 0.3:
        target = "supervisor"
    elif routing == "evacuate" or decision == "EVACUATE":
        target = "resource_allocator"
    elif routing == "deploy" or decision == "DEPLOY_RESOURCES":
        target = "resource_allocator"
    elif routing == "alert_only" or decision == "ALERT":
        target = "notifier"
    else:  # MONITOR / STANDBY
        target = "log_and_end"

    logger.info(f"🔀 ROUTER [analyst → {target}] zone={zone_id} decision={decision} conf={confidence}")
    return target


# ══════════════════════════════════════════════════════════════
# 4. RESOURCE ALLOCATOR ROUTER
# ══════════════════════════════════════════════════════════════

def route_from_resources(state: AgentState) -> str:
    """
    Routes from resource allocator based on allocation result.

    Possible targets:
      - notifier:   Resources allocated → proceed to notifications
      - supervisor:  Escalation needed (no capacity, allocation failed)
    """
    plan = state.get("resource_plan", {})
    routing = plan.get("routing_decision", "allocated")
    escalation = plan.get("escalation_needed", False)
    zone_id = state.get("zone_id", "?")

    if routing in ("escalation_needed", "no_capacity") or escalation:
        target = "supervisor"
    else:
        target = "notifier"

    logger.info(f"🔀 ROUTER [resources → {target}] zone={zone_id} escalation={escalation}")
    return target


# ══════════════════════════════════════════════════════════════
# 5. NOTIFIER ROUTER
# ══════════════════════════════════════════════════════════════

def route_from_notifier(state: AgentState) -> str:
    """
    Routes from notifier based on delivery status.

    Possible targets:
      - feedback:   Delivery successful → check response effectiveness
      - notifier:   Delivery needs retry (CRITICAL alert)
      - supervisor:  Delivery completely failed
    """
    notif = state.get("notification_result", {})
    routing = notif.get("routing_decision", "delivered")
    delivery = notif.get("delivery_status", "unknown")
    retry_count = state.get("notification_retry_count", 0)
    zone_id = state.get("zone_id", "?")

    if routing == "delivery_failed" or delivery == "failed":
        target = "supervisor"
    elif routing == "critical_retry" and retry_count < MAX_NOTIFICATION_RETRIES:
        target = "notifier"
        logger.info(f"🔁 ROUTER [notifier → notifier] RETRY #{retry_count + 1}")
    else:
        target = "feedback"

    logger.info(f"🔀 ROUTER [notifier → {target}] zone={zone_id} delivery={delivery}")
    return target


# ══════════════════════════════════════════════════════════════
# 6. FEEDBACK ROUTER
# ══════════════════════════════════════════════════════════════

def route_from_feedback(state: AgentState) -> str:
    """
    Routes from feedback agent — implements the Notifier→Feedback→Analyst loop.

    Possible targets:
      - zone_analyst:  Re-trigger analysis (conditions not improving)
      - notifier:      Renotify (notification delivery issue)
      - supervisor:    Escalate (max loops or critical failure)
    """
    fb = state.get("feedback", {})
    routing = fb.get("routing_decision", "success")
    action = fb.get("action", "none")
    loop_count = state.get("feedback_loop_count", 0)
    zone_id = state.get("zone_id", "?")

    if routing == "re_trigger" and loop_count < MAX_FEEDBACK_LOOPS:
        # Feedback → Analyst (the core non-linear feedback loop)
        target = "zone_analyst"
        logger.info(f"🔁 ROUTER [feedback → analyst] RE-TRIGGER loop #{loop_count}")
    elif routing == "renotify" and state.get("notification_retry_count", 0) < MAX_NOTIFICATION_RETRIES:
        # Feedback → Notifier (notification issue, not analysis issue)
        target = "notifier"
        logger.info(f"🔁 ROUTER [feedback → notifier] RENOTIFY")
    else:
        # Success or escalate → supervisor for final review
        target = "supervisor"

    logger.info(f"🔀 ROUTER [feedback → {target}] zone={zone_id} action={action} loops={loop_count}")
    return target


# ══════════════════════════════════════════════════════════════
# 7. SUPERVISOR ROUTER
# ══════════════════════════════════════════════════════════════

def route_from_supervisor(state: AgentState) -> str:
    """
    Routes from supervisor — can override and reroute to any agent.

    Possible targets:
      - log_and_end:        Resolved, pipeline complete
      - resource_allocator: Override: force resource deployment
      - zone_analyst:       Override: reanalyze with new context
      - notifier:           Override: resend notifications
      - log_and_end:        Terminal escalation (max interventions)
    """
    sup = state.get("supervisor_decision", {})
    routing = sup.get("routing_decision", "resolved")
    interventions = state.get("supervisor_interventions", 0)
    zone_id = state.get("zone_id", "?")

    # Guard: prevent infinite supervisor loops
    if interventions >= MAX_SUPERVISOR_INTERVENTIONS:
        logger.warning(
            f"⛔ ROUTER [supervisor → log_and_end] MAX INTERVENTIONS ({interventions}) reached"
        )
        return "log_and_end"

    if routing == "override_evacuate":
        target = "resource_allocator"
    elif routing == "override_reanalyze":
        target = "zone_analyst"
    elif routing == "override_renotify":
        target = "notifier"
    elif routing == "terminal_escalation":
        target = "log_and_end"
    else:  # "resolved"
        target = "log_and_end"

    logger.info(
        f"🔀 ROUTER [supervisor → {target}] zone={zone_id} "
        f"routing={routing} interventions={interventions}"
    )
    return target
