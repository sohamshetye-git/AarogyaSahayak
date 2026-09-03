import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { doctorPaths } from "./doctorRoutes";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge } from "../../components/StatusBadge";

const PARAMETER_META: Record<string, { label: string; unit: string }> = {
  systolic_bp: { label: "Systolic Blood Pressure", unit: "mmHg" },
  diastolic_bp: { label: "Diastolic Blood Pressure", unit: "mmHg" },
  blood_pressure: { label: "Blood Pressure", unit: "mmHg" },
  spo2: { label: "Oxygen Saturation (SpO₂)", unit: "%" },
  pulse: { label: "Pulse Rate", unit: "bpm" },
  temperature_c: { label: "Body Temperature", unit: "°C" },
  glucose_mg_dl: { label: "Blood Glucose", unit: "mg/dL" },
  respiratory_rate: { label: "Respiratory Rate", unit: "breaths/min" },
  weight_kg: { label: "Weight", unit: "kg" },
};

function formatSourceLabel(source?: string): string {
  if (!source) return "Doctor Prescribed Directive";
  switch (source) {
    case "ASHA_SCHEDULED":
      return "Scheduled by ASHA workflow";
    case "DOCTOR_ASSIGNED":
      return "Doctor Prescribed Directive";
    case "SYSTEM_GENERATED":
      return "System Automated Protocol";
    default:
      return source.replace(/_/g, " ");
  }
}

