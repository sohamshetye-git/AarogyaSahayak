# Architecture

## 1. System view

```text
Citizen Mobile (React Native)
        |
Healthcare Portal (React: ASHA/Doctor/Admin)
        |
FastAPI API + WebSocket boundary
        |
+-------------------+---------------------+
| Operational Core  | AI/Knowledge        |
| PostgreSQL        | Lyzr + Gemini       |
| Auth/RBAC         | Milvus Clinical RAG |
| Cases/Visits      | Neo4j Scheme Graph  |
| Referrals         | Verifier            |
+-------------------+---------------------+
        |
External adapters: BHASHINI, Tavily, n8n, ABDM Sandbox, object storage
```

## 2. Repository

```text
aarogya-sahayak/
├── apps/
│   ├── citizen-mobile/
│   └── healthcare-portal/
├── backend/
├── packages/
│   ├── design-tokens/
│   ├── shared-types/
│   └── api-client/
├── ai-services/
│   ├── agents/
│   ├── clinical-rag/
│   ├── scheme-graph/
│   └── edge-model/
├── automation/n8n-workflows/
├── infrastructure/
├── docs/
├── docker-compose.yml
├── .env.example
└── README.md
```

## 3. Frontend architecture

### Citizen

- Feature-based Expo Router routes.
- UI components contain no direct external API calls.
- `services/api` calls FastAPI.
- `offline/queue` owns SQLite pending operations.
- `features/triage` runs local rules/TFLite adapter.
- Tokens use SecureStore.

### Portal

```text
src/
├── app/router.tsx
├── auth/
├── layouts/
├── features/asha/
├── features/doctor/
├── features/admin/
├── components/
├── services/api.ts
├── hooks/
├── types/
└── styles/
```

- React Router protects role sections.
- TanStack Query owns server state.
- React Hook Form + Zod own form state/validation.
- Dexie owns ASHA offline drafts.
- Shared components must not contain role-specific permission logic.

## 4. Backend layering

```text
Router -> Service -> Repository -> Database
                 -> Integration Adapter
                 -> Domain Event
```

- Routers validate transport and authorization.
- Services enforce workflow and safety rules.
- Repositories contain database access.
- Integration adapters isolate external APIs.
- Domain events trigger WebSocket/n8n actions after successful commits.
- Agent calls never write directly to the database.

## 5. AI request flow

```text
Input
-> PII minimizer
-> language/symptom normalizer
-> deterministic safety service
-> Router Agent
   -> Clinical Agent + Milvus
   -> Scheme Agent + Neo4j/Tavily
-> Verifier Agent
-> strict response schema
-> human-facing response/action
```

The Verifier produces:

```json
{
  "approved": true,
  "risk_level": "URGENT",
  "citizen_message": "...",
  "required_action": "CONTACT_ASHA",
  "source_ids": ["GUIDE-001"],
  "prohibited_content_detected": false
}
```

If validation fails, use a deterministic fallback.

## 6. Data ownership

- PostgreSQL: operational and clinical workflow data.
- SQLite/IndexedDB: temporary offline client data.
- Milvus: approved knowledge chunks only.
- Neo4j: schemes, rules, packages, documents, facilities.
- Object storage: authorized generated documents/attachments.
- n8n: automation execution metadata, not master clinical data.

## 7. External adapters

Every external adapter must expose a stable internal interface and map provider-specific failures into:

```text
TEMPORARILY_UNAVAILABLE
INVALID_REQUEST
UNAUTHORIZED
RATE_LIMITED
TIMEOUT
PROVIDER_ERROR
```

No provider response is trusted without schema validation.

## 8. Security architecture

- JWT access and refresh flow.
- Server-side RBAC and resource-scope checks.
- Argon2 password hashing.
- HTTPS outside localhost.
- Audit logs with actor, action, resource, timestamp, and outcome.
- PII redaction in logs and AI context.
- Signed document URLs.
- Consent state attached to voice/document operations.
- Environment secrets never committed.

## 9. Resilience

- Explicit timeouts for all network calls.
- Retry only safe/idempotent operations.
- Idempotency keys for offline writes.
- Circuit-break external provider failures.
- Store event only after DB transaction succeeds.
- Provide local demo fixtures when sponsor/government sandboxes are unavailable.

## 10. Deployment profiles

### Local/hackathon

Docker Compose runs PostgreSQL, Neo4j, Milvus standalone, n8n, MinIO, and FastAPI. Portal and Expo may run in dev mode. Maintain seeded demo data and a no-internet fallback.

### Prototype cloud

- Portal on static hosting.
- FastAPI container behind HTTPS.
- Managed PostgreSQL.
- Neo4j Aura or container.
- Milvus standalone/managed service.
- n8n separate service.
- S3-compatible object storage.

## 11. Observability

- JSON structured logs.
- Correlation ID and case ID where permitted.
- Metrics: API latency, external failures, queue length, sync failures, notification delivery, referral response time.
- Sentry optional for application errors.
- Never log raw access tokens, full voice, Aadhaar/ABHA, phone, or diagnosis text unnecessarily.

## 12. Environment variables

```text
DATABASE_URL
JWT_SECRET
JWT_REFRESH_SECRET
LYZR_API_KEY
GEMINI_API_KEY
BHASHINI_API_KEY
BHASHINI_USER_ID
BHASHINI_PIPELINE_ID
TAVILY_API_KEY
NEO4J_URI
NEO4J_USERNAME
NEO4J_PASSWORD
MILVUS_URI
MILVUS_TOKEN
N8N_WEBHOOK_URL
N8N_WEBHOOK_SECRET
ABDM_BASE_URL
ABDM_CLIENT_ID
ABDM_CLIENT_SECRET
OBJECT_STORAGE_ENDPOINT
OBJECT_STORAGE_ACCESS_KEY
OBJECT_STORAGE_SECRET_KEY
OBJECT_STORAGE_BUCKET
```

