import random
import uuid
import math
from app.services.state import state

def init_shelters():
    base_lat, base_lng = 12.9716, 77.5946
    state.shelters = []
    names = ["City Hall Shelter", "Community Center", "High School Gym", "Stadium Arena", "Red Cross Camp"]
    
    for i in range(5):
        cap = random.randint(500, 2000)
        state.shelters.append({
            "id": str(uuid.uuid4()),
            "name": names[i],
            "lat": base_lat + random.uniform(-0.08, 0.08),
            "lng": base_lng + random.uniform(-0.08, 0.08),
            "capacity": cap,
            "available_capacity": cap
        })

def update_shelters():
    # Shelters capacity is updated based on evacuations, handled elsewhere or simulate slight variation
    pass

def get_shelters_near(zone_id: str):
    # Find zone
    zone = next((z for z in state.zones if z["id"] == zone_id), None)
    if not zone:
        return []
    
    results = []
    for s in state.shelters:
        # Simple euclidean distance (not accurate for geo but good enough for simulation)
        dist = math.hypot(s["lat"] - zone["lat"], s["lng"] - zone["lng"])
        results.append({
            "shelter_id": s["id"],
            "name": s["name"],
            "distance": round(dist * 111, 2), # Approx to km
            "capacity": s["capacity"],
            "available_capacity": s["available_capacity"]
        })
        
    return sorted(results, key=lambda x: x["distance"])
