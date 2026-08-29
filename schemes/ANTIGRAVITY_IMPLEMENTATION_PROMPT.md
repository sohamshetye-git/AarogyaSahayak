# Antigravity implementation prompt — Government Scheme Knowledge Base

You are working inside the existing Aarogya Sahayak monorepo. Implement the Government Health Scheme Knowledge Base using the attached package as the specification and seed source:

- `README.md`
- `sources.json`
- `schemes.json`
- `eligibility-rule.schema.json`
- `postgresql_schema.sql`
- `neo4j_seed.cypher`
- `rag_manifest.json`

Do not replace the existing PostgreSQL/FastAPI/React/Neo4j/Milvus architecture. Inspect current models, migrations, routers, services, tests and UI before editing. Preserve existing functionality and unrelated changes.

## Non-negotiable safety rules

1. PostgreSQL is authoritative. Neo4j and Milvus are derived and rebuildable.
2. Never let Gemini or another LLM generate eligibility rules, benefit amounts, required documents or `VERIFIED_ELIGIBLE`.
3. Evaluate rules with `TRUE`, `FALSE`, `UNKNOWN`. Missing data returns `UNKNOWN`, never false.
4. `VERIFIED_ELIGIBLE` can be stored only with an authorized verification method, timestamp and reference.
5. PM-JAY local screening can never exceed `OFFICIAL_VERIFICATION_REQUIRED`; BIS is authoritative.
6. ABHA is a digital health identifier, not PM-JAY or other scheme eligibility.
7. ABDM HFR registration is not PM-JAY hospital empanelment.
8. Do not enable records marked `MANUAL_REVIEW`, `DISCOVERY_ONLY`, `BLOCKED` or `PENDING_HUMAN_DOCUMENT_REVIEW` in deterministic matching.
9. Do not ingest applicant/beneficiary PII into Milvus or Neo4j.
10. Do not invent or call an undocumented government API. Keep an adapter in `UNAVAILABLE` mode until documented credentials are configured.

## Phase 1 — inspect and map

- Create `docs/SCHEME_KB_IMPLEMENTATION_MAP.md` mapping the package schema to existing SQLAlchemy models, Alembic migrations, services, routers, Neo4j and Milvus code.
- Identify existing hardcoded JSY/PM-JAY/MJPJAY logic and replace it safely with database-backed versions.
- Do not delete current working routes until compatibility tests exist.

## Phase 2 — PostgreSQL authoritative registry

- Create SQLAlchemy models and Alembic migrations corresponding to the normalized schema.
- Adapt naming to existing conventions but preserve relationships and immutability of approved `SchemeVersion` rows.
- Add idempotent importer: `python -m app.schemes.import_kb --path <package-dir>`.
- Validate `schemes.json` and every rule tree with `eligibility-rule.schema.json` before any transaction.
- Import in one transaction. Re-running the same dataset version must not duplicate rows.
- A changed approved source/rule creates a new version; never silently overwrites the previous approved version.
- Store official URLs, effective dates, last verified, review due, confidence and review state.

## Phase 3 — deterministic eligibility engine

Implement typed Pydantic contracts:

- `PatientSchemeProfile`
- `RuleEvaluation`
- `SchemeEvaluationResult`
- `MatchedRule`
- `FailedRule`
- `UnknownRule`
- `MissingQuestion`
- `OfficialVerificationAction`
- `SchemeAccessStep`

Supported logical nodes: `all`, `any`, `not`, `if/then/else`, and atomic rules. Operators must be allow-listed exactly as defined in the schema. No `eval`, dynamic Python expressions or LLM-written code.

Implement statuses exactly:

- `SERVICE_AVAILABLE`
- `LIKELY_ELIGIBLE`
- `POTENTIALLY_ELIGIBLE`
- `MORE_INFORMATION_REQUIRED`
- `OFFICIAL_VERIFICATION_REQUIRED`
- `VERIFIED_ELIGIBLE`
- `NOT_ELIGIBLE`

Return relevance and eligibility separately. A service program may be relevant without having an eligibility decision.

## Phase 4 — APIs

Add role-protected endpoints under the existing `/api` prefix:

- `GET /api/schemes?state=&district=&category=&entity_type=`
- `GET /api/schemes/{scheme_id}`
- `POST /api/schemes/evaluate`
- `GET /api/schemes/evaluations/{patient_id}` for ASHA/Doctor access only
- `POST /api/schemes/{scheme_id}/verification-intents`
- `GET /api/admin/schemes/review-queue`
- `POST /api/admin/schemes/{scheme_version_id}/approve`
- `POST /api/admin/sources/{source_document_id}/mark-reviewed`
- `GET /api/admin/sources/freshness`

All responses must expose official source citations and `last_verified`. Never expose raw PII in admin analytics.

