import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { doctorPaths } from "./doctorRoutes";
import { apiClient } from "@aarogya/api-client";
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
  ShieldCheckIcon,
} from "../../components/Icons";
import { useRealtime } from "../../hooks/useRealtime";

export function DoctorReferralQueueScreen() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialStatus = searchParams.get("status") || "ALL_ACTIVE";
  
  const [referrals, setReferrals] = useState<any[]>([]);
  const [summaryData, setSummaryData] = useState<any>(null);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<any>(null);
  const [activeFilter, setActiveFilter] = useState<string>(initialStatus);
  const [sortBy, setSortBy] = useState<string>("priority_first");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState<string | null>(null);
  const [lastSynced, setLastSynced] = useState<string>(new Date().toLocaleTimeString());

  const currentFilterParam = searchParams.get("filter") || searchParams.get("status") || "ALL_ACTIVE";

  useEffect(() => {
    setActiveFilter(currentFilterParam);
  }, [currentFilterParam]);

  const handleSelectFilter = (filterId: string) => {
    setActiveFilter(filterId);
    setSearchParams({ filter: filterId });
  };
  
  // Request Missing Info Modal State
  const [requestModalCase, setRequestModalCase] = useState<any | null>(null);
  const [missingInfoText, setMissingInfoText] = useState<string>("");

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, refsRes, dashRes] = await Promise.all([
        apiClient.getDoctorReferralsSummary(),
        apiClient.getDoctorReferrals({
          sort_by: sortBy,
          status_filter: activeFilter === "ALL" || activeFilter === "ALL_ACTIVE" ? undefined : activeFilter,
        }),
        apiClient.getDoctorDashboard(),
      ]);
      setSummaryData(sumRes || null);
      const itemsList = Array.isArray(refsRes) ? refsRes : (refsRes?.items || []);
      setReferrals(itemsList);
      setDashboardData(dashRes || null);
      setLastSynced(new Date().toLocaleTimeString());
    } catch (err: any) {
      console.error("Failed to load doctor referral queue", err);
      setError(err?.message || "Unable to fetch referral queue from backend service.");
    } finally {
      setLoading(false);
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
        "MISSING_INFO_REQUESTED",
      ].includes(event)
    ) {
      loadData();
    }
  });

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 10000);
    return () => clearInterval(timer);
  }, [sortBy, activeFilter]);

  // Lifecycle Action Handlers with Canonical IDs
  const handleAcknowledgeReferral = async (e: React.MouseEvent, refItem: any) => {
    e.stopPropagation();
    const refId = refItem.referral_id || refItem.id;
    setIsProcessing(refId);
    try {
      await apiClient.acknowledgeDoctorReferral(refId);
      await loadData();
    } catch (err) {
      console.error("Failed to acknowledge referral", err);
    } finally {
      setIsProcessing(null);
    }
  };

  const handleMarkTransport = async (e: React.MouseEvent, refItem: any) => {
    e.stopPropagation();
    const refId = refItem.referral_id || refItem.id;
    setIsProcessing(refId);
    try {
      await apiClient.markTransportArranged(refId);
      await loadData();
    } catch (err) {
      console.error("Failed to mark transport arranged", err);
    } finally {
      setIsProcessing(null);
    }
  };

  const handleMarkArrived = async (e: React.MouseEvent, refItem: any) => {
    e.stopPropagation();
    const refId = refItem.referral_id || refItem.id;
    setIsProcessing(refId);
    try {
      await apiClient.markPatientArrived(refId);
      await loadData();
    } catch (err) {
      console.error("Failed to mark patient arrived", err);
    } finally {
      setIsProcessing(null);
    }
  };

  const handleStartConsultation = async (e: React.MouseEvent, refItem: any) => {
    e.stopPropagation();
    const refId = refItem.referral_id || refItem.id;
    setIsProcessing(refId);
    try {
      const res = await apiClient.startOrResumeConsultation({ referral_id: refId, case_id: refItem.case_id });
      const consId = res?.data?.consultation_id || refItem.consultation_id || res?.consultation_id;
      if (consId) {
        navigate(`/doctor/consultations/${consId}`);
      } else {
        navigate(`/doctor/consultations?caseId=${refItem.case_id}`);
      }
    } catch (err) {
      console.error("Failed to start/resume consultation", err);
      navigate(`/doctor/consultations?caseId=${refItem.case_id}`);
    } finally {
      setIsProcessing(null);
    }
  };

  const handleOpenReviewNextUrgent = () => {
    const nextUrgent = referrals.find(
      (r) =>
        (r.urgency === "URGENT" || r.urgency === "HIGH") &&
        ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"].includes(r.status)
    );
    if (nextUrgent) {
      navigate(`/doctor/referrals/${nextUrgent.id || nextUrgent.referral_id}`);
    } else if (referrals.length > 0) {
      navigate(`/doctor/referrals/${referrals[0].id || referrals[0].referral_id}`);
    }
  };

  const handleSubmitMissingInfo = async () => {
    if (!requestModalCase || !missingInfoText.trim()) return;
    setIsProcessing(requestModalCase.id);
    try {
      await apiClient.requestMissingInfo(requestModalCase.case_id, missingInfoText.trim());
      setRequestModalCase(null);
      setMissingInfoText("");
      await loadData();
    } catch (err) {
      console.error("Failed to submit missing info request", err);
    } finally {
      setIsProcessing(null);
    }
  };

  const summary = {
    new: summaryData?.new_referrals ?? summaryData?.new ?? referrals.filter((r) => ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"].includes(r.status)).length,
    urgent_active: summaryData?.active_urgent_referrals ?? summaryData?.urgent_active ?? referrals.filter((r) => (r.urgency === "URGENT" || r.urgency === "HIGH") && !["PROCESSED", "COMPLETED"].includes(r.status)).length,
    urgent_pending_review: summaryData?.urgent_pending_review ?? referrals.filter((r) => (r.urgency === "URGENT" || r.urgency === "HIGH") && ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"].includes(r.status)).length,
    acknowledged: summaryData?.acknowledged ?? referrals.filter((r) => ["DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED"].includes(r.status)).length,
    transport_arranged: summaryData?.transport_arranged ?? referrals.filter((r) => r.status === "TRANSPORT_ARRANGED" || r.transport_assistance_required).length,
    transport_en_route: summaryData?.transport_en_route ?? summaryData?.transport_arranged ?? referrals.filter((r) => r.status === "TRANSPORT_ARRANGED" || r.transport_assistance_required).length,
    patient_arrived: summaryData?.patient_arrived ?? referrals.filter((r) => r.status === "PATIENT_ARRIVED").length,
    in_consultation: summaryData?.in_consultation ?? referrals.filter((r) => r.status === "IN_CONSULTATION").length,
    processed_today: summaryData?.processed_today ?? 0,
    total_active: summaryData?.total_active_referrals ?? summaryData?.total_active ?? referrals.length,
  };

  const urgentUnacknowledged = referrals.filter(
    (r) => (r.urgency === "URGENT" || r.urgency === "HIGH") && ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"].includes(r.status)
  );

  const escalations: any[] = dashboardData?.escalations || [];

  // Filtered referrals by search
  const filteredReferrals = referrals.filter((r) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase().trim();
    return (
      r.citizen_name?.toLowerCase().includes(q) ||
      r.case_reference?.toLowerCase().includes(q) ||
      r.reference?.toLowerCase().includes(q) ||
      r.village_name?.toLowerCase().includes(q) ||
      r.referring_asha_name?.toLowerCase().includes(q)
    );
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 1440, margin: "0 auto", width: "100%" }}>
      {/* Top Header & Context */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
            PHC Referral Queue
          </h1>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
            {dashboardData?.facility_name || "Kalyanpur Primary Health Centre"} · Live Sync Active · {lastSynced}
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button
            onClick={() => loadData()}
            style={{
              padding: "8px 14px",
              backgroundColor: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            🔄 Refresh Queue
          </button>

          {urgentUnacknowledged.length > 0 && (
            <button
              onClick={handleOpenReviewNextUrgent}
              style={{
                padding: "8px 18px",
                backgroundColor: "#DC2626",
                color: "#FFF",
                border: "none",
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Review Next Urgent ({urgentUnacknowledged.length}) →
            </button>
          )}
        </div>
      </div>

      {/* Urgent Referral Warning Banner (Conditional on urgent_pending_review > 0) */}
      {summary.urgent_pending_review > 0 && (
        <div
          style={{
            backgroundColor: "#FEF2F2",
            border: "2px solid #DC2626",
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
                backgroundColor: "#DC2626",
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
              <div style={{ fontSize: 16, fontWeight: 800, color: "#991B1B" }}>
                {summary.urgent_pending_review} Urgent Referral{summary.urgent_pending_review > 1 ? "s" : ""} Pending Review
              </div>
              <div style={{ fontSize: 13, color: "#7F1D1D", marginTop: 2 }}>
                Newest Patient: <strong>{urgentUnacknowledged[0]?.citizen_name || "Sunita Devi"}</strong> · Referring ASHA: {urgentUnacknowledged[0]?.referring_asha_name || "Sita Patel (ASHA)"}
              </div>
            </div>
          </div>
          <button
            onClick={() => handleSelectFilter("URGENT_PENDING_REVIEW")}
            style={{
              padding: "8px 16px",
              backgroundColor: "#DC2626",
              color: "#FFF",
              borderRadius: 8,
              border: "none",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Filter Urgent Referrals →
          </button>
        </div>
      )}

      {/* 6 Dynamic Metric Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 12 }}>
        {[
          { id: "NEW", title: "New Referrals", count: summary.new, color: "#1D4ED8", border: "#BFDBFE" },
          { id: "URGENT_ACTIVE", title: "Active Urgent Referrals", count: summary.urgent_active, color: "#DC2626", border: "#FCA5A5" },
          { id: "ACKNOWLEDGED", title: "Acknowledged", count: summary.acknowledged, color: "#0284C7", border: "#BAE6FD" },
          { id: "TRANSPORT_ARRANGED", title: "Transport Arranged", count: summary.transport_arranged, color: "#0D9488", border: "#99F6E4" },
          { id: "PATIENT_ARRIVED", title: "Patient Arrived", count: summary.patient_arrived, color: "#059669", border: "#A7F3D0" },
          { id: "PROCESSED_TODAY", title: "Processed Today", count: summary.processed_today, color: "#16A34A", border: "#BBF7D0" },
        ].map((card) => {
          const isSelected = activeFilter === card.id;
          return (
            <div
              key={card.id}
              onClick={() => handleSelectFilter(card.id)}
              style={{
                backgroundColor: "var(--surface)",
                padding: "14px 16px",
                borderRadius: 10,
                border: isSelected ? `2px solid ${card.color}` : `1px solid ${card.border || "var(--border)"}`,
                cursor: "pointer",
                boxShadow: isSelected ? "0 2px 6px rgba(0,0,0,0.06)" : "none",
              }}
            >
              <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>{card.title}</div>
              <div style={{ fontSize: 26, fontWeight: 800, color: card.color, marginTop: 4 }}>{card.count}</div>
            </div>
          );
        })}
      </div>

      {/* Main Referral List Layout */}
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
        <div style={{ flex: "1 1 700px", minWidth: 320, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            {/* Filtered vs Total Header Reconciliation Count */}
            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 12 }}>
              {activeFilter === "ALL_ACTIVE" || activeFilter === "ALL" ? (
                `Showing ${filteredReferrals.length} active referrals`
              ) : (
                `Showing ${filteredReferrals.length} of ${summary.total_active} active referrals (${activeFilter.replace(/_/g, ' ')})`
              )}
            </div>

            {/* Search and Sort Bar */}
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
              <div
                style={{
                  flex: "1 1 260px",
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
                  placeholder="Search patient, case, referral, village or ASHA..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ border: "none", outline: "none", width: "100%", fontSize: 13, backgroundColor: "transparent" }}
                />
              </div>

              {/* Sort Selector */}
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>Sort by:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  style={{
                    padding: "6px 10px",
                    borderRadius: 6,
                    border: "1px solid var(--border)",
                    backgroundColor: "var(--surface)",
                    fontSize: 12,
                    fontWeight: 600,
                  }}
                >
                  <option value="priority_first">Priority First</option>
                  <option value="oldest_first">Oldest First</option>
                  <option value="newest_first">Newest First</option>
                </select>
              </div>
            </div>

            {/* Referral Specific Filter Tabs */}
            <div style={{ display: "flex", gap: 6, overflowX: "auto", marginBottom: 16, paddingBottom: 4 }}>
              {[
                { id: "ALL_ACTIVE", label: "All Active" },
                { id: "NEW", label: "New / Unacknowledged" },
                { id: "URGENT_PENDING_REVIEW", label: "Urgent Pending Review" },
                { id: "ACKNOWLEDGED", label: "Acknowledged" },
                { id: "TRANSPORT_ARRANGED", label: "Transport Arranged" },
                { id: "PATIENT_ARRIVED", label: "Patient Arrived" },
                { id: "PROCESSED_TODAY", label: "Processed Today" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => handleSelectFilter(tab.id)}
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

            {/* Referral Cards Feed */}
            {error ? (
              <div style={{ padding: 30, textAlign: "center", backgroundColor: "#FEF2F2", border: "1.5px solid #FCA5A5", borderRadius: 10, margin: "10px 0" }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#991B1B" }}>Error Loading Referrals Queue</div>
                <div style={{ fontSize: 13, color: "#B91C1C", marginTop: 4, marginBottom: 16 }}>{error}</div>
                <button
                  onClick={() => loadData()}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: "#DC2626",
                    color: "#FFF",
                    borderRadius: 8,
                    border: "none",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Retry Request
                </button>
              </div>
            ) : loading ? (
              <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
                Loading PHC referral queue...
              </div>
            ) : referrals.length === 0 ? (
              <div style={{ padding: 40, textAlign: "center", backgroundColor: "var(--neutral-bg)", borderRadius: 8, color: "var(--text-secondary)" }}>
                No referrals currently assigned to this PHC.
              </div>
            ) : filteredReferrals.length === 0 ? (
              <div style={{ padding: 40, textAlign: "center", backgroundColor: "var(--neutral-bg)", borderRadius: 8, color: "var(--text-secondary)" }}>
                No referrals match this filter.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {filteredReferrals.map((ref) => {
                  const statusVal = ref.status?.toUpperCase() || "PENDING_DOCTOR_REVIEW";
                  const urgencyVal = ref.urgency?.toUpperCase() || ref.priority?.toUpperCase() || "ROUTINE";
                  
                  const isUrgentPending = urgencyVal === "URGENT" && ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"].includes(statusVal);
                  const isHigh = urgencyVal === "HIGH";
                  const isAcked = ["DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED"].includes(statusVal);
                  const isTransport = statusVal === "TRANSPORT_ARRANGED";
                  const isArrived = statusVal === "PATIENT_ARRIVED";
                  const isInConsultation = statusVal === "IN_CONSULTATION";
                  const isProcessed = ["PROCESSED", "COMPLETED"].includes(statusVal);

                  // Border Color Scheme by status and priority (No hardcoded all-pink!)
                  let borderColor = "var(--border)";
                  let bgColor = "var(--surface)";
                  
                  if (isUrgentPending) {
                    borderColor = "#DC2626";
                    bgColor = "#FEF2F2";
                  } else if (isHigh) {
                    borderColor = "#EA580C";
                    bgColor = "#FFF7ED";
                  } else if (isAcked) {
                    borderColor = "#0284C7";
                    bgColor = "#F0F9FF";
                  } else if (isTransport || isArrived) {
                    borderColor = "#0D9488";
                    bgColor = "#F0FDFA";
                  } else if (isInConsultation) {
                    borderColor = "#7C3AED";
                    bgColor = "#F5F3FF";
                  } else if (isProcessed) {
                    borderColor = "#16A34A";
                    bgColor = "#F0FDF4";
                  }

                  return (
                    <div
                      key={ref.id || ref.referral_id}
                      style={{
                        padding: 18,
                        borderRadius: 10,
                        border: `1.5px solid ${borderColor}`,
                        backgroundColor: bgColor,
                        display: "flex",
                        flexDirection: "column",
                        gap: 12,
                        boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
                      }}
                    >
                      {/* Top Header Row: Patient Bio & Category Badges */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                            <span style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)" }}>
                              {ref.citizen_name}
                            </span>
                            <span style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 600 }}>
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
                                🩺 NCD Patient
                              </span>
                            )}
                            <PriorityBadge priority={urgencyVal} size="sm" />
                          </div>

                          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, display: "flex", gap: 10, flexWrap: "wrap" }}>
                            <span>Ref: <strong>{ref.reference}</strong></span>
                            <span>Case: <strong>{ref.case_reference}</strong></span>
                            <span>Referred: <strong>{ref.created_at ? new Date(ref.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Recently"}</strong></span>
                            <span>ASHA: <strong>{ref.referring_asha_name}</strong></span>
                          </div>
                        </div>

                        <div>
                          <span
                            style={{
                              padding: "4px 10px",
                              borderRadius: 6,
                              fontSize: 11,
                              fontWeight: 800,
                              backgroundColor: isProcessed
                                ? "#DCFCE7"
                                : isInConsultation
                                ? "#F3E8FF"
                                : isArrived
                                ? "#CCFBF1"
                                : isTransport
                                ? "#E0F2FE"
                                : isAcked
                                ? "#E0F2FE"
                                : "#FEE2E2",
                              color: isProcessed
                                ? "#15803D"
                                : isInConsultation
                                ? "#6B21A8"
                                : isArrived
                                ? "#0F766E"
                                : isTransport
                                ? "#0369A1"
                                : isAcked
                                ? "#0369A1"
                                : "#B91C1C",
                            }}
                          >
                            {isProcessed
                              ? "✓ PROCESSED"
                              : isInConsultation
                              ? "IN CONSULTATION"
                              : isArrived
                              ? "✓ PATIENT ARRIVED"
                              : isTransport
                              ? "🚑 TRANSPORT ARRANGED"
                              : isAcked
                              ? "DOCTOR ACKNOWLEDGED"
                              : "PENDING REVIEW"}
                          </span>
                        </div>
                      </div>

                      {/* Middle: Clinical Findings & Measured Vitals */}
                      <div style={{ padding: 12, backgroundColor: "var(--surface)", borderRadius: 8, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 6 }}>
                        <div style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 700 }}>
                          ⚠️ Triage Reason: {ref.reason || "Maternal warning signs detected."}
                        </div>
                        {ref.citizen_reported_concern && (
                          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                            <strong>Reported Concern:</strong> "{ref.citizen_reported_concern}"
                          </div>
                        )}
                        {ref.asha_confirmed_symptoms && ref.asha_confirmed_symptoms.length > 0 && (
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginTop: 2 }}>
                            <span style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 600 }}>Confirmed Symptoms:</span>
                            {ref.asha_confirmed_symptoms.map((sym: string, i: number) => (
                              <span key={i} style={{ fontSize: 11, padding: "2px 6px", borderRadius: 4, backgroundColor: "var(--neutral-bg)", border: "1px solid var(--border)", fontWeight: 600 }}>
                                {sym}
                              </span>
                            ))}
                          </div>
                        )}
                        {ref.latest_vitals && (
                          <div style={{ fontSize: 12, color: "var(--primary-dark)", display: "flex", gap: 12, flexWrap: "wrap", marginTop: 4, padding: "6px 10px", backgroundColor: "#F8FAFC", borderRadius: 6, border: "1px solid #E2E8F0" }}>
                            {ref.latest_vitals.systolic_bp && (
                              <span style={{ fontWeight: ref.latest_vitals.systolic_bp >= 140 ? 800 : 600, color: ref.latest_vitals.systolic_bp >= 140 ? "#DC2626" : "inherit" }}>
                                <strong>BP:</strong> {ref.latest_vitals.systolic_bp}/{ref.latest_vitals.diastolic_bp} mmHg
                              </span>
                            )}
                            {ref.latest_vitals.spo2 && (
                              <span style={{ fontWeight: ref.latest_vitals.spo2 <= 94 ? 800 : 600, color: ref.latest_vitals.spo2 <= 94 ? "#DC2626" : "inherit" }}>
                                <strong>SpO₂:</strong> {ref.latest_vitals.spo2}%
                              </span>
                            )}
                            {ref.latest_vitals.pulse && <span><strong>Pulse:</strong> {ref.latest_vitals.pulse} bpm</span>}
                            {ref.latest_vitals.temperature_c && <span><strong>Temp:</strong> {ref.latest_vitals.temperature_c}°C</span>}
                            <span style={{ fontSize: 11, color: "var(--text-secondary)", marginLeft: "auto" }}>
                              Recorded by {ref.latest_vitals.recorded_by || ref.referring_asha_name}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Bottom Action Command Bar */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          {ref.referring_asha_phone && (
                            <a
                              href={`tel:${ref.referring_asha_phone}`}
                              style={{
                                padding: "6px 12px",
                                backgroundColor: "var(--surface)",
                                border: "1px solid var(--border)",
                                borderRadius: 6,
                                fontSize: 12,
                                fontWeight: 600,
                                color: "#0369A1",
                                textDecoration: "none",
                              }}
                            >
                              📞 Call ASHA
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
                              cursor: "pointer",
                            }}
                          >
                            View Timeline
                          </button>
                          {ref.citizen_id && (
                            <button
                              onClick={() => navigate(doctorPaths.patientRecord(ref.citizen_id, window.location.pathname))}
                              style={{
                                padding: "6px 12px",
                                backgroundColor: "var(--surface)",
                                border: "1px solid var(--border)",
                                borderRadius: 6,
                                fontSize: 12,
                                fontWeight: 600,
                                color: "var(--text-secondary)",
                                cursor: "pointer",
                              }}
                            >
                              Patient Record
                            </button>
                          )}
                        </div>

                        <div style={{ display: "flex", gap: 8 }}>
                          {["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"].includes(statusVal) && (
                            <button
                              disabled={isProcessing === (ref.id || ref.referral_id)}
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
                              {isProcessing === (ref.id || ref.referral_id) ? "Processing..." : "✓ Review & Acknowledge"}
                            </button>
                          )}

                          {isAcked && (
                            <>
                              <button
                                disabled={isProcessing === (ref.id || ref.referral_id)}
                                onClick={(e) => handleMarkTransport(e, ref)}
                                style={{
                                  padding: "8px 12px",
                                  backgroundColor: "#E0F2FE",
                                  color: "#0369A1",
                                  border: "1px solid #7DD3FC",
                                  borderRadius: 6,
                                  fontSize: 12,
                                  fontWeight: 700,
                                  cursor: "pointer",
                                }}
                              >
                                🚑 Mark Transport Arranged
                              </button>
                              <button
                                disabled={isProcessing === (ref.id || ref.referral_id)}
                                onClick={(e) => handleMarkArrived(e, ref)}
                                style={{
                                  padding: "8px 14px",
                                  backgroundColor: "#CCFBF1",
                                  color: "#0F766E",
                                  border: "1px solid #5EEAD4",
                                  borderRadius: 6,
                                  fontSize: 12,
                                  fontWeight: 700,
                                  cursor: "pointer",
                                }}
                              >
                                🏥 Mark Patient Arrived
                              </button>
                            </>
                          )}

                          {isTransport && (
                            <button
                              disabled={isProcessing === (ref.id || ref.referral_id)}
                              onClick={(e) => handleMarkArrived(e, ref)}
                              style={{
                                padding: "8px 16px",
                                backgroundColor: "#0D9488",
                                color: "#FFF",
                                border: "none",
                                borderRadius: 6,
                                fontSize: 13,
                                fontWeight: 700,
                                cursor: "pointer",
                              }}
                            >
                              🏥 Mark Patient Arrived
                            </button>
                          )}

                          {isArrived && (
                            <button
                              disabled={isProcessing === (ref.id || ref.referral_id)}
                              onClick={(e) => handleStartConsultation(e, ref)}
                              style={{
                                padding: "8px 18px",
                                backgroundColor: "#16A34A",
                                color: "#FFF",
                                border: "none",
                                borderRadius: 6,
                                fontSize: 13,
                                fontWeight: 800,
                                cursor: "pointer",
                              }}
                            >
                              ▶ Start Consultation Now
                            </button>
                          )}

                          {isInConsultation && (
                            <button
                              onClick={(e) => handleStartConsultation(e, ref)}
                              style={{
                                padding: "8px 18px",
                                backgroundColor: "#7C3AED",
                                color: "#FFF",
                                border: "none",
                                borderRadius: 6,
                                fontSize: 13,
                                fontWeight: 800,
                                cursor: "pointer",
                              }}
                            >
                              Continue Consultation →
                            </button>
                          )}

                          {isProcessed && (
                            <button
                              onClick={() => navigate(`/doctor/consultations/${ref.consultation_id || ''}`)}
                              style={{
                                padding: "8px 14px",
                                backgroundColor: "var(--neutral-bg)",
                                color: "var(--text-primary)",
                                border: "1px solid var(--border)",
                                borderRadius: 6,
                                fontSize: 12,
                                fontWeight: 600,
                                cursor: "pointer",
                              }}
                            >
                              View Completed Case
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Queue Summary Info */}
        <div style={{ flex: "1 1 340px", minWidth: 300, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
                Queue Summary
              </h3>
              {loading && (
                <span style={{ fontSize: 11, color: "var(--text-secondary)", fontStyle: "italic" }}>
                  Syncing...
                </span>
              )}
            </div>

            {error ? (
              <div style={{ padding: 14, backgroundColor: "#FEF2F2", border: "1px solid #FCA5A5", borderRadius: 8, textAlign: "center" }}>
                <div style={{ fontSize: 13, color: "#991B1B", fontWeight: 600 }}>Unable to load queue summary</div>
                <button
                  type="button"
                  onClick={() => loadData()}
                  style={{
                    marginTop: 8,
                    padding: "4px 12px",
                    backgroundColor: "#DC2626",
                    color: "#FFF",
                    border: "none",
                    borderRadius: 6,
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Retry
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  {
                    id: "ALL_ACTIVE",
                    label: "Total Active Referrals",
                    count: summary.total_active,
                    color: "#1D4ED8",
                    bgColor: "#EFF6FF",
                    borderColor: "#BFDBFE",
                    icon: "📊",
                    ariaLabel: `Filter by Total Active Referrals, count ${summary.total_active}`,
                    onClick: () => handleSelectFilter("ALL_ACTIVE"),
                  },
                  {
                    id: "URGENT_PENDING_REVIEW",
                    label: "Urgent Pending Review",
                    count: summary.urgent_pending_review,
                    color: "#DC2626",
                    bgColor: "#FEF2F2",
                    borderColor: "#FCA5A5",
                    icon: "⚠️",
                    ariaLabel: `Filter by Urgent Pending Review, count ${summary.urgent_pending_review}`,
                    onClick: () => handleSelectFilter("URGENT_PENDING_REVIEW"),
                  },
                  {
                    id: "TRANSPORT_ARRANGED",
                    label: "Transport En Route",
                    count: summary.transport_en_route,
                    color: "#0D9488",
                    bgColor: "#F0FDFA",
                    borderColor: "#99F6E4",
                    icon: "🚑",
                    ariaLabel: `Filter by Transport En Route, count ${summary.transport_en_route}`,
                    onClick: () => handleSelectFilter("TRANSPORT_ARRANGED"),
                  },
                  {
                    id: "PATIENT_ARRIVED",
                    label: "Patients Arrived",
                    count: summary.patient_arrived,
                    color: "#059669",
                    bgColor: "#F0FDF4",
                    borderColor: "#A7F3D0",
                    icon: "🏥",
                    ariaLabel: `Filter by Patients Arrived, count ${summary.patient_arrived}`,
                    onClick: () => handleSelectFilter("PATIENT_ARRIVED"),
                  },
                  {
                    id: "IN_CONSULTATION",
                    label: "Active Consultations",
                    count: summary.in_consultation,
                    color: "#7C3AED",
                    bgColor: "#F5F3FF",
                    borderColor: "#DDD6FE",
                    icon: "🩺",
                    ariaLabel: `View Active Consultations workspace, count ${summary.in_consultation}`,
                    onClick: () => navigate("/doctor/consultations?status=IN_CONSULTATION"),
                  },
                  {
                    id: "PROCESSED_TODAY",
                    label: "Processed Today",
                    count: summary.processed_today,
                    color: "#16A34A",
                    bgColor: "#F0FDF4",
                    borderColor: "#BBF7D0",
                    icon: "✓",
                    ariaLabel: `Filter by Processed Today, count ${summary.processed_today}`,
                    onClick: () => handleSelectFilter("PROCESSED_TODAY"),
                  },
                ].map((row) => {
                  const isSelected = activeFilter === row.id;
                  return (
                    <button
                      key={row.id}
                      type="button"
                      onClick={row.onClick}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          row.onClick();
                        }
                      }}
                      aria-label={row.ariaLabel}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "10px 12px",
                        borderRadius: 8,
                        border: isSelected ? `2px solid ${row.color}` : `1px solid ${row.borderColor || "var(--border)"}`,
                        backgroundColor: isSelected ? row.bgColor : "var(--neutral-bg)",
                        cursor: "pointer",
                        textAlign: "left",
                        width: "100%",
                        transition: "all 0.15s ease",
                        outline: "none",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontSize: 14 }}>{row.icon}</span>
                        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{row.label}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <strong style={{ fontSize: 15, fontWeight: 800, color: row.color }}>{loading ? "..." : row.count}</strong>
                        <span style={{ fontSize: 14, color: "var(--text-secondary)" }}>›</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* ASHA Escalation Panel */}
          {escalations.length > 0 && (
            <div style={{ backgroundColor: "#FEF3C7", padding: 18, borderRadius: 12, border: "1px solid #FCD34D" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <WarningIcon size={20} color="#92400E" />
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "#92400E" }}>
                  ASHA Field Escalations ({escalations.length})
                </h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {escalations.map((esc) => (
                  <div key={esc.id} style={{ backgroundColor: "#FFF", padding: 12, borderRadius: 8, border: "1px solid #FDE68A" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700 }}>
                      <span>{esc.citizen_name}</span>
                      <span style={{ fontSize: 11, color: "#92400E" }}>{esc.village_name}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                      {esc.escalation_reason}
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
        </div>
      </div>

      {/* Modal: Request Missing Clinical Information */}
      {requestModalCase && (
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
          <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, maxWidth: 500, width: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>
              Request Missing Information from ASHA
            </h3>
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
              Patient: <strong>{requestModalCase.citizen_name}</strong> · Referring ASHA: <strong>{requestModalCase.referring_asha_name}</strong>
            </p>
            <textarea
              rows={4}
              placeholder="Specify the missing observations, repeat vitals, or clinical clarification required..."
              value={missingInfoText}
              onChange={(e) => setMissingInfoText(e.target.value)}
              style={{
                width: "100%",
                padding: 12,
                borderRadius: 8,
                border: "1px solid var(--border)",
                fontSize: 13,
                outline: "none",
              }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                onClick={() => setRequestModalCase(null)}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "var(--neutral-bg)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                disabled={!missingInfoText.trim() || isProcessing === requestModalCase.id}
                onClick={handleSubmitMissingInfo}
                style={{
                  padding: "8px 18px",
                  backgroundColor: "var(--primary)",
                  color: "#FFF",
                  border: "none",
                  borderRadius: 6,
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {isProcessing === requestModalCase.id ? "Sending..." : "Submit Request to ASHA"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export { DoctorPatientsScreen } from "./DoctorPatientsScreen";

