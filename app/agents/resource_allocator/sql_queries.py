"""
RakshaSetu — PostGIS SQL Queries for Resource Allocation
Raw SQL templates for spatial queries, row locking, and atomic transactions.
"""

# ==========================================================================
# SHELTER QUERIES
# ==========================================================================

FIND_SHELTERS_NEAR_ZONE = """
SELECT
    s.id,
    s.name,
    s.capacity,
    s.current_occupancy,
    s.shelter_type,
    s.is_active,
    s.latitude,
    s.longitude,
    ST_Distance(s.geom, z.geom) AS distance_m
FROM shelters s, zones z
WHERE z.id = %(zone_id)s
  AND s.is_active = TRUE
  AND ST_DWithin(s.geom, z.geom, %(radius_m)s)
ORDER BY distance_m ASC;
"""

FIND_SINGLE_NEAREST_SHELTER = """
SELECT
    s.id,
    s.name,
    s.capacity,
    s.current_occupancy,
    ST_Distance(s.geom, z.geom) AS distance_m
FROM shelters s
CROSS JOIN LATERAL (
    SELECT geom FROM zones WHERE id = %(zone_id)s
) z
WHERE s.is_active = TRUE
  AND s.current_occupancy < s.capacity
ORDER BY s.geom <-> z.geom
LIMIT 1;
"""

FIND_MULTI_SHELTERS_WITH_CAPACITY = """
SELECT
    s.id,
    s.name,
    s.capacity,
    s.current_occupancy,
    (s.capacity - s.current_occupancy) AS available_spots,
    ST_Distance(s.geom, z.geom) AS distance_m
FROM shelters s, zones z
WHERE z.id = %(zone_id)s
  AND s.is_active = TRUE
  AND s.current_occupancy < s.capacity
  AND ST_DWithin(s.geom, z.geom, %(radius_m)s)
ORDER BY distance_m ASC
LIMIT %(max_shelters)s;
"""

# ==========================================================================
# VOLUNTEER QUERIES
# ==========================================================================

FIND_VOLUNTEERS_NEAR_ZONE = """
SELECT
    v.id,
    v.name,
    v.skill_type,
    v.current_workload,
    v.max_workload,
    v.latitude,
    v.longitude,
    ST_Distance(v.geom, z.geom) AS distance_m
FROM volunteers v, zones z
WHERE z.id = %(zone_id)s
  AND v.is_available = TRUE
  AND v.current_workload < v.max_workload
  AND (%(skill_type)s = 'any' OR v.skill_type = %(skill_type)s)
ORDER BY distance_m ASC;
"""

# ==========================================================================
# ASSIGNMENT QUERIES (with row locking)
# ==========================================================================

LOCK_VOLUNTEER = """
SELECT id, current_workload, max_workload
FROM volunteers
WHERE id = %(volunteer_id)s
FOR UPDATE NOWAIT;
"""

ASSIGN_VOLUNTEER = """
UPDATE volunteers
SET current_workload = current_workload + 1,
    is_available = CASE
        WHEN current_workload + 1 >= max_workload THEN FALSE
        ELSE TRUE
    END
WHERE id = %(volunteer_id)s
  AND current_workload < max_workload;
"""

LOCK_SHELTER = """
SELECT id, current_occupancy, capacity
FROM shelters
WHERE id = %(shelter_id)s
FOR UPDATE NOWAIT;
"""

ASSIGN_SHELTER = """
UPDATE shelters
SET current_occupancy = current_occupancy + %(people_count)s
WHERE id = %(shelter_id)s
  AND current_occupancy + %(people_count)s <= capacity;
"""

CREATE_ASSIGNMENT = """
INSERT INTO assignments (zone_id, volunteer_id, shelter_id, assignment_type, status)
VALUES (%(zone_id)s, %(volunteer_id)s, %(shelter_id)s, %(assignment_type)s, 'active')
RETURNING id;
"""

# ==========================================================================
# CAPACITY CHECK
# ==========================================================================

CHECK_TOTAL_CAPACITY = """
SELECT
    COALESCE(SUM(capacity - current_occupancy), 0) AS total_available
FROM shelters s, zones z
WHERE z.id = %(zone_id)s
  AND s.is_active = TRUE
  AND ST_DWithin(s.geom, z.geom, %(radius_m)s);
"""
