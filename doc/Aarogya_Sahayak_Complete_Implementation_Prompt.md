YOU ARE THE LEAD FULL-STACK SOFTWARE ARCHITECT AND IMPLEMENTATION AGENT FOR:

AAROGYA SAHAYAK

AI-Powered, Voice-First Rural Healthcare Assistance, ASHA Copilot, PHC Referral and Government Health Intelligence Platform for India.

Build a complete hackathon-ready application with a production-oriented architecture.

Do not build a generic chatbot.

Do not build four disconnected applications.

Build one integrated healthcare ecosystem connecting:

Rural Citizen
ASHA Worker
PHC Doctor
District Health Officer / Government Administrator

Before modifying code:

Inspect the entire existing repository.
Locate existing Figma exports, screenshots, design tokens and assets.
Identify the current frontend, backend, database and configuration.
Identify uncommitted or user-created work.
Preserve existing working functionality.
Do not rewrite unrelated files.
Do not delete existing code without explaining why.
Do not create duplicate React applications if a shared portal already exists.
Do not introduce unnecessary dependencies.
Follow existing project conventions when they are reasonable.
Keep TypeScript strict.
Keep Python type-safe and validated with Pydantic.
Never hardcode API keys, passwords or private health information.
Add an .env.example, but never add real secrets.
Build incrementally and verify every phase.
Run formatting, linting, type-checking, tests and production builds.
Report every changed file.
Preserve separation between clinical assistance and final medical decisions.
Never generate hidden chain-of-thought for users.
Never present AI output as a confirmed diagnosis.

Start by returning:

Existing repository analysis
Proposed architecture
Files to create or modify
Risks and assumptions
Phased implementation plan

Then implement the approved architecture incrementally.

If the repository is empty, scaffold the monorepo described below.

==================================================

PRODUCT DEFINITION
==================================================

Aarogya Sahayak is a voice-first rural healthcare coordination platform.

It helps rural citizens:

Speak about health concerns in a regional language
Receive short, safe, non-diagnostic guidance
Detect configured emergency warning signs
Connect to an assigned ASHA worker
Find relevant government healthcare schemes
Find healthcare facilities
Track referral and follow-up status
Work during limited connectivity

It helps ASHA workers:

See risk-prioritized citizen tasks
Acknowledge urgent cases
Contact citizens
Plan and conduct field visits
Record symptoms and vital signs
Verify AI-extracted information
Use consent-based voice-assisted notes
Work offline
Refer patients to PHCs
Assist with scheme-document requirements
Track doctor acknowledgement
Complete follow-ups

It helps PHC doctors:

Review ASHA referrals
Acknowledge urgent referrals
Review patient, ASHA and AI-assisted information separately
Conduct consultations
Confirm the final clinical diagnosis
Order investigations
Write and approve prescriptions
Create care plans
Refer patients to higher facilities
Assign ASHA follow-ups
Generate approved clinical documents

It helps district health officers:

View anonymized district-level health statistics
Review possible symptom clusters
Monitor referral performance
Review scheme-utilization gaps
Review facility workload
Review ASHA workload support requirements
Monitor synchronization and operational health

The application is not a doctor replacement.

The citizen-facing AI may:

Summarize reported symptoms
Identify configured warning signs
Provide approved general health information
Recommend appropriate professional evaluation
Find potentially relevant health schemes
Help find healthcare facilities
Escalate to ASHA or PHC services

The citizen-facing AI must not:

Confirm a diagnosis
Prescribe medication
Select dosage
Recommend stopping prescribed medication
Claim guaranteed scheme eligibility
Claim emergency dispatch occurred unless integration confirms it
Hide uncertainty
Override deterministic emergency rules

Only an authenticated doctor may:

Confirm a diagnosis
Approve medicine
Enter dosage
Sign a prescription
Approve a clinical care plan
Complete a clinical consultation

Every AI-generated clinical summary must display:

“AI-assisted summary – human review required.”

Every citizen health-response screen must display:

“AI-assisted information – not a diagnosis.”

Do not show artificial confidence percentages to citizens.

Use:

“We need more information.”
“Warning signs were detected.”
“Urgent professional evaluation is recommended.”
“I cannot determine this safely.”
“Your ASHA worker has been notified.”

The first working vertical slice must implement this scenario:

A pregnant citizen opens the mobile application.
She chooses Marathi or Hindi.
She reports blurred vision, severe headache and swollen feet.
She enters or an ASHA later records BP 150/100.
Deterministic safety rules identify pregnancy-related warning signs.
The citizen receives calm urgent guidance.
A case is created and assigned to an ASHA worker.
The ASHA dashboard receives the urgent case.
The ASHA worker acknowledges the case.
The citizen sees that the ASHA worker received it.
The ASHA worker conducts a field visit.
The ASHA worker confirms symptoms and enters vital signs.
The ASHA worker refers the case to a PHC.
The Doctor Referral Queue receives the same case.
The doctor acknowledges the referral.
The ASHA worker and citizen receive the acknowledgement.
The doctor reviews the patient and ASHA information.
The doctor records a consultation and care plan.
The doctor assigns a BP follow-up to the ASHA worker.
The ASHA dashboard receives the follow-up.
The District Admin dashboard updates anonymized maternal-risk and referral statistics.

