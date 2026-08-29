import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { doctorPaths } from "./doctorRoutes";
import { apiClient } from "@aarogya/api-client";
import { ChevronRightIcon, SearchIcon } from "../../components/Icons";
import { useRealtime } from "../../hooks/useRealtime";

export function getEventMetadata(eventType: string) {
  switch (eventType) {
    case "REFERRAL_RECEIVED":
      return { icon: "📨", bg: "#EFF6FF", color: "#2563EB", label: "Referral Received" };
    case "REFERRAL_ACKNOWLEDGED":
      return { icon: "✓", bg: "#E0E7FF", color: "#3730A3", label: "Referral Acknowledged" };
    case "PATIENT_ARRIVED":
      return { icon: "🏥", bg: "#DEF7EC", color: "#03543F", label: "Patient Arrived" };
    case "CONSULTATION_STARTED":
      return { icon: "🩺", bg: "#F3E8FF", color: "#7C3AED", label: "Consultation Started" };
    case "CONSULTATION_COMPLETED":
      return { icon: "✅", bg: "#D1FAE5", color: "#065F46", label: "Consultation Completed" };
    case "INVESTIGATION_ORDERED":
      return { icon: "🧪", bg: "#FEF3C7", color: "#92400E", label: "Test Ordered" };
    case "INVESTIGATION_RESULT_AVAILABLE":
      return { icon: "📊", bg: "#E0F2FE", color: "#0369A1", label: "Result Ready" };
    case "PRESCRIPTION_SIGNED":
      return { icon: "💊", bg: "#F0F9FF", color: "#0284C7", label: "Prescription Signed" };
    case "ASHA_FOLLOWUP_ASSIGNED":
      return { icon: "📋", bg: "#CCFBF1", color: "#115E59", label: "Follow-up Assigned" };
    case "ASHA_FOLLOWUP_COMPLETED":
      return { icon: "🎉", bg: "#D1FAE5", color: "#047857", label: "Follow-up Completed" };
    case "ASHA_ESCALATION_CREATED":
      return { icon: "🚨", bg: "#FEE2E2", color: "#991B1B", label: "ASHA Escalation" };
    case "ASHA_ESCALATION_REVIEWED":
      return { icon: "👁️", bg: "#FFEDD5", color: "#C2410C", label: "Escalation Reviewed" };
    case "HIGHER_CENTER_REFERRAL_CREATED":
      return { icon: "🚑", bg: "#F3E8FF", color: "#6B21A8", label: "Higher Center Referral" };
    default:
      return { icon: "ℹ️", bg: "#F1F5F9", color: "#475569", label: "Care Activity" };
  }
}

