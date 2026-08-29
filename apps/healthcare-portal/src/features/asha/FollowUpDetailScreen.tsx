import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge } from "../../components/StatusBadge";
import { VoiceInputModal } from "../../components/VoiceInputModal";
import { ashaSyncService } from "../../services/AshaSyncService";
import { useAuth } from "../../auth/AuthContext";
import { doctorPaths } from "../doctor/doctorRoutes";
import { useLanguage } from "@aarogya/i18n";

export function FollowUpDetailScreen() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const { t } = useLanguage();

  const isDoctorView = location.pathname.startsWith("/doctor/") || searchParams.get("view") === "doctor" || (user && (user.role === "PHC_DOCTOR" || String(user.role).includes("DOCTOR")));

  const [fup, setFup] = useState<any>(null);
  const [escalation, setEscalation] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDrafting, setIsDrafting] = useState(false);
  const [draftSavedMessage, setDraftSavedMessage] = useState<string | null>(null);

  // Doctor Action Modal States
  const [showDoctorActionModal, setShowDoctorActionModal] = useState(false);
  const [actionType, setActionType] = useState<"REQUEST_PATIENT_TO_PHC" | "REPEAT_FOLLOWUP">("REQUEST_PATIENT_TO_PHC");
  const [actionNotes, setActionNotes] = useState("");
  
  const [showDoctorResolveModal, setShowDoctorResolveModal] = useState(false);
  const [resolveNotes, setResolveNotes] = useState("");
  const [resolveOutcome, setResolveOutcome] = useState("RESOLVED_SATISFACTORILY");

  const [showDoctorReviewModal, setShowDoctorReviewModal] = useState(false);
  const [doctorReviewNote, setDoctorReviewNote] = useState("Result reviewed. No immediate clinical escalation required.");

  const [showDoctorRescheduleModal, setShowDoctorRescheduleModal] = useState(false);
  const [doctorRescheduleDate, setDoctorRescheduleDate] = useState("");
  const [doctorRescheduleReason, setDoctorRescheduleReason] = useState("");

  const [showDoctorCancelModal, setShowDoctorCancelModal] = useState(false);
  const [doctorCancelReason, setDoctorCancelReason] = useState("");

  // Form State for completing
  const [systolic, setSystolic] = useState<number | "">("");
  const [diastolic, setDiastolic] = useState<number | "">("");
  const [spo2, setSpo2] = useState<number | "">("");
  const [pulse, setPulse] = useState<number | "">("");
  const [randomBloodSugar, setRandomBloodSugar] = useState<number | "">("");
  const [temperature, setTemperature] = useState<number | "">("");
  const [fetalHeartRate, setFetalHeartRate] = useState<number | "">("");
  const [medicationAdherent, setMedicationAdherent] = useState(true);
  const [phcAttended, setPhcAttended] = useState(false);
  const [symptomsImproved, setSymptomsImproved] = useState(true);
  const [symptomsOutcome, setSymptomsOutcome] = useState<"IMPROVED" | "UNCHANGED" | "WORSENED">("IMPROVED");
  const [notes, setNotes] = useState("");
  const [escalate, setEscalate] = useState(false);
  const [showVoiceModal, setShowVoiceModal] = useState(false);

  // Reschedule state
  const [showRescheduleModal, setShowRescheduleModal] = useState(false);
  const [rescheduleDate, setRescheduleDate] = useState("");
  const [rescheduleReason, setRescheduleReason] = useState("");

  // Escalate Modal state
  const [showEscalateModal, setShowEscalateModal] = useState(false);
  const [escalateReason, setEscalateReason] = useState("");
  const [escalateUrgency, setEscalateUrgency] = useState("HIGH");
  const [escalateNotes, setEscalateNotes] = useState("");

  const loadFollowup = async () => {
    if (!id) return;
    try {
      if (isDoctorView) {
        try {
          const escRes = await apiClient.getEscalation(id);
          const escData = escRes?.data || escRes;
          setEscalation(escData);
        } catch (e) {
          console.warn("Escalation record fetch by ID failed, falling back to follow-up details", e);
        }
      }
      const res = await apiClient.getAshaFollowup(id);
      const data = res?.data || res;
      setFup(data);

      if (data?.completion_notes && !notes) {
        setNotes(data.completion_notes);
      }
    } catch (err) {
      console.error("Failed to load follow-up details", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFollowup();
  }, [id]);

  const handleStartFollowUp = async () => {
    try {
      setIsSubmitting(true);
      if (!navigator.onLine) {
        await ashaSyncService.queueAction("UPDATE_FOLLOWUP", fup?.case_id || "", { id, action: "start" });
      } else {
        await apiClient.startAshaFollowup(id!);
      }
      await loadFollowup();
    } catch (err) {
      console.error("Failed to start follow-up", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!id) return;
    setIsDrafting(true);
    setDraftSavedMessage(null);
    try {
      const payload = {
        vitals:
          systolic || diastolic || spo2 || pulse || randomBloodSugar || temperature
            ? {
                systolic_bp: Number(systolic) || undefined,
                diastolic_bp: Number(diastolic) || undefined,
                spo2: Number(spo2) || undefined,
                pulse: Number(pulse) || undefined,
                random_blood_sugar_mg_dl: Number(randomBloodSugar) || undefined,
                temperature_c: Number(temperature) || undefined,
              }
            : undefined,
        medication_adherent: medicationAdherent,
        phc_attended: phcAttended,
        symptoms_improved: symptomsImproved,
        symptoms_outcome: symptomsOutcome,
        notes: notes,
        escalate_to_doctor: escalate,
      };

      if (!navigator.onLine) {
        await ashaSyncService.queueAction("UPDATE_FOLLOWUP", fup?.case_id || "", { id, action: "draft", ...payload });
      } else {
        await apiClient.draftAshaFollowup(id, payload);
      }
      setDraftSavedMessage(t("followups.draft_saved", "Draft saved successfully."));
      setTimeout(() => setDraftSavedMessage(null), 3000);
      await loadFollowup();
    } catch (err) {
      console.error("Failed to save draft", err);
    } finally {
      setIsDrafting(false);
    }
  };

  const handleRescheduleSubmit = async () => {
    if (!rescheduleDate) {
      alert(t("followups.alert_select_date", "Please select a valid new due date."));
      return;
    }
    setIsSubmitting(true);
    try {
      const payload = {
        new_due_date: new Date(rescheduleDate).toISOString(),
        reason: rescheduleReason || "Citizen unavailable/rescheduled by ASHA",
      };

      if (!navigator.onLine) {
        await ashaSyncService.queueAction("RESCHEDULE_FOLLOWUP", fup?.case_id || "", { id, ...payload });
      } else {
        await apiClient.rescheduleAshaFollowup(id!, payload);
      }
      setShowRescheduleModal(false);
      await loadFollowup();
    } catch (err) {
      console.error("Failed to reschedule follow-up", err);
      alert(t("followups.alert_reschedule_failed", "Failed to reschedule follow-up. Please try again."));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEscalateSubmit = async () => {
    if (!escalateReason.trim()) {
      alert(t("followups.alert_provide_reason", "Please provide a reason for doctor escalation."));
      return;
    }
    setIsSubmitting(true);
    try {
      const payload = {
        reason: escalateReason,
        urgency: escalateUrgency,
        notes: escalateNotes,
      };

      if (!navigator.onLine) {
        await ashaSyncService.queueAction("ESCALATE_FOLLOWUP", fup?.case_id || "", { id, ...payload });
      } else {
        await apiClient.escalateAshaFollowup(id!, payload);
      }
      setShowEscalateModal(false);
      navigate("/asha/followups");
    } catch (err) {
      console.error("Failed to escalate follow-up", err);
      alert(t("followups.alert_escalate_failed", "Failed to escalate follow-up."));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDoctorAcknowledge = async () => {
    setIsSubmitting(true);
    try {
      const escId = escalation?.escalation_id || id;
      await apiClient.acknowledgeEscalation(escId);
      await loadFollowup();
      alert("Escalation acknowledged successfully.");
    } catch (err) {
      console.error("Failed to acknowledge escalation", err);
      alert("Failed to acknowledge escalation.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDoctorSubmitResolve = async () => {
    if (!resolveNotes.trim()) {
      alert("Please provide clinical resolution notes.");
      return;
    }
    setIsSubmitting(true);
    try {
      const escId = escalation?.escalation_id || id;
      await apiClient.resolveEscalation(escId, {
        resolution_outcome: resolveOutcome,
        resolution_notes: resolveNotes,
      });
      setShowDoctorResolveModal(false);
      await loadFollowup();
      alert("Escalation resolved successfully.");
    } catch (err) {
      console.error("Failed to resolve escalation", err);
      alert("Failed to resolve escalation.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDoctorSubmitReview = async () => {
    if (!doctorReviewNote.trim()) {
      alert("Please enter clinical review notes.");
      return;
    }
    setIsSubmitting(true);
    try {
      const fupId = fup?.id || id;
      await apiClient.reviewDoctorFollowup(fupId, { notes: doctorReviewNote });
      setShowDoctorReviewModal(false);
      await loadFollowup();
      alert("Follow-up marked as clinically reviewed.");
    } catch (err) {
      console.error("Failed to review follow-up", err);
      alert("Failed to submit review.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDoctorSubmitReschedule = async () => {
    if (!doctorRescheduleDate) {
      alert("Please select a new due date.");
      return;
    }
    setIsSubmitting(true);
    try {
      const fupId = fup?.id || id;
      await apiClient.rescheduleDoctorFollowup(fupId, {
        new_due_at: new Date(doctorRescheduleDate).toISOString(),
        reason: doctorRescheduleReason || "Rescheduled by doctor",
      });
      setShowDoctorRescheduleModal(false);
      await loadFollowup();
      alert("Follow-up rescheduled successfully.");
    } catch (err) {
      console.error("Failed to reschedule", err);
      alert("Failed to reschedule follow-up.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDoctorSubmitCancel = async () => {
    if (!doctorCancelReason.trim()) {
      alert("Please enter a cancellation reason.");
      return;
    }
    setIsSubmitting(true);
    try {
      const fupId = fup?.id || id;
      await apiClient.cancelDoctorFollowup(fupId, { reason: doctorCancelReason });
      setShowDoctorCancelModal(false);
      await loadFollowup();
      alert("Follow-up task cancelled.");
      navigate("/doctor/dashboard");
    } catch (err) {
      console.error("Failed to cancel follow-up", err);
      alert("Failed to cancel follow-up task.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleComplete = async () => {
    setIsSubmitting(true);
    try {
      const payload = {
        vitals:
          systolic || diastolic || spo2 || pulse || randomBloodSugar || temperature
            ? {
                systolic_bp: Number(systolic) || undefined,
                diastolic_bp: Number(diastolic) || undefined,
                spo2: Number(spo2) || undefined,
                pulse: Number(pulse) || undefined,
                random_blood_sugar_mg_dl: Number(randomBloodSugar) || undefined,
                temperature_c: Number(temperature) || undefined,
              }
            : undefined,
        medication_adherent: medicationAdherent,
        phc_attended: phcAttended,
        symptoms_improved: symptomsImproved,
        symptoms_outcome: symptomsOutcome,
        notes: notes,
        escalate_to_doctor: escalate,
      };

      if (!navigator.onLine) {
        await ashaSyncService.queueAction("UPDATE_FOLLOWUP", fup?.case_id || "", { id, action: "complete", ...payload });
      } else {
        await apiClient.completeAshaFollowup(id!, payload);
      }

      navigate("/asha/followups");
    } catch (err) {
      console.error("Failed to complete follow-up", err);
      alert(t("followups.alert_complete_failed", "Failed to complete follow-up. Please check fields."));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return <div style={{ padding: 40, textAlign: "center" }}>{t("common.loading", "Loading Follow-up...")}</div>;
  }

  if (!fup) {
    return (
      <div style={{ padding: 40, textAlign: "center" }}>
        <p>{t("followups.not_found", "Follow-up record not found.")}</p>
        <button
          onClick={() => navigate(isDoctorView ? "/doctor/followups" : "/asha/followups")}
          style={{ padding: "8px 16px", backgroundColor: "var(--primary)", color: "#FFF", borderRadius: 8, border: "none", cursor: "pointer" }}
        >
          {t("followups.back_to_list", "Back to Follow-ups")}
        </button>
      </div>
    );
  }

  const isPending = fup.status === "PENDING" || fup.status === "SCHEDULED";
  const isInProgress = fup.status === "IN_PROGRESS";
  const isCompleted = fup.status === "COMPLETED";
  const isEscalated = fup.status === "ESCALATED";
  const isDoctor = ["DOCTOR_DIRECTIVE", "DOCTOR", "DOCTOR_ASSIGNED"].includes(fup.source);

  // Clean doctor name
  const rawDoc = fup.doctor_name || "";
  const cleanDoc = rawDoc.startsWith("Dr.") ? rawDoc : rawDoc ? `Dr. ${rawDoc}` : "";

  // Dynamic vitals context detection
  const taskTypeStr = String(fup.task_type || "").toUpperCase();
  const isMaternal = Boolean(fup.is_pregnant) || taskTypeStr.includes("MATERNAL") || taskTypeStr.includes("ANC");
  const isDiabetic = taskTypeStr.includes("DIABETES") || taskTypeStr.includes("SUGAR") || taskTypeStr.includes("NCD");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 1200, margin: "0 auto" }}>
      {/* Header Banner */}
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <button
          id="btn-back-to-followups"
          onClick={() => navigate(isDoctorView ? "/doctor/followups" : "/asha/followups")}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--primary)",
            fontWeight: 700,
            marginBottom: 16,
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 14,
          }}
        >
          ← {isDoctorView ? "Back to Doctor Queue" : t("followups.back_to_followups", "Back to Follow-ups")}
        </button>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 22, fontWeight: 700 }}>{fup.citizen_name}</span>
              {fup.age && <span style={{ fontSize: 14, color: "var(--text-secondary)" }}>({fup.age}y {fup.gender || ""})</span>}
              {fup.is_pregnant && (
                <span style={{ padding: "2px 8px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                  🤰 Pregnant
                </span>
              )}
              <PriorityBadge priority={fup.priority} size="sm" />
              <span
                style={{
                  padding: "4px 10px",
                  borderRadius: 8,
                  fontSize: 12,
                  fontWeight: 700,
                  backgroundColor: isDoctor ? "#EEF2FF" : "#F0FDF4",
                  color: isDoctor ? "#4338CA" : "#15803D",
                  border: isDoctor ? "1px solid #C7D2FE" : "1px solid #BBF7D0",
                }}
              >
                {isDoctor ? "👩‍⚕️ Doctor Directive" : "🏠 ASHA Scheduled"}
              </span>
              <span
                style={{
                  padding: "4px 10px",
                  borderRadius: 8,
                  fontSize: 12,
                  fontWeight: 700,
                  backgroundColor: isEscalated ? "#FEE2E2" : isPending ? "#FEF3C7" : isInProgress ? "#E0E7FF" : "#DEF7EC",
                  color: isEscalated ? "#991B1B" : isPending ? "#92400E" : isInProgress ? "#3730A3" : "#03543F",
                }}
              >
                {fup.status}
              </span>
            </div>
            <div style={{ fontSize: 14, color: "var(--text-secondary)", display: "flex", gap: 16, flexWrap: "wrap" }}>
              <span>Case: <strong>{fup.case_reference}</strong></span>
              <span>Village: <strong>{fup.village_name}</strong></span>
              <span>Due: <strong>{fup.due_at ? new Date(fup.due_at).toLocaleDateString() : "Not set"}</strong></span>
              {cleanDoc && <span>Doctor: <strong>{cleanDoc}</strong></span>}
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {fup.citizen_phone && (
              <a
                id="btn-call-citizen"
                href={`tel:${fup.citizen_phone}`}
                style={{
                  padding: "10px 16px",
                  backgroundColor: "#E0F2FE",
                  color: "#0369A1",
                  border: "none",
                  borderRadius: 8,
                  fontWeight: 700,
                  fontSize: 13,
                  textDecoration: "none",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  minHeight: 44,
                }}
              >
                📞 {t("followups.call_citizen", "Call")} ({fup.citizen_phone})
              </a>
            )}
            <button
              id="btn-view-case-timeline"
              onClick={() => navigate(`/asha/cases/${encodeURIComponent(fup.case_id)}?tab=timeline&returnTo=${encodeURIComponent(`/asha/followups/${id}`)}`)}
              style={{
                padding: "10px 16px",
                backgroundColor: "var(--neutral-bg)",
                color: "var(--text-primary)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontWeight: 700,
                fontSize: 13,
                cursor: "pointer",
                minHeight: 44,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              🕒 {t("followups.view_timeline", "View Timeline")}
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid Content */}
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
        {/* Left Column: Context & History */}
        <div style={{ flex: 1, minWidth: 320, display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Why this follow-up exists */}
          <div style={{ padding: 20, backgroundColor: isDoctor ? "#EEF2FF" : "var(--primary-light)", borderRadius: 12, border: isDoctor ? "1px solid #C7D2FE" : "1px solid var(--primary-border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, color: isDoctor ? "#312E81" : "var(--primary-dark)" }}>
              {t("followups.directive_title", "Why this follow-up is required")}
            </h3>
            <p style={{ margin: "0 0 8px", fontSize: 14, color: isDoctor ? "#1E1B4B" : "var(--primary-dark)" }}>
              <strong>{t("followups.instructions", "Instructions")}:</strong> {fup.instructions || fup.scheduled_reason || "Monitor patient vitals and treatment adherence."}
            </p>
            {fup.scheduled_reason && (
              <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
                <strong>{t("followups.reason", "Reason")}:</strong> {fup.scheduled_reason}
              </p>
            )}
          </div>

          {/* Previous Clinical Context */}
          <div style={{ padding: 20, backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>
              {t("followups.previous_vitals_title", "Previous Clinical Context")}
            </h3>
            {fup.previous_vitals && fup.previous_vitals.length > 0 ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 10 }}>
                {fup.previous_vitals.map((v: any, i: number) => (
                  <div key={i} style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>
                      Recorded: {v.recorded_at ? new Date(v.recorded_at).toLocaleString() : "Consultation / Visit"}
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 700, display: "flex", gap: 16, flexWrap: "wrap" }}>
                      {v.systolic_bp && <span>BP: {v.systolic_bp}/{v.diastolic_bp} mmHg</span>}
                      {v.pulse && <span>Pulse: {v.pulse} bpm</span>}
                      {v.spo2 && <span>SpO₂: {v.spo2}%</span>}
                      {v.temperature_c && <span>Temp: {v.temperature_c}°C</span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                {t("followups.no_prior_vitals", "No prior vitals recorded for this case.")}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Execution Form / Status Views */}
        <div style={{ flex: 1.4, minWidth: 340, display: "flex", flexDirection: "column", gap: 20 }}>
          {isPending ? (
            <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 20 }}>⏳</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>
                    {t("followups.scheduled_ready_title", "Follow-up is Scheduled")}
                  </h3>
                  <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-secondary)" }}>
                    {t("followups.scheduled_ready_desc", "Begin in-person home assessment or reschedule if patient is unavailable.")}
                  </p>
                </div>
              </div>

              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 8 }}>
                <button
                  id="start-followup-btn"
                  onClick={handleStartFollowUp}
                  disabled={isSubmitting}
                  style={{
                    flex: 1,
                    minWidth: 160,
                    padding: "12px 20px",
                    backgroundColor: "var(--primary)",
                    color: "#FFF",
                    border: "none",
                    borderRadius: 8,
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: "pointer",
                    minHeight: 48,
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 8,
                  }}
                >
                  <span>{isSubmitting ? "Starting..." : "▶ Start Follow-up"}</span>
                </button>
                <button
                  id="reschedule-followup-btn"
                  onClick={() => setShowRescheduleModal(true)}
                  disabled={isSubmitting}
                  style={{
                    padding: "12px 18px",
                    backgroundColor: "var(--surface)",
                    color: "var(--text-primary)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 14,
                    fontWeight: 600,
                    cursor: "pointer",
                    minHeight: 48,
                  }}
                >
                  📅 {t("followups.reschedule", "Reschedule")}
                </button>
                <button
                  id="escalate-modal-open-btn"
                  onClick={() => setShowEscalateModal(true)}
                  disabled={isSubmitting}
                  style={{
                    padding: "12px 18px",
                    backgroundColor: "#FEE2E2",
                    color: "#991B1B",
                    border: "1px solid #FECACA",
                    borderRadius: 8,
                    fontSize: 14,
                    fontWeight: 600,
                    cursor: "pointer",
                    minHeight: 48,
                  }}
                >
                  ⚠️ {t("followups.escalate", "Escalate")}
                </button>
              </div>
            </div>
          ) : isInProgress ? (
            <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 18 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
                  <span>📋</span> {t("followups.assessment_title", "Home Visit Assessment")}
                </h3>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    id="btn-save-draft"
                    type="button"
                    onClick={handleSaveDraft}
                    disabled={isDrafting || isSubmitting}
                    style={{
                      padding: "8px 14px",
                      backgroundColor: "var(--neutral-bg)",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    💾 {isDrafting ? "Saving..." : t("common.save_draft", "Save Draft")}
                  </button>
                </div>
              </div>

              {draftSavedMessage && (
                <div style={{ padding: "8px 12px", backgroundColor: "#DEF7EC", color: "#03543F", borderRadius: 6, fontSize: 13, fontWeight: 600 }}>
                  ✓ {draftSavedMessage}
                </div>
              )}

              {/* Vitals Recording Section */}
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <label style={{ fontSize: 14, fontWeight: 700 }}>
                  {t("followups.repeat_vitals", "Repeat Vital Signs")}
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 12 }}>
                  <div>
                    <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Systolic BP (mmHg)</label>
                    <input
                      id="input-systolic"
                      type="number"
                      placeholder="120"
                      value={systolic}
                      onChange={(e) => setSystolic(e.target.value ? Number(e.target.value) : "")}
                      style={{ width: "100%", padding: 10, borderRadius: 6, border: "1px solid var(--border)", fontWeight: 700 }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Diastolic BP (mmHg)</label>
                    <input
                      id="input-diastolic"
                      type="number"
                      placeholder="80"
                      value={diastolic}
                      onChange={(e) => setDiastolic(e.target.value ? Number(e.target.value) : "")}
                      style={{ width: "100%", padding: 10, borderRadius: 6, border: "1px solid var(--border)", fontWeight: 700 }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>SpO₂ (%)</label>
                    <input
                      id="input-spo2"
                      type="number"
                      placeholder="98"
                      value={spo2}
                      onChange={(e) => setSpo2(e.target.value ? Number(e.target.value) : "")}
                      style={{ width: "100%", padding: 10, borderRadius: 6, border: "1px solid var(--border)", fontWeight: 700 }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Pulse (bpm)</label>
                    <input
                      id="input-pulse"
                      type="number"
                      placeholder="72"
                      value={pulse}
                      onChange={(e) => setPulse(e.target.value ? Number(e.target.value) : "")}
                      style={{ width: "100%", padding: 10, borderRadius: 6, border: "1px solid var(--border)", fontWeight: 700 }}
                    />
                  </div>

                  {/* Patient-Context-Dependent Vitals */}
                  {isDiabetic && (
                    <div>
                      <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Random Glucose (mg/dL)</label>
                      <input
                        id="input-glucose"
                        type="number"
                        placeholder="110"
                        value={randomBloodSugar}
                        onChange={(e) => setRandomBloodSugar(e.target.value ? Number(e.target.value) : "")}
                        style={{ width: "100%", padding: 10, borderRadius: 6, border: "1px solid var(--border)", fontWeight: 700 }}
                      />
                    </div>
                  )}

                  {isMaternal && (
                    <div>
                      <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Fetal Heart Rate (bpm)</label>
                      <input
                        id="input-fhr"
                        type="number"
                        placeholder="140"
                        value={fetalHeartRate}
                        onChange={(e) => setFetalHeartRate(e.target.value ? Number(e.target.value) : "")}
                        style={{ width: "100%", padding: 10, borderRadius: 6, border: "1px solid var(--border)", fontWeight: 700 }}
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Symptom Outcome & Adherence */}
              <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 4 }}>
                <label style={{ fontSize: 14, fontWeight: 700 }}>
                  {t("followups.symptom_progression", "Symptom Status & Adherence")}
                </label>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  {(["IMPROVED", "UNCHANGED", "WORSENED"] as const).map((outcome) => (
                    <button
                      key={outcome}
                      type="button"
                      id={`btn-symptom-${outcome.toLowerCase()}`}
                      onClick={() => {
                        setSymptomsOutcome(outcome);
                        setSymptomsImproved(outcome === "IMPROVED");
                        if (outcome === "WORSENED") setEscalate(true);
                      }}
                      style={{
                        padding: "8px 16px",
                        borderRadius: 8,
                        border: symptomsOutcome === outcome ? "2px solid var(--primary)" : "1px solid var(--border)",
                        backgroundColor: symptomsOutcome === outcome ? "var(--primary-light)" : "var(--surface)",
                        color: symptomsOutcome === outcome ? "var(--primary-dark)" : "var(--text-primary)",
                        fontWeight: 700,
                        fontSize: 13,
                        cursor: "pointer",
                      }}
                    >
                      {outcome === "IMPROVED" ? "🟢 Improved" : outcome === "UNCHANGED" ? "🟡 Unchanged" : "🔴 Worsened"}
                    </button>
                  ))}
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 4 }}>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                    <input
                      id="checkbox-medication"
                      type="checkbox"
                      checked={medicationAdherent}
                      onChange={(e) => setMedicationAdherent(e.target.checked)}
                    />
                    <span>{t("followups.check_medication", "Patient has taken all prescribed medicines on schedule")}</span>
                  </label>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                    <input
                      id="checkbox-phc-attended"
                      type="checkbox"
                      checked={phcAttended}
                      onChange={(e) => setPhcAttended(e.target.checked)}
                    />
                    <span>{t("followups.check_phc_attended", "Patient attended scheduled PHC doctor appointment / lab test")}</span>
                  </label>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer", color: "var(--urgent)", fontWeight: 600 }}>
                    <input
                      id="checkbox-escalate"
                      type="checkbox"
                      checked={escalate}
                      onChange={(e) => setEscalate(e.target.checked)}
                    />
                    <span>⚠️ {t("followups.check_escalate", "Escalate to PHC Medical Officer (Warning signs / Non-response)")}</span>
                  </label>
                </div>
              </div>

              {/* Notes */}
              <div style={{ marginTop: 4 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <label style={{ fontSize: 13, fontWeight: 700 }}>
                    {t("followups.notes_label", "ASHA Observations & Recommendations")}
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowVoiceModal(true)}
                    style={{
                      padding: "4px 10px",
                      backgroundColor: "var(--primary-light)",
                      color: "var(--primary-dark)",
                      border: "1px solid var(--primary)",
                      borderRadius: 6,
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    🎙 {t("followups.speak_notes", "Speak Notes")}
                  </button>
                </div>
                <textarea
                  id="textarea-notes"
                  value={notes}
                  placeholder={t("followups.notes_placeholder", "Record observations regarding recovery, vitals, adherence, or danger signs...")}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
                />
              </div>

              <VoiceInputModal
                isOpen={showVoiceModal}
                onClose={() => setShowVoiceModal(false)}
                preferredLanguage="mr-IN"
                fieldLabel="Follow-up Notes"
                onConfirmText={(text) => setNotes((prev) => (prev ? `${prev} ${text}` : text))}
              />

              <div style={{ display: "flex", gap: 12, marginTop: 10, flexWrap: "wrap" }}>
                <button
                  id="complete-followup-submit-btn"
                  onClick={handleComplete}
                  disabled={isSubmitting}
                  style={{
                    flex: 1,
                    minWidth: 200,
                    padding: "14px 24px",
                    backgroundColor: escalate ? "var(--urgent)" : "var(--success)",
                    color: "#FFF",
                    border: "none",
                    borderRadius: 8,
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: "pointer",
                    minHeight: 48,
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 8,
                  }}
                >
                  {isSubmitting ? "Submitting..." : escalate ? "⚠️ Escalate & Finalize" : "✓ Complete & Sign Follow-up"}
                </button>
              </div>
            </div>
          ) : isEscalated ? (
            <div style={{ padding: 24, backgroundColor: "#FEE2E2", borderRadius: 12, border: "1px solid #FECACA" }}>
              <h3 style={{ margin: "0 0 12px", fontSize: 18, color: "#991B1B", fontWeight: 700 }}>⚠️ Escalated to Medical Officer</h3>
              <p style={{ fontSize: 14, color: "#7F1D1D", margin: "0 0 12px" }}>
                This follow-up was escalated to the PHC doctor due to red-flag symptoms. An emergency escalation record was created.
              </p>
              {fup.result && (
                <div style={{ padding: 12, backgroundColor: "#FFF", borderRadius: 8, fontSize: 13, color: "#991B1B", fontWeight: 600 }}>
                  Escalation Note: {fup.result}
                </div>
              )}
            </div>
          ) : (
            <div style={{ padding: 24, backgroundColor: "#DEF7EC", borderRadius: 12, border: "1px solid #A7F3D0" }}>
              <h3 style={{ margin: "0 0 12px", fontSize: 18, color: "#03543F", fontWeight: 700 }}>✓ Follow-up Completed</h3>
              <p style={{ fontSize: 14, color: "#065F46", margin: "0 0 8px" }}>
                <strong>Completed At:</strong> {fup.completed_at ? new Date(fup.completed_at).toLocaleString() : "Recently"}
              </p>
              {fup.result && (
                <p style={{ fontSize: 14, color: "#065F46", margin: 0 }}>
                  <strong>Outcome:</strong> {fup.result}
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Reschedule Modal */}
      {showRescheduleModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, width: "100%", maxWidth: 450, display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>📅 Reschedule Follow-up</h3>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>New Due Date</label>
              <input
                id="reschedule-date-input"
                type="date"
                value={rescheduleDate}
                onChange={(e) => setRescheduleDate(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Reason for Rescheduling</label>
              <input
                id="reschedule-reason-input"
                type="text"
                placeholder="e.g., Citizen out of station, requested next Monday"
                value={rescheduleReason}
                onChange={(e) => setRescheduleReason(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)" }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8 }}>
              <button
                onClick={() => setShowRescheduleModal(false)}
                style={{ padding: "10px 16px", backgroundColor: "var(--neutral-bg)", border: "1px solid var(--border)", borderRadius: 8, cursor: "pointer", minHeight: 44 }}
              >
                Cancel
              </button>
              <button
                id="confirm-reschedule-btn"
                onClick={handleRescheduleSubmit}
                disabled={isSubmitting}
                style={{ padding: "10px 18px", backgroundColor: "var(--primary)", color: "#FFF", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer", minHeight: 44 }}
              >
                {isSubmitting ? "Saving..." : "Confirm Reschedule"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Escalate Modal */}
      {showEscalateModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, width: "100%", maxWidth: 450, display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#991B1B" }}>⚠️ Escalate to Medical Officer</h3>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Reason for Urgent Escalation</label>
              <input
                id="escalate-reason-input"
                type="text"
                placeholder="e.g., Severe breathing difficulty, uncontrolled hypertension"
                value={escalateReason}
                onChange={(e) => setEscalateReason(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Urgency Level</label>
              <select
                id="escalate-urgency-select"
                value={escalateUrgency}
                onChange={(e) => setEscalateUrgency(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)" }}
              >
                <option value="HIGH">High Urgency</option>
                <option value="EMERGENCY">Emergency</option>
                <option value="MEDIUM">Medium Urgency</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Clinical Notes</label>
              <textarea
                id="escalate-notes-textarea"
                rows={3}
                placeholder="Details of symptoms observed during visit..."
                value={escalateNotes}
                onChange={(e) => setEscalateNotes(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)" }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8 }}>
              <button
                onClick={() => setShowEscalateModal(false)}
                style={{ padding: "10px 16px", backgroundColor: "var(--neutral-bg)", border: "1px solid var(--border)", borderRadius: 8, cursor: "pointer", minHeight: 44 }}
              >
                Cancel
              </button>
              <button
                id="confirm-escalate-btn"
                onClick={handleEscalateSubmit}
                disabled={isSubmitting}
                style={{ padding: "10px 18px", backgroundColor: "#991B1B", color: "#FFF", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer", minHeight: 44 }}
              >
                {isSubmitting ? "Escalating..." : "Confirm Escalation"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