All interfaces must use the same case_id.

Build two user-facing applications:

A. Citizen Mobile Application

Technology:
React Native + Expo + TypeScript

Users:
Rural citizens

B. Healthcare Web Portal

Technology:
React + Vite + TypeScript

Users:
ASHA workers, PHC doctors and District Admins

Protected routes:

/asha/*
/doctor/*
/admin/*

Common login:

/login

C. Shared Backend

Technology:
FastAPI + Pydantic + SQLAlchemy + PostgreSQL

Responsibilities:

Authentication
Role-based authorization
Case management
Task assignment
Field visits
Referrals
Consultations
Follow-ups
Notifications
AI orchestration
Government integrations
Audit history
Aggregated analytics

D. Specialized Data Services

PostgreSQL: operational application data
Milvus: approved clinical guideline embeddings
Neo4j: government health-scheme relationships and rules
SQLite: citizen mobile offline data
IndexedDB: ASHA PWA offline drafts and synchronization queue

E. AI and Integration Services

Lyzr: multi-agent orchestration
Gemini: controlled language reasoning and response generation
BHASHINI: speech-to-text, translation and text-to-speech
Swytchcode: governed external tool execution
Tavily: current official-domain verification
n8n: operational notifications and follow-up automation
ABDM Sandbox: consented ABHA and care-context demonstration
TensorFlow Lite: bounded offline triage classification
LaTeX or equivalent PDF service: professional clinical documents

Use adapters for all external services.

The application must work in mock mode without external credentials.

Use this structure when creating a new repository:

aarogya-sahayak/
│
├── apps/
│ ├── citizen-mobile/
│ │ ├── app/
│ │ ├── components/
│ │ ├── features/
│ │ ├── services/
│ │ ├── offline/
│ │ ├── hooks/
│ │ ├── types/
│ │ └── assets/
│ │
│ └── healthcare-portal/
│ ├── src/
│ │ ├── app/
│ │ ├── auth/
│ │ ├── layouts/
│ │ ├── features/
│ │ │ ├── asha/
│ │ │ ├── doctor/
│ │ │ └── admin/
│ │ ├── components/
│ │ ├── services/
│ │ ├── hooks/
│ │ ├── types/
│ │ └── styles/
│ └── public/
│
├── backend/
│ ├── app/
│ │ ├── main.py
│ │ ├── config.py
│ │ ├── database.py
│ │ ├── dependencies.py
│ │ ├── auth/
│ │ ├── models/
│ │ ├── schemas/
│ │ ├── repositories/
│ │ ├── routers/
│ │ │ ├── auth.py
│ │ │ ├── citizen.py
│ │ │ ├── asha.py
│ │ │ ├── doctor.py
│ │ │ ├── admin.py
│ │ │ ├── integrations.py
│ │ │ └── websocket.py
│ │ ├── services/
│ │ │ ├── case_service.py
│ │ │ ├── triage_service.py
│ │ │ ├── referral_service.py
│ │ │ ├── consultation_service.py
│ │ │ ├── notification_service.py
│ │ │ ├── report_service.py
│ │ │ └── aggregation_service.py
│ │ ├── integrations/
│ │ │ ├── base.py
│ │ │ ├── bhashini.py
│ │ │ ├── lyzr.py
│ │ │ ├── gemini.py
│ │ │ ├── milvus.py
│ │ │ ├── neo4j.py
│ │ │ ├── tavily.py
│ │ │ ├── swytchcode.py
│ │ │ ├── n8n.py
│ │ │ └── abdm.py
│ │ ├── safety/
│ │ │ ├── emergency_rules.py
│ │ │ ├── output_guard.py
│ │ │ └── pii_masking.py
│ │ ├── analytics/
│ │ └── tests/
│ ├── alembic/
│ └── requirements.txt
│
├── packages/
│ ├── shared-types/
│ ├── design-tokens/
│ └── api-client/
│
├── ai/
│ ├── agents/
│ ├── prompts/
│ ├── clinical-rag/
│ ├── scheme-graph/
│ └── edge-model/
│
├── automation/
│ └── n8n-workflows/
│
├── infrastructure/
│ ├── docker/
│ └── docker-compose.yml
│
├── docs/
│ ├── architecture.md
│ ├── api-contract.md
│ ├── database-schema.md
│ ├── safety.md
│ ├── demo-guide.md
│ └── setup.md
│
├── .env.example
├── README.md
└── docker-compose.yml

Citizen mobile:

React Native
Expo
TypeScript
Expo Router
SecureStore for secure token storage
SQLite for offline queue
Network connectivity detection
Audio recording
React Hook Form
Zod
TanStack Query
Accessible React Native components

Healthcare portal:

React
Vite
TypeScript
React Router
TanStack Query
React Hook Form
Zod
Tailwind CSS or the existing styling system
IndexedDB/Dexie for ASHA offline drafts
PWA support
Accessible charts only where necessary
WebSocket or Server-Sent Events for live updates

Do not add Redux unless the existing project already requires it.

Use server state through TanStack Query.

Use local state for forms and interface controls.

Use a small global store only for:

Authenticated user
Language
Connectivity
Unsynchronized action count

Use the existing Figma design.

If design tokens do not exist, implement:

Primary:
#1565C0

Primary Dark:
#0D47A1

Primary Light:
#E3F2FD

Secondary Teal:
#00897B

Background:
#F6F8FB

Surface:
#FFFFFF

Primary Text:
#17202A

Secondary Text:
#5F6B76

Border:
#D9E0E7

Urgent:
#C62828

Urgent Background:
#FDECEC

Warning:
#D65A00

Warning Background:
#FFF3E8

Success:
#2E7D32

Success Background:
#EAF5EB

Offline:
#8A5200

Offline Background:
#FFF4E5

Typography:

Noto Sans
Noto Sans Devanagari where required
Noto Sans fonts for other supported Indian scripts

Desktop Page Title:
28/36 px, 600

Mobile Page Title:
24/32 px, 600

Section Title:
20–22 px, 600

Card Title:
17–18 px, 600

Body:
16/24 px

Secondary:
14/20–21 px

Caption:
12/16 px

Button:
16/20 px, 600

Important Vital:
24–28/32–36 px, 700

Use an 8-point spacing system.

Minimum touch target:
48 × 48 px

Use colour + icon + text for status.

Meet WCAG AA contrast.

Use one portal login.

Do not allow users to choose their role.

Backend determines role from account.

Roles:

CITIZEN
ASHA_WORKER
PHC_DOCTOR
DISTRICT_ADMIN

Use JWT access and refresh tokens or the existing secure authentication solution.

For the browser portal, prefer secure HTTP-only cookies when feasible.

Implement:

Password hashing
Access-token expiry
Refresh flow
Logout
Session timeout
Protected routes
Backend permission checks
Audit logs
Rate limiting on login
Generic invalid-login messages

Example login response:

{
"user": {
"id": "ASHA-012",
"name": "Sita Patel",
"role": "ASHA_WORKER",
"facility_id": "PHC-09",
"village_ids": ["VILLAGE-01"]
}
}

Redirect:

ASHA_WORKER → /asha/dashboard
PHC_DOCTOR → /doctor/dashboard
DISTRICT_ADMIN → /admin/dashboard

Frontend route guards improve UX.

Backend authorization is mandatory for security.

CITIZEN:

Manage own profile
Create health request
View own cases
View own notifications
Give or withdraw consent
View approved guidance
View approved scheme information

ASHA_WORKER:

View assigned citizens
View assigned cases
Acknowledge tasks
Conduct field visits
Confirm or correct extracted information
Record vital signs
Create PHC referral
Schedule follow-up
Assist with health-scheme documents
View doctor acknowledgement
Work with offline drafts

PHC_DOCTOR:

View referrals assigned to facility
View authorized patient information
Acknowledge referrals
Conduct consultation
Confirm diagnosis
Create prescriptions
Order tests
Create care plan
Refer to higher facility
Assign follow-up
Sign doctor documents

DISTRICT_ADMIN:

View aggregated district statistics
Review possible cluster alerts
Review referral trends
Review scheme-utilization trends
Review facility workload
Review workforce support indicators
Manage authorized operational configuration

District Admin must not normally access raw private citizen conversations or complete clinical records.

Create SQLAlchemy models and Alembic migrations for:

users
roles
user_roles
citizen_profiles
asha_profiles
doctor_profiles
admin_profiles
facilities
districts
blocks
villages
households
cases
case_assignments
symptoms
case_symptoms
vital_records
triage_results
safety_rule_events
asha_tasks
asha_visits
visit_notes
consent_records
referrals
referral_events
consultations
diagnoses
prescriptions
prescription_items
investigation_orders
test_results
care_plans
follow_ups
notifications
scheme_definitions
scheme_checks
facility_scheme_links
documents
integration_events
sync_operations
audit_logs
anonymized_events
cluster_alerts

Use UUIDs internally.

Human-readable references may use:

CASE-2026-001
REF-2026-001
VISIT-2026-001

Store timestamps in UTC.

Expose localized timestamps in the UI.

Add:

created_at
updated_at
created_by where relevant
version for optimistic concurrency where relevant
soft deletion only where legally and operationally appropriate
audit events for clinical changes

Never silently overwrite signed clinical records.

Corrections must create an audit event.

CasePriority:

URGENT
HIGH
FOLLOW_UP
ROUTINE
INFORMATION

CaseStatus:

NEW
ASHA_ACKNOWLEDGED
CITIZEN_CONTACTED
VISIT_SCHEDULED
VISIT_IN_PROGRESS
ASHA_REVIEWED
REFERRED_TO_PHC
DOCTOR_ACKNOWLEDGED
PATIENT_ARRIVED
CONSULTATION_IN_PROGRESS
FOLLOW_UP_REQUIRED
REFERRED_HIGHER
COMPLETED
UNREACHABLE
DECLINED
PENDING_SYNC

InformationSource:

CITIZEN_REPORTED
ASHA_CONFIRMED
DEVICE_MEASURED
AI_EXTRACTED
RULE_GENERATED
DOCTOR_CONFIRMED

IntegrationStatus:

PENDING
PROCESSING
SUCCESS
FAILED_RETRYABLE
FAILED_FINAL
MOCKED

Use REST for normal operations.

Use WebSocket or Server-Sent Events for real-time case updates.

FastAPI must generate OpenAPI documentation.

Use consistent response and error structures.

Example validation error:

{
"error": {
"code": "VALIDATION_ERROR",
"message": "Please check the entered information.",
"fields": {
"systolic_bp": "Enter a valid number."
},
"request_id": "..."
}
}

Do not expose stack traces to frontend users.

POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
GET /api/auth/me

GET /api/citizen/profile
PUT /api/citizen/profile
POST /api/citizen/cases
GET /api/citizen/cases
GET /api/citizen/cases/{case_id}
POST /api/citizen/cases/{case_id}/audio
POST /api/citizen/cases/{case_id}/transcript-confirmation
POST /api/citizen/cases/{case_id}/answers
POST /api/citizen/cases/{case_id}/vitals
POST /api/citizen/cases/{case_id}/consent
GET /api/citizen/notifications
GET /api/citizen/facilities
POST /api/citizen/scheme-checks
POST /api/citizen/sync

GET /api/asha/dashboard
GET /api/asha/tasks
GET /api/asha/tasks/{task_id}
GET /api/asha/cases/{case_id}
POST /api/asha/cases/{case_id}/acknowledge
POST /api/asha/cases/{case_id}/contact-result
POST /api/asha/cases/{case_id}/schedule-visit
POST /api/asha/visits
GET /api/asha/visits/{visit_id}
PUT /api/asha/visits/{visit_id}
POST /api/asha/visits/{visit_id}/consent
POST /api/asha/visits/{visit_id}/symptoms
POST /api/asha/visits/{visit_id}/vitals
POST /api/asha/visits/{visit_id}/verify-extraction
POST /api/asha/visits/{visit_id}/complete
POST /api/asha/cases/{case_id}/refer
POST /api/asha/cases/{case_id}/follow-up
GET /api/asha/people
GET /api/asha/people/{patient_id}
GET /api/asha/notifications
POST /api/asha/sync

GET /api/doctor/dashboard
GET /api/doctor/referrals
GET /api/doctor/referrals/{case_id}
POST /api/doctor/referrals/{case_id}/acknowledge
POST /api/doctor/referrals/{case_id}/request-information
POST /api/doctor/referrals/{case_id}/redirect
GET /api/doctor/patients
GET /api/doctor/patients/{patient_id}
POST /api/doctor/consultations
GET /api/doctor/consultations/{consultation_id}
PUT /api/doctor/consultations/{consultation_id}
POST /api/doctor/consultations/{consultation_id}/diagnosis
POST /api/doctor/consultations/{consultation_id}/orders
POST /api/doctor/consultations/{consultation_id}/prescription
POST /api/doctor/consultations/{consultation_id}/care-plan
POST /api/doctor/consultations/{consultation_id}/complete
POST /api/doctor/cases/{case_id}/refer-higher
POST /api/doctor/cases/{case_id}/follow-up
GET /api/doctor/results
POST /api/doctor/results/{result_id}/review
GET /api/doctor/reports
GET /api/doctor/notifications

GET /api/admin/dashboard
GET /api/admin/district-summary
GET /api/admin/block-summary
GET /api/admin/village-summary
GET /api/admin/cluster-alerts
POST /api/admin/cluster-alerts/{alert_id}/review
POST /api/admin/cluster-alerts/{alert_id}/assign-investigation
GET /api/admin/referral-analytics
GET /api/admin/scheme-analytics
GET /api/admin/facility-performance
GET /api/admin/workforce-overview
GET /api/admin/system-health
GET /api/admin/reports

Admin APIs should return aggregated or anonymized data by default.

Build these screens:

Splash
Language selection
Optional simple profile
Home
Voice listening
Transcript confirmation
Follow-up questions
Processing
Normal guidance
High-risk guidance
Uncertain result
Government health schemes
Scheme questions
Scheme result
Healthcare finder
My Health Updates
Case details
ASHA status
Notifications
Offline safety check
Saved requests
Profile and privacy

Citizen navigation:

Home
My Updates
Help

Do not create a duplicate Ask destination.

The microphone is the main Home action.

Use tap-to-start and tap-to-stop consistently.

Use audio-first guidance.

Provide a text alternative.

Citizen taps microphone.
Mobile streams compressed audio to FastAPI.
FastAPI sends audio through the BHASHINI adapter.
BHASHINI returns transcript and language confidence.
Citizen confirms transcript.
PII masking removes unnecessary identifiers.
Dialect normalizer maps colloquial terms to clinical concepts.
Deterministic emergency rules execute.
If urgent, create the case and notify ASHA immediately.
If not urgent, route to the Lyzr agent system.
Clinical Agent retrieves approved clinical information.
Scheme Agent retrieves scheme rules if relevant.
Verification Agent reviews the response.
Verified response is converted through BHASHINI TTS.
Citizen receives audio, text, icons and next action.
Case status becomes available in My Updates.

Do not claim that TensorFlow Lite understands unrestricted offline voice unless a real on-device speech model is implemented.

When offline, provide two options:

A. Check urgent warning signs now

Use structured questions and vital signs.

B. Record and save my message

Save encrypted audio/request locally for processing after reconnection.

Offline urgent flow:

Pregnancy status
Difficulty breathing
Heavy bleeding
Unconsciousness
Convulsions
Chest pain
Severe headache
Blurred vision
Vital signs if available

Run:

Deterministic local safety rules
TFLite bounded risk categorization
Cached safety messages

Save to SQLite.

Synchronize after connectivity returns.

Protected route:

/asha/*

ASHA navigation:

Home
Tasks
Visit
People
More

Build:

ASHA Dashboard
Priority task list
Urgent-case details
Alert acknowledgement
Contact-result dialog
Plan home visit
Citizen identification
Consent
Field-visit wizard
Symptoms
Vitals
AI-extraction verification
Safety warning
ASHA assessment
PHC referral
Referral success
Report preview
Follow-up management
People directory
Citizen profile
Scheme assistance
Document checklist
Notifications
Offline queue
Synchronization states

Every AI-extracted field must support:

Confirm
Correct
Mark unclear

ASHA cannot make a final diagnosis or prescription.

Open assigned case.
Acknowledge.
Contact citizen.
Schedule or start visit.
Confirm citizen identity.
Obtain consent.
Select reason for visit.
Record symptoms.
Enter vital signs.
Review AI-extracted information.
Run local and backend safety rules.
Confirm or correct priority.
Choose next action.
Refer to PHC if required.
Generate structured field summary.
Wait for doctor acknowledgement.
Complete assigned follow-up.

Save a draft after every step.

Protected route:

/doctor/*

Doctor navigation:

Dashboard
Referral Queue
Patients
Consultations
Orders & Tests
Prescriptions
Follow-ups
Reports
Notifications

Build:

Doctor Dashboard
Urgent referral queue
Referral acknowledgement
Patient case review
ASHA field summary
Citizen message and transcript
Vitals timeline
AI-assisted summary
Evidence panel
Request ASHA clarification
Consultation workspace
Examination
Doctor assessment
Diagnosis confirmation
Investigation orders
Result review
Prescription builder
Medicine safety alerts
Citizen-language instruction preview
Care plan
Scheme package review
Higher-facility referral
Consultation completion
Follow-up assignment
Patient directory
Longitudinal record
Reports
Notifications
Doctor receives referral assigned to the PHC.
Doctor acknowledges the referral.
ASHA and citizen receive status update.
Doctor reviews citizen-reported information.
Doctor reviews ASHA-confirmed information.
Doctor reviews device measurements.
Doctor reviews AI-assisted summary.
Doctor begins consultation.
Doctor records examination.
Doctor confirms clinical diagnosis.
Doctor orders tests if necessary.
Doctor writes and approves prescription.
Doctor creates care plan.
Doctor assigns follow-up to ASHA.
Doctor completes consultation.
Citizen receives approved simplified instructions.
ABDM sandbox update is queued after consent.

Protected route:

/admin/*

Admin navigation:

Overview
Public Health Alerts
Geography
Referral Analytics
Scheme Analytics
Facilities
ASHA Workforce
Reports
System Health
Notifications

Build:

District overview
Active urgent-case aggregate
Referral trends
Facility workload
Follow-up completion
Scheme-utilization analytics
Village and block comparisons
Possible symptom-cluster alerts
Cluster review
Field investigation assignment
Workforce support indicators
Synchronization health
Integration health
Reports

Do not create a punitive ASHA leaderboard.

Use supportive indicators such as:

High workload
Additional support recommended
Many records awaiting sync
Connectivity-related delay

Admin analytics should use anonymized events.

Example:

{
"district_id": "DISTRICT-04",
"block_id": "BLOCK-02",
"village_id": "VILLAGE-01",
"symptom_group": "FEVER_JOINT_PAIN",
"case_count": 18,
"time_window_hours": 48
}

Do not send:

Patient name
Phone
Raw transcript
ABHA number
Full address
Private doctor notes

Possible cluster detection is an early-warning signal, not a confirmed outbreak.

Use:

“Possible symptom cluster – epidemiological review required.”

Implement safety rules separately from AI.

Rules must be configuration-driven and tested.

Initial demonstration rules may include:

Chest pain
Severe breathlessness
Unconsciousness
Convulsions
Heavy bleeding
Severe pregnancy warning signs
Very low SpO₂
Configured critical BP combinations
Self-harm expressions

Example demonstration rule:

Pregnant
AND
(Systolic BP >= configured threshold OR Diastolic BP >= configured threshold)
AND
(Blurred vision OR severe headache)
→ URGENT professional evaluation

Do not present demonstration thresholds as universally complete clinical policy.

Document their source and review status.

The backend must run the authoritative rule check.

The frontend may run a copy for immediate offline warning, but cannot override backend safety results.

Use TensorFlow Lite only for bounded offline triage categories.

Input examples:

Age
Pregnancy status
Systolic BP
Diastolic BP
SpO₂
Temperature
Glucose
Structured symptom flags

Output:

ROUTINE
FOLLOW_UP
URGENT

The model must not output disease diagnosis.

Hardcoded emergency rules run before or alongside the model.

Prioritize recall for critical risk during experimentation, but clearly report false-positive and false-negative evaluation.

Include:

Model training script
Evaluation
Confusion matrix
Quantization
.tflite export
Representative dataset
Model metadata
Input normalization
Mobile inference wrapper

Use a deterministic mock risk service until a properly evaluated model is available.

Use Lyzr as the primary orchestrator.

Do not claim both Lyzr and LangGraph are simultaneously the main orchestrator.

Agents:

Intake and Router Agent
Clinical Triage Agent
Government Scheme Agent
Critic/Verification Agent

Router Agent:

Receives PII-protected normalized text
Classifies medical, scheme or mixed intent
Detects missing information
Routes tasks
Bypasses AI when deterministic emergency rule triggers

Clinical Agent:

Uses approved clinical Vector RAG
Does not search unrestricted internet
Produces non-diagnostic draft guidance
Includes citations/source IDs

Scheme Agent:

Uses Neo4j GraphRAG for exact scheme relationships
Uses Tavily only when live official verification is necessary
Distinguishes potential relevance from verified eligibility

Verification Agent:

Checks source support
Checks contradictions
Checks medical boundaries
Blocks prescriptions
Blocks unsupported eligibility claims
Checks response length and clarity
Escalates uncertain output to human review

Store agent audit metadata, but do not expose hidden reasoning.

Use Milvus for approved clinical information.

Initial data may include licensed or publicly permitted:

ICMR Standard Treatment Workflows
Approved Ministry of Health guidance
Approved maternal-health triage guidance
Approved ASHA training material

Ingestion pipeline:

Load document.
Extract text.
Remove headers and duplication.
Split into meaningful chunks.
Attach metadata.
Create embeddings.
Store in Milvus.
Test retrieval.

Chunk metadata:

source_id
document_title
organization
publication_date
section
page
language
approval_status
last_verified_at

Never ingest private patient information into the clinical knowledge base.

Use Neo4j for scheme and facility relationships.

Initial node types:

Scheme
EligibilityRule
DemographicCategory
HealthCondition
TreatmentPackage
RequiredDocument
State
District
Facility

Relationships:

AVAILABLE_IN
REQUIRES
COVERS
APPLIES_TO
EMPANELLED_AT
REQUIRES_DOCUMENT
HAS_ELIGIBILITY_RULE

Start with two or three demonstration schemes:

PM-JAY
Janani Suraksha Yojana
Maharashtra-specific relevant health scheme if verified

Return:

Potential relevance
Rule path
Missing information
Required documents
Official source
Last verification date

Do not claim eligibility when required information is missing.

Use Tavily only for changing information:

Empanelled hospital status
Current scheme notices
Current application links
Current official advisories

Restrict searches to approved official domains.

Return:

Result
Source URL
Source title
Publication/update date
Retrieval time

Never treat an unofficial search result as authoritative.

If verification fails, show:

“Current official information could not be verified. Please confirm through the official service.”

Use an adapter interface.

Responsibilities:

Automatic speech recognition
Translation
Text-to-speech

Do not call BHASHINI directly from the mobile frontend.

Flow:

Citizen audio
→ FastAPI
→ Swytchcode adapter
→ BHASHINI
→ Transcript
→ Clinical normalization
→ AI/safety processing
→ Verified text
→ BHASHINI TTS
→ Citizen audio

Implement mock BHASHINI mode:

Use predefined transcript for demo audio
Use browser/device TTS or recorded demo audio when external service is unavailable
Clearly record integration status internally

Use Swytchcode as the governed execution boundary where available.

Responsibilities:

Credential management
External API execution
Schema validation
Timeouts
Retries
Tool access policy
Response validation
Audit logs

If the integration is unavailable, use an adapter with a mock implementation.

Never hallucinate successful external API execution.

Create n8n workflow definitions for:

A. Urgent ASHA Alert

High-risk case
→ FastAPI webhook
→ n8n
→ Notify assigned ASHA
→ Record delivery result
→ Escalate operationally if unacknowledged

B. PHC Referral Notification

ASHA referral
→ FastAPI webhook
→ n8n
→ Notify PHC queue
→ Notify doctor
→ Record delivery

C. Follow-up Reminder

Doctor creates follow-up
→ n8n waits until due time
→ Notify ASHA/citizen
→ Record notification

D. Report Dispatch

Approved report created
→ Secure storage
→ Notify authorized recipient
→ Record audit event

E. Possible Cluster Alert

Aggregation threshold met
→ Create possible cluster event
→ Notify District Admin
→ Require human review

n8n performs automation, not clinical decisions.

Use ABDM sandbox only after consent.

Create an adapter for:

ABHA reference verification
Consent workflow
Care-context linking
Structured record demonstration
Facility/professional reference where available

If sandbox access is unavailable:

Implement a clearly labelled mock adapter
Do not claim production integration
Show “Sandbox simulation” in developer/admin view

PDF alone is not interoperability.

Store structured clinical data separately.

Before sending text to an external model, detect and mask:

Names
Phone numbers
Aadhaar numbers
ABHA numbers
Addresses
Bank details
Other unnecessary identifiers

Example:

Original:

“Sunita Devi, ABHA 12-3456-7890-1234, has blurred vision.”

Protected AI input:

“[PATIENT_01] has blurred vision.”

Keep the mapping inside the secure application boundary.

Send only the minimum required context.

Citizen mobile:

SQLite queue
Encrypted sensitive local data
Pending requests
Pending vitals
Pending consent events
Safe retry
Idempotency keys

ASHA portal:

IndexedDB queue
Visit drafts
Pending acknowledgements
Pending vital submissions
Referral drafts
Follow-up drafts

Every offline action contains:

Local action ID
Idempotency key
Entity ID
Operation
Payload
Created time
Retry count
Sync status

Sync states:

PENDING
SYNCING
SYNCHRONIZED
FAILED_RETRYABLE
CONFLICT

Do not silently overwrite conflicts.

Use record versioning.

Implement WebSocket or Server-Sent Events.

Events:

CASE_CREATED
ASHA_ASSIGNED
ASHA_ACKNOWLEDGED
VISIT_SCHEDULED
REFERRAL_CREATED
DOCTOR_ACKNOWLEDGED
CONSULTATION_COMPLETED
FOLLOW_UP_ASSIGNED
FOLLOW_UP_COMPLETED
REPORT_AVAILABLE
SYNC_COMPLETED

Example:

{
"event": "DOCTOR_ACKNOWLEDGED",
"case_id": "CASE-2026-001",
"actor_id": "DOC-007",
"facility_id": "PHC-09",
"timestamp": "2026-08-23T11:30:00Z"
}

Use polling fallback if real-time connection fails.

Notification channels may include:

In-app
Push
SMS
WhatsApp through authorized provider
Email for professional workflows

Do not expose sensitive details on lock screens.

Safe notification:

“A new urgent case has been assigned.”

Unsafe notification:

“Sunita Devi may have a pregnancy complication.”

Store:

Recipient
Channel
Template
Delivery status
Retry status
Related case
Created time

Generate:

ASHA field-visit summary
PHC referral
Doctor consultation summary
Prescription
Higher-facility referral
Follow-up summary
Scheme-document checklist

Reports must include:

Human-readable reference
Patient reference
Author
Facility
Date and time
Approval status
Signature status
“Not a final diagnosis” where appropriate
Audit reference

Generate structured JSON first.

Render PDF second.

Do not treat PDF as the primary clinical data format.

Implement:

Strong password hashing
Role-based authorization
Least-privilege access
Secure token storage
Session expiration
Input validation
Output encoding
CORS configuration
CSRF protection where relevant
Rate limiting
Audit logs
Secure file access
Signed download URLs where relevant
No secrets in source control
No sensitive data in application logs
No raw clinical data in analytics logs
Automatic portal lock after inactivity
Consent tracking
Record-access logging

Do not claim legal compliance merely because controls exist.

Document security assumptions and remaining production requirements.

Create deterministic seed data.

Users:

Citizen:
Sunita Devi

ASHA:
Sita Patel
ID: ASHA-012
Village: Kalyanpur

Doctor:
Dr Abhinav Sharma
ID: DOC-007
Facility: Kalyanpur PHC

Admin:
District Health Officer
ID: ADMIN-003
District: District 04

Demo case:

Case ID:
CASE-2026-001

Citizen:
Sunita Devi, age 28

Pregnancy:
Approximately seven months

Symptoms:

Blurred vision
Severe headache
Swelling in feet

Vitals:

BP 150/100
SpO₂ 97
Temperature 98.6°F

Initial status:
NEW

Priority:
URGENT

Assigned ASHA:
ASHA-012

Target facility:
PHC-09

Create additional routine and follow-up cases so dashboards do not look empty.

Add configuration:

INTEGRATION_MODE=mock

Provider-specific options:

BHASHINI_MODE=mock
LYZR_MODE=mock
GEMINI_MODE=mock
TAVILY_MODE=mock
ABDM_MODE=mock
SWYTCHCODE_MODE=mock
N8N_MODE=mock

Every adapter must implement the same interface in mock and live modes.

Mock behavior must be deterministic.

UI must not falsely show “live government verified” when mock mode is active.

In developer/admin diagnostics, show:

“Sandbox/Mock integration”

Keep citizen-facing wording simple.

Backend tests:

Authentication
Role authorization
Case state transitions
ASHA assignment
Referral creation
Doctor acknowledgement
Consultation completion
Follow-up creation
Safety rules
PII masking
Idempotent sync
Admin anonymization
Integration adapter failures

Frontend tests:

Protected routes
Dashboard rendering
Loading state
Empty state
Error state
Offline state
Form validation
Urgent-case acknowledgement
Field-visit wizard
Referral submission
Doctor consultation
Follow-up updates
Responsive navigation
Accessibility checks

End-to-end test:

Citizen creates case
→ ASHA acknowledges
→ ASHA refers
→ Doctor acknowledges
→ Doctor completes consultation
→ ASHA receives follow-up
→ Admin aggregate updates

PHASE 0 – FOUNDATION

Inspect repository
Finalize monorepo
Add shared design tokens
Add shared domain types
Add linting and formatting
Add environment configuration
Add Docker Compose
Add documentation

PHASE 1 – SHARED BACKEND

PostgreSQL
SQLAlchemy models
Alembic migrations
Authentication
Role authorization
Seed data
OpenAPI
Audit events

PHASE 2 – PORTAL SHELL

Common login
Protected routes
ASHA layout
Doctor layout
Admin layout
Shared components
Mock API service

PHASE 3 – CORE VERTICAL SLICE

Citizen creates case
ASHA dashboard
ASHA acknowledgement
Field visit
Vitals
PHC referral
Doctor queue
Doctor acknowledgement
Consultation
Follow-up
Admin aggregate

PHASE 4 – OFFLINE

Citizen SQLite
ASHA IndexedDB
Sync queue
Idempotency
Conflict handling
Connectivity UI

PHASE 5 – AI AND RETRIEVAL

PII masking
Safety rules
Lyzr adapters
Milvus ingestion
Neo4j scheme graph
Verification Agent
Mock/live modes

PHASE 6 – EXTERNAL INTEGRATIONS

BHASHINI
Tavily
Swytchcode
n8n
ABDM sandbox
Integration status and retry

PHASE 7 – REPORTING AND ANALYTICS

Clinical reports
Admin aggregates
Cluster alert demonstration
Scheme analytics
Facility metrics

PHASE 8 – QUALITY

Tests
Accessibility
Performance
Security review
Error handling
Demo reset
Production builds
Documentation

Do not begin with external APIs.

First make the complete core vertical slice work with deterministic mock providers.

Development:

Use Docker Compose for:

PostgreSQL
Backend
Healthcare portal
Neo4j
Milvus
n8n where feasible

Citizen mobile runs through Expo during development.

Production-oriented deployment:

Citizen app: Android APK
Healthcare portal: static frontend hosting
FastAPI: container hosting
PostgreSQL: managed database
Neo4j: managed or controlled deployment
Milvus: controlled deployment
Documents: private object storage
n8n: secured automation instance

Use HTTPS.

Configure environment-specific URLs.

Never point a real phone to localhost.

For local Wi-Fi testing, use the development computer’s LAN IP.

For remote demo, use a securely deployed backend URL.

Create a complete README containing:

Product overview
Architecture
Screenshots
Technology stack
Repository structure
Environment variables
Local setup
Docker setup
Database migration
Seed data
Running citizen app
Running portal
Running backend
Mock integration mode
Test commands
Demo credentials
Demo flow
Safety limitations
Known limitations
Production requirements

Create:

docs/architecture.md
docs/api-contract.md
docs/database-schema.md
docs/safety.md
docs/demo-guide.md
docs/team-workflow.md

Organize features so four members can work safely.

Member 1:

Citizen mobile application

Member 2:

ASHA Portal

Member 3:

Doctor Portal

Member 4:

Admin Portal and shared integration support

Shared files require review.

Branches:

feature/citizen-app
feature/asha-portal
feature/doctor-portal
feature/admin-portal
feature/backend-core

Do not allow generated code to modify unrelated feature folders.

After each phase, run the project’s equivalent of:

Format
Lint
Type-check
Unit tests
Backend tests
Production frontend build
Backend startup check
Database migration check

Do not claim success if a command was not run.

Report:

Command
Result
Remaining warning
Remaining limitation

The project is ready for the hackathon demo when:

All four roles can log in.
Backend determines role.
Citizen can create a case.
Urgent rule creates an ASHA task.
ASHA can acknowledge.
Citizen sees acknowledgement.
ASHA can record a visit and vitals.
ASHA can refer to PHC.
Doctor receives the referral.
Doctor can acknowledge it.
ASHA and citizen receive the doctor update.
Doctor can record consultation.
Doctor can create follow-up.
ASHA receives follow-up.
Admin receives anonymized metrics.
Offline drafts are preserved.
External APIs can be replaced by deterministic mocks.
No role can access unauthorized routes or records.
AI does not issue diagnoses or prescriptions.
The complete demo can be reset and repeated reliably.

For this session:

Inspect the repository.
Return the architecture and file-impact plan.
Do not destroy existing work.
Create or correct shared domain types.
Create or correct the FastAPI foundation.
Create common authentication and role guards.
Create the shared portal layouts.
Implement deterministic seed data.
Implement the core end-to-end vertical slice.
Verify the vertical slice.
Only then add secondary screens.
Only then add external AI and government integrations.

Do not generate placeholder pages that appear complete but have no working data connection.

Do not create fake buttons.

Every primary action in the demonstration must perform a real state change through the shared backend.

Lead with a working integrated flow, then enhance it.

At the end of each implementation cycle, report:

What was implemented
Architecture decisions
Files created
Files modified
Database migrations
API endpoints added
Screens completed
Tests executed
Build results
Mocked integrations
Live integrations
Known limitations
Security concerns
Recommended next task