# schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Patient schemas
class PatientBase(BaseModel):
    patient_id: str
    name: str
    age: int
    blood_type: str
    allergies: Optional[str] = None
    medications: List[str] = []
    risk_profile: str = "Moderate"

class PatientCreate(PatientBase):
    pass

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    medications: Optional[List[str]] = None
    risk_profile: Optional[str] = None

class Patient(PatientBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Nanobot schemas
class BotMetricBase(BaseModel):
    glucose: float = 95.0
    heart_rate: float = 72.0
    temperature: float = 36.6
    troponin: float = 0.01
    oxygen: float = 98.0
    ph_level: float = 7.4
    blood_pressure_sys: int = 120
    blood_pressure_dia: int = 80
    health_score: int = 100
    risk_level: str = "Low"

class BotMetric(BotMetricBase):
    id: int
    bot_id: int
    updated_at: datetime
    
    class Config:
        from_attributes = True

class NanobotBase(BaseModel):
    bot_id: str
    status: str = "active"
    battery_level: float = 100.0
    firmware_version: str = "1.0.0"
    current_x: float = 0.0
    current_y: float = 0.0

class NanobotCreate(NanobotBase):
    patient_id: int

class Nanobot(NanobotBase):
    id: int
    patient_id: int
    deployment_date: datetime
    last_active: datetime
    metrics: Optional[BotMetric] = None
    
    class Config:
        from_attributes = True

class NanobotUpdate(BaseModel):
    status: Optional[str] = None
    battery_level: Optional[float] = None
    current_x: Optional[float] = None
    current_y: Optional[float] = None

# Reading schemas
class BotReadingBase(BaseModel):
    metric_type: str
    value: float
    unit: str

class BotReadingCreate(BotReadingBase):
    bot_id: int

class BotReading(BotReadingBase):
    id: int
    bot_id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True

# Alert schemas
class AlertBase(BaseModel):
    alert_type: str
    metric: str
    value: float
    threshold: float
    message: str

class AlertCreate(AlertBase):
    patient_id: int
    bot_id: Optional[int] = None

class Alert(AlertBase):
    id: int
    patient_id: int
    bot_id: Optional[int]
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# WebSocket message schemas
class WSMessage(BaseModel):
    type: str  # "bot_update", "alert", "patient_data", "command"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BotUpdateMessage(BaseModel):
    bot_id: str
    patient_id: int
    metrics: BotMetricBase
    position: Dict[str, float]

# Dashboard data
class DashboardData(BaseModel):
    patient: Patient
    active_bots: int
    total_bots: int
    health_score: int
    alerts: List[Alert]
    recent_readings: List[BotReading]
    risk_factors: Dict[str, float]