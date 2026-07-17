"""
WebSocket Routes for Real-time Updates.
"""

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request

from ragpipe.domain.events.events import DomainEvent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info("WebSocket connected. Total: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("WebSocket disconnected. Total: %d", len(self.active_connections))

    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients."""
        async with self._lock:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except Exception:
                    disconnected.append(connection)
                    
            for conn in disconnected:
                self.active_connections.remove(conn)

    def handle_domain_event(self, event: DomainEvent):
        """Callback to handle domain events and broadcast them."""
        # Need to convert datetimes to ISO strings for JSON serialization
        from enum import Enum
        def serialize_dt(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(f"Type {type(obj)} not serializable")
            
        try:
            event_dict = asdict(event)
            event_json = json.dumps({
                "type": "domain_event",
                "event": event_dict
            }, default=serialize_dt)
            
            # Create a background task for the broadcast so we don't block the event bus
            asyncio.create_task(self.broadcast(event_json))
        except Exception as e:
            logger.error("Failed to serialize or broadcast event %s: %s", event.event_type, e)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/pipeline")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time pipeline events."""
    await manager.connect(websocket)
    
    # Send initial system stats on connect
    try:
        status_service = websocket.app.state.container.status_service
        stats = await status_service.get_system_stats()
        await websocket.send_json({"type": "initial_stats", "data": stats})
    except Exception as e:
        logger.error("Failed to send initial stats: %s", e)
        
    try:
        while True:
            # Wait for any message from the client (e.g., ping/pong or requests)
            data = await websocket.receive_text()
            
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
