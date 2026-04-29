import random
import uuid
from app.services.state import state

def init_zones():
    # Initialize some dummy zones based on Bangalore coordinates
    base_lat, base_lng = 12.9716, 77.5946
    state.zones = []
    for i in range(5):
        damage = random.uniform(0.1, 0.9)
        alerts = random.randint(0, 20)
        
        severity = "low"
        if damage > 0.75 or alerts > 15:
            severity = "critical"
        elif damage > 0.5:
            severity = "high"
        elif damage > 0.25:
            severity = "medium"
            
        state.zones.append({
            "id": str(uuid.uuid4()),
            "lat": base_lat + random.uniform(-0.05, 0.05),
            "lng": base_lng + random.uniform(-0.05, 0.05),
            "population": random.randint(1000, 10000),
            "damage_level": round(damage, 2),
            "alert_count": alerts,
            "severity": severity
        })

def update_zones():
    # Slightly vary parameters each cycle to make it dynamic
    for zone in state.zones:
        # Damage might increase slightly
        if random.random() > 0.8 and zone["damage_level"] < 1.0:
            zone["damage_level"] = min(1.0, zone["damage_level"] + random.uniform(0.01, 0.05))
            zone["damage_level"] = round(zone["damage_level"], 2)
            
        # Alerts might go up or down
        zone["alert_count"] = max(0, zone["alert_count"] + random.randint(-2, 3))
        
        # Re-evaluate severity
        damage = zone["damage_level"]
        alerts = zone["alert_count"]
        
        if damage > 0.75 or alerts > 15:
            zone["severity"] = "critical"
        elif damage > 0.5:
            zone["severity"] = "high"
        elif damage > 0.25:
            zone["severity"] = "medium"
        else:
            zone["severity"] = "low"
