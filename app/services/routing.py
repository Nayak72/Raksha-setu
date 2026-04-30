"""
Routing service — generates real road-aligned routes using OSRM.

Routes are generated between the closest shelter and each disaster zone
using the free OSRM public API (router.project-osrm.org), which returns
geometries snapped to real road networks.

Fallback: If OSRM is unavailable, generates a single straight-line route.
"""
import math
import random
import logging
from typing import List, Tuple, Optional
import urllib.request
import json

from app.services.state import state

logger = logging.getLogger(__name__)

# Fallback base if no shelters loaded yet (Mangalore SDMC HQ)
FALLBACK_BASE_LAT, FALLBACK_BASE_LNG = 12.8700, 74.8500

# OSRM public demo server (free, no API key)
OSRM_BASE = "https://router.project-osrm.org"

# Timeout for OSRM requests (seconds)
OSRM_TIMEOUT = 10


def _haversine(lat1, lng1, lat2, lng2):
    """Distance in km between two coordinates."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _decode_polyline(encoded: str) -> List[List[float]]:
    """
    Decode a Google-encoded polyline string (precision 5) into [[lat, lng], ...].
    OSRM returns polyline-encoded geometries by default.
    """
    result = []
    index = 0
    lat = 0
    lng = 0
    while index < len(encoded):
        # Decode latitude
        shift = 0
        b = 0x20
        while b >= 0x20:
            b = ord(encoded[index]) - 63
            index += 1
            lat += (b & 0x1F) << shift
            shift += 5
        lat_change = ~(lat >> 1) if (lat & 1) else (lat >> 1)

        # Decode longitude
        shift = 0
        b = 0x20
        lat = 0  # reset accumulator
        lng_acc = 0
        while b >= 0x20:
            b = ord(encoded[index]) - 63
            index += 1
            lng_acc += (b & 0x1F) << shift
            shift += 5
        lng_change = ~(lng_acc >> 1) if (lng_acc & 1) else (lng_acc >> 1)

        result.append([round(lat_change / 1e5, 6), round(lng_change / 1e5, 6)])

    # The decoded values above are deltas; accumulate them
    # Re-implement properly:
    return result


def _decode_polyline5(encoded: str) -> List[List[float]]:
    """
    Proper Google polyline decoder (precision 5).
    Returns list of [lat, lng] pairs.
    """
    result = []
    index = 0
    lat = 0
    lng = 0

    while index < len(encoded):
        # Latitude
        shift = 0
        value = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            value |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(value >> 1) if (value & 1) else (value >> 1)
        lat += dlat

        # Longitude
        shift = 0
        value = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            value |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(value >> 1) if (value & 1) else (value >> 1)
        lng += dlng

        result.append([round(lat / 1e5, 6), round(lng / 1e5, 6)])

    return result


def _fetch_osrm_routes(
    origin_lat: float, origin_lng: float,
    dest_lat: float, dest_lng: float,
    alternatives: int = 3,
) -> Optional[List[dict]]:
    """
    Query OSRM for driving routes between origin and destination.
    Returns list of route dicts with 'geometry', 'distance' (m), 'duration' (s).
    Returns None on failure.
    """
    # OSRM uses lng,lat ordering in the URL
    coords = f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
    url = (
        f"{OSRM_BASE}/route/v1/driving/{coords}"
        f"?overview=full&geometries=polyline&alternatives={alternatives}"
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RakshaSetu/1.0"})
        with urllib.request.urlopen(req, timeout=OSRM_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())

        if data.get("code") != "Ok":
            logger.warning(f"OSRM returned non-Ok: {data.get('code')}")
            return None

        return data.get("routes", [])
    except Exception as e:
        logger.warning(f"OSRM request failed: {e}")
        return None


def _path_distance(path: List[List[float]]) -> float:
    """Sum haversine distances along all segments."""
    total = 0.0
    for i in range(len(path) - 1):
        total += _haversine(path[i][0], path[i][1], path[i + 1][0], path[i + 1][1])
    return round(total, 2)


def _find_nearest_shelter(zone):
    """Find the nearest shelter to a zone as the route origin."""
    if not state.shelters:
        return FALLBACK_BASE_LAT, FALLBACK_BASE_LNG

    best = None
    best_dist = float('inf')
    for shelter in state.shelters:
        d = _haversine(zone["lat"], zone["lng"], shelter["lat"], shelter["lng"])
        if d < best_dist:
            best_dist = d
            best = shelter

    if best:
        return best["lat"], best["lng"]
    return FALLBACK_BASE_LAT, FALLBACK_BASE_LNG


def _build_fallback_route(origin_lat, origin_lng, dest_lat, dest_lng):
    """Straight-line fallback route when OSRM is unavailable."""
    path = [
        [round(origin_lat, 6), round(origin_lng, 6)],
        [round(dest_lat, 6), round(dest_lng, 6)],
    ]
    dist = _haversine(origin_lat, origin_lng, dest_lat, dest_lng)
    time_min = max(1, round(dist * 2.0))  # ~30 km/h
    return {
        "path": path,
        "distance": round(dist, 2),
        "time": time_min,
    }


def _simplify_path(path: List[List[float]], max_points: int = 80) -> List[List[float]]:
    """
    Downsample a path to at most max_points while keeping start/end and
    evenly-spaced intermediate points.
    """
    if len(path) <= max_points:
        return path
    step = (len(path) - 1) / (max_points - 1)
    indices = [round(i * step) for i in range(max_points)]
    indices[-1] = len(path) - 1  # ensure last point
    return [path[i] for i in dict.fromkeys(indices)]  # dedupe preserving order


def init_routes():
    """
    Generate road-aligned routes per zone using OSRM.
    Each zone gets 1-3 alternative routes (OSRM limit) from its nearest shelter.
    Falls back to straight line if OSRM is unreachable.
    """
    state.routes = {}

    for zone in state.zones:
        origin_lat, origin_lng = _find_nearest_shelter(zone)
        dest_lat, dest_lng = zone["lat"], zone["lng"]

        osrm_routes = _fetch_osrm_routes(
            origin_lat, origin_lng,
            dest_lat, dest_lng,
            alternatives=3,
        )

        routes = []
        shortest_idx = 0
        min_dist = float('inf')

        if osrm_routes:
            for i, osrm_route in enumerate(osrm_routes):
                # Decode the polyline geometry → [[lat, lng], ...]
                geometry_str = osrm_route.get("geometry", "")
                if not geometry_str:
                    continue

                try:
                    path = _decode_polyline5(geometry_str)
                except Exception as e:
                    logger.warning(f"Polyline decode failed for zone {zone['id']}: {e}")
                    continue

                if len(path) < 2:
                    continue

                # Use the full path for accurate road alignment
                # (Removed simplification that was causing straight, non-road-aligned paths)
                # path = _simplify_path(path, max_points=80)

                # OSRM gives distance in meters, duration in seconds
                dist_km = round(osrm_route.get("distance", 0) / 1000, 2)
                time_min = max(1, round(osrm_route.get("duration", 0) / 60))

                if dist_km < min_dist:
                    min_dist = dist_km
                    shortest_idx = i

                routes.append({
                    "path": path,
                    "distance": dist_km,
                    "time": time_min,
                })

        # Fallback: if no OSRM routes, use straight line
        if not routes:
            logger.info(f"Using fallback straight-line route for zone {zone['id']}")
            routes.append(_build_fallback_route(origin_lat, origin_lng, dest_lat, dest_lng))
            shortest_idx = 0

        state.routes[zone["id"]] = {
            "routes": routes,
            "shortest_route_index": shortest_idx,
        }

    logger.info(f"Routes initialized for {len(state.routes)} zones")


def update_routes():
    """Roads are mostly static; only regenerate if zones change significantly."""
    pass


def get_routes(zone_id: str):
    return state.routes.get(zone_id, {"routes": [], "shortest_route_index": 0})
