"""
RakshaSetu — AutoGen Internal Debate Module for Zone Analyst
Implements a 3-agent debate: Risk Agent vs Safety Agent vs Planner Agent.

The debate runs for a configurable number of rounds, then the Planner
synthesizes a final decision.
"""

import json
import logging
from app.shared.utils import get_llm
from app.agents.zone_analyst.prompts import (
    RISK_AGENT_PROMPT,
    SAFETY_AGENT_PROMPT,
    PLANNER_AGENT_PROMPT,
)

logger = logging.getLogger(__name__)

# Number of debate rounds
DEBATE_ROUNDS = 2


def run_internal_debate(context: dict, rounds: int = DEBATE_ROUNDS) -> dict:
    """
    Run AutoGen-style internal debate between 3 agents.

    Agents:
    - RiskAgent: Evaluates worst-case scenarios, argues for caution
    - SafetyAgent: Evaluates current safety margins, argues for measured response
    - PlannerAgent: Synthesizes perspectives into actionable decision

    Args:
        context: Dict with zone_id, detection_data, weather_data, zone_history, rag_context
        rounds: Number of debate rounds

    Returns:
        Dict with final decision, summary, and debate transcript
    """
    llm = get_llm()
    context_str = json.dumps(context, default=str, indent=2)

    debate_transcript = []

    # Initial positions
    risk_position = ""
    safety_position = ""
    planner_synthesis = ""

    for round_num in range(1, rounds + 1):
        logger.info(f"   Debate round {round_num}/{rounds}")

        # ----------------------------------------------------------
        # Risk Agent speaks
        # ----------------------------------------------------------
        risk_input = f"""
SITUATION CONTEXT:
{context_str}

{"PREVIOUS ROUND - Safety Agent said: " + safety_position if safety_position else "This is the opening round."}
{"PREVIOUS ROUND - Planner said: " + planner_synthesis if planner_synthesis else ""}

Analyze the worst-case risks. What is the maximum danger this zone faces?
Provide your risk assessment and recommended action.
"""
        try:
            risk_response = llm.invoke([
                {"role": "system", "content": RISK_AGENT_PROMPT},
                {"role": "user", "content": risk_input},
            ])
            risk_position = risk_response.content
        except Exception as e:
            risk_position = f"[Risk Agent error: {e}] High risk assumed due to uncertainty."
            logger.warning(f"   Risk agent error: {e}")

        debate_transcript.append({
            "round": round_num,
            "agent": "RiskAgent",
            "position": risk_position[:500],
        })

        # ----------------------------------------------------------
        # Safety Agent responds
        # ----------------------------------------------------------
        safety_input = f"""
SITUATION CONTEXT:
{context_str}

RISK AGENT SAYS (Round {round_num}):
{risk_position}

{"PREVIOUS ROUND - Planner said: " + planner_synthesis if planner_synthesis else ""}

Counter-analyze the risk assessment. Are the risks overestimated?
What are the current safety margins? What measured response is appropriate?
"""
        try:
            safety_response = llm.invoke([
                {"role": "system", "content": SAFETY_AGENT_PROMPT},
                {"role": "user", "content": safety_input},
            ])
            safety_position = safety_response.content
        except Exception as e:
            safety_position = f"[Safety Agent error: {e}] Moderate safety margins assumed."
            logger.warning(f"   Safety agent error: {e}")

        debate_transcript.append({
            "round": round_num,
            "agent": "SafetyAgent",
            "position": safety_position[:500],
        })

        # ----------------------------------------------------------
        # Planner Agent synthesizes
        # ----------------------------------------------------------
        planner_input = f"""
SITUATION CONTEXT:
{context_str}

RISK AGENT (Round {round_num}):
{risk_position}

SAFETY AGENT (Round {round_num}):
{safety_position}

Synthesize both perspectives. Make a concrete decision.
Respond ONLY with JSON:
{{
    "decision": "<EVACUATE|ALERT|MONITOR|DEPLOY_RESOURCES|STANDBY>",
    "priority_score": <0.0 to 1.0>,
    "confidence": <0.0 to 1.0>,
    "summary": "<brief synthesis of the debate>"
}}
"""
        try:
            planner_response = llm.invoke([
                {"role": "system", "content": PLANNER_AGENT_PROMPT},
                {"role": "user", "content": planner_input},
            ])
            planner_synthesis = planner_response.content

            debate_transcript.append({
                "round": round_num,
                "agent": "PlannerAgent",
                "position": planner_synthesis[:500],
            })
        except Exception as e:
            planner_synthesis = json.dumps({
                "decision": "ALERT",
                "priority_score": 0.5,
                "confidence": 0.4,
                "summary": f"Planner error ({e}), defaulting to ALERT.",
            })
            logger.warning(f"   Planner agent error: {e}")

    # Parse final planner decision
    try:
        from app.shared.utils import from_json
        final_decision = from_json(planner_synthesis)
    except Exception:
        final_decision = {
            "decision": "ALERT",
            "priority_score": 0.5,
            "confidence": 0.4,
            "summary": "Could not parse planner output, defaulting to ALERT.",
        }

    final_decision["debate_transcript"] = debate_transcript
    return final_decision
