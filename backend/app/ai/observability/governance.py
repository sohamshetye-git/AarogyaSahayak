from typing import Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import AIUsageEvent
from app.config import settings

class AIGovernance:
    """
    Central API Efficiency & Cost Governance Controller.
    Prevents budget overrun, logs provider execution metrics, 
    and checks rate limits before allowing external provider requests.
    """
    
    @classmethod
    def record_usage(
        cls,
        db: Session,
        provider: str,
        mode: str,
        operation: str,
        role: Optional[str] = None,
        latency_ms: float = 0.0,
        status: str = "SUCCESS",
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        result_count: int = 0
    ):
        try:
            event = AIUsageEvent(
                provider=provider,
                mode=mode,
                operation=operation,
                requesting_role=role,
                status=status,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                result_count=result_count
            )
            db.add(event)
            db.commit()
        except Exception as e:
            print(f"Error logging AI Usage: {e}")

    @classmethod
    def check_rate_limit(cls, db: Session, provider: str) -> bool:
        """
        Return True if requests are within allowed daily limits.
        """
        from datetime import datetime, timedelta, timezone
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Simple daily count
        daily_count = db.query(AIUsageEvent).filter(
            AIUsageEvent.provider == provider,
            AIUsageEvent.created_at >= today_start
        ).count()
        
        limit = settings.GEMINI_DAILY_REQUEST_LIMIT if provider == "GEMINI" else settings.AI_DAILY_REQUEST_LIMIT
        return daily_count < limit
