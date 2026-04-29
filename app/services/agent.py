"""
Agent decision pipeline — 6 named agents that each produce structured logs.
"""

from app.services.state import state
from app.services.logs import record_log
from app.services.shelters import get_shelters_near


def run_agent_decisions():
    for zone in state.zones:
        pop = zone["population"]
        damage = zone["damage_level"]
        alerts = zone["alert_count"]

        evac_record = next((e for e in state.evacuations if e["zone_id"] == zone["id"]), None)
        current_evac = evac_record["evacuated_count"] if evac_record else 0

        shelters = get_shelters_near(zone["id"])
        total_capacity = sum(s["available_capacity"] for s in shelters)
        remaining_pop = pop - current_evac

        # ── 1. Triage Agent ─────────────────────────────────────
        triage_inputs = {
            "damage_level": damage,
            "alert_count": alerts,
            "population": pop,
        }
        triage_params = {"damage_weight": 0.7, "alert_weight": 0.2, "pop_weight": 0.1}
        triage_thresholds = [
            {"parameter": "damage_level", "value": round(damage, 3), "threshold": 0.75, "exceeded": damage > 0.75},
            {"parameter": "alert_count", "value": alerts, "threshold": 15, "exceeded": alerts > 15},
        ]
        triage_score = (damage * triage_params["damage_weight"]
                        + min(alerts / 20, 1.0) * triage_params["alert_weight"]
                        + min(pop / 10000, 1.0) * triage_params["pop_weight"])
        triage_priority = "critical" if triage_score > 0.7 else "high" if triage_score > 0.5 else "medium" if triage_score > 0.3 else "low"

        triage_reasoning = (
            f"Triage Agent computed a composite score of {round(triage_score, 2)} "
            f"(damage {damage} × {triage_params['damage_weight']}, "
            f"alerts {alerts}/20 × {triage_params['alert_weight']}, "
            f"pop {pop}/10000 × {triage_params['pop_weight']}). "
        )
        if damage > 0.75:
            triage_reasoning += f"Damage level ({damage}) exceeded critical threshold (0.75). "
        if alerts > 15:
            triage_reasoning += f"Alert count ({alerts}) exceeded threshold (15). "
        triage_reasoning += f"Zone classified as {triage_priority.upper()} priority."

        record_log(
            agent_name="Triage Agent",
            zone_id=zone["id"],
            input_data=triage_inputs,
            parameters_used=triage_params,
            thresholds_checked=triage_thresholds,
            decision=f"Priority level: {triage_priority}",
            outcome=f"Zone tagged as {triage_priority.upper()} — forwarded to downstream agents.",
            reasoning=triage_reasoning,
        )

        # ── 2. Weather Agent ────────────────────────────────────
        # Simulate weather factor derived from damage proxy
        weather_factor = min(1.0, damage * 1.2 + 0.1)
        weather_inputs = {"base_damage": damage, "weather_factor": round(weather_factor, 3)}
        weather_params = {"amplification_rate": 1.2, "baseline_offset": 0.1}
        weather_thresholds = [
            {"parameter": "weather_factor", "value": round(weather_factor, 3), "threshold": 0.8, "exceeded": weather_factor > 0.8},
        ]
        weather_decision = "adverse" if weather_factor > 0.8 else "moderate" if weather_factor > 0.5 else "stable"
        weather_reasoning = (
            f"Weather Agent derived weather_factor={round(weather_factor, 3)} from base_damage ({damage}) "
            f"using amplification_rate ({weather_params['amplification_rate']}) + baseline offset ({weather_params['baseline_offset']}). "
            f"Conditions assessed as {weather_decision.upper()}."
        )
        if weather_factor > 0.8:
            weather_reasoning += " Adverse weather increases evacuation urgency."

        record_log(
            agent_name="Weather Agent",
            zone_id=zone["id"],
            input_data=weather_inputs,
            parameters_used=weather_params,
            thresholds_checked=weather_thresholds,
            decision=f"Weather condition: {weather_decision}",
            outcome=f"Weather flag '{weather_decision}' applied to zone risk model.",
            reasoning=weather_reasoning,
        )

        # ── 3. Zone Analyst Agent ───────────────────────────────
        risk_score = round(triage_score * 0.6 + weather_factor * 0.4, 3)
        analyst_inputs = {"triage_score": round(triage_score, 3), "weather_factor": round(weather_factor, 3)}
        analyst_params = {"triage_weight": 0.6, "weather_weight": 0.4}
        analyst_thresholds = [
            {"parameter": "combined_risk", "value": risk_score, "threshold": 0.6, "exceeded": risk_score > 0.6},
        ]
        evac_urgency = "HIGH" if risk_score > 0.6 else "MEDIUM" if risk_score > 0.35 else "LOW"
        analyst_reasoning = (
            f"Zone Analyst fused triage_score ({round(triage_score, 3)}) and weather_factor ({round(weather_factor, 3)}) "
            f"with weights {analyst_params} to produce combined_risk={risk_score}. "
        )
        if risk_score > 0.6:
            analyst_reasoning += f"Combined risk ({risk_score}) exceeded threshold (0.6) — evacuation urgency set to HIGH."
        elif risk_score > 0.35:
            analyst_reasoning += f"Combined risk ({risk_score}) in moderate range — evacuation urgency MEDIUM."
        else:
            analyst_reasoning += f"Combined risk ({risk_score}) below concern — evacuation urgency LOW."

        record_log(
            agent_name="Zone Analyst Agent",
            zone_id=zone["id"],
            input_data=analyst_inputs,
            parameters_used=analyst_params,
            thresholds_checked=analyst_thresholds,
            decision=f"Evacuation urgency: {evac_urgency}",
            outcome=f"Risk score {risk_score} computed; evacuation urgency={evac_urgency}.",
            reasoning=analyst_reasoning,
        )

        # ── 4. Resource Allocator Agent ─────────────────────────
        safe_margin = 1.2  # 20% buffer
        needed_capacity = int(remaining_pop * safe_margin)
        capacity_met = total_capacity >= needed_capacity

        alloc_inputs = {
            "remaining_population": remaining_pop,
            "shelter_capacity_nearby": total_capacity,
            "needed_capacity": needed_capacity,
        }
        alloc_params = {"safety_margin_factor": safe_margin}
        alloc_thresholds = [
            {"parameter": "shelter_capacity", "value": total_capacity, "threshold": needed_capacity, "exceeded": not capacity_met},
        ]
        alloc_level = "max" if triage_priority == "critical" else "moderate" if triage_priority == "high" else "minimal"
        alloc_reasoning = (
            f"Resource Allocator evaluated remaining population ({remaining_pop}) against "
            f"nearby shelter capacity ({total_capacity}) with safety margin ×{safe_margin} "
            f"(needed: {needed_capacity}). "
        )
        if not capacity_met:
            alloc_reasoning += f"Shelter capacity ({total_capacity}) is BELOW needed ({needed_capacity}) — resource allocation escalated to {alloc_level.upper()}."
        else:
            alloc_reasoning += f"Shelter capacity ({total_capacity}) meets demand. Resources set to {alloc_level.upper()}."

        record_log(
            agent_name="Resource Allocator Agent",
            zone_id=zone["id"],
            input_data=alloc_inputs,
            parameters_used=alloc_params,
            thresholds_checked=alloc_thresholds,
            decision=f"Resource allocation: {alloc_level}",
            outcome=f"Allocated resources at {alloc_level.upper()} level for {remaining_pop} remaining population.",
            reasoning=alloc_reasoning,
        )

        # ── 5. Supervisor Agent ─────────────────────────────────
        sup_inputs = {
            "priority": triage_priority,
            "weather": weather_decision,
            "evac_urgency": evac_urgency,
            "resource_level": alloc_level,
        }
        route_req = "shortest" if evac_urgency == "HIGH" else "multiple"
        final_severity = zone["severity"]

        sup_reasoning = (
            f"Supervisor Agent reviewed all upstream outputs: "
            f"priority={triage_priority}, weather={weather_decision}, "
            f"evac_urgency={evac_urgency}, resources={alloc_level}. "
            f"Final zone severity confirmed as {final_severity.upper()}. "
            f"Routing strategy set to '{route_req}'."
        )

        record_log(
            agent_name="Supervisor Agent",
            zone_id=zone["id"],
            input_data=sup_inputs,
            parameters_used={"review_mode": "cross-validation"},
            thresholds_checked=[],
            decision=f"Final severity: {final_severity}, routing: {route_req}",
            outcome=f"Zone confirmed {final_severity.upper()}; {route_req} routing dispatched.",
            reasoning=sup_reasoning,
        )

        # ── 6. Feedback Agent ───────────────────────────────────
        evac_pct = round(current_evac / pop * 100, 1) if pop > 0 else 0
        fb_inputs = {"evacuated": current_evac, "population": pop, "evac_percent": evac_pct}
        fb_thresholds = [
            {"parameter": "evac_percent", "value": evac_pct, "threshold": 80, "exceeded": evac_pct >= 80},
        ]
        fb_status = "on_track" if evac_pct >= 50 else "lagging" if evac_pct >= 20 else "critical_delay"

        fb_reasoning = (
            f"Feedback Agent measured {evac_pct}% evacuation progress "
            f"({current_evac}/{pop}). "
        )
        if evac_pct >= 80:
            fb_reasoning += "Evacuation nearly complete — zone may be downgraded soon."
        elif evac_pct >= 50:
            fb_reasoning += "Progress is on track; maintaining current resource allocation."
        elif evac_pct >= 20:
            fb_reasoning += "Evacuation lagging behind target — recommending resource boost."
        else:
            fb_reasoning += "Critical delay detected — escalation recommended to Supervisor."

        record_log(
            agent_name="Feedback Agent",
            zone_id=zone["id"],
            input_data=fb_inputs,
            parameters_used={"target_evac_percent": 80},
            thresholds_checked=fb_thresholds,
            decision=f"Evacuation status: {fb_status}",
            outcome=f"Feedback loop reports {fb_status.replace('_', ' ')} at {evac_pct}%.",
            reasoning=fb_reasoning,
        )
