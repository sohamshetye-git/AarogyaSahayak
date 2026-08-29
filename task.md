# Find Health Centre Feature Rebuild & Integration Checklist

## 1. Audit & Component Status Matrix
- [x] Audit current state of codebase components:
  - Citizen Facility Screen (`apps/citizen-mobile/src/components/FacilitiesScreen.tsx`): `STATIC_OR_MOCK` (Hardcoded cards, static dummy array, fake distance, alert-based directions)
  - Citizen Chatbot Facility Intent (`apps/citizen-mobile/src/components/AssistantScreen.tsx`): `MISSING` (No structured blocks for location request, facility search progress, typed facility cards)
  - Facility & FacilityService Models (`backend/app/models/`): `PARTIAL` (Only basic `Facility` table with 7 columns; missing capabilities, services, hours, schemes, search log, assistance & appointments)
  - Facility Seed Data (`backend/app/`): `STATIC_OR_MOCK` (No dedicated idempotent seed; only ad-hoc dictionaries in `citizen_service.py`)
  - Backend Endpoints (`backend/app/routers/citizen.py`): `PARTIAL` (Only trivial `/api/citizen/facilities` without ranking, capability filter, suitability reasons or mutations)
  - API Client Methods (`packages/api-client/index.ts`): `PARTIAL` (Missing typed methods for search, detail, hours, schemes, call events, ASHA assistance, appointment requests, referrals)
  - Geolocation Handling (`apps/citizen-mobile`): `MISSING` (No explicit consent, no GPS capture once + locality confirmation, no manual fallback/voice input)
  - Map / Directions Handling: `STATIC_OR_MOCK` (Uses `alert()`; missing native Google Maps url launcher, text directions fallback, copy address, low-data view)
  - Deterministic Safety Engine Integration (`backend/app/safety/emergency_rules.py`): `IMPLEMENTED_BUT_UNTESTED` (Works for triage, not wired into facility ranking before search)
  - ASHA Facility / Transport Tasks (`apps/healthcare-portal`, `backend`): `STATIC_OR_MOCK` (Missing dedicated `Facility & Transport Assistance` task workflow & stage transitions)
  - Doctor Referral Facility Fields (`backend/app/models/__init__.py`, `DoctorConsultationScreen.tsx`): `PARTIAL` (Referral model has `to_facility_name` but missing structured target facility links & directions in Citizen My Care)
  - Scheme Empanelment Records: `PARTIAL` (Only static mock array in citizen router; missing relational `FacilitySchemeEmpanelment` linking)
  - Offline Storage and Synchronization (`citizen-mobile/src/services/`): `PARTIAL` (No offline facility cache, offline directions or queued idempotent actions)
  - WebSocket / Domain Events (`backend/app/routers/websocket.py`): `PARTIAL` (Missing facility search/selection/assistance/appointment domain events)
  - Mobile Routing and Multilingual i18n (`citizen-mobile`): `PARTIAL` (Needs dedicated subroutes `/facilities`, `/facilities/search`, `/facilities/:facilityId`, etc., and Marathi/Hindi/English translations)

---

## 2. Database Models & Schema Extensions
- [x] Implement robust facility models in `backend/app/models/facilities.py` (and export in `backend/app/models/__init__.py`):
  - `Facility`: id, public_reference, official_name, localized_name, facility_type, ownership, authority, state, district, block, village, pincode, address, landmark, latitude, longitude, phone, email, active, verification_status, source_id, last_verified_at
  - `FacilityService`: facility_id, service_code, localized_service_name, service_level, availability_status, emergency_capability, appointment_requirement, source, last_verified
  - `FacilityHours`: day, opening_time, closing_time, is_24x7_emergency, verification_status, source, last_verified
  - `FacilitySchemeEmpanelment`: facility_id, scheme_id/code, empanelment_reference, effective_from, effective_until, verification_status, official_source
  - `FacilitySearch`: citizen_id, household_member_id, requested_service, urgency, location_method, coordinates_or_locality, consent_reference, filters, result_facility_ids, selected_facility_id, created_at
  - `FacilityAssistanceRequest`: citizen_id, household_member_id, active_need_or_case_id, selected_facility_id, assistance_type, transport_needed, assigned_asha_id, status, due_at, outcome
  - `FacilityAppointmentRequest`: citizen_id, household_member_id, facility_id, service_code, requested_slot, status, facility_confirmation_source, appointment_reference, created_at, updated_at
