# AAROGYA SAHAYAK — COMPLETE DYNAMIC CITIZEN APP IMPLEMENTATION SPRINT

Implement the complete Citizen App in the existing Aarogya Sahayak monorepo.

The result must be a real, connected, voice-first rural healthcare application—not a static chatbot UI. Every screen, metric, button, status and notification must use FastAPI and PostgreSQL and correctly affect the ASHA, Doctor, Citizen and Admin modules.

Use the attached 10-screen Citizen App image as the visual and UX reference.

Existing architecture to preserve:

- Citizen mobile app: apps/citizen-mobile
- Staff portal: apps/healthcare-portal
- Backend: FastAPI
- Database: PostgreSQL with Alembic
- Shared API client
- Deterministic clinical safety engine
- ASHA and Doctor workflows
- WebSocket with polling fallback
- Gemini structured-language layer
- Sarvam/BHASHINI voice adapters with manual fallback
- Structured scheme eligibility engine
- Verified facility database
- Existing authentication, RBAC, audit, timeline and idempotency

Do not break any existing ASHA, Doctor, Admin, referral, consultation, investigation, prescription, follow-up, scheme or offline workflow.

Before coding:

1. Audit current Citizen frontend, backend routes, schemas, models, API client, authentication and seeded Citizen data.
2. Read relevant docs and existing status/state-machine definitions.
3. Identify reusable components and API contracts.
4. Create `task.md` with a complete checklist.
5. Mark a task complete only after testing it.
6. Never claim success based only on compilation.

---

# 1. PRODUCT PRINCIPLE

The Citizen App must follow:

Citizen speaks or types
→ system understands the need
→ citizen confirms the understanding
→ deterministic safety rules run
→ system gives clear actionable choices
→ request reaches Doctor, ASHA, facility or scheme engine
→ progress returns to the Citizen App.

The AI is an access and coordination assistant. It must not diagnose or prescribe.

Support two connected care pathways:

1. Citizen → ASHA → PHC Doctor
2. Citizen → PHC Doctor directly → ASHA support when required

The citizen must never be forced to go through ASHA before requesting an immediate Doctor consultation.

---

# 2. CITIZEN APP NAVIGATION

Implement mobile-first bottom navigation:

1. Home
2. My Care
3. Medicines
4. Benefits
5. Profile

Emergency Help must always remain accessible from the Home and active-concern screens.

Routes:

- `/citizen/home`
- `/citizen/assistant`
- `/citizen/assistant/:sessionId`
- `/citizen/care`
- `/citizen/cases/:caseId`
- `/citizen/doctor`
- `/citizen/doctor/requests/:requestId`
- `/citizen/consultations/:consultationId`
- `/citizen/emergency`
- `/citizen/asha`
- `/citizen/appointments`
- `/citizen/appointments/:appointmentId`
- `/citizen/medicines`
- `/citizen/prescriptions/:prescriptionId`
- `/citizen/investigations`
- `/citizen/investigations/:investigationId`
- `/citizen/followups`
- `/citizen/followups/:followUpId`
- `/citizen/schemes`
- `/citizen/schemes/:schemeId`
- `/citizen/scheme-screenings/:screeningId`
- `/citizen/facilities`
- `/citizen/facilities/:facilityId`
- `/citizen/household`
- `/citizen/household/:memberId`
- `/citizen/notifications`
- `/citizen/profile`

Protect routes with Citizen RBAC and household authorization.

---

# 3. FIRST-USE LANGUAGE SCREEN

Create a first-use language selection screen matching the visual reference.

Show:

- Aarogya Sahayak logo
- “आपली भाषा निवडा / Choose your language”
- Marathi
- Hindi
- English
- Read-aloud preview
- Accessibility settings
- Continue

Behaviour:

- Save selected language in Citizen profile and device preferences.
- Load all critical safety messages from approved translated templates.
- Allow changing language later.
- Do not depend on Gemini for essential navigation or emergency translations.
- Use correct Unicode fonts and test Marathi/Hindi rendering.

