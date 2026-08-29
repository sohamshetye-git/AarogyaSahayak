# Doctor Portal Interactive Element & Routing Action Matrix

This action matrix documents all interactive routes, buttons, identifiers, APIs, database effects, and cross-role updates across the Aarogya Sahayak PHC Doctor Portal.

---

## 1. Canonical Identifier & Type Rules

The application strictly separates canonical entity IDs:
- **`citizenId`** (`CIT-...` / UUID): Unique identifier for the Citizen Profile.
- **`caseId`** (`CASE-...` / UUID): Unique clinical episode / health issue identifier.
- **`referralId`** (`REF-...` / UUID): Specific referral record between ASHA and PHC / CHC.
- **`consultationId`** (`CON-...` / UUID): Clinical doctor consultation instance.
- **`followUpId`** (`FU-...` / UUID): Assigned post-consultation / ANC / NCD follow-up task.
- **`investigationId`** (`INV-...` / UUID): Laboratory order record.
- **`prescriptionId`** (`RX-...` / UUID): Doctor signed prescription.
- **`alertId`** (`ALT-...` / UUID): Epidemiological / ASHA field escalation alert.

---

## 2. Canonical Typed Routes (`doctorPaths`)

| Route Builder | Canonical Path | Description |
|---|---|---|
| `doctorPaths.dashboard()` | `/doctor/dashboard` | Main PHC Doctor Dashboard |
| `doctorPaths.referrals(filters?)` | `/doctor/referrals` | PHC Referral Queue with filter queries |
| `doctorPaths.referral(referralId)` | `/doctor/referrals/:referralId` | Individual Referral Overview |
| `doctorPaths.consultations(filters?)` | `/doctor/consultations` | Active Consultation Workspace Landing |
| `doctorPaths.consultation(consultationId)` | `/doctor/consultations/:consultationId` | 5-Step Patient-Specific Clinical Consultation |
| `doctorPaths.patient(citizenId)` | `/doctor/patients/:citizenId` | Comprehensive Citizen Medical Record |
| `doctorPaths.timeline(caseId)` | `/doctor/cases/:caseId/timeline` | Deduplicated Case Event Timeline |
| `doctorPaths.followUps(filters?)` | `/doctor/followups` | ASHA Follow-up & Escalation Management |
| `doctorPaths.followUp(followUpId)` | `/doctor/followups/:followUpId` | Detailed Follow-up Review Screen |
| `doctorPaths.investigations(filters?)` | `/doctor/investigations` | Lab Orders & Diagnostic Reports |
| `doctorPaths.investigation(investigationId)` | `/doctor/investigations/:investigationId` | Single Lab Order & Results |
| `doctorPaths.prescriptions(filters?)` | `/doctor/prescriptions` | Doctor Prescriptions Register |
| `doctorPaths.prescription(prescriptionId)` | `/doctor/prescriptions/:prescriptionId` | View Signed Prescription Detail |
| `doctorPaths.alerts(filters?)` | `/doctor/alerts` | ASHA Field Escalations & Alerts |
| `doctorPaths.alert(alertId)` | `/doctor/alerts/:alertId` | Single Alert Review |
| `doctorPaths.systemStatus()` | `/doctor/system-status` | System & Integration Connectivity Health |

---

## 3. Screen-by-Screen Interactive Action Matrix

