"""
RakshaSetu Phase 4 — Non-Linear LangGraph Workflow
Fully decision-driven graph where EVERY transition is conditional.

Graph topology:
  START → triage
    triage →(decision)→ weather | analyst | log | supervisor
    weather →(decision)→ analyst | weather | supervisor
    analyst →(decision)→ resources | notifier | log | supervisor
    resources →(decision)→ notifier | supervisor
    notifier →(decision)→ feedback | notifier | supervisor
    feedback →(decision)→ analyst | notifier | supervisor  ← FEEDBACK LOOP
    supervisor →(decision)→ log | resources | analyst | notifier
    log → END

Key design:
  - ZERO static add_edge() calls between agent nodes
  - Only START→triage and log_and_end→END are fixed
  - Every agent-to-agent transition uses add_conditional_edges()
"""

import time
import logging
from langgraph.graph import StateGraph, START, END

from app.shared.state import AgentState
from app.agents.triage.agent import triage_node
from app.agents.weather.agent import weather_simulation_node
from app.agents.zone_analyst.agent import zone_analyst_node
from app.agents.resource_allocator.agent import resource_allocator_node
from app.agents.notifier.agent import notifier_node
from app.agents.feedback_supervisor.feedback_agent import feedback_node
from app.agents.feedback_supervisor.supervisor_agent import supervisor_node

from app.graph.routers import (
    route_from_triage,
    route_from_weather,
    route_from_analyst,
    route_from_resources,
    route_from_notifier,
    route_from_feedback,
    route_from_supervisor,
)

logger = logging.getLogger("raksha.graph")


# ── Terminal Node ─────────────────────────────────────────────

def log_and_end_node(state: AgentState) -> dict:
    """
    Terminal node: logs final pipeline summary and execution trace.
    """
    zone_id = state.get("zone_id", "?")
    trace_len = len(state.get("execution_trace", []))
    routing_len = len(state.get("routing_history", []))
    sup_interventions = state.get("supervisor_interventions", 0)
    feedback_loops = state.get("feedback_loop_count", 0)

    # Determine final outcome
    sup = state.get("supervisor_decision", {})
    analysis = state.get("zone_analysis", {})
    triage = state.get("triage_result", {})

    final_decision = (
        sup.get("final_decision")
        or analysis.get("decision")
        or triage.get("severity", "LOW")
    )

    summary = (
        f"Pipeline complete for zone {zone_id}: "
        f"decision={final_decision}, "
        f"trace_entries={trace_len}, "
        f"routing_steps={routing_len}, "
        f"feedback_loops={feedback_loops}, "
        f"supervisor_interventions={sup_interventions}"
    )
    logger.info(f"📋 {summary}")

    return {
        "execution_trace": [
            {
                "node": "log_and_end",
                "timestamp_enter": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "timestamp_exit": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "decision": f"COMPLETE: {final_decision}",
                "confidence": 1.0,
                "routed_to": "END",
                "duration_ms": 0,
                "state_snapshot": {
                    "zone_id": zone_id,
                    "feedback_loop_count": feedback_loops,
                    "supervisor_interventions": sup_interventions,
                },
            }
        ],
        "routing_history": [
            {
                "from": "log_and_end",
                "to": "END",
                "reason": summary,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        ],
        "messages": [],
    }


# ── Build the Graph ──────────────────────────────────────────

def build_workflow() -> StateGraph:
    """
    Construct the Phase 4 non-linear LangGraph StateGraph.
    Every edge is conditional — decision-driven transitions throughout.
    Returns the uncompiled StateGraph.
    """
    graph = StateGraph(AgentState)

    # ── Register ALL Nodes ────────────────────────────────
    graph.add_node("triage", triage_node)
    graph.add_node("weather_simulation", weather_simulation_node)
    graph.add_node("zone_analyst", zone_analyst_node)
    graph.add_node("resource_allocator", resource_allocator_node)
    graph.add_node("notifier", notifier_node)
    graph.add_node("feedback", feedback_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("log_and_end", log_and_end_node)

    # ── ENTRY: START → triage (only fixed entry) ──────────
    graph.add_edge(START, "triage")

    # ── 1. Triage → ? (decision-based) ────────────────────
    graph.add_conditional_edges(
        "triage",
        route_from_triage,
        {
            "weather_simulation": "weather_simulation",
            "zone_analyst": "zone_analyst",
            "log_and_end": "log_and_end",
            "supervisor": "supervisor",
        },
    )

    # ── 2. Weather → ? (decision-based) ──────────────────
    graph.add_conditional_edges(
        "weather_simulation",
        route_from_weather,
        {
            "zone_analyst": "zone_analyst",
            "weather_simulation": "weather_simulation",
            "supervisor": "supervisor",
        },
    )

    # ── 3. Zone Analyst → ? (decision-based) ─────────────
    graph.add_conditional_edges(
        "zone_analyst",
        route_from_analyst,
        {
            "resource_allocator": "resource_allocator",
            "notifier": "notifier",
            "log_and_end": "log_and_end",
            "supervisor": "supervisor",
        },
    )

    # ── 4. Resource Allocator → ? (decision-based) ───────
    graph.add_conditional_edges(
        "resource_allocator",
        route_from_resources,
        {
            "notifier": "notifier",
            "supervisor": "supervisor",
        },
    )

    # ── 5. Notifier → ? (decision-based) ─────────────────
    graph.add_conditional_edges(
        "notifier",
        route_from_notifier,
        {
            "feedback": "feedback",
            "notifier": "notifier",
            "supervisor": "supervisor",
        },
    )

    # ── 6. Feedback → ? (decision-based, FEEDBACK LOOP) ──
    graph.add_conditional_edges(
        "feedback",
        route_from_feedback,
        {
            "zone_analyst": "zone_analyst",   # Notifier → Feedback → Analyst loop
            "notifier": "notifier",           # Renotify path
            "supervisor": "supervisor",       # Success or escalate
        },
    )

    # ── 7. Supervisor → ? (decision-based, can override) ─
    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "log_and_end": "log_and_end",
            "resource_allocator": "resource_allocator",
            "zone_analyst": "zone_analyst",
            "notifier": "notifier",
        },
    )

    # ── TERMINAL: log_and_end → END (only fixed exit) ────
    graph.add_edge("log_and_end", END)

    logger.info("✅ Phase 4 non-linear LangGraph workflow built (all conditional edges)")
    return graph


def compile_workflow():
    """Build and compile the workflow into a runnable app."""
    workflow = build_workflow()
    app = workflow.compile()
    logger.info("✅ LangGraph workflow compiled and ready.")
    return app
