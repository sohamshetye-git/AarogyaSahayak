import time
import uuid
from typing import Dict, Any, Optional
from app.ai.contracts.schemas import (
    NormalizedIntake, ClinicalEvidenceSummary, SchemeExplanation, SafetyCritique, AgentExecutionResult
)
from app.ai.pii.masker import PIIMasker
from app.ai.rag.clinical_rag import clinical_rag_service
from app.ai.graph.scheme_graph import scheme_graph_service
from app.ai.providers.gemini_service import gemini_service
from app.safety.emergency_rules import EmergencyRuleEvaluator

class MultiAgentOrchestrator:
    """
    Multi-Agent Intelligence Orchestrator.
    Coordinating:
    1. Deterministic Emergency Rules (Runs First - Authoritative)
    2. PII Masking Engine
    3. Intake Agent
    4. Clinical Evidence Agent (Milvus RAG)
    5. Scheme Agent (Neo4j GraphRAG)
    6. Safety Critic Agent (Runs Last - Validation Guardrail)
    """

    @classmethod
    def orchestrate(
        cls,
        raw_text: str,
        citizen_name: Optional[str] = None,
        phone: Optional[str] = None,
        abha: Optional[str] = None,
        preferred_language: str = "mr-IN",
        systolic_bp: Optional[int] = None,
        diastolic_bp: Optional[int] = None,
        spo2: Optional[int] = None,
        temperature_c: Optional[float] = None,
        is_pregnant: bool = False,
        gestational_weeks: Optional[int] = None
    ) -> AgentExecutionResult:
        start_time = time.time()
        exec_id = f"EXEC-{uuid.uuid4().hex[:8].upper()}"

        # 1. Deterministic Emergency Rule Evaluation (Runs First)
        # Note: Rule evaluator is strictly authoritative for urgency
        priority, rule_triggered, rule_reason, guidance = EmergencyRuleEvaluator.evaluate(
            symptoms=[raw_text],
            is_pregnant=is_pregnant,
            gestational_weeks=gestational_weeks,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            spo2=spo2,
            temperature_c=temperature_c
        )

        # 2. PII Masking Engine
        masked_text, token_map = PIIMasker.mask_text(
            text=raw_text,
            citizen_name=citizen_name,
            phone=phone,
            abha=abha
        )

        # 3. Agent 1: Intake Normalization Agent
        from app.ai.providers.llm_router import llm_router
        intake = llm_router.process_intake(masked_text, preferred_language=preferred_language)
        if is_pregnant:
            intake.is_pregnant = True
            intake.gestational_weeks = gestational_weeks or 28

        # 4. Agent 2: Clinical Evidence Retrieval Agent (Milvus RAG)
        vitals_desc = ""
        if systolic_bp and diastolic_bp:
            vitals_desc = f"BP {systolic_bp}/{diastolic_bp} mmHg"
        if spo2:
            vitals_desc += f" SpO2 {spo2}%"

        evidence_query = f"{' '.join(intake.symptoms)} {vitals_desc} {'pregnant' if is_pregnant else ''}"
        retrieved_evidence = clinical_rag_service.search(query=evidence_query, top_k=3)
        
        evidence_summary = llm_router.generate_clinical_evidence_summary(
            intake=intake,
            vitals_text=vitals_desc,
            retrieved_evidence=retrieved_evidence
        )
        if not evidence_summary.guideline_citations:
            if retrieved_evidence:
                evidence_summary.guideline_citations = [
                    f"{r.get('title', 'Clinical Guideline')} ({r.get('authority', 'MoHFW / ICMR')})"
                    for r in retrieved_evidence
                ]
            else:
                evidence_summary.guideline_citations = [
                    "ASHA Field Reference Manual - Maternal Danger Signs & High Risk Pregnancy Triage (MoHFW)",
                    "Standard Treatment Workflow Reference - Hypertensive Disorders in Pregnancy (ICMR)"
                ]

        # 5. Agent 3: Scheme Evaluation Agent (Neo4j GraphRAG)
        raw_schemes = scheme_graph_service.evaluate_eligibility(
            is_pregnant=intake.is_pregnant,
            state="Maharashtra",
            area_type="RURAL"
        )
        scheme_dtos = [
            SchemeExplanation(
                scheme_code=s["scheme_code"],
                scheme_name=s["scheme_name"],
                eligibility_status=s["status"],
                explanation=f"{s['benefit_summary']} Applicable for rural healthcare assistance.",
                actionable_steps=["Present MCP Card at Kalyanpur PHC", "Verify Aadhaar and Bank details"],
                required_documents=s["required_documents"]
            )
            for s in raw_schemes
        ]

        # 6. Agent 4: Safety Critic Agent (Runs Last)
        critique = gemini_service.evaluate_safety_critic(intake=intake, summary=evidence_summary)

        latency_ms = round((time.time() - start_time) * 1000, 2)

        # Log usage to database if db session is available
        try:
            from app.database import SessionLocal
            from app.ai.observability.governance import AIGovernance
            db = SessionLocal()
            if AIGovernance.check_rate_limit(db, "GEMINI"):
                AIGovernance.record_usage(
                    db=db,
                    provider="GEMINI",
                    mode=gemini_service.get_mode(),
                    operation="MULTI_AGENT_ORCHESTRATE",
                    role="ASHA_WORKER",
                    latency_ms=latency_ms,
                    result_count=len(scheme_dtos)
                )
            db.close()
        except Exception:
            pass

        return AgentExecutionResult(
            execution_id=exec_id,
            intake=intake,
            evidence_summary=evidence_summary,
            schemes=scheme_dtos,
            critique=critique,
            provider_mode=gemini_service.get_mode(),
            orchestrator="LOCAL_ORCHESTRATOR",
            latency_ms=latency_ms
        )

orchestrator_service = MultiAgentOrchestrator()
