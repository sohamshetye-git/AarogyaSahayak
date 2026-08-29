import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge } from "../../components/StatusBadge";
import {
  WarningIcon,
  SearchIcon,
  StethoscopeIcon,
  PeopleIcon,
  VisitIcon,
  ChevronRightIcon,
  PillIcon,
  ShieldCheckIcon,
  ActivityIcon,
} from "../../components/Icons";
import { useRealtime } from "../../hooks/useRealtime";
import { doctorPaths } from "./doctorRoutes";

export function DoctorConsultationWorkspaceScreen() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialStatus = searchParams.get("status") || "ALL";
  const [referrals, setReferrals] = useState<any[]>([]);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [waitingData, setWaitingData] = useState<{ items: any[]; total: number }>({ items: [], total: 0 });
  const [waitingLoading, setWaitingLoading] = useState<boolean>(true);
  const [waitingError, setWaitingError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<string>(initialStatus === "READY_TO_START" ? "ARRIVED" : initialStatus);
  const activeTab = activeFilter;
  const setActiveTab = setActiveFilter;
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("urgent_oldest");
  const [isStarting, setIsStarting] = useState<string | null>(null);
  const [lastSynced, setLastSynced] = useState<string>(new Date().toLocaleTimeString());

  useEffect(() => {
    const st = searchParams.get("status");
    if (st) {
      setActiveFilter(st === "READY_TO_START" ? "ARRIVED" : st);
    }
  }, [searchParams]);

  const loadWaitingPatients = async () => {
    try {
      setWaitingError(null);
      const res = await apiClient.getWaitingPatients({ page: 1, page_size: 10 });
      setWaitingData({ items: res?.items || [], total: res?.total || 0 });
    } catch (err: any) {
      console.error("Failed to load waiting patients", err);
      setWaitingError(err?.message || "Failed to load waiting patients.");
    } finally {
      setWaitingLoading(false);
    }
  };

  const loadWorkspaceData = async () => {
    try {
      const [refsRes, dashRes] = await Promise.all([
        apiClient.getDoctorReferrals({
          sort_by: sortBy === "urgent_oldest" ? "priority_first" : sortBy,
          status_filter: activeFilter === "ALL" ? undefined : activeFilter,
        }),
        apiClient.getDoctorDashboard(),
      ]);
      const itemsList = Array.isArray(refsRes) ? refsRes : (refsRes?.items || []);
      setReferrals(itemsList);
      setDashboardData(dashRes || null);
      setLastSynced(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
    } catch (err) {
      console.error("Failed to load doctor consultation workspace", err);
    } finally {
      setLoading(false);
    }
    loadWaitingPatients();
  };

  useRealtime((event) => {
    if (
      [
        "REFERRAL_CREATED",
        "REFERRAL_ACKNOWLEDGED",
        "PATIENT_ARRIVED",
        "CONSULTATION_STARTED",
        "CONSULTATION_COMPLETED",
        "FOLLOW_UP_ASSIGNED",
      ].includes(event)
    ) {
      loadWorkspaceData();
    }
  });

  useEffect(() => {
    loadWorkspaceData();
    const interval = setInterval(loadWorkspaceData, 10000);
    return () => clearInterval(interval);
  }, [sortBy, activeFilter]);

  const handleStartOrResume = async (e: React.MouseEvent, item: any) => {
    e.stopPropagation();
    setIsStarting(item.id);
    try {
      const res = await apiClient.startConsultation(item.id || item.case_id);
      const consId = res?.consultation_id || res?.reference || item.case_id;
      navigate(`/doctor/consultations/${consId}`);
    } catch (err) {
      console.error("Failed to start/resume consultation", err);
      // Fallback
      navigate(`/doctor/consultations/${item.case_id}`);
    } finally {
      setIsStarting(null);
    }
  };

  const handleMarkArrived = async (e: React.MouseEvent, item: any) => {
    e.stopPropagation();
    setIsStarting(item.id);
    try {
      await apiClient.markPatientArrived(item.id);
      await loadWorkspaceData();
    } catch (err) {
      console.error("Failed to mark arrived", err);
    } finally {
      setIsStarting(null);
    }
  };

  // Patients ready for consultation (Arrived or In Progress)
  const readyPatients = referrals.filter(
    (r) => r.arrival_status === "ARRIVED" || r.status === "PATIENT_ARRIVED" || r.status === "IN_CONSULTATION"
  );

  const metrics = {
    readyToStart: referrals.filter((r) => r.arrival_status === "ARRIVED" || r.status === "PATIENT_ARRIVED").length,
    inProgress: referrals.filter((r) => r.status === "IN_CONSULTATION" || r.status === "CONSULTATION_IN_PROGRESS").length,
    savedDrafts: referrals.filter((r) => r.status === "DOCTOR_ACKNOWLEDGED" || r.status === "DRAFT").length,
    awaitingResults: referrals.filter((r) => r.status === "AWAITING_INVESTIGATION" || r.urgency === "HIGH").length,
    followupReview: referrals.filter((r) => r.status === "FOLLOW_UP_REQUIRED").length,
    completedToday: dashboardData?.today_consultations_count || dashboardData?.metrics?.completed_today_count || 0,
  };

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
    <div style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 1440, margin: "0 auto", width: "100%" }}>
      {/* Top Header & Breadcrumb */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>
            Doctor Portal / <strong style={{ color: "var(--text-primary)" }}>Consultations</strong>
          </div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
            Consultation Workspace
          </h1>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
            Review waiting patients, resume drafts and manage active clinical work.
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            Last synced: <strong>{lastSynced}</strong>
          </div>
          <button
            onClick={() => loadWorkspaceData()}
            style={{
              padding: "8px 14px",
              backgroundColor: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Conditional Next Patient Banner */}
      {readyPatients.length > 0 && (
        <div
          style={{
            backgroundColor: "#E0F2FE",
            border: "1px solid #BAE6FD",
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
                width: 42,
                height: 42,
                borderRadius: "50%",
                backgroundColor: "#0284C7",
                color: "#FFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <PeopleIcon size={22} color="#FFF" />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#0369A1" }}>
                {readyPatients.length} patient{readyPatients.length > 1 ? "s are" : " is"} ready for consultation
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
                Oldest waiting patient: <strong>{readyPatients[0].citizen_name}</strong> ({readyPatients[0].village_name})
              </div>
            </div>
          </div>

          <button
            onClick={(e) => handleStartOrResume(e, readyPatients[0])}
            style={{
              padding: "10px 20px",
              backgroundColor: "#0284C7",
              color: "#FFF",
              border: "none",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Open Next Patient →
          </button>
        </div>
      )}

      {/* Dynamic 6 Metric Cards (Clickable) */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 12 }}>
        {[
          { id: "ARRIVED", title: "Ready to Start", count: metrics.readyToStart, color: "#0284C7", border: "#BAE6FD" },
          { id: "IN_CONSULTATION", title: "In Progress", count: metrics.inProgress, color: "#D97706", border: "#FDE68A" },
          { id: "ACKNOWLEDGED", title: "Saved Drafts", count: metrics.savedDrafts, color: "#2563EB", border: "#BFDBFE" },
          { id: "AWAITING_RESULTS", title: "Awaiting Results", count: metrics.awaitingResults, color: "#7C3AED", border: "#DDD6FE" },
          { id: "FOLLOW_UP_REQUIRED", title: "Follow-up Review", count: metrics.followupReview, color: "#059669", border: "#A7F3D0" },
          { id: "COMPLETED", title: "Completed Today", count: metrics.completedToday, color: "#16A34A", border: "#BBF7D0" },
        ].map((card) => {
          const isSelected = activeFilter === card.id;
          return (
            <div
              key={card.id}
              onClick={() => setActiveFilter(card.id)}
              style={{
                backgroundColor: "var(--surface)",
                padding: "14px 16px",
                borderRadius: 10,
                border: isSelected ? `2px solid ${card.color}` : `1px solid ${card.border || "var(--border)"}`,
                cursor: "pointer",
              }}
            >
              <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>{card.title}</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: card.color, marginTop: 4 }}>
                {card.count} <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)" }}>patients</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Main 2-Column Section */}
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
        {/* Left Column: Active Consultations Queue (Matching Image 1) */}
        <div style={{ flex: "1 1 700px", minWidth: 320, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            {/* Search and Filters */}
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
                  placeholder="Search patient, case, referral or ASHA..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ border: "none", outline: "none", width: "100%", fontSize: 13, backgroundColor: "transparent" }}
                />
              </div>

              {/* Filter Pills */}
              <div style={{ display: "flex", gap: 6, overflowX: "auto" }}>
                {[
                  { id: "ALL", label: "All Active" },
                  { id: "ARRIVED", label: "Ready to Start" },
                  { id: "IN_CONSULTATION", label: "In Progress" },
                  { id: "ACKNOWLEDGED", label: "Drafts" },
                  { id: "AWAITING_RESULTS", label: "Awaiting Results" },
                  { id: "FOLLOW_UP_REQUIRED", label: "Follow-up Required" },
                  { id: "COMPLETED", label: "Completed" },
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

            <h3 style={{ margin: "0 0 14px", fontSize: 15, fontWeight: 700 }}>Active Consultations</h3>

            {/* List of Consultation Cards */}
            {loading ? (
              <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
                Loading consultation workspace...
              </div>
            ) : filteredReferrals.length === 0 ? (
              <div style={{ padding: 40, textAlign: "center", backgroundColor: "var(--neutral-bg)", borderRadius: 8, color: "var(--text-secondary)" }}>
                No active patients found for the selected filter.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {filteredReferrals.map((item) => {
                  const isUrgent = item.urgency === "URGENT" || item.urgency === "HIGH";
                  const isArrived = item.arrival_status === "ARRIVED" || item.status === "PATIENT_ARRIVED";
                  const isInProgress = item.status === "IN_CONSULTATION" || item.status === "CONSULTATION_IN_PROGRESS";
                  const isDraft = item.status === "DOCTOR_ACKNOWLEDGED" || item.status === "DRAFT";
                  const isCompleted = item.status === "CONSULTED" || item.status === "COMPLETED";

                  return (
                    <div
                      key={item.id}
                      style={{
                        padding: 16,
                        borderRadius: 10,
                        border: isUrgent ? "1px solid #F5C6CB" : "1px solid var(--border)",
                        backgroundColor: isUrgent ? "var(--urgent-bg)" : "var(--surface)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        flexWrap: "wrap",
                        gap: 12,
                      }}
                    >
                      {/* Patient Details */}
                      <div style={{ flex: "1 1 360px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
                            {item.citizen_name}
                          </span>
                          <PriorityBadge priority={item.urgency} size="sm" />
                          <span
                            style={{
                              padding: "2px 8px",
                              borderRadius: 4,
                              fontSize: 11,
                              fontWeight: 700,
                              backgroundColor: isCompleted
                                ? "#D4EDDA"
                                : isInProgress
                                ? "#FEF3C7"
                                : isArrived
                                ? "#DEF7EC"
                                : "#E0E7FF",
                              color: isCompleted
                                ? "#155724"
                                : isInProgress
                                ? "#92400E"
                                : isArrived
                                ? "#03543F"
                                : "#3730A3",
                            }}
                          >
                            {isCompleted
                              ? "Completed"
                              : isInProgress
                              ? "In Progress"
                              : isArrived
                              ? "Patient Arrived"
                              : "Draft Saved"}
                          </span>
                          {item.is_pregnant && (
                            <span style={{ padding: "2px 8px", borderRadius: 10, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                              Pregnant · {item.gestational_weeks ? `${item.gestational_weeks}w` : "30 weeks"}
                            </span>
                          )}
                        </div>

                        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, display: "flex", gap: 10, flexWrap: "wrap" }}>
                          <span>{item.case_reference}</span>
                          <span>|</span>
                          <span>{item.reference}</span>
                          <span>|</span>
                          <span>{item.village_name || "Kalyanpur"}</span>
                        </div>

                        <div style={{ fontSize: 13, color: "var(--text-primary)", marginTop: 6, fontWeight: 500 }}>
                          <strong>Concern:</strong> {item.citizen_reported_concern || item.reason}
                        </div>

                        {item.latest_vitals && (
                          <div style={{ fontSize: 12, color: "var(--primary-dark)", display: "flex", gap: 10, marginTop: 4 }}>
                            {item.latest_vitals.systolic_bp && (
                              <span style={{ fontWeight: 700, color: item.latest_vitals.systolic_bp >= 140 ? "var(--urgent)" : "inherit" }}>
                                BP {item.latest_vitals.systolic_bp}/{item.latest_vitals.diastolic_bp}
                              </span>
                            )}
                            {item.latest_vitals.spo2 && <span>• SpO₂ {item.latest_vitals.spo2}%</span>}
                            {item.latest_vitals.pulse && <span>• Pulse {item.latest_vitals.pulse}</span>}
                          </div>
                        )}

                        <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
                          Ref. by: <strong>{item.referring_asha_name}</strong>
                        </div>
                      </div>

                      {/* Right Action Buttons */}
                      <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "flex-end" }}>
                        <div style={{ fontSize: 11, color: isArrived ? "#03543F" : "var(--text-secondary)", fontWeight: 600 }}>
                          {isArrived ? "Arrived 18 min ago" : "Draft autosaved 4 min ago"}
                        </div>

                        {isArrived && (
                          <button
                            disabled={isStarting === item.id}
                            onClick={(e) => handleStartOrResume(e, item)}
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
                            {isStarting === item.id ? "Opening..." : "Start Consultation"}
                          </button>
                        )}

                        {isInProgress && (
                          <button
                            disabled={isStarting === item.id}
                            onClick={(e) => handleStartOrResume(e, item)}
                            style={{
                              padding: "8px 18px",
                              backgroundColor: "#0284C7",
                              color: "#FFF",
                              border: "none",
                              borderRadius: 6,
                              fontSize: 13,
                              fontWeight: 700,
                              cursor: "pointer",
                            }}
                          >
                            Resume Consultation
                          </button>
                        )}

                        {isDraft && !isArrived && (
                          <button
                            onClick={(e) => handleStartOrResume(e, item)}
                            style={{
                              padding: "8px 18px",
                              backgroundColor: "#2563EB",
                              color: "#FFF",
                              border: "none",
                              borderRadius: 6,
                              fontSize: 13,
                              fontWeight: 700,
                              cursor: "pointer",
                            }}
                          >
                            Continue Draft
                          </button>
                        )}

                        {isCompleted && (
                          <button
                            onClick={(e) => handleStartOrResume(e, item)}
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
                            View Consultation
                          </button>
                        )}

                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (item.case_id) {
                                navigate(doctorPaths.caseTimeline(item.case_id) + "?returnTo=/doctor/consultations");
                              } else {
                                alert("Timeline unavailable because this consultation is not linked to a case.");
                              }
                            }}
                            style={{
                              padding: "4px 8px",
                              backgroundColor: "transparent",
                              border: "none",
                              fontSize: 12,
                              fontWeight: 600,
                              color: "var(--primary)",
                              cursor: "pointer",
                              textDecoration: "underline",
                            }}
                          >
                            View Timeline
                          </button>
                          {item.referring_asha_phone && (
                            <a
                              href={`tel:${item.referring_asha_phone}`}
                              style={{
                                padding: "4px 8px",
                                fontSize: 11,
                                color: "#0284C7",
                                textDecoration: "none",
                              }}
                            >
                              📞 Call ASHA
                            </a>
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

        {/* Right Column: Workspace Side Panels (Matching Image 1) */}
        <div style={{ flex: "1 1 320px", minWidth: 280, display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Patients Waiting at PHC */}
          <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 10, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700 }}>Patients Waiting at PHC</h4>
                {waitingData.total > 0 && (
                  <span style={{ padding: "2px 6px", borderRadius: 10, backgroundColor: "#E0F2FE", color: "#0369A1", fontSize: 11, fontWeight: 700 }}>
                    {waitingData.total}
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => {
                  navigate("/doctor/consultations?status=READY_TO_START");
                  setActiveFilter("ARRIVED");
                }}
                style={{
                  background: "none",
                  border: "none",
                  fontSize: 12,
                  color: "var(--primary)",
                  fontWeight: 700,
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                View All ({waitingData.total}) →
              </button>
            </div>

            {waitingLoading ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} style={{ height: 48, backgroundColor: "var(--neutral-bg)", borderRadius: 6, opacity: 0.6 }} />
                ))}
              </div>
            ) : waitingError ? (
              <div style={{ padding: 12, backgroundColor: "#FEF2F2", borderRadius: 8, border: "1px solid #FCA5A5", textAlign: "center", fontSize: 12 }}>
                <div style={{ color: "#991B1B", marginBottom: 6 }}>{waitingError}</div>
                <button
                  type="button"
                  onClick={loadWaitingPatients}
                  style={{ padding: "4px 10px", backgroundColor: "#DC2626", color: "#FFF", border: "none", borderRadius: 4, fontSize: 11, fontWeight: 700, cursor: "pointer" }}
                >
                  Retry
                </button>
              </div>
            ) : waitingData.items.length === 0 ? (
              <div style={{ padding: "16px 12px", textAlign: "center", backgroundColor: "var(--neutral-bg)", borderRadius: 6, color: "var(--text-secondary)", fontSize: 12 }}>
                No patients are currently waiting at this PHC.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {waitingData.items.slice(0, 4).map((p, idx) => {
                  const waitText =
                    p.waiting_minutes < 2
                      ? "Arrived just now"
                      : p.waiting_minutes >= 60
                      ? `Arrived ${Math.floor(p.waiting_minutes / 60)} hr ${p.waiting_minutes % 60} min ago`
                      : `Arrived ${p.waiting_minutes} min ago`;

                  const absTooltip = p.arrived_at
                    ? `Arrival: ${new Date(p.arrived_at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}`
                    : "Arrival time not recorded";

                  const isUrgentBP = p.latest_vitals?.systolic_bp && p.latest_vitals.systolic_bp >= 140;

                  return (
                    <div
                      key={p.referral_id || idx}
                      style={{
                        padding: 12,
                        borderRadius: 8,
                        border: "1px solid var(--border)",
                        backgroundColor: "var(--surface)",
                        display: "flex",
                        flexDirection: "column",
                        gap: 6,
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                            {idx + 1}. {p.citizen_name} ({p.age}y · {p.gender} · {p.village_name})
                          </div>
                          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2, display: "flex", gap: 6 }}>
                            <span>{p.case_reference}</span>
                            <span>|</span>
                            <span>{p.referral_reference}</span>
                          </div>
                        </div>
                        <PriorityBadge priority={p.priority} size="sm" />
                      </div>

                      <div style={{ fontSize: 12, color: "var(--text-primary)", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" as any, overflow: "hidden" }}>
                        <strong>Concern:</strong> {p.chief_concern}
                      </div>

                      {isUrgentBP && (
                        <div style={{ fontSize: 11, fontWeight: 700, color: "var(--urgent)" }}>
                          ⚠️ High BP: {p.latest_vitals.systolic_bp}/{p.latest_vitals.diastolic_bp} mmHg
                        </div>
                      )}

                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4, flexWrap: "wrap", gap: 6 }}>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 600 }} title={absTooltip}>
                          ⏱️ {waitText}
                        </div>
                        <div style={{ display: "flex", gap: 6 }}>
                          <button
                            type="button"
                            disabled={isStarting === p.referral_id}
                            onClick={async (e) => {
                              e.stopPropagation();
                              setIsStarting(p.referral_id);
                              try {
                                const res = await apiClient.startOrResumeConsultation(p.referral_id);
                                await Promise.all([loadWorkspaceData(), loadWaitingPatients()]);
                                navigate(`/doctor/consultations/${res.consultation_id}`);
                              } catch (err) {
                                console.error("Failed to start/resume waiting consultation", err);
                                navigate(`/doctor/cases/${p.case_id}/timeline`);
                              } finally {
                                setIsStarting(null);
                              }
                            }}
                            style={{
                              padding: "4px 10px",
                              backgroundColor: p.consultation_id ? "#0284C7" : "var(--primary)",
                              color: "#FFF",
                              border: "none",
                              borderRadius: 6,
                              fontSize: 11,
                              fontWeight: 700,
                              cursor: "pointer",
                            }}
                          >
                            {isStarting === p.referral_id
                              ? "Opening..."
                              : p.consultation_id
                              ? "Resume Consultation"
                              : "Start Consultation"}
                          </button>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(doctorPaths.caseTimeline(p.case_id) + "?returnTo=/doctor/consultations");
                            }}
                            style={{
                              padding: "4px 8px",
                              backgroundColor: "transparent",
                              border: "1px solid var(--border)",
                              borderRadius: 6,
                              fontSize: 11,
                              fontWeight: 600,
                              color: "var(--text-secondary)",
                              cursor: "pointer",
                            }}
                          >
                            Timeline
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Results Ready for Review */}
          <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 10, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700 }}>
                Results Ready for Review ({referrals.filter((r) => r.status === "AWAITING_INVESTIGATION").length})
              </h4>
              <span onClick={() => setActiveTab("AWAITING_RESULTS")} style={{ fontSize: 11, color: "var(--primary)", fontWeight: 600, cursor: "pointer" }}>View All</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
              {referrals.filter((r) => r.status === "AWAITING_INVESTIGATION").length === 0 ? (
                <div style={{ color: "var(--text-secondary)", fontStyle: "italic" }}>No pending investigation results.</div>
              ) : (
                referrals.filter((r) => r.status === "AWAITING_INVESTIGATION").slice(0, 3).map((p, idx) => (
                  <div key={idx}>
                    <strong>{p.citizen_name}</strong> · <span style={{ color: "var(--text-secondary)" }}>Investigation Orders Available</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* ASHA Escalations Alert */}
          {escalations.length > 0 && (
            <div style={{ backgroundColor: "#FEF3C7", padding: 14, borderRadius: 10, border: "1px solid #FCD34D" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#92400E" }}>ASHA Escalation</div>
                <span style={{ padding: "1px 6px", borderRadius: 4, backgroundColor: "var(--urgent)", color: "#FFF", fontSize: 10, fontWeight: 700 }}>New</span>
              </div>
              <div style={{ fontSize: 12, color: "#92400E" }}>
                <strong>{escalations[0].asha_name || "Sita Patel (ASHA)"}</strong>: {escalations[0].reason || "Repeat BP remains elevated in pregnant woman. Please review and advise."}
              </div>
            </div>
          )}

          {/* Today's Progress */}
          <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 10, border: "1px solid var(--border)" }}>
            <h4 style={{ margin: "0 0 10px", fontSize: 14, fontWeight: 700 }}>Today's Progress</h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, textAlign: "center" }}>
              <div style={{ padding: 8, backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: "var(--primary)" }}>{metrics.completedToday}</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Consultations</div>
              </div>
              <div style={{ padding: 8, backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: "var(--success)" }}>
                  {referrals.filter((r) => r.status === "CONSULTED" || r.status === "PATIENT_ARRIVED" || r.status === "IN_CONSULTATION").length}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Referrals Handled</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
