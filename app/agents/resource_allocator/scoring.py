"""
RakshaSetu — Resource Allocation Scoring Functions
Volunteer and shelter scoring + plan generation.

Scoring formulas:
  volunteer_score = distance + workload_penalty - skill_match_bonus
  shelter_score = distance + occupancy_penalty + congestion_factor
"""

import logging

logger = logging.getLogger(__name__)

# Scoring weights
WORKLOAD_PENALTY = 500     # meters equivalent penalty per active assignment
SKILL_BONUS = 1000         # meters equivalent bonus for matching skill
OCCUPANCY_WEIGHT = 2000    # penalty scaling for occupancy ratio
CONGESTION_WEIGHT = 1500   # penalty for congested shelters


def score_volunteer(
    distance_m: float,
    current_workload: int,
    skill_type: str,
    required_skill: str = "any",
) -> float:
    """
    Score a volunteer for assignment (lower is better).

    score = distance + workload_penalty - skill_match_bonus

    Args:
        distance_m: Distance from zone in meters
        current_workload: Number of active assignments
        skill_type: Volunteer's skill type
        required_skill: Required skill for this assignment

    Returns:
        Score value (lower = better candidate)
    """
    workload_penalty = current_workload * WORKLOAD_PENALTY

    skill_match = 0
    if required_skill == "any" or skill_type == required_skill:
        skill_match = SKILL_BONUS
    elif skill_type == "rescue":
        # Rescue workers get partial bonus for any task
        skill_match = SKILL_BONUS * 0.5

    score = distance_m + workload_penalty - skill_match
    return round(max(0, score), 2)


def score_shelter(
    distance_m: float,
    capacity: int,
    current_occupancy: int,
    shelter_type: str = "general",
) -> float:
    """
    Score a shelter for allocation (lower is better).

    score = distance + occupancy_ratio * weight + congestion_factor

    Args:
        distance_m: Distance from zone in meters
        capacity: Total shelter capacity
        current_occupancy: Current number of occupants
        shelter_type: Type of shelter

    Returns:
        Score value (lower = better shelter)
    """
    occupancy_ratio = current_occupancy / max(capacity, 1)
    available = capacity - current_occupancy

    # Shelter with no space gets massive penalty
    if available <= 0:
        return float("inf")

    occupancy_penalty = occupancy_ratio * OCCUPANCY_WEIGHT

    # Congestion: shelters above 80% capacity get extra penalty
    congestion = 0
    if occupancy_ratio > 0.8:
        congestion = (occupancy_ratio - 0.8) * CONGESTION_WEIGHT * 5

    score = distance_m + occupancy_penalty + congestion
    return round(score, 2)


def generate_allocation_plans(
    zone_id: str,
    shelters: list[dict],
    volunteers: list[dict],
    decision: str,
    priority: float,
) -> list[dict]:
    """
    Generate candidate allocation plans based on decision and resources.

    Handles:
    - single shelter allocation
    - multi-shelter allocation
    - no capacity → escalation flag

    Returns:
        List of plan dicts, each with 'volunteers', 'shelters', 'score'
    """
    plans = []

    # Determine how many resources to allocate based on priority
    if decision == "EVACUATE":
        max_volunteers = min(len(volunteers), 5)
        max_shelters = min(len(shelters), 3)
    elif decision == "DEPLOY_RESOURCES":
        max_volunteers = min(len(volunteers), 3)
        max_shelters = min(len(shelters), 2)
    elif decision == "ALERT":
        max_volunteers = min(len(volunteers), 2)
        max_shelters = min(len(shelters), 1)
    else:
        max_volunteers = min(len(volunteers), 1)
        max_shelters = min(len(shelters), 1)

    # Score all volunteers
    scored_volunteers = []
    required_skill = "rescue" if decision == "EVACUATE" else "any"
    for v in volunteers:
        s = score_volunteer(
            distance_m=v.get("distance_m", 9999),
            current_workload=v.get("current_workload", 0),
            skill_type=v.get("skill_type", "general"),
            required_skill=required_skill,
        )
        scored_volunteers.append({**v, "score": s})
    scored_volunteers.sort(key=lambda x: x["score"])

    # Score all shelters
    scored_shelters = []
    for s in shelters:
        sc = score_shelter(
            distance_m=s.get("distance_m", 9999),
            capacity=s.get("capacity", 0),
            current_occupancy=s.get("current_occupancy", 0),
            shelter_type=s.get("shelter_type", "general"),
        )
        scored_shelters.append({**s, "score": sc})
    scored_shelters.sort(key=lambda x: x["score"])

    # ---- Plan A: Best volunteers + best single shelter ----
    if scored_shelters and scored_volunteers:
        plan_a_vols = scored_volunteers[:max_volunteers]
        plan_a_shelters = scored_shelters[:1]
        plan_a_score = (
            sum(v["score"] for v in plan_a_vols) / len(plan_a_vols)
            + plan_a_shelters[0]["score"]
        )
        plans.append({
            "name": "Plan A: Concentrated (single shelter)",
            "volunteers": plan_a_vols,
            "shelters": plan_a_shelters,
            "score": round(plan_a_score, 2),
        })

    # ---- Plan B: Multi-shelter distribution ----
    if len(scored_shelters) >= 2 and scored_volunteers:
        plan_b_vols = scored_volunteers[:max_volunteers]
        plan_b_shelters = scored_shelters[:max_shelters]
        plan_b_score = (
            sum(v["score"] for v in plan_b_vols) / len(plan_b_vols)
            + sum(s["score"] for s in plan_b_shelters) / len(plan_b_shelters)
        )
        plans.append({
            "name": "Plan B: Distributed (multi-shelter)",
            "volunteers": plan_b_vols,
            "shelters": plan_b_shelters,
            "score": round(plan_b_score, 2),
        })

    # ---- Plan C: Volunteers only (no shelters available) ----
    if scored_volunteers and not scored_shelters:
        plan_c_vols = scored_volunteers[:max_volunteers]
        plan_c_score = sum(v["score"] for v in plan_c_vols) / len(plan_c_vols) + 5000  # High penalty
        plans.append({
            "name": "Plan C: Volunteers only (no shelters)",
            "volunteers": plan_c_vols,
            "shelters": [],
            "score": round(plan_c_score, 2),
        })

    return plans


def select_optimal_plan(plans: list[dict]) -> dict:
    """Select the plan with the lowest score (lower = better)."""
    if not plans:
        return {"volunteers": [], "shelters": [], "score": float("inf")}
    return min(plans, key=lambda p: p["score"])
