"""Schemas for detection payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DetectionCreate(BaseModel):
    """Incoming detection from a sensor / drone / camera."""

    zone_id: UUID
    count: int = Field(..., ge=0, description="Number of people / objects detected")
    metadata: Optional[dict] = None


class DetectionResponse(BaseModel):
    """Detection record returned from the API."""

    id: UUID = Field(default_factory=uuid4)
    zone_id: UUID
    count: int
    timestamp: datetime
    metadata: Optional[dict] = None

    model_config = {"from_attributes": True}
