from app.services.state import state
from datetime import datetime, timezone

def init_logs():
    state.logs = []

def record_log(zone_id, inputs, parameters, thresholds, decision, reasoning):
    # Keep only the latest 1000 logs
    if len(state.logs) > 1000:
        state.logs.pop(0)
        
    state.logs.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zone_id": zone_id,
        "inputs": inputs,
        "parameters": parameters,
        "thresholds": thresholds,
        "decision": decision,
        "reasoning": reasoning
    })

def get_logs(zone_id=None, severity=None):
    # Filter logs if required
    logs = state.logs
    if zone_id:
        logs = [log for log in logs if log["zone_id"] == zone_id]
    
    # We could filter by severity if we put it in the log structure
    # For now return the last 100
    return logs[-100:]
