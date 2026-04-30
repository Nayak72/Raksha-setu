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
# 7 zones covering all disaster-prone regions of Coastal Karnataka
KARNATAKA_DISASTER_ZONES = [
    # id, name, lat, lng, disaster_type, base_population
    # Mangalore region — flood-prone coastal area
    ("11111111-1111-4111-8111-111111111111", "Mangalore",      12.8698, 74.8431, "flood",     8500),

    # Udupi region — cyclone corridor
    ("22222222-2222-4222-8222-222222222222", "Udupi-Malpe",          13.3500, 74.7069, "cyclone",   5400),

    # Karwar region — storm surge belt
    ("33333333-3333-4333-8333-333333333333", "Karwar",           14.8024, 74.1293, "storm",     6800),

    # Chikkamagaluru — landslide-prone hilly terrain
    ("44444444-4444-4444-8444-444444444444", "Chikkamagaluru",     13.1325, 75.6404, "landslide", 3200),

    # Dakshina Kannada — flood/storm mix
    ("55555555-5555-4555-8555-555555555555", "DK-Puttur",             12.7590, 75.2039, "flood",     5100),

    # Uttara Kannada inland — cyclone risk
    ("66666666-6666-4666-8666-666666666666", "Ankola",              14.6600, 74.3039, "cyclone",   3900),

    # Shimoga/Shivamogga — landslide corridor
    ("77777777-7777-4777-8777-777777777777", "Sringeri",          13.4186, 75.2590, "landslide", 2800),
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
    for zid, name, lat, lng, disaster_type, population in KARNATAKA_DISASTER_ZONES:
        damage = round(random.uniform(0.1, 0.9), 2)
        alerts = random.randint(0, 20)
        severity = _compute_severity(damage, alerts)

        state.zones.append({
            "id": zid,
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