---

# 4. CITIZEN HOME SCREEN

Create a simple, rural-friendly voice-first home screen.

Header:

- Citizen’s first name
- Selected language
- Notification badge
- Read-aloud toggle
- Connectivity state
- Profile shortcut

Main section:

- Large 88–112 px microphone
- “बोलून सांगा / Speak”
- “टाइप करा / Type”

Quick actions:

- Speak to Doctor Now
- Emergency Help
- Call/Request ASHA
- Find Health Centre
- Check Government Scheme
- My Medicines and Tests

Dynamic active-care card:

- Current concern
- Current understandable status
- Responsible person
- Next action
- Appointment/follow-up
- Last update

Never show internal enum text such as `PENDING_DOCTOR_REVIEW`.

Translate statuses:

- `NEW` → “Your concern was received”
- `ASHA_ACKNOWLEDGED` → “Your ASHA worker accepted the request”
- `REFERRED_TO_PHC` → “Your information was sent to the PHC”
- `DOCTOR_ACKNOWLEDGED` → “A Doctor is reviewing your case”
- `FOLLOW_UP_REQUIRED` → “A follow-up visit is required”
- `COMPLETED` → “This care episode is completed”

All Home data must come from one Citizen home-summary API, not hardcoded counters.

---

# 5. CHATBOT TECHNICAL ARCHITECTURE

Do not implement an unrestricted ChatGPT-style chatbot.

Build a guided `Citizen Need & Intent Orchestrator`.

Flow:

Voice/text/photo
→ speech-to-text if needed
→ language detection
→ transcript confirmation
→ structured AI extraction
→ Pydantic validation
→ Citizen Need Profile
→ deterministic safety rules
→ approved question selector
→ citizen confirmation
→ action router
→ real service request.

Gemini responsibilities:

- Language understanding
- Intent classification
- Entity extraction
- Marathi/Hindi/English normalization
- Detect missing fields
- Produce short explanations from verified facts
- Translate non-critical responses

Gemini must not:

- Make final emergency classification
- Diagnose
- Prescribe
- Invent facilities
- Confirm scheme eligibility
- Assign staff
- Change workflow states
- Claim an action succeeded before API confirmation

Use Gemini 2.5 Flash through a backend provider gateway with:

- Structured JSON output
- Pydantic validation
- Low temperature
- Short prompts
- Maximum output tokens
- Timeout
- Maximum two retries
- Exponential backoff
- Rate limiting
- Circuit breaker
- Usage logging
- PII masking
- Prompt versioning

Do not expose API keys in React/Vite.

Target 1–3 Gemini calls per Citizen Need session.

---

# 6. CHAT SESSION, NEED, CASE AND REQUEST SEPARATION

Implement separate entities:

1. CitizenProfile
2. HouseholdMember
3. CitizenChatSession
4. CitizenChatMessage
5. CitizenNeed
6. NeedIntent
7. NeedSymptom
8. SafetyRuleResult
9. Case
10. ServiceRequest
11. TimelineEvent
12. AuditLog

Important invariant:

Chat Session ≠ Citizen Need ≠ Clinical Case ≠ Service Request.

A chat session produces a confirmed Citizen Need.

Create a clinical Case only when:

- A health concern is confirmed
- Doctor consultation is requested
- Clinical ASHA assistance is requested
- Worsening symptoms are reported
- Medicine problem/side effect is reported
- Referral or follow-up is required

Do not create a clinical Case for:

- General facility search
- Generic scheme information
- Document guidance
- Out-of-scope questions
- Abandoned or unconfirmed transcripts

---

# 7. CHAT SESSION DATA MODEL

Create/extend:

`CitizenChatSession`

- id
- session_reference
- citizen_id
- person_affected_id
- preferred_language
- detected_language
- channel: VOICE/TEXT/MIXED
- current_state
- primary_intent
- status
- started_at
- last_activity_at
- expires_at
- completed_at
- linked_need_id
- linked_case_id
- consent_status
- device_id
- offline_created
- sync_status

