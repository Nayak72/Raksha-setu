"""
RakshaSetu Phase 4 — Triage Agent (LangGraph Node)
Entry-point agent that dynamically classifies initial detection data
and routes to the appropriate next agent.

Routing decisions:
  high_severity   → weather_simulation (full pipeline)
  medium_severity → zone_analyst (skip weather if data is sufficient)
  low_severity    → log_and_end (no action needed)
  data_conflict   → supervisor (detection data is inconsistent)
"""

import logging
from langchain_core.messages import HumanMessage

from app.shared.state import AgentState
from app.shared.tracer import trace_entry, trace_exit

logger = logging.getLogger(__name__)


def triage_node(state: AgentState) -> dict:
    """
    LangGraph node: Triage Agent.
    Evaluates raw detection data to determine initial severity and route.
    """
    zone_id = state["zone_id"]
    detection = state.get("detection_data", {})
    reasoning_steps = []

    trace = trace_entry("triage", state)
    logger.info(f"🔀 Triage Agent started for zone: {zone_id}")

    # ── Step 1: Extract detection metrics ──────────────────────
    reasoning_steps.append("Step 1: Extracting detection metrics from YOLO data.")

    crowd_density = detection.get("crowd_density", 0)
    flood_level = detection.get("flood_level", 0)
    structural_damage = detection.get("structural_damage", 0)
    fire_detected = detection.get("fire_detected", False)
    det_confidence = detection.get("confidence", 0)

    reasoning_steps.append(
        f"  → crowd={crowd_density:.3f}, flood={flood_level:.3f}, "
        f"damage={structural_damage:.3f}, fire={fire_detected}, "
        f"confidence={det_confidence:.3f}"
    )

    # ── Step 2: Compute composite severity score ───────────────
    reasoning_steps.append("Step 2: Computing composite severity score.")

    # Weighted composite: flood has highest weight, crowd next, then damage
    composite = (
        flood_level * 0.40
        + crowd_density * 0.30
        + structural_damage * 0.20
        + (0.10 if fire_detected else 0.0)
    )
    composite = round(composite, 3)
    reasoning_steps.append(f"  → Composite score: {composite:.3f}")

    # ── Step 3: Check for data conflicts ───────────────────────
    reasoning_steps.append("Step 3: Checking for data conflicts / anomalies.")

    has_conflict = False
    # Conflict: high detection values but very low confidence
    if composite > 0.4 and det_confidence < 0.5:
        has_conflict = True
        reasoning_steps.append(
            f"  → CONFLICT: High composite ({composite}) but low detection confidence ({det_confidence})"
        )
    # Conflict: fire detected with no structural damage
    if fire_detected and structural_damage < 0.01:
        has_conflict = True
        reasoning_steps.append(
            "  → CONFLICT: Fire detected but zero structural damage (sensor anomaly?)"
        )

    # ── Step 4: Route decision ─────────────────────────────────
    reasoning_steps.append("Step 4: Making routing decision.")

    if has_conflict:
        routing_decision = "data_conflict"
        severity = "conflict"
        confidence = 0.4
        reasoning_steps.append("  → Decision: data_conflict → route to supervisor for resolution")
    elif composite >= 0.45:
        routing_decision = "high_severity"
        severity = "HIGH"
        confidence = min(0.9, det_confidence)
        reasoning_steps.append(
            f"  → Decision: high_severity (composite {composite} ≥ 0.45) → route to weather_simulation"
        )
    elif composite >= 0.20:
        routing_decision = "medium_severity"
        severity = "MEDIUM"
        confidence = min(0.85, det_confidence)
        reasoning_steps.append(
            f"  → Decision: medium_severity (0.20 ≤ {composite} < 0.45) → route to zone_analyst"
        )
    else:
        routing_decision = "low_severity"
        severity = "LOW"
        confidence = 0.9
        reasoning_steps.append(
            f"  → Decision: low_severity (composite {composite} < 0.20) → route to log_and_end"
        )

    triage_result = {
        "severity": severity,
        "composite_score": composite,
        "reasoning_steps": reasoning_steps,
        "confidence": confidence,
        "routing_decision": routing_decision,
    }

    trace_exit(trace, decision=f"severity={severity}", confidence=confidence, routed_to=routing_decision)

    logger.info(
        f"🔀 Triage complete → severity={severity}, composite={composite}, "
        f"route={routing_decision}"
    )

    return {
        "triage_result": triage_result,
        "execution_trace": [trace],
        "routing_history": [],
        "messages": [HumanMessage(content=f"Triage for {zone_id}: severity={severity}, route={routing_decision}")],
    }
