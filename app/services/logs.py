"""Log storage for agent decisions."""
from app.services.state import state
from datetime import datetime, timezone


def init_logs():
    state.logs = []


def record_log(agent_name, zone_id, input_data, parameters_used,
               thresholds_checked, decision, outcome, reasoning):
    """Record a structured agent decision log entry."""
    if len(state.logs) > 1000:
        state.logs.pop(0)

    state.logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_name": agent_name,
        "zone_id": zone_id,
        "input_data": input_data,
        "parameters_used": parameters_used,
        "thresholds_checked": thresholds_checked,
        "decision": decision,
        "outcome": outcome,
        "reasoning": reasoning,
    })


def get_logs(zone_id=None, agent_name=None):
    logs = state.logs
    if zone_id:
        logs = [l for l in logs if l["zone_id"] == zone_id]
    if agent_name:
        logs = [l for l in logs if l["agent_name"] == agent_name]
    return logs[-200:]
