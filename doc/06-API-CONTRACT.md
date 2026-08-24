# API Contract

## 1. General rules

- Base path: `/api/v1`.
- JSON uses `snake_case` consistently.
- Dates are ISO-8601 UTC.
- Protected requests require authentication.
- Write requests that may retry accept `Idempotency-Key`.
- Responses include `request_id` for support/debugging.
- Errors never expose stack traces in production.

Success envelope:

```json
{"data": {}, "request_id": "req_uuid"}
```

Error envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Please check the highlighted information.",
    "fields": {"systolic_bp": "Enter a valid number."}
  },
  "request_id": "req_uuid"
}
```

## 2. Authentication

### POST `/api/v1/auth/login`

```json
{"identifier":"asha01","password":"demo123"}
```

```json
{
  "data": {
    "access_token": "token",
    "refresh_token": "token",
    "user": {
      "id": "uuid",
      "name": "Sita Patel",
      "role": "ASHA_WORKER",
      "facility_id": "uuid",
      "assigned_village_ids": ["uuid"]
    }
  },
  "request_id": "req_uuid"
}
```

Also implement refresh, logout, and `GET /auth/me`.

## 3. Citizen

### POST `/citizen/cases`

```json
{
  "client_case_id": "offline_uuid",
  "preferred_language": "mr-IN",
  "transcript": "...",
  "structured_answers": {},
  "consent_to_process": true
}
```

Returns case reference, priority, status, citizen message, and next actions.

### GET `/citizen/cases`

Returns only the authenticated citizen's cases.

### GET `/citizen/cases/{case_id}`

Returns citizen-friendly status, not internal clinical notes.

### POST `/citizen/sync`

Accepts ordered offline operations with unique client operation IDs and returns per-item accepted/duplicate/conflict status.

## 4. Voice

### POST `/voice/transcribe`

Multipart audio plus `source_language`. Returns transcript, detected language, and whether user confirmation is required.

### POST `/voice/synthesize`

```json
{"text":"...","target_language":"mr-IN","voice":"default"}
```

Returns a short-lived audio reference.

## 5. ASHA

### GET `/asha/dashboard`

Returns counts, urgent cases, today's visits, follow-ups, recent updates, and sync summary scoped to authenticated ASHA worker.

### GET `/asha/tasks`

Query: `priority`, `status`, `due`, `page`, `page_size`, `search`.

### GET `/asha/cases/{case_id}`

Returns source-labelled case details and allowed actions.

### POST `/asha/cases/{case_id}/acknowledge`

```json
{"acknowledged_at":"2026-08-23T11:22:00Z"}
```

Validates assignment and transition.

### POST `/asha/cases/{case_id}/contact-result`

```json
{
  "outcome":"SPOKE_TO_CITIZEN",
  "next_action":"PLAN_VISIT",
  "notes":"Citizen agreed to a home visit."
}
```

### POST `/asha/visits`

Creates a visit/draft using `case_id`, identity confirmation, consent, visit type, and optional offline client ID.

### POST `/asha/visits/{visit_id}/vitals`

```json
{
  "systolic_bp":150,
  "diastolic_bp":100,
  "spo2":97,
  "pulse":92,
  "recorded_at":"2026-08-23T11:15:00Z",
  "confirmed_unusual_values":true
}
```

Returns deterministic rule result and recommended workflow action.

### POST `/asha/visits/{visit_id}/complete`

Requires verified extracted fields, notes, and next action.

### POST `/asha/cases/{case_id}/refer`

```json
{
  "facility_id":"phc_uuid",
  "urgency":"IMMEDIATE",
  "reason":"Pregnancy-related warning signs",
  "transport_required":false
}
```

Returns referral and doctor-queue status.

### POST `/asha/cases/{case_id}/follow-ups`

Creates or completes authorized ASHA follow-up work.

## 6. Doctor

### GET `/doctor/dashboard`

Returns urgent referrals, waiting reviews, follow-ups, and pending actions for the authenticated facility/doctor.

### GET `/doctor/referrals`

Supports priority/status/wait filters.

### GET `/doctor/cases/{case_id}`

Returns patient summary, source-labelled data, ASHA visit, vitals, evidence, timeline, documents, and allowed actions.

### POST `/doctor/referrals/{case_id}/acknowledge`

Validates facility scope and publishes acknowledgement event.

### POST `/doctor/cases/{case_id}/clarifications`

Creates an ASHA clarification task.

### POST `/doctor/consultations`

Starts a consultation for an authorized case.

### POST `/doctor/consultations/{id}/assessment`

Doctor-only provisional/confirmed/differential assessment.

### POST `/doctor/consultations/{id}/orders`

Creates test/investigation orders.

### POST `/doctor/consultations/{id}/prescriptions`

Creates a draft. Separate `/issue` action requires explicit confirmation and authorization.

### POST `/doctor/consultations/{id}/care-plan`

Creates citizen, ASHA, and PHC actions.

### POST `/doctor/consultations/{id}/complete`

Validates completion checklist, writes audit record, and generates follow-up/events.

## 7. Admin

### GET `/admin/dashboard`

Returns aggregate counts only.

### GET `/admin/outbreak-alerts`

Returns possible cluster alerts with geography and time bucket, not citizen identity.

### GET `/admin/referral-analytics`

Returns facility/referral response metrics.

### GET `/admin/scheme-analytics`

Returns scheme-support funnel metrics.

### GET `/admin/workforce`

Returns support/workload indicators without a punitive leaderboard.

## 8. AI internal endpoints

These may remain service functions rather than public endpoints. If exposed, restrict to service/admin roles.

```text
POST /ai/normalize
POST /ai/clinical-guidance
POST /ai/scheme-match
POST /ai/verify
```

All outputs use strict schemas with source IDs and prohibited-content flags.

## 9. Reports

```text
POST /reports/referral
POST /reports/consultation
GET  /reports/{document_id}
```

GET returns an authorization-checked short-lived signed link or streamed file.

## 10. Events

WebSocket/SSE events:

```text
CASE_CREATED
ASHA_ASSIGNED
ASHA_ACKNOWLEDGED
VISIT_COMPLETED
REFERRAL_CREATED
DOCTOR_ACKNOWLEDGED
CLARIFICATION_REQUESTED
FOLLOW_UP_CREATED
FOLLOW_UP_COMPLETED
CASE_COMPLETED
```

Example:

```json
{
  "event":"DOCTOR_ACKNOWLEDGED",
  "case_id":"uuid",
  "occurred_at":"2026-08-23T11:30:00Z",
  "safe_payload":{"facility_name":"Kalyanpur PHC"}
}
```

## 11. Standard error codes

```text
AUTHENTICATION_REQUIRED
PERMISSION_DENIED
RESOURCE_NOT_FOUND
INVALID_STATUS_TRANSITION
VALIDATION_ERROR
CONSENT_REQUIRED
DUPLICATE_OPERATION
VERSION_CONFLICT
EXTERNAL_SERVICE_UNAVAILABLE
RATE_LIMITED
UNSAFE_AI_OUTPUT
```

