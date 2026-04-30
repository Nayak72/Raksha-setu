from app.services.state import state

def init_evacuations():
    state.evacuations = []
    for zone in state.zones:
        state.evacuations.append({
            "zone_id": zone["id"],
            "evacuated_count": 0
        })

def update_evacuations():
    # Evacuated count increases per cycle based on severity
    for evac in state.evacuations:
        zone = next((z for z in state.zones if z["id"] == evac["zone_id"]), None)
        if not zone:
            continue
            
        rate = 0
        if zone["severity"] == "critical":
            rate = 100
        elif zone["severity"] == "high":
            rate = 50
        elif zone["severity"] == "medium":
            rate = 20
        elif zone["severity"] == "low":
            rate = 5
            
        new_count = evac["evacuated_count"] + rate
        # Cannot exceed population
        evac["evacuated_count"] = min(new_count, zone["population"])
