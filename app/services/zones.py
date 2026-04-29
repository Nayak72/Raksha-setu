"""
Zone service — geographically consistent disaster zones across Coastal Karnataka.

All zones are constrained to:
  Latitude:  12.5 → 15.0
  Longitude: 74.0 → 75.5

Zones are initialized ONCE with fixed locations. Only dynamic parameters
(severity, damage_level, alert_count) change over simulation cycles.
"""
import random
import uuid
from app.services.state import state

# ── Fixed disaster zone definitions ────────────────────────────────
# Each entry: (name, lat, lng, disaster_type, base_population)
KARNATAKA_DISASTER_ZONES = [
    # Mangalore region — flood-prone coastal area
    ("Mangalore-Netravathi Flood Zone", 12.8698, 74.8431, "flood", 8500),
    ("Mangalore-Surathkal Storm Zone",  12.9854, 74.7936, "storm", 6200),
    ("Mangalore-Ullal Cyclone Zone",    12.8074, 74.8560, "cyclone", 7100),

    # Udupi region — cyclone and flood corridors
    ("Udupi-Malpe Cyclone Zone",        13.3500, 74.7069, "cyclone", 5400),
    ("Udupi-Brahmavar Flood Zone",      13.4245, 74.7480, "flood", 4800),

    # Karwar region — storm surge and cyclone belt
    ("Karwar-Port Storm Surge Zone",    14.8024, 74.1293, "storm", 6800),
    ("Karwar-Ankola Cyclone Zone",      14.6600, 74.3039, "cyclone", 3900),

    # Chikkamagaluru — landslide-prone hilly terrain (minimum 5 zones)
    ("Chikkamagaluru-Mudigere Landslide", 13.1325, 75.6404, "landslide", 3200),
    ("Chikkamagaluru-Sringeri Landslide", 13.4186, 75.2590, "landslide", 2800),
    ("Chikkamagaluru-Kalasa Landslide",   13.2401, 75.3765, "landslide", 2500),
    ("Chikkamagaluru-Koppa Landslide",    13.5384, 75.3570, "landslide", 3600),
    ("Chikkamagaluru-Aldur Landslide",    13.4700, 75.5930, "landslide", 2100),

    # Dakshina Kannada — mixed flood/storm
    ("DK-Puttur Flood Zone",             12.7590, 75.2039, "flood", 5100),
    ("DK-Bantwal Storm Zone",            12.8917, 75.0264, "storm", 4300),
    ("DK-Belthangady Landslide Zone",    12.9700, 75.3000, "landslide", 3000),
]


def _compute_severity(damage: float, alerts: int) -> str:
    """Derive severity from damage + alert count."""
    if damage > 0.75 or alerts > 15:
        return "critical"
    elif damage > 0.5:
        return "high"
    elif damage > 0.25:
        return "medium"
    return "low"


def init_zones():
    """Create fixed disaster zones across coastal Karnataka."""
    state.zones = []
    for name, lat, lng, disaster_type, population in KARNATAKA_DISASTER_ZONES:
        damage = round(random.uniform(0.1, 0.9), 2)
        alerts = random.randint(0, 20)
        severity = _compute_severity(damage, alerts)

        state.zones.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "lat": lat,
            "lng": lng,
            "population": population,
            "affected_population": int(population * random.uniform(0.3, 0.8)),
            "damage_level": damage,
            "alert_count": alerts,
            "severity": severity,
            "disaster_type": disaster_type,
        })


def update_zones():
    """Update dynamic parameters WITHOUT relocating zones."""
    for zone in state.zones:
        # Damage might increase slightly
        if random.random() > 0.8 and zone["damage_level"] < 1.0:
            zone["damage_level"] = min(1.0, zone["damage_level"] + random.uniform(0.01, 0.05))
            zone["damage_level"] = round(zone["damage_level"], 2)

        # Alerts might go up or down
        zone["alert_count"] = max(0, zone["alert_count"] + random.randint(-2, 3))

        # Affected population drifts slightly
        pop = zone["population"]
        zone["affected_population"] = max(
            int(pop * 0.1),
            min(pop, zone["affected_population"] + random.randint(-50, 80)),
        )

        # Re-evaluate severity
        zone["severity"] = _compute_severity(zone["damage_level"], zone["alert_count"])
