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
  VisitIcon,
  ChevronRightIcon,
  PillIcon,
  ShieldCheckIcon,
} from "../../components/Icons";
import { useRealtime } from "../../hooks/useRealtime";

export function DoctorFollowupsScreen() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const initialStatus = searchParams.get("status") || "ACTIONABLE";
  const [activeFilter, setActiveFilter] = useState<string>(initialStatus);
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");
  const [sortBy, setSortBy] = useState<string>("due_date_first");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [page, setPage] = useState(1);

  const [followups, setFollowups] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState<string | null>(null);
  const [lastSynced, setLastSynced] = useState<string>(new Date().toLocaleTimeString());

  // Modal States
  const [activeModal, setActiveModal] = useState<"REVIEW" | "DIRECTIVE" | "RESOLVE" | "REPEAT" | null>(null);
  const [selectedFup, setSelectedFup] = useState<any | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [directiveText, setDirectiveText] = useState("");
  const [directiveDueDate, setDirectiveDueDate] = useState("");
  const [directivePriority, setDirectivePriority] = useState("HIGH");
  const [resolveNotes, setResolveNotes] = useState("");
  const [resolveOutcome, setResolveOutcome] = useState("RESOLVED_SATISFACTORILY");
  const [repeatVitals, setRepeatVitals] = useState<string[]>(["systolic_bp", "diastolic_bp"]);
  const [repeatNotes, setRepeatNotes] = useState("");

  useEffect(() => {
    const st = searchParams.get("status");
    if (st) setActiveFilter(st);
  }, [searchParams]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, listRes] = await Promise.all([
        apiClient.getDoctorFollowupsSummary(),
        apiClient.getDoctorFollowups({
          status: activeFilter === "ALL" ? undefined : activeFilter,
          priority: priorityFilter === "ALL" ? undefined : priorityFilter,
          query: searchQuery.trim() || undefined,
          page,
          limit: 20,
        }),
      ]);

      setSummary(sumRes?.data || sumRes || null);
      const listData = listRes?.data || listRes;
      setFollowups(listData?.items || listData || []);
      setTotal(listData?.total ?? (listData?.items ? listData.items.length : (Array.isArray(listData) ? listData.length : 0)));
      setLastSynced(new Date().toLocaleTimeString());
    } catch (err: any) {
      console.error("Failed to load doctor follow-ups workspace", err);
      setError("Failed to connect to follow-up service. Please check server.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeFilter, priorityFilter, page]);

  useRealtime(() => {
    loadData();
  });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  const handleFilterClick = (statusKey: string) => {
    setActiveFilter(statusKey);
    setPage(1);
    setSearchParams({ status: statusKey });
  };

  const handleAcknowledge = async (e: React.MouseEvent, fup: any) => {
    e.stopPropagation();
    const fupId = fup.follow_up_id || fup.id;
    setIsProcessing(fupId);
    try {
      await apiClient.acknowledgeDoctorFollowup(fupId);
      await loadData();
    } catch (err) {
      console.error("Failed to acknowledge escalation", err);
      alert("Failed to acknowledge escalation.");
    } finally {
      setIsProcessing(null);
    }
  };

  const handleCallAsha = async (e: React.MouseEvent, fup: any) => {
    e.stopPropagation();
    const fupId = fup.follow_up_id || fup.id;
    try {
      await apiClient.recordAshaContact(fupId);
      alert(`Call attempt logged to ASHA worker ${fup.assigned_asha_name || 'Sita Patel'}`);
    } catch (err) {
      console.error("Failed to log call", err);
    }
  };

  const handleOpenModal = (modalType: "REVIEW" | "DIRECTIVE" | "RESOLVE" | "REPEAT", fup: any) => {
    setSelectedFup(fup);
    setActiveModal(modalType);
    if (modalType === "REVIEW") {
      setReviewNote("Follow-up result reviewed by PHC Doctor. No immediate escalation needed.");
    } else if (modalType === "DIRECTIVE") {
      setDirectiveText(fup.directive || fup.instructions || "Repeat BP in 48 hours and check compliance.");
      setDirectiveDueDate("");
      setDirectivePriority(fup.priority || "HIGH");
    } else if (modalType === "RESOLVE") {
      setResolveNotes("Patient symptoms resolved and vitals stabilized.");
      setResolveOutcome("RESOLVED_SATISFACTORILY");
    } else if (modalType === "REPEAT") {
      setRepeatVitals(fup.measurements_to_repeat || ["systolic_bp", "diastolic_bp"]);
      setRepeatNotes("Please perform repeat BP check tomorrow morning.");
    }
  };

  const handleSubmitModal = async () => {
    if (!selectedFup) return;
    const fupId = selectedFup.follow_up_id || selectedFup.id;
    setIsProcessing(fupId);
    try {
      if (activeModal === "REVIEW") {
        await apiClient.reviewDoctorFollowup(fupId, { review_notes: reviewNote });
      } else if (activeModal === "DIRECTIVE") {
        await apiClient.updateDoctorFollowupDirective(fupId, {
          instructions: directiveText,
          due_at: directiveDueDate ? new Date(directiveDueDate).toISOString() : undefined,
          priority: directivePriority,
        });
      } else if (activeModal === "RESOLVE") {
        await apiClient.resolveDoctorFollowup(fupId, {
          resolution_notes: resolveNotes,
          resolution_outcome: resolveOutcome,
        });
      } else if (activeModal === "REPEAT") {
        await apiClient.requestRepeatVitals(fupId, {
          vitals_to_repeat: repeatVitals,
          notes: repeatNotes,
        });
      }
      setActiveModal(null);
      setSelectedFup(null);
      await loadData();
    } catch (err) {
      console.error("Failed to process follow-up action", err);
      alert("Failed to process follow-up action. Please try again.");
    } finally {
      setIsProcessing(null);
    }
  };

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "20px 16px", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Link to="/doctor/dashboard" style={{ fontSize: 13, color: "var(--primary)", fontWeight: 600, textDecoration: "none" }}>
              ← Doctor Dashboard
            </Link>
          </div>
          <h2 style={{ margin: "4px 0 2px", fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>
            ASHA Follow-up Review Workspace
          </h2>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            Kalyanpur PHC · Clinical field checkups, repeat vitals & escalations (Synced: {lastSynced})
          </span>
        </div>

        <button
          onClick={loadData}
          style={{
            padding: "8px 16px",
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
          🔄 Refresh Workspace
        </button>
      </div>

      {/* Dynamic Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 12 }}>
        <button
          onClick={() => handleFilterClick("REVIEW_REQUIRED")}
          style={{
            padding: 14,
            borderRadius: 10,
            border: activeFilter === "REVIEW_REQUIRED" ? "2px solid #0284C7" : "1px solid var(--border)",
            backgroundColor: "#E0F2FE",
            textAlign: "left",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 700, color: "#0369A1" }}>🧪 Result Ready</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#0284C7", marginTop: 4 }}>
            {summary?.results_ready_count ?? 0}
          </div>
          <div style={{ fontSize: 11, color: "#0369A1", marginTop: 2 }}>Awaiting doctor review</div>
        </button>

        <button
          onClick={() => handleFilterClick("ESCALATED")}
          style={{
            padding: 14,
            borderRadius: 10,
            border: activeFilter === "ESCALATED" ? "2px solid #DC2626" : "1px solid var(--border)",
            backgroundColor: "#FEE2E2",
            textAlign: "left",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 700, color: "#991B1B" }}>🚨 Escalated</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#DC2626", marginTop: 4 }}>
            {summary?.escalated_count ?? 0}
          </div>
          <div style={{ fontSize: 11, color: "#991B1B", marginTop: 2 }}>Urgent ASHA alerts</div>
        </button>

        <button
          onClick={() => handleFilterClick("OVERDUE")}
          style={{
            padding: 14,
            borderRadius: 10,
            border: activeFilter === "OVERDUE" ? "2px solid #EA580C" : "1px solid var(--border)",
            backgroundColor: "#FFEDD5",
            textAlign: "left",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 700, color: "#C2410C" }}>⚠️ Overdue</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#EA580C", marginTop: 4 }}>
            {summary?.overdue_count ?? 0}
          </div>
          <div style={{ fontSize: 11, color: "#C2410C", marginTop: 2 }}>Past assigned due date</div>
        </button>

        <button
          onClick={() => handleFilterClick("DUE_TODAY")}
          style={{
            padding: 14,
            borderRadius: 10,
            border: activeFilter === "DUE_TODAY" ? "2px solid #D97706" : "1px solid var(--border)",
            backgroundColor: "#FEF3C7",
            textAlign: "left",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 700, color: "#92400E" }}>📅 Due Today</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#D97706", marginTop: 4 }}>
            {summary?.due_today_count ?? 0}
          </div>
          <div style={{ fontSize: 11, color: "#92400E", marginTop: 2 }}>Scheduled field visits</div>
        </button>

        <button
          onClick={() => handleFilterClick("PENDING")}
          style={{
            padding: 14,
            borderRadius: 10,
            border: activeFilter === "PENDING" ? "2px solid #475569" : "1px solid var(--border)",
            backgroundColor: "#F1F5F9",
            textAlign: "left",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>⏳ Pending ASHA</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#334155", marginTop: 4 }}>
            {summary?.pending_count ?? 0}
          </div>
          <div style={{ fontSize: 11, color: "#475569", marginTop: 2 }}>In progress in field</div>
        </button>

        <button
          onClick={() => handleFilterClick("REVIEWED")}
          style={{
            padding: 14,
            borderRadius: 10,
            border: activeFilter === "REVIEWED" ? "2px solid #16A34A" : "1px solid var(--border)",
            backgroundColor: "#DCFCE7",
            textAlign: "left",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 700, color: "#15803D" }}>✓ Reviewed Today</div>
          <div style={{ fontSize: 22, fontWeight: 800, color: "#16A34A", marginTop: 4 }}>
            {summary?.reviewed_today_count ?? 0}
          </div>
          <div style={{ fontSize: 11, color: "#15803D", marginTop: 2 }}>Completed & signed off</div>
        </button>
      </div>

      {/* Search & Filters */}
      <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 12, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 14 }}>
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          {/* Status Tabs */}
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", flex: 1 }}>
            {[
              { id: "ACTIONABLE", label: "All Actionable" },
              { id: "REVIEW_REQUIRED", label: "Result Ready" },
              { id: "ESCALATED", label: "Escalated" },
              { id: "OVERDUE", label: "Overdue" },
              { id: "DUE_TODAY", label: "Due Today" },
              { id: "PENDING", label: "Pending" },
              { id: "REVIEWED", label: "Reviewed" },
              { id: "RESOLVED", label: "Resolved" },
              { id: "ALL", label: "All Records" },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => handleFilterClick(tab.id)}
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

          {/* Priority Select */}
          <select
            value={priorityFilter}
            onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}
            style={{ padding: "7px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13, backgroundColor: "#FFF" }}
          >
            <option value="ALL">All Priorities</option>
            <option value="URGENT">Urgent Priority</option>
            <option value="HIGH">High Priority</option>
            <option value="ROUTINE">Routine Priority</option>
          </select>

          {/* Search Query */}
          <div style={{ position: "relative", minWidth: 220 }}>
            <input
              type="text"
              placeholder="Search patient, case ref, ASHA, village..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: "100%", padding: "7px 12px 7px 32px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
            />
            <div style={{ position: "absolute", left: 10, top: 9, color: "var(--text-disabled)" }}>
              <SearchIcon size={14} />
            </div>
          </div>

          <button
            type="submit"
            style={{
              padding: "7px 16px",
              backgroundColor: "var(--primary)",
              color: "#FFF",
              border: "none",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Search
          </button>
        </form>
      </div>

      {/* Content Feed */}
      {loading ? (
        <div style={{ padding: 40, textAlign: "center", backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>Loading ASHA follow-up records...</div>
        </div>
      ) : error ? (
        <div style={{ padding: 30, textAlign: "center", backgroundColor: "#FEE2E2", borderRadius: 12, border: "1px solid #FCA5A5", color: "#991B1B" }}>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8 }}>{error}</div>
          <button onClick={loadData} style={{ padding: "8px 18px", backgroundColor: "#DC2626", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}>
            Retry Loading
          </button>
        </div>
      ) : followups.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center", backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
          No ASHA follow-up records match the selected filter criteria.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {followups.map((fup: any) => {
            const fupId = fup.follow_up_id || fup.id;
            const statusKey = fup.status || "PENDING";
            const isEscalated = statusKey === "ESCALATED";
            const isCompleted = statusKey === "COMPLETED" || statusKey === "RESULT_READY";
            const isOverdue = statusKey === "OVERDUE";
            const isAcknowledged = statusKey === "DOCTOR_ACKNOWLEDGED";

            let badgeBg = "#F1F5F9";
            let badgeColor = "#475569";
            let badgeLabel = "Pending ASHA";
            let badgeIcon = "⏳";

            if (isEscalated) {
              badgeBg = "#FEE2E2"; badgeColor = "#991B1B"; badgeLabel = "Escalated"; badgeIcon = "🚨";
            } else if (isOverdue) {
              badgeBg = "#FFEDD5"; badgeColor = "#C2410C"; badgeLabel = "Overdue"; badgeIcon = "⚠️";
            } else if (isCompleted) {
              badgeBg = "#E0F2FE"; badgeColor = "#0369A1"; badgeLabel = "Result Ready"; badgeIcon = "🧪";
            } else if (isAcknowledged) {
              badgeBg = "#E0E7FF"; badgeColor = "#3730A3"; badgeLabel = "Acknowledged"; badgeIcon = "✓";
            } else if (statusKey === "REVIEWED" || statusKey === "RESOLVED") {
              badgeBg = "#DCFCE7"; badgeColor = "#15803D"; badgeLabel = "Reviewed & Closed"; badgeIcon = "✓";
            }

            return (
              <div
                key={fupId}
                style={{
                  padding: 18,
                  backgroundColor: "var(--surface)",
                  borderRadius: 12,
                  border: isEscalated ? "2px solid #FCA5A5" : "1px solid var(--border)",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                }}
              >
                {/* Escalation Alert Banner if present */}
                {isEscalated && (
                  <div style={{ padding: "10px 14px", backgroundColor: "#FEF2F2", border: "1px solid #FCA5A5", borderRadius: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, fontWeight: 700, color: "#991B1B" }}>
                      <span>🚨 ASHA Escalation Alert:</span>
                      <span>{fup.completion_notes || fup.directive || "Urgent clinical escalation submitted from field visit."}</span>
                    </div>
                    {!isAcknowledged && (
                      <button
                        disabled={isProcessing === fupId}
                        onClick={(e) => handleAcknowledge(e, fup)}
                        style={{
                          padding: "4px 10px",
                          backgroundColor: "#991B1B",
                          color: "#FFF",
                          border: "none",
                          borderRadius: 6,
                          fontSize: 11,
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                      >
                        {isProcessing === fupId ? "Acknowledging..." : "✓ Acknowledge"}
                      </button>
                    )}
                  </div>
                )}

                {/* Top Row: Patient Demographics & Badges */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 10 }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <strong style={{ fontSize: 16, color: "var(--text-primary)" }}>{fup.patient_name || fup.citizen_name || "Citizen"}</strong>
                      <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                        ({fup.patient_age ?? fup.age ?? 28}y · {fup.patient_gender || fup.gender || "Female"} · {fup.village_name || "Kalyanpur"})
                      </span>
                      {fup.is_pregnant && (
                        <span style={{ padding: "2px 8px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                          🤰 Maternal ({fup.gestational_weeks ? `${fup.gestational_weeks}w` : "28w"})
                        </span>
                      )}
                      <PriorityBadge priority={fup.priority} size="sm" />
                    </div>

                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, display: "flex", gap: 12, flexWrap: "wrap" }}>
                      <span>Case: <strong>{fup.case_reference || "CASE-001"}</strong></span>
                      <span>Follow-up: <strong>{fup.follow_up_reference || fup.reference || `FUP-${fupId.slice(0, 8)}`}</strong></span>
                      <span>Source: <strong>{fup.source || "DOCTOR_ASSIGNED"}</strong></span>
                      <span>ASHA: <strong>{fup.assigned_asha_name || "Sita Patel"}</strong></span>
                    </div>
                  </div>

                  <span style={{ padding: "4px 10px", borderRadius: 8, backgroundColor: badgeBg, color: badgeColor, fontWeight: 700, fontSize: 12, display: "inline-flex", alignItems: "center", gap: 5 }}>
                    {badgeIcon} {badgeLabel}
                  </span>
                </div>

                {/* Doctor Directive */}
                <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}>
                  <div style={{ fontWeight: 700, color: "var(--text-primary)", marginBottom: 2 }}>
                    📋 Doctor Directive:
                  </div>
                  <div style={{ color: "var(--text-secondary)" }}>{fup.directive || fup.instructions || "Conduct ASHA home follow-up."}</div>
                  <div style={{ fontSize: 11, color: "var(--text-disabled)", marginTop: 4, display: "flex", justifyContent: "space-between" }}>
                    <span>Assigned Doctor: <strong>{fup.created_by_doctor_name || fup.assigned_doctor_name || "Medical Officer"}</strong></span>
                    <span>Due Date: <strong>{fup.due_at ? new Date(fup.due_at).toLocaleDateString() : "Today"}</strong></span>
                  </div>
                </div>

                {/* Vitals & Outcomes (if recorded) */}
                {fup.latest_vitals && (
                  <div style={{ display: "flex", gap: 14, flexWrap: "wrap", fontSize: 12, padding: "8px 12px", backgroundColor: "#F0F9FF", border: "1px solid #BAE6FD", borderRadius: 8 }}>
                    <div style={{ color: "#0369A1", fontWeight: 700 }}>📊 Field Vitals Recorded:</div>
                    {fup.latest_vitals.systolic_bp && (
                      <span style={{ fontWeight: fup.latest_vitals.systolic_bp >= 140 ? 700 : 500, color: fup.latest_vitals.systolic_bp >= 140 ? "#DC2626" : "#0369A1" }}>
                        BP: {fup.latest_vitals.systolic_bp}/{fup.latest_vitals.diastolic_bp} mmHg
                      </span>
                    )}
                    {fup.latest_vitals.spo2 && (
                      <span style={{ color: fup.latest_vitals.spo2 <= 94 ? "#DC2626" : "#0369A1" }}>
                        SpO₂: {fup.latest_vitals.spo2}%
                      </span>
                    )}
                    {fup.latest_vitals.pulse && <span>Pulse: {fup.latest_vitals.pulse} bpm</span>}
                    {fup.symptoms_outcome && (
                      <span style={{ fontWeight: 700, color: fup.symptoms_outcome === "WORSENED" ? "#DC2626" : "#16A34A" }}>
                        Progression: {fup.symptoms_outcome}
                      </span>
                    )}
                  </div>
                )}

                {/* Action Command Bar */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8, paddingTop: 6, borderTop: "1px dashed var(--border)" }}>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <button
                      onClick={(e) => handleCallAsha(e, fup)}
                      style={{
                        padding: "6px 12px",
                        backgroundColor: "#FFF",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      📞 Call ASHA ({fup.assigned_asha_name})
                    </button>
                    <button
                      onClick={() => navigate(doctorPaths.caseTimeline(fup.case_id) + "?returnTo=/doctor/followups")}
                      style={{
                        padding: "6px 12px",
                        backgroundColor: "#FFF",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      View Case Timeline
                    </button>
                  </div>

                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <button
                      onClick={() => handleOpenModal("REPEAT", fup)}
                      style={{
                        padding: "6px 12px",
                        backgroundColor: "#FFF",
                        color: "#0D9488",
                        border: "1px solid #0D9488",
                        borderRadius: 6,
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      🔄 Request Repeat Vitals
                    </button>

                    <button
                      onClick={() => handleOpenModal("DIRECTIVE", fup)}
                      style={{
                        padding: "6px 12px",
                        backgroundColor: "#FFF",
                        color: "#7C3AED",
                        border: "1px solid #7C3AED",
                        borderRadius: 6,
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      ✏️ Modify Directive
                    </button>

                    {isCompleted && (
                      <button
                        onClick={() => handleOpenModal("REVIEW", fup)}
                        style={{
                          padding: "6px 14px",
                          backgroundColor: "#0284C7",
                          color: "#FFF",
                          border: "none",
                          borderRadius: 6,
                          fontSize: 12,
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                      >
                        ✓ Mark Reviewed
                      </button>
                    )}

                    <button
                      onClick={() => handleOpenModal("RESOLVE", fup)}
                      style={{
                        padding: "6px 14px",
                        backgroundColor: "#16A34A",
                        color: "#FFF",
                        border: "none",
                        borderRadius: 6,
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      ✓ Resolve Follow-up
                    </button>

                    <button
                      data-testid={`fup-review-detail-btn-${fupId}`}
                      onClick={() => navigate(doctorPaths.followUpDetail(fup.follow_up_id || fupId, `/doctor/followups?status=${activeFilter}`))}
                      style={{
                        padding: "6px 14px",
                        backgroundColor: "var(--primary)",
                        color: "#FFF",
                        border: "none",
                        borderRadius: 6,
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      Review Detail →
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", backgroundColor: "var(--surface)", borderRadius: 10, border: "1px solid var(--border)" }}>
          <button
            disabled={page === 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid var(--border)", cursor: page === 1 ? "not-allowed" : "pointer" }}
          >
            ← Previous Page
          </button>
          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>
            Page {page} of {Math.ceil(total / 20)} ({total} records)
          </span>
          <button
            disabled={page >= Math.ceil(total / 20)}
            onClick={() => setPage((p) => p + 1)}
            style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid var(--border)", cursor: page >= Math.ceil(total / 20) ? "not-allowed" : "pointer" }}
          >
            Next Page →
          </button>
        </div>
      )}

      {/* Doctor Review Modal */}
      {activeModal === "REVIEW" && selectedFup && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "#FFF", padding: 24, borderRadius: 12, maxWidth: 500, width: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#0284C7" }}>
              ✓ Mark Follow-up Result Reviewed
            </h3>
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
              Patient: <strong>{selectedFup.patient_name}</strong> · Follow-up: <strong>FUP-{(selectedFup.follow_up_id || selectedFup.id).slice(0, 8)}</strong>
            </p>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 6 }}>DOCTOR REVIEW NOTE</label>
              <textarea
                rows={4}
                value={reviewNote}
                onChange={(e) => setReviewNote(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button onClick={() => setActiveModal(null)} style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)", cursor: "pointer" }}>
                Cancel
              </button>
              <button onClick={handleSubmitModal} disabled={!!isProcessing} style={{ padding: "8px 18px", backgroundColor: "#0284C7", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}>
                {isProcessing ? "Submitting..." : "Confirm Review & Sign-off"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modify Directive Modal */}
      {activeModal === "DIRECTIVE" && selectedFup && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "#FFF", padding: 24, borderRadius: 12, maxWidth: 500, width: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#7C3AED" }}>
              ✏️ Modify Doctor Directive for ASHA Worker
            </h3>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 6 }}>NEW INSTRUCTIONS FOR ASHA</label>
              <textarea
                rows={4}
                value={directiveText}
                onChange={(e) => setDirectiveText(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 6 }}>NEW DUE DATE (OPTIONAL)</label>
              <input
                type="datetime-local"
                value={directiveDueDate}
                onChange={(e) => setDirectiveDueDate(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button onClick={() => setActiveModal(null)} style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)", cursor: "pointer" }}>
                Cancel
              </button>
              <button onClick={handleSubmitModal} disabled={!directiveText.trim() || !!isProcessing} style={{ padding: "8px 18px", backgroundColor: "#7C3AED", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}>
                {isProcessing ? "Saving..." : "Save Directive & Notify ASHA"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Resolve Follow-up Modal */}
      {activeModal === "RESOLVE" && selectedFup && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "#FFF", padding: 24, borderRadius: 12, maxWidth: 500, width: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#16A34A" }}>
              ✓ Resolve & Close Follow-up Record
            </h3>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 6 }}>RESOLUTION OUTCOME</label>
              <select
                value={resolveOutcome}
                onChange={(e) => setResolveOutcome(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
              >
                <option value="RESOLVED_SATISFACTORILY">Resolved Satisfactorily</option>
                <option value="PATIENT_RECOVERED">Patient Symptoms Recovered</option>
                <option value="PATIENT_ATTENDED_PHC">Patient Attended PHC Consultation</option>
                <option value="NO_FURTHER_ACTION">No Further Action Required</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 6 }}>CLINICAL DISPOSITION NOTE</label>
              <textarea
                rows={4}
                value={resolveNotes}
                onChange={(e) => setResolveNotes(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button onClick={() => setActiveModal(null)} style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)", cursor: "pointer" }}>
                Cancel
              </button>
              <button onClick={handleSubmitModal} disabled={!resolveNotes.trim() || !!isProcessing} style={{ padding: "8px 18px", backgroundColor: "#16A34A", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}>
                {isProcessing ? "Resolving..." : "Confirm Resolution & Close"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Repeat Vitals Modal */}
      {activeModal === "REPEAT" && selectedFup && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "#FFF", padding: 24, borderRadius: 12, maxWidth: 500, width: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#0D9488" }}>
              🔄 Request Repeat Vitals Check by ASHA
            </h3>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 6 }}>MEASUREMENTS TO REPEAT</label>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 13 }}>
                {["systolic_bp", "diastolic_bp", "spo2", "pulse", "temperature_c", "glucose_mg_dl"].map((v) => (
                  <label key={v} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={repeatVitals.includes(v)}
                      onChange={(e) => {
                        if (e.target.checked) setRepeatVitals([...repeatVitals, v]);
                        else setRepeatVitals(repeatVitals.filter((x) => x !== v));
                      }}
                    />
                    {v.replace("_", " ").toUpperCase()}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 6 }}>ADDITIONAL INSTRUCTIONS</label>
              <textarea
                rows={3}
                value={repeatNotes}
                onChange={(e) => setRepeatNotes(e.target.value)}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button onClick={() => setActiveModal(null)} style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)", cursor: "pointer" }}>
                Cancel
              </button>
              <button onClick={handleSubmitModal} disabled={repeatVitals.length === 0 || !!isProcessing} style={{ padding: "8px 18px", backgroundColor: "#0D9488", color: "#FFF", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}>
                {isProcessing ? "Sending..." : "Submit Repeat Request"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
