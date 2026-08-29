# Aarogya Sahayak — Clinical Safety Engine, Boundaries & Invariants

## 1. Core Clinical Safety Invariants

### 1.1 Strict ASHA Role Boundaries
1. **Zero Diagnostic Assertions**: ASHA workers are front-line community health facilitators and are strictly prohibited from issuing clinical diagnoses (e.g. diagnosing "Pre-eclampsia" or "Myocardial Infarction").
2. **Deterministic Danger Sign Guidance**: The system evaluates clinical red flags using rule-based algorithms rather than non-deterministic LLMs.
3. **Approved Non-Diagnostic Phrasing**:
   * *Approved System Wording*: `"Warning signs detected. Urgent professional evaluation is recommended."`
   * *Prohibited System Wording*: `"Pre-eclampsia detected."`, `"You have severe hypertension."`, `"Prescribing medication."`
4. **Prescription Invariant**: Only registered PHC Medical Officers (MBBS) may prescribe prescription medications. ASHA workers may only verify medication adherence and dispense approved OTC supplements (e.g. IFA tablets, ORS, Zinc) as per National Health Mission protocols.

---

## 2. Deterministic Emergency Rule Evaluator Architecture

```
                       [ Incoming Assessment ]
                    (Symptoms + Vitals + Pregnancy)
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │ Deterministic Rule Evaluator │
                   │  (app/safety/rules.py)       │
                   └──────────────┬───────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         │                                                 │
         ▼                                                 ▼
[ Red Flag Triggered ]                          [ Normal / Routine ]
• Priority: URGENT                              • Priority: ROUTINE
• Rule Reason: Pregnancy warning signs          • Standard ANC/NCD Schedule
• Action: Immediate PHC Referral                • Routine Health Counseling
```

### 2.1 Deterministic Red Flag Trigger Matrix

| Category | Trigger Conditions | Clinical Action | Priority |
|---|---|---|---|
| **Maternal Antenatal** | Pregnancy + Systolic BP ≥ 140 OR Diastolic BP ≥ 90 + (Headache / Blurred Vision / Edema / Epigastric Pain) | Immediate PHC Medical Officer referral & ambulance transport | `URGENT` |
| **Severe Hypertension** | Systolic BP ≥ 160 OR Diastolic BP ≥ 100 | Immediate medical officer evaluation | `URGENT` |
| **Hypoxemia** | SpO2 < 92% on room air | Emergency referral with oxygen support | `URGENT` |
| **Severe Tachycardia** | Pulse Rate > 120 bpm at rest | Priority clinical triage | `HIGH` |
| **Severe Hypoglycemia** | Blood Glucose < 60 mg/dL with altered sensorium | Urgent oral glucose & facility transfer | `URGENT` |

---

## 3. Grounded Retrieval (GraphRAG & Milvus) Safety Constraints
* AI-assisted guidelines must originate from validated ICMR (Indian Council of Medical Research) and MoHFW National Health Mission clinical manuals.
* All displayed guidelines cite exact policy IDs (e.g. `ICMR-OBS-01`) and source documents.
* Summaries are flagged as `"AI-assisted summary — human clinical review required"`.
