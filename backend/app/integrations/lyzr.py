from typing import Dict, Any, List
from app.integrations.base import BaseIntegrationAdapter
from app.config import settings

class LyzrOrchestratorAdapter(BaseIntegrationAdapter):
    """
    Lyzr Multi-Agent Orchestrator:
    - Router Agent
    - Clinical Triage Agent
    - Scheme Agent
    - Verification / Critic Agent
    """
    def __init__(self):
        super().__init__(mode=settings.LYZR_MODE)

    def route_and_triage(self, normalized_text: str, is_pregnant: bool = False, symptoms: List[str] = None) -> Dict[str, Any]:
        if self.is_mock:
            return {
                "status": "MOCKED",
                "router_agent_decision": "CLINICAL_AND_SCHEME_TRIAGE",
                "clinical_summary": (
                    "Reported symptoms (severe headache, blurred vision, pedal edema in pregnancy) "
                    "align with elevated clinical risk for pre-eclampsia. Prompt obstetrical evaluation is required."
                ),
                "potential_schemes": ["Janani Suraksha Yojana (JSY)", "Pradhan Mantri Matru Vandana Yojana (PMMVY)"],
                "source_citations": ["ICMR-STW-Obstetrics-2023", "MoHFW-Maternal-Triage-Protocol"],
                "verifier_approved": True,
                "verifier_notes": "No prohibited medical claims or autonomous prescriptions detected."
            }
        return {
            "status": "MOCKED",
            "clinical_summary": "Clinical evaluation required by healthcare worker.",
            "verifier_approved": True
        }

lyzr_adapter = LyzrOrchestratorAdapter()
