"""
RAKSHA AI — Pydantic Data Models
Defines all data structures used across the application.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ─── Enumerations ────────────────────────────────────────────────────────────

class IncidentType(str, Enum):
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    CYCLONE = "cyclone"
    FIRE = "fire"
    LANDSLIDE = "landslide"
    BUILDING_COLLAPSE = "building_collapse"
    CHEMICAL = "chemical"
    TSUNAMI = "tsunami"
    OTHER = "other"


class IncidentStatus(str, Enum):
    REPORTED = "reported"
    ACTIVE = "active"
    CONTAINED = "contained"
    RESOLVED = "resolved"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TriageColor(str, Enum):
    RED = "red"        # Immediate — life-threatening
    YELLOW = "yellow"  # Delayed — serious but stable
    GREEN = "green"    # Minimal — walking wounded
    BLACK = "black"    # Expectant — unlikely to survive


class ResponderRole(str, Enum):
    MEDICAL = "medical"
    SEARCH_RESCUE = "search_rescue"
    FIREFIGHTER = "firefighter"
    POLICE = "police"
    NDRF = "ndrf"
    VOLUNTEER = "volunteer"


class ResponderStatus(str, Enum):
    AVAILABLE = "available"
    DISPATCHED = "dispatched"
    ON_SCENE = "on_scene"
    OFF_DUTY = "off_duty"


class AlertSeverity(str, Enum):
    EXTREME = "extreme"
    SEVERE = "severe"
    MODERATE = "moderate"
    MINOR = "minor"


# ─── Geographic Types ────────────────────────────────────────────────────────

class GeoPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    address: Optional[str] = None


class GeoZone(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    coordinates: List[GeoPoint]
    type: str = "polygon"  # polygon, circle
    radius_km: Optional[float] = None


# ─── AI Assessment Models ─────────────────────────────────────────────────────

class ResourceEstimate(BaseModel):
    teams_required: int = 0
    medical_personnel: int = 0
    equipment: List[str] = []
    estimated_duration_hours: float = 0


class AIAssessment(BaseModel):
    model_config = {"protected_namespaces": ()}
    damage_severity: float = Field(..., ge=0, le=10)
    hazards: List[str] = []
    structural_integrity: str = "unknown"
    recommended_actions: List[str] = []
    triage_priority: Priority = Priority.MEDIUM
    resource_requirements: ResourceEstimate = ResourceEstimate()
    estimated_trapped: Optional[int] = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    model_used: str = "unknown"
    processing_time_ms: int = 0
    raw_response: Optional[str] = None


# ─── Incident Models ──────────────────────────────────────────────────────────

class IncidentCreate(BaseModel):
    type: IncidentType
    description: str
    coordinates: GeoPoint
    affected_count: Optional[int] = None
    language: str = "en"
    reported_by: Optional[str] = None


class Incident(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: IncidentType
    severity: float = 0.0
    status: IncidentStatus = IncidentStatus.REPORTED
    coordinates: GeoPoint
    affected_count: Optional[int] = None
    description: str
    images: List[str] = []
    ai_assessment: Optional[AIAssessment] = None
    responders_assigned: List[str] = []
    language: str = "en"
    reported_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class IncidentUpdate(BaseModel):
    status: Optional[IncidentStatus] = None
    severity: Optional[float] = None
    affected_count: Optional[int] = None
    description: Optional[str] = None


# ─── Responder Models ─────────────────────────────────────────────────────────

class ResponderCreate(BaseModel):
    name: str
    role: ResponderRole
    team: str
    phone: Optional[str] = None
    current_location: Optional[GeoPoint] = None
    skills: List[str] = []
    equipment: List[str] = []


class Responder(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: ResponderRole
    team: str
    phone: Optional[str] = None
    current_location: Optional[GeoPoint] = None
    status: ResponderStatus = ResponderStatus.AVAILABLE
    skills: List[str] = []
    equipment: List[str] = []
    incidents_assigned: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Triage Models ────────────────────────────────────────────────────────────

class TriageEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    incident_id: Optional[str] = None
    patient_id: str = Field(default_factory=lambda: f"P-{str(uuid.uuid4())[:6].upper()}")
    age_estimate: Optional[str] = None
    gender: Optional[str] = None
    symptoms: List[str] = []
    vitals: Dict[str, Any] = {}
    triage_color: TriageColor
    ai_notes: Optional[str] = None
    responder_id: Optional[str] = None
    location: Optional[GeoPoint] = None


class TriageCreate(BaseModel):
    incident_id: Optional[str] = None
    symptoms: List[str]
    age_estimate: Optional[str] = None
    gender: Optional[str] = None
    vitals: Dict[str, Any] = {}
    location: Optional[GeoPoint] = None
    location_accuracy: Optional[float] = None  # GPS accuracy in meters
    additional_notes: Optional[str] = None
    language: str = "en"


# ─── Alert Models ─────────────────────────────────────────────────────────────

class AlertCreate(BaseModel):
    title: str
    message: str
    severity: AlertSeverity
    affected_zones: List[str] = []
    coordinates: Optional[GeoPoint] = None
    radius_km: Optional[float] = None
    languages: List[str] = ["en"]
    incident_id: Optional[str] = None


class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    title: str
    message: str
    severity: AlertSeverity
    affected_zones: List[str] = []
    coordinates: Optional[GeoPoint] = None
    radius_km: Optional[float] = None
    languages: List[str] = ["en"]
    translations: Dict[str, str] = {}
    incident_id: Optional[str] = None
    created_by: Optional[str] = None


# ─── Chat Models ──────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    language: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    language: str = "en"
    incident_id: Optional[str] = None
    image_base64: Optional[str] = None
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    session_id: str
    message: str
    language: str
    model_used: str
    function_calls: List[Dict[str, Any]] = []
    function_results: List[Dict[str, Any]] = []
    processing_time_ms: int = 0


# ─── Damage Assessment Models ─────────────────────────────────────────────────

class AssessmentRequest(BaseModel):
    image_base64: str
    disaster_type: Optional[IncidentType] = None
    building_type: Optional[str] = None
    incident_id: Optional[str] = None
    language: str = "en"
    coordinates: Optional[GeoPoint] = None


# ─── Dispatch Models ──────────────────────────────────────────────────────────

class DispatchRequest(BaseModel):
    incident_id: str
    responder_id: Optional[str] = None  # If None, auto-select nearest
    priority: Priority = Priority.HIGH
    notes: Optional[str] = None


class DispatchResult(BaseModel):
    success: bool
    responder: Optional[Responder] = None
    dispatch_time: datetime = Field(default_factory=datetime.utcnow)
    eta_minutes: Optional[float] = None
    message: str


# ─── System Status ────────────────────────────────────────────────────────────

class SystemStatus(BaseModel):
    model_config = {"protected_namespaces": ()}
    status: str = "operational"
    version: str = "1.0.0"
    online: bool = False
    model_available: bool = False
    model_type: str = "none"  # "cloud", "local", "none"
    active_incidents: int = 0
    available_responders: int = 0
    db_status: str = "unknown"
    uptime_seconds: float = 0