- [x] Create Alembic migration / SQLite / PostgreSQL compatibility layer for facility models.

---

## 3. Verified Data & Idempotent Seeding
- [x] Implement `backend/app/seeds/seed_facilities.py`:
  - 10+ realistic synthetic demo facilities with distinct capabilities:
    1. Ganeshpur Sub-Centre (Village sub-centre, maternal ANC, no emergency)
    2. Kalyanpur Primary Health Centre (PHC, 24x7 emergency, OPD, labor room, PM-JAY desk)
    3. Kalyanpur Community Health Centre (CHC, surgery, pediatric, 24x7)
    4. District Hospital District 04 (Tertiary care, trauma, ICU, MJPJAY/PM-JAY, blood bank)
    5. LifeCare Emergency & Trauma Hospital (Private empanelled, 24x7 cardiac & ICU)
    6. Mother & Child Maternity Hospital (Specialized obstetrics, NICU)
    7. Kalyanpur Child Immunization & Nutrition Centre (Routine vaccination, pediatric)
    8. Central Diagnostic & Pathology Lab (X-ray, blood tests, ultrasound)
    9. District TB & Chest Diseases Centre (Nikshay TB DOTS, respiratory care)
    10. Kalyanpur CSC & Ayushman Scheme Help Desk (Empanelment help, e-KYC)
    11. Jan Aushadhi Kendra Kalyanpur (Essential medicines & pharmacy)
  - Ensure script is 100% idempotent (executing twice produces exactly 0 duplicate records).

---

## 4. Search and Ranking Engine (Capability & Suitability First)
- [x] Create `backend/app/services/facility_service.py`:
  - Haversine backend distance calculation from genuine GPS or village coordinates.
  - Multi-tier ranking algorithm prioritizing clinical capability over raw distance.
  - Generate explicit `suitability_reason` explaining why the facility is recommended over nearer unsuitable ones.

---

## 5. Backend FastAPI Endpoints
- [x] Implement endpoints in `backend/app/routers/citizen.py`:
  - `GET /api/citizen/facilities/search` (Search & rank facilities by capability, urgency, location)
  - `POST /api/citizen/facilities/searches` (Log search audit record with consent)
  - `GET /api/citizen/facilities/{facilityId}` (Full facility overview)
  - `GET /api/citizen/facilities/{facilityId}/services` (Capability & service status matrix)
  - `GET /api/citizen/facilities/{facilityId}/hours` (Opening hours & emergency status)
  - `GET /api/citizen/facilities/{facilityId}/schemes` (Verified empanelments)
  - `POST /api/citizen/facilities/{facilityId}/select` (Confirm facility selection)
  - `POST /api/citizen/facilities/{facilityId}/call-events` (Log `CALL_INITIATED`)
  - `POST /api/citizen/facilities/{facilityId}/asha-assistance` (Create ASHA facility/transport task)
  - `POST /api/citizen/facilities/{facilityId}/appointment-requests` (Create appointment request)
  - `GET /api/citizen/facility-referrals` (Referrals to facilities)
  - `GET /api/citizen/facility-assistance` (Active assistance tasks)
  - `GET /api/citizen/facility-appointments` (Citizen appointments)
- [x] Publish domain events on WebSocket (`FACILITY_SEARCHED`, `FACILITY_SELECTED`, `FACILITY_ASSISTANCE_REQUESTED`, `FACILITY_APPOINTMENT_REQUESTED`).

---

## 6. Shared API Client & TypeScript Types
- [x] Update `packages/api-client/index.ts`:
  - Add all typed DTOs and methods: `searchCitizenFacilities`, `getCitizenFacilityDetail`, `getCitizenFacilityServices`, `getCitizenFacilityHours`, `getCitizenFacilitySchemes`, `selectCitizenFacility`, `logFacilityCallEvent`, `requestFacilityAshaAssistance`, `requestFacilityAppointment`, `getCitizenFacilityReferrals`, `getCitizenFacilityAssistance`, `getCitizenFacilityAppointments`.

