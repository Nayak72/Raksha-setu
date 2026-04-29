"""
Shelter service — geographically consistent shelter placement near disaster zones.

Shelters are placed:
  • Within realistic distance (3–15 km) of disaster zones
  • OUTSIDE the immediate disaster epicenter
  • At logically safe but accessible locations (schools, stadiums, community halls)

Each zone is assigned 2–5 nearby shelters.
"""
import uuid
import math
from app.services.state import state


# ── Pre-defined shelter locations near Karnataka coastal disaster zones ──
# (name, lat, lng, base_capacity, assigned_zone_indices)
#
# Zone indices reference KARNATAKA_DISASTER_ZONES order in zones.py:
#   0-2: Mangalore   3-4: Udupi   5-6: Karwar
#   7-11: Chikkamagaluru   12-14: DK

KARNATAKA_SHELTERS = [
    # --- Mangalore region shelters (serve zones 0,1,2) ---
    ("Mangalore Town Hall",              12.8750, 74.8800, 1200),
    ("Surathkal Community Center",       12.9950, 74.8150, 800),
    ("Kadri Park Relief Camp",           12.8830, 74.8700, 950),
    ("Ullal High School Shelter",        12.8200, 74.8700, 700),
    ("Mangalore University Auditorium",  12.9100, 74.8000, 1500),
    ("Bejai Stadium Camp",               12.8920, 74.8500, 1100),

    # --- Udupi region shelters (serve zones 3,4) ---
    ("Udupi Town Hall",                  13.3400, 74.7400, 900),
    ("Manipal Convention Center",        13.3520, 74.7900, 1400),
    ("Malpe Community Hall",             13.3630, 74.7200, 600),
    ("Brahmavar Govt School",            13.4300, 74.7700, 750),
    ("Kundapura Relief Shelter",         13.6210, 74.6920, 850),

    # --- Karwar region shelters (serve zones 5,6) ---
    ("Karwar Stadium Relief Camp",       14.8100, 74.1500, 1000),
    ("Ankola High School Shelter",       14.6700, 74.3200, 650),
    ("Kumta Community Center",           14.4280, 74.4100, 800),
    ("Karwar Navy Ground Camp",          14.7900, 74.1100, 1200),

    # --- Chikkamagaluru shelters (serve zones 7-11) ---
    ("Mudigere Govt College",            13.1400, 75.6100, 500),
    ("Sringeri Community Hall",          13.4250, 75.2300, 450),
    ("Kalasa Temple Complex Shelter",    13.2500, 75.3500, 400),
    ("Koppa Relief Camp",                13.5450, 75.3400, 550),
    ("Aldur Panchayat Hall",             13.4800, 75.5700, 350),
    ("Chikkamagaluru Town Hall",         13.3161, 75.7720, 1100),
    ("NR Pura High School",              13.2000, 75.5200, 400),
    ("Birur Relief Center",              13.5970, 75.9690, 700),

    # --- Dakshina Kannada shelters (serve zones 12-14) ---
    ("Puttur Town Hall",                 12.7650, 75.2200, 750),
    ("Bantwal Community Center",         12.8980, 75.0400, 600),
    ("Belthangady Govt School",          12.9800, 75.3200, 500),
    ("Sullia Relief Center",             12.5600, 75.3900, 650),
    ("Vitla Community Hall",             12.7700, 75.1100, 550),
]

# Zone → Shelter mapping (zone_index → list of shelter_indices)
# Ensures 2-5 shelters per zone within realistic distance
ZONE_SHELTER_MAP = {
    0:  [0, 2, 4, 5],         # Mangalore-Netravathi → Town Hall, Kadri, Univ, Bejai
    1:  [1, 4, 0],            # Mangalore-Surathkal → Surathkal CC, Univ, Town Hall
    2:  [3, 5, 0, 2],         # Mangalore-Ullal → Ullal HS, Bejai, Town Hall, Kadri
    3:  [6, 8, 7],            # Udupi-Malpe → Town Hall, Malpe CH, Manipal
    4:  [9, 7, 6, 10],        # Udupi-Brahmavar → Brahmavar, Manipal, TH, Kundapura
    5:  [11, 14, 13],         # Karwar-Port → Stadium, Navy, Kumta
    6:  [12, 13, 11],         # Karwar-Ankola → Ankola HS, Kumta, Stadium
    7:  [15, 21, 16],         # Chikkamagaluru-Mudigere → Mudigere, NR Pura, Sringeri
    8:  [16, 17, 20],         # Chikkamagaluru-Sringeri → Sringeri, Kalasa, CKM TH
    9:  [17, 16, 20],         # Chikkamagaluru-Kalasa → Kalasa, Sringeri, CKM TH
    10: [18, 20, 22],         # Chikkamagaluru-Koppa → Koppa, CKM TH, Birur
    11: [19, 20, 15],         # Chikkamagaluru-Aldur → Aldur, CKM TH, Mudigere
    12: [23, 27, 24],         # DK-Puttur → Puttur TH, Vitla, Bantwal
    13: [24, 27, 23],         # DK-Bantwal → Bantwal CC, Vitla, Puttur
    14: [25, 26, 24],         # DK-Belthangady → Belthangady, Sullia, Bantwal
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
