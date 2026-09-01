import React, { useState, useEffect } from "react";
import { useLanguage } from "@aarogya/i18n";
import {
  ArrowLeft, CheckCircle2, Circle, Clock, User, Phone, MapPin,
  Calendar, AlertTriangle, ShieldCheck, FileText, XCircle, Loader2, Sparkles
} from "lucide-react";
import { apiClient } from "@aarogya/api-client";

interface ServiceRequestDetailScreenProps {
  requestId: string;
  onBack: () => void;
}

export const ServiceRequestDetailScreen: React.FC<ServiceRequestDetailScreenProps> = ({
  requestId,
  onBack
}) => {
  const { t, locale } = useLanguage();

  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState<boolean>(false);
  const [cancelReason, setCancelReason] = useState<string>("");
  const [showCancelModal, setShowCancelModal] = useState<boolean>(false);

  const fetchDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.getCitizenServiceRequestDetail(requestId);
      const data = res?.data || res;
      setDetail(data);
    } catch (err: any) {
      console.error("Failed to load service request detail:", err);
      const status = err?.response?.status;
      if (status === 403) {
        setError("You do not have access to view this service request.");
      } else if (status === 404) {
        setError("Service request not found.");
      } else {
        setError(err?.message || "Could not load service request.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
    // 5-second polling fallback
    const interval = setInterval(() => {
      apiClient.getCitizenServiceRequestDetail(requestId).then(res => {
        const d = res?.data || res;
        if (d) setDetail(d);
      }).catch(() => {});
    }, 5000);

    return () => clearInterval(interval);
  }, [requestId]);

  const handleCancelRequest = async () => {
    if (!cancelReason.trim()) return;
    setCancelling(true);
    try {
      await apiClient.cancelCitizenServiceRequest(requestId, cancelReason.trim());
      setShowCancelModal(false);
      await fetchDetail();
    } catch (err: any) {
      console.error("Cancel failed:", err);
      alert(err?.message || "Failed to cancel request.");
    } finally {
      setCancelling(false);
    }
  };

  if (loading && !detail) {
    return (
      <div style={{ padding: 32, textAlign: "center", color: "#64748B" }}>
        <Loader2 size={32} className="animate-spin" style={{ margin: "0 auto 12px auto" }} />
        <div style={{ fontSize: 14, fontWeight: 700 }}>Loading care request details...</div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
        <button
          onClick={onBack}
          style={{
            border: "none",
            background: "none",
            display: "flex",
            alignItems: "center",
            gap: 6,
            color: "#2563EB",
            fontWeight: 800,
            cursor: "pointer",
            fontSize: 14
          }}
        >
          <ArrowLeft size={18} /> Back to My Care
        </button>
        <div style={{ padding: 20, backgroundColor: "#FEF2F2", borderRadius: 16, border: "1px solid #FCA5A5", color: "#991B1B" }}>
          <div style={{ fontSize: 15, fontWeight: 800 }}>Error</div>
          <div style={{ fontSize: 13, marginTop: 4 }}>{error || "Service request not found."}</div>
        </div>
      </div>
    );
  }

  const isDoc = detail.request_type === "DOCTOR_CONSULTATION";
  const isAsha = detail.request_type === "ASHA_ASSISTANCE";
  const handoff = detail.handoff_packet || {};
  const packetSafety = handoff.safety || {};
  const status = detail.status;
  const isUrgent = detail.priority === "URGENT" || detail.priority === "HIGH" || detail.priority === "EMERGENCY";

  // Status Stepper definition
  const ashaSteps = [
    { title: t("common.submitted", "Submitted"), done: true },
    { title: t("status.ASHA_ASSIGNED", "ASHA Assigned"), done: status !== "ASSIGNMENT_PENDING" },
    { title: t("status.VISIT_SCHEDULED", "Visit Scheduled"), done: ["VISIT_SCHEDULED", "IN_PROGRESS", "FIELD_VISIT_IN_PROGRESS", "COMPLETED"].includes(status) },
    { title: t("common.completed", "Completed"), done: status === "COMPLETED" }
  ];

  const docSteps = [
    { title: t("common.submitted", "Submitted"), done: true },
    { title: t("status.DOCTOR_ACKNOWLEDGED", "Doctor Accepted"), done: ["DOCTOR_ACCEPTED", "IN_CONSULTATION", "COMPLETED"].includes(status) },
    { title: t("status.CONSULTATION_IN_PROGRESS", "Consultation"), done: ["IN_CONSULTATION", "COMPLETED"].includes(status) },
    { title: t("common.completed", "Completed"), done: status === "COMPLETED" }
  ];

  const steps = isDoc ? docSteps : ashaSteps;

  return (
    <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 16, backgroundColor: "#F8FAFC", minHeight: "100%" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <button
          onClick={onBack}
          style={{
            background: "#FFFFFF",
            borderRadius: 12,
            padding: "8px 12px",
            display: "flex",
            alignItems: "center",
            gap: 6,
            color: "#1E293B",
            fontWeight: 800,
            cursor: "pointer",
            fontSize: 13,
            boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
            border: "1px solid #E2E8F0"
          }}
        >
          <ArrowLeft size={16} /> {t("common.back", "Back")}
        </button>

        <span
          style={{
            fontSize: 11,
            fontWeight: 800,
            padding: "4px 10px",
            borderRadius: 12,
            backgroundColor: isUrgent ? "#FEE2E2" : "#EFF6FF",
            color: isUrgent ? "#DC2626" : "#1D4ED8",
            border: `1px solid ${isUrgent ? '#FCA5A5' : '#BFDBFE'}`
          }}
        >
          {isUrgent ? `⚠️ ${t("priority.URGENT", "URGENT")}` : t("priority.ROUTINE", "ROUTINE")} • Ref: {detail.request_reference}
        </span>
      </div>

      {/* Main Request Banner */}
      <div
        style={{
          backgroundColor: "#FFFFFF",
          borderRadius: 20,
          padding: 16,
          border: "1px solid #E2E8F0",
          boxShadow: "0 2px 8px rgba(0,0,0,0.04)"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 800, color: isDoc ? "#2563EB" : "#059669", textTransform: "uppercase" }}>
              {isDoc ? `🩺 ${t("citizen.doctor_teleconsultation", "Doctor Teleconsultation")}` : `🏡 ${t("citizen.asha_assistance", "ASHA Home Assistance")}`}
            </div>
            <div style={{ fontSize: 16, fontWeight: 800, color: "#0F172A", marginTop: 4 }}>
              {detail.chief_concern || "Health Care Request"}
            </div>
          </div>
          <span
            style={{
              fontSize: 11,
              fontWeight: 800,
              padding: "4px 8px",
              borderRadius: 8,
              backgroundColor: status === "COMPLETED" ? "#DCFCE7" : "#FEF3C7",
              color: status === "COMPLETED" ? "#166534" : "#92400E"
            }}
          >
            {t(`status.${status}`, status.replace(/_/g, " "))}
          </span>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 12, fontSize: 12, color: "#64748B" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <User size={14} />
            <span>{t("wizard.step6_field_patient", "Patient:")} <strong style={{ color: "#1E293B" }}>{detail.beneficiary?.name || handoff.beneficiary_name || detail.beneficiary_name || "Myself"}</strong></span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <Clock size={14} />
            <span>{t("common.date", "Date")}: {new Date(detail.submitted_at || detail.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" })}</span>
          </div>
        </div>
      </div>

      {/* Status Stepper */}
      <div
        style={{
          backgroundColor: "#FFFFFF",
          borderRadius: 20,
          padding: 16,
          border: "1px solid #E2E8F0"
        }}
      >
        <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", marginBottom: 14 }}>
          {t("case.timeline", "Care Progress Stepper")}
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          {steps.map((st, idx) => (
            <div key={idx} style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1, position: "relative" }}>
              {st.done ? (
                <CheckCircle2 size={22} color="#166534" />
              ) : (
                <Circle size={22} color="#CBD5E1" />
              )}
              <span style={{ fontSize: 9, fontWeight: 700, color: st.done ? "#166534" : "#94A3B8", marginTop: 4, textAlign: "center" }}>
                {st.title}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Assigned Health Worker Card (Shown only after assignment) */}
      <div
        style={{
          backgroundColor: "#FFFFFF",
          borderRadius: 20,
          padding: 16,
          border: "1px solid #E2E8F0"
        }}
      >
        <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", marginBottom: 10 }}>
          {t("citizen.care_team", "Assigned Healthcare Provider")}
        </div>
        {detail.assigned_user_id || status !== "ASSIGNMENT_PENDING" ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: 12, borderRadius: 14, backgroundColor: isDoc ? "#EFF6FF" : "#ECFDF5" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: isDoc ? "#DBEAFE" : "#DCFCE7", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <User size={20} color={isDoc ? "#1E40AF" : "#166534"} />
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 800, color: "#0F172A" }}>
                  {detail.assigned_worker_name || (isDoc ? "Dr. Abhinav Sharma" : "Sita Patel (ASHA)")}
                </div>
                <div style={{ fontSize: 11, color: "#64748B" }}>
                  {isDoc ? `${t("roles.PHC_DOCTOR", "PHC Medical Officer")} • Kalyanpur PHC` : `${t("roles.ASHA_WORKER", "Accredited Social Health Activist")} • Kalyanpur`}
                </div>
              </div>
            </div>
            <button
              onClick={() => window.open("tel:9823012345", "_self")}
              style={{
                padding: "8px 12px",
                borderRadius: 20,
                backgroundColor: isDoc ? "#2563EB" : "#059669",
                color: "#FFFFFF",
                border: "none",
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 4
              }}
            >
              <Phone size={14} /> {t("common.speak", "Call")}
            </button>
          </div>
        ) : (
          <div style={{ padding: 12, borderRadius: 14, backgroundColor: "#FFFBEB", border: "1px solid #FDE68A", color: "#92400E", fontSize: 13, fontWeight: 700 }}>
            ⏳ {t("status.ASHA_ASSIGNED", "Matching available health worker for your jurisdiction...")}
          </div>
        )}
      </div>

      {/* Shared Information Summary */}
      <div
        style={{
          backgroundColor: "#FFFFFF",
          borderRadius: 20,
          padding: 16,
          border: "1px solid #E2E8F0"
        }}
      >
        <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", marginBottom: 10, display: "flex", alignItems: "center", gap: 6 }}>
          <ShieldCheck size={16} color="#059669" />
          <span>{t("wizard.step5_title", "Shared Clinical Summary (Consented)")}</span>
        </div>
        <div style={{ fontSize: 13, color: "#334155", lineHeight: 1.5, backgroundColor: "#F8FAFC", padding: 12, borderRadius: 12, border: "1px solid #E2E8F0" }}>
          {detail.citizen_summary || handoff.citizen_summary || `${detail.chief_concern} reported by citizen.`}
        </div>

        {handoff.symptoms && handoff.symptoms.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#64748B", marginBottom: 6 }}>{t("wizard.step2_identified_symptoms", "Identified Symptoms")}:</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {handoff.symptoms.map((sym: any, sIdx: number) => {
                const sStr = typeof sym === "string" ? sym : (sym.display || sym.code);
                const sKey = sStr.toUpperCase().replace(/\s+/g, "_");
                return (
                  <span
                    key={sIdx}
                    style={{
                      padding: "4px 10px",
                      borderRadius: 12,
                      backgroundColor: "#EFF6FF",
                      color: "#1D4ED8",
                      fontSize: 11,
                      fontWeight: 700,
                      border: "1px solid #BFDBFE"
                    }}
                  >
                    ✓ {t(`symptoms.${sKey}`, sStr)}
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Doctor Consultation Outcome (Displayed when consultation is completed or outcome is available) */}
      {(detail.consultation || (detail.prescriptions && detail.prescriptions.length > 0) || (detail.investigations && detail.investigations.length > 0) || (detail.followups && detail.followups.length > 0)) && (
        <div
          style={{
            backgroundColor: "#FFFFFF",
            borderRadius: 20,
            padding: 16,
            border: "2px solid #2563EB",
            boxShadow: "0 4px 14px rgba(37, 99, 235, 0.08)"
          }}
        >
          <div style={{ fontSize: 15, fontWeight: 900, color: "#1E3A8A", marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
            <span>🩺 {t("consultation.treatment_plan", "Doctor Consultation Outcome")}</span>
            <span style={{ fontSize: 10, fontWeight: 800, padding: "2px 8px", borderRadius: 8, backgroundColor: "#DBEAFE", color: "#1D4ED8" }}>
              {t("common.saved", "DOCTOR SIGNED")}
            </span>
          </div>

          {/* Doctor & Diagnosis Details */}
          <div style={{ backgroundColor: "#F0F9FF", borderRadius: 14, padding: 12, border: "1px solid #BAE6FD", marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 800, color: "#0369A1" }}>
              {detail.consultation?.doctor_name || detail.assigned_worker_name || "Dr. Abhinav Sharma"} • {detail.consultation?.facility_name || "Kalyanpur PHC"}
            </div>
            <div style={{ fontSize: 13, color: "#0F172A", marginTop: 4 }}>
              <strong>{t("consultation.clinical_notes", "Doctor Confirmed Diagnosis")}:</strong> {detail.consultation?.confirmed_diagnosis || detail.consultation?.provisional_diagnosis || detail.details?.provisional_diagnosis || "Clinical evaluation completed"}
            </div>
            {(detail.consultation?.care_plan_summary || detail.details?.patient_guidance) && (
              <div style={{ fontSize: 12, color: "#334155", marginTop: 6, lineHeight: 1.5 }}>
                <strong>{t("consultation.patient_advice", "Care Guidance")}:</strong> {detail.consultation?.care_plan_summary || detail.details?.patient_guidance}
              </div>
            )}
          </div>

          {/* Prescribed Medicines */}
          {detail.prescriptions && detail.prescriptions.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 800, color: "#1E293B", marginBottom: 6, display: "flex", alignItems: "center", gap: 4 }}>
                💊 {t("navigation.medicines", "Prescribed Medicines")} ({detail.prescriptions.length})
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {detail.prescriptions.map((rx: any, rxIdx: number) => (
                  <div key={rxIdx} style={{ backgroundColor: "#F8FAFC", borderRadius: 10, padding: 10, border: "1px solid #E2E8F0" }}>
                    {rx.items?.map((item: any, iIdx: number) => (
                      <div key={iIdx} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 2 }}>
                        <span style={{ fontWeight: 700, color: "#0F172A" }}>• {item.medicine_name}</span>
                        <span style={{ color: "#64748B" }}>{item.dosage} • {item.frequency} ({item.duration_days} days)</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Ordered Investigations */}
          {detail.investigations && detail.investigations.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 800, color: "#1E293B", marginBottom: 6, display: "flex", alignItems: "center", gap: 4 }}>
                🔬 {t("investigation.test_name", "Lab Investigations")} ({detail.investigations.length})
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {detail.investigations.map((inv: any, invIdx: number) => (
                  <span key={invIdx} style={{ padding: "4px 10px", borderRadius: 10, backgroundColor: "#FEF3C7", color: "#92400E", fontSize: 11, fontWeight: 700, border: "1px solid #FDE68A" }}>
                    🧪 {inv.test_name} ({t(`status.${inv.status}`, inv.status)})
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Follow-up Directive */}
          {detail.followups && detail.followups.length > 0 && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 800, color: "#1E293B", marginBottom: 6, display: "flex", alignItems: "center", gap: 4 }}>
                📅 {t("consultation.followup_required", "Assigned Follow-up Plan")} ({detail.followups.length})
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {detail.followups.map((fu: any, fuIdx: number) => (
                  <div key={fuIdx} style={{ backgroundColor: "#F0FDF4", borderRadius: 10, padding: 10, border: "1px solid #BBF7D0", fontSize: 12, color: "#166534" }}>
                    <div style={{ fontWeight: 800 }}>Task: {fu.task_type}</div>
                    <div>Instructions: {fu.instructions}</div>
                    {fu.due_at && <div style={{ fontSize: 11, opacity: 0.8, marginTop: 2 }}>Due: {new Date(fu.due_at).toLocaleDateString()}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* State Audit History */}
      {detail.status_history && detail.status_history.length > 0 && (
        <div
          style={{
            backgroundColor: "#FFFFFF",
            borderRadius: 20,
            padding: 16,
            border: "1px solid #E2E8F0"
          }}
        >
          <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", marginBottom: 12 }}>
            Activity & Audit History
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {detail.status_history.map((h: any, hIdx: number) => (
              <div key={hIdx} style={{ display: "flex", gap: 10, borderLeft: "2px solid #2563EB", paddingLeft: 10 }}>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 800, color: "#0F172A" }}>
                    {h.to_status.replace(/_/g, " ")} ({h.actor_role})
                  </div>
                  <div style={{ fontSize: 11, color: "#64748B", marginTop: 1 }}>{h.reason}</div>
                  <div style={{ fontSize: 10, color: "#94A3B8", marginTop: 2 }}>{new Date(h.occurred_at).toLocaleString()}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cancel Action if pending */}
      {["SUBMITTED", "WAITING_FOR_DOCTOR", "PENDING", "ASSIGNMENT_PENDING", "ASHA_ASSIGNED"].includes(status) && (
        <button
          onClick={() => setShowCancelModal(true)}
          style={{
            padding: 12,
            borderRadius: 14,
            backgroundColor: "#FEF2F2",
            border: "1px solid #FCA5A5",
            color: "#DC2626",
            fontSize: 13,
            fontWeight: 800,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 6
          }}
        >
          <XCircle size={16} /> Cancel Care Request
        </button>
      )}

      {/* Cancel Dialog Modal */}
      {showCancelModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 16
          }}
        >
          <div style={{ width: "100%", maxWidth: 380, backgroundColor: "#FFFFFF", borderRadius: 20, padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: "#0F172A" }}>Cancel Care Request</div>
            <div style={{ fontSize: 13, color: "#64748B" }}>Please tell us the reason for cancelling this request:</div>
            <textarea
              rows={3}
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="e.g. Symptoms resolved, visited clinic directly..."
              style={{
                width: "100%",
                padding: 10,
                borderRadius: 12,
                border: "1px solid #CBD5E1",
                fontSize: 13,
                outline: "none"
              }}
            />
            <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
              <button
                onClick={() => setShowCancelModal(false)}
                style={{ flex: 1, padding: 10, borderRadius: 12, border: "1px solid #CBD5E1", backgroundColor: "#F8FAFC", fontWeight: 700, cursor: "pointer" }}
              >
                Go Back
              </button>
              <button
                onClick={handleCancelRequest}
                disabled={!cancelReason.trim() || cancelling}
                style={{ flex: 1, padding: 10, borderRadius: 12, border: "none", backgroundColor: "#DC2626", color: "#FFFFFF", fontWeight: 800, cursor: !cancelReason.trim() || cancelling ? "not-allowed" : "pointer" }}
              >
                {cancelling ? "Cancelling..." : "Confirm Cancel"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