export function DoctorFollowUpDetailScreen() {
  const { followUpId } = useParams<{ followUpId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const returnTo = searchParams.get("returnTo") || "/doctor/followups";

  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Action Panel State
  const [actionNote, setActionNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Modal / Form States for secondary actions
  const [activeModal, setActiveModal] = useState<"DIRECTIVE" | "REPEAT" | "RESCHEDULE" | "CANCEL" | null>(null);
  const [newInstructions, setNewInstructions] = useState("");
  const [newDueDate, setNewDueDate] = useState("");
  const [cancelReason, setCancelReason] = useState("");
  const [repeatVitals, setRepeatVitals] = useState<string[]>(["systolic_bp", "diastolic_bp"]);

  const fetchDetail = async () => {
    if (!followUpId) return;
    setLoading(true);
    setErrorStatus(null);
    setErrorMessage(null);
    try {
      const res = await apiClient.getDoctorFollowUpDetail(followUpId);
      const detail = res?.data || res;
      setData(detail);
      setNewInstructions(detail.instructions || detail.directive || "");
      if (detail.measurements_to_repeat && detail.measurements_to_repeat.length > 0) {
        setRepeatVitals(detail.measurements_to_repeat);
      }
    } catch (err: any) {
      console.error("Failed to load doctor follow-up detail", err);
      const status = err?.status || err?.response?.status || 500;
      setErrorStatus(status);
      setErrorMessage(err?.message || "Failed to load follow-up record details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [followUpId]);

  const handleCallAsha = () => {
    const phone = data?.assigned_asha_phone || "9823012345";
    const name = data?.assigned_asha_name || "ASHA Worker";
    if (window.confirm(`Call ${name} at ${phone}?`)) {
      window.location.href = `tel:${phone}`;
    }
  };

  const handleMarkReviewed = async () => {
    if (!followUpId) return;
    if (!actionNote.trim()) {
      alert("Please enter doctor clinical notes before marking as reviewed.");
      return;
    }
    setIsSubmitting(true);
    setSuccessMessage(null);
    try {
      await apiClient.reviewAshaFollowup(followUpId, "MARK_REVIEWED", actionNote.trim());
      setSuccessMessage("Follow-up marked as Reviewed successfully.");
      setActionNote("");
      await fetchDetail();
    } catch (err: any) {
      alert("Failed to mark follow-up reviewed: " + (err?.message || "Server error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAcknowledge = async () => {
    if (!followUpId) return;
    setIsSubmitting(true);
    try {
      await apiClient.acknowledgeDoctorFollowup(followUpId, actionNote.trim() || undefined);
      setSuccessMessage("Escalation acknowledged.");
      await fetchDetail();
    } catch (err: any) {
      alert("Failed to acknowledge escalation: " + (err?.message || "Server error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResolve = async () => {
    if (!followUpId) return;
    if (!actionNote.trim()) {
      alert("Please provide clinical resolution notes before resolving this follow-up.");
      return;
    }
    setIsSubmitting(true);
    try {
      await apiClient.resolveDoctorFollowup(followUpId, { notes: actionNote.trim() });
      setSuccessMessage("Follow-up resolved successfully.");
      setActionNote("");
      await fetchDetail();
    } catch (err: any) {
      alert("Failed to resolve follow-up: " + (err?.message || "Server error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveDirective = async () => {
    if (!followUpId || !newInstructions.trim()) return;
    setIsSubmitting(true);
    try {
      await apiClient.updateDoctorFollowupDirective(followUpId, {
        instructions: newInstructions.trim(),
        status: data?.status === "ESCALATED" ? "ACTION_ASSIGNED" : data?.status
      });
      setActiveModal(null);
      setSuccessMessage("Doctor directive updated and sent to ASHA.");
      await fetchDetail();
    } catch (err: any) {
      alert("Failed to update directive: " + (err?.message || "Server error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRequestRepeatVitals = async () => {
    if (!followUpId) return;
    setIsSubmitting(true);
    try {
      await apiClient.requestRepeatVitals(followUpId, {
        measurements_to_repeat: repeatVitals,
        notes: actionNote.trim() || "Repeat measurements requested by doctor."
      });
      setActiveModal(null);
      setSuccessMessage("Repeat measurements request issued to ASHA.");
      await fetchDetail();
    } catch (err: any) {
      alert("Failed to request repeat measurements: " + (err?.message || "Server error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReschedule = async () => {
    if (!followUpId || !newDueDate) {
      alert("Please select a new due date and time.");
      return;
    }
    setIsSubmitting(true);
    try {
      await apiClient.rescheduleDoctorFollowup(followUpId, {
        new_due_at: new Date(newDueDate).toISOString(),
        reason: actionNote.trim() || "Rescheduled by doctor"
      });
      setActiveModal(null);
      setSuccessMessage("Follow-up rescheduled successfully.");
      await fetchDetail();
    } catch (err: any) {
      alert("Failed to reschedule follow-up: " + (err?.message || "Server error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelFollowup = async () => {
    if (!followUpId || !cancelReason.trim()) {
      alert("Please enter a cancellation reason.");
      return;
    }
    setIsSubmitting(true);
    try {
      await apiClient.cancelDoctorFollowup(followUpId, {
        reason: cancelReason.trim()
      });
      setActiveModal(null);
      setSuccessMessage("Follow-up cancelled.");
      await fetchDetail();
    } catch (err: any) {
      alert("Failed to cancel follow-up: " + (err?.message || "Server error"));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>⏳</div>
        <div>Loading Follow-up Record & Clinical Details...</div>
      </div>
    );
  }

  if (errorStatus === 404) {
    return (
      <div style={{ padding: 40, maxWidth: 600, margin: "40px auto", backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", textAlign: "center" }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🔍</div>
        <h2 style={{ margin: "0 0 12px", color: "var(--urgent)" }}>Follow-up Record Not Found (404)</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>
          No follow-up matching ID <strong>{followUpId}</strong> was found in the database.
        </p>
        <button
          onClick={() => navigate(returnTo)}
          style={{ padding: "10px 20px", backgroundColor: "var(--primary)", color: "#FFF", borderRadius: 8, border: "none", fontWeight: 700, cursor: "pointer" }}
        >
          ← Return to Follow-ups Workspace
        </button>
      </div>
    );
  }

  if (errorStatus && errorStatus >= 500) {
    return (
      <div style={{ padding: 40, maxWidth: 600, margin: "40px auto", backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", textAlign: "center" }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
        <h2 style={{ margin: "0 0 12px", color: "var(--urgent)" }}>Failed to Load Follow-up Detail</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>{errorMessage}</p>
        <button
          onClick={fetchDetail}
          style={{ padding: "10px 20px", backgroundColor: "var(--primary)", color: "#FFF", borderRadius: 8, border: "none", fontWeight: 700, cursor: "pointer" }}
        >
          Retry Loading
        </button>
      </div>
    );
  }

  // Lifecycle Status Determinations
  const status = data?.status || "PENDING";
  const isPending = status === "PENDING" || status === "SCHEDULED";
  const isInProgress = status === "IN_PROGRESS";
  const isCompleted = ["COMPLETED_BY_ASHA", "REVIEW_REQUIRED", "COMPLETED"].includes(status);
  const isEscalated = ["ESCALATED", "DOCTOR_ACKNOWLEDGED"].includes(status);
  const isReviewed = status === "REVIEWED";
  const isResolved = status === "RESOLVED";
  const isCancelled = status === "CANCELLED";

  // Check if visit has occurred
  const hasVisitOccurred = isCompleted || isEscalated || isReviewed || isResolved;

  // Due status calculation
  const dueDate = data?.due_at ? new Date(data.due_at) : null;
  const isOverdue = (isPending || isInProgress) && dueDate && dueDate.getTime() < Date.now();

  // Status Badge Styling
  let badgeBg = "#FEF3C7";
  let badgeColor = "#92400E";
  let badgeText = status;

  if (isEscalated) {
    badgeBg = "#FEE2E2";
    badgeColor = "#991B1B";
    badgeText = status === "DOCTOR_ACKNOWLEDGED" ? "DOCTOR ACKNOWLEDGED" : "ESCALATED";
  } else if (isCompleted) {
    badgeBg = "#E0F2FE";
    badgeColor = "#0369A1";
    badgeText = "COMPLETED BY ASHA";
  } else if (isReviewed || isResolved) {
    badgeBg = "#DCFCE7";
    badgeColor = "#166534";
    badgeText = isResolved ? "RESOLVED" : "REVIEWED";
  } else if (isCancelled) {
    badgeBg = "#F1F5F9";
    badgeColor = "#64748B";
    badgeText = "CANCELLED";
  } else if (isOverdue) {
    badgeBg = "#FEE2E2";
    badgeColor = "#B91C1C";
    badgeText = "PENDING (OVERDUE)";
  }

  // Measurements list for table
  const requestedMeasurements: string[] = data?.measurements_to_repeat && data.measurements_to_repeat.length > 0
    ? data.measurements_to_repeat
    : (data?.baseline_vitals ? Object.keys(data.baseline_vitals).filter(k => k !== "recorded_at") : ["systolic_bp", "diastolic_bp", "pulse"]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 1200, margin: "0 auto", width: "100%" }}>
      {/* Header Banner */}
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
          <button
            onClick={() => navigate(returnTo)}
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--primary)", fontWeight: 700, fontSize: 14 }}
          >
            ← Back to Follow-ups
          </button>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {data?.citizen_id && (
              <button
                onClick={() => navigate(doctorPaths.patientRecord(data.citizen_id))}
                style={{ padding: "6px 14px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, fontWeight: 600, fontSize: 12, cursor: "pointer" }}
              >
                👁 View Patient Record
              </button>
            )}
            {data?.case_id && (
              <button
                onClick={() => navigate(doctorPaths.caseTimeline(data.case_id))}
                style={{ padding: "6px 14px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, fontWeight: 600, fontSize: 12, cursor: "pointer" }}
              >
                📜 View Case Timeline
              </button>
            )}
            {data?.assigned_asha_name && data?.assigned_asha_name !== "Unassigned" && (
              <button
                onClick={handleCallAsha}
                style={{ padding: "6px 14px", backgroundColor: "#0284C7", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, fontSize: 12, cursor: "pointer" }}
              >
                📞 Call ASHA ({data.assigned_asha_name})
              </button>
            )}
            <button
              onClick={fetchDetail}
              style={{ padding: "6px 14px", backgroundColor: "var(--neutral-bg)", border: "1px solid var(--border)", borderRadius: 6, fontWeight: 600, fontSize: 12, cursor: "pointer" }}
            >
              ↻ Refresh
            </button>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
                {data?.patient_name || data?.citizen_name || "Patient Record"}
              </span>
              <span style={{ fontSize: 14, color: "var(--text-secondary)" }}>
                ({data?.patient_age ? `${data.patient_age}y` : "Age N/A"} · {data?.patient_gender || "Female"} · {data?.village_name || "Kalyanpur"})
              </span>
              {data?.is_pregnant && (
                <span style={{ padding: "3px 10px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 12, fontWeight: 700 }}>
                  🤰 Maternal ({data?.gestational_weeks ? `${data.gestational_weeks}w` : "Registered"})
                </span>
              )}
              <PriorityBadge priority={data?.priority} />
            </div>

            <div style={{ display: "flex", gap: 16, fontSize: 13, color: "var(--text-secondary)", flexWrap: "wrap" }}>
              <span>Case: <strong>{data?.case_reference || "N/A"}</strong></span>
              <span>Follow-up Ref: <strong>{data?.follow_up_reference || data?.id}</strong></span>
              <span>Source: <strong>{formatSourceLabel(data?.source)}</strong></span>
              <span>Assigned Doctor: <strong>{data?.assigned_doctor_name || data?.created_by_doctor_name || "Unassigned"}</strong></span>
              <span>Assigned ASHA: <strong>{data?.assigned_asha_name || "Unassigned"}</strong></span>
            </div>
          </div>

          <div style={{ padding: "8px 16px", borderRadius: 8, backgroundColor: badgeBg, color: badgeColor, fontWeight: 800, fontSize: 14 }}>
            Status: {badgeText}
          </div>
        </div>
      </div>

      {successMessage && (
        <div style={{ padding: 12, backgroundColor: "#DCFCE7", border: "1px solid #86EFAC", color: "#166534", borderRadius: 8, fontWeight: 600, fontSize: 14 }}>
          ✓ {successMessage}
        </div>
      )}

      {/* Main Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Left Column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Section 1: Original Clinical Context */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>Section 1: Original Clinical Context</h3>
            <div style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 8 }}>
              <div>• <strong>Reason for Follow-up:</strong> {data?.reason || "Post-consultation clinical monitoring"}</div>
              <div>• <strong>Task Type:</strong> {data?.task_type ? data.task_type.replace(/_/g, " ") : "Routine Home Follow-up"}</div>
              <div>• <strong>Primary Disposition:</strong> {data?.disposition || (data?.source === "ASHA_SCHEDULED" ? "ASHA Scheduled Follow-up" : "Discharge with ASHA Home Follow-up")}</div>
            </div>
          </div>

          {/* Section 2: Doctor Directive */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Section 2: Doctor Directive</h3>
              {!isReviewed && !isResolved && !isCancelled && (
                <button
                  onClick={() => setActiveModal("DIRECTIVE")}
                  style={{ padding: "4px 10px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer" }}
                >
                  ✏️ Modify Directive
                </button>
              )}
            </div>
            <div style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8, border: "1px solid var(--border)", fontWeight: 600 }}>
                "{data?.directive || data?.instructions || "Evaluate patient at home and report observations."}"
              </div>
              <div>
                • <strong>Requested Measurements:</strong>{" "}
                {requestedMeasurements.map(m => PARAMETER_META[m]?.label || m).join(", ") || "General Vitals"}
              </div>
              <div>
                • <strong>Escalation Conditions:</strong>{" "}
                {data?.escalation_conditions || "Escalate if warning signs develop or vitals exceed safe range."}
              </div>
              <div>
                • <strong>Due Date:</strong>{" "}
                {dueDate ? dueDate.toLocaleString() : "Pending Scheduling"}
                {isOverdue && (
                  <span style={{ marginLeft: 8, color: "#DC2626", fontWeight: 700 }}>
                    ⚠️ OVERDUE
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Section 3: Baseline vs Repeat Measurement Comparison */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>Section 3: Baseline vs Repeat Measurements</h3>
            {requestedMeasurements.length === 0 ? (
              <div style={{ padding: 16, textAlign: "center", color: "var(--text-secondary)", fontSize: 13 }}>
                No specific repeat measurements requested.
              </div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ backgroundColor: "var(--neutral-bg)", textAlign: "left" }}>
                    <th style={{ padding: 8, borderBottom: "1px solid var(--border)" }}>Parameter</th>
                    <th style={{ padding: 8, borderBottom: "1px solid var(--border)" }}>Baseline (Clinic)</th>
                    <th style={{ padding: 8, borderBottom: "1px solid var(--border)" }}>Repeat (ASHA Visit)</th>
                    <th style={{ padding: 8, borderBottom: "1px solid var(--border)" }}>Delta / Status</th>
                  </tr>
                </thead>
                <tbody>
                  {requestedMeasurements.map((paramKey) => {
                    const meta = PARAMETER_META[paramKey] || { label: paramKey, unit: "" };
                    const baselineVal = data?.baseline_vitals?.[paramKey];
                    const repeatVal = data?.repeat_vitals?.[paramKey];

                    // Formatted strings
                    const baselineStr = baselineVal !== undefined && baselineVal !== null ? `${baselineVal} ${meta.unit}` : "Not recorded";
                    const repeatStr = hasVisitOccurred
                      ? (repeatVal !== undefined && repeatVal !== null ? `${repeatVal} ${meta.unit}` : "Not recorded")
                      : "Awaiting ASHA visit";

                    // Delta / status evaluation
                    let deltaStr = "—";
                    let deltaColor = "var(--text-secondary)";
                    if (hasVisitOccurred && repeatVal !== undefined && repeatVal !== null) {
                      if (baselineVal !== undefined && baselineVal !== null && typeof baselineVal === "number" && typeof repeatVal === "number") {
                        const diff = repeatVal - baselineVal;
                        const sign = diff > 0 ? `+${diff}` : `${diff}`;
                        deltaStr = `${sign} ${meta.unit}`;
                        deltaColor = diff === 0 ? "var(--text-secondary)" : (paramKey === "spo2" ? (diff > 0 ? "#16A34A" : "#DC2626") : (diff < 0 ? "#16A34A" : "#DC2626"));
                      } else {
                        deltaStr = "Recorded";
                        deltaColor = "#16A34A";
                      }
                    }

                    return (
                      <tr key={paramKey}>
                        <td style={{ padding: 8, borderBottom: "1px solid var(--border)", fontWeight: 600 }}>{meta.label}</td>
                        <td style={{ padding: 8, borderBottom: "1px solid var(--border)" }}>{baselineStr}</td>
                        <td style={{ padding: 8, borderBottom: "1px solid var(--border)", fontWeight: hasVisitOccurred ? 700 : 400, color: hasVisitOccurred ? "var(--text-primary)" : "var(--text-disabled)" }}>
                          {repeatStr}
                        </td>
                        <td style={{ padding: 8, borderBottom: "1px solid var(--border)", color: deltaColor, fontWeight: hasVisitOccurred ? 600 : 400 }}>
                          {deltaStr}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right Column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Section 4: ASHA Field Visit Result */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>Section 4: ASHA Field Visit Result</h3>
            <div style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 8 }}>
              <div>
                • <strong>Visit Status:</strong>{" "}
                {hasVisitOccurred
                  ? "Conducted"
                  : (isInProgress ? "Visit In Progress" : "Visit Not Started / Awaiting ASHA Visit")}
              </div>
              <div>
                • <strong>Visit Timestamp:</strong>{" "}
                {data?.completed_at ? new Date(data.completed_at).toLocaleString() : (data?.started_at ? new Date(data.started_at).toLocaleString() : "Pending Visit")}
              </div>
              <div>• <strong>ASHA Worker:</strong> {data?.assigned_asha_name || "Unassigned"}</div>

              {hasVisitOccurred ? (
                <>
                  <div>
                    • <strong>Symptom Outcome:</strong>{" "}
                    <strong style={{ color: data?.symptoms_outcome === "WORSENED" ? "#DC2626" : "#16A34A" }}>
                      {data?.symptoms_outcome || "Not reported"}
                    </strong>
                  </div>
                  <div>• <strong>ASHA Field Notes:</strong></div>
                  <div style={{ padding: 12, backgroundColor: data?.symptoms_outcome === "WORSENED" ? "#FEF2F2" : "#F0FDF4", borderRadius: 8, border: `1px solid ${data?.symptoms_outcome === "WORSENED" ? "#FECACA" : "#BBF7D0"}`, color: data?.symptoms_outcome === "WORSENED" ? "#991B1B" : "#166534" }}>
                    "{data?.completion_notes || "No notes entered by ASHA worker."}"
                  </div>
                </>
              ) : (
                <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8, border: "1px dashed var(--border)", color: "var(--text-secondary)", fontStyle: "italic" }}>
                  ASHA field outcome and observation notes will appear here after the home visit is completed.
                </div>
              )}
            </div>
          </div>

          {/* Section 5 (Conditional): Escalation Alert */}
          {isEscalated && (
            <div style={{ backgroundColor: "#FEE2E2", padding: 20, borderRadius: 12, border: "1px solid #FCA5A5" }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: "#991B1B", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                <span>🚨</span> Escalated for Immediate Doctor Review
              </div>
              <div style={{ fontSize: 13, color: "#7F1D1D", marginBottom: 12 }}>
                <strong>Reason:</strong> {data?.escalation_reason || data?.completion_notes || "Severe vitals elevation or clinical warning signs reported during field visit."}
              </div>
              {status === "ESCALATED" && (
                <button
                  onClick={handleAcknowledge}
                  disabled={isSubmitting}
                  style={{ padding: "8px 16px", backgroundColor: "#991B1B", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}
                >
                  ✓ Acknowledge Escalation
                </button>
              )}
            </div>
          )}

          {/* Section 5: Lifecycle Audit Timeline */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>Section 5: Lifecycle Audit Timeline</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {(data?.timeline || []).map((ev: any, idx: number) => (
                <div key={idx} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "6px 10px", backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                  <span><strong>{ev.event}</strong> ({ev.actor})</span>
                  <span style={{ color: "var(--text-secondary)" }}>{ev.timestamp ? new Date(ev.timestamp).toLocaleString() : "Pending"}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Section 6: Doctor Decision Actions */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>Section 6: Doctor Clinical Decision</h3>

            {isReviewed || isResolved || isCancelled ? (
              <div style={{ padding: 14, backgroundColor: isCancelled ? "#F1F5F9" : "#DCFCE7", borderRadius: 8, border: `1px solid ${isCancelled ? "#CBD5E1" : "#86EFAC"}`, fontSize: 13 }}>
                <div style={{ fontWeight: 700, color: isCancelled ? "#475569" : "#166534", marginBottom: 4 }}>
                  {isResolved ? "✓ Follow-up Closed & Resolved" : (isReviewed ? "✓ Result Reviewed & Signed Off" : "Follow-up Cancelled")}
                </div>
                <div style={{ color: isCancelled ? "#64748B" : "#15803D" }}>
                  {data?.completion_notes || "Clinical review recorded."}
                </div>
              </div>
            ) : isPending || isInProgress ? (
              <div>
                <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13, color: "var(--text-secondary)", marginBottom: 14 }}>
                  This follow-up is currently awaiting field execution by ASHA worker <strong>{data?.assigned_asha_name || "Sita Patel"}</strong>. You may contact the ASHA, adjust directives, reschedule, or cancel this follow-up.
                </div>

                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button
                    onClick={handleCallAsha}
                    style={{ padding: "10px 16px", backgroundColor: "#0284C7", color: "#FFF", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}
                  >
                    📞 Call ASHA
                  </button>

                  <button
                    onClick={() => setActiveModal("DIRECTIVE")}
                    style={{ padding: "10px 16px", backgroundColor: "var(--surface)", color: "var(--primary)", border: "1px solid var(--primary)", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}
                  >
                    ✏️ Modify Directive
                  </button>

                  <button
                    onClick={() => setActiveModal("RESCHEDULE")}
                    style={{ padding: "10px 16px", backgroundColor: "var(--surface)", color: "#D97706", border: "1px solid #D97706", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}
                  >
                    📅 Reschedule
                  </button>

                  <button
                    onClick={() => setActiveModal("CANCEL")}
                    style={{ padding: "10px 16px", backgroundColor: "var(--surface)", color: "#DC2626", border: "1px solid #DC2626", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}
                  >
                    ✕ Cancel Follow-up
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <div style={{ marginBottom: 14 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                    Doctor Clinical Assessment Notes (Mandatory for Review / Resolution)
                  </label>
                  <textarea
                    value={actionNote}
                    onChange={(e) => setActionNote(e.target.value)}
                    placeholder="Enter clinical assessment notes, treatment titration, or resolution rationale..."
                    style={{ width: "100%", height: 75, padding: 8, borderRadius: 6, border: "1px solid var(--border)", fontSize: 13 }}
                  />
                </div>

                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button
                    onClick={handleMarkReviewed}
                    disabled={isSubmitting}
                    style={{ padding: "10px 18px", backgroundColor: "#0284C7", color: "#FFF", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}
                  >
                    ✓ Accept Result & Mark Reviewed
                  </button>

                  <button
                    onClick={() => setActiveModal("REPEAT")}
                    style={{ padding: "10px 16px", backgroundColor: "var(--surface)", color: "#0D9488", border: "1px solid #0D9488", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}
                  >
                    🔄 Request Repeat Vitals
                  </button>

                  <button
                    onClick={handleResolve}
                    disabled={isSubmitting}
                    style={{ padding: "10px 18px", backgroundColor: "#16A34A", color: "#FFF", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}
                  >
                    ✓ Resolve & Close
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* MODAL: DIRECTIVE UPDATE */}
      {activeModal === "DIRECTIVE" && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, maxWidth: 500, width: "90%", border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px" }}>Modify Doctor Directive</h3>
            <textarea
              value={newInstructions}
              onChange={(e) => setNewInstructions(e.target.value)}
              placeholder="Enter updated instructions for ASHA worker..."
              style={{ width: "100%", height: 100, padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginBottom: 16 }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button onClick={() => setActiveModal(null)} style={{ padding: "8px 16px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
              <button onClick={handleSaveDirective} style={{ padding: "8px 16px", backgroundColor: "var(--primary)", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}>Save & Send to ASHA</button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: REPEAT VITALS */}
      {activeModal === "REPEAT" && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, maxWidth: 500, width: "90%", border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px" }}>Request Repeat Measurements</h3>
            <div style={{ fontSize: 13, marginBottom: 12 }}>Select clinical parameters for ASHA worker to re-measure:</div>
            {["systolic_bp", "diastolic_bp", "spo2", "pulse", "glucose_mg_dl", "temperature_c", "respiratory_rate"].map((vKey) => (
              <label key={vKey} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, fontSize: 13, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={repeatVitals.includes(vKey)}
                  onChange={(e) => {
                    if (e.target.checked) setRepeatVitals([...repeatVitals, vKey]);
                    else setRepeatVitals(repeatVitals.filter(k => k !== vKey));
                  }}
                />
                <span>{PARAMETER_META[vKey]?.label || vKey.toUpperCase()}</span>
              </label>
            ))}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
              <button onClick={() => setActiveModal(null)} style={{ padding: "8px 16px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
              <button onClick={handleRequestRepeatVitals} style={{ padding: "8px 16px", backgroundColor: "#0D9488", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}>Issue Repeat Request</button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: RESCHEDULE */}
      {activeModal === "RESCHEDULE" && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, maxWidth: 500, width: "90%", border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px" }}>Reschedule Follow-up</h3>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
              New Due Date & Time
            </label>
            <input
              type="datetime-local"
              value={newDueDate}
              onChange={(e) => setNewDueDate(e.target.value)}
              style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginBottom: 16 }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button onClick={() => setActiveModal(null)} style={{ padding: "8px 16px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
              <button onClick={handleReschedule} style={{ padding: "8px 16px", backgroundColor: "#D97706", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}>Confirm Reschedule</button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: CANCEL */}
      {activeModal === "CANCEL" && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, maxWidth: 500, width: "90%", border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", color: "#DC2626" }}>Cancel Follow-up Directive</h3>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
              Reason for Cancellation
            </label>
            <textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Enter reason for cancelling this follow-up (e.g., patient admitted, duplicate order)..."
              style={{ width: "100%", height: 80, padding: 8, borderRadius: 6, border: "1px solid var(--border)", marginBottom: 16 }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button onClick={() => setActiveModal(null)} style={{ padding: "8px 16px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
              <button onClick={handleCancelFollowup} style={{ padding: "8px 16px", backgroundColor: "#DC2626", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}>Confirm Cancellation</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
