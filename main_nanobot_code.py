# main.py
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
from datetime import datetime
import json

from database import SessionLocal, engine, Base
from models import *
from schemas import *
from websocket_manager import manager
from nanobot_simulator import simulator
import logging

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize app
app = FastAPI(title="Vita-Bot Nanobot Health Monitor API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Start the nanobot simulator on app startup"""
    asyncio.create_task(simulator.start_simulation())
    logger.info("Application started, simulator running")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Stop the nanobot simulator on app shutdown"""
    await simulator.stop_simulation()
    logger.info("Application stopped")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Vita-Bot Nanobot Health Monitor API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": [
            "/docs",
            "/patients",
            "/nanobots",
            "/alerts",
            "/ws/{patient_id}"
        ]
    }

# ============= PATIENT ENDPOINTS =============

@app.post("/patients/", response_model=Patient)
async def create_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    """Create a new patient"""
    db_patient = Patient(
        patient_id=patient.patient_id,
        name=patient.name,
        age=patient.age,
        blood_type=patient.blood_type,
        allergies=patient.allergies,
        medications=patient.medications,
        risk_profile=patient.risk_profile
    )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

@app.get("/patients/", response_model=List[Patient])
async def get_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all patients"""
    patients = db.query(Patient).offset(skip).limit(limit).all()
    return patients

@app.get("/patients/{patient_id}", response_model=Patient)
async def get_patient(patient_id: str, db: Session = Depends(get_db)):
    """Get patient by ID"""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@app.put("/patients/{patient_id}", response_model=Patient)
async def update_patient(patient_id: str, patient_update: PatientUpdate, db: Session = Depends(get_db)):
    """Update patient information"""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    for key, value in patient_update.dict(exclude_unset=True).items():
        setattr(patient, key, value)
    
    patient.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(patient)
    return patient

@app.delete("/patients/{patient_id}")
async def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    """Delete a patient"""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db.delete(patient)
    db.commit()
    return {"message": "Patient deleted successfully"}

# ============= NANOBOT ENDPOINTS =============

@app.post("/nanobots/", response_model=Nanobot)
async def create_nanobot(bot: NanobotCreate, db: Session = Depends(get_db)):
    """Deploy a new nanobot"""
    # Check if patient exists
    patient = db.query(Patient).filter(Patient.id == bot.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db_bot = Nanobot(
        bot_id=bot.bot_id,
        patient_id=bot.patient_id,
        status=bot.status,
        battery_level=bot.battery_level,
        firmware_version=bot.firmware_version,
        current_x=bot.current_x,
        current_y=bot.current_y
    )
    db.add(db_bot)
    db.commit()
    db.refresh(db_bot)
    
    # Create initial metrics
    metrics = BotMetric(bot_id=db_bot.id)
    db.add(metrics)
    db.commit()
    
    return db_bot

@app.get("/nanobots/", response_model=List[Nanobot])
async def get_nanobots(patient_id: Optional[int] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all nanobots, optionally filtered by patient_id or status"""
    query = db.query(Nanobot)
    
    if patient_id:
        query = query.filter(Nanobot.patient_id == patient_id)
    if status:
        query = query.filter(Nanobot.status == status)
    
    bots = query.all()
    return bots

@app.get("/nanobots/{bot_id}", response_model=Nanobot)
async def get_nanobot(bot_id: str, db: Session = Depends(get_db)):
    """Get nanobot by ID"""
    bot = db.query(Nanobot).filter(Nanobot.bot_id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Nanobot not found")
    return bot

@app.put("/nanobots/{bot_id}", response_model=Nanobot)
async def update_nanobot(bot_id: str, bot_update: NanobotUpdate, db: Session = Depends(get_db)):
    """Update nanobot status or position"""
    bot = db.query(Nanobot).filter(Nanobot.bot_id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Nanobot not found")
    
    for key, value in bot_update.dict(exclude_unset=True).items():
        setattr(bot, key, value)
    
    bot.last_active = datetime.utcnow()
    db.commit()
    db.refresh(bot)
    return bot

@app.get("/nanobots/{bot_id}/readings", response_model=List[BotReading])
async def get_bot_readings(bot_id: str, limit: int = 100, db: Session = Depends(get_db)):
    """Get recent readings from a specific nanobot"""
    bot = db.query(Nanobot).filter(Nanobot.bot_id == bot_id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Nanobot not found")
    
    readings = db.query(BotReading).filter(BotReading.bot_id == bot.id).order_by(BotReading.timestamp.desc()).limit(limit).all()
    return readings

# ============= ALERT ENDPOINTS =============

@app.get("/alerts/", response_model=List[Alert])
async def get_alerts(patient_id: Optional[int] = None, resolved: Optional[bool] = None, db: Session = Depends(get_db)):
    """Get all alerts, optionally filtered"""
    query = db.query(Alert)
    
    if patient_id:
        query = query.filter(Alert.patient_id == patient_id)
    if resolved is not None:
        query = query.filter(Alert.is_resolved == resolved)
    
    alerts = query.order_by(Alert.created_at.desc()).all()
    return alerts

@app.put("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """Mark an alert as resolved"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Alert resolved successfully"}

# ============= DASHBOARD ENDPOINTS =============

@app.get("/dashboard/{patient_id}")
async def get_dashboard(patient_id: str, db: Session = Depends(get_db)):
    """Get comprehensive dashboard data for a patient"""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get active bots
    bots = db.query(Nanobot).filter(Nanobot.patient_id == patient.id).all()
    active_bots = len([b for b in bots if b.status == "active"])
    
    # Get recent alerts
    alerts = db.query(Alert).filter(
        Alert.patient_id == patient.id,
        Alert.is_resolved == False
    ).order_by(Alert.created_at.desc()).limit(10).all()
    
    # Get recent readings
    recent_readings = []
    for bot in bots[:5]:  # Limit to 5 bots
        readings = db.query(BotReading).filter(
            BotReading.bot_id == bot.id
        ).order_by(BotReading.timestamp.desc()).limit(20).all()
        recent_readings.extend(readings)
    
    # Calculate average health score
    health_scores = []
    for bot in bots:
        metrics = db.query(BotMetric).filter(BotMetric.bot_id == bot.id).first()
        if metrics:
            health_scores.append(metrics.health_score)
    
    avg_health_score = sum(health_scores) // len(health_scores) if health_scores else 100
    
    # Calculate risk factors
    risk_factors = {
        "cardiac": 0,
        "diabetes": 0,
        "hypertension": 0,
        "hypoxia": 0
    }
    
    for bot in bots:
        metrics = db.query(BotMetric).filter(BotMetric.bot_id == bot.id).first()
        if metrics:
            if metrics.troponin > 0.04:
                risk_factors["cardiac"] += 1
            if metrics.glucose > 140:
                risk_factors["diabetes"] += 1
            if metrics.blood_pressure_sys > 130:
                risk_factors["hypertension"] += 1
            if metrics.oxygen < 92:
                risk_factors["hypoxia"] += 1
    
    # Normalize risk factors
    total_bots = len(bots)
    for key in risk_factors:
        risk_factors[key] = (risk_factors[key] / total_bots * 100) if total_bots > 0 else 0
    
    return {
        "patient": patient,
        "active_bots": active_bots,
        "total_bots": len(bots