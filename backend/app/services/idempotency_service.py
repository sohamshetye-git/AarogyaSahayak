import hashlib
import json
from typing import Optional, Tuple, Any
from sqlalchemy.orm import Session
from fastapi import Response, HTTPException, status
from app.models import IdempotencyRecord, User

def compute_payload_hash(payload: Any) -> str:
    """Computes a deterministic SHA-256 hash of a dictionary, model, or string."""
    if payload is None:
        normalized_str = ""
    elif isinstance(payload, str):
        normalized_str = payload
    elif hasattr(payload, "model_dump_json"):
        normalized_str = payload.model_dump_json()
    elif hasattr(payload, "model_dump"):
        normalized_str = json.dumps(payload.model_dump(), sort_keys=True, default=str)
    elif isinstance(payload, dict):
        normalized_str = json.dumps(payload, sort_keys=True, default=str)
    else:
        normalized_str = str(payload)
    
    return hashlib.sha256(normalized_str.encode("utf-8")).hexdigest()

def check_idempotency(
    db: Session,
    idempotency_key: Optional[str],
    user_id: Optional[str],
    request_path: str,
    payload: Any = None
) -> Optional[Response]:
    """
    Checks if an idempotency record exists.
    - If matches key + payload_hash: returns cached response.
    - If key matches but payload_hash differs or user differs: raises 409 Conflict.
    - If key does not exist: returns None.
    """
    if not idempotency_key:
        return None

    record = db.query(IdempotencyRecord).filter(
        IdempotencyRecord.idempotency_key == idempotency_key
    ).first()

    if not record:
        return None

    current_hash = compute_payload_hash(payload)

    # Validate ownership & payload integrity
    if record.user_id and user_id and record.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "IDEMPOTENCY_USER_MISMATCH",
                "message": "Idempotency key was created by a different user session."
            }
        )

    if record.payload_hash and current_hash and record.payload_hash != current_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "IDEMPOTENCY_PAYLOAD_MISMATCH",
                "message": "Idempotency key was already used with different request parameters."
            }
        )

    return Response(
        content=record.response_body,
        status_code=record.response_status,
        media_type="application/json"
    )

def record_idempotency(
    db: Session,
    idempotency_key: Optional[str],
    user_id: Optional[str],
    http_method: str,
    request_path: str,
    operation: str,
    payload: Any,
    response_status: int,
    response_body_json: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None
) -> None:
    """Saves or updates an IdempotencyRecord transaction-safely."""
    if not idempotency_key:
        return

    payload_hash = compute_payload_hash(payload)

    record = db.query(IdempotencyRecord).filter(
        IdempotencyRecord.idempotency_key == idempotency_key
    ).first()

    if record:
        record.response_status = response_status
        record.response_body = response_body_json
        record.payload_hash = payload_hash
        record.resource_type = resource_type
        record.resource_id = resource_id
    else:
        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            user_id=user_id,
            http_method=http_method,
            request_path=request_path,
            operation=operation,
            payload_hash=payload_hash,
            resource_type=resource_type,
            resource_id=resource_id,
            response_status=response_status,
            response_body=response_body_json
        )
        db.add(record)
    
    db.commit()
