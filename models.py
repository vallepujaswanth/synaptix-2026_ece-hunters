# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, unique=True, index=True)
    name = Column(String)
    age = Column(Integer)
    blood_type = Column(String)
    allergies = Column(String, nullable=True)
    medications = Column(JSON, default=[])  # Store as JSON array
    risk_profile = Column(String, default="Moderate")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    nanobots = relationship("Nanobot", back_populates="patient")
    health_records = relationship("HealthRecord", back_populates="patient")
    alerts = relationship("Alert", back_populates="patient")

class Nanobot(Base):
    __tablename__ = "nanobots"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(String, unique=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    status = Column(String, default="active")  # active, inactive, degraded
    battery_level = Column(Float, default=100.0)
    firmware_version = Column(String, default="1.0.0")
    deployment_date = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Current position (simulated)
    current_x = Column(Float, default=0.0)
    current_y = Column(Float, default=0.0)
    
    # Relationships
    patient = relationship("Patient", back_populates="nanobots")
    readings = relationship("BotReading", back_populates="nanobot")
    metrics = relationship("BotMetric", back_populates="nanobot", uselist=False)

class BotMetric(Base):
    __tablename__ = "bot_metrics"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("nanobots.id"))
    
    # Health metrics
    glucose = Column(Float, default=95.0)
    heart_rate = Column(Float, default=72.0)
    temperature = Column(Float, default=36.6)
    troponin = Column(Float, default=0.01)
    oxygen = Column(Float, default=98.0)
    ph_level = Column(Float, default=7.4)
    blood_pressure_sys = Column(Integer, default=120)
    blood_pressure_dia = Column(Integer, default=80)
    
    # Risk assessment
    health_score = Column(Integer, default=100)
    risk_level = Column(String, default="Low")  # Low, Moderate, High, Critical
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    nanobot = relationship("Nanobot", back_populates="metrics")

class BotReading(Base):
    __tablename__ = "bot_readings"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("nanobots.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    metric_type = Column(String)  # glucose, heart_rate, etc.
    value = Column(Float)
    unit = Column(String)
    
    # Relationships
    nanobot = relationship("Nanobot", back_populates="readings")

class HealthRecord(Base):
    __tablename__ = "health_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    record_type = Column(String)  # checkup, test, emergency
    diagnosis = Column(String, nullable=True)
    prescription = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="health_records")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    bot_id = Column(Integer, ForeignKey("nanobots.id"), nullable=True)
    alert_type = Column(String)  # critical, warning, info
    metric = Column(String)
    value = Column(Float)
    threshold = Column(Float)
    message = Column(String)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="alerts")