"""
RakshaSetu — Supervisor Debate Module
AutoGen-style debate for resolving inter-agent conflicts.
"""

import json
import logging
from app.shared.utils import get_llm
from app.agents.feedback_supervisor.prompts import (
    CONFLICT_RESOLVER_PROMPT,
    ESCALATION_ADVISOR_PROMPT,
)

logger = logging.getLogger(__name__)


def run_supervisor_debate(agent_summary: dict, conflicts: list[str]) -> dict:
    """
    Run a 2-agent debate to resolve supervisor-level conflicts.

    Agents:
    - ConflictResolver: Attempts to find compromises between conflicting agents
    - EscalationAdvisor: Argues whether escalation to human oversight is needed

    Args:
        agent_summary: Dict summarizing all agent outputs
        conflicts: List of conflict descriptions

    Returns:
        Dict with resolution, resolutions list, and escalation recommendation
    """
    llm = get_llm()

    context = f"""
AGENT OUTPUTS:
{json.dumps(agent_summary, indent=2)}

DETECTED CONFLICTS:
{json.dumps(conflicts, indent=2)}
"""

    # ----------------------------------------------------------
    # Conflict Resolver speaks
    # ----------------------------------------------------------
    resolver_input = f"""
{context}

Analyze these conflicts and propose resolutions for each one.
How can we reconcile the different agent outputs?
"""
    try:
        resolver_response = llm.invoke([
            {"role": "system", "content": CONFLICT_RESOLVER_PROMPT},
            {"role": "user", "content": resolver_input},
        ])
        resolver_position = resolver_response.content
    except Exception as e:
        resolver_position = f"[Resolver error: {e}] Recommend accepting majority agent consensus."
        logger.warning(f"   Conflict resolver error: {e}")

    # ----------------------------------------------------------
    # Escalation Advisor responds
    # ----------------------------------------------------------
    advisor_input = f"""
{context}

CONFLICT RESOLVER SAYS:
{resolver_position}

Given the conflicts and proposed resolutions, should this situation be
escalated to human oversight? Or can the automated system handle it?

Respond with JSON:
{{
    "resolution": "<summary of the final resolution>",
    "resolutions": ["<resolution for conflict 1>", "<resolution for conflict 2>", ...],
    "escalate_to_human": true/false,
    "reasoning": "<explanation>"
}}
"""
    try:
        advisor_response = llm.invoke([
            {"role": "system", "content": ESCALATION_ADVISOR_PROMPT},
            {"role": "user", "content": advisor_input},
        ])
        from app.shared.utils import from_json
        result = from_json(advisor_response.content)
    except Exception as e:
        logger.warning(f"   Escalation advisor error: {e}")
        result = {
            "resolution": "Debate inconclusive. Accepting zone analyst decision.",
            "resolutions": [f"Auto-resolved: {c}" for c in conflicts],
            "escalate_to_human": len(conflicts) >= 3,
            "reasoning": f"Advisor error ({e}), defaulting to conservative approach.",
        }

    return result
