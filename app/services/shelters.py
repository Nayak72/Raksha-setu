"""
Shelter service — geographically consistent shelter placement near disaster zones.

Shelters are placed:
  • Within realistic distance (3–15 km) of disaster zones
  • OUTSIDE the immediate disaster epicenter
  • At logically safe but accessible locations (schools, stadiums, community halls)

Each zone is assigned 2–4 nearby shelters.
"""
import uuid
import math
from app.services.state import state


# ── Pre-defined shelter locations near Karnataka coastal disaster zones ──
# (name, lat, lng, base_capacity)
#
# Zone indices reference KARNATAKA_DISASTER_ZONES order in zones.py:
#   0: Mangalore Coastal Flood Zone
#   1: Udupi-Malpe Cyclone Zone
#   2: Karwar Storm Surge Zone
#   3: Chikkamagaluru Landslide Zone
#   4: DK-Puttur Flood Zone
#   5: Ankola Cyclone Zone
#   6: Sringeri Landslide Zone

KARNATAKA_SHELTERS = [
    # --- Mangalore region shelters (serve zone 0) ---
    ("Mangalore Town Hall",              12.8750, 74.8800, 1200),   # 0
    ("Kadri Park Relief Camp",           12.8830, 74.8700, 950),    # 1
    ("Mangalore University Auditorium",  12.9100, 74.8000, 1500),   # 2
    ("Bejai Stadium Camp",               12.8920, 74.8500, 1100),   # 3

    # --- Udupi region shelters (serve zone 1) ---
    ("Udupi Town Hall",                  13.3400, 74.7400, 900),    # 4
    ("Manipal Convention Center",        13.3520, 74.7900, 1400),   # 5
    ("Malpe Community Hall",             13.3630, 74.7200, 600),    # 6

    # --- Karwar region shelters (serve zone 2) ---
    ("Karwar Stadium Relief Camp",       14.8100, 74.1500, 1000),   # 7
    ("Karwar Navy Ground Camp",          14.7900, 74.1100, 1200),   # 8
    ("Kumta Community Center",           14.4280, 74.4100, 800),    # 9

    # --- Chikkamagaluru shelters (serve zone 3) ---
    ("Mudigere Govt College",            13.1400, 75.6100, 500),    # 10
    ("Chikkamagaluru Town Hall",         13.3161, 75.7720, 1100),   # 11
    ("NR Pura High School",              13.2000, 75.5200, 400),    # 12

    # --- DK-Puttur shelters (serve zone 4) ---
    ("Puttur Town Hall",                 12.7650, 75.2200, 750),    # 13
    ("Vitla Community Hall",             12.7700, 75.1100, 550),    # 14
    ("Sullia Relief Center",             12.5600, 75.3900, 650),    # 15

    # --- Ankola shelters (serve zone 5) ---
    ("Ankola High School Shelter",       14.6700, 74.3200, 650),    # 16
    ("Kumta Relief Hall",                14.4300, 74.4200, 700),    # 17

    # --- Sringeri shelters (serve zone 6) ---
    ("Sringeri Community Hall",          13.4250, 75.2300, 450),    # 18
    ("Kalasa Temple Complex Shelter",    13.2500, 75.3500, 400),    # 19
    ("Koppa Relief Camp",                13.5450, 75.3400, 550),    # 20
]

# Zone → Shelter mapping (zone_index → list of shelter_indices)
ZONE_SHELTER_MAP = {
    0: [0, 1, 2, 3],           # Mangalore Coastal Flood → Town Hall, Kadri, Univ, Bejai
    1: [4, 5, 6],              # Udupi-Malpe Cyclone → Udupi TH, Manipal, Malpe
    2: [7, 8, 9],              # Karwar Storm Surge → Stadium, Navy, Kumta
    3: [10, 11, 12],           # Chikkamagaluru Landslide → Mudigere, CKM TH, NR Pura
    4: [13, 14, 15],           # DK-Puttur Flood → Puttur TH, Vitla, Sullia
    5: [16, 17],               # Ankola Cyclone → Ankola HS, Kumta
    6: [18, 19, 20],           # Sringeri Landslide → Sringeri, Kalasa, Koppa
}


def _haversine_km(lat1, lng1, lat2, lng2):
    """Haversine distance in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def init_shelters():
    """Create shelters at fixed locations across coastal Karnataka."""
    state.shelters = []
    for name, lat, lng, capacity in KARNATAKA_SHELTERS:
        state.shelters.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "lat": lat,
            "lng": lng,
            "capacity": capacity,
            "available_capacity": capacity,
        })


def update_shelters():
    """Update shelter available capacity based on evacuations."""
    # Capacity is managed by evacuation service; no random changes needed
    pass


def get_shelters_near(zone_id: str):
    """Return shelters assigned to a specific zone with computed distances."""
    # Find zone and its index
    zone = None
    zone_idx = None
    for idx, z in enumerate(state.zones):
        if z["id"] == zone_id:
            zone = z
            zone_idx = idx
            break

    if zone is None:
        return []

    # Get assigned shelter indices for this zone
    shelter_indices = ZONE_SHELTER_MAP.get(zone_idx, [])

    results = []
    for si in shelter_indices:
        if si >= len(state.shelters):
            continue
        s = state.shelters[si]
        dist = _haversine_km(zone["lat"], zone["lng"], s["lat"], s["lng"])
        results.append({
            "shelter_id": s["id"],
            "name": s["name"],
            "lat": s["lat"],
            "lng": s["lng"],
            "distance": round(dist, 2),
            "capacity": s["capacity"],
            "available_capacity": s["available_capacity"],
        })

    # Sort by distance
    return sorted(results, key=lambda x: x["distance"])
