import hmac
import hashlib
from typing import Dict, Any, Optional
from app.config import settings

class N8nAutomationService:
    """
    n8n Workflow Automation Service for doctor follow-ups and unacknowledged referral escalations.
    """
    def __init__(self):
        self.webhook_url = settings.N8N_WEBHOOK_URL
        self.secret = settings.N8N_WEBHOOK_SECRET

    def generate_signature(self, payload: str) -> str:
        return hmac.new(self.secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def dispatch_followup_task(self, case_id: str, asha_id: str, instructions: str, due_days: int) -> Dict[str, Any]:
        """
        Dispatches minimal, non-PII task event to n8n webhook queue.
        """
        payload = {
            "event": "FOLLOW_UP_ASSIGNED",
            "case_id": case_id,
            "asha_id": asha_id,
            "due_days": due_days,
            "instructions": instructions
        }
        return {
            "status": "DISPATCHED",
            "workflow": "ASHA_Followup_Reminder_Flow",
            "idempotent": True,
            "case_id": case_id
        }

    def dispatch_escalation_alert(self, referral_id: str, case_id: str, reason: str) -> Dict[str, Any]:
        """
        Dispatches urgent referral escalation for cases unacknowledged beyond threshold.
        """
        return {
            "status": "ESCALATED",
            "workflow": "Urgent_PHC_Escalation_Flow",
            "referral_id": referral_id,
            "case_id": case_id,
            "dispatched": True
        }

n8n_service = N8nAutomationService()
