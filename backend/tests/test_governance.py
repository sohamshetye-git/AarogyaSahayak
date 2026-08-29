import pytest
from app.database import SessionLocal
from app.models import AIUsageEvent
from app.ai.observability.governance import AIGovernance

def test_ai_usage_event_budget_limits_and_logging():
    db = SessionLocal()
    # Initial count
    initial_count = db.query(AIUsageEvent).count()

    # Log a dummy usage event
    AIGovernance.record_usage(
        db=db,
        provider="GEMINI",
        mode="MOCK",
        operation="UNIT_TEST_LOGGING",
        role="ASHA_WORKER",
        latency_ms=120.5,
        status="SUCCESS",
        input_tokens=150,
        output_tokens=50
    )

    new_count = db.query(AIUsageEvent).count()
    assert new_count == initial_count + 1

    # Verify rate limit check evaluates to True under normal budget
    assert AIGovernance.check_rate_limit(db, "GEMINI") is True

    # Clean up test event
    db.query(AIUsageEvent).filter(AIUsageEvent.operation == "UNIT_TEST_LOGGING").delete()
    db.commit()
    db.close()