---

## 7. Citizen Mobile App "Find Health Centre" Rebuild
- [x] Rebuild `apps/citizen-mobile/src/components/FacilitiesScreen.tsx` with full rural UX:
  - Multilingual support: Marathi (`mr-IN`), Hindi (`hi-IN`), English (`en-IN`).
  - Sub-views/Routing:
    - `/facilities` (Entry: Service category cards, Who needs care selector, Location selector, Emergency 108)
    - `/facilities/search` (Search Results list, Capability-first badge, Why Recommended, Filter chips, List/Map toggle, Low-Data mode)
    - `/facilities/:facilityId` (Detail: Overview, Services table, Hours disclaimer, Directions, ASHA/Appointment actions)
    - `/facilities/assistance` & `/facilities/appointments` (Live status trackers)

---

## 8. Chatbot, Doctor & ASHA Workflows Integration
- [x] Chatbot facility query intent handling in `AssistantScreen.tsx` (`FACILITY_RESULTS`, `SAFETY_ALERT`, `ACTION_CHOICES`).
- [x] Doctor Referral integration in `MyCareScreen.tsx` with facility directions and quick call.

---

## 9. Verification & Automated Tests
- [x] Unit test suite in `backend/tests/test_facility_service.py` (13 test cases passed).
- [x] Frontend TypeScript compilation & Vite production bundle (`apps/citizen-mobile` build passing).

    - `/facilities/:facilityId/directions` (Turn-by-turn text directions, landmark guide, Native Maps launcher, copy/share)
    - `/facilities/assistance` (ASHA assistance tracker & transport status)
    - `/facilities/appointments` (Appointment lifecycle tracker)
    - `/facilities/referrals` (Doctor referral target facility viewer)
  - Explicit Location workflow: Permission explanation, single capture, village/pincode manual fallback, saved locations.
  - Read-Aloud (TTS) and Voice search on all screens.
  - Offline caching with timestamp: `"These details were last updated online at [time]. Please call before travelling."`

---

## 8. Chatbot, ASHA & Doctor Integration
- [ ] Chatbot integration in `apps/citizen-mobile/src/components/AssistantScreen.tsx`:
  - Typed blocks for `LOCATION_REQUEST`, `FACILITY_SEARCH_PROGRESS`, `FACILITY_RESULTS`, `SAFETY_ALERT`, `ACTION_CHOICES`, `FACILITY_SELECTION_CONFIRMATION`.
  - Handle facility queries (Nearest PHC, Child vaccination, Hospital for delivery, Father chest pain).
- [ ] ASHA Portal in `apps/healthcare-portal`:
  - Display `Facility & Transport Assistance` tasks in ASHA dashboard & tasks list.
  - ASHA actions: Call Citizen, Confirm location, Record transport plan, Confirm departure/arrival, Complete assistance.
- [ ] Doctor Referrals:
  - Doctor referral destination linked to verified facility with directions & guidance in Citizen My Care.

---

## 9. Automated Testing & Verification
- [ ] Backend pytest suite:
  - 19 automated test cases covering GPS, village/pincode, distance, capability ranking, emergency override, maternity ranking, child vaccination filter, unverified hours warning, scheme empanelment, RBAC, consent, ASHA assistance creation, appointment state lifecycle, idempotency.
- [ ] Playwright E2E tests:
  - Routine PHC search (GPS denied -> manual pincode -> PHC results -> detail -> directions)
  - Emergency search (Chest pain -> Emergency 108 banner -> Emergency-capable ranking -> ASHA notify)
  - Maternal search (Pregnancy -> Maternity facility -> Doctor referral target -> ASHA transport task)
  - Child vaccination (Child member -> Vaccination filter -> Appointment request -> My Care)
  - Scheme empanelment (PM-JAY/MJPJAY -> Verified filter -> Official disclaimer)
- [ ] Responsive UI verification (360px, 390px, 768px, 1440px) and production build validation.
