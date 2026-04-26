"""
RakshaSetu — Weather Agent Tools
Re-exports shared tools for the weather agent context.
"""

from app.shared.tools import get_previous_weather, get_zone_geography

# List of tools available to the Weather Simulation Agent
WEATHER_TOOLS = [get_previous_weather, get_zone_geography]
