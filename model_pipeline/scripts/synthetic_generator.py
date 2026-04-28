import random
import math
import json
import uuid
import numpy as np

class DisasterDataGenerator:
    """
    Generates mathematically realistic synthetic data for RakshaSetu simulation.
    Uses stochastic processes to prevent unrealistic jumps.
    """
    def __init__(self):
        # State tracking for continuous random walks
        self.state = {
            "flood_level": 0.0,
            "rain_mm": 0.0,
            "wind_kmh": 10.0,
            "temperature_c": 25.0,
            "humidity_pct": 50.0
        }

    def generate_detection_data(self, scenario="calm"):
        """Generates YOLOv8 detection metadata mapped to composite scores."""
        # Poisson distribution for realistic crowd clustering
        lam = 85 if scenario in ["flood_event", "fire_event"] else 5
        crowd_density = min(1.0, np.random.poisson(lam) / 100.0) 
        
        # Determine base parameters
        if scenario == "flood_event":
            # Continuous random walk for flood level
            self.state["flood_level"] = min(1.0, max(0.0, self.state["flood_level"] + random.uniform(0.05, 0.15)))
            fire_detected = False
            # Structural damage correlates with flood level over time
            structural_damage = min(1.0, self.state["flood_level"] * random.uniform(0.5, 0.9))
        elif scenario == "fire_event":
            self.state["flood_level"] = 0.0
            fire_detected = True
            structural_damage = random.uniform(0.3, 1.0)
            crowd_density = max(0.0, crowd_density - random.uniform(0.1, 0.4)) # People fleeing
        else:
            self.state["flood_level"] = max(0.0, self.state["flood_level"] - random.uniform(0.01, 0.05))
            fire_detected = random.random() < 0.05 # 5% chance of random fire anomaly
            structural_damage = random.uniform(0.0, 0.05)

        vehicle_count = int(random.gauss(30, 10))
        
        return {
            "crowd_density": round(crowd_density, 3),
            "flood_level": round(self.state["flood_level"], 3),
            "fire_detected": fire_detected,
            "structural_damage": round(structural_damage, 3),
            "vehicle_count": max(0, vehicle_count),
            "confidence": round(random.uniform(0.75, 0.98), 2)
        }

    def generate_weather_data(self, scenario="calm"):
        """Generates stochastic weather evolution using Markov chains and Gaussian noise."""
        if scenario == "flood_event":
            self.state["rain_mm"] += random.uniform(5.0, 20.0)
            self.state["humidity_pct"] = min(100.0, self.state["humidity_pct"] + random.uniform(2.0, 5.0))
        elif scenario == "fire_event":
            self.state["rain_mm"] = 0.0
            self.state["humidity_pct"] = max(10.0, self.state["humidity_pct"] - random.uniform(5.0, 15.0))
            self.state["wind_kmh"] += random.uniform(5.0, 15.0)
            self.state["temperature_c"] += random.uniform(1.0, 3.0)
        else:
            # Revert to baseline
            self.state["rain_mm"] *= 0.5
            self.state["wind_kmh"] = max(5.0, self.state["wind_kmh"] - random.uniform(1.0, 5.0))
            self.state["humidity_pct"] = min(60.0, max(40.0, self.state["humidity_pct"] + random.uniform(-2, 2)))
            self.state["temperature_c"] = min(30.0, max(20.0, self.state["temperature_c"] + random.uniform(-1, 1)))
            
        severity_score = min(1.0, (self.state["rain_mm"] / 100 * 0.5) + (self.state["wind_kmh"] / 100 * 0.3) + (self.state["humidity_pct"] / 100 * 0.2))

        return {
            "rainfall_mm": round(self.state["rain_mm"], 2),
            "wind_kmh": round(self.state["wind_kmh"], 2),
            "humidity_pct": round(self.state["humidity_pct"], 2),
            "temperature_c": round(self.state["temperature_c"], 2),
            "severity_score": round(severity_score, 3)
        }

def generate_historical_rag_data(num_records=50):
    """Generates a JSON file with historical decisions to seed the ChromaDB vector database."""
    records = []
    for _ in range(num_records):
        flood = random.uniform(0.0, 1.0)
        rain = random.uniform(0.0, 200.0)
        crowd = random.uniform(0.0, 1.0)
        fire = random.choice([True, False])
        
        # Simple heuristic to determine historical decision
        composite = (flood * 0.4) + (crowd * 0.3) + (0.1 if fire else 0.0)
        
        if composite > 0.6 or fire:
            decision = "EVACUATE"
            outcome = "SUCCESS: Casualties avoided due to rapid response."
        elif composite > 0.3:
            decision = "DEPLOY_RESOURCES"
            outcome = "SUCCESS: Shelters opened, supplies delivered."
        else:
            decision = "MONITOR"
            outcome = "SUCCESS: Threat dissipated."
            
        record = {
            "id": str(uuid.uuid4()),
            "state": {
                "flood_level": round(flood, 2),
                "rainfall_mm": round(rain, 1),
                "crowd_density": round(crowd, 2),
                "fire_detected": fire
            },
            "decision": decision,
            "outcome": outcome,
            "reasoning": f"Based on historical threshold analysis where composite risk was {round(composite, 2)}."
        }
        records.append(record)
        
    with open("model_pipeline/datasets/historical_rag_seed.json", "w") as f:
        json.dump(records, f, indent=2)
    print(f"✅ Generated {num_records} historical RAG records at model_pipeline/datasets/historical_rag_seed.json")

if __name__ == "__main__":
    generator = DisasterDataGenerator()
    print("Testing Generation Pipeline...")
    print("Calm:", generator.generate_detection_data("calm"))
    print("Flood:", generator.generate_detection_data("flood_event"))
    print("Weather:", generator.generate_weather_data("flood_event"))
    
    generate_historical_rag_data()
