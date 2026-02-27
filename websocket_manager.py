# websocket_manager.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Store active connections: {patient_id: [websockets]}
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Store bot-specific connections: {bot_id: websocket}
        self.bot_connections: Dict[str, WebSocket] = {}

    async def connect_patient(self, websocket: WebSocket, patient_id: int):
        await websocket.accept()
        if patient_id not in self.active_connections:
            self.active_connections[patient_id] = []
        self.active_connections[patient_id].append(websocket)
        logger.info(f"Patient {patient_id} connected. Total connections: {len(self.active_connections[patient_id])}")

    async def connect_bot(self, websocket: WebSocket, bot_id: str):
        await websocket.accept()
        self.bot_connections[bot_id] = websocket
        logger.info(f"Bot {bot_id} connected")

    def disconnect_patient(self, websocket: WebSocket, patient_id: int):
        if patient_id in self.active_connections:
            self.active_connections[patient_id].remove(websocket)
            if not self.active_connections[patient_id]:
                del self.active_connections[patient_id]
        logger.info(f"Patient {patient_id} disconnected")

    def disconnect_bot(self, bot_id: str):
        if bot_id in self.bot_connections:
            del self.bot_connections[bot_id]
        logger.info(f"Bot {bot_id} disconnected")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def send_to_patient(self, patient_id: int, message: Dict[str, Any]):
        if patient_id in self.active_connections:
            for connection in self.active_connections[patient_id]:
                try:
                    await connection.send_json(message)
                except:
                    # Remove dead connections
                    self.active_connections[patient_id].remove(connection)

    async def send_to_bot(self, bot_id: str, message: Dict[str, Any]):
        if bot_id in self.bot_connections:
            try:
                await self.bot_connections[bot_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending to bot {bot_id}: {e}")
                self.disconnect_bot(bot_id)

    async def broadcast_to_all_patients(self, message: Dict[str, Any]):
        for patient_id in self.active_connections:
            await self.send_to_patient(patient_id, message)

    async def broadcast_to_all_bots(self, message: Dict[str, Any]):
        for bot_id in self.bot_connections:
            await self.send_to_bot(bot_id, message)

# Create a single instance
manager = ConnectionManager()