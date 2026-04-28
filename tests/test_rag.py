import logging
logging.basicConfig(level=logging.DEBUG)

from app.rag.memory import get_memory_store

def test():
    store = get_memory_store()
    event = {
        "zone_id": "19.0760, 72.8777",
        "crowd_density": 80,
        "fire_detected": True,
        "flood_detected": False,
        "structural_damage": 0,
        "vehicle_count": 0,
        "confidence": 0.9,
    }
    try:
        store.ingest_detection_event(event)
        print("Success!")
    except Exception as e:
        import traceback
        traceback.print_exc()

test()
