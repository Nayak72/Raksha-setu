"""
RakshaSetu Phase 4 — Zone Analyst Agent (LangGraph Node)
Enhanced with routing_decision output and execution trace.

Multi-step reasoning:
  Step 1 → analyze YOLO detection data
  Step 2 → compare with historical events (RAG)
  Step 3 → analyze trends (weather + detection)
  Step 4 → decide action via AutoGen debate (Risk vs Safety vs Planner)
  Step 5 → determine routing decision for non-linear graph
"""

import json
import logging
from langchain_core.messages import HumanMessage, SystemMessage

from app.shared.state import AgentState
from app.shared.utils import get_llm, from_json
from app.shared.tools import get_zone_history, get_weather_trend
from app.shared.tracer import trace_entry, trace_exit
from app.agents.zone_analyst.rag import ZoneRAG
from app.agents.zone_analyst.debate import run_internal_debate
from app.agents.zone_analyst.prompts import ZONE_ANALYST_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Singleton RAG instance
_rag = None


def _get_rag():
    global _rag
    if _rag is None:
        _rag = ZoneRAG()
    return _rag


def zone_analyst_node(state: AgentState) -> dict:
    """
    LangGraph node: Zone Analyst Agent.
    Reads weather_data and detection_data, produces zone_analysis
    with routing_decision for non-linear graph.
    """
    zone_id = state["zone_id"]
    weather_data = state.get("weather_data") or {}
    detection_data = state.get("detection_data") or {}
    reasoning_steps = []
    tools_used = []

    trace = trace_entry("zone_analyst", state)
    logger.info(f"🔍 Zone Analyst started for zone: {zone_id}")

    # ==================================================================
    # Step 1: Analyze YOLO detection data
    # ==================================================================
    reasoning_steps.append("Step 1: Analyzing YOLO detection data for the zone.")

    crowd_density = detection_data.get("crowd_density", 0)
    flood_level = detection_data.get("flood_level", 0)
    structural_damage = detection_data.get("structural_damage", 0)
    fire_detected = detection_data.get("fire_detected", False)

    detection_summary = (
        f"Crowd density: {crowd_density:.2f}, Flood level: {flood_level:.2f}, "
        f"Structural damage: {structural_damage:.2f}, Fire: {fire_detected}, "
        f"Vehicles: {detection_data.get('vehicle_count', 0)}, "
        f"Detection confidence: {detection_data.get('confidence', 0):.2f}"
    )
    reasoning_steps.append(f"  → Detection summary: {detection_summary}")

    # ==================================================================
    # Step 2: Retrieve past events from RAG (ChromaDB)
    # ==================================================================
    reasoning_steps.append("Step 2: Retrieving comprehensive context from RAG memory.")

    rag_context = {}
    retrieved_context = []
    rag_prompt_context = ""
    try:
        rag = _get_rag()
        # Get full context: weather history + detection history + zone events
        rag_context = rag.get_full_context(
            zone_id=zone_id,
            current_weather=weather_data,
            current_detection=detection_data,
        )
        tools_used.append("rag_retrieve_full_context")

        # Extract documents for backward compatibility
        for item in rag_context.get("zone_events", []):
            retrieved_context.append(item.get("document", ""))
        for item in rag_context.get("weather_history", []):
            retrieved_context.append(item.get("document", ""))
        for item in rag_context.get("detection_history", []):
            retrieved_context.append(item.get("document", ""))

        # Format context for LLM prompt injection
        rag_prompt_context = rag.format_context_for_prompt(rag_context)
    except Exception as e:
        logger.warning(f"   RAG retrieval failed: {e}")
        retrieved_context = []
        rag_prompt_context = "No historical context available."
        reasoning_steps.append(f"  → RAG retrieval failed ({e}), proceeding without historical context.")

    n_weather_hist = len(rag_context.get("weather_history", []))
    n_detection_hist = len(rag_context.get("detection_history", []))
    n_zone_events = len(rag_context.get("zone_events", []))
    reasoning_steps.append(
        f"  → Retrieved {n_weather_hist} weather events, "
        f"{n_detection_hist} detection events, "
        f"{n_zone_events} zone analysis decisions from RAG memory."
    )

    # ==================================================================
    # Step 3: Analyze trends (zone history + weather trend)
    # ==================================================================
    reasoning_steps.append("Step 3: Analyzing detection and weather trends.")

    try:
        zone_history_raw = get_zone_history.invoke(zone_id)
        zone_history = json.loads(zone_history_raw)
        tools_used.append("get_zone_history")
    except Exception as e:
        logger.warning(f"   Zone history failed: {e}")
        zone_history = []

    try:
        weather_trend_raw = get_weather_trend.invoke({"zone_id": zone_id, "hours": 24})
        weather_trend = json.loads(weather_trend_raw)
        tools_used.append("get_weather_trend")
    except Exception as e:
        logger.warning(f"   Weather trend failed: {e}")
        weather_trend = []

    if isinstance(zone_history, list) and len(zone_history) >= 2:
        crowd_trend = zone_history[0].get("crowd_density", 0) - zone_history[-1].get("crowd_density", 0)
        flood_trend = zone_history[0].get("flood_level", 0) - zone_history[-1].get("flood_level", 0)
        reasoning_steps.append(
            f"  → Trends: crowd density {'↑' if crowd_trend > 0 else '↓'} ({crowd_trend:+.2f}), "
            f"flood level {'↑' if flood_trend > 0 else '↓'} ({flood_trend:+.2f})"
        )
    else:
        reasoning_steps.append("  → Insufficient history for trend analysis.")

    # ==================================================================
    # Step 4: AutoGen internal debate → final decision
    # ==================================================================
    reasoning_steps.append("Step 4: Running internal debate (Risk Agent vs Safety Agent vs Planner Agent).")

    debate_context = {
        "zone_id": zone_id,
        "detection_data": detection_data,
        "weather_data": weather_data,
        "zone_history_summary": zone_history[:3] if isinstance(zone_history, list) and zone_history else [],
        "rag_context": retrieved_context[:5],
        "rag_summary": rag_context.get("summary", ""),
        "detection_summary": detection_summary,
    }

    try:
        debate_result = run_internal_debate(debate_context)
        reasoning_steps.append(f"  → Debate concluded: {debate_result.get('summary', 'N/A')}")
    except Exception as e:
        logger.warning(f"   Debate failed, falling back to LLM: {e}")
        reasoning_steps.append(f"  → Debate failed ({e}), using direct LLM analysis.")
        debate_result = None

    # ==================================================================
    # Step 5: LLM synthesis → decision
    # ==================================================================
    reasoning_steps.append("Step 5: LLM synthesizing all analysis into final decision.")

    llm = get_llm()
    synthesis_input = f"""
Zone: {zone_id}
Detection: {detection_summary}
Weather: severity={weather_data.get('severity', 'UNKNOWN')}, rainfall={weather_data.get('rainfall', 0)}mm

--- RAG HISTORICAL CONTEXT ---
{rag_prompt_context}
--- END HISTORICAL CONTEXT ---

Debate result: {json.dumps(debate_result) if debate_result else 'Debate unavailable — use your own analysis'}

Synthesize all information including the historical context and provide your decision as JSON:
{{
    "decision": "<EVACUATE|ALERT|MONITOR|DEPLOY_RESOURCES|STANDBY>",
    "priority_score": <0.0 to 1.0, where 1.0 is highest priority>,
    "confidence": <0.0 to 1.0>,
    "reasoning": "<brief explanation referencing both current data and historical patterns>"
}}
"""
    try:
        response = llm.invoke([
            SystemMessage(content=ZONE_ANALYST_SYSTEM_PROMPT),
            HumanMessage(content=synthesis_input),
        ])
        llm_decision = from_json(response.content)
    except Exception as e:
        logger.warning(f"   LLM synthesis failed: {e}")
        composite = crowd_density * 0.3 + flood_level * 0.4 + structural_damage * 0.3
        if composite >= 0.6:
            decision = "EVACUATE"
        elif composite >= 0.4:
            decision = "DEPLOY_RESOURCES"
        elif composite >= 0.2:
            decision = "ALERT"
        else:
            decision = "MONITOR"
        llm_decision = {
            "decision": decision,
            "priority_score": round(composite, 2),
            "confidence": 0.5,
            "reasoning": f"Fallback heuristic (LLM unavailable): composite score={composite:.2f}",
        }

    # Store event in RAG for future retrieval
    try:
        rag = _get_rag()
        rag.ingest_event({
            "zone_id": zone_id,
            "decision": llm_decision.get("decision"),
            "detection": detection_data,
            "weather_severity": weather_data.get("severity"),
            "priority": llm_decision.get("priority_score"),
        })
    except Exception as e:
        logger.warning(f"   RAG ingestion failed: {e}")

    # ==================================================================
    # Step 6: Determine routing decision (Phase 4 — non-linear)
    # ==================================================================
    reasoning_steps.append("Step 6: Determining routing decision for non-linear graph.")

    decision = llm_decision.get("decision", "MONITOR")
    confidence = llm_decision.get("confidence", 0.5)

    # Low confidence → route to supervisor for validation
    if confidence < 0.3:
        routing_decision = "conflict"
        reasoning_steps.append(f"  → Low confidence ({confidence}) → routing to supervisor")
    elif decision in ("EVACUATE", "DEPLOY_RESOURCES"):
        routing_decision = "evacuate" if decision == "EVACUATE" else "deploy"
        reasoning_steps.append(f"  → {decision} → routing to resource_allocator")
    elif decision == "ALERT":
        routing_decision = "alert_only"
        reasoning_steps.append(f"  → ALERT → routing to notifier (skip resources)")
    else:
        routing_decision = "monitor"
        reasoning_steps.append(f"  → {decision} → routing to log_and_end")

    zone_analysis = {
        "decision": decision,
        "priority_score": llm_decision.get("priority_score", 0.0),
        "reasoning_steps": reasoning_steps,
        "tools_used": tools_used,
        "retrieved_context": retrieved_context,
        "confidence": confidence,
        "routing_decision": routing_decision,
    }

    trace_exit(trace, decision=decision, confidence=confidence, routed_to=routing_decision)

    logger.info(
        f"🔍 Zone Analyst complete → decision={decision}, route={routing_decision}, "
        f"confidence={confidence}"
    )

    return {
        "zone_analysis": zone_analysis,
        "execution_trace": [trace],
        "routing_history": [],
        "messages": [HumanMessage(content=f"Zone analysis complete for {zone_id}: decision={decision}")],
    }
