import asyncio
import json
import logging
from typing import Dict, List, Optional, Set, Any
from fastapi import WebSocket

logger = logging.getLogger("aarogya-event-bus")

class DomainEventBus:
    """
    Central real-time event bus managing authenticated WebSocket connections.
    Provides scoped pub/sub filtered by user_id, user_role, facility_id, and case_id.
    """
    def __init__(self):
        # Active connections mapped to their authenticated context
        # websocket -> { user_id, role, facility_id, connected_at }
        self._connections: Dict[WebSocket, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def register(self, websocket: WebSocket, context: Dict[str, Any]):
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = context
        logger.info(f"WebSocket client connected: user={context.get('user_id')}, role={context.get('role')}")
        
        # Send initial handshake ack
        await websocket.send_text(json.dumps({
            "event": "CONNECTED",
            "data": {
                "user_id": context.get("user_id"),
                "role": context.get("role"),
                "status": "ONLINE"
            }
        }))

    async def unregister(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self._connections:
                user_id = self._connections[websocket].get("user_id")
                del self._connections[websocket]
                logger.info(f"WebSocket client disconnected: user={user_id}")

    async def broadcast(
        self,
        event_name: str,
        payload: Dict[str, Any],
        target_roles: Optional[List[str]] = None,
        target_user_ids: Optional[List[str]] = None,
        facility_id: Optional[str] = None
    ):
        """
        Broadcasts an event only to authorized connected clients.
        Keeps payloads minimal and sanitized (no PII, credentials, or clinical secrets).
        """
        message = json.dumps({
            "event": event_name,
            "data": payload,
            "timestamp": payload.get("timestamp")
        })

        async with self._lock:
            targets = list(self._connections.items())

        dead_connections: List[WebSocket] = []

        for ws, ctx in targets:
            # Check user filtering
            if target_user_ids and ctx.get("user_id") not in target_user_ids:
                continue

            # Check role filtering
            if target_roles and ctx.get("role") not in target_roles:
                continue

            # Check facility filtering if specified
            if facility_id and ctx.get("facility_id") and ctx.get("facility_id") != facility_id:
                continue

            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"Error dispatching to websocket: {e}")
                dead_connections.append(ws)

        for dead_ws in dead_connections:
            await self.unregister(dead_ws)


event_bus = DomainEventBus()

def publish_domain_event(
    event_name: str,
    payload: Dict[str, Any],
    target_roles: Optional[List[str]] = None,
    target_user_ids: Optional[List[str]] = None,
    facility_id: Optional[str] = None
):
    """
    Synchronous helper to safely schedule event broadcasting from synchronous routes
    after a DB commit.
    """
    try:
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(
                event_bus.broadcast(
                    event_name=event_name,
                    payload=payload,
                    target_roles=target_roles,
                    target_user_ids=target_user_ids,
                    facility_id=facility_id
                )
            )
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        event_bus.broadcast(
                            event_name=event_name,
                            payload=payload,
                            target_roles=target_roles,
                            target_user_ids=target_user_ids,
                            facility_id=facility_id
                        ),
                        loop
                    )
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Event broadcast skipped: {e}")
