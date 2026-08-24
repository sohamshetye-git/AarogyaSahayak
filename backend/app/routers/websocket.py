from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any
import json
import logging
from app.dependencies import get_current_user
from app.models import User
from app.schemas import StandardResponse
from app.services.event_bus import event_bus
from app.services.ticket_service import generate_realtime_ticket, redeem_realtime_ticket

logger = logging.getLogger("aarogya-websocket")

router = APIRouter(prefix="/realtime", tags=["WebSocket Real-Time Sync"])

@router.post("/ticket", response_model=StandardResponse)
def get_websocket_ticket(current_user: User = Depends(get_current_user)):
    """
    Issues a short-lived (60s), single-use ticket for establishing an authenticated
    WebSocket connection without exposing long-lived JWTs in URLs.
    """
    facility_id = None
    if current_user.worker_profile:
        facility_id = current_user.worker_profile.facility_id

    ticket = generate_realtime_ticket(
        user_id=current_user.id,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        facility_id=facility_id
    )

    return StandardResponse(data={
        "ticket": ticket,
        "expires_in_seconds": 60,
        "ws_url": f"/api/ws?ticket={ticket}"
    })

# Also provide standalone /ws endpoint (or under /api/ws)
ws_router = APIRouter(tags=["WebSocket Endpoint"])

@ws_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    ticket: Optional[str] = Query(None)
):
    if not ticket:
        logger.warning("Rejected WebSocket connection: missing ticket")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    context = redeem_realtime_ticket(ticket)
    if not context:
        logger.warning("Rejected WebSocket connection: invalid or expired ticket")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await event_bus.register(websocket, context)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "PING":
                    await websocket.send_text(json.dumps({"event": "PONG", "timestamp": msg.get("timestamp")}))
            except Exception:
                pass
    except WebSocketDisconnect:
        await event_bus.unregister(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await event_bus.unregister(websocket)
