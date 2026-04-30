import asyncio
import traceback
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from app.db.listener import _run_graph_for_zone

async def run_demo():
    zone_id = "cc0a2353-6648-406d-a8e2-32e792bb5de0"
    trigger_event = {
        "zone_id": zone_id,
        "detection": {
            "crowd_density": 0.95,
            "flood_level": 0.7,
            "structural_damage": 0.4,
            "fire_detected": True,
            "confidence": 0.92,
            "vehicle_count": 12,
        }
    }
    
    try:
        await _run_graph_for_zone(zone_id, trigger_event)
        print("SUCCESS: All agents completed!")
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_demo())
