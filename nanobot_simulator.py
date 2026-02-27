# nanobot_simulator.py
import asyncio
import random
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
from websocket_manager import manager
from database import SessionLocal
from models import Nanobot, BotMetric, BotReading, Alert
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NanobotSimulator:
    def __init__(self):
        self.simulation_running = False
        self.bots_data: Dict[int, Dict[str, Any]] = {}  # bot_id -> bot data
        self.update_interval = 2  # seconds
        
    async def start_simulation(self):
        """Start the nanobot simulation"""
        self.simulation_running = True
        logger.info("Nanobot simulation started")
        
        while self.simulation_running:
            try:
                await self.update_all_bots()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in simulation: {e}")
                await asyncio.sleep(5)
    
    async def stop_simulation(self):
        """Stop the nanobot simulation"""
        self.simulation_running = False
        logger.info("Nanobot simulation stopped")
    
    async def update_all_bots(self):
        """Update all active bots with new data"""
        db = SessionLocal()
        try:
            # Get all active bots from database
            bots = db.query(Nanobot).filter(Nanobot.status == "active").all()
            
            for bot in bots:
                await self.update_bot(bot, db)
                
        except Exception as e:
            logger.error(f"Error updating bots: {e}")
        finally:
            db.close()
    
    async def update_bot(self, bot: Nanobot, db):
        """Update a single bot with simulated data"""
        
        # Get or create bot metrics
        metrics = db.query(BotMetric).filter(BotMetric.bot_id == bot.id).first()
        if not metrics:
            metrics = BotMetric(bot_id=bot.id)
            db.add(metrics)
        
        # Simulate realistic vital sign changes
        old_glucose = metrics.glucose
        
        # Update metrics with realistic variations
        metrics.glucose += random.uniform(-3, 3)
        metrics.glucose = max(70, min(180, metrics.glucose))
        
        metrics.heart_rate += random.uniform(-2, 2)
        metrics.heart_rate = max(60, min(100, metrics.heart_rate))
        
        metrics.temperature += random.uniform(-0.1, 0.1)
        metrics.temperature = max(36.0, min(38.0, metrics.temperature))
        
        metrics.troponin += random.uniform(-0.002, 0.002)
        metrics.troponin = max(0.0, min(0.1, metrics.troponin))
        
        metrics.oxygen += random.uniform(-0.5, 0.5)
        metrics.oxygen = max(90, min(100, metrics.oxygen))
        
        metrics.ph_level += random.uniform(-0.02, 0.02)
        metrics.ph_level = max(7.35, min(7.45, metrics.ph_level))
        
        # Update blood pressure
        metrics.blood_pressure_sys += random.randint(-3, 3)
        metrics.blood_pressure_sys = max(100, min(140, metrics.blood_pressure_sys))
        
        metrics.blood_pressure_dia += random.randint(-2, 2)
        metrics.blood_pressure_dia = max(60, min(90, metrics.blood_pressure_dia))
        
        # Calculate health score
        health_score = 100
        if metrics.glucose > 140: health_score -= 15
        elif metrics.glucose > 120: health_score -= 5
        
        if metrics.heart_rate > 90: health_score -= 10
        elif metrics.heart_rate < 50: health_score -= 15
        
        if metrics.temperature > 37.8: health_score -= 10
        elif metrics.temperature < 36.0: health_score -= 5
        
        if metrics.troponin > 0.04: health_score -= 30
        
        if metrics.oxygen < 92: health_score -= 20
        
        metrics.health_score = max(0, health_score)
        
        # Determine risk level
        if metrics.health_score < 50:
            metrics.risk_level = "Critical"
        elif metrics.health_score < 70:
            metrics.risk_level = "High"
        elif metrics.health_score < 85:
            metrics.risk_level = "Moderate"
        else:
            metrics.risk_level = "Low"
        
        # Update bot position (simulate movement through bloodstream)
        bot.current_x += random.uniform(-2, 2)
        bot.current_y += random.uniform(-2, 2)
        
        # Keep within bounds (0-100)
        bot.current_x = max(0, min(100, bot.current_x))
        bot.current_y = max(0, min(100, bot.current_y))
        
        bot.last_active = datetime.utcnow()
        
        # Save reading
        if random.random() < 0.3:  # 30% chance to save a reading
            reading = BotReading(
                bot_id=bot.id,
                metric_type="glucose",
                value=metrics.glucose,
                unit="mg/dL"
            )
            db.add(reading)
        
        db.commit()
        
        # Check for alerts
        await self.check_alerts(bot, metrics, db)
        
        # Send WebSocket update
        await self.send_bot_update(bot, metrics)
        
        logger.debug(f"Updated bot {bot.bot_id}: Health={metrics.health_score}, Risk={metrics.risk_level}")
    
    async def check_alerts(self, bot: Nanobot, metrics: BotMetric, db):
        """Check for abnormal values and create alerts"""
        
        alerts = []
        
        # Check glucose
        if metrics.glucose > 140:
            alerts.append({
                "type": "critical" if metrics.glucose > 180 else "warning",
                "metric": "glucose",
                "value": metrics.glucose,
                "threshold": 140,
                "message": f"High glucose level: {metrics.glucose:.1f} mg/dL"
            })
        elif metrics.glucose < 70:
            alerts.append({
                "type": "warning",
                "metric": "glucose",
                "value": metrics.glucose,
                "threshold": 70,
                "message": f"Low glucose level: {metrics.glucose:.1f} mg/dL"
            })
        
        # Check heart rate
        if metrics.heart_rate > 100:
            alerts.append({
                "type": "critical",
                "metric": "heart_rate",
                "value": metrics.heart_rate,
                "threshold": 100,
                "message": f"Tachycardia: {metrics.heart_rate:.0f} bpm"
            })
        elif metrics.heart_rate < 50:
            alerts.append({
                "type": "critical",
                "metric": "heart_rate",
                "value": metrics.heart_rate,
                "threshold": 50,
                "message": f"Bradycardia: {metrics.heart_rate:.0f} bpm"
            })
        
        # Check troponin (cardiac marker)
        if metrics.troponin > 0.04:
            alerts.append({
                "type": "critical",
                "metric": "troponin",
                "value": metrics.troponin,
                "threshold": 0.04,
                "message": f"Elevated troponin: {metrics.troponin:.3f} ng/mL - Possible cardiac event"
            })
        
        # Check oxygen
        if metrics.oxygen < 92:
            alerts.append({
                "type": "critical" if metrics.oxygen < 88 else "warning",
                "metric": "oxygen",
                "value": metrics.oxygen,
                "threshold": 92,
                "message": f"Low oxygen saturation: {metrics.oxygen:.1f}%"
            })
        
        # Create alerts in database and send via WebSocket
        for alert_data in alerts:
            # Check if similar alert already exists and not resolved
            existing = db.query(Alert).filter(
                Alert.bot_id == bot.id,
                Alert.metric == alert_data["metric"],
                Alert.is_resolved == False
            ).first()
            
            if not existing:
                alert = Alert(
                    patient_id=bot.patient_id,
                    bot_id=bot.id,
                    alert_type=alert_data["type"],
                    metric=alert_data["metric"],
                    value=alert_data["value"],
                    threshold=alert_data["threshold"],
                    message=alert_data["message"]
                )
                db.add(alert)
                db.commit()
                
                # Send WebSocket alert
                await manager.send_to_patient(
                    bot.patient_id,
                    {
                        "type": "alert",
                        "data": {
                            "bot_id": bot.bot_id,
                            "alert_type": alert_data["type"],
                            "metric": alert_data["metric"],
                            "message": alert_data["message"],
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                )
                logger.warning(f"Alert created for bot {bot.bot_id}: {alert_data['message']}")
    
    async def send_bot_update(self, bot: Nanobot, metrics: BotMetric):
        """Send bot update via WebSocket"""
        update_data = {
            "type": "bot_update",
            "data": {
                "bot_id": bot.bot_id,
                "patient_id": bot.patient_id,
                "timestamp": datetime.utcnow().isoformat(),
                "position": {
                    "x": bot.current_x,
                    "y": bot.current_y
                },
                "metrics": {
                    "glucose": metrics.glucose,
                    "heart_rate": metrics.heart_rate,
                    "temperature": metrics.temperature,
                    "troponin": metrics.troponin,
                    "oxygen": metrics.oxygen,
                    "ph_level": metrics.ph_level,
                    "blood_pressure": {
                        "systolic": metrics.blood_pressure_sys,
                        "diastolic": metrics.blood_pressure_dia
                    }
                },
                "health_score": metrics.health_score,
                "risk_level": metrics.risk_level,
                "battery": bot.battery_level
            }
        }
        
        await manager.send_to_patient(bot.patient_id, update_data)

# Create simulator instance
simulator = NanobotSimulator()