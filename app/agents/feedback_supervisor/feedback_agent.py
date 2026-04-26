"""
RakshaSetu Phase 4 — Feedback Agent (LangGraph Node)
Enhanced with non-linear routing: can route back to Analyst or Notifier.

Implements the core feedback loop: Notifier → Feedback → Analyst

Routing decisions:
  success    → supervisor (for final sign-off)
  re_trigger → zone_analyst (conditions not improving, re-analyze)
  renotify   → notifier (notification issue, not analysis issue)
  escalate   → supervisor (max loops or critical failure)
"""

import logging
from langchain_core.messages import HumanMessage, SystemMessage

from app.shared.state import AgentState
from app.shared.utils import get_llm, from_json
from app.shared.tools import generate_mock_detection
from app.shared.tracer import trace_entry, trace_exit
from app.agents.feedback_supervisor.prompts import FEEDBACK_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_FEEDBACK_LOOPS = 3


def feedback_node(state: AgentState) -> dict:
    """
    LangGraph node: Feedback Agent.
    Compares current detection with previous to assess response effectiveness.
    Decides whether to re-trigger, renotify, or declare success.
    """
    zone_id = state["zone_id"]
    previous_detection = state.get("detection_data", {})
    notification_result = state.get("notification_result", {})
    zone_analysis = state.get("zone_analysis", {})
    loop_count = state.get("feedback_loop_count", 0)
    reasoning_steps = []

    trace = trace_entry("feedback", state)
    logger.info(f"🔄 Feedback Agent started for zone: {zone_id} (loop #{loop_count + 1})")

    # ==================================================================
    # Step 1: Get fresh detection data (simulates new YOLO frame)
    # ==================================================================
    reasoning_steps.append("Step 1: Acquiring fresh detection data to compare with previous state.")

    new_detection = generate_mock_detection(zone_id)

    prev_crowd = previous_detection.get("crowd_density", 0)
    new_crowd = new_detection.get("crowd_density", 0)
    prev_flood = previous_detection.get("flood_level", 0)
    new_flood = new_detection.get("flood_level", 0)

    crowd_delta = new_crowd - prev_crowd
    flood_delta = new_flood - prev_flood

    reasoning_steps.append(
        f"  → Previous: crowd={prev_crowd:.3f}, flood={prev_flood:.3f}"
    )
    reasoning_steps.append(
        f"  → Current:  crowd={new_crowd:.3f}, flood={new_flood:.3f}"
    )
    reasoning_steps.append(
        f"  → Delta:    crowd={crowd_delta:+.3f}, flood={flood_delta:+.3f}"
    )

    # ==================================================================
    # Step 2: Check notification delivery status
    # ==================================================================
    reasoning_steps.append("Step 2: Evaluating notification delivery status.")

    delivery_status = notification_result.get("delivery_status", "unknown")
    reasoning_steps.append(f"  → Delivery status: {delivery_status}")

    # Check if notification was the problem
    notification_failed = delivery_status in ("failed", "partial_failure")
    if notification_failed:
        reasoning_steps.append("  → ⚠️ Notification delivery had issues — may need renotify")

    # ==================================================================
    # Step 3: LLM evaluates response effectiveness
    # ==================================================================
    reasoning_steps.append("Step 3: LLM evaluating response effectiveness.")

    llm = get_llm()
    eval_input = f"""
Zone: {zone_id}
Previous detection: crowd_density={prev_crowd:.3f}, flood_level={prev_flood:.3f}
Current detection:  crowd_density={new_crowd:.3f}, flood_level={new_flood:.3f}
Crowd change: {crowd_delta:+.3f}
Flood change: {flood_delta:+.3f}
Notification delivery: {delivery_status}
Zone decision was: {zone_analysis.get('decision', 'UNKNOWN')}
Feedback loop iteration: {loop_count + 1}/{MAX_FEEDBACK_LOOPS}

Evaluate whether the disaster response was effective.
Respond with JSON:
{{
    "success": true/false,
    "action": "<none|re_trigger|renotify|escalate>",
    "confidence": <0.0 to 1.0>,
    "reasoning": "<explanation>"
}}

Guidelines:
- If crowd density decreased: likely success
- If flood level decreased: situation improving
- If both increased: likely need re-trigger (re-analyze)
- If notification delivery failed but conditions improved: success anyway
- If notification delivery failed and conditions NOT improving: renotify
- If at max loop count ({MAX_FEEDBACK_LOOPS}): must escalate, cannot re-trigger
"""
    try:
        response = llm.invoke([
            SystemMessage(content=FEEDBACK_SYSTEM_PROMPT),
            HumanMessage(content=eval_input),
        ])
        evaluation = from_json(response.content)
    except Exception as e:
        logger.warning(f"   LLM feedback evaluation failed: {e}")
        # Fallback: heuristic
        if crowd_delta < -0.05 or flood_delta < -0.05:
            evaluation = {
                "success": True,
                "action": "none",
                "confidence": 0.6,
                "reasoning": f"Heuristic: conditions improving (crowd {crowd_delta:+.3f}, flood {flood_delta:+.3f})",
            }
        elif notification_failed:
            evaluation = {
                "success": False,
                "action": "renotify",
                "confidence": 0.5,
                "reasoning": f"Heuristic: notification failed, renotify needed",
            }
        else:
            evaluation = {
                "success": False,
                "action": "re_trigger" if loop_count < MAX_FEEDBACK_LOOPS - 1 else "escalate",
                "confidence": 0.5,
                "reasoning": f"Heuristic: conditions not improving, LLM unavailable",
            }

    # Enforce max loop count
    if loop_count >= MAX_FEEDBACK_LOOPS - 1 and evaluation.get("action") == "re_trigger":
        evaluation["action"] = "escalate"
        reasoning_steps.append(f"  → Max feedback loops ({MAX_FEEDBACK_LOOPS}) reached. Forcing escalation.")

    success = evaluation.get("success", False)
    action = evaluation.get("action", "none")
    confidence = evaluation.get("confidence", 0.5)
    reasoning_steps.append(f"  → Evaluation: success={success}, action={action}")
    reasoning_steps.append(f"  → Reasoning: {evaluation.get('reasoning', 'N/A')}")

    # ==================================================================
    # Step 4: Determine routing decision (Phase 4 — non-linear)
    # ==================================================================
    reasoning_steps.append("Step 4: Determining routing decision for non-linear graph.")

    if action == "re_trigger" and loop_count < MAX_FEEDBACK_LOOPS:
        routing_decision = "re_trigger"
        reasoning_steps.append(
            f"  → RE-TRIGGER → routing to zone_analyst (Notifier→Feedback→Analyst loop)"
        )
    elif action == "renotify":
        routing_decision = "renotify"
        reasoning_steps.append("  → RENOTIFY → routing to notifier")
    elif action == "escalate":
        routing_decision = "escalate"
        reasoning_steps.append("  → ESCALATE → routing to supervisor")
    else:
        # Success → still route to supervisor for final sign-off
        routing_decision = "success"
        reasoning_steps.append("  → SUCCESS → routing to supervisor for final review")

    should_retrigger = routing_decision == "re_trigger"

    feedback_output = {
        "success": success,
        "action": action,
        "reasoning_steps": reasoning_steps,
        "confidence": confidence,
        "routing_decision": routing_decision,
    }

    trace_exit(trace, decision=f"success={success},action={action}",
               confidence=confidence, routed_to=routing_decision)

    logger.info(
        f"🔄 Feedback Agent complete → success={success}, action={action}, "
        f"route={routing_decision}"
    )

    return {
        "feedback": feedback_output,
        "feedback_loop_count": loop_count + 1,
        "should_retrigger": should_retrigger,
        "detection_data": new_detection,
        "execution_trace": [trace],
        "routing_history": [],
        "messages": [HumanMessage(content=f"Feedback for {zone_id}: success={success}, route={routing_decision}")],
    }
