import secrets
import time
from typing import Dict, Any, Optional

# In-memory ticket cache: ticket -> { "user_id": ..., "role": ..., "facility_id": ..., "expires_at": ... }
_TICKET_CACHE: Dict[str, Dict[str, Any]] = {}
TICKET_TTL_SECONDS = 60

def generate_realtime_ticket(user_id: str, role: str, facility_id: Optional[str] = None) -> str:
    """Generates a cryptographically random, short-lived single-use ticket."""
    clean_expired_tickets()
    ticket = secrets.token_urlsafe(32)
    _TICKET_CACHE[ticket] = {
        "user_id": user_id,
        "role": role,
        "facility_id": facility_id,
        "expires_at": time.time() + TICKET_TTL_SECONDS
    }
    return ticket

def redeem_realtime_ticket(ticket: str) -> Optional[Dict[str, Any]]:
    """Redeems and invalidates a single-use ticket."""
    clean_expired_tickets()
    if not ticket or ticket not in _TICKET_CACHE:
        return None

    data = _TICKET_CACHE.pop(ticket)
    if time.time() > data["expires_at"]:
        return None

    return data

def clean_expired_tickets():
    now = time.time()
    expired = [k for k, v in _TICKET_CACHE.items() if now > v["expires_at"]]
    for k in expired:
        _TICKET_CACHE.pop(k, None)
