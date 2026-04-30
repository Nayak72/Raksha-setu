"""
RakshaSetu Phase 4 — Resource Allocator Agent (LangGraph Node)
Enhanced with routing_decision output and execution trace.

Multi-step reasoning:
1. Evaluate current capacities (shelters, volunteers)
2. Generate candidate allocation plans
3. Score and rank plans
4. Select optimal plan
5. Execute atomic DB updates
6. Determine routing decision for non-linear graph
"""

import json
import logging
from langchain_core.messages import HumanMessage, SystemMessage

from app.shared.state import AgentState
from app.shared.utils import get_llm, from_json
from app.shared.tools import get_shelters, get_available_volunteers, update_assignments
from app.shared.tracer import trace_entry, trace_exit
from app.agents.resource_allocator.scoring import (
    generate_allocation_plans,
    select_optimal_plan,
)
from app.agents.resource_allocator.prompts import RESOURCE_ALLOCATOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def resource_allocator_node(state: AgentState) -> dict:
    """
    LangGraph node: Resource Allocator Agent.
    Reads zone_analysis, queries shelters/volunteers, generates allocation plan.
    Includes routing_decision for non-linear graph.
    """
    zone_id = state["zone_id"]
    zone_analysis = state.get("zone_analysis", {})
    weather_data = state.get("weather_data", {})
    reasoning_steps = []
    tools_used = []

    trace = trace_entry("resource_allocator", state)

    decision = zone_analysis.get("decision", "MONITOR")
    priority = zone_analysis.get("priority_score", 0.0)

    logger.info(f"📦 Resource Allocator started for zone: {zone_id} (decision={decision})")

    # Skip allocation if no resources needed
    if decision in ("MONITOR", "STANDBY"):
        reasoning_steps.append(f"Zone decision is '{decision}' — no resource allocation needed.")
        trace_exit(trace, decision="skipped", confidence=0.9, routed_to="allocated")
        return {
            "resource_plan": {
                "volunteer_assignments": [],
                "shelter_assignments": [],
                "escalation_needed": False,
                "reasoning_steps": reasoning_steps,
                "tools_used": tools_used,
                "confidence": 0.9,
                "routing_decision": "allocated",
            },
            "execution_trace": [trace],
            "routing_history": [],
            "messages": [HumanMessage(content=f"Resource allocation skipped for {zone_id}: decision={decision}")],
        }

    # ==================================================================
    # Step 1: Evaluate current shelter capacity
    # ==================================================================
    reasoning_steps.append("Step 1: Querying available shelters near the zone (PostGIS ST_Distance).")

    try:
        shelters_raw = get_shelters.invoke({"zone_id": zone_id, "radius_km": 15.0})
        shelters = json.loads(shelters_raw)
        tools_used.append("get_shelters")
    except Exception as e:
        logger.warning(f"   Shelter query failed: {e}")
        shelters = []
        reasoning_steps.append(f"  → Shelter query failed: {e}")

    if isinstance(shelters, dict) and "error" in shelters:
        reasoning_steps.append(f"  → Error fetching shelters: {shelters['error']}")
        shelters = []

    total_capacity = sum(s.get("capacity", 0) - s.get("current_occupancy", 0) for s in shelters)
    reasoning_steps.append(
        f"  → Found {len(shelters)} shelters, total available capacity: {total_capacity} spots"
    )

    # ==================================================================
    # Step 2: Evaluate available volunteers
    # ==================================================================
    reasoning_steps.append("Step 2: Querying available volunteers near the zone.")

    skill_needed = "any"
    if decision == "EVACUATE":
        skill_needed = "rescue"
    elif weather_data.get("severity") == "CRITICAL":
        skill_needed = "rescue"

    try:
        volunteers_raw = get_available_volunteers.invoke({"zone_id": zone_id, "skill_type": skill_needed})
        volunteers = json.loads(volunteers_raw)
        tools_used.append("get_available_volunteers")
    except Exception as e:
        logger.warning(f"   Volunteer query failed: {e}")
        volunteers = []

    if isinstance(volunteers, dict) and "error" in volunteers:
        reasoning_steps.append(f"  → Error fetching volunteers: {volunteers['error']}")
        volunteers = []

    reasoning_steps.append(f"  → Found {len(volunteers)} available volunteers (skill: {skill_needed})")

    if len(volunteers) == 0 and skill_needed != "any":
        reasoning_steps.append("  → No specialized volunteers, searching all skills.")
        try:
            volunteers_raw = get_available_volunteers.invoke({"zone_id": zone_id, "skill_type": "any"})
            volunteers = json.loads(volunteers_raw)
            if isinstance(volunteers, dict) and "error" in volunteers:
                volunteers = []
        except Exception:
            volunteers = []
        reasoning_steps.append(f"  → Found {len(volunteers)} volunteers (any skill)")

    # ==================================================================
    # Step 3: Generate candidate allocation plans
    # ==================================================================
    reasoning_steps.append("Step 3: Generating candidate allocation plans.")

    plans = generate_allocation_plans(
        zone_id=zone_id,
        shelters=shelters,
        volunteers=volunteers,
        decision=decision,
        priority=priority,
    )
    reasoning_steps.append(f"  → Generated {len(plans)} candidate plans")

    # ==================================================================
    # Step 4: Score and select optimal plan
    # ==================================================================
    reasoning_steps.append("Step 4: Scoring plans and selecting optimal allocation.")

    escalation_needed = False
    if len(plans) == 0:
        reasoning_steps.append("  → No viable plans! Escalation needed.")
        escalation_needed = True
        selected_plan = {"volunteers": [], "shelters": [], "score": 0}
    else:
        selected_plan = select_optimal_plan(plans)
        reasoning_steps.append(
            f"  → Selected plan: {len(selected_plan['volunteers'])} volunteers, "
            f"{len(selected_plan['shelters'])} shelters, score={selected_plan['score']:.2f}"
        )

    if total_capacity <= 0 and decision in ("EVACUATE", "DEPLOY_RESOURCES"):
        escalation_needed = True
        reasoning_steps.append("  → WARNING: All shelters at capacity! Escalation required.")

    # ==================================================================
    # Step 5: LLM review + execute assignments
    # ==================================================================
    reasoning_steps.append("Step 5: LLM reviewing plan before execution.")

    llm = get_llm()
    review_input = f"""
Zone: {zone_id}, Decision: {decision}, Priority: {priority}
Weather severity: {weather_data.get('severity', 'UNKNOWN')}

Selected allocation plan:
- Volunteers: {json.dumps(selected_plan.get('volunteers', []))}
- Shelters: {json.dumps(selected_plan.get('shelters', []))}
- Plan score: {selected_plan.get('score', 0)}
- Escalation needed: {escalation_needed}

Review this plan. Should we proceed? Respond with JSON:
{{
    "approve": true/false,
    "adjustments": "<any adjustments needed>",
    "confidence": <0.0 to 1.0>
}}
"""
    try:
        response = llm.invoke([
            SystemMessage(content=RESOURCE_ALLOCATOR_SYSTEM_PROMPT),
            HumanMessage(content=review_input),
        ])
        review = from_json(response.content)
        reasoning_steps.append(f"  → LLM review: {review.get('adjustments', 'Approved as-is')}")
        confidence = review.get("confidence", 0.7)
    except Exception as e:
        logger.warning(f"   LLM review failed: {e}")
        reasoning_steps.append(f"  → LLM review failed ({e}), proceeding with plan.")
        confidence = 0.5

    # Execute atomic assignments
    vol_assignments = []
    shelter_assignments = []

    if selected_plan.get("volunteers") or selected_plan.get("shelters"):
        assignment_data = []
        for v in selected_plan.get("volunteers", []):
            entry = {"zone_id": zone_id, "volunteer_id": v["id"], "assignment_type": "volunteer"}
            assignment_data.append(entry)
            vol_assignments.append(entry)
        for s in selected_plan.get("shelters", []):
            entry = {"zone_id": zone_id, "shelter_id": s["id"], "assignment_type": "shelter"}
            assignment_data.append(entry)
            shelter_assignments.append(entry)

        if assignment_data:
            try:
                result_raw = update_assignments.invoke(json.dumps(assignment_data))
                result = json.loads(result_raw)
                tools_used.append("update_assignments")
                reasoning_steps.append(f"  → Assignments executed: {result.get('status', 'unknown')}")
            except Exception as e:
                logger.error(f"   Assignment execution failed: {e}")
                reasoning_steps.append(f"  → Assignment execution FAILED: {e}")
                escalation_needed = True

    # ==================================================================
    # Step 6: Determine routing decision (Phase 4 — non-linear)
    # ==================================================================
    reasoning_steps.append("Step 6: Determining routing decision for non-linear graph.")

    if escalation_needed and total_capacity <= 0:
        routing_decision = "no_capacity"
        reasoning_steps.append("  → No capacity → routing to supervisor")
    elif escalation_needed:
        routing_decision = "escalation_needed"
        reasoning_steps.append("  → Escalation needed → routing to supervisor")
    else:
        routing_decision = "allocated"
        reasoning_steps.append("  → Resources allocated → routing to notifier")

    resource_plan = {
        "volunteer_assignments": vol_assignments,
        "shelter_assignments": shelter_assignments,
        "escalation_needed": escalation_needed,
        "reasoning_steps": reasoning_steps,
        "tools_used": tools_used,
        "confidence": confidence,
        "routing_decision": routing_decision,
    }

    trace_exit(trace, decision=f"alloc:{len(vol_assignments)}v/{len(shelter_assignments)}s",
               confidence=confidence, routed_to=routing_decision)

    logger.info(
        f"📦 Resource Allocator complete → "
        f"{len(vol_assignments)} volunteers, {len(shelter_assignments)} shelters, "
        f"route={routing_decision}"
    )

    return {
        "resource_plan": resource_plan,
        "execution_trace": [trace],
        "routing_history": [],
        "messages": [HumanMessage(content=f"Resource allocation complete for {zone_id}")],
    }
