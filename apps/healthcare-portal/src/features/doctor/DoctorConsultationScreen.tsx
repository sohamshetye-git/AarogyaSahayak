import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import {
  StethoscopeIcon,
  PillIcon,
  ActivityIcon,
  CheckCircleIcon,
  WarningIcon,
  ShieldCheckIcon,
} from "../../components/Icons";

export function DoctorConsultationScreen() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const caseId = searchParams.get("caseId") || "case-canonical-001";

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isAcknowledging, setIsAcknowledging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [completedConsultation, setCompletedConsultation] = useState<any>(null);

  // Form State
  const [examinationNotes, setExaminationNotes] = useState(
    "Patient alert, oriented. Bilateral pedal edema 2+ noted. Deep tendon reflexes brisk (3+). Fundoscopy reveals arteriolar narrowing without papilledema. Uterine size corresponds to 28 weeks, fetal heart sounds regular (142 bpm)."
  );
  const [confirmedDiagnosis, setConfirmedDiagnosis] = useState(
    "Gestational Hypertension / Pre-eclampsia (ICD-10: O14.9)"
  );
  const [icd10Code, setIcd10Code] = useState("O14.9");
  const [prescriptionItems, setPrescriptionItems] = useState([
    {
      medicine: "Labetalol",
      strength: "100mg",
      form: "Tablet",
      dose: "1 tablet",
      frequency: "Twice daily",
      duration: "14 days",
      timing: "After food",
      instructions: "Take after meals. Monitor for dizziness.",
    },
    {
      medicine: "Calcium + Vitamin D3",
      strength: "500mg",
      form: "Tablet",
      dose: "1 tablet",
      frequency: "Once daily",
      duration: "30 days",
      timing: "After food",
      instructions: "Take in the morning.",
    },
  ]);
  const [tests, setTests] = useState([
    "Complete Blood Count (CBC)",
    "Urine Albumin (Dipstick / 24hr)",
    "Serum Creatinine & Uric Acid",
    "Obstetric Ultrasound (Growth & Doppler)",
  ]);
  const [carePlan, setCarePlan] = useState(
    "Bed rest on left lateral side. Low sodium diet. Antihypertensive regimen initiated. Emergency warning signs (severe epigastric pain, visual disturbance) explained. Return immediately if symptoms worsen."
  );
  const [ashaInstructions, setAshaInstructions] = useState(
    "Conduct home visit every 3 days. Record resting blood pressure and verify medicine compliance. Report any BP >= 160/110 immediately."
  );
  const [followupDays, setFollowupDays] = useState(3);

  const fetchDetails = async () => {
    try {
      const res = await apiClient.getDoctorCaseDetails(caseId);
      setData(res);
    } catch (err) {
      console.error("Failed to load doctor case details", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [caseId]);

  const handleAcknowledge = async () => {
    setIsAcknowledging(true);
    try {
      await apiClient.acknowledgeReferral(caseId);
      await fetchDetails();
    } catch (err) {
      console.error(err);
    } finally {
      setIsAcknowledging(false);
    }
  };

  const handleCompleteConsultation = async () => {
    setIsSubmitting(true);
    try {
      const res = await apiClient.completeConsultation({
        case_id: data?.case_id || caseId,
        examination_notes: examinationNotes,
        clinical_summary: "Confirmed maternal pre-eclampsia. Antihypertensive started and ASHA follow-up dispatched.",
        confirmed_diagnosis: confirmedDiagnosis,
        icd10_code: icd10Code,
        prescription_items: prescriptionItems,
        investigation_orders: tests,
        care_plan_summary: carePlan,
        asha_followup_instructions: ashaInstructions,
        followup_due_days: followupDays,
      });
      setCompletedConsultation(res);
    } catch (err) {
      console.error("Failed to complete consultation", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading || !data) {
    return <div style={{ padding: 40, textAlign: "center" }}>Loading clinical consultation workspace...</div>;
  }

  if (completedConsultation) {
    return (
      <div
        style={{
          backgroundColor: "var(--surface)",
          padding: 40,
          borderRadius: 16,
          border: "1px solid var(--border)",
          textAlign: "center",
          maxWidth: 650,
          margin: "40px auto",
        }}
      >
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: "50%",
            backgroundColor: "var(--success-bg)",
            color: "var(--success)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 20px",
          }}
        >
          <CheckCircleIcon size={36} color="var(--success)" />
        </div>
        <h2 style={{ margin: "0 0 8px", fontSize: 22, fontWeight: 700, color: "var(--text-primary)" }}>
          Consultation & Prescription Signed!
        </h2>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 24, lineHeight: "22px" }}>
          Clinical diagnosis <strong>{completedConsultation.confirmed_diagnosis}</strong> recorded. Prescription issued with digital signature ref. ASHA follow-up assigned for Kalyanpur village in {followupDays} days.
        </p>

        <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
          <button
            onClick={() => navigate("/doctor/dashboard")}
            style={{
              padding: "12px 24px",
              backgroundColor: "var(--primary)",
              color: "#FFF",
              borderRadius: 8,
              border: "none",
              fontSize: 14,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Return to Referral Queue
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Patient Header Banner */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          padding: 24,
          borderRadius: 12,
          border: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: "var(--text-primary)" }}>
              {data.citizen_name}
            </h1>
            <PriorityBadge priority={data.priority} />
            <StatusBadge status={data.status} />
          </div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            Case: <strong>{data.case_reference}</strong> · Age: {data.citizen_age} · Village: {data.village_name} ·
            {data.is_pregnant && (
              <span style={{ color: "#C2185B", fontWeight: 700, marginLeft: 6 }}>
                Pregnant ({data.gestational_weeks ? `${data.gestational_weeks}w` : "7m"})
              </span>
            )}
            · ASHA: {data.assigned_asha_name}
          </div>
        </div>

        {data.referral_status === "PENDING_DOCTOR_REVIEW" && (
          <button
            onClick={handleAcknowledge}
            disabled={isAcknowledging}
            style={{
              padding: "10px 20px",
              backgroundColor: "var(--primary)",
              color: "#FFF",
              borderRadius: 8,
              border: "none",
              fontSize: 14,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            {isAcknowledging ? "Acknowledging..." : "✓ Acknowledge Referral"}
          </button>
        )}
      </div>

      {/* 3-Column Source Evidence View */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        {/* Column 1: Citizen Reported */}
        <div style={{ backgroundColor: "var(--surface)", padding: 18, borderRadius: 10, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>
            🗣 1. Citizen Spoken Voice
          </div>
          <div style={{ fontSize: 13, fontStyle: "italic", color: "var(--text-secondary)", lineHeight: "20px", marginBottom: 10 }}>
            "{data.primary_concern}"
          </div>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>Reported Symptoms:</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
            {data.symptoms?.map((s: any, i: number) => (
              <span key={i} style={{ padding: "3px 8px", borderRadius: 4, backgroundColor: "var(--neutral-bg)", fontSize: 12 }}>
                {s.term}
              </span>
            ))}
          </div>
        </div>

        {/* Column 2: ASHA Field Vitals */}
        <div style={{ backgroundColor: "var(--surface)", padding: 18, borderRadius: 10, border: "1px solid #F5C6CB" }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--urgent)", marginBottom: 8 }}>
            🩺 2. ASHA Confirmed Vitals
          </div>
          <div style={{ fontSize: 24, fontWeight: 800, color: "var(--urgent)" }}>
            {data.vitals?.[0]?.systolic_bp || 150}/{data.vitals?.[0]?.diastolic_bp || 100}{" "}
            <span style={{ fontSize: 12, fontWeight: 500 }}>mmHg</span>
          </div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 6 }}>
            SpO₂: <strong>{data.vitals?.[0]?.spo2 || 97}%</strong> · Pulse: <strong>{data.vitals?.[0]?.pulse || 88} bpm</strong> · Temp: <strong>37.0°C</strong>
          </div>
          <div style={{ fontSize: 12, color: "var(--urgent)", fontWeight: 600, marginTop: 8 }}>
            ⚠️ Stage 2 Hypertension in pregnancy
          </div>
        </div>

        {/* Column 3: AI Guideline Evidence */}
        <div style={{ backgroundColor: "var(--surface)", padding: 18, borderRadius: 10, border: "1px solid #BEE3F8" }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--primary)", marginBottom: 8 }}>
            📚 3. AI-Assisted Protocol
          </div>
          <div style={{ fontSize: 12, color: "var(--text-primary)", lineHeight: "18px" }}>
            {data.ai_assisted_summary}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 8, fontStyle: "italic" }}>
            Sources: ICMR-STW-Obstetrics-2023, MoHFW Maternal Care Protocol.
          </div>
        </div>
      </div>

      {/* Clinical Workspace Form */}
      <div style={{ backgroundColor: "var(--surface)", padding: 28, borderRadius: 12, border: "1px solid var(--border)" }}>
        <h2 style={{ margin: "0 0 20px", fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
          Clinical Consultation & Care Plan
        </h2>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Examination Notes */}
          <div>
            <label style={{ display: "block", fontSize: 13, fontWeight: 700, marginBottom: 6 }}>
              Physical & Obstetric Examination Notes
            </label>
            <textarea
              value={examinationNotes}
              onChange={(e) => setExaminationNotes(e.target.value)}
              rows={3}
              style={{ width: "100%", padding: 12, borderRadius: 8, border: "1px solid var(--border)", fontSize: 14 }}
            />
          </div>

          {/* Diagnosis & ICD-10 */}
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 700, marginBottom: 6 }}>
                Doctor-Confirmed Clinical Diagnosis
              </label>
              <input
                type="text"
                value={confirmedDiagnosis}
                onChange={(e) => setConfirmedDiagnosis(e.target.value)}
                style={{ width: "100%", height: 44, padding: "0 12px", borderRadius: 8, border: "2px solid var(--primary)", fontSize: 14, fontWeight: 600 }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 700, marginBottom: 6 }}>
                ICD-10 Code
              </label>
              <input
                type="text"
                value={icd10Code}
                onChange={(e) => setIcd10Code(e.target.value)}
                style={{ width: "100%", height: 44, padding: "0 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 14 }}
              />
            </div>
          </div>

          {/* Prescription Items */}
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <label style={{ fontSize: 13, fontWeight: 700 }}>Prescription Items (Doctor Approved)</label>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {prescriptionItems.map((item, index) => (
                <div
                  key={index}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 1fr 1fr 1fr 2fr",
                    gap: 10,
                    padding: 12,
                    backgroundColor: "var(--neutral-bg)",
                    borderRadius: 8,
                  }}
                >
                  <input
                    type="text"
                    value={item.medicine}
                    readOnly
                    style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)", fontWeight: 700 }}
                  />
                  <input
                    type="text"
                    value={item.strength}
                    readOnly
                    style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)" }}
                  />
                  <input
                    type="text"
                    value={item.frequency}
                    readOnly
                    style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)" }}
                  />
                  <input
                    type="text"
                    value={item.duration}
                    readOnly
                    style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)" }}
                  />
                  <input
                    type="text"
                    value={item.instructions}
                    readOnly
                    style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)" }}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Investigation Orders */}
          <div>
            <label style={{ display: "block", fontSize: 13, fontWeight: 700, marginBottom: 8 }}>
              Lab Investigations Ordered
            </label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {tests.map((test, i) => (
                <span
                  key={i}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 6,
                    backgroundColor: "var(--primary-light)",
                    color: "var(--primary-dark)",
                    fontSize: 13,
                    fontWeight: 600,
                  }}
                >
                  🧪 {test}
                </span>
              ))}
            </div>
          </div>

          {/* Care Plan & ASHA Follow-up */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 700, marginBottom: 6 }}>
                Citizen Care Plan & Instructions
              </label>
              <textarea
                value={carePlan}
                onChange={(e) => setCarePlan(e.target.value)}
                rows={3}
                style={{ width: "100%", padding: 12, borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 700, marginBottom: 6 }}>
                ASHA Follow-up Assignment (Every {followupDays} days)
              </label>
              <textarea
                value={ashaInstructions}
                onChange={(e) => setAshaInstructions(e.target.value)}
                rows={3}
                style={{ width: "100%", padding: 12, borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
              />
            </div>
          </div>

          {/* Sign & Complete Button */}
          <div style={{ marginTop: 12 }}>
            <button
              onClick={handleCompleteConsultation}
              disabled={isSubmitting}
              style={{
                width: "100%",
                height: 52,
                backgroundColor: "var(--success)",
                color: "#FFF",
                borderRadius: 8,
                border: "none",
                fontSize: 16,
                fontWeight: 700,
                cursor: isSubmitting ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 10,
              }}
            >
              <ShieldCheckIcon size={22} color="#FFF" />
              <span>{isSubmitting ? "Signing Record..." : "Sign & Complete Clinical Consultation"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
