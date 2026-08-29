# ASHA Worker Portal — Interactive Action Contract

This document provides a comprehensive audit of all primary interactive actions (buttons and submissions) on the ASHA Worker Portal interface, specifying pre-conditions, API/local behaviors, database side-effects, cross-role effects, offline behavior, and testing strategies.

---

## 1. Add Patient Registration Wizard

- **Screen**: `/asha/patients/new`
- **Button**: `✓ Complete & Save Patient` (Step 7)
- **Visible Condition**: Active wizard step is `7` and final ASHA confirmation checkbox is checked.
- **API / Local Action**: Sends a POST request to `/api/asha/patient-registration`.
- **Loading State**: Disables submit button, shows `Saving Patient...` text and a spinner.
- **Success State**: Opens a Success Modal summarizing registration data and recommendations.
- **Error State**: Renders clear form-level warnings and resets button state.
- **Database Effect**: Atomically inserts `CitizenProfile`, optional `Case`, initial `AshaVisit`, `Referral`, `FollowUp`, and `AuditLog` in a single transaction.
- **Cross-Role Effect**: 
  - If referred, immediately populates the PHC Doctor's Referral Queue.
  - If a follow-up is scheduled, populates the ASHA Follow-up Workspace.
- **Offline Behavior**: Queues a `REGISTER_PATIENT` action in Dexie's `pendingActions`. Reconnection triggers an atomic sync replay with local-to-server ID mapping.
- **Test Coverage**: Tested in `tests/e2e_add_patient_wizard.py` and `tests/test_patient_registration.py`.

---

## 2. Dynamic Field Visit Submission

- **Screen**: `/asha/visit?caseId={caseId}`
- **Button**: `Submit Visit & Actions` (Step 7)
- **Visible Condition**: Active wizard step is `7` and consent is checked.
- **API / Local Action**: Sends a POST request to `/api/asha/visits`.
- **Loading State**: Disables submit button and sets `isSubmitting = true`.
- **Success State**: Displays a Success Modal.
- **Error State**: Alerts the user and saves locally to the offline queue.
- **Database Effect**:
  - Updates `Case.status` to `ASHA_REVIEWED` or `REFERRED_TO_PHC`.
  - Inserts `VitalRecord`, `AshaVisit`, and optional `Referral` and `FollowUp` records.
- **Cross-Role Effect**:
  - Creates PHC doctor queue referral record.
  - Updates live dashboard counts.
- **Offline Behavior**: Queues `CREATE_VISIT` and optional `CREATE_FOLLOWUP` actions in Dexie.
- **Test Coverage**: Verified in `tests/e2e_offline_workflow.py`.

---

## 3. Case Acknowledgment

- **Screen**: `/asha/dashboard` or `/asha/cases/{caseId}`
- **Button**: `Acknowledge Case`
- **Visible Condition**: Case status is `NEW`.
- **API / Local Action**: Sends a POST request to `/api/asha/cases/{caseId}/acknowledge`.
- **Loading State**: Button displays standard loading state.
- **Success State**: Changes button to disabled `Acknowledged` indicator and updates status to `ASHA_ACKNOWLEDGED`.
- **Error State**: Displays alert banner.
- **Database Effect**: Updates `Case.status` to `ASHA_ACKNOWLEDGED` and appends an `AuditLog`.
- **Cross-Role Effect**: Broadcasts WebSocket event updating timelines across roles.
- **Offline Behavior**: Queues an `ACKNOWLEDGE_CASE` action.
- **Test Coverage**: Verified in `tests/test_case_workflow.py`.

---

## 4. Contact Attempt

- **Screen**: `/asha/dashboard`
- **Button**: `Log Contact Attempt` (within Case Row)
- **Visible Condition**: Always available on active cases.
- **API / Local Action**: Sends a POST request to `/api/asha/cases/{caseId}/contact-result`.
- **Loading State**: Standard inline loading indicator.
- **Success State**: Displays inline confirmation toast.
- **Error State**: Shows toast alert.
- **Database Effect**: Adds `AshaVisit` record with status `ATTEMPTED`.
- **Cross-Role Effect**: Updates case timeline with contact attempt.
- **Offline Behavior**: Queues `CONTACT_CITIZEN` action.
- **Test Coverage**: Verified in `tests/test_cross_role_mvc.py`.

---

## 5. Follow-Up Resolution (Start / Reschedule / Complete)

- **Screen**: `/asha/followups/{id}`
- **Buttons**: `Start Follow-up`, `Record Contact Attempt`, `Complete Follow-up`
- **Visible Condition**: Based on the current Follow-up status:
  - `Start`: Status is `PENDING`.
  - `Record Contact / Complete`: Status is `IN_PROGRESS`.
- **API / Local Action**: POST request to `/api/asha/followups/{id}/[start|contact-result|complete]`.
- **Loading State**: Standard button loading text.
- **Success State**: Transitions local follow-up status view.
- **Error State**: Renders inline warning text.
- **Database Effect**: Updates `FollowUp` status and timestamps; adds clinical observations or vitals.
- **Cross-Role Effect**: Resolves active follow-up counts on the dashboard.
- **Offline Behavior**: Queues `UPDATE_FOLLOWUP` action with sub-action details.
- **Test Coverage**: Verified in `tests/test_followups_and_timeline.py`.
