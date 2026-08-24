# Requirements

## 1. Requirement notation

- `MUST`: required for the hackathon MVP.
- `SHOULD`: implement after the end-to-end MVP works.
- `MAY`: optional future enhancement.

## 2. Functional requirements

### Authentication and authorization

- AUTH-001: The portal MUST provide one common login screen.
- AUTH-002: The backend MUST derive the user's role from the stored account; the user must not select authority at login.
- AUTH-003: Roles MUST include `CITIZEN`, `ASHA_WORKER`, `PHC_DOCTOR`, `DISTRICT_ADMIN`, and `SYSTEM_ADMIN`.
- AUTH-004: Every protected backend endpoint MUST enforce role and resource scope.
- AUTH-005: An ASHA worker MUST only access assigned citizens/cases.
- AUTH-006: A doctor MUST only access referrals and patients linked to an authorized facility or care relationship.
- AUTH-007: District Admin views MUST default to anonymized/aggregated data.
- AUTH-008: The system MUST record login, clinical write, referral, prescription, consent, and sensitive-read audit events.

### Citizen application

- CIT-001: The citizen MUST be able to select a supported language.
- CIT-002: The citizen MUST be able to record a voice message and hear a response.
- CIT-003: The citizen MUST be able to confirm, replay, or re-record the transcript.
- CIT-004: The app MUST provide a text alternative to voice interaction.
- CIT-005: The app MUST check connectivity and show useful offline messaging.
- CIT-006: Offline mode MUST support structured warning-sign questions and vital inputs.
- CIT-007: Free-form voice recorded offline MUST be marked as pending processing until connectivity returns unless an offline ASR model is actually implemented.
- CIT-008: The app MUST display citizen-friendly case status without exposing internal IDs prominently.
- CIT-009: High-risk screens MUST provide direct human-care actions.
- CIT-010: The system MUST distinguish potentially relevant schemes from confirmed eligibility.

### Safety and triage

- SAF-001: Deterministic emergency rules MUST execute before ordinary LLM response generation.
- SAF-002: The offline model MUST output only a bounded workflow category: `ROUTINE`, `REVIEW_SOON`, or `URGENT`.
- SAF-003: The offline model MUST NOT output a disease diagnosis.
- SAF-004: An ML or LLM result MUST NOT override a configured deterministic urgent rule.
- SAF-005: The system MUST block AI-generated prescriptions and dosages in citizen/ASHA responses.
- SAF-006: If evidence is missing, conflicting, or unsafe, the response MUST fall back to human escalation.
- SAF-007: All medical guidance displayed to a citizen MUST be concise, non-diagnostic, and source-grounded.

### ASHA Portal

- ASHA-001: The ASHA dashboard MUST show urgent cases first.
- ASHA-002: The ASHA worker MUST be able to acknowledge a case.
- ASHA-003: The ASHA worker MUST be able to record the contact outcome.
- ASHA-004: The ASHA worker MUST be able to schedule and start a field visit.
- ASHA-005: A field visit MUST record consent status before ambient audio processing.
- ASHA-006: The ASHA worker MUST verify or correct AI-extracted information before submission.
- ASHA-007: The ASHA worker MUST be able to enter and confirm vitals.
- ASHA-008: Unusual vital values MUST trigger confirmation, not silent rejection.
- ASHA-009: The ASHA worker MUST be able to refer an authorized case to a PHC.
- ASHA-010: The portal MUST show doctor acknowledgement when received.
- ASHA-011: The ASHA worker MUST receive and complete doctor-created follow-up tasks.
- ASHA-012: Field-visit drafts MUST survive weak connectivity.

### Doctor Portal

