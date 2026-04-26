"""
RakshaSetu Phase 4 — Supervisor Agent (LangGraph Node)
Enhanced with ROUTING AUTHORITY — can override and reroute to any agent.

The Phase 4 supervisor doesn't just make a final decision. It can:
  - Override to evacuate:  route to resource_allocator
  - Override to reanalyze: route to zone_analyst
  - Override to renotify:  route to notifier
  - Resolve:               route to log_and_end
  - Terminal escalation:   force-end when max interventions reached

Uses AutoGen-style debate for conflict resolution.
"""

import json
import logging
from langchain_core.messages import HumanMessage, SystemMessage

from app.shared.state import AgentState
from app.shared.utils import get_llm, from_json
from app.shared.tracer import trace_entry, trace_exit
from app.agents.feedback_supervisor.debate import run_supervisor_debate
from app.agents.feedback_supervisor.prompts import SUPERVISOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_SUPERVISOR_INTERVENTIONS = 3


def supervisor_node(state: AgentState) -> dict:
    """
    LangGraph node: Supervisor Agent.
    Reviews all agent outputs, resolves conflicts, makes routing decisions.
    Can override and reroute pipeline to any agent.
    """
    zone_id = state["zone_id"]
    weather_data = state.get("weather_data", {})
    zone_analysis = state.get("zone_analysis", {})
    resource_plan = state.get("resource_plan", {})
    notification_result = state.get("notification_result", {})
    feedback = state.get("feedback", {})
    triage_result = state.get("triage_result", {})
    interventions = state.get("supervisor_interventions", 0)
    reasoning_steps = []

    trace = trace_entry("supervisor", state)
    logger.info(f"👁️  Supervisor Agent started for zone: {zone_id} (intervention #{interventions + 1})")

    # ==================================================================
    # Step 1: Collect all agent outputs for review
    # ==================================================================
    reasoning_steps.append("Step 1: Collecting outputs from all agents for review.")

    agent_summary = {
        "triage": {
            "severity": triage_result.get("severity", "UNKNOWN"),
            "composite_score": triage_result.get("composite_score", 0),
            "confidence": triage_result.get("confidence", 0),
        },
        "weather": {
            "severity": weather_data.get("severity", "UNKNOWN") if weather_data else "NOT_RUN",
            "confidence": weather_data.get("confidence", 0) if weather_data else 0,
            "rainfall": weather_data.get("rainfall", 0) if weather_data else 0,
        },
        "zone_analyst": {
            "decision": zone_analysis.get("decision", "UNKNOWN") if zone_analysis else "NOT_RUN",
            "priority": zone_analysis.get("priority_score", 0) if zone_analysis else 0,
            "confidence": zone_analysis.get("confidence", 0) if zone_analysis else 0,
        },
        "resource_allocator": {
            "volunteers_assigned": len(resource_plan.get("volunteer_assignments", [])) if resource_plan else 0,
            "shelters_assigned": len(resource_plan.get("shelter_assignments", [])) if resource_plan else 0,
            "escalation": resource_plan.get("escalation_needed", False) if resource_plan else False,
            "confidence": resource_plan.get("confidence", 0) if resource_plan else 0,
        },
        "notifier": {
            "delivery_status": notification_result.get("delivery_status", "unknown") if notification_result else "NOT_RUN",
            "topic": notification_result.get("topic", "none") if notification_result else "none",
            "confidence": notification_result.get("confidence", 0) if notification_result else 0,
        },
        "feedback": {
            "success": feedback.get("success", None) if feedback else None,
            "action": feedback.get("action", "unknown") if feedback else "NOT_RUN",
            "confidence": feedback.get("confidence", 0) if feedback else 0,
        },
    }

    reasoning_steps.append(f"  → Agent summary compiled for {len(agent_summary)} agents")

    # ==================================================================
    # Step 2: Detect conflicts between agents
    # ==================================================================
    reasoning_steps.append("Step 2: Detecting conflicts between agent outputs.")

    conflicts = []

    # Conflict: Weather says LOW but zone analyst says EVACUATE
    if (weather_data and weather_data.get("severity") == "LOW"
            and zone_analysis and zone_analysis.get("decision") == "EVACUATE"):
        conflicts.append("Weather indicates LOW severity but Zone Analyst recommends EVACUATE")

    # Conflict: Resources needed but escalation required
    if (resource_plan and resource_plan.get("escalation_needed")
            and zone_analysis and zone_analysis.get("decision") != "EVACUATE"):
        conflicts.append("Resource escalation needed but decision is not EVACUATE")

    # Conflict: Notification failed
    if notification_result and notification_result.get("delivery_status") == "failed":
        conflicts.append("Notification delivery FAILED — alerts may not have reached field")

    # Conflict: Feedback says escalate
    if feedback and feedback.get("action") == "escalate":
        conflicts.append("Feedback loop exhausted — situation not improving, escalation required")

    # Conflict: Low confidence across multiple agents
    low_conf_agents = [
        name for name, data in agent_summary.items()
        if isinstance(data.get("confidence"), (int, float)) and data["confidence"] < 0.4
        and data.get("confidence") > 0  # Skip NOT_RUN agents
    ]
    if len(low_conf_agents) >= 2:
        conflicts.append(f"Low confidence in multiple agents: {', '.join(low_conf_agents)}")

    # Conflict: Resource allocation failed (no capacity)
    if resource_plan and resource_plan.get("routing_decision") == "no_capacity":
        conflicts.append("CRITICAL: All shelters at capacity — no resources available")

    reasoning_steps.append(f"  → Conflicts detected: {len(conflicts)}")
    for c in conflicts:
        reasoning_steps.append(f"    • {c}")

    # ==================================================================
    # Step 3: Resolve conflicts via debate (if any)
    # ==================================================================
    conflicts_resolved = []

    if conflicts:
        reasoning_steps.append("Step 3: Running supervisor debate to resolve conflicts.")
        try:
            debate_result = run_supervisor_debate(agent_summary, conflicts)
            reasoning_steps.append(f"  → Debate resolution: {debate_result.get('resolution', 'N/A')}")
            conflicts_resolved = debate_result.get("resolutions", [])
        except Exception as e:
            logger.warning(f"   Supervisor debate failed: {e}")
            reasoning_steps.append(f"  → Debate failed ({e}), using direct LLM resolution.")
            debate_result = None
    else:
        reasoning_steps.append("Step 3: No conflicts detected — all agents aligned.")
        debate_result = None

    # ==================================================================
    # Step 4: LLM final review and decision WITH routing authority
    # ==================================================================
    reasoning_steps.append("Step 4: LLM producing final supervisor decision with routing authority.")

    # Check if we're at max interventions
    if interventions >= MAX_SUPERVISOR_INTERVENTIONS - 1:
        reasoning_steps.append(
            f"  → ⚠️ Max interventions ({MAX_SUPERVISOR_INTERVENTIONS}) approaching. "
            f"Will force terminal resolution."
        )

    llm = get_llm()
    review_input = f"""
Zone: {zone_id}
Agent Summary: {json.dumps(agent_summary, indent=2)}
Conflicts: {json.dumps(conflicts)}
Debate Result: {json.dumps(debate_result) if debate_result else 'No debate needed or debate failed'}
Feedback loop count: {state.get('feedback_loop_count', 0)}
Supervisor intervention count: {interventions + 1}/{MAX_SUPERVISOR_INTERVENTIONS}

As the supervisor, make your final decision. You have ROUTING AUTHORITY to redirect the pipeline.

Available routing decisions:
- "resolved": Pipeline complete. Route to log_and_end.
- "override_evacuate": Force resource allocation. Route to resource_allocator.
- "override_reanalyze": Confidence too low, re-run analysis. Route to zone_analyst.
- "override_renotify": Notification failed, resend. Route to notifier.
- "terminal_escalation": Max interventions reached, force-end.

Respond with JSON:
{{
    "final_decision": "<summary of the final coordinated action>",
    "override_decision": "<EVACUATE|ALERT|MONITOR|DEPLOY_RESOURCES|STANDBY|null>",
    "routing_decision": "<resolved|override_evacuate|override_reanalyze|override_renotify|terminal_escalation>",
    "confidence": <0.0 to 1.0>,
    "status": "<RESOLVED|ESCALATED|MONITORING|OVERRIDING>"
}}
"""
    try:
        response = llm.invoke([
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            HumanMessage(content=review_input),
        ])
        supervisor_decision = from_json(response.content)
    except Exception as e:
        logger.warning(f"   Supervisor LLM failed: {e}")
        # Fallback: resolve if no conflicts, escalate if conflicts
        if not conflicts:
            supervisor_decision = {
                "final_decision": f"Supervisor review for {zone_id}: pipeline nominal. No conflicts.",
                "override_decision": None,
                "routing_decision": "resolved",
                "confidence": 0.7,
                "status": "RESOLVED",
            }
        elif interventions >= MAX_SUPERVISOR_INTERVENTIONS - 1:
            supervisor_decision = {
                "final_decision": f"Terminal escalation for {zone_id}: max interventions reached.",
                "override_decision": None,
                "routing_decision": "terminal_escalation",
                "confidence": 0.4,
                "status": "ESCALATED",
            }
        elif notification_result and notification_result.get("delivery_status") == "failed":
            supervisor_decision = {
                "final_decision": f"Override: renotify for {zone_id} — delivery failed.",
                "override_decision": None,
                "routing_decision": "override_renotify",
                "confidence": 0.6,
                "status": "OVERRIDING",
            }
        else:
            supervisor_decision = {
                "final_decision": f"Supervisor review for {zone_id}: {len(conflicts)} conflicts. Accepting analyst decision.",
                "override_decision": None,
                "routing_decision": "resolved",
                "confidence": 0.5,
                "status": "RESOLVED",
            }

    # Force terminal if at max interventions
    routing_decision = supervisor_decision.get("routing_decision", "resolved")
    if interventions >= MAX_SUPERVISOR_INTERVENTIONS - 1 and routing_decision.startswith("override"):
        routing_decision = "terminal_escalation"
        reasoning_steps.append(
            f"  → FORCED terminal_escalation: max interventions ({MAX_SUPERVISOR_INTERVENTIONS}) reached"
        )

    reasoning_steps.append(f"  → Final decision: {supervisor_decision.get('final_decision', 'N/A')}")
    reasoning_steps.append(f"  → Routing: {routing_decision}")

    confidence = supervisor_decision.get("confidence", 0.5)

    supervisor_output = {
        "final_decision": supervisor_decision.get("final_decision", ""),
        "conflicts_resolved": conflicts_resolved or conflicts,
        "reasoning_steps": reasoning_steps,
        "confidence": confidence,
        "routing_decision": routing_decision,
    }

    trace_exit(trace, decision=supervisor_decision.get("status", "UNKNOWN"),
               confidence=confidence, routed_to=routing_decision)

    logger.info(
        f"👁️  Supervisor complete → status={supervisor_decision.get('status', 'UNKNOWN')}, "
        f"route={routing_decision}, interventions={interventions + 1}"
    )

    return {
        "supervisor_decision": supervisor_output,
        "supervisor_interventions": interventions + 1,
        "execution_trace": [trace],
        "routing_history": [],
        "messages": [HumanMessage(content=f"Supervisor review complete for {zone_id}: route={routing_decision}")],
    }
