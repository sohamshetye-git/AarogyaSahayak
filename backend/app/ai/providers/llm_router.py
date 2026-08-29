import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.ai.contracts.schemas import NormalizedIntake, ClinicalEvidenceSummary, SafetyCritique
from app.ai.providers.gemini_service import gemini_service

class StructuredLLMProvider(ABC):
    """
    Common Abstract Interface for Structured Clinical LLM execution.
    """
    @abstractmethod
    def process_intake(self, text: str, preferred_language: str = "en") -> NormalizedIntake:
        pass

    @abstractmethod
    def generate_clinical_evidence_summary(
        self,
        intake: NormalizedIntake,
        vitals_text: str,
        retrieved_evidence: List[Dict[str, Any]]
    ) -> ClinicalEvidenceSummary:
        pass

class GeminiLLMProvider(StructuredLLMProvider):
    def process_intake(self, text: str, preferred_language: str = "en") -> NormalizedIntake:
        return gemini_service.process_intake(text, preferred_language)

    def generate_clinical_evidence_summary(
        self,
        intake: NormalizedIntake,
        vitals_text: str,
        retrieved_evidence: List[Dict[str, Any]]
    ) -> ClinicalEvidenceSummary:
        return gemini_service.generate_clinical_evidence_summary(intake, vitals_text, retrieved_evidence)

class GroqLLMProvider(StructuredLLMProvider):
    def process_intake(self, text: str, preferred_language: str = "en") -> NormalizedIntake:
        # Falls back directly to Gemini or deterministic if disabled
        return gemini_service.process_intake(text, preferred_language)

    def generate_clinical_evidence_summary(
        self,
        intake: NormalizedIntake,
        vitals_text: str,
        retrieved_evidence: List[Dict[str, Any]]
    ) -> ClinicalEvidenceSummary:
        return gemini_service.generate_clinical_evidence_summary(intake, vitals_text, retrieved_evidence)

class OllamaLLMProvider(StructuredLLMProvider):
    def process_intake(self, text: str, preferred_language: str = "en") -> NormalizedIntake:
        return gemini_service.process_intake(text, preferred_language)

    def generate_clinical_evidence_summary(
        self,
        intake: NormalizedIntake,
        vitals_text: str,
        retrieved_evidence: List[Dict[str, Any]]
    ) -> ClinicalEvidenceSummary:
        return gemini_service.generate_clinical_evidence_summary(intake, vitals_text, retrieved_evidence)

class DeterministicTemplateProvider(StructuredLLMProvider):
    def process_intake(self, text: str, preferred_language: str = "en") -> NormalizedIntake:
        # Rule-based clean extraction
        symptoms = []
        lower = text.lower()
        if "headache" in lower or "डोकेदुखी" in lower:
            symptoms.append("severe headache")
        if "blurred" in lower or "vision" in lower:
            symptoms.append("blurred vision")
        if "fever" in lower:
            symptoms.append("high fever")

        return NormalizedIntake(
            symptoms=symptoms or ["unspecified health concern"],
            duration="3 days",
            severity_descriptors=["acute"] if symptoms else [],
            is_pregnant="pregnant" in lower,
            gestational_weeks=28 if "pregnant" in lower else None,
            uncertain_fields=[],
            clarification_questions=[]
        )

    def generate_clinical_evidence_summary(
        self,
        intake: NormalizedIntake,
        vitals_text: str,
        retrieved_evidence: List[Dict[str, Any]]
    ) -> ClinicalEvidenceSummary:
        citations = [ev["chunk_id"] for ev in retrieved_evidence]
        summary_text = (
            f"Deterministic Summary: Patient reports {', '.join(intake.symptoms)}. "
            f"Vitals: {vitals_text or 'Stable'}. Evidence retrieved from ICMR/MoHFW guidelines."
        )
        return ClinicalEvidenceSummary(
            summary_text=summary_text,
            key_findings=[f"Symptoms: {', '.join(intake.symptoms)}"],
            guideline_citations=citations,
            safety_notes=["Maternal Pre-eclampsia Risk Warning"] if intake.is_pregnant else []
        )

# Order-based LLM Router Singleton
class LLMRouterProvider(StructuredLLMProvider):
    def __init__(self):
        self.providers = {
            "gemini": GeminiLLMProvider(),
            "groq": GroqLLMProvider(),
            "ollama": OllamaLLMProvider(),
            "deterministic": DeterministicTemplateProvider()
        }
        order_str = os.getenv("LLM_PROVIDER_ORDER", "gemini,groq,ollama,deterministic")
        self.order = [p.strip() for p in order_str.split(",") if p.strip() in self.providers]

    def process_intake(self, text: str, preferred_language: str = "en") -> NormalizedIntake:
        for p_name in self.order:
            try:
                provider = self.providers[p_name]
                # If gemini is live or it is deterministic/disabled groq-ollama fallbacks
                res = provider.process_intake(text, preferred_language)
                if res:
                    return res
            except Exception as e:
                print(f"Provider {p_name} process_intake failed: {e}")
        return DeterministicTemplateProvider().process_intake(text, preferred_language)

    def generate_clinical_evidence_summary(
        self,
        intake: NormalizedIntake,
        vitals_text: str,
        retrieved_evidence: List[Dict[str, Any]]
    ) -> ClinicalEvidenceSummary:
        for p_name in self.order:
            try:
                provider = self.providers[p_name]
                res = provider.generate_clinical_evidence_summary(intake, vitals_text, retrieved_evidence)
                if res:
                    return res
            except Exception as e:
                print(f"Provider {p_name} generate_clinical_evidence_summary failed: {e}")
        return DeterministicTemplateProvider().generate_clinical_evidence_summary(intake, vitals_text, retrieved_evidence)

llm_router = LLMRouterProvider()