States:

- STARTED
- LISTENING
- TRANSCRIBING
- AWAITING_TRANSCRIPT_CONFIRMATION
- UNDERSTANDING
- COLLECTING_INFORMATION
- SAFETY_ACTION_REQUIRED
- AWAITING_ACTION_SELECTION
- ROUTING
- REQUEST_CREATED
- COMPLETED
- CANCELLED
- EXPIRED

`CitizenChatMessage`

- id
- session_id
- sequence_number
- sender
- input_type
- original_text
- confirmed_text
- translated_text
- language
- message_type
- structured_payload
- confirmation_status
- model_provider
- model_name
- prompt_version
- created_at

For audio:

- temporary_audio_reference
- audio_consent_at
- transcription_provider
- transcription_confidence
- audio_deleted_at

Raw audio must be temporary and deleted according to the retention policy after confirmed transcription unless explicitly required and consented.

---

# 8. CITIZEN NEED PROFILE

Create a structured `CitizenNeed`:

- need_reference
- session_id
- citizen_id
- person_affected_id
- primary_intent
- secondary_intents
- requested_service
- detected_language
- confirmed_summary
- location
- special_context
- urgency
- safety_result_id
- status
- citizen_confirmed_at
- created_at

Canonical intents:

- HEALTH_CONCERN
- DOCTOR_CONSULTATION
- ASHA_ASSISTANCE
- EMERGENCY_HELP
- FACILITY_SEARCH
- SCHEME_ELIGIBILITY
- SCHEME_APPLICATION_HELP
- DOCUMENT_SERVICE_HELP
- MEDICINE_INFORMATION
- MEDICINE_HELP
- INVESTIGATION_HELP
- VACCINATION_HELP
- APPOINTMENT_HELP
- CARE_PLAN_HELP
- OUT_OF_SCOPE

Support multiple simultaneous intents.

Example:

“Mother has chest pain, I want a Doctor and need the nearest hospital.”

Primary:

- DOCTOR_CONSULTATION

Secondary:

- HEALTH_CONCERN
- FACILITY_SEARCH

Do not force mutually exclusive radio selection.

Special contexts:

- MATERNAL
- POSTNATAL
- NEWBORN
- CHILD
- ELDERLY
- NCD
- RESPIRATORY
- MENTAL_HEALTH
- GENERAL

---

# 9. CHAT UI AND RESPONSE BEHAVIOUR

The assistant screen must show:

- Session/person affected
- Current language
- Conversation status
- Start new concern
- Large voice input
- Type option
- Read response aloud
- One question at a time
- Edit previous response
- Connectivity/sync status

Required interaction:

1. Citizen speaks.
2. Show waveform.
3. Transcribe.
4. Show exact transcript.
5. Citizen selects Confirm, Edit or Speak Again.
6. Show “What I understood.”
7. Citizen confirms/corrects.
8. Ask only required missing questions.
9. Safety engine runs.
10. Show short explanation and actionable buttons.

Response contract:

```json
{
  "session_id": "SESSION-001",
  "state": "AWAITING_ACTION_SELECTION",
  "language": "mr-IN",
  "message": "Short citizen-safe message",
  "read_aloud_text": "Same safe message",
  "understanding": {
    "person": "Mother",
    "symptoms": ["Chest pain", "Breathing difficulty"],
    "duration": "3 days",
    "intent": "Speak to Doctor"
  },
  "safety": {
    "level": "POSSIBLE_EMERGENCY",
    "rule_ids": ["CHEST-BREATH-01"]
  },
  "actions": [
    {
      "type": "EMERGENCY_HELP",
      "label": "Get Emergency Help",
      "style": "DANGER"
    },
    {
      "type": "SPEAK_TO_DOCTOR",
      "label": "Speak to Doctor Now",
      "style": "PRIMARY"
    },
    {
      "type": "FIND_FACILITY",
      "label": "Find Nearest Hospital",
      "style": "SECONDARY"
    }
  ]
}