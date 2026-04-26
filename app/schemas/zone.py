"""Schemas for zones, volunteers, and shelters."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ─── Zones ───────────────────────────────────
class ZoneBase(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    risk_score: float = Field(default=0.0, ge=0.0, le=10.0)


class ZoneCreate(ZoneBase):
    pass


class ZoneResponse(ZoneBase):
    id: UUID = Field(default_factory=uuid4)

    model_config = {"from_attributes": True}


# ─── Volunteers ──────────────────────────────
class VolunteerBase(BaseModel):
    location: str = Field(..., description="GeoJSON point or lat,lon string")
    status: str = Field(default="available", description="available | dispatched | offline")
    skill_level: int = Field(default=1, ge=1, le=5)


class VolunteerCreate(VolunteerBase):
    pass


class VolunteerResponse(VolunteerBase):
    id: UUID = Field(default_factory=uuid4)
    last_assigned_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Shelters ────────────────────────────────
class ShelterBase(BaseModel):
    location: str = Field(..., description="GeoJSON point or lat,lon string")
    capacity: int = Field(..., ge=0)
    available_beds: int = Field(..., ge=0)


class ShelterCreate(ShelterBase):
    pass


class ShelterResponse(ShelterBase):
    id: UUID = Field(default_factory=uuid4)

    model_config = {"from_attributes": True}


# ─── System Status ───────────────────────────
class SystemStatus(BaseModel):
    """Aggregate system health snapshot."""

    status: str = "operational"
    mqtt_connected: bool = False
    pg_listener_active: bool = False
    active_zones: int = 0
    total_volunteers: int = 0
    available_volunteers: int = 0
    total_shelters: int = 0
    available_beds: int = 0
    pending_alerts: int = 0
    uptime_seconds: float = 0.0
