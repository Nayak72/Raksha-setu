"""
RakshaSetu — Stochastic Weather Simulation Engine

Core formula:
    rain(t+1) = rain(t) + f(wind, humidity, terrain) + randomness

This module is pure computation — no LLM, no DB calls.
The agent.py node calls this and then uses LLM to refine.
"""

import numpy as np


# Terrain multipliers — how terrain affects weather intensity
TERRAIN_FACTORS = {
    "flat":    {"rain": 1.0,  "wind": 1.2,  "humidity": 1.0},
    "hilly":   {"rain": 1.3,  "wind": 0.8,  "humidity": 1.2},
    "coastal": {"rain": 1.5,  "wind": 1.5,  "humidity": 1.4},
    "urban":   {"rain": 0.8,  "wind": 0.7,  "humidity": 0.9},
    "forest":  {"rain": 1.1,  "wind": 0.6,  "humidity": 1.3},
}

# Elevation effect: higher elevation → more rainfall condensation
ELEVATION_RAIN_FACTOR = 0.005  # mm per meter above 500m


def _terrain_modifier(terrain_type: str) -> dict:
    """Get terrain-specific modifiers."""
    return TERRAIN_FACTORS.get(terrain_type, TERRAIN_FACTORS["flat"])


def _elevation_effect(elevation_m: float) -> float:
    """Higher elevations cause orographic rainfall increase."""
    if elevation_m > 500:
        return (elevation_m - 500) * ELEVATION_RAIN_FACTOR
    return 0.0


def simulate_rainfall(
    rain_t: float,
    wind_speed: float,
    humidity: float,
    terrain_factor: float,
    noise_scale: float = 0.15,
) -> float:
    """
    Core stochastic rainfall simulation.

    rain(t+1) = rain(t) + f(wind, humidity, terrain) + randomness

    Args:
        rain_t: Previous rainfall in mm
        wind_speed: Wind speed in km/h
        humidity: Humidity as percentage (0-100)
        terrain_factor: Terrain multiplier for rain
        noise_scale: Scale of Gaussian noise relative to rain_t

    Returns:
        Simulated rainfall for next timestep in mm
    """
    # Environmental contribution function
    wind_contribution = (wind_speed / 100) * 0.3   # Normalized wind effect
    humidity_contribution = (humidity / 100) * 0.5  # Humidity drives condensation
    environmental_effect = (wind_contribution + humidity_contribution) * terrain_factor * 10

    # Stochastic noise — proportional to current rainfall with a base noise
    if rain_t > 0:
        noise = np.random.normal(0, noise_scale * max(rain_t, 1.0))
    else:
        noise = np.random.uniform(0, 3.0)  # Base noise when no prior rain

    # Simulate next rainfall
    rain_next = rain_t + environmental_effect + noise

    return round(max(0, rain_next), 2)


def simulate_wind(wind_t: float, terrain_type: str) -> float:
    """Simulate wind speed evolution with terrain effects."""
    modifier = _terrain_modifier(terrain_type)
    base_change = np.random.normal(0, 3.0)  # Wind is volatile
    wind_next = wind_t * modifier["wind"] * 0.9 + base_change + np.random.uniform(-2, 5)
    return round(max(0, min(120, wind_next)), 1)


def simulate_humidity(humidity_t: float, terrain_type: str) -> float:
    """Simulate humidity evolution."""
    modifier = _terrain_modifier(terrain_type)
    base_change = np.random.normal(0, 5.0)
    humidity_next = humidity_t * modifier["humidity"] * 0.95 + base_change
    return round(max(10, min(100, humidity_next)), 1)


def simulate_temperature(temp_t: float, humidity: float, elevation_m: float) -> float:
    """Simulate temperature — inversely correlated with humidity and elevation."""
    # Lapse rate: ~6.5°C per 1000m
    elevation_effect = -(elevation_m / 1000) * 0.5
    humidity_effect = -(humidity - 60) / 100 * 2  # High humidity cools slightly
    noise = np.random.normal(0, 1.0)
    temp_next = temp_t + elevation_effect + humidity_effect + noise
    return round(max(-10, min(50, temp_next)), 1)


def classify_severity(rainfall_mm: float, wind_speed: float, humidity: float) -> str:
    """
    Adaptive severity classification — no hardcoded if/else rules.
    Uses a weighted composite score.
    """
    # Normalize each factor to 0-1 scale
    rain_score = min(1.0, rainfall_mm / 100)
    wind_score = min(1.0, wind_speed / 80)
    humidity_score = min(1.0, humidity / 100)

    # Weighted composite
    composite = rain_score * 0.5 + wind_score * 0.3 + humidity_score * 0.2

    # Fuzzy boundaries with noise for adaptiveness
    noise = np.random.uniform(-0.05, 0.05)
    composite += noise

    if composite >= 0.75:
        return "CRITICAL"
    elif composite >= 0.50:
        return "HIGH"
    elif composite >= 0.30:
        return "MEDIUM"
    return "LOW"


def simulate_weather(prev_weather: dict, zone_geo: dict) -> dict:
    """
    Full weather simulation pipeline.

    Args:
        prev_weather: Dict with rainfall_mm, wind_speed_kmh, humidity_pct, temperature_c
        zone_geo: Dict with terrain_type, elevation_m

    Returns:
        Dict with simulated next-step weather values
    """
    terrain = zone_geo.get("terrain_type", "flat")
    elevation = zone_geo.get("elevation_m", 0)
    terrain_mod = _terrain_modifier(terrain)

    # Extract previous values (with defaults)
    rain_t = prev_weather.get("rainfall_mm", 0)
    wind_t = prev_weather.get("wind_speed_kmh", 10)
    humidity_t = prev_weather.get("humidity_pct", 60)
    temp_t = prev_weather.get("temperature_c", 25)

    # Simulate each variable
    rain_next = simulate_rainfall(rain_t, wind_t, humidity_t, terrain_mod["rain"])
    rain_next += _elevation_effect(elevation)  # Orographic enhancement
    rain_next = round(rain_next, 2)

    wind_next = simulate_wind(wind_t, terrain)
    humidity_next = simulate_humidity(humidity_t, terrain)
    temp_next = simulate_temperature(temp_t, humidity_next, elevation)

    severity = classify_severity(rain_next, wind_next, humidity_next)

    return {
        "rainfall_mm": rain_next,
        "wind_speed_kmh": wind_next,
        "humidity_pct": humidity_next,
        "temperature_c": temp_next,
        "severity": severity,
        "terrain_type": terrain,
        "elevation_m": elevation,
    }
