# Government Scheme Integration Checklist

- Source directory: schemes/
- Target: Full PostgreSQL 3-valued deterministic engine, Neo4j GraphRAG, Milvus evidence, Gemini explanation, and ASHA/Citizen/Doctor/Admin portals.

---

## Task List & Implementation Status

- [x] **Phase 0 & 1: Knowledge Package Audit & Task Tracking**
  - [x] Create docs/SCHEME_INTEGRATION_TASKS.md tracking all sprint tasks
  - [x] Validate schema & uniqueness across sources.json, schemes.json, rag_manifest.json, eligibility-rule.schema.json

- [x] **Phase 2: PostgreSQL Authoritative Schema & Alembic Migration**
  - [x] Define SQLAlchemy models for Scheme, SchemeVersion, SchemeSource, EligibilityRuleSet, RuleNode, SchemeBenefit, RequiredDocument, ApplicationStep, SchemeEvaluation, SchemeEvaluationResult, SchemeVerification in app/models/schemes.py
  - [x] Generate and execute additive Alembic migration add_scheme_engine_tables

- [x] **Phase 3: Knowledge Base Importer**
  - [x] Create backend/app/schemes/import_kb.py with --validate-only, --dry-run, --apply modes
  - [x] Import 29 schemes, 16 sources, and rule sets into PostgreSQL with SHA-256 integrity check and idempotency

- [x] **Phase 4: Pure 3-Valued Deterministic Eligibility Engine**
  - [x] Create backend/app/schemes/engine.py implementing TRUE, FALSE, UNKNOWN three-valued logic for AND, OR, NOT, and atomic comparison operators (equals, gt, gte, lt, lte, in, between, contains, exists)
  - [x] Implement canonical fact mapper (backend/app/schemes/fact_mapper.py) translating CitizenProfile / ASHA visit data to evaluation facts
  - [x] Persist SchemeEvaluation and SchemeEvaluationResult records to PostgreSQL

- [x] **Phase 5: Neo4j Graph Projection & Milvus Evidence RAG**
  - [x] Create backend/app/schemes/project_neo4j.py to project PostgreSQL scheme versions into Neo4j graph nodes and relationships
  - [x] Create backend/app/schemes/ingest_rag.py to index official source documents from rag_manifest.json into Milvus vector collection with SHA-256 metadata

- [x] **Phase 6: Gemini Explanation Layer**
  - [x] Implement fallback-safe Gemini scheme explanation service (backend/app/schemes/explanation.py) that accepts deterministic results + RAG evidence without overriding rule outputs

- [x] **Phase 7: FastAPI Endpoints & RBAC**
  - [x] Update backend/app/routers/schemes.py to expose /api/schemes, /api/schemes/{id}, /api/schemes/evaluate, /api/schemes/evaluations/{id}, and /api/admin/schemes/source-health
  - [x] Enforce RBAC: Citizen (own), ASHA (assigned), Doctor (referred), Admin (anonymized aggregates only)

- [x] **Phase 8: Frontend ASHA / Citizen / Doctor / Admin UI Integration**
  - [x] Update ASHA Schemes view (/asha/schemes) to enable citizen evaluation, missing information collection, and assistance task creation
  - [x] Update Field Visit Step 4 and Beneficiary Directory with scheme eligibility chips and official links
  - [x] Update Citizen Portal and Doctor Portal views with simplified eligibility statuses and official evidence links

- [x] **Phase 9: Comprehensive Testing & Verification**
  - [x] Run backend unit/integration tests for eligibility engine, importer, and APIs
  - [x] Run end-to-end browser/Playwright tests verifying synthetic citizen scheme evaluations
  - [x] Build frontend workspace (npm run build)