## Phase 5 — Neo4j projection

- Implement a projection service that reads only approved PostgreSQL versions and upserts the Neo4j graph.
- Nodes: `Scheme`, `SchemeVersion`, `Authority`, `Jurisdiction`, `Rule`, `Benefit`, `RequiredDocument`, `ApplicationChannel`, `VerificationMethod`, `HelpPoint`, `Source`.
- Edges: `ISSUED_BY`, `APPLIES_IN`, `REQUIRES_RULE`, `HAS_BENEFIT`, `REQUIRES_DOCUMENT`, `APPLIED_THROUGH`, `VERIFIED_THROUGH`, `ACCESSED_AT`, `SUPPORTED_BY`, `SUPERSEDES`.
- Add a rebuild command and a drift diagnostic comparing PostgreSQL version IDs with Neo4j.
- Do not store patient names, phones, ABHA, Aadhaar or raw voice transcripts in Neo4j.

## Phase 6 — official-source RAG

- Ingest only manifest documents with `ingest=true` and `review_state=APPROVED`.
- Store the required chunk metadata and SHA-256 hash.
- Apply metadata filters before vector similarity.
- Do not retrieve superseded or not-yet-effective chunks by default.
- RAG may explain matched/missing rules and access steps; it may not determine eligibility.
- If no approved current evidence exists, return `EVIDENCE_UNAVAILABLE` and use the structured result without an AI summary.

## Phase 7 — ASHA/Doctor/Citizen/Admin UI

In the ASHA patient profile and Add Patient review:

- Show “Check Government Support” action.
- Ask only missing profile questions needed by candidate rules.
- Show separate cards for `Cash/insurance schemes` and `Public health services`.
- Each card shows status, matched rules, missing information, benefits, required documents, access steps, official verification button, source, last verified and safety notice.
- `Start official verification` must open the official URL in a new window or create a safe internal intent; never iframe myScheme or government verification pages.
- PM-JAY must display: “ABHA is not proof of PM-JAY eligibility.”

Doctor portal:

- Show relevant financial/access support without changing clinical decisions.
- Do not show `VERIFIED_ELIGIBLE` unless official verification evidence exists.

Citizen app:

- Use plain language: “may qualify,” “more information needed,” or “official verification required.”
- Never say “Government approved” based on local screening.

Admin portal:

- Source freshness dashboard, changed-source queue, blocked rules, document review due dates and audit history.
- No citizen PII in aggregate scheme analytics.

## Phase 8 — freshness jobs

- Add a scheduled link/hash checker for public official sources.
- Do not bypass authentication, CAPTCHA or rate limits.
- On content hash change, mark source `SOURCE_CHANGED`, block affected material rules and require human review.
- Provide a command: `python -m app.schemes.verify_sources --no-authenticated-systems`.
- No authenticated beneficiary verification should run as part of a crawler.

## Phase 9 — tests and completion gate

Backend tests must cover:

- JSON-schema rejection of invalid/un-sourced atom rules.
- AND/OR/NOT/conditional three-valued logic.
- Missing data produces `MORE_INFORMATION_REQUIRED`.
- PM-JAY cannot become `VERIFIED_ELIGIBLE` locally.
- ABHA presence does not change PM-JAY eligibility status.
- HFR facility does not imply PM-JAY empanelment.
- PMMVY first-child and second-girl branches.
- JSY Maharashtra BPL/SC/ST and facility conditions.
- Service programs return `SERVICE_AVAILABLE`, not “eligible.”
- Superseded/stale/changed sources are excluded.
- Idempotent import and immutable approved versions.
- PII does not enter Neo4j/Milvus/admin outputs.

Playwright E2E must cover:

1. ASHA opens Sunita’s profile.
2. Scheme evaluation asks for missing PMMVY/JSY facts.
3. JSSK/PMSMA show as services.
4. PM-JAY and MJPJAY show official verification required.
5. Source links and last-verified dates render.
6. Doctor sees the same source-backed results.
7. Offline ASHA can cache the last approved scheme catalogue and queue a profile re-evaluation, but the UI clearly says official verification requires connectivity.

Do not report completion based only on unit mocks. Completion requires:

- PostgreSQL migration and idempotent import succeed.
- Neo4j projection diagnostic succeeds.
- Approved RAG documents ingest and retrieve with source metadata.
- Backend tests pass.
- Browser E2E passes on the real UI.
- Production frontend builds pass.
- `docs/SCHEME_KB_IMPLEMENTATION_MAP.md`, API docs and demo script are updated.

At the end, output a factual status matrix with `LIVE`, `LOCAL_VERIFIED`, `MOCK`, `AUTH_REQUIRED`, `BLOCKED`, or `NOT_IMPLEMENTED`. Never label BIS/ABDM/myScheme API integration live without documented authorization and a successful real health check.
