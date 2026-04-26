"""
RakshaSetu Phase 4 — Execution Trace Logger
Records every node entry/exit with timestamps, decisions, and routing info.

Usage inside agent nodes:
    trace = trace_entry("zone_analyst", state)
    # ... agent logic ...
    trace_exit(trace, decision="EVACUATE", routed_to="resource_allocator")
    return { "execution_trace": [trace], ... }
"""

import time
import logging

logger = logging.getLogger("raksha.tracer")


def trace_entry(node_name: str, state: dict) -> dict:
    """
    Create a trace record when a node begins execution.

    Args:
        node_name: Name of the LangGraph node
        state: Current graph state

    Returns:
        Mutable trace dict to be updated at exit
    """
    trace = {
        "node": node_name,
        "timestamp_enter": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "timestamp_exit": None,
        "state_snapshot": {
            "zone_id": state.get("zone_id", "?"),
            "feedback_loop_count": state.get("feedback_loop_count", 0),
            "supervisor_interventions": state.get("supervisor_interventions", 0),
            "weather_recheck_count": state.get("weather_recheck_count", 0),
            "notification_retry_count": state.get("notification_retry_count", 0),
        },
        "decision": None,
        "confidence": None,
        "routed_to": None,
        "duration_ms": None,
    }
    trace["_start_time"] = time.monotonic()

    logger.info(
        f"━━ TRACE ▶ [{node_name}] entered | zone={state.get('zone_id', '?')} | "
        f"loops: feedback={state.get('feedback_loop_count', 0)}, "
        f"supervisor={state.get('supervisor_interventions', 0)}"
    )
    return trace


def trace_exit(
    trace: dict,
    decision: str = "",
    confidence: float = 0.0,
    routed_to: str = "",
) -> dict:
    """
    Finalize a trace record when a node finishes execution.

    Args:
        trace: The trace dict from trace_entry()
        decision: The decision this node made
        confidence: Confidence level
        routed_to: Which node the router should send to next

    Returns:
        The finalized trace dict (also mutated in-place)
    """
    elapsed = time.monotonic() - trace.pop("_start_time", time.monotonic())
    trace["timestamp_exit"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    trace["decision"] = decision
    trace["confidence"] = round(confidence, 2)
    trace["routed_to"] = routed_to
    trace["duration_ms"] = round(elapsed * 1000, 1)

    logger.info(
        f"━━ TRACE ◀ [{trace['node']}] exited | decision={decision} | "
        f"confidence={confidence:.2f} | routed_to={routed_to} | "
        f"duration={trace['duration_ms']}ms"
    )
    return trace


def make_routing_record(from_node: str, to_node: str, reason: str) -> dict:
    """
    Create a routing history entry for the routing_history append-only list.

    Args:
        from_node: Source node name
        to_node: Target node name
        reason: Why this route was chosen

    Returns:
        Routing record dict
    """
    record = {
        "from": from_node,
        "to": to_node,
        "reason": reason,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    logger.info(f"━━ ROUTE  [{from_node}] ──▶ [{to_node}] reason: {reason}")
    return record


def format_trace_table(execution_trace: list[dict]) -> str:
    """
    Format the full execution trace as a readable table for CLI output.

    Args:
        execution_trace: List of trace dicts from the final state

    Returns:
        Formatted string table
    """
    lines = []
    lines.append("")
    lines.append("┏" + "━" * 98 + "┓")
    lines.append("┃{:^98s}┃".format(" EXECUTION TRACE "))
    lines.append("┣" + "━" * 4 + "┳" + "━" * 22 + "┳" + "━" * 20 + "┳" + "━" * 22 + "┳" + "━" * 10 + "┳" + "━" * 16 + "┫")
    lines.append(
        "┃{:^4s}┃{:^22s}┃{:^20s}┃{:^22s}┃{:^10s}┃{:^16s}┃".format(
            "#", "Node", "Decision", "Routed To", "Conf.", "Duration"
        )
    )
    lines.append("┣" + "━" * 4 + "╋" + "━" * 22 + "╋" + "━" * 20 + "╋" + "━" * 22 + "╋" + "━" * 10 + "╋" + "━" * 16 + "┫")

    for i, t in enumerate(execution_trace, 1):
        node = (t.get("node") or "?")[:20]
        decision = (t.get("decision") or "—")[:18]
        routed = (t.get("routed_to") or "—")[:20]
        conf = f"{t.get('confidence', 0):.2f}" if t.get("confidence") is not None else "—"
        dur = f"{t.get('duration_ms', 0):.0f}ms" if t.get("duration_ms") is not None else "—"
        lines.append(
            "┃{:^4d}┃ {:<21s}┃ {:<19s}┃ {:<21s}┃{:^10s}┃{:^16s}┃".format(
                i, node, decision, routed, conf, dur
            )
        )

    lines.append("┗" + "━" * 4 + "┻" + "━" * 22 + "┻" + "━" * 20 + "┻" + "━" * 22 + "┻" + "━" * 10 + "┻" + "━" * 16 + "┛")
    lines.append("")

    return "\n".join(lines)


def format_routing_table(routing_history: list[dict]) -> str:
    """
    Format the routing history as a readable flow diagram.

    Args:
        routing_history: List of routing records

    Returns:
        Formatted string
    """
    lines = []
    lines.append("")
    lines.append("┏" + "━" * 80 + "┓")
    lines.append("┃{:^80s}┃".format(" ROUTING HISTORY (Decision-Driven Transitions) "))
    lines.append("┣" + "━" * 4 + "┳" + "━" * 22 + "┳" + "━" * 22 + "┳" + "━" * 28 + "┫")
    lines.append(
        "┃{:^4s}┃{:^22s}┃{:^22s}┃{:^28s}┃".format("#", "From", "To", "Reason")
    )
    lines.append("┣" + "━" * 4 + "╋" + "━" * 22 + "╋" + "━" * 22 + "╋" + "━" * 28 + "┫")

    for i, r in enumerate(routing_history, 1):
        frm = (r.get("from") or "?")[:20]
        to = (r.get("to") or "?")[:20]
        reason = (r.get("reason") or "—")[:26]
        lines.append(
            "┃{:^4d}┃ {:<21s}┃ {:<21s}┃ {:<27s}┃".format(i, frm, to, reason)
        )

    lines.append("┗" + "━" * 4 + "┻" + "━" * 22 + "┻" + "━" * 22 + "┻" + "━" * 28 + "┛")
    lines.append("")

    return "\n".join(lines)
