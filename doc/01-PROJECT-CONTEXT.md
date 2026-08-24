# Aarogya Sahayak - Project Context

## 1. Purpose

Aarogya Sahayak is a voice-first, multilingual rural-health assistance platform for India. It connects rural citizens, ASHA workers, PHC doctors, and authorized district health officers through one controlled case workflow.

It is not a diagnostic chatbot and must never be presented as a replacement for a doctor. Its purpose is to convert an accessible citizen interaction into a safe, structured, human-supervised healthcare action.

The core journey is:

```text
Citizen reports a concern
-> deterministic safety check
-> AI-assisted, source-grounded triage
-> ASHA verification and field visit
-> PHC doctor consultation
-> follow-up
-> anonymized district analytics
```

## 2. Problem

Rural citizens may face several barriers simultaneously:

- low literacy or limited confidence with written forms;
- regional-language and dialect differences;
- unstable 2G/3G connectivity;
- long travel distances to healthcare facilities;
- limited awareness of health schemes;
- shared family phones and privacy concerns;
- overloaded ASHA workers using paper registers;
- PHC doctors receiving incomplete or unstructured histories;
- administrators receiving delayed, fragmented aggregate information.

Existing government systems provide important infrastructure, directories, telemedicine, and health-record exchange, but the project targets the missing workflow between a citizen's spoken concern and coordinated human action.

## 3. Product boundaries

### The system may

- collect citizen symptoms and structured vital signs;
- detect configured emergency warning conditions;
- provide short, non-prescriptive health information;
- classify workflow urgency as routine, review soon, or urgent;
- suggest potentially relevant health schemes;
- create ASHA tasks and PHC referrals;
- assist doctors with structured documentation;
- create follow-up tasks;
- produce anonymized administrative aggregates.

### The system must not

- make a final diagnosis without a doctor;
- independently prescribe medicine or dosage;
- cancel a deterministic emergency warning;
- claim confirmed scheme eligibility without official verification;
- expose chain-of-thought or internal agent reasoning;
- send unnecessary personally identifiable information to an LLM;
- store patient records in the clinical knowledge vector database;
- claim a mock or sandbox API is a production integration.

## 4. Users and interfaces

### Rural Citizen

Uses a separate React Native Android application with a large microphone, regional-language audio, offline structured safety checks, saved requests, health updates, nearby care, and scheme guidance.

### ASHA Worker

Uses a responsive React PWA at `/asha`. The ASHA worker sees assigned priorities, contacts citizens, conducts consented field visits, confirms extracted information, records vitals, creates referrals, and completes follow-ups.

### PHC Doctor

Uses the same responsive healthcare portal at `/doctor`. The doctor reviews referrals and ASHA-confirmed data, conducts consultations, confirms diagnoses, issues prescriptions, orders tests, creates care plans, and assigns follow-ups.

### District Health Officer / Admin

Uses the same portal at `/admin`. The administrator sees authorized, anonymized or aggregated district metrics, possible symptom clusters, referral patterns, scheme utilization, facility load, and workforce-support indicators.

## 5. Applications

```text
apps/citizen-mobile       React Native + Expo
apps/healthcare-portal   React + Vite responsive PWA
backend                  FastAPI shared backend
```

The healthcare portal contains role-protected sections for ASHA, Doctor, and Admin. It is one application, not three unrelated websites.

## 6. Core differentiators

1. Voice-first citizen access through BHASHINI.
2. Offline bounded triage using deterministic rules and TensorFlow Lite.
3. Human-in-the-loop escalation through ASHA and doctors.
4. Dual retrieval: Milvus for clinical text and Neo4j for scheme relationships.
5. A verifier agent that blocks unsupported or unsafe output.
6. One case ID connecting the citizen, ASHA, doctor, and administrative aggregate.
7. Consent, PII minimization, audit logs, and role-based access.

## 7. Fixed technology choices

- Citizen: React Native, Expo, TypeScript, Expo SQLite, SecureStore.
- Portal: React, Vite, TypeScript, React Router, TanStack Query, React Hook Form, Zod.
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic.
- Operational DB: PostgreSQL.
- Clinical RAG: Milvus.
- Scheme graph: Neo4j.
- Offline model: TensorFlow Lite.
- Agent orchestration: Lyzr.
- LLM: Gemini through backend/Lyzr configuration.
- Voice: BHASHINI ASR, translation, and TTS.
- Current scheme verification: Tavily restricted to approved domains.
- Automation: n8n.
- Government integration: ABDM sandbox only until production approval.
- Reports: Jinja2 HTML templates rendered to PDF with WeasyPrint.

Do not replace these technologies without a documented architecture decision approved by the team.

## 8. Canonical demo scenario

Sunita Devi, approximately seven months pregnant, reports blurred vision, severe headache, and swollen feet. An ASHA worker records BP 150/100. The system must:

1. create an urgent case;
2. provide calm, non-diagnostic guidance;
3. notify the assigned ASHA worker;
4. allow the ASHA worker to acknowledge and verify the case;
5. record the field visit and vitals;
6. refer the case to the configured PHC;
7. let the doctor acknowledge and complete a consultation;
8. create an ASHA follow-up;
9. show a citizen-friendly status update;
10. update an anonymized district metric.

This scenario is the first end-to-end acceptance test.

## 9. Success criteria

- The complete demo runs from a clean setup using documented commands.
- Each role sees only authorized data and actions.
- The citizen flow remains usable during a network interruption.
- Emergency rules work without an LLM.
- AI failures produce a safe human-escalation response.
- An ASHA referral appears in the correct doctor's queue.
- A doctor follow-up appears in the correct ASHA queue.
- Admin analytics do not expose patient identity.
- All core endpoints are documented in OpenAPI and tested.

