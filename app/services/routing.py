from app.services.state import state
import random

def init_routes():
    # Base location (e.g. disaster management center)
    base_lat, base_lng = 12.9716, 77.5946
    state.routes = {}
    
    for zone in state.zones:
        # Generate 3-5 routes
        num_routes = random.randint(3, 5)
        routes = []
        shortest_idx = 0
        min_dist = float('inf')
        
        for i in range(num_routes):
            # Generate a random path
            dist = random.uniform(2.0, 15.0)
            if dist < min_dist:
                min_dist = dist
                shortest_idx = i
                
            routes.append({
                "path": [[base_lat, base_lng], [zone["lat"], zone["lng"]]], # Simplified straight line
                "distance": round(dist, 2),
                "time": int(dist * 5) # Assume 5 mins per km
            })
            
        state.routes[zone["id"]] = {
            "routes": routes,
            "shortest_route_index": shortest_idx
        }

def update_routes():
    # Routes don't change much unless a road is blocked, we can leave static or regenerate
    pass

def get_routes(zone_id: str):
    return state.routes.get(zone_id, {"routes": [], "shortest_route_index": 0})
