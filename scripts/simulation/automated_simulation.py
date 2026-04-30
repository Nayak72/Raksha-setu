import time
import requests
import random
from datetime import datetime

# URL of your local FastAPI backend
API_URL = "http://127.0.0.1:8000/api/v1/detect"

import sys
import os

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from dotenv import load_dotenv

load_dotenv(os.path.join(project_root, ".env"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def get_zones():
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/zones?select=id", headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        })
        return [z['id'] for z in res.json()]
    except:
        # Fallback zones
        return ["cc0a2353-6648-406d-a8e2-32e792bb5de0"]

try:
    from model_pipeline.scripts.synthetic_generator import DisasterDataGenerator
    generator = DisasterDataGenerator()
except ImportError:
    generator = None

def trigger_simulation():
    zones = get_zones()
    zone_id = random.choice(zones) if zones else "cc0a2353-6648-406d-a8e2-32e792bb5de0"
    
    # Pick a random scenario and maintain state
    scenario = random.choices(["calm", "flood_event", "fire_event"], weights=[0.6, 0.2, 0.2])[0]
    
    if generator:
        detection_data = generator.generate_detection_data(scenario)
        weather_data = generator.generate_weather_data(scenario)
        
        crowd = int(detection_data["crowd_density"] * 100)
        flood_level = detection_data["flood_level"]
        fire = detection_data["fire_detected"]
        vehicles = detection_data["vehicle_count"]
        damage = detection_data["structural_damage"]
        confidence = detection_data["confidence"]
    else:
        # Fallback to pure random
        flood_level = round(random.uniform(0.1, 0.9), 2)
        fire = random.choice([True, False])
        crowd = random.randint(20, 200)
        vehicles = random.randint(5, 50)
        damage = round(random.uniform(0.1, 0.8), 2)
        confidence = round(random.uniform(0.85, 0.99), 2)
    
    payload = {
        "zone_id": zone_id,
        "count": crowd,
        "metadata": {
            "flood_level": flood_level,
            "structural_damage": damage,
            "fire_detected": fire,
            "confidence": confidence,
            "vehicle_count": vehicles,
            "scenario": scenario,
            "source": random.choice(["drone_camera", "cctv", "satellite"])
        }
    }
    
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Triggering {scenario.upper()} in zone {zone_id}...")
        response = requests.post(API_URL, json=payload, timeout=10)
        
        if response.status_code in [200, 202]:
            print(f"✅ Simulation successful: AI Agents are now processing the threat.")
        else:
            print(f"⚠️ Failed to trigger: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error contacting API: {e}. Is the backend running on port 8001?")

if __name__ == "__main__":
    print("==================================================")
    print("🚀 RakshaSetu Automated Disaster Simulator Started")
    print("==================================================")
    print("This script will automatically trigger a disaster simulation")
    print("every 2 minutes. Keep your dashboard open to see the AI")
    print("agents dynamically generate plans and update analytics!")
    print("Press Ctrl+C to stop.\n")
    
    # Trigger first one immediately
    trigger_simulation()
    
    # Loop every 120 seconds (2 minutes)
    while True:
        try:
            time.sleep(120)
            trigger_simulation()
        except KeyboardInterrupt:
            print("\n🛑 Simulation stopped.")
            break
