from app.services.state import state
from app.services.logs import record_log
from app.services.shelters import get_shelters_near

def run_agent_decisions():
    for zone in state.zones:
        # Inputs
        pop = zone["population"]
        damage = zone["damage_level"]
        alerts = zone["alert_count"]
        
        # Evac count
        evac_record = next((e for e in state.evacuations if e["zone_id"] == zone["id"]), None)
        current_evac = evac_record["evacuated_count"] if evac_record else 0
        
        # Shelter capacity nearby
        shelters = get_shelters_near(zone["id"])
        total_capacity = sum(s["available_capacity"] for s in shelters)
        
        inputs = {
            "population": pop,
            "damage_level": damage,
            "alert_count": alerts,
            "current_evac_count": current_evac,
            "shelter_capacity_nearby": total_capacity
        }
        
        # Parameters & Thresholds
        params = {
            "risk_weight": 0.8,
            "capacity_weight": 0.2
        }
        thresholds = {
            "evac_threshold": 0.6,
            "resource_threshold": 0.5
        }
        
        # Logic
        risk_score = (damage * params["risk_weight"]) + (alerts * 0.1) + (pop * 0.0001)
        
        evac_urgency = "LOW"
        if risk_score > thresholds["evac_threshold"]:
            evac_urgency = "HIGH"
        elif risk_score > 0.3:
            evac_urgency = "MEDIUM"
            
        resource_alloc = "minimal"
        if zone["severity"] == "critical":
            resource_alloc = "max"
        elif zone["severity"] == "high":
            resource_alloc = "moderate"
            
        route_req = "shortest" if evac_urgency == "HIGH" else "multiple"
        
        decision = {
            "priority_level": zone["severity"],
            "evacuation_urgency": evac_urgency,
            "resource_allocation": resource_alloc,
            "routing_request": route_req
        }
        
        # Reasoning
        reasoning = f"Zone marked {zone['severity']} due to damage ({damage}) and alerts ({alerts}). "
        if evac_urgency == "HIGH":
            reasoning += f"Evacuation prioritized due to high risk score ({round(risk_score, 2)}). "
        else:
            reasoning += "Evacuation not critical at this time. "
            
        reasoning += f"Resources allocated at {resource_alloc} level. "
        reasoning += f"Routing restricted to {route_req}."
        
        record_log(zone["id"], inputs, params, thresholds, decision, reasoning)
