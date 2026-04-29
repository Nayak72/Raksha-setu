"""
Routing service — generates realistic road-network-style routes.

Instead of straight lines, we simulate a road graph by generating
intermediate waypoints that follow a grid/road-like pattern between
the base and each zone. Each route takes a different corridor.
"""
import random
import math
from app.services.state import state


# Disaster management center (Mangalore SDMC HQ)
BASE_LAT, BASE_LNG = 12.8700, 74.8500


def _haversine(lat1, lng1, lat2, lng2):
    """Distance in km between two coordinates."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _generate_road_path(start_lat, start_lng, end_lat, end_lng, corridor_offset=0.0):
    """
    Build a multi-waypoint path that mimics a road by:
    1. Adding a lateral corridor offset (so different routes diverge)
    2. Inserting 6-10 intermediate points with small perpendicular jitter
    3. Following a rough grid pattern (alternating lat/lng moves)
    """
    num_segments = random.randint(6, 10)
    path = [[round(start_lat, 6), round(start_lng, 6)]]

    # Direction vector
    dlat = end_lat - start_lat
    dlng = end_lng - start_lng

    # Perpendicular direction for corridor offset
    perp_lat = -dlng
    perp_lng = dlat
    norm = math.sqrt(perp_lat ** 2 + perp_lng ** 2) or 1.0
    perp_lat /= norm
    perp_lng /= norm

    for i in range(1, num_segments):
        t = i / num_segments
        # Base interpolated position
        lat = start_lat + dlat * t
        lng = start_lng + dlng * t

        # Apply corridor offset (creates different route corridors)
        lat += perp_lat * corridor_offset
        lng += perp_lng * corridor_offset

        # Add road-like jitter (small, perpendicular to travel direction)
        jitter_scale = 0.002  # ~200m jitter
        lat += random.uniform(-jitter_scale, jitter_scale)
        lng += random.uniform(-jitter_scale, jitter_scale)

        # Simulate road grid: occasionally snap to axis-aligned movement
        if random.random() > 0.6:
            # Axis-aligned segment: move only lat or lng
            if random.random() > 0.5:
                lat = path[-1][0]  # same lat as previous (horizontal road)
            else:
                lng = path[-1][1]  # same lng as previous (vertical road)

        path.append([round(lat, 6), round(lng, 6)])

    # End at destination
    path.append([round(end_lat, 6), round(end_lng, 6)])
    return path


def _path_distance(path):
    """Sum haversine distances along all segments."""
    total = 0.0
    for i in range(len(path) - 1):
        total += _haversine(path[i][0], path[i][1], path[i + 1][0], path[i + 1][1])
    return round(total, 2)


def init_routes():
    state.routes = {}

    for zone in state.zones:
        num_routes = random.randint(3, 5)
        routes = []
        shortest_idx = 0
        min_dist = float('inf')

        # Different corridor offsets so routes diverge visually
        offsets = [0.0, 0.008, -0.008, 0.015, -0.015]

        for i in range(num_routes):
            offset = offsets[i] if i < len(offsets) else random.uniform(-0.02, 0.02)
            path = _generate_road_path(BASE_LAT, BASE_LNG, zone["lat"], zone["lng"], corridor_offset=offset)
            dist = _path_distance(path)
            time_min = max(1, int(dist * random.uniform(4.0, 6.0)))  # 4-6 min/km

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
    # Roads are mostly static; only regenerate if zones change significantly
    pass


def get_routes(zone_id: str):
    return state.routes.get(zone_id, {"routes": [], "shortest_route_index": 0})
