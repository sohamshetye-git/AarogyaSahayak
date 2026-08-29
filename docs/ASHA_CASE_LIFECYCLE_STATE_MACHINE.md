# Aarogya Sahayak — ASHA Case Lifecycle State Machine

## 1. Authoritative State Graph & Transitions

```mermaid
stateDiagram-v2
    [*] --> NEW: Case Created (Citizen App / Voice Intake / Registration)
    NEW --> ASHA_ACKNOWLEDGED: ASHA clicks "Acknowledge Case"
    ASHA_ACKNOWLEDGED --> CITIZEN_CONTACTED: Spoke to Citizen / Contact Saved
    ASHA_ACKNOWLEDGED --> ASHA_ACKNOWLEDGED: Unreachable Attempt Logged
    CITIZEN_CONTACTED --> ASHA_REVIEWED: In-Person Field Visit Submitted
    ASHA_REVIEWED --> REFERRED_TO_PHC: Urgent/Routine PHC Referral Created
    REFERRED_TO_PHC --> DOCTOR_ACKNOWLEDGED: PHC Medical Officer Reviews Case
    DOCTOR_ACKNOWLEDGED --> FOLLOW_UP_REQUIRED: Doctor Issues Clinical Directive
    FOLLOW_UP_REQUIRED --> COMPLETED: ASHA Submits Repeat Follow-up Check
    COMPLETED --> [*]
```

---

## 2. State Invariants & Role Access Matrix

| Case Status | Permitted Actor | Permitted Action | Triggered API Route | Next Status | UI Presentation |
|---|---|---|---|---|---|
| `NEW` | ASHA Worker | Acknowledge Assignment | `POST /asha/cases/:id/acknowledge` | `ASHA_ACKNOWLEDGED` | Primary "Acknowledge Case" button |
| `ASHA_ACKNOWLEDGED` | ASHA Worker | Spoke to Citizen | `POST /asha/cases/:id/contact-result` | `CITIZEN_CONTACTED` | "Spoke to Citizen" Modal |
| `ASHA_ACKNOWLEDGED` | ASHA Worker | Log Unreachable | `POST /asha/cases/:id/contact-result` | `ASHA_ACKNOWLEDGED` | "Unreachable" Modal (Attempt ++ ) |
| `CITIZEN_CONTACTED` | ASHA Worker | Conduct Field Visit | `POST /asha/visits` | `ASHA_REVIEWED` | 7-Step Field Visit Wizard |
| `ASHA_REVIEWED` | ASHA Worker / System | Submit PHC Referral | `POST /asha/referrals` | `REFERRED_TO_PHC` | Instant Doctor Queue Referral |
| `REFERRED_TO_PHC` | PHC Doctor | Doctor Review | `POST /doctor/referrals/:id/acknowledge` | `DOCTOR_ACKNOWLEDGED` | Doctor Referral Queue |
| `DOCTOR_ACKNOWLEDGED` | PHC Doctor | Consultation / Directives | `POST /doctor/consultations` | `FOLLOW_UP_REQUIRED` | Doctor Prescription & Instructions |
| `FOLLOW_UP_REQUIRED` | ASHA Worker | Complete Home Checkup | `POST /asha/followups/:id/complete` | `COMPLETED` | Follow-up Completion Modal |
| `COMPLETED` | All Roles | View Longitudinal History | `GET /asha/cases/:id` | None (Final State) | Read-only Audit Trail & Timeline |

---

## 3. Idempotency & Concurrency Rules
* Every POST state mutation accepts an `Idempotency-Key` header with UUIDv4.
* Re-executing an acknowledged or completed request with the same key returns the cached HTTP 200 payload and does NOT create duplicate timeline entries or duplicate database records.