| Screen / Component | Interactive Element | Required Current State | Identifier Used | API Endpoint | Database Effect | Success Destination | Cross-Role Effect |
|---|---|---|---|---|---|---|---|
| **Sidebar** | `Home` Link | Any | None | None | None | `/doctor/dashboard` | None |
| **Sidebar** | `Referrals` Link | Any | None | None | None | `/doctor/referrals` | None |
| **Sidebar** | `Consultations` Link | Any | None | None | None | `/doctor/consultations` | None |
| **Sidebar** | `ASHA Follow-ups` Link | Any | None | None | None | `/doctor/followups` | None |
| **Sidebar** | `Patients` Link | Any | None | None | None | `/doctor/patients` | None |
| **Sidebar** | `Investigations` Link | Any | None | None | None | `/doctor/investigations` | None |
| **Sidebar** | `Prescriptions` Link | Any | None | None | None | `/doctor/prescriptions` | None |
| **Sidebar** | `Alerts` Link | Any | None | None | None | `/doctor/alerts` | None |
| **Sidebar** | `System Status` Link | Any | None | None | None | `/doctor/system-status` | None |
| **Sidebar** | `Sign Out` Button | Authenticated | None | `POST /api/auth/logout` | Token invalidated | `/login` | Session cleared |
| **Metric Cards** | `New Referrals` Card | Any | None | `GET /api/doctor/referrals` | None | `/doctor/referrals?status=PENDING_DOCTOR_REVIEW` | None |
| **Metric Cards** | `Urgent Cases` Card | Any | None | `GET /api/doctor/referrals` | None | `/doctor/referrals?priority=URGENT&active=true` | None |
| **Metric Cards** | `Awaiting Consultation` Card | Any | None | `GET /api/doctor/referrals` | None | `/doctor/consultations?status=READY_TO_START` | None |
| **Metric Cards** | `ASHA Follow-ups` Card | Any | None | `GET /api/doctor/followups` | None | `/doctor/followups?status=REVIEW_REQUIRED` | None |
| **Metric Cards** | `Escalations` Card | Any | None | `GET /api/doctor/followups` | None | `/doctor/followups?status=ESCALATED` | None |
| **Metric Cards** | `Completed Today` Card | Any | None | `GET /api/doctor/consultations` | None | `/doctor/consultations?status=COMPLETED&date=today` | None |
| **Today's Clinical Work** | `Patients Arrived at PHC` Row | Click | None | None | None | `/doctor/consultations?status=READY_TO_START` | None |
| **Today's Clinical Work** | `Consultations in Progress` Row | Click | None | None | None | `/doctor/consultations?status=IN_CONSULTATION` | None |
| **Today's Clinical Work** | `Pending Investigations` Row | Click | None | None | None | `/doctor/investigations?status=ORDERED` | None |
| **Today's Clinical Work** | `ASHA Follow-ups to Review` Row | Click | None | None | None | `/doctor/followups?status=REVIEW_REQUIRED` | None |
| **ASHA Escalations Banner** | `Review Patient` Button | Escalated | `followUpId` | `GET /api/doctor/followups/:id` | None | `/doctor/followups/:followUpId` | None |
| **Referral Card** | `Review & Acknowledge` Button | `PENDING_DOCTOR_REVIEW` | `referralId` | `POST /api/doctor/referrals/:id/acknowledge` | `referrals.status = DOCTOR_ACKNOWLEDGED`, AuditLog | Updates list in-place | ASHA notified, timeline event created |
| **Referral Card** | `Mark Patient Arrived` Button | `DOCTOR_ACKNOWLEDGED` | `referralId` | `POST /api/doctor/referrals/:id/arrived` | `referrals.status = PATIENT_ARRIVED`, AuditLog | Updates list in-place | ASHA & Citizen see arrived status |
| **Referral Card** | `Start Consultation` Button | `PATIENT_ARRIVED` | `referralId` | `POST /api/doctor/consultations/start` | Creates `Consultation` record, `referrals.status = IN_CONSULTATION` | `/doctor/consultations/:consultationId` | Citizen/ASHA sees Doctor in consultation |
| **Referral Card** | `Resume Consultation` Button | `IN_CONSULTATION` | `consultationId` | `GET /api/doctor/consultations/:id` | None | `/doctor/consultations/:consultationId` | None |
| **Referral Card** | `View Completed` Button | `COMPLETED` | `consultationId` | `GET /api/doctor/consultations/:id` | None | `/doctor/consultations/:consultationId` | Read-only mode |
| **Referral Card** | `Call ASHA` Button | Any | None | `tel:` or Contact Modal | AuditLog on contact outcome | Opens phone dialer / outcome modal | ASHA contact audited |
| **Referral Card** | `View Timeline` Button | Any | `caseId` | `GET /api/cases/:id/timeline` | None | `/doctor/cases/:caseId/timeline` | None |
| **Referral Card** | `Request Missing Info` Button | Any | `caseId` | `POST /api/doctor/referrals/:id/request-info` | FollowUp/Notification record created | In-place modal feedback | ASHA receives Missing Info task |
| **Consultation Workspace** | `Open Next Patient` Banner Button | Arrived patient available | `referralId` | `POST /api/doctor/consultations/start` | Starts next arrived patient consultation | `/doctor/consultations/:consultationId` | Citizen/ASHA updated |
| **Consultation Screen** | `Record Repeat Vitals` Button | In consultation | `caseId` | `POST /api/doctor/consultations/record-vitals` | Creates new `VitalRecord` (Doctor source) | Vitals refreshed | New doctor vital in patient history |
| **Consultation Screen** | `Autosave Draft` | Input change (debounced) | `consultationId` | `PUT /api/doctor/consultations/:id/draft` | Updates draft consultation fields & version | Shows `Autosaved HH:MM` | Prevents multi-tab data loss |
| **Consultation Screen** | `Review & Sign Consultation` Button | Step 5 complete with Disposition | `consultationId` | `POST /api/doctor/consultations` | `consultations.status = COMPLETED`, `prescriptions.status = SIGNED` | `/doctor/consultations` | Citizen care plan, ASHA follow-up assigned |

---

## 4. State Machine Invariants

1. **State Exclusivity**:
   - Only `PENDING_DOCTOR_REVIEW` displays `Review & Acknowledge`.
   - Only `DOCTOR_ACKNOWLEDGED` displays `Mark Patient Arrived`.
   - Only `PATIENT_ARRIVED` displays `Start Consultation`.
   - Only `IN_CONSULTATION` displays `Resume Consultation`.
2. **One Active Consultation Per Referral**:
   - `POST /api/doctor/consultations/start` returns the existing active consultation if one is already open, preventing duplicate database records.
3. **Idempotent Mutations**:
   - Re-acknowledging or re-marking arrival returns the canonical record without creating duplicate audit events or notifications.
