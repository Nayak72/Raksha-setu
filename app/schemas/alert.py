"""Schemas for alert payloads."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertCreate(BaseModel):
    """Payload to broadcast an alert."""

    zone: str = Field(..., description="Zone identifier or name")
    message: str = Field(..., min_length=1, max_length=1000)
    severity: Severity = Severity.MEDIUM


class AlertResponse(BaseModel):
    """Alert record returned from the API."""

    id: UUID = Field(default_factory=uuid4)
    zone: str
    message: str
    severity: Severity
    timestamp: datetime

    model_config = {"from_attributes": True}


class AcknowledgmentCreate(BaseModel):
    """Device acknowledgment of a received alert."""

    device_id: str
    alert_id: UUID
    status: str = Field(default="received", description="received | read | acted")


class AcknowledgmentResponse(BaseModel):
    """Acknowledgment record returned from the API."""

    device_id: str
    alert_id: UUID
    status: str
    timestamp: datetime

    model_config = {"from_attributes": True}
