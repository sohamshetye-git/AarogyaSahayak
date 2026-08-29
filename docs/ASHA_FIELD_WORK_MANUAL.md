# Aarogya Sahayak — ASHA Worker Field Work Manual & Operating Procedures

## 1. Role and Clinical Boundaries
The Accredited Social Health Activist (ASHA) serves as the primary health intermediary between the rural community and the public healthcare delivery system (Primary Health Centres, Sub-Centres, and Community Health Centres).

### Core Responsibilities
* **Antenatal and Postnatal Care Tracking**: Routine home visits, maternal danger sign identification, and birth preparedness counseling.
* **Triage & Risk Screening**: Initial observation of presenting symptoms, basic vital sign recording (BP, SpO2, Pulse, Temp, Glucose), and deterministic danger sign identification.
* **Referral Facilitation**: Promptly escalating identified danger signs to the PHC Medical Officer, coordinating 108/102 emergency ambulance transport, and ensuring institutional delivery.
* **Direct Treatment Adherence**: Verifying consumption of prescribed medicines (e.g. Iron Folic Acid, Calcium, antihypertensive therapy) as directed by the PHC Medical Officer.
* **Government Scheme Facilitation**: Verifying beneficiary eligibility and assisting rural citizens in enrolling for Pradhan Mantri Matru Vandana Yojana (PMMVY), Janani Suraksha Yojana (JSY), and Ayushman Bharat PM-JAY.

---

## 2. Standard Operating Procedures (SOP) by Workflow

### SOP-01: Citizen Case Triage & Phone Contact
1. **Case Receipt**: Review newly assigned cases under `Tasks` or `Home Dashboard`. Urgent red flag cases must be reviewed immediately.
2. **Acknowledgment**: Click `✓ Acknowledge Case` within 30 minutes of receiving an urgent assignment.
3. **Contact Attempt**:
   * Attempt phone call via `📞 Call Citizen`.
   * If spoken to citizen: select `✓ Spoke to Citizen`, verify current symptoms, schedule home visit timing, and click `Save Outcome`.
   * If unreachable: select `🚫 Unreachable`, record attempt number and reason (e.g. No Answer, Switched Off), and set next attempt date. If 3 consecutive calls fail, escalate to PHC.

### SOP-02: 7-Step In-Person Field Visit
1. **Step 1 — Consent & Identification**:
   * Verify citizen identity at their residence.
   * Seek explicit informed verbal consent before measuring vitals.
2. **Step 2 — Spoken Symptoms Verification**:
   * Review citizen voice transcript.
   * Check off all confirmed symptoms individually; add any newly observed symptoms manually.
3. **Step 3 — Vital Signs Recording**:
   * Measure Blood Pressure using calibrated digital sphygmomanometer.
   * Measure Oxygen Saturation (SpO2) and Pulse Rate using pulse oximeter.
   * Record body temperature and random blood glucose when indicated.
   * If Systolic BP ≥ 140 mmHg or Diastolic BP ≥ 90 mmHg in pregnancy, deterministic red flag triggers automatically.
4. **Step 4 — Safety Engine & GraphRAG Protocol Review**:
   * Review ICMR/MoHFW standard care workflows and government scheme benefits.
   * Verify source policy citations and confidence scores.
5. **Step 5 — ASHA Clinical Observations**:
   * Record observational notes using text or Marathi/Hindi voice input.
   * Provide hydration and rest counseling (e.g. left lateral resting position).
6. **Step 6 — Referral & Scheduling**:
   * Select destination PHC (e.g. Kalyanpur PHC) and urgency level (`URGENT`).
   * Toggle emergency ambulance transport if needed.
   * Schedule required in-person ASHA follow-up visit.
7. **Step 7 — Review & Submission**:
   * Review the complete clinical summary.
   * Click `Submit Field Visit & Referral` for instant transmission to the Doctor portal.

### SOP-03: Post-Doctor Follow-up Checkup
1. Open assigned follow-ups in `Follow-ups` tab.
2. Visit citizen residence on the scheduled due date.
3. Verify medication adherence and check if symptoms have resolved or worsened.
4. Measure repeat Blood Pressure and Pulse.
5. If blood pressure remains elevated or warning signs persist, toggle `Escalate to Doctor` and submit completion report.

---

## 3. Offline & Low-Connectivity Field Procedures
* The Aarogya Sahayak application operates completely offline using IndexedDB (Dexie.js).
* Field visit drafts, symptom confirmations, and vital sign records are stored locally with zero data loss.
* When connectivity is re-established, records synchronize automatically with PostgreSQL backend in the background.
* In the event of a sync conflict, the ASHA worker is notified with a 3-way conflict resolution interface.
