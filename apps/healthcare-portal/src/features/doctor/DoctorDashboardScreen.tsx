import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { useLanguage } from "../../context/LanguageContext";
import { PriorityBadge } from "../../components/StatusBadge";
import {
  WarningIcon,
  CheckCircleIcon,
  ActivityIcon,
  SearchIcon,
  StethoscopeIcon,
  PeopleIcon,
  VisitIcon,
  ChevronRightIcon,
  PillIcon,
} from "../../components/Icons";
import { useRealtime } from "../../hooks/useRealtime";
import { doctorPaths } from "./doctorRoutes";
import { getEventMetadata, formatRelativeTime, formatIndiaTimestamp } from "./DoctorActivityScreen";

export function DoctorDashboardScreen() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState<string | null>(null);

  const [clinicalWorkSummary, setClinicalWorkSummary] = useState<any>(null);
  const [cwLoading, setCwLoading] = useState(true);
  const [cwError, setCwError] = useState(false);

  const fetchDashboard = async () => {
    try {
      const res = await apiClient.getDoctorDashboard();
      setData(res);
    } catch (err) {
      console.error("Failed to load doctor dashboard", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchClinicalWork = async () => {
    try {
      setCwError(false);
      const summary = await apiClient.getClinicalWorkSummary();
      setClinicalWorkSummary(summary);
    } catch (err) {
      console.error("Failed to load clinical work summary", err);
      setCwError(true);
    } finally {
      setCwLoading(false);
    }
  };

  useRealtime((event) => {
    if (
      [
        "REFERRAL_CREATED",
        "REFERRAL_ACKNOWLEDGED",
        "PATIENT_ARRIVED",
        "CONSULTATION_STARTED",
        "CONSULTATION_COMPLETED",
        "INVESTIGATION_RESULT_AVAILABLE",
        "INVESTIGATION_RESULT_REVIEWED",
        "FOLLOWUP_COMPLETED",
        "FOLLOWUP_ESCALATED",
        "FOLLOWUP_REVIEWED",
        "VISIT_COMPLETED",
      ].includes(event)
    ) {
      console.log(`[RealTime] Doctor dashboard refresh on event: ${event}`);
      fetchDashboard();
      fetchClinicalWork();
    }
  });

  useEffect(() => {
    fetchDashboard();
    fetchClinicalWork();
    const timer = setInterval(() => {
      fetchDashboard();
      fetchClinicalWork();
    }, 15000);
    return () => clearInterval(timer);
  }, []);

  // Action Handlers
  const handleAcknowledgeReferral = async (e: React.MouseEvent, refItem: any) => {
    e.stopPropagation();
    setIsProcessing(refItem.id);
    try {
      await apiClient.acknowledgeReferral(refItem.case_id || refItem.id);
      await fetchDashboard();
    } catch (err) {
      console.error("Failed to acknowledge referral", err);
    } finally {
      setIsProcessing(null);
    }
  };

  const handleMarkArrived = async (e: React.MouseEvent, refItem: any) => {
    e.stopPropagation();
    setIsProcessing(refItem.id);
    try {
      await apiClient.markPatientArrived(refItem.id);
      await fetchDashboard();
    } catch (err) {
      console.error("Failed to mark patient arrived", err);
    } finally {
      setIsProcessing(null);
    }
  };

  const handleStartConsultation = async (e: React.MouseEvent, refItem: any) => {
    e.stopPropagation();
    setIsProcessing(refItem.id);
    try {
      const targetId = refItem.id || refItem.case_id;
      const res = await apiClient.startConsultation(targetId);
      const consId = res?.consultation_id || res?.data?.consultation_id || res?.reference || refItem.case_id;
      navigate(doctorPaths.consultation(consId));
    } catch (err) {
      console.error("Failed to start consultation, navigating by case_id", err);
      navigate(doctorPaths.consultation(refItem.case_id || refItem.id));
    } finally {
      setIsProcessing(null);
    }
  };

  const handleAcknowledgeEscalation = async (e: React.MouseEvent, escItem: any) => {
    e.stopPropagation();
    setIsProcessing(escItem.id);
    try {
      await apiClient.acknowledgeDoctorEscalation(escItem.followup_id);
      await fetchDashboard();
    } catch (err) {
      console.error("Failed to acknowledge escalation", err);
    } finally {
      setIsProcessing(null);
    }
  };

  if (loading && !data) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
        {t("doctor.loading_queue", "Loading PHC clinical queue...")}
      </div>
    );
  }

  const metrics = data?.metrics || {
    new_referrals_count: data?.urgent_referrals_count || 0,
    urgent_cases_count: data?.urgent_referrals_count || 0,
    awaiting_consultation_count: 0,
    asha_followups_count: data?.pending_followups_count || 0,
    escalations_count: 0,
    completed_today_count: data?.today_consultations_count || 0,
  };

  const incomingReferrals: any[] = data?.incoming_referrals || data?.referrals || [];
  const urgentSummary = data?.urgent_summary;
  const todayWork = data?.today_clinical_work || {
    patients_arrived: 0,
    consultations_in_progress: 0,
    pending_investigations: 1,
    followups_to_review: metrics.asha_followups_count,
  };
  const ashaFollowups: any[] = data?.asha_followups || [];
  const escalations: any[] = data?.escalations || [];
  const recentActivities: any[] = data?.recent_activity || [];

  // Filtering & Search
  const filteredReferrals = incomingReferrals.filter((r) => {
    if (activeFilter === "URGENT" && r.urgency !== "URGENT" && r.urgency !== "HIGH") return false;
    if (activeFilter === "NEW" && !["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"].includes(r.status)) return false;
    if (activeFilter === "ACKNOWLEDGED" && !["DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED"].includes(r.status)) return false;
    if (activeFilter === "ARRIVED" && r.arrival_status !== "ARRIVED" && r.status !== "PATIENT_ARRIVED") return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      const nameMatch = r.citizen_name?.toLowerCase().includes(q);
      const caseMatch = r.case_reference?.toLowerCase().includes(q);
      const refMatch = r.reference?.toLowerCase().includes(q);
      const ashaMatch = r.referring_asha_name?.toLowerCase().includes(q);
      const villageMatch = r.village_name?.toLowerCase().includes(q);
      if (!nameMatch && !caseMatch && !refMatch && !ashaMatch && !villageMatch) {
        return false;
      }
    }
    return true;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 1440, margin: "0 auto", width: "100%" }}>
      {/* Top Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
            {t("doctor.phc_doctor_dashboard", "PHC Doctor Dashboard")}
          </h1>
          <div style={{ fontSize: 14, color: "var(--text-secondary)", marginTop: 4 }}>
            {data?.facility_name || "Assigned Primary Health Centre"} · {data?.doctor_name || "Medical Officer"} ({data?.doctor_role || "PHC Medical Officer"})
          </div>
        </div>

        <Link
          to="/doctor/direct-requests"
          style={{
            padding: "10px 18px",
            backgroundColor: "#2563EB",
            color: "#FFF",
            borderRadius: 12,
            textDecoration: "none",
            fontSize: 13,
            fontWeight: 800,
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            boxShadow: "0 4px 12px rgba(37, 99, 235, 0.2)"
          }}
        >
          <StethoscopeIcon size={16} color="#FFF" />
          <span>{t("doctor.view_direct_requests", "View Direct Citizen Requests →")}</span>
        </Link>
      </div>

      {/* Urgent Referral Banner (Shown only when urgent unacknowledged items exist) */}
      {urgentSummary && urgentSummary.count > 0 && (
        <div
          style={{
            backgroundColor: "var(--urgent-bg)",
            border: "1px solid #F5C6CB",
            borderRadius: 12,
            padding: "16px 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "50%",
                backgroundColor: "var(--urgent)",
                color: "#FFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <WarningIcon size={24} color="#FFF" />
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "var(--urgent)" }}>
                {urgentSummary.count}{" "}
                {t(
                  urgentSummary.count === 1 ? "doctor.urgent_referral_alert_single" : "doctor.urgent_referral_alert_plural",
                  urgentSummary.count === 1 ? "Urgent PHC Referral Waiting Doctor Review" : "Urgent PHC Referrals Waiting Doctor Review"
                )}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-primary)", marginTop: 2 }}>
                {urgentSummary.count > 1 ? (
                  <>
                    <span style={{ fontWeight: 600, color: "var(--urgent)" }}>{t("doctor.latest_case", "Latest")}: </span>
                    <span>{urgentSummary.patient_name || t("doctor.unnamed_patient", "Patient")}</span>
                    <span> · {t("doctor.referring_asha_label", "Referring ASHA")}: {urgentSummary.referring_asha_name || t("doctor.unassigned_asha", "ASHA")}</span>
                    <span> · {t("doctor.reason_label", "Reason")}: {urgentSummary.reason || t("doctor.default_urgent_reason", "Immediate PHC clinical evaluation required")}</span>
                  </>
                ) : (
                  <>
                    <span>{t("doctor.patient_label", "Patient")}: {urgentSummary.patient_name || t("doctor.unnamed_patient", "Patient")}</span>
                    <span> · {t("doctor.referring_asha_label", "Referring ASHA")}: {urgentSummary.referring_asha_name || t("doctor.unassigned_asha", "ASHA")}</span>
                    <span> · {t("doctor.reason_label", "Reason")}: {urgentSummary.reason || t("doctor.default_urgent_reason", "Immediate PHC clinical evaluation required")}</span>
                  </>
                )}
              </div>
            </div>
          </div>
          <button
            onClick={() => {
              setActiveFilter("URGENT");
            }}
            style={{
              padding: "10px 18px",
              backgroundColor: "var(--urgent)",
              color: "#FFF",
              borderRadius: 8,
              border: "none",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            {t("doctor.review_urgent_referrals", "Review Urgent Referrals →")}
          </button>
        </div>
      )}

      {/* 6 Clickable Metric Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14 }}>
        {[
          { id: "NEW", title: t("doctor.new_referrals_card", "New Referrals"), count: metrics.new_referrals_count, color: "#1565C0", bg: "#E3F2FD", border: "#BBDEFB" },
          { id: "URGENT", title: t("doctor.urgent_cases_card", "Urgent Cases"), count: metrics.urgent_cases_count, color: "var(--urgent)", bg: "var(--urgent-bg)", border: "#F5C6CB" },
          { id: "ACKNOWLEDGED", title: t("doctor.awaiting_consultation_card", "Awaiting Consultation"), count: metrics.awaiting_consultation_count, color: "#D65A00", bg: "#FFF3E8", border: "#FFE8D6" },
          { id: "FOLLOWUPS", title: t("doctor.asha_followups_card", "ASHA Follow-ups"), count: metrics.asha_followups_count, color: "#B26A00", bg: "#FFF8E1", border: "#FFF3CD" },
          { id: "ESCALATIONS", title: t("doctor.escalations_card", "Escalations"), count: metrics.escalations_count, color: "#C2185B", bg: "#FCE4EC", border: "#F8BBD0" },
          { id: "COMPLETED", title: t("doctor.completed_today_card", "Completed Today"), count: metrics.completed_today_count, color: "var(--success)", bg: "var(--success-bg)", border: "#D4EDDA" },
        ].map((card) => {
          const isSelected = activeFilter === card.id;
          return (
            <div
              key={card.id}
              onClick={() => setActiveFilter(card.id)}
              style={{
                backgroundColor: "var(--surface)",
                padding: "16px 18px",
                borderRadius: 12,
                border: isSelected ? `2px solid ${card.color}` : `1px solid ${card.border || "var(--border)"}`,
                cursor: "pointer",
                transition: "all 0.15s ease-in-out",
                boxShadow: isSelected ? "0 2px 8px rgba(0,0,0,0.08)" : "none",
              }}
            >
              <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 600 }}>{card.title}</div>
              <div style={{ fontSize: 30, fontWeight: 800, color: card.color, marginTop: 4 }}>
                {card.count}
              </div>
            </div>
          );
        })}
      </div>

      {/* Main 2-Column Clinical Layout */}
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
        {/* Left Column: Incoming Referral Queue */}
        <div style={{ flex: "1 1 680px", minWidth: 320, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: 16 }}>
              <div>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
                  {t("doctor.incoming_referrals", "Incoming ASHA Referrals")} ({filteredReferrals.length})
                </h2>
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
                  {t("doctor.incoming_referrals_subtitle", "Patients triaged in the field requiring PHC Medical Officer consultation")}
                </div>
              </div>
              <Link
                to="/doctor/referrals"
                style={{ fontSize: 13, fontWeight: 600, color: "var(--primary)", textDecoration: "none" }}
              >
                {t("doctor.view_full_queue", "View Full Queue →")}
              </Link>
            </div>

            {/* Search and Filters Bar */}
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginBottom: 16 }}>
              <div
                style={{
                  flex: "1 1 240px",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  backgroundColor: "var(--neutral-bg)",
                  padding: "0 12px",
                  height: 38,
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                }}
              >
                <SearchIcon size={16} color="var(--text-secondary)" />
                <input
                  type="text"
                  placeholder={t("doctor.search_referrals_placeholder", "Search patient, case, referral or ASHA...")}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ border: "none", outline: "none", width: "100%", fontSize: 13, backgroundColor: "transparent" }}
                />
              </div>

              <div style={{ display: "flex", gap: 6, overflowX: "auto" }}>
                {[
                  { id: "ALL", label: t("doctor.filter_all", "All") },
                  { id: "URGENT", label: t("doctor.filter_urgent", "Urgent") },
                  { id: "NEW", label: t("doctor.filter_new", "New") },
                  { id: "ACKNOWLEDGED", label: t("doctor.filter_acknowledged", "Acknowledged") },
                  { id: "ARRIVED", label: t("doctor.filter_arrived", "Patient Arrived") },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveFilter(tab.id)}
                    style={{
                      padding: "6px 12px",
                      borderRadius: 6,
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: "pointer",
                      border: activeFilter === tab.id ? "2px solid var(--primary)" : "1px solid var(--border)",
                      backgroundColor: activeFilter === tab.id ? "var(--primary-light)" : "var(--surface)",
                      color: activeFilter === tab.id ? "var(--primary-dark)" : "var(--text-primary)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Referrals Cards List */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {filteredReferrals.length === 0 ? (
                <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)", backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                  No referrals match the selected filter.
                </div>
              ) : (
                filteredReferrals.map((ref: any) => {
                  const isUrgent = ref.urgency === "URGENT" || ref.urgency === "HIGH";
                  const isPending = ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"].includes(ref.status);
                  const isAcknowledged = ["DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED"].includes(ref.status);
                  const isArrived = ref.arrival_status === "ARRIVED" || ref.status === "PATIENT_ARRIVED";

                  return (
                    <div
                      key={ref.id}
                      data-testid={`referral-card-${ref.case_id}`}
                      style={{
                        padding: 18,
                        borderRadius: 10,
                        border: isUrgent ? "1px solid #F5C6CB" : "1px solid var(--border)",
                        backgroundColor: isUrgent ? "var(--urgent-bg)" : "var(--surface)",
                        display: "flex",
                        flexDirection: "column",
                        gap: 12,
                        boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                      }}
                    >
                      {/* Top Row: Patient Info, Category & Status Badges */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 10 }}>
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                            <span style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
                              {ref.citizen_name}
                            </span>
                            <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                              ({ref.citizen_age}y · {ref.citizen_gender || "Female"} · {ref.village_name || "Kalyanpur"})
                            </span>
                            {ref.is_pregnant && (
                              <span style={{ padding: "2px 8px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                                🤰 Maternal ({ref.gestational_weeks ? `${ref.gestational_weeks}w` : "28w"})
                              </span>
                            )}
                            {ref.category === "CHILD" && (
                              <span style={{ padding: "2px 8px", borderRadius: 12, backgroundColor: "#E0F2FE", color: "#0369A1", fontSize: 11, fontWeight: 700 }}>
                                👶 Child Health
                              </span>
                            )}
                            {ref.category === "NCD" && (
                              <span style={{ padding: "2px 8px", borderRadius: 12, backgroundColor: "#FEF3C7", color: "#92400E", fontSize: 11, fontWeight: 700 }}>
                                🩺 NCD
                              </span>
                            )}
                            <PriorityBadge priority={ref.urgency} size="sm" />
                          </div>

                          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, display: "flex", gap: 10, flexWrap: "wrap" }}>
                            <span>Ref: <strong>{ref.reference}</strong></span>
                            <span>Case: <strong>{ref.case_reference}</strong></span>
                            <span>Referred: <strong>{new Date(ref.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong></span>
                            <span>ASHA: <strong>{ref.referring_asha_name}</strong></span>
                          </div>
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span
                            style={{
                              padding: "4px 8px",
                              borderRadius: 6,
                              fontSize: 11,
                              fontWeight: 700,
                              backgroundColor: isArrived ? "#DEF7EC" : isAcknowledged ? "#E0E7FF" : "#FEF3C7",
                              color: isArrived ? "#03543F" : isAcknowledged ? "#3730A3" : "#92400E",
                            }}
                          >
                            {isArrived
                              ? `✓ ${t("doctor.patient_arrived_badge", "PATIENT ARRIVED")}`
                              : isAcknowledged
                              ? t("doctor.doctor_acknowledged_badge", "DOCTOR ACKNOWLEDGED")
                              : t("doctor.pending_review_badge", "PENDING REVIEW")}
                          </span>
                        </div>
                      </div>

                      {/* Middle Row: Non-diagnostic Triage Reason & Clinical Evidence */}
                      <div style={{ padding: 12, backgroundColor: "var(--surface)", borderRadius: 8, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 6 }}>
                        <div style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 600 }}>
                          ⚠️ {t("doctor.triage_reason_prefix", "Triage Reason")}: {ref.reason || "Elevated blood pressure and warning signs recorded. Doctor review required."}
                        </div>
                        {ref.citizen_reported_concern && (
                          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                            <strong>{t("doctor.citizen_concern_prefix", "Citizen concern")}:</strong> "{ref.citizen_reported_concern}"
                          </div>
                        )}
                        {ref.latest_vitals && (
                          <div style={{ fontSize: 12, color: "var(--primary-dark)", display: "flex", gap: 12, flexWrap: "wrap", marginTop: 2 }}>
                            {ref.latest_vitals.systolic_bp && (
                              <span><strong>BP:</strong> {ref.latest_vitals.systolic_bp}/{ref.latest_vitals.diastolic_bp} mmHg</span>
                            )}
                            {ref.latest_vitals.spo2 && <span><strong>SpO₂:</strong> {ref.latest_vitals.spo2}%</span>}
                            {ref.latest_vitals.pulse && <span><strong>Pulse:</strong> {ref.latest_vitals.pulse} bpm</span>}
                            {ref.latest_vitals.recorded_at && (
                              <span style={{ color: "var(--text-secondary)" }}>
                                (Recorded: {new Date(ref.latest_vitals.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Bottom Row: State-dependent Action Buttons */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                        <div style={{ display: "flex", gap: 6 }}>
                          {ref.referring_asha_phone && (
                            <a
                              href={`tel:${ref.referring_asha_phone}`}
                              onClick={(e) => e.stopPropagation()}
                              style={{
                                padding: "6px 12px",
                                backgroundColor: "var(--surface)",
                                border: "1px solid var(--border)",
                                borderRadius: 6,
                                fontSize: 12,
                                fontWeight: 600,
                                color: "#0369A1",
                                textDecoration: "none",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 4,
                              }}
                            >
                              📞 {t("doctor.call_asha", "Call ASHA")}
                            </a>
                          )}
                          <button
                            onClick={() => navigate(doctorPaths.caseTimeline(ref.case_id))}
                            style={{
                              padding: "6px 12px",
                              backgroundColor: "var(--surface)",
                              border: "1px solid var(--border)",
                              borderRadius: 6,
                              fontSize: 12,
                              fontWeight: 600,
                              color: "var(--text-primary)",
                              cursor: "pointer",
                            }}
                          >
                            {t("doctor.view_timeline", "View Timeline")}
                          </button>
                        </div>

                        <div style={{ display: "flex", gap: 8 }}>
                          {isPending && (
                            <button
                              disabled={isProcessing === ref.id}
                              onClick={(e) => handleAcknowledgeReferral(e, ref)}
                              style={{
                                padding: "8px 16px",
                                backgroundColor: "var(--primary)",
                                color: "#FFF",
                                border: "none",
                                borderRadius: 6,
                                fontSize: 13,
                                fontWeight: 700,
                                cursor: "pointer",
                              }}
                            >
                              {isProcessing === ref.id ? "Acknowledging..." : `✓ ${t("doctor.review_and_acknowledge", "Review & Acknowledge")}`}
                            </button>
                          )}

                          {isAcknowledged && !isArrived && (
                            <>
                              <button
                                disabled={isProcessing === ref.id}
                                onClick={(e) => handleMarkArrived(e, ref)}
                                style={{
                                  padding: "8px 14px",
                                  backgroundColor: "#DEF7EC",
                                  color: "#03543F",
                                  border: "1px solid #31C48D",
                                  borderRadius: 6,
                                  fontSize: 13,
                                  fontWeight: 700,
                                  cursor: "pointer",
                                }}
                              >
                                {isProcessing === ref.id ? "Updating..." : t("doctor.mark_arrived", "Mark Patient Arrived")}
                              </button>
                              <button
                                onClick={(e) => handleStartConsultation(e, ref)}
                                style={{
                                  padding: "8px 16px",
                                  backgroundColor: "var(--primary)",
                                  color: "#FFF",
                                  border: "none",
                                  borderRadius: 6,
                                  fontSize: 13,
                                  fontWeight: 700,
                                  cursor: "pointer",
                                }}
                              >
                                Start Consultation →
                              </button>
                            </>
                          )}

                          {isArrived && (
                            <button
                              onClick={(e) => handleStartConsultation(e, ref)}
                              style={{
                                padding: "8px 18px",
                                backgroundColor: "var(--success)",
                                color: "#FFF",
                                border: "none",
                                borderRadius: 6,
                                fontSize: 13,
                                fontWeight: 700,
                                cursor: "pointer",
                              }}
                            >
                              ▶ Start Consultation Now
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Clinical Rails */}
        <div style={{ flex: "1 1 360px", minWidth: 300, display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Today's Clinical Work Card */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
                Today's Clinical Work
              </h3>
              {clinicalWorkSummary?.generated_at && (
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  Updated: {new Date(clinicalWorkSummary.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
            </div>

            {cwLoading ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10, padding: 4 }}>
                <div style={{ height: 44, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }} />
                <div style={{ height: 44, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }} />
                <div style={{ height: 44, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }} />
                <div style={{ height: 44, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }} />
              </div>
            ) : cwError ? (
              <div style={{ padding: 16, backgroundColor: "#FEE2E2", borderRadius: 8, border: "1px solid #FCA5A5", textAlign: "center" }}>
                <div style={{ fontSize: 13, color: "#991B1B", marginBottom: 8, fontWeight: 600 }}>
                  Unable to load today's clinical work.
                </div>
                <button
                  onClick={fetchClinicalWork}
                  style={{ padding: "6px 14px", backgroundColor: "#991B1B", color: "#FFF", borderRadius: 6, border: "none", fontSize: 12, fontWeight: 700, cursor: "pointer" }}
                >
                  Retry
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {/* 1. Ready to Start Consultations */}
                <button
                  data-testid="clinical-work-row-ready-to-start"
                  aria-label={`Open ${clinicalWorkSummary?.ready_to_start ?? todayWork.patients_arrived} consultations ready to start`}
                  title="Count of patients who arrived at PHC waiting for a doctor consultation to begin"
                  onClick={() => navigate(doctorPaths.consultations({ status: "READY_TO_START" }))}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "12px 14px",
                    backgroundColor: "#F0FDF4",
                    border: "1px solid #BBF7D0",
                    borderRadius: 10,
                    cursor: "pointer",
                    textAlign: "left",
                    minHeight: 48,
                    width: "100%",
                    transition: "all 0.2s ease-in-out",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 18 }}>🟢</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: "#166534" }}>
                      Ready to Start Consultations
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 15, fontWeight: 800, color: "#15803D" }}>
                      {clinicalWorkSummary?.ready_to_start ?? todayWork.patients_arrived}
                    </span>
                    <ChevronRightIcon size={16} color="#15803D" />
                  </div>
                </button>

                {/* 2. Consultations in Progress */}
                <button
                  data-testid="clinical-work-row-in-progress"
                  aria-label={`Open ${clinicalWorkSummary?.consultations_in_progress ?? todayWork.consultations_in_progress} consultations in progress`}
                  title="Count of active un-signed doctor consultations currently in progress"
                  onClick={() => navigate(doctorPaths.consultations({ status: "IN_CONSULTATION" }))}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "12px 14px",
                    backgroundColor: "#EFF6FF",
                    border: "1px solid #BFDBFE",
                    borderRadius: 10,
                    cursor: "pointer",
                    textAlign: "left",
                    minHeight: 48,
                    width: "100%",
                    transition: "all 0.2s ease-in-out",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 18 }}>🩺</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: "#1E40AF" }}>
                      Consultations in Progress
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 15, fontWeight: 800, color: "#1D4ED8" }}>
                      {clinicalWorkSummary?.consultations_in_progress ?? todayWork.consultations_in_progress}
                    </span>
                    <ChevronRightIcon size={16} color="#1D4ED8" />
                  </div>
                </button>

                {/* 3. Results Ready for Review */}
                <button
                  data-testid="clinical-work-row-results-ready"
                  aria-label={`Open ${clinicalWorkSummary?.results_ready_for_review ?? todayWork.pending_investigations} test results ready for review`}
                  title="Count of lab investigation test results returned ready for doctor review"
                  onClick={() => navigate(doctorPaths.investigations({ status: "RESULT_AVAILABLE" }))}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "12px 14px",
                    backgroundColor: "#F3E8FF",
                    border: "1px solid #E9D5FF",
                    borderRadius: 10,
                    cursor: "pointer",
                    textAlign: "left",
                    minHeight: 48,
                    width: "100%",
                    transition: "all 0.2s ease-in-out",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 18 }}>🧪</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: "#6B21A8" }}>
                      Results Ready for Review
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 15, fontWeight: 800, color: "#7E22CE" }}>
                      {clinicalWorkSummary?.results_ready_for_review ?? todayWork.pending_investigations}
                    </span>
                    <ChevronRightIcon size={16} color="#7E22CE" />
                  </div>
                </button>

                {/* 4. ASHA Follow-ups to Review */}
                <button
                  data-testid="clinical-work-row-followups-to-review"
                  aria-label={`Open ${clinicalWorkSummary?.asha_followups_to_review ?? todayWork.followups_to_review} ASHA follow-ups to review`}
                  title="Count of home follow-up checkups completed or escalated by ASHA workers awaiting doctor sign-off"
                  onClick={() => navigate(doctorPaths.followUps({ status: "REVIEW_REQUIRED" }))}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "12px 14px",
                    backgroundColor: "#FEF3C7",
                    border: "1px solid #FDE68A",
                    borderRadius: 10,
                    cursor: "pointer",
                    textAlign: "left",
                    minHeight: 48,
                    width: "100%",
                    transition: "all 0.2s ease-in-out",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 18 }}>📋</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: "#92400E" }}>
                      ASHA Follow-ups to Review
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 15, fontWeight: 800, color: "#B45309" }}>
                      {clinicalWorkSummary?.asha_followups_to_review ?? todayWork.followups_to_review}
                    </span>
                    <ChevronRightIcon size={16} color="#B45309" />
                  </div>
                </button>
              </div>
            )}
          </div>

          {/* ASHA Escalations Alert Card (Amber Card) */}
          {escalations.length > 0 && (
            <div style={{ backgroundColor: "#FEF3C7", padding: 18, borderRadius: 12, border: "1px solid #FCD34D" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <WarningIcon size={20} color="#92400E" />
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "#92400E" }}>
                  ASHA Escalations ({escalations.length})
                </h3>
              </div>
              <p style={{ margin: "0 0 12px", fontSize: 12, color: "#78350F" }}>
                Field workers detected red-flag symptoms during home follow-ups.
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {escalations.map((esc) => (
                  <div key={esc.id} style={{ backgroundColor: "#FFF", padding: 12, borderRadius: 8, border: "1px solid #FDE68A" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <span style={{ fontSize: 14, fontWeight: 700 }}>{esc.citizen_name}</span>
                      <span style={{ fontSize: 11, color: "#92400E", fontWeight: 700 }}>{esc.village_name}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                      <strong>Reason:</strong> {esc.escalation_reason}
                    </div>
                    <div style={{ display: "flex", justifyContent: "flex-end", gap: 6, marginTop: 8 }}>
                      <button
                        onClick={async (e) => {
                          e.stopPropagation();
                          try {
                            await apiClient.callAshaOutcome(esc.id || esc.follow_up_id);
                            alert(`Call logged to ASHA worker ${esc.assigned_asha_name || 'Sita Patel'}`);
                          } catch (err) {
                            console.error(err);
                          }
                        }}
                        style={{
                          padding: "4px 10px",
                          backgroundColor: "#FFF",
                          color: "#92400E",
                          border: "1px solid #FDE68A",
                          borderRadius: 6,
                          fontSize: 11,
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                      >
                        📞 Call ASHA
                      </button>
                      <button
                        data-testid={`review-escalation-btn-${esc.follow_up_id || esc.id}`}
                        onClick={() => navigate(doctorPaths.followUp(esc.follow_up_id || esc.id))}
                        style={{
                          padding: "4px 10px",
                          backgroundColor: "#B45309",
                          color: "#FFF",
                          border: "none",
                          borderRadius: 6,
                          fontSize: 11,
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                      >
                        Review Escalation →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ASHA Follow-up Monitoring */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
                  {t("doctor.asha_followup_monitoring", "ASHA Follow-up Monitoring")}
                </h3>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  {t("doctor.followup_monitoring_desc", "Track adherence, repeated vitals & warning signs")}
                </span>
              </div>
              <Link to="/doctor/followups" style={{ fontSize: 12, color: "var(--primary)", fontWeight: 700, textDecoration: "none" }}>
                {t("doctor.view_all_followups", "View all follow-ups")} ({ashaFollowups.length}) →
              </Link>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {ashaFollowups.length === 0 ? (
                <div style={{ fontSize: 13, color: "var(--text-secondary)", textAlign: "center", padding: 20 }}>
                  {t("doctor.no_followups_recorded", "No pending ASHA follow-ups.")}
                </div>
              ) : (
                ashaFollowups.slice(0, 5).map((fup: any) => {
                  const statusKey = fup.status || "PENDING";
                  let badgeBg = "#F1F5F9";
                  let badgeColor = "#475569";
                  let badgeLabel = "Pending";
                  let badgeIcon = "⏳";
                  let primaryBtnText = "View Directive →";

                  if (statusKey === "ESCALATED") {
                    badgeBg = "#FEE2E2"; badgeColor = "#991B1B"; badgeLabel = "Escalated"; badgeIcon = "🚨";
                    primaryBtnText = "Review Escalation →";
                  } else if (statusKey === "OVERDUE") {
                    badgeBg = "#FFEDD5"; badgeColor = "#C2410C"; badgeLabel = "Overdue"; badgeIcon = "⚠️";
                    primaryBtnText = "Contact ASHA →";
                  } else if (statusKey === "COMPLETED" || statusKey === "RESULT_READY") {
                    badgeBg = "#E0F2FE"; badgeColor = "#0369A1"; badgeLabel = "Result Ready"; badgeIcon = "🧪";
                    primaryBtnText = "Review Result →";
                  } else if (statusKey === "REVIEWED" || statusKey === "RESOLVED") {
                    badgeBg = "#DCFCE7"; badgeColor = "#15803D"; badgeLabel = "Reviewed"; badgeIcon = "✓";
                    primaryBtnText = "View History →";
                  }

                  const fupId = fup.follow_up_id || fup.id;

                  return (
                    <div key={fupId} style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 10, border: "1px solid var(--border)", fontSize: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 6 }}>
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>{fup.patient_name || fup.citizen_name}</strong>
                            <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{fup.case_reference} · {fup.village_name || "Kalyanpur"}</span>
                          </div>
                          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>
                            {fup.patient_category || "MATERNAL"} · Priority: <strong>{fup.priority || "NORMAL"}</strong>
                          </div>
                        </div>

                        <span style={{ padding: "3px 8px", borderRadius: 6, backgroundColor: badgeBg, color: badgeColor, fontWeight: 700, fontSize: 11, display: "inline-flex", alignItems: "center", gap: 4 }}>
                          {badgeIcon} {badgeLabel}
                        </span>
                      </div>

                      <div style={{ margin: "8px 0 6px", fontSize: 12, color: "var(--text-primary)", fontWeight: 600 }}>
                        📋 {fup.directive || fup.reason || fup.instructions}
                      </div>

                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 6, marginTop: 8, paddingTop: 6, borderTop: "1px dashed var(--border)" }}>
                        <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                          ASHA: <strong>{fup.assigned_asha_name || "Sita Patel"}</strong> | Due: {fup.due_at ? new Date(fup.due_at).toLocaleDateString() : "Today"}
                        </span>

                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            onClick={async (e) => {
                              e.stopPropagation();
                              try {
                                await apiClient.recordAshaContact(fupId);
                                alert(`Call attempt logged to ASHA worker ${fup.assigned_asha_name || 'Sita Patel'}`);
                              } catch (err) {
                                console.error(err);
                              }
                            }}
                            style={{
                              padding: "4px 8px",
                              backgroundColor: "#FFF",
                              color: "var(--text-primary)",
                              border: "1px solid var(--border)",
                              borderRadius: 6,
                              fontSize: 11,
                              fontWeight: 600,
                              cursor: "pointer",
                            }}
                          >
                            📞 {t("doctor.call_asha", "Call ASHA")}
                          </button>
                          <button
                            data-testid={`fup-monitor-action-btn-${fupId}`}
                            onClick={() => navigate(doctorPaths.followUp(fupId))}
                            style={{
                              padding: "4px 10px",
                              backgroundColor: "var(--primary)",
                              color: "#FFF",
                              border: "none",
                              borderRadius: 6,
                              fontSize: 11,
                              fontWeight: 700,
                              cursor: "pointer",
                            }}
                          >
                            {primaryBtnText}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Recent Care Activity Stream */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
                  {t("doctor.recent_care_activity", "Recent Care Activity")}
                </h3>
                <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  {t("doctor.care_activity_desc", "PHC clinical care events & status transitions")}
                </span>
              </div>
              <Link to="/doctor/activity" style={{ fontSize: 12, color: "var(--primary)", fontWeight: 700, textDecoration: "none" }}>
                {t("doctor.view_all_activity", "View all activity")} →
              </Link>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {recentActivities.length === 0 ? (
                <div style={{ fontSize: 13, color: "var(--text-secondary)", textAlign: "center", padding: 20 }}>
                  {t("doctor.no_activity_recorded", "No recent care activity recorded.")}
                </div>
              ) : (
                recentActivities.slice(0, 8).map((act: any) => {
                  const meta = getEventMetadata(act.event_type);
                  const relTime = formatRelativeTime(act.occurred_at || act.timestamp);
                  const istTime = formatIndiaTimestamp(act.occurred_at || act.timestamp);

                  return (
                    <div
                      key={act.event_id || act.id}
                      tabIndex={0}
                      role="button"
                      aria-label={`Open details for ${act.title}`}
                      onClick={() => {
                        if (act.target_route) navigate(act.target_route);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          if (act.target_route) navigate(act.target_route);
                        }
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: 10,
                        backgroundColor: "var(--neutral-bg)",
                        borderRadius: 10,
                        border: "1px solid var(--border)",
                        fontSize: 12,
                        cursor: act.target_route ? "pointer" : "default",
                        outline: "none",
                        transition: "all 0.15s ease-in-out",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 10, flex: 1 }}>
                        <div
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: "50%",
                            backgroundColor: meta.bg,
                            color: meta.color,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: 15,
                            flexShrink: 0,
                            marginTop: 2,
                          }}
                        >
                          {meta.icon}
                        </div>

                        <div style={{ flex: 1 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                            <strong style={{ fontSize: 13, color: "var(--text-primary)" }}>{act.title}</strong>
                            {act.patient_name && (
                              <span style={{ fontSize: 12, fontWeight: 700, color: "var(--primary-dark)" }}>{act.patient_name}</span>
                            )}
                            {act.case_reference && (
                              <span style={{ fontSize: 10, padding: "1px 5px", borderRadius: 4, backgroundColor: "#FFF", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                                {act.case_reference}
                              </span>
                            )}
                          </div>
                          <div style={{ color: "var(--text-secondary)", marginTop: 2, fontSize: 12, lineHeight: "1.35" }}>
                            {act.description}
                          </div>
                          <div style={{ fontSize: 11, color: "var(--text-disabled)", marginTop: 4, display: "flex", gap: 10, flexWrap: "wrap" }}>
                            <span>👤 {act.actor_name} ({act.actor_role})</span>
                            <span title={istTime}>🕒 {relTime}</span>
                          </div>
                        </div>
                      </div>

                      <div style={{ paddingLeft: 8, color: "var(--text-secondary)", flexShrink: 0 }}>
                        <ChevronRightIcon size={16} />
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
