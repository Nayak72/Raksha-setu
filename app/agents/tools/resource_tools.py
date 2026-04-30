"""
RakshaSetu — MCP Resource Tools
LangChain tool interfaces for shelter, volunteer, and assignment operations.

Schema alignment:
  shelters     → TEXT id, capacity, current_occupancy, is_active
  volunteers   → TEXT id, is_available (bool), current_workload, max_workload
  assignments  → zone_id, volunteer_id FK, shelter_id FK, assignment_type, status
"""

import logging
from langchain_core.tools import tool
from app.db.supabase_client import get_supabase as get_supabase_client

logger = logging.getLogger("raksha.tools.resource")


@tool
def get_shelters(zone_id: str) -> dict:
    """
    Fetch all active shelters with available capacity.
    Available beds = capacity - current_occupancy.
    Use this tool to find shelter capacity before allocating beds.
    """
    try:
        client = get_supabase_client()

        # Shelters are not directly linked to zones via FK,
        # so we fetch all active shelters with available capacity.
        response = (
            client.table("shelters")
            .select("id, name, latitude, longitude, capacity, current_occupancy, shelter_type, is_active")
            .eq("is_active", True)
            .order("capacity", desc=True)
            .execute()
        )
        shelters = response.data or []

        # Compute available beds per shelter
        result_shelters = []
        total_available = 0
        for s in shelters:
            available = max(0, s.get("capacity", 0) - s.get("current_occupancy", 0))
            if available > 0:
                result_shelters.append({
                    "id": s["id"],
                    "name": s.get("name", ""),
                    "capacity": s.get("capacity", 0),
                    "current_occupancy": s.get("current_occupancy", 0),
                    "available_beds": available,
                    "shelter_type": s.get("shelter_type", "general"),
                })
                total_available += available

        # Sort by available beds desc so the first entry is the best choice
        result_shelters.sort(key=lambda s: s["available_beds"], reverse=True)

        return {
            "zone_id": zone_id,
            "shelters": result_shelters,
            "shelter_count": len(result_shelters),
            "total_available_beds": total_available,
            "fallback": False,
        }

    except Exception as e:
        logger.error(f"get_shelters failed: {e}")
        return {
            "zone_id": zone_id,
            "shelters": [],
            "shelter_count": 0,
            "total_available_beds": 0,
            "fallback": True,
            "error": str(e),
        }


@tool
def get_available_volunteers(zone_id: str) -> dict:
    """
    Fetch all available volunteers who have capacity for more work.
    A volunteer is available if is_available=TRUE and current_workload < max_workload.
    Use this tool to check volunteer capacity before making assignments.
    """
    try:
        client = get_supabase_client()

        response = (
            client.table("volunteers")
            .select("id, name, latitude, longitude, skill_type, current_workload, max_workload")
            .eq("is_available", True)
            .execute()
        )
        all_vols = response.data or []

        # Filter: only those with remaining workload capacity
        available = [
            v for v in all_vols
            if v.get("current_workload", 0) < v.get("max_workload", 3)
        ]

        return {
            "zone_id": zone_id,
            "available_count": len(available),
            "volunteers": [
                {
                    "id": v["id"],
                    "name": v.get("name", "Unknown"),
                    "skill_type": v.get("skill_type", "general"),
                    "current_workload": v.get("current_workload", 0),
                    "max_workload": v.get("max_workload", 3),
                }
                for v in available
            ],
            "fallback": False,
        }

    except Exception as e:
        logger.error(f"get_available_volunteers failed: {e}")
        return {
            "zone_id": zone_id,
            "available_count": 0,
            "volunteers": [],
            "fallback": True,
            "error": str(e),
        }


@tool
def update_assignments(zone_id: str, volunteer_ids: list[str], shelter_id: str) -> dict:
    """
    Create assignment records linking volunteers and a shelter to a zone.
    Also increments shelter occupancy and volunteer workload.
    Use this tool after deciding on resource allocation.
    """
    try:
        client = get_supabase_client()
        created_assignments = []

        # 1. Assign each volunteer
        for vol_id in volunteer_ids:
            assign_resp = (
                client.table("assignments")
                .insert({
                    "zone_id": zone_id,
                    "volunteer_id": vol_id,
                    "shelter_id": shelter_id,
                    "assignment_type": "volunteer",
                    "status": "active",
                })
                .execute()
            )
            record = (assign_resp.data or [{}])[0]
            created_assignments.append(record.get("id"))

            # Increment volunteer workload
            vol_resp = (
                client.table("volunteers")
                .select("current_workload")
                .eq("id", vol_id)
                .single()
                .execute()
            )
            if vol_resp.data:
                new_workload = vol_resp.data.get("current_workload", 0) + 1
                client.table("volunteers").update(
                    {"current_workload": new_workload}
                ).eq("id", vol_id).execute()

        # 2. Increment shelter occupancy by number of assigned volunteers
        if shelter_id and volunteer_ids:
            shelter_resp = (
                client.table("shelters")
                .select("current_occupancy, capacity")
                .eq("id", shelter_id)
                .single()
                .execute()
            )
            if shelter_resp.data:
                current = shelter_resp.data.get("current_occupancy", 0)
                cap = shelter_resp.data.get("capacity", 0)
                new_occ = min(current + len(volunteer_ids), cap)
                client.table("shelters").update(
                    {"current_occupancy": new_occ}
                ).eq("id", shelter_id).execute()

        return {
            "zone_id": zone_id,
            "assignment_ids": created_assignments,
            "volunteers_assigned": len(volunteer_ids),
            "shelter_id": shelter_id,
            "success": True,
            "fallback": False,
        }

    except Exception as e:
        logger.error(f"update_assignments failed for zone {zone_id}: {e}")
        return {
            "zone_id": zone_id,
            "assignment_ids": [],
            "volunteers_assigned": 0,
            "shelter_id": shelter_id,
            "success": False,
            "fallback": True,
            "error": str(e),
        }
