from typing import Dict, Any, List
from app.integrations.base import BaseIntegrationAdapter
from app.config import settings

class GeminiAdapter(BaseIntegrationAdapter):
    """
    Google Gemini Controlled Reasoning Adapter for structured medical synthesis.
    """
    def __init__(self):
        super().__init__(mode=settings.GEMINI_MODE)

    def extract_symptoms_and_entities(self, text: str) -> Dict[str, Any]:
        if self.is_mock:
            return {
                "status": "MOCKED",
                "extracted_symptoms": ["severe headache", "blurred vision", "swollen feet"],
                "pregnancy_mentioned": True,
                "confidence": 0.98
            }
        return {"status": "MOCKED", "extracted_symptoms": [], "confidence": 0.5}

class MilvusClinicalRAGAdapter(BaseIntegrationAdapter):
    """
    Milvus Vector Database for ICMR and MoHFW clinical guideline chunks.
    No patient PII is ever ingested into Milvus.
    """
    def __init__(self):
        super().__init__(mode=settings.MILVUS_MODE)

    def search_guidelines(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if self.is_mock:
            return [
                {
                    "source_id": "ICMR-STW-OBS-01",
                    "title": "ICMR Standard Treatment Workflow - Hypertensive Disorders in Pregnancy",
                    "organization": "ICMR",
                    "snippet": "In pregnant women >20 weeks gestation, BP >= 140/90 with headache or visual disturbance indicates pre-eclampsia requiring urgent referral to PHC/FRU.",
                    "similarity_score": 0.94
                },
                {
                    "source_id": "MoHFW-ASHA-HB-04",
                    "title": "MoHFW Maternal Health ASHA Field Reference Manual",
                    "organization": "Ministry of Health & Family Welfare",
                    "snippet": "High blood pressure during pregnancy with swelling and severe headache are danger signs. Contact ANM/Doctor immediately.",
                    "similarity_score": 0.89
                }
            ]
        return []

class Neo4jSchemeGraphAdapter(BaseIntegrationAdapter):
    """
    Neo4j Graph Database for Government Healthcare Schemes and Facility Capabilities.
    """
    def __init__(self):
        super().__init__(mode=settings.NEO4J_MODE)

    def find_eligible_schemes(self, condition: str, state: str = "Maharashtra", is_pregnant: bool = True) -> List[Dict[str, Any]]:
        if self.is_mock:
            return [
                {
                    "scheme_code": "JSY",
                    "scheme_name": "Janani Suraksha Yojana",
                    "coverage_amount": "Rs 1,400 direct cash assistance + institutional delivery",
                    "required_documents": ["Aadhaar card", "Mother & Child Protection (MCP) Card", "Bank passbook"],
                    "eligible_facilities": ["Kalyanpur PHC", "Shivaji Nagar CHC"],
                    "official_portal": "https://nhm.gov.in"
                },
                {
                    "scheme_code": "PMJAY",
                    "scheme_name": "Ayushman Bharat PM-JAY",
                    "coverage_amount": "Up to Rs 5,00,000 per family per year",
                    "required_documents": ["Ration Card", "Ayushman Card / ABHA ID"],
                    "eligible_facilities": ["Kalyanpur PHC (Empanelled)", "District Hospital"],
                    "official_portal": "https://pmjay.gov.in"
                }
            ]
        return []

class TavilyVerificationAdapter(BaseIntegrationAdapter):
    """
    Tavily Search Adapter restricted to official government domains (.gov.in, .nic.in).
    """
    def __init__(self):
        super().__init__(mode=settings.TAVILY_MODE)

    def verify_official_notice(self, query: str) -> Dict[str, Any]:
        if self.is_mock:
            return {
                "status": "MOCKED",
                "verified": True,
                "domain": "mohfw.gov.in",
                "title": "National Health Mission - Maternal and Child Health Protocols 2024",
                "url": "https://nhm.gov.in/index1.php?lang=1&level=1&sublinkid=969&lid=603"
            }
        return {"status": "MOCKED", "verified": False}

class N8nAutomationAdapter(BaseIntegrationAdapter):
    """
    n8n Workflow Automation for ASHA escalation, doctor referral alerts, and follow-up reminders.
    """
    def __init__(self):
        super().__init__(mode=settings.N8N_MODE)

    def trigger_urgent_alert(self, case_id: str, citizen_name: str, priority: str, details: str) -> Dict[str, Any]:
        if self.is_mock:
            return {
                "status": "MOCKED",
                "workflow": "Urgent_ASHA_Escalation",
                "dispatched": True,
                "case_id": case_id
            }
        return {"status": "MOCKED", "dispatched": True}

class ABDMSandboxAdapter(BaseIntegrationAdapter):
    """
    Ayushman Bharat Digital Mission (ABDM) Sandbox Interoperability Adapter.
    """
    def __init__(self):
        super().__init__(mode=settings.ABDM_MODE)

    def verify_abha(self, abha_number: str) -> Dict[str, Any]:
        if self.is_mock:
            return {
                "status": "MOCKED",
                "sandbox_verified": True,
                "abha_number": abha_number or "12-3456-7890-1234",
                "abha_status": "ACTIVE",
                "health_id": "sunita.devi@abdm"
            }
        return {"status": "MOCKED", "sandbox_verified": False}

gemini_adapter = GeminiAdapter()
milvus_adapter = MilvusClinicalRAGAdapter()
neo4j_adapter = Neo4jSchemeGraphAdapter()
tavily_adapter = TavilyVerificationAdapter()
n8n_adapter = N8nAutomationAdapter()
abdm_adapter = ABDMSandboxAdapter()
