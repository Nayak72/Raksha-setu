"""
Routing service — generates realistic road-network-style routes.

Routes are generated between the closest shelter and each disaster zone,
simulating realistic road networks with:
  • Multiple intermediate waypoints (10–18 per route)
  • Road-grid intersection snapping
  • Corridor offsets so each route takes a visibly different path
  • Realistic haversine-summed distances
  • Estimated travel times based on road speed
"""
import random
import math
from app.services.state import state


# Fallback base if no shelters loaded yet (Mangalore SDMC HQ)
FALLBACK_BASE_LAT, FALLBACK_BASE_LNG = 12.8700, 74.8500

# Road grid resolution (degrees) — roughly ~500m per grid cell
GRID_STEP = 0.005


def _haversine(lat1, lng1, lat2, lng2):
    """Distance in km between two coordinates."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _snap_to_grid(val):
    """Snap a coordinate value to the nearest road-grid line."""
    return round(round(val / GRID_STEP) * GRID_STEP, 6)


def _generate_road_path(start_lat, start_lng, end_lat, end_lng, corridor_offset=0.0):
    """
    Build a multi-waypoint path that mimics a road network by:
    1. Applying a lateral corridor offset (so different routes visibly diverge)
    2. Inserting 10-18 intermediate points
    3. Using a mix of:
       - Grid-snapped axis-aligned segments (horizontal/vertical roads)
       - Smooth interpolation with perpendicular jitter (curves)
       - Intersection turns (direction changes at grid nodes)
    """
    num_segments = random.randint(10, 18)
    path = [[round(start_lat, 6), round(start_lng, 6)]]

    # Direction vector from start to end
    dlat = end_lat - start_lat
    dlng = end_lng - start_lng
    total_dist = math.sqrt(dlat ** 2 + dlng ** 2)

    # Perpendicular direction for corridor offset
    if total_dist > 0:
        perp_lat = -dlng / total_dist
        perp_lng = dlat / total_dist
    else:
        perp_lat, perp_lng = 0.0, 0.0

    # Corridor shift scales with distance (farther = more spread)
    corridor_scale = max(0.003, total_dist * 0.05)
    offset_lat = perp_lat * corridor_offset * corridor_scale / 0.008
    offset_lng = perp_lng * corridor_offset * corridor_scale / 0.008

    prev_lat, prev_lng = start_lat, start_lng

    for i in range(1, num_segments):
        t = i / num_segments
        # Smooth S-curve interpolation (hermite-like)
        t_smooth = t * t * (3 - 2 * t)

        # Base interpolated position along the corridor
        base_lat = start_lat + dlat * t_smooth + offset_lat * math.sin(math.pi * t)
        base_lng = start_lng + dlng * t_smooth + offset_lng * math.sin(math.pi * t)

        # Road-like jitter (varies with position along route)
        jitter_scale = 0.003 * math.sin(math.pi * t)  # max jitter at midpoint
        jitter_lat = random.uniform(-jitter_scale, jitter_scale)
        jitter_lng = random.uniform(-jitter_scale, jitter_scale)

        lat = base_lat + jitter_lat
        lng = base_lng + jitter_lng

        # Simulate road-grid behavior
        dice = random.random()
        if dice < 0.35:
            # Axis-aligned segment: move only lat (horizontal road)
            lat = _snap_to_grid(lat)
            lng = prev_lng + (lng - prev_lng) * 0.7
        elif dice < 0.55:
            # Axis-aligned segment: move only lng (vertical road)
            lat = prev_lat + (lat - prev_lat) * 0.7
            lng = _snap_to_grid(lng)
        elif dice < 0.75:
            # Grid intersection turn — snap both
            lat = _snap_to_grid(lat)
            lng = _snap_to_grid(lng)
        # else: free curve (natural road bend)

        # Avoid backtracking: ensure net progress toward destination
        progress_lat = (lat - start_lat) / (dlat if abs(dlat) > 1e-6 else 1.0)
        progress_lng = (lng - start_lng) / (dlng if abs(dlng) > 1e-6 else 1.0)
        avg_progress = (progress_lat + progress_lng) / 2
        if avg_progress < (i - 1) / num_segments * 0.5:
            # Too much backtracking, nudge forward
            lat = start_lat + dlat * t * 0.9 + jitter_lat * 0.5
            lng = start_lng + dlng * t * 0.9 + jitter_lng * 0.5

        path.append([round(lat, 6), round(lng, 6)])
        prev_lat, prev_lng = lat, lng

    # End at destination
    path.append([round(end_lat, 6), round(end_lng, 6)])
    return path


def _path_distance(path):
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


def init_routes():
    """Generate 3–5 distinct routes per zone from nearest shelter to zone epicenter."""
    state.routes = {}

    for zone in state.zones:
        origin_lat, origin_lng = _find_nearest_shelter(zone)
        num_routes = random.randint(3, 5)
        routes = []
        shortest_idx = 0
        min_dist = float('inf')

        # Corridor offsets — each route takes a visibly different path
        offsets = [0.0, 0.008, -0.008, 0.015, -0.015]

        for i in range(num_routes):
            offset = offsets[i] if i < len(offsets) else random.uniform(-0.02, 0.02)

            path = _generate_road_path(
                origin_lat, origin_lng,
                zone["lat"], zone["lng"],
                corridor_offset=offset,
            )
            dist = _path_distance(path)

            # Realistic travel time:
            #   Urban: ~25 km/h → 2.4 min/km
            #   Rural: ~40 km/h → 1.5 min/km
            #   Mix: ~30 km/h → 2.0 min/km  ± variation
            speed_factor = random.uniform(1.5, 2.8)  # min per km
            time_min = max(1, round(dist * speed_factor))

            if dist < min_dist:
                min_dist = dist
                shortest_idx = i

            routes.append({
                "path": path,
                "distance": dist,
                "time": time_min,
            })

        state.routes[zone["id"]] = {
            "routes": routes,
            "shortest_route_index": shortest_idx,
        }


def update_routes():
    """Roads are mostly static; only regenerate if zones change significantly."""
    pass


def get_routes(zone_id: str):
    return state.routes.get(zone_id, {"routes": [], "shortest_route_index": 0})
