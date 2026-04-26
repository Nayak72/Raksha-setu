"""
RakshaSetu Phase 4 — Weather Simulation Agent (LangGraph Node)
Enhanced with routing_decision output and execution trace logging.

Pipeline:
1. get_previous_weather → retrieve last known state
2. get_zone_geography → terrain/elevation factors
3. Run stochastic simulation
4. LLM analyzes and adjusts
5. Determine routing_decision for non-linear graph
6. Returns structured WeatherOutput with routing hint
"""

import json
import logging
from langchain_core.messages import HumanMessage, SystemMessage

from app.shared.state import AgentState
from app.shared.utils import get_llm, from_json
from app.shared.tools import get_previous_weather, get_zone_geography
from app.shared.tracer import trace_entry, trace_exit
from app.agents.weather.simulation import simulate_weather
from app.agents.weather.prompts import WEATHER_SYSTEM_PROMPT
from app.rag.memory import get_memory_store

logger = logging.getLogger(__name__)


def weather_simulation_node(state: AgentState) -> dict:
    """
    LangGraph node: Weather Simulation Agent.
    Reads zone_id from state, simulates next weather, returns weather_data
    with a routing_decision for the non-linear graph.
    """
    zone_id = state["zone_id"]
    recheck_count = state.get("weather_recheck_count", 0)
    reasoning_steps = []
    tools_used = []

    trace = trace_entry("weather_simulation", state)
    logger.info(f"🌦️  Weather Agent started for zone: {zone_id} (recheck #{recheck_count})")

    # ------------------------------------------------------------------
    # Step 1: Retrieve previous weather
    # ------------------------------------------------------------------
    reasoning_steps.append("Step 1: Retrieving previous weather data from database.")
    try:
        prev_weather_raw = get_previous_weather.invoke(zone_id)
        prev_weather = json.loads(prev_weather_raw)
        tools_used.append("get_previous_weather")
    except Exception as e:
        logger.warning(f"   Previous weather retrieval failed: {e}")
        prev_weather = {"rainfall_mm": 10, "wind_speed_kmh": 15, "humidity_pct": 70, "temperature_c": 25}
        reasoning_steps.append(f"  → Fallback: using default weather (DB error: {e})")

    # ------------------------------------------------------------------
    # Step 2: Retrieve zone geography
    # ------------------------------------------------------------------
    reasoning_steps.append("Step 2: Retrieving zone geography and terrain data.")
    try:
        zone_geo_raw = get_zone_geography.invoke(zone_id)
        zone_geo = json.loads(zone_geo_raw)
        tools_used.append("get_zone_geography")
    except Exception as e:
        logger.warning(f"   Zone geography retrieval failed: {e}")
        zone_geo = {"terrain_type": "flat", "elevation_m": 500}
        reasoning_steps.append(f"  → Fallback: using default geography (DB error: {e})")

    # ------------------------------------------------------------------
    # Step 3: Run stochastic simulation
    # ------------------------------------------------------------------
    reasoning_steps.append("Step 3: Running stochastic weather simulation model.")
    sim_result = simulate_weather(prev_weather, zone_geo)
    reasoning_steps.append(
        f"  → Simulated rainfall: {sim_result['rainfall_mm']}mm, "
        f"wind: {sim_result['wind_speed_kmh']}km/h, "
        f"humidity: {sim_result['humidity_pct']}%"
    )

    # ------------------------------------------------------------------
    # Step 3.5: Retrieve similar past weather events from RAG
    # ------------------------------------------------------------------
    reasoning_steps.append("Step 3.5: Retrieving similar past weather events from RAG memory.")
    rag_weather_context = ""
    try:
        rag_store = get_memory_store()
        sim_severity = sim_result.get("severity", "MEDIUM")
        rag_results = rag_store.retrieve_weather_history(
            query=f"Weather in zone {zone_id}: severity={sim_severity}, rainfall={sim_result['rainfall_mm']}mm",
            n_results=3,
            zone_filter=zone_id,
        )
        past_docs = rag_results.get("documents", [[]])[0]
        if past_docs:
            rag_weather_context = "\nPast similar weather events:\n" + "\n".join(
                f"  - {doc}" for doc in past_docs
            )
            reasoning_steps.append(f"  → Found {len(past_docs)} similar past weather events.")
            tools_used.append("rag_weather_retrieve")
        else:
            reasoning_steps.append("  → No similar past weather events found.")
    except Exception as e:
        logger.warning(f"   RAG weather retrieval failed: {e}")
        reasoning_steps.append(f"  → RAG retrieval failed ({e}), proceeding without history.")

    # ------------------------------------------------------------------
    # Step 4: LLM reasoning — adjust + classify severity
    # ------------------------------------------------------------------
    reasoning_steps.append("Step 4: LLM analyzing simulation output and adjusting based on context.")

    feedback_context = ""
    if state.get("feedback") and state["feedback"].get("action") == "re_trigger":
        feedback_context = (
            "\n\nIMPORTANT FEEDBACK: The previous simulation was re-triggered because "
            "the situation worsened. Please factor in escalation in your analysis."
        )
        reasoning_steps.append("  → Incorporating feedback: previous round triggered re-evaluation.")

    llm = get_llm()
    llm_input = f"""
Previous weather: {json.dumps(prev_weather)}
Zone geography: {json.dumps(zone_geo)}
Simulation output: {json.dumps(sim_result)}
{feedback_context}
{rag_weather_context}

Analyze the weather simulation and provide your assessment as JSON:
{{
    "rainfall": <adjusted rainfall in mm>,
    "wind_speed": <wind speed km/h>,
    "humidity": <humidity %>,
    "temperature": <temperature °C>,
    "severity": "<LOW|MEDIUM|HIGH|CRITICAL>",
    "confidence": <0.0 to 1.0>,
    "adjustment_reasoning": "<why you adjusted or kept the simulation values>"
}}
"""
    try:
        response = llm.invoke([
            SystemMessage(content=WEATHER_SYSTEM_PROMPT),
            HumanMessage(content=llm_input),
        ])
        llm_output = from_json(response.content)
        reasoning_steps.append(f"  → LLM adjustment: {llm_output.get('adjustment_reasoning', 'N/A')}")
    except Exception as e:
        logger.warning(f"   LLM call failed, using raw simulation: {e}")
        reasoning_steps.append(f"  → LLM call failed ({e}), using raw simulation output.")
        llm_output = {
            "rainfall": sim_result["rainfall_mm"],
            "wind_speed": sim_result["wind_speed_kmh"],
            "humidity": sim_result["humidity_pct"],
            "temperature": sim_result["temperature_c"],
            "severity": sim_result["severity"],
            "confidence": 0.6,
        }

    # ------------------------------------------------------------------
    # Step 5: Determine routing decision (Phase 4 — non-linear)
    # ------------------------------------------------------------------
    reasoning_steps.append("Step 5: Determining routing decision for non-linear graph.")

    severity = llm_output.get("severity", "LOW")
    if isinstance(severity, dict):
        severity = severity.get("severity", "LOW")
    
    confidence = llm_output.get("confidence", 0.7)
    if isinstance(confidence, dict):
        confidence = confidence.get("confidence", 0.7)
        
    rainfall = llm_output.get("rainfall", sim_result["rainfall_mm"])
    if isinstance(rainfall, dict):
        rainfall = next(iter(rainfall.values())) if rainfall else sim_result["rainfall_mm"]
        
    wind_speed = llm_output.get("wind_speed", sim_result["wind_speed_kmh"])
    if isinstance(wind_speed, dict):
        wind_speed = next(iter(wind_speed.values())) if wind_speed else sim_result["wind_speed_kmh"]
        
    humidity = llm_output.get("humidity", sim_result["humidity_pct"])
    if isinstance(humidity, dict):
        humidity = next(iter(humidity.values())) if humidity else sim_result["humidity_pct"]
        
    temperature = llm_output.get("temperature", sim_result["temperature_c"])
    if isinstance(temperature, dict):
        temperature = next(iter(temperature.values())) if temperature else sim_result["temperature_c"]

    # Anomaly detection: extreme values that seem unrealistic
    is_anomaly = (rainfall > 200 and confidence < 0.5) or (severity == "CRITICAL" and confidence < 0.4)

    if is_anomaly and recheck_count < 2:
        routing_decision = "needs_recheck"
        reasoning_steps.append(f"  → ANOMALY: extreme values with low confidence → recheck")
    elif is_anomaly and recheck_count >= 2:
        routing_decision = "anomaly_detected"
        reasoning_steps.append(f"  → ANOMALY persists after {recheck_count} rechecks → supervisor")
    else:
        routing_decision = "proceed_to_analyst"
        reasoning_steps.append(f"  → Normal flow → proceed to zone analyst")

    # ------------------------------------------------------------------
    # Compose output
    # ------------------------------------------------------------------
    weather_output = {
        "zone": zone_id,
        "rainfall": float(rainfall),
        "wind_speed": float(wind_speed),
        "humidity": float(humidity),
        "temperature": float(temperature),
        "severity": str(severity),
        "reasoning_steps": reasoning_steps,
        "tools_used": tools_used,
        "confidence": float(confidence),
        "routing_decision": routing_decision,
    }

    trace_exit(trace, decision=f"severity={severity}", confidence=confidence, routed_to=routing_decision)

    # ------------------------------------------------------------------
    # Step 6: Store weather event in RAG memory
    # ------------------------------------------------------------------
    try:
        rag_store = get_memory_store()
        rag_store.ingest_weather_event(weather_output)
        logger.info(f"🌦️  Weather event stored in RAG memory for zone {zone_id}")
    except Exception as e:
        logger.warning(f"   RAG weather ingestion failed: {e}")

    logger.info(f"🌦️  Weather Agent complete → severity={severity}, route={routing_decision}")

    return {
        "weather_data": weather_output,
        "weather_recheck_count": recheck_count + 1 if routing_decision == "needs_recheck" else recheck_count,
        "execution_trace": [trace],
        "routing_history": [],
        "messages": [HumanMessage(content=f"Weather simulation complete for {zone_id}: severity={severity}")],
    }
