import json
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from app.rag.memory import get_memory_store

def seed_rag():
    seed_file = os.path.join(project_root, "model_pipeline", "datasets", "historical_rag_seed.json")
    if not os.path.exists(seed_file):
        print(f"Seed file not found: {seed_file}")
        print("Please run python model_pipeline/scripts/synthetic_generator.py first.")
        return

    with open(seed_file, "r") as f:
        records = json.load(f)

    store = get_memory_store()
    print(f"Loaded {len(records)} records from seed file.")

    for record in records:
        event_data = {
            "zone_id": "simulated_historical",
            "decision": record["decision"],
            "detection": record["state"],
            "reasoning": record["outcome"] + " " + record["reasoning"]
        }
        store.ingest_zone_event(event_data)
        
    print("✅ RAG Memory seeding completed!")

if __name__ == "__main__":
    seed_rag()
