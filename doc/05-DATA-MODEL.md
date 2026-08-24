# Data Model

## 1. Conventions

- Primary IDs are UUIDs; optional human references may use `CASE-2026-0001`.
- Store timestamps in UTC with timezone.
- Use append-only audit history for clinically meaningful changes.
- Use soft deletion/status for clinical records; do not hard-delete signed records.
- Keep enums centralized.
- Use optimistic version numbers for offline-conflict detection.

## 2. Core enums

```text
UserRole: CITIZEN, ASHA_WORKER, PHC_DOCTOR, DISTRICT_ADMIN, SYSTEM_ADMIN

Priority: URGENT, HIGH, FOLLOW_UP, ROUTINE, INFORMATION

CaseStatus: NEW, ASHA_ASSIGNED, ASHA_ACKNOWLEDGED, CONTACTED,
VISIT_SCHEDULED, VISIT_IN_PROGRESS, ASHA_REVIEWED, REFERRED_TO_PHC,
DOCTOR_ACKNOWLEDGED, CONSULTATION_IN_PROGRESS, MORE_INFORMATION_REQUIRED,
FOLLOW_UP_REQUIRED, REFERRED_TO_HIGHER_FACILITY, COMPLETED, CANCELLED

SourceType: CITIZEN_REPORTED, ASHA_CONFIRMED, DEVICE_MEASURED,
AI_EXTRACTED, RULE_GENERATED, DOCTOR_CONFIRMED

SyncStatus: PENDING, SYNCING, SYNCED, FAILED, CONFLICT
```

## 3. Entities

### User

```text
id UUID PK
name string
phone encrypted/hashed lookup representation as appropriate
email nullable
password_hash
role
preferred_language
active boolean
created_at
updated_at
```

### CitizenProfile

```text
id UUID PK
user_id nullable FK User
display_name
date_of_birth nullable
age_estimate nullable
sex nullable
preferred_language
village_id FK
abha_reference_encrypted nullable
abha_link_status
version integer
created_at
updated_at
```

### WorkerProfile

```text
id UUID PK
user_id FK User
worker_type ASHA/DOCTOR/ADMIN
facility_id nullable
district_id nullable
professional_registration nullable
created_at
```

### Case

```text
id UUID PK
reference unique string
citizen_id FK
priority
status
primary_concern
preferred_language
assigned_asha_id nullable FK
assigned_facility_id nullable FK
assigned_doctor_id nullable FK
created_by
version integer
created_at
updated_at
completed_at nullable
```

### SymptomObservation

```text
id UUID PK
case_id FK
spoken_term nullable
normalized_term
standard_code nullable
present boolean
duration_text nullable
severity nullable
source_type
recorded_by
recorded_at
confirmed_by nullable
```

### VitalRecord

```text
id UUID PK
case_id FK
visit_id nullable FK
systolic_bp nullable
diastolic_bp nullable
temperature_c nullable
spo2 nullable
pulse nullable
respiratory_rate nullable
glucose_mg_dl nullable
weight_kg nullable
source_type
recorded_by
recorded_at
confirmation_required boolean
confirmed_at nullable
```

### AshaVisit

```text
id UUID PK
case_id FK
asha_worker_id FK
visit_type
status
scheduled_at nullable
started_at nullable
completed_at nullable
consent_status
notes
next_action
offline_client_id nullable
version integer
```

### Referral

```text
id UUID PK
case_id FK
from_asha_id nullable
from_doctor_id nullable
to_facility_id FK
urgency
reason
status
created_at
acknowledged_by nullable
acknowledged_at nullable
```

### Consultation

```text
id UUID PK
case_id FK
doctor_id FK
facility_id FK
consultation_type
status
examination_notes
clinical_summary
started_at
completed_at nullable
signed_at nullable
version integer
```

### Diagnosis

```text
id UUID PK
consultation_id FK
term
code nullable
diagnosis_type provisional/confirmed/differential
doctor_id FK
confirmed_at nullable
```

### Prescription and PrescriptionItem

```text
Prescription: id, consultation_id, doctor_id, status, issued_at, signature_ref
PrescriptionItem: medicine, strength, form, dose, frequency, route,
duration, timing, instructions, reason
```

### TestOrder and TestResult

```text
TestOrder: id, consultation_id, test_name, priority, reason, facility_id,
status, ordered_at, due_at
TestResult: id, order_id, result_text, reference_range, abnormal_flag,
document_id, reviewed_by, reviewed_at
```

### FollowUp

```text
id UUID PK
case_id FK
task_type
assigned_role
assigned_user_id nullable
instructions
priority
due_at
status
result
created_by
completed_at nullable
```

### ConsentRecord

```text
id UUID PK
citizen_id FK
case_id nullable FK
purpose
status
language
captured_by
captured_at
expires_at nullable
withdrawn_at nullable
```

### Notification

```text
id UUID PK
recipient_user_id FK
case_id nullable FK
type
title_generic
body_private nullable
priority
read_at nullable
delivery_status
created_at
```

### SchemeCheck

```text
id UUID PK
case_id nullable
citizen_id
scheme_code
result POTENTIAL/VERIFIED_NOT/VERIFIED_ELIGIBLE/UNKNOWN
reason_summary
source_urls
verified_at nullable
created_at
```

### Document

```text
id UUID PK
case_id FK
document_type
object_key
mime_type
created_by
approval_status
signed_by nullable
created_at
```

### AuditLog

```text
id UUID PK
actor_user_id nullable
actor_role
action
resource_type
resource_id
outcome
metadata_redacted JSON
timestamp
```

## 4. Relationships

```text
Citizen 1 -> many Cases
Case 1 -> many Symptoms
Case 1 -> many Vitals
Case 1 -> many ASHA Visits
Case 1 -> many Referrals
Case 1 -> many Consultations
Consultation 1 -> many Diagnoses
Consultation 1 -> many Prescriptions
Consultation 1 -> many Test Orders
Case 1 -> many FollowUps
Case 1 -> many Documents
Case 1 -> many AuditLogs
```

## 5. Milvus schema

```text
id
document_id
chunk_id
title
source_organization
source_url
publication_date
document_version
section
language
text
embedding
approved boolean
```

No patient data is permitted in this collection.

## 6. Neo4j graph

Nodes:

```text
Scheme, EligibilityRule, HealthPackage, DocumentRequirement,
State, District, Facility, DiseaseCategory
```

Relationships:

```text
(Scheme)-[:AVAILABLE_IN]->(State)
(Scheme)-[:HAS_RULE]->(EligibilityRule)
(Scheme)-[:COVERS_PACKAGE]->(HealthPackage)
(Scheme)-[:REQUIRES]->(DocumentRequirement)
(HealthPackage)-[:AVAILABLE_AT]->(Facility)
(HealthPackage)-[:TREATS_CATEGORY]->(DiseaseCategory)
```

Use parameterized Cypher queries. Never concatenate user input into Cypher.

## 7. Indexes and constraints

- Unique: User email where present, Case reference, Scheme code, Facility code.
- Index: Case status/priority/assigned worker/facility/created_at.
- Index: FollowUp assigned_user/due_at/status.
- Index: Referral facility/status/urgency.
- Index: Notification recipient/read_at.
- Full-text or normalized search fields for authorized citizen lookup.

## 8. Seed data

Provide demo accounts and fixtures:

```text
asha01 / demo password
doctor01 / demo password
admin01 / demo password
citizen Sunita Devi
ASHA Sita Patel
Doctor Dr Sharma
Kalyanpur PHC
canonical urgent pregnancy case
```

Demo credentials must be disabled or changed outside development.

