from app.services.state import state
import random

def init_allocations():
    state.allocations = []
    for shelter in state.shelters:
        state.allocations.append({
            "shelter_id": shelter["id"],
            "food_units": 1000,
            "beds": shelter["capacity"],
            "medical_kits": 500,
            "rescue_teams": 2
        })

def update_allocations():
    # Allocate resources to shelters based on the severity of the zones around them
    # For simplicity, we just randomize a bit to simulate consumption/replenishment
    for alloc in state.allocations:
        # Simulate dynamic allocation
        alloc["food_units"] = max(0, alloc["food_units"] + random.randint(-50, 50))
        alloc["beds"] = max(0, alloc["beds"] + random.randint(-10, 10))
        alloc["medical_kits"] = max(0, alloc["medical_kits"] + random.randint(-5, 10))
        alloc["rescue_teams"] = max(0, alloc["rescue_teams"] + random.randint(-1, 1))
