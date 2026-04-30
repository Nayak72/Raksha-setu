"""
RakshaSetu Phase 4 — Enhanced LangGraph State
Non-linear graph state with execution trace, routing history, and supervisor fields.

Key additions over Phase 3:
  - triage_result:              Entry-point triage classification
  - execution_trace:            Full ordered log of every node entry/exit (append-only)
  - routing_history:            Ordered record of {from, to, reason} transitions (append-only)
  - supervisor_interventions:   Count of supervisor re-routes (loop guard)
  - weather_recheck_count:      Prevents infinite weather self-loops
  - notification_retry_count:   Prevents infinite notifier self-loops
"""

import operator
from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


# ── Sub-schemas (same as Phase 3) ─────────────────────────────

class WeatherOutput(TypedDict):
    """Output schema for Weather Simulation Agent."""
    zone: str
    rainfall: float
    wind_speed: float
    humidity: float
    temperature: float
    severity: str
    reasoning_steps: list[str]
    tools_used: list[str]
    confidence: float
    routing_decision: str


class ZoneAnalysisOutput(TypedDict):
    """Output schema for Zone Analyst Agent."""
    decision: str
    priority_score: float
    reasoning_steps: list[str]
    tools_used: list[str]
    retrieved_context: list[str]
    confidence: float
    routing_decision: str


class ResourcePlanOutput(TypedDict):
    """Output schema for Resource Allocator Agent."""
    volunteer_assignments: list[dict]
    shelter_assignments: list[dict]
    escalation_needed: bool
    reasoning_steps: list[str]
    tools_used: list[str]
    confidence: float
    routing_decision: str


class NotificationOutput(TypedDict):
    """Output schema for Notifier Agent."""
    topic: str
    reasoning_steps: list[str]
    tools_used: list[str]
    delivery_status: str
    confidence: float
    routing_decision: str


class FeedbackOutput(TypedDict):
    """Output schema for Feedback Agent."""
    success: bool
    action: str  # "none", "re_trigger", "escalate", "renotify"
    reasoning_steps: list[str]
    confidence: float
    routing_decision: str


class SupervisorOutput(TypedDict):
    """Output schema for Supervisor Agent."""
    final_decision: str
    conflicts_resolved: list[str]
    reasoning_steps: list[str]
    confidence: float
    routing_decision: str  # "resolved" | "override_evacuate" | "override_reanalyze" | "override_renotify" | "terminal_escalation"


class TriageOutput(TypedDict):
    """Output schema for Triage Agent."""
    severity: str  # "high" | "medium" | "low"
    composite_score: float
    reasoning_steps: list[str]
    confidence: float
    routing_decision: str


# ── Master State ──────────────────────────────────────────────

class AgentState(TypedDict):
    """
    Master state for the Phase 4 non-linear LangGraph pipeline.
    Every agent reads from and writes to this shared state.

    Append-only fields use operator.add reducer so each node's
    entries are concatenated, never overwritten.
    """

    # --- Input ---
    zone_id: str

    # --- Mock YOLO detection data ---
    detection_data: Optional[dict]

    # --- Triage (NEW — Phase 4) ---
    triage_result: Optional[TriageOutput]

    # --- Agent Outputs ---
    weather_data: Optional[WeatherOutput]
    zone_analysis: Optional[ZoneAnalysisOutput]
    resource_plan: Optional[ResourcePlanOutput]
    notification_result: Optional[NotificationOutput]
    feedback: Optional[FeedbackOutput]
    supervisor_decision: Optional[SupervisorOutput]

    # --- Feedback loop ---
    feedback_loop_count: int
    should_retrigger: bool

    # --- Loop guards (NEW — Phase 4) ---
    supervisor_interventions: int
    weather_recheck_count: int
    notification_retry_count: int

    # --- Execution Trace (NEW — Phase 4, append-only) ---
    execution_trace: Annotated[list[dict], operator.add]
    routing_history: Annotated[list[dict], operator.add]

    # --- Message history for LLM context ---
    messages: Annotated[list[BaseMessage], add_messages]
