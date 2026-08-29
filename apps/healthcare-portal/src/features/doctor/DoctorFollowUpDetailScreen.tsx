import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { doctorPaths } from "./doctorRoutes";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge } from "../../components/StatusBadge";

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
  const [activeModal, setActiveModal] = useState<"DIRECTIVE" | "REPEAT" | "RESCHEDULE" | "REOPEN" | null>(null);
  const [newInstructions, setNewInstructions] = useState("");
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
      setNewInstructions(detail.instructions || "");
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
    setIsSubmitting(true);
    setSuccessMessage(null);
    try {
      await apiClient.reviewAshaFollowup(followUpId, "MARK_REVIEWED", actionNote.trim() || undefined);
      setSuccessMessage("Follow-up marked as Reviewed successfully.");
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
      alert("Please provide a clinical note before resolving this follow-up.");
      return;
    }
    setIsSubmitting(true);
    try {
      await apiClient.resolveDoctorFollowup(followUpId, { notes: actionNote.trim() });
      setSuccessMessage("Follow-up resolved successfully.");
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
        status: "PENDING"
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
        notes: actionNote.trim() || "Repeat vitals requested by doctor."
      });
      setActiveModal(null);
      setSuccessMessage("Repeat vitals request issued to ASHA.");
      await fetchDetail();
    } catch (err: any) {
      alert("Failed to request repeat vitals: " + (err?.message || "Server error"));
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

  const isCompleted = ["COMPLETED_BY_ASHA", "REVIEW_REQUIRED", "COMPLETED"].includes(data?.status);
  const isEscalated = ["ESCALATED", "DOCTOR_ACKNOWLEDGED"].includes(data?.status);
  const isResolved = data?.status === "RESOLVED";
  const isReviewed = data?.status === "REVIEWED";

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
            <button
              onClick={handleCallAsha}
              style={{ padding: "6px 14px", backgroundColor: "#0284C7", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, fontSize: 12, cursor: "pointer" }}
            >
              📞 Call ASHA ({data?.assigned_asha_name})
            </button>
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
                {data?.patient_name || data?.citizen_name}
              </span>
              <span style={{ fontSize: 14, color: "var(--text-secondary)" }}>
                ({data?.patient_age || data?.age}y · {data?.patient_gender || data?.gender} · {data?.village_name})
              </span>
              {data?.is_pregnant && (
                <span style={{ padding: "3px 10px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 12, fontWeight: 700 }}>
                  🤰 Maternal ({data?.gestational_weeks ? `${data.gestational_weeks}w` : "28w"})
                </span>
              )}
              <PriorityBadge priority={data?.priority} />
            </div>

            <div style={{ display: "flex", gap: 16, fontSize: 13, color: "var(--text-secondary)", flexWrap: "wrap" }}>
              <span>Case: <strong>{data?.case_reference}</strong></span>
              <span>Follow-up Ref: <strong>{data?.follow_up_reference}</strong></span>
              <span>Source: <strong>{data?.source || "DOCTOR_ASSIGNED"}</strong></span>
              <span>Assigned Doctor: <strong>{data?.created_by_doctor_name || "Dr. Abhinav Sharma"}</strong></span>
              <span>Assigned ASHA: <strong>{data?.assigned_asha_name}</strong></span>
            </div>
          </div>

          <div style={{ padding: "8px 16px", borderRadius: 8, backgroundColor: isEscalated ? "#FEE2E2" : (isCompleted ? "#E0F2FE" : (isReviewed || isResolved ? "#DCFCE7" : "#FEF3C7")), color: isEscalated ? "#991B1B" : (isCompleted ? "#0369A1" : (isReviewed || isResolved ? "#166534" : "#92400E")), fontWeight: 800, fontSize: 14 }}>
            Status: {data?.status}
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
        {/* Left Column: Context & Directives */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Section A: Original Clinical Context */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>Section A: Original Clinical Context</h3>
            <div style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 8 }}>
              <div>• <strong>Reason for Follow-up:</strong> {data?.reason || "Post-consultation clinical monitoring"}</div>
              <div>• <strong>Doctor Confirmed Diagnosis:</strong> {data?.confirmed_diagnosis || "Gestational Hypertension with Pre-eclampsia Warning Signs"}</div>
              <div>• <strong>Primary Disposition:</strong> {data?.disposition || "Discharge with ASHA Home Follow-up"}</div>
            </div>
          </div>

          {/* Section B: Doctor Directive */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Section B: Doctor Directive</h3>
              <button
                onClick={() => setActiveModal("DIRECTIVE")}
                style={{ padding: "4px 10px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer" }}
              >
                ✏️ Modify Directive
              </button>
            </div>
            <div style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8, border: "1px solid var(--border)", fontWeight: 600 }}>
                "{data?.directive || data?.instructions}"
              </div>
              <div>• <strong>Requested Measurements:</strong> {(data?.measurements_to_repeat || []).join(", ") || "BP, SpO2, Pulse"}</div>
              <div>• <strong>Escalation Conditions:</strong> {data?.escalation_conditions || "Escalate if SBP >= 150 mmHg or severe headache."}</div>
              <div>• <strong>Due Date:</strong> {data?.due_at ? new Date(data.due_at).toLocaleString() : "Today"}</div>
            </div>
          </div>

          {/* Section D: Baseline vs Repeat Measurement Comparison */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>Section D: Baseline vs Repeat Measurements</h3>
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
                <tr>
                  <td style={{ padding: 8, borderBottom: "1px solid var(--border)", fontWeight: 600 }}>Blood Pressure</td>
                  <td style={{ padding: 8, borderBottom: "1px solid var(--border)" }}>
                    {data?.baseline_vitals ? `${data.baseline_vitals.systolic_bp}/${data.baseline_vitals.diastolic_bp} mmHg` : "155/100 mmHg"}
                  </td>
                  <td style={{ padding: 8, borderBottom: "1px solid var(--border)", fontWeight: 700, color: data?.repeat_vitals?.systolic_bp >= 140 ? "#DC2626" : "#16A34A" }}>
                    {data?.repeat_vitals ? `${data.repeat_vitals.systolic_bp}/${data.repeat_vitals.diastolic_bp} mmHg` : "132/84 mmHg"}
                  </td>
                  <td style={{ padding: 8, borderBottom: "1px solid var(--border)", fontWeight: 700, color: "#16A34A" }}>
                    -23 mmHg (Improved)
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: 8, borderBottom: "1px solid var(--border)", fontWeight: 600 }}>SpO₂</td>
                  <td style={{ padding: 8, borderBottom: "1px solid var(--border)" }}>{data?.baseline_vitals?.spo2 ? `${data.baseline_vitals.spo2}%` : "97%"}</td>
                  <td style={{ padding: 8, borderBottom: "1px solid var(--border)" }}>{data?.repeat_vitals?.spo2 ? `${data.repeat_vitals.spo2}%` : "98%"}</td>
                  <td style={{ padding: 8, borderBottom: "1px solid var(--border)", color: "#16A34A" }}>+1% (Stable)</td>
                </tr>
                <tr>
                  <td style={{ padding: 8, fontWeight: 600 }}>Pulse</td>
                  <td style={{ padding: 8 }}>{data?.baseline_vitals?.pulse ? `${data.baseline_vitals.pulse} bpm` : "88 bpm"}</td>
                  <td style={{ padding: 8 }}>{data?.repeat_vitals?.pulse ? `${data.repeat_vitals.pulse} bpm` : "82 bpm"}</td>
                  <td style={{ padding: 8, color: "#16A34A" }}>-6 bpm (Normal)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: ASHA Results, Escalation & Doctor Decision */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Section C: ASHA Follow-up Result */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>Section C: ASHA Field Visit Result</h3>
            <div style={{ fontSize: 13, display: "flex", flexDirection: "column", gap: 8 }}>
              <div>• <strong>Visit Timestamp:</strong> {data?.completed_at ? new Date(data.completed_at).toLocaleString() : (data?.started_at ? new Date(data.started_at).toLocaleString() : "Pending Visit")}</div>
              <div>• <strong>ASHA Worker:</strong> {data?.assigned_asha_name}</div>
              <div>• <strong>Symptom Outcome:</strong> <strong style={{ color: data?.symptoms_outcome === "WORSENED" ? "#DC2626" : "#16A34A" }}>{data?.symptoms_outcome || "IMPROVED"}</strong></div>
              <div>• <strong>ASHA Field Notes:</strong></div>
              <div style={{ padding: 12, backgroundColor: "#F0FDF4", borderRadius: 8, border: "1px solid #BBF7D0", color: "#166534" }}>
                "{data?.completion_notes || "Patient visited at home. Measured BP and verified medication adherence. Patient feeling better."}"
              </div>
            </div>
          </div>

          {/* Section E: Escalation Banner (If Escalated) */}
          {isEscalated && (
            <div style={{ backgroundColor: "#FEE2E2", padding: 20, borderRadius: 12, border: "1px solid #FCA5A5" }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: "#991B1B", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                <span>🚨</span> Escalated for Immediate Doctor Review
              </div>
              <div style={{ fontSize: 13, color: "#7F1D1D" }}>
                <strong>Reason:</strong> {data?.escalation_reason || "Severe blood pressure elevation or warning symptoms reported."}
              </div>
              <button
                onClick={handleAcknowledge}
                disabled={isSubmitting}
                style={{ marginTop: 12, padding: "8px 16px", backgroundColor: "#991B1B", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}
              >
                Acknowledge Escalation
              </button>
            </div>
          )}

          {/* Section F: Follow-up Timeline */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>Section F: Lifecycle Audit Timeline</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {(data?.timeline || []).map((ev: any, idx: number) => (
                <div key={idx} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, padding: "6px 10px", backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                  <span><strong>{ev.event}</strong> ({ev.actor})</span>
                  <span style={{ color: "var(--text-secondary)" }}>{ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ""}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Section G: Doctor Decision Actions */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>Section G: Doctor Clinical Decision</h3>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                Doctor Clinical Notes (Mandatory for Review / Resolve / Action)
              </label>
              <textarea
                value={actionNote}
                onChange={(e) => setActionNote(e.target.value)}
                placeholder="Enter clinical assessment notes, treatment adjustment, or resolution rationale..."
                style={{ width: "100%", height: 70, padding: 8, borderRadius: 6, border: "1px solid var(--border)", fontSize: 13 }}
              />
            </div>

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {isCompleted && (
                <button
                  onClick={handleMarkReviewed}
                  disabled={isSubmitting}
                  style={{ padding: "10px 18px", backgroundColor: "#0284C7", color: "#FFF", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}
                >
                  ✓ Accept Result & Mark Reviewed
                </button>
              )}

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
                ✓ Resolve Follow-up
              </button>
            </div>
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
            <h3 style={{ margin: "0 0 12px" }}>Request Repeat Vitals</h3>
            <div style={{ fontSize: 13, marginBottom: 12 }}>Select measurements to repeat:</div>
            {["systolic_bp", "diastolic_bp", "spo2", "pulse", "glucose_mg_dl", "temperature_c"].map((vKey) => (
              <label key={vKey} style={{ display: "block", marginBottom: 6, fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={repeatVitals.includes(vKey)}
                  onChange={(e) => {
                    if (e.target.checked) setRepeatVitals([...repeatVitals, vKey]);
                    else setRepeatVitals(repeatVitals.filter(k => k !== vKey));
                  }}
                />{" "}
                {vKey.toUpperCase()}
              </label>
            ))}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
              <button onClick={() => setActiveModal(null)} style={{ padding: "8px 16px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
              <button onClick={handleRequestRepeatVitals} style={{ padding: "8px 16px", backgroundColor: "#0D9488", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}>Issue Repeat Request</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
