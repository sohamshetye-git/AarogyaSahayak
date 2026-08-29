import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import {
  ArrowLeft, Phone, Calendar, Clock, MapPin, User, CheckCircle2,
  AlertTriangle, ShieldCheck, Home as HomeIcon, Activity, FileText,
  Navigation, Stethoscope, Eye, AlertCircle, Info, RefreshCw, Send,
  ChevronRight, Heart, Shield, Check
} from "lucide-react";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";

export function AshaCitizenRequestDetailScreen() {
  const { requestId } = useParams<{ requestId: string }>();
  const navigate = useNavigate();
  const [requestData, setRequestData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isActioning, setIsActioning] = useState(false);

  // Action Modals State
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduledDate, setScheduledDate] = useState(new Date().toISOString().split("T")[0]);
  const [timeSlot, setTimeSlot] = useState("MORNING");

  const [showEscalateModal, setShowEscalateModal] = useState(false);
  const [escalateReason, setEscalateReason] = useState("");

  const [showRequestInfoModal, setShowRequestInfoModal] = useState(false);
  const [infoRequestNotes, setInfoRequestNotes] = useState("");

  const [showCompleteModal, setShowCompleteModal] = useState(false);
  const [completionNotes, setCompletionNotes] = useState("Home visit completed, guidance provided, patient stable.");

  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  const fetchDetail = async () => {
    if (!requestId) {
      setErrorMsg("Missing Request ID in URL");
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await apiClient.getAshaCitizenRequestDetail(requestId);
      setRequestData(res?.data || res);
    } catch (err: any) {
      console.error("Failed to load citizen request detail", err);
      const msg = err.response?.data?.detail || err.message || "Failed to load request details";
      setErrorMsg(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [requestId]);

  const handleAction = async (action: string, extraData: any = {}) => {
    if (!requestId) return;
    try {
      setIsActioning(true);
      await apiClient.patchAshaCitizenRequestStatus(requestId, { action, ...extraData });
      await fetchDetail();
      setShowScheduleModal(false);
      setShowEscalateModal(false);
      setShowRequestInfoModal(false);
      setShowCompleteModal(false);
      setShowCancelModal(false);
    } catch (err: any) {
      console.error(`Failed to execute action ${action}`, err);
      alert(`Action failed: ${err.message || "Server error"}`);
    } finally {
      setIsActioning(false);
    }
  };

  const handleCallCitizen = async () => {
    if (!requestData?.citizen_phone) return;
    try {
      // Fire action audit in background
      apiClient.patchAshaCitizenRequestStatus(requestId!, { action: "CALL_INITIATED" }).catch(() => {});
    } finally {
      window.open(`tel:${requestData.citizen_phone}`, "_self");
    }
  };

  const handleStartFieldVisit = () => {
    if (!requestData) return;
    const targetCaseId = requestData.case_id || requestData.id;
    navigate(`/asha/visit?caseId=${targetCaseId}&requestId=${requestData.id}&citizenId=${requestData.citizen_id || ''}&handoffId=${requestData.handoff_id || ''}`);
  };

  if (loading) {
    return (
      <div style={{ padding: "60px 20px", textAlign: "center", color: "var(--text-secondary)" }}>
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>Loading Citizen Assistance Request...</div>
        <div style={{ fontSize: 13 }}>Fetching clinical facts, safety profile & consent scope</div>
      </div>
    );
  }

  if (errorMsg || !requestData) {
    return (
      <div style={{ maxWidth: 600, margin: "40px auto", padding: 30, backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", textAlign: "center" }}>
        <div style={{ width: 48, height: 48, borderRadius: "50%", backgroundColor: "#FFEBEE", color: "#C62828", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
          <AlertCircle size={28} />
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>
          Unable to Load Citizen Request
        </h2>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 24 }}>
          {errorMsg || "The requested service request could not be found or you do not have authorization to view it."}
        </p>
        <button
          onClick={() => navigate("/asha/tasks?source=CITIZEN_REQUEST")}
          style={{ padding: "10px 20px", backgroundColor: "var(--primary)", color: "#FFF", borderRadius: 8, border: "none", fontWeight: 700, fontSize: 13, cursor: "pointer" }}
        >
          Return to Citizen Requests
        </button>
      </div>
    );
  }

  const packet = requestData.handoff_packet || {};
  const safety = requestData.safety_snapshot || packet.safety || {};
  const consent = requestData.consent || {};
  const patientContext = requestData.patient_context || {};
  const status = requestData.status || "NEW";
  const isUrgent = requestData.priority === "URGENT" || requestData.priority === "EMERGENCY" || safety.priority === "URGENT";

  // Calculate waiting time
  const submittedTime = new Date(requestData.submitted_at || requestData.created_at);
  const diffHours = Math.round((new Date().getTime() - submittedTime.getTime()) / (1000 * 60 * 60));
  const waitingText = diffHours < 1 ? "Just now" : diffHours === 1 ? "1 hour ago" : `${diffHours} hours ago`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 1200, margin: "0 auto" }}>
      {/* Top Breadcrumb & Quick Reference Bar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <button
          onClick={() => navigate("/asha/tasks?source=CITIZEN_REQUEST")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            backgroundColor: "var(--surface)",
            border: "1px solid var(--border)",
            padding: "8px 14px",
            borderRadius: 8,
            fontWeight: 600,
            fontSize: 13,
            cursor: "pointer",
            color: "var(--text-primary)"
          }}
        >
          <ArrowLeft size={16} />
          <span>Back to Citizen Requests</span>
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, fontFamily: "monospace", fontWeight: 700, padding: "4px 8px", backgroundColor: "var(--surface)", borderRadius: 6, border: "1px solid var(--border)" }}>
            Ref: {requestData.request_reference || requestData.id}
          </span>
          <span style={{ fontSize: 12, fontWeight: 700, padding: "4px 10px", backgroundColor: "#E8F5E9", color: "#2E7D32", borderRadius: 12 }}>
            Source: Citizen Chat
          </span>
        </div>
      </div>

      {/* Main Request Header Banner */}
      <div
        style={{
          backgroundColor: isUrgent ? "var(--urgent-bg)" : "var(--surface)",
          border: isUrgent ? "1px solid #F5C6CB" : "1px solid var(--border)",
          borderRadius: 12,
          padding: 24,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: 20
        }}
      >
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: 12,
              backgroundColor: isUrgent ? "var(--urgent)" : "var(--primary)",
              color: "#FFF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0
            }}
          >
            <User size={28} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>
                {requestData.citizen_name}
              </h1>
              {requestData.citizen_age && (
                <span style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 600 }}>
                  ({requestData.citizen_age}y · {requestData.citizen_gender || "Female"})
                </span>
              )}
              {requestData.is_pregnant && (
                <span style={{ padding: "2px 8px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                  Pregnant ({requestData.gestational_weeks ? `${requestData.gestational_weeks}w` : "Maternal"})
                </span>
              )}
              <PriorityBadge priority={requestData.priority} />
              <StatusBadge status={status} />
            </div>

            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 6, display: "flex", gap: 12, flexWrap: "wrap" }}>
              <span>📍 {requestData.village_name || "Kalyanpur Village"}</span>
              <span>🗣 Language: {requestData.language || "mr-IN"}</span>
              <span>🕒 Waiting: <strong>{waitingText}</strong></span>
              <span>👩‍⚕️ Assigned ASHA: <strong>{requestData.assigned_asha_name || "Sita Patel"}</strong></span>
            </div>
          </div>
        </div>

        {/* Header Actions */}
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          {requestData.citizen_phone && (
            <button
              onClick={handleCallCitizen}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "10px 16px",
                backgroundColor: "var(--teal)",
                color: "#FFF",
                borderRadius: 8,
                border: "none",
                fontWeight: 700,
                fontSize: 13,
                cursor: "pointer"
              }}
            >
              <Phone size={16} />
              <span>Call ({requestData.citizen_phone})</span>
            </button>
          )}
        </div>
      </div>

      {/* Grid Layout: 2 Cols Left (Clinical Facts), 1 Col Right (Action Palette & History) */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20, alignItems: "start" }}>
        {/* Left Column (Clinical Facts & Patient Context) */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20, gridColumn: "span 2" }}>
          {/* Section 1: Citizen Stated Health Concern & Symptoms */}
          <div style={{ backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", padding: 20 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Activity size={18} color="var(--primary)" />
                <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
                  Citizen Reported Health Concern
                </h2>
              </div>
              <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", backgroundColor: "#E3F2FD", color: "#1976D2", borderRadius: 8 }}>
                AI_STRUCTURED_CITIZEN_CONFIRMED
              </span>
            </div>

            <div style={{ backgroundColor: "var(--background)", padding: 14, borderRadius: 8, marginBottom: 16, borderLeft: "4px solid var(--primary)" }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 4 }}>CHIEF CONCERN</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                {requestData.chief_concern || "Home visit assistance requested"}
              </div>
              {requestData.citizen_summary && (
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 6 }}>
                  "{requestData.citizen_summary}"
                </div>
              )}
            </div>

            {/* Confirmed & Negated Symptoms */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 8 }}>
                  CONFIRMED SYMPTOMS
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {(requestData.symptoms && requestData.symptoms.length > 0 ? requestData.symptoms : [{ display: requestData.chief_concern }]).map((s: any, idx: number) => (
                    <span key={idx} style={{ fontSize: 12, fontWeight: 600, padding: "4px 10px", backgroundColor: "#E3F2FD", color: "#1565C0", borderRadius: 6 }}>
                      ✓ {typeof s === "string" ? s : s.display || s.term || s.code}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 8 }}>
                  EXPLICITLY DENIED SYMPTOMS
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {requestData.negated_symptoms && requestData.negated_symptoms.length > 0 ? (
                    requestData.negated_symptoms.map((ns: any, idx: number) => (
                      <span key={idx} style={{ fontSize: 12, fontWeight: 600, padding: "4px 10px", backgroundColor: "#ECEFF1", color: "#546E7A", borderRadius: 6 }}>
                        ✕ {typeof ns === "string" ? ns : ns.display || ns.term}
                      </span>
                    ))
                  ) : (
                    <span style={{ fontSize: 12, color: "var(--text-secondary)", fontStyle: "italic" }}>None recorded</span>
                  )}
                </div>
              </div>
            </div>

            {/* Vitals & Preferences */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, borderTop: "1px solid var(--border)", paddingTop: 14 }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)" }}>REPORTED VITALS</div>
                <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>
                  {requestData.vitals?.temperature_f ? `Temp: ${requestData.vitals.temperature_f}°F` : "No vitals self-reported"}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)" }}>PREFERRED VISIT TIME</div>
                <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>
                  {requestData.preferred_time_window || "ANYTIME"}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-secondary)" }}>LOCATION / LANDMARK</div>
                <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>
                  {requestData.location?.landmark || requestData.details?.landmark || requestData.village_name || "Kalyanpur"}
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Deterministic Safety Evaluation */}
          <div
            style={{
              backgroundColor: isUrgent ? "#FFEBEE" : "#E8F5E9",
              border: isUrgent ? "1px solid #FFCDD2" : "1px solid #C8E6C9",
              borderRadius: 12,
              padding: 18,
              display: "flex",
              gap: 14,
              alignItems: "flex-start"
            }}
          >
            <div style={{ color: isUrgent ? "#C62828" : "#2E7D32", marginTop: 2 }}>
              {isUrgent ? <AlertTriangle size={22} /> : <ShieldCheck size={22} />}
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 800, color: isUrgent ? "#B71C1C" : "#1B5E20" }}>
                Deterministic Clinical Safety Assessment ({safety.priority || requestData.priority || "ROUTINE"})
              </div>
              <p style={{ margin: "4px 0 8px", fontSize: 13, color: isUrgent ? "#C62828" : "#2E7D32", lineHeight: "20px" }}>
                {safety.citizen_message || safety.reason || "Standard rural health visit request. No critical danger signs triggered."}
              </p>
              {safety.triggered_rule_ids && safety.triggered_rule_ids.length > 0 && (
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                  {safety.triggered_rule_ids.map((rule: string, idx: number) => (
                    <span key={idx} style={{ fontSize: 10, fontWeight: 700, padding: "2px 6px", backgroundColor: "#FFCDD2", color: "#B71C1C", borderRadius: 4 }}>
                      Rule: {rule}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Section 3: Consent & Sharing Metadata */}
          <div style={{ backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", padding: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <Shield size={18} color="var(--primary)" />
              <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                Citizen Consent & Provenance
              </h2>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, fontSize: 12 }}>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Consent Recorded:</span>
                <div style={{ fontWeight: 600, marginTop: 2 }}>
                  {new Date(consent.consented_at || requestData.created_at).toLocaleString()}
                </div>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Authorized Recipient:</span>
                <div style={{ fontWeight: 600, marginTop: 2 }}>ASHA_WORKER</div>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Handoff Version:</span>
                <div style={{ fontWeight: 600, marginTop: 2 }}>v{requestData.handoff_version || 1}.0</div>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)" }}>Provenance:</span>
                <div style={{ fontWeight: 600, marginTop: 2 }}>CITIZEN_REPORTED</div>
              </div>
            </div>
          </div>

          {/* Section 4: Registered Patient Profile Context */}
          {patientContext.registered && (
            <div style={{ backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", padding: 20 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <FileText size={18} color="var(--primary)" />
                  <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                    Registered Patient Context
                  </h2>
                </div>
                {patientContext.citizen_id && (
                  <button
                    onClick={() => navigate(`/asha/cases/${requestData.case_id}`)}
                    style={{ fontSize: 12, fontWeight: 700, color: "var(--primary)", background: "none", border: "none", cursor: "pointer" }}
                  >
                    View Full Medical File →
                  </button>
                )}
              </div>

              {patientContext.active_cases && patientContext.active_cases.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {patientContext.active_cases.map((ac: any, idx: number) => (
                    <div key={idx} style={{ padding: "10px 12px", backgroundColor: "var(--background)", borderRadius: 6, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 700 }}>{ac.primary_concern}</div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Ref: {ac.reference} · Opened {new Date(ac.created_at).toLocaleDateString()}</div>
                      </div>
                      <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", backgroundColor: "var(--surface)", borderRadius: 10 }}>
                        {ac.status}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                  No prior chronic health cases registered for this beneficiary.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: State Dependent Action Bar & State History */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Action Palette Card */}
          <div style={{ backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", padding: 20 }}>
            <h2 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 800, color: "var(--text-primary)" }}>
              ASHA Action Palette
            </h2>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {/* 1. Status: ASHA_ASSIGNED / NEW / SUBMITTED */}
              {(status === "ASHA_ASSIGNED" || status === "NEW" || status === "SUBMITTED" || status === "ASSIGNMENT_PENDING") && (
                <>
                  <button
                    disabled={isActioning}
                    onClick={() => handleAction("ACKNOWLEDGE")}
                    style={{
                      padding: "12px",
                      backgroundColor: "var(--teal)",
                      color: "#FFF",
                      borderRadius: 8,
                      border: "none",
                      fontWeight: 700,
                      fontSize: 13,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8
                    }}
                  >
                    <CheckCircle2 size={16} />
                    <span>Acknowledge Request</span>
                  </button>

                  <button
                    disabled={isActioning}
                    onClick={() => setShowRequestInfoModal(true)}
                    style={{
                      padding: "10px",
                      backgroundColor: "var(--surface)",
                      color: "var(--text-primary)",
                      borderRadius: 8,
                      border: "1px solid var(--border)",
                      fontWeight: 600,
                      fontSize: 13,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6
                    }}
                  >
                    <Info size={16} />
                    <span>Request Information</span>
                  </button>
                </>
              )}

              {/* 2. Status: ASHA_ACKNOWLEDGED */}
              {status === "ASHA_ACKNOWLEDGED" && (
                <>
                  <button
                    disabled={isActioning}
                    onClick={() => handleAction("MARK_CONTACTED")}
                    style={{
                      padding: "12px",
                      backgroundColor: "#1976D2",
                      color: "#FFF",
                      borderRadius: 8,
                      border: "none",
                      fontWeight: 700,
                      fontSize: 13,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8
                    }}
                  >
                    <Phone size={16} />
                    <span>Mark Contacted</span>
                  </button>

                  <button
                    disabled={isActioning}
                    onClick={() => setShowScheduleModal(true)}
                    style={{
                      padding: "10px",
                      backgroundColor: "var(--primary)",
                      color: "#FFF",
                      borderRadius: 8,
                      border: "none",
                      fontWeight: 700,
                      fontSize: 13,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6
                    }}
                  >
                    <Calendar size={16} />
                    <span>Schedule Visit</span>
                  </button>

                  <button
                    disabled={isActioning}
                    onClick={() => handleAction("MARK_UNREACHABLE")}
                    style={{
                      padding: "10px",
                      backgroundColor: "var(--surface)",
                      color: "#C62828",
                      borderRadius: 8,
                      border: "1px solid #FFCDD2",
                      fontWeight: 600,
                      fontSize: 13,
                      cursor: "pointer"
                    }}
                  >
                    Mark Unreachable
                  </button>
                </>
              )}

              {/* 3. Status: CITIZEN_CONTACTED */}
              {status === "CITIZEN_CONTACTED" && (
                <>
                  <button
                    disabled={isActioning}
                    onClick={() => setShowScheduleModal(true)}
                    style={{
                      padding: "12px",
                      backgroundColor: "var(--primary)",
                      color: "#FFF",
                      borderRadius: 8,
                      border: "none",
                      fontWeight: 700,
                      fontSize: 13,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8
                    }}
                  >
                    <Calendar size={16} />
                    <span>Schedule Field Visit</span>
                  </button>

                  <button
                    disabled={isActioning}
                    onClick={handleStartFieldVisit}
                    style={{
                      padding: "12px",
                      backgroundColor: "var(--teal)",
                      color: "#FFF",
                      borderRadius: 8,
                      border: "none",
                      fontWeight: 700,
                      fontSize: 13,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8
                    }}
                  >
                    <HomeIcon size={16} />
                    <span>Start Field Visit</span>
                  </button>

                  <button
                    disabled={isActioning}
                    onClick={() => setShowEscalateModal(true)}
                    style={{
                      padding: "10px",
                      backgroundColor: "#FFEBEE",
                      color: "#C62828",
                      borderRadius: 8,
                      border: "1px solid #FFCDD2",
                      fontWeight: 700,
                      fontSize: 13,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6
                    }}
                  >
                    <Stethoscope size={16} />
                    <span>Escalate to PHC Doctor</span>
                  </button>
                </>
              )}

              {/* 4. Status: VISIT_SCHEDULED */}
              {status === "VISIT_SCHEDULED" && (
                <>
                  <button
                    disabled={isActioning}
                    onClick={handleStartFieldVisit}
                    style={{
                      padding: "12px",
                      backgroundColor: "var(--teal)",
                      color: "#FFF",
                      borderRadius: 8,
                      border: "none",
                      fontWeight: 700,
                      fontSize: 13,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8
                    }}
                  >
                    <HomeIcon size={16} />
                    <span>Start Field Visit</span>
                  </button>

                  <button
                    disabled={isActioning}
                    onClick={() => setShowScheduleModal(true)}
                    style={{
                      padding: "10px",
                      backgroundColor: "var(--surface)",
                      color: "var(--text-primary)",
                      borderRadius: 8,
                      border: "1px solid var(--border)",
                      fontWeight: 600,
                      fontSize: 13,
                      cursor: "pointer"
                    }}
                  >
                    Reschedule Visit
                  </button>

                  <button
                    disabled={isActioning}
                    onClick={() => setShowCancelModal(true)}
                    style={{
                      padding: "10px",
                      backgroundColor: "#FFEBEE",
                      color: "#C62828",
                      borderRadius: 8,
                      border: "1px solid #FFCDD2",
                      fontWeight: 600,
                      fontSize: 13,
                      cursor: "pointer"
                    }}
                  >
                    Cancel Visit
                  </button>
                </>
              )}

              {/* 5. Status: VISIT_IN_PROGRESS */}
              {status === "VISIT_IN_PROGRESS" && (
                <>
                  <button
                    onClick={handleStartFieldVisit}
                    style={{
                      padding: "12px",
                      backgroundColor: "var(--teal)",
                      color: "#FFF",
                      borderRadius: 8,
                      border: "none",
                      fontWeight: 700,
                      fontSize: 13,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8
                    }}
                  >
                    <HomeIcon size={16} />
                    <span>Continue Field Visit</span>
                  </button>

                  <button
                    disabled={isActioning}
                    onClick={() => setShowCompleteModal(true)}
                    style={{
                      padding: "10px",
                      backgroundColor: "#2E7D32",
                      color: "#FFF",
                      borderRadius: 8,
                      border: "none",
                      fontWeight: 700,
                      fontSize: 13,
                      cursor: "pointer"
                    }}
                  >
                    Complete Request
                  </button>
                </>
              )}

              {/* 6. Status: COMPLETED / REFERRED_TO_PHC */}
              {(status === "COMPLETED" || status === "REFERRED_TO_PHC") && (
                <div style={{ textAlign: "center", padding: "16px 0", color: "var(--text-secondary)" }}>
                  <CheckCircle2 size={36} color="#2E7D32" style={{ margin: "0 auto 8px" }} />
                  <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                    {status === "COMPLETED" ? "Request Completed" : "Escalated to PHC Doctor"}
                  </div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>
                    {status === "COMPLETED"
                      ? "Field visit has been successfully conducted and recorded."
                      : "Case is in PHC doctor triage queue for consultation."}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Status Timeline History Card */}
          {requestData.status_history && requestData.status_history.length > 0 && (
            <div style={{ backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", padding: 20 }}>
              <h2 style={{ margin: "0 0 14px", fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                Request Status Timeline
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {requestData.status_history.map((h: any, idx: number) => (
                  <div key={idx} style={{ borderLeft: "2px solid var(--primary)", paddingLeft: 12, position: "relative" }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                      {h.to_status ? h.to_status.replace(/_/g, " ") : "STATUS UPDATE"}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                      {h.reason || `Action by ${h.actor_role || 'ASHA'}`}
                    </div>
                    <div style={{ fontSize: 10, color: "var(--text-secondary)", marginTop: 4 }}>
                      {new Date(h.occurred_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · {new Date(h.occurred_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Schedule Modal */}
      {showScheduleModal && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.5)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <div style={{ backgroundColor: "var(--surface)", borderRadius: 12, padding: 24, maxWidth: 440, width: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Schedule Field Visit</h3>
            <div>
              <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 6 }}>Visit Date</label>
              <input
                type="date"
                value={scheduledDate}
                onChange={(e) => setScheduledDate(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--background)", color: "var(--text-primary)" }}
              />
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 6 }}>Time Window</label>
              <select
                value={timeSlot}
                onChange={(e) => setTimeSlot(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--background)", color: "var(--text-primary)" }}
              >
                <option value="MORNING">Morning (9:00 AM - 12:00 PM)</option>
                <option value="AFTERNOON">Afternoon (12:00 PM - 3:00 PM)</option>
                <option value="EVENING">Evening (3:00 PM - 6:00 PM)</option>
              </select>
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
              <button onClick={() => setShowScheduleModal(false)} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer" }}>
                Cancel
              </button>
              <button
                onClick={() => handleAction("SCHEDULE_VISIT", { scheduled_date: scheduledDate, scheduled_time_slot: timeSlot })}
                style={{ padding: "8px 16px", borderRadius: 8, border: "none", backgroundColor: "var(--primary)", color: "#FFF", fontWeight: 700, cursor: "pointer" }}
              >
                Confirm Schedule
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Escalate Modal */}
      {showEscalateModal && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.5)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <div style={{ backgroundColor: "var(--surface)", borderRadius: 12, padding: 24, maxWidth: 460, width: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#C62828" }}>Escalate to PHC Doctor</h3>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
              This will create a referral in the Kalyanpur PHC doctor queue for immediate clinical triage.
            </p>
            <div>
              <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 6 }}>Clinical Reason for Escalation</label>
              <textarea
                rows={3}
                placeholder="Severe fever, blood pressure red flags, or medication review needed..."
                value={escalateReason}
                onChange={(e) => setEscalateReason(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--background)", color: "var(--text-primary)", fontSize: 13 }}
              />
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
              <button onClick={() => setShowEscalateModal(false)} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer" }}>
                Cancel
              </button>
              <button
                onClick={() => handleAction("ESCALATE_PHC", { reason: escalateReason })}
                style={{ padding: "8px 16px", borderRadius: 8, border: "none", backgroundColor: "#C62828", color: "#FFF", fontWeight: 700, cursor: "pointer" }}
              >
                Confirm Escalation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Request Info Modal */}
      {showRequestInfoModal && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.5)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <div style={{ backgroundColor: "var(--surface)", borderRadius: 12, padding: 24, maxWidth: 440, width: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Request Missing Information</h3>
            <div>
              <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 6 }}>Notes for Citizen</label>
              <textarea
                rows={3}
                placeholder="Please share updated landmark or symptom duration..."
                value={infoRequestNotes}
                onChange={(e) => setInfoRequestNotes(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--background)", color: "var(--text-primary)", fontSize: 13 }}
              />
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
              <button onClick={() => setShowRequestInfoModal(false)} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer" }}>
                Cancel
              </button>
              <button
                onClick={() => handleAction("REQUEST_INFO", { notes: infoRequestNotes })}
                style={{ padding: "8px 16px", borderRadius: 8, border: "none", backgroundColor: "var(--primary)", color: "#FFF", fontWeight: 700, cursor: "pointer" }}
              >
                Send Request
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Complete Modal */}
      {showCompleteModal && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.5)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <div style={{ backgroundColor: "var(--surface)", borderRadius: 12, padding: 24, maxWidth: 440, width: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Complete Request</h3>
            <div>
              <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 6 }}>Completion Summary</label>
              <textarea
                rows={3}
                value={completionNotes}
                onChange={(e) => setCompletionNotes(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--background)", color: "var(--text-primary)", fontSize: 13 }}
              />
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
              <button onClick={() => setShowCompleteModal(false)} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer" }}>
                Cancel
              </button>
              <button
                onClick={() => handleAction("COMPLETE", { notes: completionNotes })}
                style={{ padding: "8px 16px", borderRadius: 8, border: "none", backgroundColor: "#2E7D32", color: "#FFF", fontWeight: 700, cursor: "pointer" }}
              >
                Mark Completed
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Modal */}
      {showCancelModal && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.5)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <div style={{ backgroundColor: "var(--surface)", borderRadius: 12, padding: 24, maxWidth: 440, width: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#C62828" }}>Cancel Request</h3>
            <div>
              <label style={{ fontSize: 12, fontWeight: 700, display: "block", marginBottom: 6 }}>Cancellation Reason</label>
              <textarea
                rows={3}
                placeholder="Reason for cancellation (e.g. citizen relocated or visited PHC directly)..."
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--background)", color: "var(--text-primary)", fontSize: 13 }}
              />
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
              <button onClick={() => setShowCancelModal(false)} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer" }}>
                Back
              </button>
              <button
                onClick={() => handleAction("CANCEL", { reason: cancelReason })}
                style={{ padding: "8px 16px", borderRadius: 8, border: "none", backgroundColor: "#C62828", color: "#FFF", fontWeight: 700, cursor: "pointer" }}
              >
                Confirm Cancellation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