export function formatRelativeTime(isoStr: string): string {
  if (!isoStr) return "Just now";
  try {
    const dt = new Date(isoStr);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - dt.getTime()) / 1000);

    if (diffSec < 60) return "Just now";
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`;
    return dt.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
  } catch {
    return "Recently";
  }
}

export function formatIndiaTimestamp(isoStr: string): string {
  if (!isoStr) return "Asia/Kolkata";
  try {
    const dt = new Date(isoStr);
    return dt.toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      dateStyle: "medium",
      timeStyle: "short",
    }) + " IST";
  } catch {
    return isoStr;
  }
}

export function DoctorActivityScreen() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const initialEventType = searchParams.get("event_type") || "ALL";
  const initialSearch = searchParams.get("search") || "";

  const [eventTypeFilter, setEventTypeFilter] = useState(initialEventType);
  const [startDate, setStartDate] = useState(searchParams.get("start_date") || "");
  const [endDate, setEndDate] = useState(searchParams.get("end_date") || "");
  const [searchQuery, setSearchQuery] = useState(initialSearch);
  const [page, setPage] = useState(1);

  const [activities, setActivities] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getDoctorActivityList({
        event_type_filter: eventTypeFilter === "ALL" ? undefined : eventTypeFilter,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        search_query: searchQuery.trim() || undefined,
        page,
        limit: 20,
      });

      const data = res?.data || res;
      setActivities(data?.items || []);
      setTotal(data?.total || 0);
    } catch (err: any) {
      console.error("Failed to load doctor activity stream", err);
      setError("Failed to load activity log. Please check server connection.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [eventTypeFilter, startDate, endDate, page]);

  useRealtime(() => {
    loadData();
  });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  const handleRowClick = (item: any) => {
    if (item.target_route) {
      navigate(item.target_route);
    }
  };

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "20px 16px", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Link to="/doctor/dashboard" style={{ fontSize: 13, color: "var(--primary)", fontWeight: 600, textDecoration: "none" }}>
              ← Doctor Dashboard
            </Link>
          </div>
          <h2 style={{ margin: "6px 0 2px", fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>
            Recent Care Activity Log
          </h2>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            PHC-scoped clinical audit & care activity history ({total} events recorded)
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
          🔄 Refresh Activity
        </button>
      </div>

      {/* Filters Bar */}
      <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 12, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 14 }}>
        <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          {/* Event Type Filter */}
          <div style={{ flex: "1 1 200px" }}>
            <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 4 }}>
              EVENT TYPE
            </label>
            <select
              value={eventTypeFilter}
              onChange={(e) => { setEventTypeFilter(e.target.value); setPage(1); }}
              style={{ width: "100%", padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13, outline: "none", backgroundColor: "#FFF" }}
            >
              <option value="ALL">All Care Events</option>
              <option value="REFERRAL_RECEIVED">Referrals Received</option>
              <option value="REFERRAL_ACKNOWLEDGED">Referrals Acknowledged</option>
              <option value="PATIENT_ARRIVED">Patients Arrived</option>
              <option value="CONSULTATION_STARTED">Consultations Started</option>
              <option value="CONSULTATION_COMPLETED">Consultations Completed</option>
              <option value="INVESTIGATION_ORDERED">Investigations Ordered</option>
              <option value="INVESTIGATION_RESULT_AVAILABLE">Test Results Ready</option>
              <option value="PRESCRIPTION_SIGNED">Prescriptions Signed</option>
              <option value="ASHA_FOLLOWUP_ASSIGNED">Follow-ups Assigned</option>
              <option value="ASHA_FOLLOWUP_COMPLETED">Follow-ups Completed</option>
              <option value="ASHA_ESCALATION_CREATED">ASHA Escalations</option>
              <option value="ASHA_ESCALATION_REVIEWED">Escalations Reviewed</option>
              <option value="HIGHER_CENTER_REFERRAL_CREATED">Higher-Center Referrals</option>
            </select>
          </div>

          {/* Start Date */}
          <div style={{ flex: "1 1 150px" }}>
            <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 4 }}>
              FROM DATE
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
              style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13, outline: "none" }}
            />
          </div>

          {/* End Date */}
          <div style={{ flex: "1 1 150px" }}>
            <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 4 }}>
              TO DATE
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
              style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13, outline: "none" }}
            />
          </div>

          {/* Search Query */}
          <div style={{ flex: "2 1 250px" }}>
            <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 4 }}>
              SEARCH PATIENT / CASE
            </label>
            <div style={{ position: "relative" }}>
              <input
                type="text"
                placeholder="Search patient name, case reference..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ width: "100%", padding: "8px 12px 8px 34px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13, outline: "none" }}
              />
              <div style={{ position: "absolute", left: 10, top: 10, color: "var(--text-disabled)" }}>
                <SearchIcon size={14} />
              </div>
            </div>
          </div>

          <button
            type="submit"
            style={{
              marginTop: 18,
              padding: "8px 16px",
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

      {/* Content Feed / States */}
      {loading ? (
        <div style={{ padding: 40, textAlign: "center", backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>Loading clinical activity feed...</div>
        </div>
      ) : error ? (
        <div style={{ padding: 30, textAlign: "center", backgroundColor: "#FEE2E2", borderRadius: 12, border: "1px solid #FCA5A5", color: "#991B1B" }}>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8 }}>{error}</div>
          <button
            onClick={loadData}
            style={{
              padding: "8px 18px",
              backgroundColor: "#DC2626",
              color: "#FFF",
              border: "none",
              borderRadius: 6,
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Retry Loading
          </button>
        </div>
      ) : activities.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center", backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
          No care activity entries match the selected filters.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {activities.map((act) => {
            const meta = getEventMetadata(act.event_type);
            const relTime = formatRelativeTime(act.occurred_at);
            const istTime = formatIndiaTimestamp(act.occurred_at);
            const isExpanded = expandedId === act.event_id;

            return (
              <div
                key={act.event_id}
                tabIndex={0}
                role="button"
                aria-label={`Open details for ${act.title} - ${act.patient_name}`}
                onClick={() => handleRowClick(act)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleRowClick(act);
                  }
                }}
                style={{
                  backgroundColor: "var(--surface)",
                  padding: 16,
                  borderRadius: 12,
                  border: "1px solid var(--border)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 14,
                  cursor: "pointer",
                  transition: "all 0.15s ease-in-out",
                  outline: "none",
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: 14, flex: 1 }}>
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: "50%",
                      backgroundColor: meta.bg,
                      color: meta.color,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 18,
                      flexShrink: 0,
                    }}
                  >
                    {meta.icon}
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <strong style={{ fontSize: 14, color: "var(--text-primary)" }}>{act.title}</strong>
                      <span style={{ fontSize: 12, fontWeight: 700, color: "var(--primary-dark)" }}>{act.patient_name}</span>
                      <span style={{ fontSize: 11, padding: "2px 6px", borderRadius: 4, backgroundColor: "var(--neutral-bg)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                        {act.case_reference}
                      </span>
                    </div>

                    <div
                      style={{
                        fontSize: 13,
                        color: "var(--text-secondary)",
                        marginTop: 4,
                        lineHeight: "1.4",
                        wordBreak: "break-word",
                      }}
                    >
                      {isExpanded ? act.description : (act.description.length > 120 ? `${act.description.slice(0, 120)}...` : act.description)}
                      {act.description.length > 120 && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setExpandedId(isExpanded ? null : act.event_id);
                          }}
                          style={{
                            background: "none",
                            border: "none",
                            color: "var(--primary)",
                            fontWeight: 700,
                            fontSize: 12,
                            cursor: "pointer",
                            marginLeft: 6,
                          }}
                        >
                          {isExpanded ? "Show less" : "Show more"}
                        </button>
                      )}
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 6, fontSize: 11, color: "var(--text-disabled)" }}>
                      <span>👤 {act.actor_name} ({act.actor_role})</span>
                      <span title={istTime}>🕒 {relTime}</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-secondary)" }}>
                  <ChevronRightIcon size={18} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {total > 20 && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10, padding: "12px 16px", backgroundColor: "var(--surface)", borderRadius: 10, border: "1px solid var(--border)" }}>
          <button
            disabled={page === 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            style={{
              padding: "6px 14px",
              borderRadius: 6,
              border: "1px solid var(--border)",
              backgroundColor: page === 1 ? "var(--neutral-bg)" : "#FFF",
              cursor: page === 1 ? "not-allowed" : "pointer",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            ← Previous Page
          </button>
          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>
            Page {page} of {Math.ceil(total / 20)} ({total} items)
          </span>
          <button
            disabled={page >= Math.ceil(total / 20)}
            onClick={() => setPage((p) => p + 1)}
            style={{
              padding: "6px 14px",
              borderRadius: 6,
              border: "1px solid var(--border)",
              backgroundColor: page >= Math.ceil(total / 20) ? "var(--neutral-bg)" : "#FFF",
              cursor: page >= Math.ceil(total / 20) ? "not-allowed" : "pointer",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            Next Page →
          </button>
        </div>
      )}
    </div>
  );
}
