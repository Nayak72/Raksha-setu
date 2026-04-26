"""
RakshaSetu — Data Models
Python dataclasses representing the core database entities and execution logs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class Zone:
    """Geographic zone monitored by the system."""
    id: str
    name: str
    latitude: float
    longitude: float
    terrain_type: str  # "flat", "hilly", "coastal", "urban", "forest"
    elevation_m: float
    area_sq_km: float
    population_density: float  # people per sq km
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WeatherRecord:
    """Historical or simulated weather data point."""
    id: Optional[int] = None
    zone_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    rainfall_mm: float = 0.0
    wind_speed_kmh: float = 0.0
    humidity_pct: float = 0.0
    temperature_c: float = 0.0
    severity: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    source: str = "simulation"  # "simulation" or "actual"


@dataclass
class Shelter:
    """Emergency shelter with geospatial position."""
    id: str = ""
    name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    capacity: int = 0
    current_occupancy: int = 0
    shelter_type: str = "general"  # "general", "medical", "women_children"
    is_active: bool = True

    @property
    def occupancy_ratio(self) -> float:
        return self.current_occupancy / max(self.capacity, 1)

    @property
    def available_spots(self) -> int:
        return max(0, self.capacity - self.current_occupancy)


@dataclass
class Volunteer:
    """Field volunteer available for deployment."""
    id: str = ""
    name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    skill_type: str = "general"  # "general", "medical", "rescue", "logistics"
    is_available: bool = True
    current_workload: int = 0  # number of active assignments
    max_workload: int = 3


@dataclass
class Alert:
    """Notification alert sent via MQTT or dashboard."""
    id: Optional[int] = None
    zone_id: str = ""
    severity: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    message: str = ""
    topic: str = ""
    delivery_status: str = "pending"  # "pending", "sent", "acked", "failed"
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    acked_at: Optional[datetime] = None


@dataclass
class Assignment:
    """Resource assignment linking volunteers/shelters to zones."""
    id: Optional[int] = None
    zone_id: str = ""
    volunteer_id: Optional[str] = None
    shelter_id: Optional[str] = None
    assignment_type: str = "volunteer"  # "volunteer" or "shelter"
    status: str = "active"  # "active", "completed", "cancelled"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DetectionEvent:
    """Mock YOLO detection event for zone monitoring."""
    id: Optional[int] = None
    zone_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    crowd_density: float = 0.0  # people per unit area
    flood_level: float = 0.0  # 0-1 scale
    structural_damage: float = 0.0  # 0-1 scale
    fire_detected: bool = False
    vehicle_count: int = 0
    confidence: float = 0.0


@dataclass
class AgentExecutionLog:
    """
    Log of an agent's execution for a particular zone and event.
    Stores the full reasoning and output to power frontend visualization.
    """
    id: Optional[int] = None
    zone_id: str = ""
    agent_name: str = ""  # "weather", "zone_analyst", "resource_allocator", "notifier", "feedback", "supervisor"
    decision: str = ""
    reasoning_steps: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    confidence: float = 0.0
    routing_decision: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
