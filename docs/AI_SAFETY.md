# AI Safety & Clinical Boundary Invariants

## 1. Non-Negotiable Safety Principles
1. **Deterministic Safety Rules Run First & Are Authoritative**: Emergency urgency triage is computed strictly through deterministic algorithmic rules (`EmergencyRuleEvaluator`). No LLM, edge model, or external service can downgrade or override an emergency red flag.
2. **Clinical Authority of Treating Medical Officers**: Diagnosis, prescription creation, lab investigation orders, and clinical care plans can **ONLY** be created and signed by an authenticated PHC Doctor (`PHC_DOCTOR`). The system never auto-prescribes or pre-fills medication without doctor confirmation.
3. **Strict Request-Scoped PII Masking**: Citizen names, 10-digit Indian phone numbers, 14-digit ABHA numbers, and Aadhaar numbers are stripped and replaced with deterministic tokens (`[CITIZEN_1]`, `[PHONE_REDACTED]`, `[ABHA_REDACTED]`) before context is passed to any external AI adapter.
4. **Deterministic Graph Scheme Matching**: Government health scheme eligibility (JSY, PM-JAY, MJPJAY) is determined strictly through structured graph rules in Neo4j. AI models are restricted to explaining matched criteria and cannot invent eligibility.
5. **Multi-Agent Safety Critic Validator**: The `SafetyCriticAgent` executes as the final step in every multi-agent pipeline, inspecting outputs for prohibited diagnostic assertions, drug dosing suggestions, or leaked PII, and mandating human confirmation before persistence.