- DOC-001: The Doctor dashboard MUST show urgent referrals first.
- DOC-002: The doctor MUST acknowledge a referral.
- DOC-003: The doctor MUST see the source of each clinical datum: citizen, ASHA, device, AI, or doctor.
- DOC-004: The doctor MUST be able to request clarification from the ASHA worker.
- DOC-005: Only an authorized doctor MAY confirm diagnosis and prescription.
- DOC-006: A prescription MUST remain draft until the doctor explicitly reviews and issues it.
- DOC-007: The doctor MUST be able to order tests and create a care plan.
- DOC-008: The doctor MUST be able to refer to a higher facility.
- DOC-009: The doctor MUST be able to assign a follow-up to the ASHA worker.
- DOC-010: Completing a consultation MUST create an immutable audit entry; corrections are appended, not silently overwritten.

### Admin Portal

- ADM-001: The admin dashboard MUST use anonymized or aggregated data by default.
- ADM-002: The admin MUST be able to view referral counts, response times, follow-up status, and scheme-support volume.
- ADM-003: Possible cluster alerts MUST be labelled as requiring review, not confirmed outbreaks.
- ADM-004: The admin SHOULD see facility load and ASHA support indicators.
- ADM-005: The portal MUST NOT create a punitive public ASHA leaderboard.

### AI and retrieval

- AI-001: Lyzr is the primary agent orchestrator.
- AI-002: Agents MUST include Router, Clinical, Scheme, and Verifier roles.
- AI-003: Clinical retrieval MUST use approved documents stored in Milvus.
- AI-004: Government scheme reasoning MUST use explicit Neo4j relationships/rules.
- AI-005: Tavily searches MUST use an approved domain allowlist.
- AI-006: The Verifier MUST require source support and reject prohibited content.
- AI-007: PII MUST be masked/minimized before an external LLM/tool call.
- AI-008: Agent output MUST conform to a strict Pydantic schema.

### Integrations

- INT-001: Client applications MUST call FastAPI, not external services directly.
- INT-002: BHASHINI credentials MUST remain server-side.
- INT-003: ABDM integration MUST target the sandbox and use a clearly labelled mock if credentials are unavailable.
- INT-004: n8n MUST automate notifications and follow-ups, not clinical decisions.
- INT-005: External calls MUST implement timeout, retry policy, structured error mapping, and audit metadata.

## 3. Non-functional requirements

### Accessibility

- WCAG 2.2 AA contrast SHOULD be met.
- Touch targets MUST be at least 48x48 px.
- Important status MUST use icon, label, and color.
- Interfaces MUST support keyboard focus and screen-reader labels.
- Citizen instructions MUST use short sentences and audio.

### Performance

- Portal initial usable render SHOULD be under 3 seconds on a typical connection.
- Normal API responses excluding external AI SHOULD target under 1 second.
- All external calls MUST have explicit timeouts.
- Lists MUST be paginated beyond 50 items.

### Reliability

- Every write request MUST have an idempotency key or server-side duplicate protection where retries may occur.
- Offline sync MUST preserve order and report conflicts.
- The system MUST not silently overwrite conflicting clinical data.
- Failed external integrations MUST not produce fake success.

### Security and privacy

- HTTPS MUST be used outside localhost.
- Passwords MUST be hashed using Argon2 or equivalent.
- Web sessions SHOULD use secure HttpOnly cookies; mobile tokens MUST use SecureStore.
- Secrets MUST be stored in environment variables and excluded from Git.
- Logs MUST exclude raw patient identifiers, tokens, and medical audio.
- Signed URLs MUST be short-lived.
- Raw audio SHOULD be deleted after processing unless explicit consent and retention policy require otherwise.

### Maintainability

- TypeScript strict mode MUST be enabled.
- Python type hints MUST be used.
- Frontend presentation components MUST not call APIs directly.
- Database migrations MUST use Alembic.
- Shared statuses and API types MUST have one canonical definition.
- AI-generated code MUST pass lint, type-check, tests, and production build.

## 4. Acceptance requirements

The build is accepted when:

1. `docker compose up` starts backend dependencies.
2. The portal and citizen app run using documented commands.
3. Demo accounts can log in with correct role routing.
4. The canonical Sunita scenario completes without manual DB changes.
5. A forced LLM failure results in safe escalation.
6. A forced network outage preserves the ASHA visit draft.
7. Admin views cannot reveal citizen identity.

