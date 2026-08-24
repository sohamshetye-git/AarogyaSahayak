# MVP Scope

## 1. Objective

Deliver one reliable end-to-end workflow before adding advanced sponsor integrations. The MVP must demonstrate access, safety, human hand-off, clinical authority, follow-up, and privacy.

## 2. Required MVP

### Shared foundation

- Monorepo/project structure.
- Common portal login and backend RBAC.
- PostgreSQL migrations and seeded demo data.
- Shared case statuses and API schemas.
- Docker Compose dependencies.
- OpenAPI/Swagger.

### Citizen

- Hindi/Marathi/English UI selection.
- Voice record/playback with mock or BHASHINI transcription.
- Transcript confirmation.
- Structured warning-sign/vital input.
- Case creation.
- Offline save and later sync.
- Citizen-friendly status.

### ASHA

- Dashboard and urgent task.
- Acknowledge.
- Contact outcome.
- Field-visit wizard with consent.
- Symptoms and vitals.
- Deterministic urgent rule.
- Referral to PHC.
- Doctor acknowledgement status.
- Follow-up task.

### Doctor

- Referral queue.
- Acknowledge.
- Source-labelled case review.
- Consultation draft.
- Doctor-confirmed assessment.
- Prescription draft and explicit issue.
- Care plan and ASHA follow-up.
- Consultation completion.

### Admin

- Aggregate dashboard.
- Urgent/referral/follow-up counts.
- Simple possible-cluster review card.
- No patient identity.

### Automation and reporting

- One n8n urgent/referral notification workflow.
- One generated referral or consultation PDF.
- Audit log for major workflow actions.

## 3. Strong additions after MVP

- BHASHINI live ASR/translation/TTS.
- Lyzr four-agent workflow.
- Small Milvus knowledge base for maternal warning guidance.
- Neo4j graph for PM-JAY, MJPJAY, and JSY.
- Tavily official-domain current verification.
- TensorFlow Lite bounded risk classifier.
- WebSocket live status.
- ABDM sandbox adapter.

## 4. Explicitly out of scope for first MVP

- Full offline free-form ASR.
- Production ABDM.
- Automatic emergency dispatch.
- Autonomous diagnosis/prescription.
- Every Indian language.
- Every government scheme.
- Full SNOMED ingestion.
- Advanced epidemiological prediction.
- Blockchain/federated learning.
- Complete hospital management.
- Real payment/claim approval.

## 5. Build order

1. Repository, auth, DB, seed data.
2. Citizen creates case.
3. ASHA sees and acknowledges it.
4. ASHA records vitals and refers.
5. Doctor acknowledges and completes consultation.
6. Follow-up returns to ASHA/citizen.
7. Admin aggregate updates.
8. Offline queue and failure handling.
9. n8n notification and PDF.
10. AI/RAG integrations one at a time.

## 6. Demo acceptance script

1. Sign in as ASHA in normal Chrome.
2. Sign in as Doctor in incognito/another browser.
3. Sign in as Admin in another browser/profile.
4. Citizen creates Sunita urgent case.
5. ASHA dashboard updates.
6. ASHA acknowledges, enters BP 150/100, and refers.
7. Doctor queue receives referral and acknowledges.
8. Doctor records assessment and assigns follow-up.
9. ASHA sees follow-up.
10. Admin sees anonymized count change.
11. Repeat an offline ASHA visit save and sync.
12. Force an AI provider failure and show safe fallback.

## 7. Definition of done

- Feature has loading, empty, error, and permission states.
- API enforces scope; UI guard alone is insufficient.
- Unit/integration tests pass.
- Lint/type-check/build pass.
- No secret or patient PII in repository/logs.
- Responsive frames work.
- Demo fixture is reproducible.
- Documentation is updated.

## 8. Team ownership

```text
Member 1: Citizen mobile
Member 2: ASHA portal
Member 3: Doctor portal
Member 4: Admin portal
Integration owner: backend contracts, DB, auth, merges, deployment
AI owner: Lyzr/Milvus/Neo4j/Tavily/BHASHINI integration
```

Each member develops on a feature branch and may not rewrite another feature folder without agreement.

