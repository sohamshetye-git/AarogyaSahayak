# User Flows

## 1. Canonical case lifecycle

```text
NEW
-> ASHA_ASSIGNED
-> ASHA_ACKNOWLEDGED
-> CONTACTED
-> VISIT_SCHEDULED
-> VISIT_IN_PROGRESS
-> ASHA_REVIEWED
-> REFERRED_TO_PHC
-> DOCTOR_ACKNOWLEDGED
-> CONSULTATION_IN_PROGRESS
-> FOLLOW_UP_REQUIRED
-> COMPLETED
```

Alternative states:

```text
PENDING_SYNC
UNREACHABLE
MORE_INFORMATION_REQUIRED
REFERRAL_DECLINED
REFERRED_TO_HIGHER_FACILITY
EMERGENCY_TRANSFER
CANCELLED_WITH_REASON
```

Status changes must be validated server-side.

## 2. Citizen health flow

1. Open application.
2. Choose supported language.
3. Tap the microphone once to start and again to stop.
4. Record a symptom concern.
5. Receive transcript and choose: confirm, replay, or re-record.
6. Backend masks PII and normalizes symptoms.
7. Deterministic emergency rules execute.
8. If required, ask one follow-up question per screen.
9. Router selects clinical, scheme, or combined path.
10. Verifier approves or blocks the draft.
11. Citizen receives short audio plus a clear action.
12. If risk or follow-up exists, create a case and assigned ASHA task.
13. Citizen sees human-friendly status updates.

### Offline citizen flow

1. Detect missing connectivity.
2. Offer `Check urgent warning signs` or `Record and save my message`.
3. Structured answers run through local rules/TFLite.
4. Save encrypted pending data in SQLite.
5. Play cached safety guidance.
6. Synchronize when network returns.
7. Mark the request processed only after backend acknowledgement.

## 3. ASHA urgent-case flow

1. ASHA logs in and lands on `/asha/dashboard`.
2. New urgent case appears at the top.
3. ASHA opens the case and sees source-labelled information.
4. ASHA acknowledges it.
5. System notifies the citizen that a human received the case.
6. ASHA calls the citizen and records contact outcome.
7. ASHA schedules or immediately starts a visit.
8. ASHA verifies citizen identity and records consent.
9. ASHA records symptoms, observations, and vitals.
10. ASHA confirms/corrects AI-extracted fields.
11. Safety rules re-evaluate the verified information.
12. ASHA chooses referral, follow-up, approved education, or medical-officer advice.
13. If referred, FastAPI creates a referral for the selected PHC.
14. Doctor queue receives the case.
15. ASHA sees doctor acknowledgement and later follow-up tasks.

## 4. Doctor referral flow

1. Doctor logs in and lands on `/doctor/dashboard`.
2. Doctor sees urgent referral queue sorted by priority and wait time.
3. Doctor opens and acknowledges the referral.
4. Doctor reviews citizen-reported, ASHA-confirmed, device, AI, and prior doctor information separately.
5. Doctor may request ASHA clarification.
6. Doctor starts an in-person or teleconsultation.
7. Doctor records examination and final assessment.
8. Doctor orders tests if required.
9. Doctor creates and explicitly signs prescription/care plan.
10. Doctor creates a higher referral if required.
11. Doctor assigns follow-up to ASHA/citizen/PHC role.
12. Doctor completes the consultation.
13. Citizen receives only simplified approved instructions.

## 5. Scheme flow

1. Citizen or ASHA asks a health-scheme question.
2. Router sends it to Scheme Agent.
3. Agent requests only missing eligibility fields.
4. Backend converts profile fields into a parameterized Neo4j query.
5. Neo4j returns potential schemes, requirements, packages, and facilities.
6. If current verification is needed, Tavily searches approved official domains.
7. Verifier checks source, timestamp, and wording.
8. UI displays `Potentially relevant` until official confirmation.
9. ASHA can generate a document checklist.

## 6. Admin analytics flow

1. Completed/active cases emit privacy-filtered events.
2. Aggregation service removes direct identifiers and groups by authorized geography/time/category.
3. Admin dashboard displays operational metrics.
4. A threshold-based cluster creates `POSSIBLE_CLUSTER_REVIEW`.
5. Authorized officer reviews and records an administrative disposition.
6. Only an authorized health authority may mark an outbreak confirmed.

## 7. Failure flows

### AI unavailable

```text
AI timeout/error
-> no fabricated response
-> safe fallback message
-> save case
-> offer ASHA/human support
```

### BHASHINI unavailable

```text
Voice service unavailable
-> retain recording only under consent/retention rule
-> allow typed/structured input
-> queue retry
```

### Duplicate offline sync

```text
Client retries with idempotency key
-> backend returns original accepted result
-> no duplicate case/visit/referral
```

### Conflicting clinical edit

```text
Server version differs from offline draft
-> do not overwrite
-> show both values and authors/timestamps
-> authorized user resolves conflict
-> audit decision
```

## 8. Notification flow

Events are created by FastAPI and may be delivered by portal notifications, push, SMS, or an authorized messaging channel through n8n. Notification payloads shown on lock screens must be generic and must not expose sensitive conditions.

