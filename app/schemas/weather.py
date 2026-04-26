"""Schemas for weather simulation payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WeatherSimulationRequest(BaseModel):
    """Simulated weather event to trigger agent responses."""

    zone_id: UUID
    event_type: str = Field(
        ...,
        description="Type of weather event: flood | cyclone | earthquake | heatwave | wildfire",
    )
    intensity: float = Field(..., ge=0.0, le=10.0, description="0-10 severity scale")
    wind_speed_kmh: Optional[float] = None
    rainfall_mm: Optional[float] = None
    temperature_c: Optional[float] = None
    description: Optional[str] = None


class WeatherSimulationResponse(BaseModel):
    """Response after weather event has been processed."""

    id: UUID = Field(default_factory=uuid4)
    zone_id: UUID
    event_type: str
    intensity: float
    risk_delta: float = Field(
        ..., description="Change applied to zone risk_score"
    )
    agents_triggered: list[str] = Field(
        default_factory=list,
        description="Names of agents activated by this event",
    )
    timestamp: datetime

    model_config = {"from_attributes": True}
