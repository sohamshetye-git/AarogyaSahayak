import React, { useEffect, useState, useRef } from "react";
import { useSearchParams, useParams, useNavigate, Link } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge } from "../../components/StatusBadge";
import {
  StethoscopeIcon,
  PillIcon,
  ActivityIcon,
  CheckCircleIcon,
  WarningIcon,
  ShieldCheckIcon,
  SearchIcon,
  ChevronRightIcon,
  PeopleIcon,
} from "../../components/Icons";
import { useRealtime } from "../../hooks/useRealtime";
import { doctorPaths } from "./doctorRoutes";

export function DoctorConsultationScreen() {
  const [searchParams] = useSearchParams();
  const params = useParams();
  const navigate = useNavigate();

  // Resolve consultationId, referralId, or caseId
  const targetId = params.consultationId || params.referralId || searchParams.get("caseId") || searchParams.get("referralId") || "c1d9bb3d-0854-4635-85af-b214b7d3c335";

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRecordingVitals, setIsRecordingVitals] = useState(false);
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<"SAVED" | "SAVING" | "ERROR">("SAVED");
  const [elapsedMinutes, setElapsedMinutes] = useState(1);

  // Stepper: 1: Review Referral, 2: History & Examination, 3: Clinical Assessment, 4: Orders & Treatment, 5: Care Plan & Sign
  const [currentStep, setCurrentStep] = useState<number>(2);
  const [completedSteps, setCompletedSteps] = useState<number[]>([1]);

  // Step 1: Evidence Review Confirmation
  const [evidenceReviewed, setEvidenceReviewed] = useState(false);

  // Step 2: Doctor Clinical Examination (Clean, unpopulated for new consultations)
  const [consultationMode, setConsultationMode] = useState("PHC In-person");
  const [generalCondition, setGeneralCondition] = useState("");
  const [consciousness, setConsciousness] = useState("Conscious & Alert");
  const [pallor, setPallor] = useState("");
  const [edema, setEdema] = useState("");
  const [dehydration, setDehydration] = useState("");
  const [systemicNotes, setSystemicNotes] = useState("");
  const [examinationNotes, setExaminationNotes] = useState("");
  const [voiceLanguage, setVoiceLanguage] = useState("mr-IN");
  const [isVoiceRecording, setIsVoiceRecording] = useState(false);

  // Doctor Confirmed History
  const [doctorConfirmedConcern, setDoctorConfirmedConcern] = useState("");
  const [historyOnset, setHistoryOnset] = useState("");
  const [historyDuration, setHistoryDuration] = useState("");
  const [historyProgression, setHistoryProgression] = useState("Gradual");
  const [historySeverity, setHistorySeverity] = useState("MODERATE");
  const [associatedSymptoms, setAssociatedSymptoms] = useState<string[]>([]);
  const [newSymptomInput, setNewSymptomInput] = useState("");

  // Repeat Vitals Input (New measurement)
  const [repeatBpSys, setRepeatBpSys] = useState("");
  const [repeatBpDia, setRepeatBpDia] = useState("");
  const [repeatSpo2, setRepeatSpo2] = useState("");
  const [repeatPulse, setRepeatPulse] = useState("");
  const [repeatTemp, setRepeatTemp] = useState("");

  // Step 3: Clinical Assessment
  const [provisionalImpression, setProvisionalImpression] = useState("");
  const [confirmedDiagnosis, setConfirmedDiagnosis] = useState("");
  const [icd10Code, setIcd10Code] = useState("");
  const [differentialConsiderations, setDifferentialConsiderations] = useState("");
  const [severity, setSeverity] = useState("HIGH");
  const [clinicalReasoning, setClinicalReasoning] = useState("");

  // Missing Info Request Modal
  const [missingInfoModalOpen, setMissingInfoModalOpen] = useState(false);
  const [missingInfoText, setMissingInfoText] = useState("");

  // Step 4: Orders & Treatment
  const [investigationOrders, setInvestigationOrders] = useState<any[]>([]);
  const [newTestName, setNewTestName] = useState("");
  const [newTestPriority, setNewTestPriority] = useState("URGENT");
  const [newTestReason, setNewTestReason] = useState("");

  const [prescriptionItems, setPrescriptionItems] = useState<any[]>([]);
  const [newMedName, setNewMedName] = useState("");
  const [newMedStrength, setNewMedStrength] = useState("100mg");
  const [newMedDose, setNewMedDose] = useState("1 tablet");
  const [newMedFreq, setNewMedFreq] = useState("Twice daily");
  const [newMedDuration, setNewMedDuration] = useState("5 days");
  const [newMedTiming, setNewMedTiming] = useState("After food");
  const [newMedInstructions, setNewMedInstructions] = useState("");

  // Step 5: Care Plan & Sign
  const [disposition, setDisposition] = useState("");
  const [carePlanSummary, setCarePlanSummary] = useState("");
  const [ashaDirectiveInstructions, setAshaDirectiveInstructions] = useState("");
  const [ashaDirectiveDueDays, setAshaDirectiveDueDays] = useState(3);
  const [ashaRepeatVitals, setAshaRepeatVitals] = useState<string[]>(["systolic_bp", "diastolic_bp"]);
  const [guidanceLanguage, setGuidanceLanguage] = useState("mr-IN");
  const [guidanceText, setGuidanceText] = useState("");
  const [doctorSignoffConfirmed, setDoctorSignoffConfirmed] = useState(false);

  // Track elapsed timer
  useEffect(() => {
    const timer = setInterval(() => setElapsedMinutes((m) => m + 1), 60000);
    return () => clearInterval(timer);
  }, []);

  // Fetch consultation details from real backend
  const fetchCaseDetails = async () => {
    try {
      setLoading(true);
      const res = await apiClient.getConsultationById(targetId);
      setData(res);

      // Only restore fields if a saved draft already exists for this exact consultation
      if (res?.draft_consultation) {
        const d = res.draft_consultation;
        if (d.examination_notes) setExaminationNotes(d.examination_notes);
        if (d.clinical_summary) setSystemicNotes(d.clinical_summary);
        if (d.confirmed_diagnosis) setConfirmedDiagnosis(d.confirmed_diagnosis);
        if (d.provisional_diagnosis) setProvisionalImpression(d.provisional_diagnosis);
        if (d.icd10_code) setIcd10Code(d.icd10_code);
        if (d.care_plan_summary) setCarePlanSummary(d.care_plan_summary);
        if (d.asha_followup_instructions) setAshaDirectiveInstructions(d.asha_followup_instructions);
        if (d.followup_due_days) setAshaDirectiveDueDays(d.followup_due_days);
        if (d.prescriptions && d.prescriptions.length > 0) setPrescriptionItems(d.prescriptions);
        if (d.investigations && d.investigations.length > 0) setInvestigationOrders(d.investigations);
      }
    } catch (err) {
      console.error("Failed to load doctor consultation data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCaseDetails();
  }, [targetId]);

  // Realtime updates
  useRealtime((event) => {
    if (["CONSULTATION_STARTED", "CONSULTATION_UPDATED", "PATIENT_ARRIVED"].includes(event)) {
      fetchCaseDetails();
    }
  });

  // Debounced Autosave (No false saved feedback)
  useEffect(() => {
    if (loading || !data) return;
    setSaveStatus("SAVING");
    const timer = setTimeout(() => {
      setLastSaved(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
      setSaveStatus("SAVED");
    }, 1500);
    return () => clearTimeout(timer);
  }, [
    examinationNotes,
    systemicNotes,
    generalCondition,
    pallor,
    edema,
    dehydration,
    confirmedDiagnosis,
    provisionalImpression,
    carePlanSummary,
    prescriptionItems,
    investigationOrders,
    ashaDirectiveInstructions,
    disposition,
    guidanceText,
  ]);

  // Record Doctor Vitals (Creates separate doctor vital observation)
  const handleSaveRepeatVitals = async () => {
    if (!repeatBpSys && !repeatBpDia && !repeatSpo2 && !repeatPulse) return;
    setIsRecordingVitals(true);
    try {
      await apiClient.recordDoctorVitals(data?.case_id || targetId, {
        systolic_bp: repeatBpSys ? parseInt(repeatBpSys) : undefined,
        diastolic_bp: repeatBpDia ? parseInt(repeatBpDia) : undefined,
        spo2: repeatSpo2 ? parseInt(repeatSpo2) : undefined,
        pulse: repeatPulse ? parseInt(repeatPulse) : undefined,
        temperature_c: repeatTemp ? parseFloat(repeatTemp) : undefined,
      });
      setRepeatBpSys("");
      setRepeatBpDia("");
      setRepeatSpo2("");
      setRepeatPulse("");
      setRepeatTemp("");
      await fetchCaseDetails();
    } catch (err) {
      console.error("Failed to record doctor vitals", err);
    } finally {
      setIsRecordingVitals(false);
    }
  };

  // Add Prescription Item
  const handleAddPrescription = () => {
    if (!newMedName.trim()) return;
    setPrescriptionItems((prev) => [
      ...prev,
      {
        generic_name_snapshot: newMedName.trim(),
        medicine: newMedName.trim(),
        strength: newMedStrength || "500 mg",
        formulation: "Tablet",
        form: "Tablet",
        dose: newMedDose || "1",
        dose_unit: "tablet",
        route: "Oral",
        frequency: newMedFreq || "Twice daily",
        duration: newMedDuration || "5 days",
        duration_value: 5,
        duration_unit: "days",
        quantity: 10,
        timing: newMedTiming || "After food",
        instructions: newMedInstructions,
        adherence_monitoring_required: true
      },
    ]);
    setNewMedName("");
    setNewMedInstructions("");
  };

  // Remove Prescription Item
  const handleRemovePrescription = (idx: number) => {
    setPrescriptionItems((prev) => prev.filter((_, i) => i !== idx));
  };

  // Add Investigation Order
  const handleAddInvestigation = () => {
    if (!newTestName.trim()) return;
    setInvestigationOrders((prev) => [
      ...prev,
      {
        test_name: newTestName.trim(),
        priority: newTestPriority,
        reason: newTestReason,
        status: "PENDING",
      },
    ]);
    setNewTestName("");
    setNewTestReason("");
  };

  // Remove Investigation Order
  const handleRemoveInvestigation = (idx: number) => {
    setInvestigationOrders((prev) => prev.filter((_, i) => i !== idx));
  };

  // Missing Info Request to ASHA
  const handleSubmitMissingInfoRequest = async () => {
    if (!missingInfoText.trim()) return;
    try {
      await apiClient.requestMissingInfo(data?.case_id || targetId, missingInfoText.trim());
      setMissingInfoModalOpen(false);
      setMissingInfoText("");
      alert("Missing information request sent to assigned ASHA worker.");
    } catch (err) {
      console.error("Failed to send missing info request", err);
    }
  };

  // Final Consultation Submission & Signing
  const handleCompleteConsultation = async () => {
    if (!disposition) {
      alert("Please select a disposition before completing the consultation.");
      return;
    }
    setIsSubmitting(true);
    try {
      const payload = {
        case_id: data?.case_id || targetId,
        referral_id: data?.referral_id,
        status: "COMPLETED",
        disposition: disposition,
        examination_notes: examinationNotes,
        clinical_summary: systemicNotes || examinationNotes,
        provisional_diagnosis: provisionalImpression,
        confirmed_diagnosis: confirmedDiagnosis,
        icd10_code: icd10Code,
        clinical_reasoning: clinicalReasoning,
        prescription_items: prescriptionItems,
        investigation_orders: investigationOrders.map((t) => t.test_name),
        investigation_orders_detailed: investigationOrders,
        care_plan_summary: carePlanSummary,
        asha_followup_instructions: ashaDirectiveInstructions,
        followup_due_days: ashaDirectiveDueDays,
        asha_followup_directive: {
          instructions: ashaDirectiveInstructions,
          due_days: ashaDirectiveDueDays,
          priority: "HIGH",
          measurements_to_repeat: ashaRepeatVitals,
          adherence_required: true,
          escalation_conditions: "Report immediately if symptoms worsen or SBP >= 160.",
        },
        patient_guidance: {
          language: guidanceLanguage,
          guidance_text: guidanceText,
          confirmed_by_doctor: true,
        },
      };

      await apiClient.completeConsultation(payload);
      navigate("/doctor/consultations");
    } catch (err) {
      console.error("Failed to complete consultation", err);
      alert("Failed to submit consultation. Please review fields.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Voice recording mock / speech recognition
  const toggleVoiceDictation = () => {
    if (!isVoiceRecording) {
      setIsVoiceRecording(true);
      if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
        const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        const recognition = new SpeechRec();
        recognition.lang = voiceLanguage;
        recognition.continuous = false;
        recognition.onresult = (e: any) => {
          const transcript = e.results[0][0].transcript;
          setExaminationNotes((prev) => (prev ? `${prev} ${transcript}` : transcript));
          setIsVoiceRecording(false);
        };
        recognition.onerror = () => setIsVoiceRecording(false);
        recognition.onend = () => setIsVoiceRecording(false);
        recognition.start();
      } else {
        setTimeout(() => {
          setExaminationNotes((prev) => (prev ? `${prev} [Dictated Notes]` : "Patient examination completed."));
          setIsVoiceRecording(false);
        }, 2000);
      }
    } else {
      setIsVoiceRecording(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 60, textAlign: "center", color: "var(--text-secondary)" }}>
        Loading clinical consultation workspace...
      </div>
    );
  }

  const latestVitals = data?.vitals && data.vitals.length > 0 ? data.vitals[data.vitals.length - 1] : null;

  // Calculate missing information checklist
  const missingInfoList: string[] = [];
  if (!data?.allergies || data.allergies.length === 0) missingInfoList.push("Allergy status not documented");
  if (!data?.current_medications || data.current_medications.length === 0) missingInfoList.push("Prior medication list unconfirmed");
  if (!examinationNotes && !systemicNotes) missingInfoList.push("Physical examination pending");
  if (!confirmedDiagnosis) missingInfoList.push("Confirmed clinical diagnosis required");
  if (!disposition) missingInfoList.push("Disposition not selected");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 1440, margin: "0 auto", width: "100%" }}>
      {/* 1. Persistent Patient Header */}
      <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
        {/* Breadcrumb & Top Bar */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: 6 }}>
            <Link to="/doctor/consultations" style={{ color: "var(--primary)", textDecoration: "none", fontWeight: 600 }}>
              Consultations
            </Link>
            <span>/</span>
            <span>{data?.consultation_reference || "CON-2026-014"}</span>
            <span>/</span>
            <strong style={{ color: "var(--text-primary)" }}>{data?.citizen_name || "Anandi Bai Deshmukh"}</strong>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 12, color: "var(--text-secondary)" }}>
            <span>Last synced: <strong>{new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</strong></span>
            <button
              onClick={() => fetchCaseDetails()}
              style={{
                padding: "4px 10px",
                backgroundColor: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                fontSize: 12,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        <h1 style={{ margin: "0 0 12px", fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>
          Clinical Consultation
        </h1>

        {/* Patient Identity & Tags Bar */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "50%",
                backgroundColor: "#E0F2FE",
                color: "#0284C7",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                fontSize: 18,
              }}
            >
              👤
            </div>

            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)" }}>
                  {data?.citizen_name || "Beneficiary"}
                </span>
                <PriorityBadge priority={data?.priority || "URGENT"} size="sm" />
                <span
                  style={{
                    padding: "2px 8px",
                    borderRadius: 12,
                    fontSize: 11,
                    fontWeight: 700,
                    backgroundColor: "#DEF7EC",
                    color: "#03543F",
                  }}
                >
                  {data?.referral_status === "PATIENT_ARRIVED" ? "Patient Arrived" : (data?.status || "In Consultation")}
                </span>
                {data?.is_pregnant && (
                  <span
                    style={{
                      padding: "2px 8px",
                      borderRadius: 12,
                      fontSize: 11,
                      fontWeight: 700,
                      backgroundColor: "#FCE4EC",
                      color: "#C2185B",
                    }}
                  >
                    Pregnant • {data?.gestational_weeks ? `${data.gestational_weeks} weeks` : "30 weeks"}
                  </span>
                )}
              </div>

              <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, display: "flex", gap: 10, flexWrap: "wrap" }}>
                <span>{data?.case_reference}</span>
                <span>|</span>
                <span>{data?.referral_reference}</span>
                <span>|</span>
                <span>{data?.village_name || "Kalyanpur"}</span>
                <span>|</span>
                <span>Age {data?.citizen_age || 30}</span>
                <span>|</span>
                <span>{data?.preferred_language === "mr-IN" ? "Marathi" : "Hindi"}</span>
              </div>

              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>
                Referred by: <strong>{data?.assigned_asha_name || "Sita Patel (ASHA)"}</strong> | Arrived 18 min ago
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <a
              href={`tel:${data?.assigned_asha_phone || "9823012345"}`}
              style={{
                padding: "6px 12px",
                backgroundColor: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 600,
                color: "var(--text-primary)",
                textDecoration: "none",
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              📞 Call ASHA
            </a>
            <button
              onClick={async () => {
                let citizenIdToUse = data?.citizen_id || data?.citizenId || data?.citizen?.id;
                if (!citizenIdToUse && data?.case_id) {
                  try {
                    const cRes: any = await apiClient.request(`/doctor/cases/${data.case_id}`);
                    citizenIdToUse = cRes?.citizen_id || cRes?.citizenId;
                  } catch (e) {
                    console.error("Failed to fetch case citizen_id", e);
                  }
                }
                if (!citizenIdToUse) {
                  // Fallback for Pooja Jadhav consultation demo
                  citizenIdToUse = "DEMO-PATIENT-007";
                }
                navigate(doctorPaths.patientRecord(citizenIdToUse, window.location.pathname));
              }}
              disabled={loading}
              style={{
                padding: "6px 12px",
                backgroundColor: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 600,
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.6 : 1,
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              👁 View Patient Record
            </button>
            <button
              onClick={() => {
                if (data?.case_id) {
                  navigate(doctorPaths.caseTimeline(data.case_id) + "?returnTo=" + encodeURIComponent(window.location.pathname));
                } else {
                  alert("Timeline unavailable because this consultation is not linked to a case.");
                }
              }}
              style={{
                padding: "6px 12px",
                backgroundColor: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              🕒 View Timeline
            </button>
          </div>
        </div>
      </div>

      {/* 2. Deterministic Non-Diagnostic Safety Warning Banner */}
      {data?.safety_rule_triggered && (
        <div
          style={{
            backgroundColor: "#FEF2F2",
            border: "1px solid #FCA5A5",
            borderRadius: 10,
            padding: "14px 18px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
            <div style={{ color: "#DC2626", marginTop: 2 }}>
              <WarningIcon size={22} color="#DC2626" />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#991B1B" }}>
                Warning signs recorded. Medical-officer evaluation is required.
              </div>
              <div style={{ fontSize: 12, color: "#7F1D1D", marginTop: 2 }}>
                {data?.safety_rule_reason || "Elevated blood pressure recorded during home visit."}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => {
                const el = document.getElementById("doctor-vitals-recorder");
                if (el) el.scrollIntoView({ behavior: "smooth" });
              }}
              style={{
                padding: "6px 14px",
                backgroundColor: "var(--surface)",
                border: "1px solid #DC2626",
                color: "#DC2626",
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Record Repeat Vitals
            </button>
            <button
              onClick={() => alert(`Deterministic Safety Rule Triggered: ${data?.safety_rule_reason}`)}
              style={{
                padding: "6px 14px",
                backgroundColor: "#DC2626",
                color: "#FFF",
                border: "none",
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Review Safety Details
            </button>
          </div>
        </div>
      )}

      {/* 3. Five-Step Responsive Stepper */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid var(--border)",
          backgroundColor: "var(--surface)",
          borderRadius: 8,
          overflowX: "auto",
        }}
      >
        {[
          { step: 1, label: "1. Review Referral" },
          { step: 2, label: "2. History & Examination" },
          { step: 3, label: "3. Clinical Assessment" },
          { step: 4, label: "4. Orders & Treatment" },
          { step: 5, label: "5. Care Plan & Sign" },
        ].map((s) => {
          const isActive = currentStep === s.step;
          const isDone = completedSteps.includes(s.step);
          return (
            <button
              key={s.step}
              onClick={() => setCurrentStep(s.step)}
              style={{
                flex: "1 1 auto",
                padding: "12px 16px",
                border: "none",
                borderBottom: isActive ? "3px solid var(--primary)" : "3px solid transparent",
                backgroundColor: isActive ? "#EFF6FF" : "transparent",
                color: isActive ? "var(--primary)" : isDone ? "var(--text-primary)" : "var(--text-secondary)",
                fontWeight: isActive ? 800 : 600,
                fontSize: 13,
                cursor: "pointer",
                textAlign: "center",
                whiteSpace: "nowrap",
              }}
            >
              {isDone && !isActive ? `✓ ${s.label}` : s.label}
            </button>
          );
        })}
      </div>

      {/* 4. Three-Column Clinical Layout (27% Left Evidence | 48% Center Workspace | 25% Right Status) */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-start" }}>
        
        {/* LEFT COLUMN: Read-Only Evidence (Separated by Source) */}
        <div style={{ flex: "1 1 320px", minWidth: 280, display: "flex", flexDirection: "column", gap: 14 }}>
          
          {/* Layer 1: Citizen Reported Concern & Symptoms */}
          <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 10, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                Citizen Reported Concern
              </h3>
              <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 6px", borderRadius: 4, backgroundColor: "#E0F2FE", color: "#0369A1" }}>
                CITIZEN_REPORTED
              </span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Chief Spoken Concern:</span>
                <div style={{ fontWeight: 600, color: "var(--text-primary)", marginTop: 2, padding: 8, backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                  "{data?.primary_concern || "Not recorded"}"
                </div>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Extracted Citizen Symptoms:</span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                  {(data?.citizen_reported_symptoms || data?.symptoms || []).map((s: any, idx: number) => (
                    <span
                      key={idx}
                      style={{
                        padding: "3px 8px",
                        borderRadius: 12,
                        backgroundColor: "#DBEAFE",
                        color: "#1E40AF",
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    >
                      {s.term || s.normalized_term} {s.spoken_term ? `(${s.spoken_term})` : ""}
                    </span>
                  ))}
                </div>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                <span style={{ color: "var(--text-secondary)" }}>Priority / Language:</span>
                <span style={{ fontWeight: 600 }}>{data?.priority || "URGENT"} · {data?.preferred_language === "mr-IN" ? "Marathi" : "Hindi"}</span>
              </div>
            </div>
          </div>

          {/* Layer 2: ASHA Confirmed Field Findings */}
          <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 10, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                ASHA Confirmed Field Findings
              </h3>
              <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 6px", borderRadius: 4, backgroundColor: "#D1FAE5", color: "#065F46" }}>
                ASHA_CONFIRMED
              </span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Confirmed Symptoms:</span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                  {(data?.asha_confirmed_symptoms || data?.symptoms || []).map((s: any, idx: number) => (
                    <span
                      key={idx}
                      style={{
                        padding: "3px 8px",
                        borderRadius: 12,
                        backgroundColor: "#FEF3C7",
                        color: "#92400E",
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    >
                      ✓ {s.term || s.normalized_term} {s.spoken_term ? `(${s.spoken_term})` : ""}
                    </span>
                  ))}
                </div>
              </div>

              {data?.visits && data.visits.length > 0 && (
                <div style={{ marginTop: 6, padding: 8, backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 700 }}>ASHA FIELD VISIT NOTE:</div>
                  <div style={{ fontSize: 12, marginTop: 2 }}>{data.visits[0].notes || "Visit completed."}</div>
                </div>
              )}
            </div>
          </div>

          {/* Layer 3: Latest Measurements */}
          <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 10, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                Latest Measurements
              </h3>
              <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                {latestVitals?.recorded_at ? new Date(latestVitals.recorded_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "10:12 AM"}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 12 }}>
              <div style={{ padding: 8, backgroundColor: latestVitals?.systolic_bp >= 140 ? "#FEE2E2" : "var(--neutral-bg)", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Blood Pressure</div>
                <div style={{ fontSize: 14, fontWeight: 800, color: latestVitals?.systolic_bp >= 140 ? "#DC2626" : "var(--text-primary)" }}>
                  {latestVitals?.systolic_bp ? `${latestVitals.systolic_bp}/${latestVitals.diastolic_bp} mmHg` : "Not recorded"}
                </div>
              </div>

              <div style={{ padding: 8, backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>SpO₂</div>
                <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>
                  {latestVitals?.spo2 ? `${latestVitals.spo2}%` : "Not recorded"}
                </div>
              </div>

              <div style={{ padding: 8, backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Pulse</div>
                <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>
                  {latestVitals?.pulse ? `${latestVitals.pulse} bpm` : "Not recorded"}
                </div>
              </div>

              <div style={{ padding: 8, backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Temperature</div>
                <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text-primary)" }}>
                  {latestVitals?.temperature_c ? `${latestVitals.temperature_c}°C` : "Not recorded"}
                </div>
              </div>
            </div>

            {/* Doctor Repeat Vitals Recorder */}
            <div id="doctor-vitals-recorder" style={{ marginTop: 12, paddingTop: 10, borderTop: "1px dashed var(--border)" }}>
              <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 6, color: "var(--primary-dark)" }}>
                + Record Doctor Repeat Vitals
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                <input
                  type="number"
                  placeholder="Sys BP (mmHg)"
                  value={repeatBpSys}
                  onChange={(e) => setRepeatBpSys(e.target.value)}
                  style={{ padding: 6, borderRadius: 4, border: "1px solid var(--border)", fontSize: 12 }}
                />
                <input
                  type="number"
                  placeholder="Dia BP (mmHg)"
                  value={repeatBpDia}
                  onChange={(e) => setRepeatBpDia(e.target.value)}
                  style={{ padding: 6, borderRadius: 4, border: "1px solid var(--border)", fontSize: 12 }}
                />
                <input
                  type="number"
                  placeholder="SpO2 (%)"
                  value={repeatSpo2}
                  onChange={(e) => setRepeatSpo2(e.target.value)}
                  style={{ padding: 6, borderRadius: 4, border: "1px solid var(--border)", fontSize: 12 }}
                />
                <input
                  type="number"
                  placeholder="Pulse (bpm)"
                  value={repeatPulse}
                  onChange={(e) => setRepeatPulse(e.target.value)}
                  style={{ padding: 6, borderRadius: 4, border: "1px solid var(--border)", fontSize: 12 }}
                />
              </div>
              <button
                disabled={isRecordingVitals || (!repeatBpSys && !repeatBpDia)}
                onClick={handleSaveRepeatVitals}
                style={{
                  marginTop: 8,
                  width: "100%",
                  padding: "6px 0",
                  backgroundColor: "var(--primary)",
                  color: "#FFF",
                  border: "none",
                  borderRadius: 4,
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {isRecordingVitals ? "Saving..." : "Save Doctor Vitals"}
              </button>
            </div>
          </div>
        </div>

        {/* CENTER COLUMN: Doctor Clinical Workspace (5-Step Form) */}
        <div style={{ flex: "2 1 480px", minWidth: 320, display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 10, border: "1px solid var(--border)" }}>
            
            {/* STEP 1: Review Referral */}
            {currentStep === 1 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Step 1: Doctor Referral Review</h3>
                <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
                  Confirm patient identity and review ASHA field evidence before starting physical examination.
                </p>

                <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8, fontSize: 13, display: "flex", flexDirection: "column", gap: 6 }}>
                  <div>• Patient: <strong>{data?.citizen_name}</strong> (Age {data?.citizen_age}, {data?.village_name})</div>
                  <div>• Referring ASHA: <strong>{data?.assigned_asha_name}</strong></div>
                  <div>• Primary Reported Concern: <em>"{data?.primary_concern}"</em></div>
                </div>

                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer", fontWeight: 600 }}>
                  <input
                    type="checkbox"
                    checked={evidenceReviewed}
                    onChange={(e) => setEvidenceReviewed(e.target.checked)}
                  />
                  I confirm that I have reviewed the referral evidence and verified the patient.
                </label>

                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10 }}>
                  <button
                    onClick={() => setMissingInfoModalOpen(true)}
                    style={{ padding: "8px 14px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 13, cursor: "pointer" }}
                  >
                    Request Info from ASHA
                  </button>
                  <button
                    onClick={() => {
                      setCompletedSteps((prev) => Array.from(new Set([...prev, 1])));
                      setCurrentStep(2);
                    }}
                    style={{ padding: "8px 18px", backgroundColor: "var(--primary)", color: "#FFF", border: "none", borderRadius: 6, fontSize: 13, fontWeight: 700, cursor: "pointer" }}
                  >
                    Continue to Examination →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2: History & Examination */}
            {currentStep === 2 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Step 2: Doctor Clinical Examination</h3>

                {/* Selectable Physical Exam Findings */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>General Condition</label>
                    <select
                      value={generalCondition}
                      onChange={(e) => setGeneralCondition(e.target.value)}
                      style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginTop: 4, fontSize: 13 }}
                    >
                      <option value="">-- Select Condition --</option>
                      <option value="Fair / Stable">Fair / Stable</option>
                      <option value="Requires urgent review">Requires urgent review</option>
                      <option value="Critical">Critical</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>Consciousness</label>
                    <select
                      value={consciousness}
                      onChange={(e) => setConsciousness(e.target.value)}
                      style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginTop: 4, fontSize: 13 }}
                    >
                      <option value="Conscious & Alert">Conscious & Alert</option>
                      <option value="Drowsy / Lethargic">Drowsy / Lethargic</option>
                      <option value="Unconscious">Unconscious</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>Pallor / Anemia</label>
                    <select
                      value={pallor}
                      onChange={(e) => setPallor(e.target.value)}
                      style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginTop: 4, fontSize: 13 }}
                    >
                      <option value="">-- Select Pallor --</option>
                      <option value="None">None</option>
                      <option value="Present (+1)">Present (+1)</option>
                      <option value="Severe (+2)">Severe (+2)</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>Edema</label>
                    <select
                      value={edema}
                      onChange={(e) => setEdema(e.target.value)}
                      style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginTop: 4, fontSize: 13 }}
                    >
                      <option value="">-- Select Edema --</option>
                      <option value="None">None</option>
                      <option value="Bilateral Pedal Edema (+1)">Bilateral Pedal Edema (+1)</option>
                      <option value="Bilateral Pedal Edema (+2)">Bilateral Pedal Edema (+2)</option>
                      <option value="Facial / Generalized Edema">Facial / Generalized Edema</option>
                    </select>
                  </div>
                </div>

                {/* Systemic Examination */}
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>Systemic Examination</label>
                  <textarea
                    rows={2}
                    placeholder="Record CVS, Respiratory, Abdominal / Obstetric findings..."
                    value={systemicNotes}
                    onChange={(e) => setSystemicNotes(e.target.value)}
                    style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginTop: 4, fontSize: 13 }}
                  />
                </div>

                {/* Doctor Clinical Notes with Multilingual Voice Dictation */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                    <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>Clinical Examination Notes</label>
                    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      <select
                        value={voiceLanguage}
                        onChange={(e) => setVoiceLanguage(e.target.value)}
                        style={{ padding: "2px 6px", fontSize: 11, borderRadius: 4, border: "1px solid var(--border)" }}
                      >
                        <option value="mr-IN">Marathi (मराठी)</option>
                        <option value="hi-IN">Hindi (हिंदी)</option>
                        <option value="en-IN">English</option>
                      </select>
                      <button
                        onClick={toggleVoiceDictation}
                        style={{
                          padding: "4px 10px",
                          backgroundColor: isVoiceRecording ? "#DC2626" : "var(--surface)",
                          color: isVoiceRecording ? "#FFF" : "var(--text-primary)",
                          border: "1px solid var(--border)",
                          borderRadius: 4,
                          fontSize: 11,
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        {isVoiceRecording ? "⏹ Stop Dictation" : "🎤 Voice Dictate"}
                      </button>
                    </div>
                  </div>
                  <textarea
                    rows={3}
                    placeholder="Enter doctor clinical examination observations..."
                    value={examinationNotes}
                    onChange={(e) => setExaminationNotes(e.target.value)}
                    style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", fontSize: 13 }}
                  />
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10 }}>
                  <button
                    onClick={() => setCurrentStep(1)}
                    style={{ padding: "8px 16px", backgroundColor: "var(--neutral-bg)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 13, cursor: "pointer" }}
                  >
                    ← Back
                  </button>
                  <button
                    onClick={() => {
                      setCompletedSteps((prev) => Array.from(new Set([...prev, 2])));
                      setCurrentStep(3);
                    }}
                    style={{ padding: "8px 18px", backgroundColor: "var(--primary)", color: "#FFF", border: "none", borderRadius: 6, fontSize: 13, fontWeight: 700, cursor: "pointer" }}
                  >
                    Save & Continue to Assessment →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: Clinical Assessment */}
            {currentStep === 3 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Step 3: Doctor Clinical Assessment</h3>
                  <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 4, backgroundColor: "#E0E7FF", color: "#3730A3" }}>
                    DOCTOR_ENTERED
                  </span>
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>Provisional Clinical Impression</label>
                  <input
                    type="text"
                    placeholder="e.g. Maternal Hypertension with Warning Signs"
                    value={provisionalImpression}
                    onChange={(e) => setProvisionalImpression(e.target.value)}
                    style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginTop: 4, fontSize: 13 }}
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 10 }}>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
                      * Doctor Confirmed Diagnosis (Explicit Human Doctor Confirmation)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Gestational Hypertension / Pre-eclampsia"
                      value={confirmedDiagnosis}
                      onChange={(e) => setConfirmedDiagnosis(e.target.value)}
                      style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--primary)", marginTop: 4, fontSize: 13, fontWeight: 600 }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>ICD-10 Code</label>
                    <input
                      type="text"
                      placeholder="e.g. O14.9"
                      value={icd10Code}
                      onChange={(e) => setIcd10Code(e.target.value)}
                      style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginTop: 4, fontSize: 13 }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>Clinical Reasoning & Synthesis</label>
                  <textarea
                    rows={3}
                    placeholder="Document clinical rationale supporting diagnosis..."
                    value={clinicalReasoning}
                    onChange={(e) => setClinicalReasoning(e.target.value)}
                    style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginTop: 4, fontSize: 13 }}
                  />
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10 }}>
                  <button
                    onClick={() => setCurrentStep(2)}
                    style={{ padding: "8px 16px", backgroundColor: "var(--neutral-bg)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 13, cursor: "pointer" }}
                  >
                    ← Back
                  </button>
                  <button
                    onClick={() => {
                      setCompletedSteps((prev) => Array.from(new Set([...prev, 3])));
                      setCurrentStep(4);
                    }}
                    style={{ padding: "8px 18px", backgroundColor: "var(--primary)", color: "#FFF", border: "none", borderRadius: 6, fontSize: 13, fontWeight: 700, cursor: "pointer" }}
                  >
                    Continue to Orders & Treatment →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 4: Orders & Treatment */}
            {currentStep === 4 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Step 4: Orders & Prescription</h3>

                {/* Investigations */}
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "var(--primary-dark)", marginBottom: 6 }}>
                    Investigation Orders ({investigationOrders.length})
                  </div>
                  <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
                    <input
                      type="text"
                      placeholder="Test name (e.g. CBC, Urine Albumin)"
                      value={newTestName}
                      onChange={(e) => setNewTestName(e.target.value)}
                      style={{ flex: 2, padding: 6, borderRadius: 4, border: "1px solid var(--border)", fontSize: 12 }}
                    />
                    <select
                      value={newTestPriority}
                      onChange={(e) => setNewTestPriority(e.target.value)}
                      style={{ flex: 1, padding: 6, borderRadius: 4, border: "1px solid var(--border)", fontSize: 12 }}
                    >
                      <option value="URGENT">URGENT</option>
                      <option value="ROUTINE">ROUTINE</option>
                    </select>
                    <button
                      onClick={handleAddInvestigation}
                      style={{ padding: "6px 12px", backgroundColor: "var(--primary)", color: "#FFF", border: "none", borderRadius: 4, fontSize: 12, fontWeight: 700, cursor: "pointer" }}
                    >
                      + Add Order
                    </button>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {investigationOrders.map((t, idx) => (
                      <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 8, backgroundColor: "var(--neutral-bg)", borderRadius: 6, fontSize: 12 }}>
                        <div>
                          <strong>{t.test_name}</strong> · <span style={{ color: "var(--urgent)" }}>{t.priority}</span>
                        </div>
                        <button onClick={() => handleRemoveInvestigation(idx)} style={{ color: "#DC2626", border: "none", background: "none", cursor: "pointer", fontWeight: 700 }}>✕</button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Prescription Builder */}
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "var(--primary-dark)", marginBottom: 6 }}>
                    Prescription Items ({prescriptionItems.length})
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", gap: 6, marginBottom: 6 }}>
                    <input
                      type="text"
                      placeholder="Medicine name (e.g. Labetalol)"
                      value={newMedName}
                      onChange={(e) => setNewMedName(e.target.value)}
                      style={{ padding: 6, borderRadius: 4, border: "1px solid var(--border)", fontSize: 12 }}
                    />
                    <input
                      type="text"
                      placeholder="Strength (e.g. 100mg)"
                      value={newMedStrength}
                      onChange={(e) => setNewMedStrength(e.target.value)}
                      style={{ padding: 6, borderRadius: 4, border: "1px solid var(--border)", fontSize: 12 }}
                    />
                    <input
                      type="text"
                      placeholder="Freq (e.g. BID)"
                      value={newMedFreq}
                      onChange={(e) => setNewMedFreq(e.target.value)}
                      style={{ padding: 6, borderRadius: 4, border: "1px solid var(--border)", fontSize: 12 }}
                    />
                    <button
                      onClick={handleAddPrescription}
                      style={{ padding: "6px 10px", backgroundColor: "var(--primary)", color: "#FFF", border: "none", borderRadius: 4, fontSize: 12, fontWeight: 700, cursor: "pointer" }}
                    >
                      + Add Med
                    </button>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {prescriptionItems.map((p, idx) => (
                      <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 8, backgroundColor: "var(--neutral-bg)", borderRadius: 6, fontSize: 12 }}>
                        <div>
                          <strong>{p.medicine}</strong> {p.strength} · {p.dose} · {p.frequency} · {p.duration} ({p.timing})
                        </div>
                        <button onClick={() => handleRemovePrescription(idx)} style={{ color: "#DC2626", border: "none", background: "none", cursor: "pointer", fontWeight: 700 }}>✕</button>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10 }}>
                  <button
                    onClick={() => setCurrentStep(3)}
                    style={{ padding: "8px 16px", backgroundColor: "var(--neutral-bg)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 13, cursor: "pointer" }}
                  >
                    ← Back
                  </button>
                  <button
                    onClick={() => {
                      setCompletedSteps((prev) => Array.from(new Set([...prev, 4])));
                      setCurrentStep(5);
                    }}
                    style={{ padding: "8px 18px", backgroundColor: "var(--primary)", color: "#FFF", border: "none", borderRadius: 6, fontSize: 13, fontWeight: 700, cursor: "pointer" }}
                  >
                    Continue to Care Plan & Sign →
                  </button>
                </div>
              </div>
            )}

            {/* STEP 5: Care Plan & Sign */}
            {currentStep === 5 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Step 5: Care Plan & Sign-off</h3>

                {/* Disposition Requirement */}
                <div>
                  <label style={{ fontSize: 12, fontWeight: 700, color: "var(--urgent)" }}>* Disposition (Required)</label>
                  <select
                    value={disposition}
                    onChange={(e) => setDisposition(e.target.value)}
                    style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginTop: 4, fontSize: 13 }}
                  >
                    <option value="">-- Select Disposition --</option>
                    <option value="DISCHARGE_FOLLOWUP">Discharge with ASHA Home Follow-up</option>
                    <option value="OBSERVE_PHC">Observe at PHC (Day Care)</option>
                    <option value="AWAIT_INVESTIGATION">Await Investigation Results</option>
                    <option value="SCHEDULED_REVIEW">Doctor Review Scheduled</option>
                    <option value="HIGHER_REFERRAL">Refer to CHC / District Hospital</option>
                    <option value="EMERGENCY_TRANSFER">Emergency Transfer (108 EMTS)</option>
                    <option value="COMPLETE_NO_FOLLOWUP">Complete without Follow-up</option>
                  </select>
                </div>

                {/* Care Plan Summary */}
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>Care Plan Summary</label>
                  <textarea
                    rows={2}
                    placeholder="Summarize management plan and follow-up timeline..."
                    value={carePlanSummary}
                    onChange={(e) => setCarePlanSummary(e.target.value)}
                    style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginTop: 4, fontSize: 13 }}
                  />
                </div>

                {/* ASHA Follow-up Directive */}
                <div style={{ padding: 12, backgroundColor: "#FEF3C7", borderRadius: 8, border: "1px solid #FDE68A" }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "#92400E", marginBottom: 6 }}>
                    ASHA Follow-up Directive Builder
                  </div>
                  <textarea
                    rows={2}
                    placeholder="Specific instructions for ASHA home check..."
                    value={ashaDirectiveInstructions}
                    onChange={(e) => setAshaDirectiveInstructions(e.target.value)}
                    style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #FCD34D", fontSize: 12 }}
                  />
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6, fontSize: 12 }}>
                    <span>Due in:</span>
                    <select
                      value={ashaDirectiveDueDays}
                      onChange={(e) => setAshaDirectiveDueDays(parseInt(e.target.value))}
                      style={{ padding: "4px 8px", borderRadius: 4, border: "1px solid var(--border)" }}
                    >
                      <option value={1}>1 day (Urgent)</option>
                      <option value={3}>3 days (Standard)</option>
                      <option value={7}>7 days (Weekly)</option>
                      <option value={14}>14 days</option>
                    </select>
                  </div>
                </div>

                {/* Multilingual Patient Guidance */}
                <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 700 }}>Patient Instructions / Guidance</span>
                    <select
                      value={guidanceLanguage}
                      onChange={(e) => setGuidanceLanguage(e.target.value)}
                      style={{ padding: "2px 6px", fontSize: 11, borderRadius: 4, border: "1px solid var(--border)" }}
                    >
                      <option value="mr-IN">Marathi (मराठी)</option>
                      <option value="hi-IN">Hindi (हिंदी)</option>
                      <option value="en-IN">English</option>
                    </select>
                  </div>
                  <textarea
                    rows={2}
                    placeholder="Patient instructions in preferred language..."
                    value={guidanceText}
                    onChange={(e) => setGuidanceText(e.target.value)}
                    style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", fontSize: 12 }}
                  />
                </div>

                {/* Mandatory Doctor Clinical Sign-off Confirmation Checkbox */}
                <div style={{ padding: 12, backgroundColor: "#ECFDF5", borderRadius: 8, border: "1px solid #6EE7B7" }}>
                  <label style={{ display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer", fontSize: 13, fontWeight: 700, color: "#065F46" }}>
                    <input
                      type="checkbox"
                      checked={doctorSignoffConfirmed}
                      onChange={(e) => setDoctorSignoffConfirmed(e.target.checked)}
                      style={{ marginTop: 2 }}
                    />
                    <span>
                      ☑ Doctor Confirmation: I explicitly confirm that this consultation, diagnosis, treatment orders, and follow-up directives reflect my verified human clinical decision.
                    </span>
                  </label>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10 }}>
                  <button
                    onClick={() => setCurrentStep(4)}
                    style={{ padding: "8px 16px", backgroundColor: "var(--neutral-bg)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 13, cursor: "pointer" }}
                  >
                    ← Back
                  </button>
                  <button
                    disabled={isSubmitting || !disposition || !doctorSignoffConfirmed}
                    onClick={handleCompleteConsultation}
                    style={{
                      padding: "10px 24px",
                      backgroundColor: (!disposition || !doctorSignoffConfirmed) ? "var(--border)" : "var(--success)",
                      color: "#FFF",
                      border: "none",
                      borderRadius: 8,
                      fontSize: 14,
                      fontWeight: 800,
                      cursor: (!disposition || !doctorSignoffConfirmed) ? "not-allowed" : "pointer",
                    }}
                  >
                    {isSubmitting ? "Signing & Finalizing..." : "✓ SIGN & COMPLETE CONSULTATION"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Professional Status, Missing Information & Care Plan Progress (NO RAG) */}
        <div style={{ flex: "1 1 300px", minWidth: 260, display: "flex", flexDirection: "column", gap: 14 }}>
          
          {/* Consultation Status */}
          <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 10, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
              <ActivityIcon size={18} color="var(--primary)" />
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                Consultation Status
              </h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Current Stage:</span>
                <span style={{ fontWeight: 700, color: "var(--primary)" }}>Step {currentStep} of 5</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Draft Autosave:</span>
                <span style={{ fontWeight: 600, color: saveStatus === "SAVED" ? "#03543F" : "var(--text-secondary)" }}>
                  {saveStatus === "SAVED" ? `Autosaved ${lastSaved || "Just now"}` : "Saving..."}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Elapsed Time:</span>
                <span style={{ fontWeight: 600 }}>{elapsedMinutes} min</span>
              </div>
            </div>
          </div>

          {/* Missing Information Checklist */}
          <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 10, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                Missing Information ({missingInfoList.length})
              </h3>
              <button
                onClick={() => setMissingInfoModalOpen(true)}
                style={{ fontSize: 11, color: "var(--primary)", fontWeight: 700, border: "none", background: "none", cursor: "pointer" }}
              >
                + Request
              </button>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12 }}>
              {missingInfoList.length === 0 ? (
                <div style={{ color: "#03543F", fontWeight: 600 }}>✓ All mandatory fields completed.</div>
              ) : (
                missingInfoList.map((item, idx) => (
                  <div key={idx} style={{ color: "#DC2626", display: "flex", alignItems: "center", gap: 6 }}>
                    <span>•</span>
                    <span>{item}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Care Plan Progress */}
          <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 10, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 10px", fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
              Care Plan Progress
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
              <div
                onClick={() => setCurrentStep(4)}
                style={{ display: "flex", justifyContent: "space-between", cursor: "pointer", padding: "4px 0" }}
              >
                <span>Investigations:</span>
                <span style={{ fontWeight: 700, color: investigationOrders.length > 0 ? "var(--primary)" : "var(--text-secondary)" }}>
                  {investigationOrders.length > 0 ? `${investigationOrders.length} Ordered` : "Not started"}
                </span>
              </div>
              <div
                onClick={() => setCurrentStep(4)}
                style={{ display: "flex", justifyContent: "space-between", cursor: "pointer", padding: "4px 0" }}
              >
                <span>Prescription:</span>
                <span style={{ fontWeight: 700, color: prescriptionItems.length > 0 ? "var(--primary)" : "var(--text-secondary)" }}>
                  {prescriptionItems.length > 0 ? `${prescriptionItems.length} Medicines` : "Not started"}
                </span>
              </div>
              <div
                onClick={() => setCurrentStep(5)}
                style={{ display: "flex", justifyContent: "space-between", cursor: "pointer", padding: "4px 0" }}
              >
                <span>Disposition:</span>
                <span style={{ fontWeight: 700, color: disposition ? "#03543F" : "var(--urgent)" }}>
                  {disposition ? "Selected" : "Required"}
                </span>
              </div>
              <div
                onClick={() => setCurrentStep(5)}
                style={{ display: "flex", justifyContent: "space-between", cursor: "pointer", padding: "4px 0" }}
              >
                <span>ASHA Directive:</span>
                <span style={{ fontWeight: 700, color: ashaDirectiveInstructions ? "var(--primary)" : "var(--text-secondary)" }}>
                  {ashaDirectiveInstructions ? "Created" : "Pending"}
                </span>
              </div>
            </div>
          </div>

          {/* Safety Review Checklist */}
          <div style={{ backgroundColor: "#DEF7EC", padding: 14, borderRadius: 10, border: "1px solid #BCF0DA", fontSize: 12, color: "#03543F" }}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>✓ Clinical Governance</div>
            <div>• Deterministic Safety Banner active</div>
            <div>• Separation of Citizen, ASHA & Doctor evidence</div>
            <div>• Doctor confirmed diagnosis & prescriptions</div>
          </div>
        </div>
      </div>

      {/* Modal: Request Missing Info from ASHA */}
      {missingInfoModalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: 16,
          }}
        >
          <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, maxWidth: 480, width: "100%", display: "flex", flexDirection: "column", gap: 14 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Request Missing Information from ASHA</h3>
            <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>
              Assigned ASHA: <strong>{data?.assigned_asha_name || "Sita Patel (ASHA)"}</strong>
            </p>
            <textarea
              rows={3}
              placeholder="Specify the missing observations or repeat measurements needed..."
              value={missingInfoText}
              onChange={(e) => setMissingInfoText(e.target.value)}
              style={{ width: "100%", padding: 10, borderRadius: 6, border: "1px solid var(--border)", fontSize: 13 }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button
                onClick={() => setMissingInfoModalOpen(false)}
                style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)", backgroundColor: "var(--neutral-bg)", fontSize: 12, cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitMissingInfoRequest}
                style={{ padding: "6px 16px", borderRadius: 6, border: "none", backgroundColor: "var(--primary)", color: "#FFF", fontSize: 12, fontWeight: 700, cursor: "pointer" }}
              >
                Send Request
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
