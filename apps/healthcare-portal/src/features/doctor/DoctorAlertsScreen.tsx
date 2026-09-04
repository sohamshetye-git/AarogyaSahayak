import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { doctorRoutes } from "./doctorRoutes";
import { useRealtime } from "../../hooks/useRealtime";

export function DoctorAlertsScreen() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // URL Sync Filters
  const activeSeverity = searchParams.get("severity") || "";
  const activeStatus = searchParams.get("status") || "ACTIVE";
  const activeCategory = searchParams.get("category") || "";
  const activeVillage = searchParams.get("village") || "";
  const searchQuery = searchParams.get("search") || "";
  const sortBy = searchParams.get("sort_by") || "newest";
  const page = parseInt(searchParams.get("page") || "1", 10);

  // States
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [summary, setSummary] = useState<any>({
    critical: 0,
    urgent: 0,
    unread: 0,
    acknowledged: 0,
    snoozed: 0,
    system: 0,
    resolved_today: 0
  });
  const [lastRefreshed, setLastRefreshed] = useState<string>(new Date().toLocaleTimeString());
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  // Resolve Primary Next Action Route using canonical entity IDs
  const getPrimaryActionRoute = (alert: any) => {
    const srcType = (alert.source_entity_type || "").toUpperCase();
    const srcId = alert.source_entity_id;

    if (srcType === "REFERRAL") return doctorRoutes.referral(srcId);
    if (srcType === "CONSULTATION") return doctorRoutes.consultation(srcId);
    if (srcType === "INVESTIGATION") return doctorRoutes.investigation(srcId);
    if (srcType === "FOLLOWUP") return doctorRoutes.followUp(srcId);
    if (srcType === "CITIZEN") return doctorRoutes.patient(srcId);
    if (alert.case_id) return doctorRoutes.timeline(alert.case_id);
    return doctorRoutes.alerts();
  };

  const getPrimaryActionLabel = (alert: any) => {
    const type = alert.alert_type;
    if (type === "URGENT_REFERRAL_CREATED") return "Review Referral";
    if (type === "PATIENT_WAIT_THRESHOLD_EXCEEDED") return "Start Consultation";
    if (type === "CRITICAL_RESULT_AVAILABLE" || type === "RESULT_REVIEW_REQUIRED") return "Review Investigation";
    if (type === "FOLLOWUP_ESCALATED" || type === "MEDICATION_ADHERENCE_ESCALATED") return "Review Follow-up";
    if (type === "CITIZEN_HELP_REQUESTED" || type === "MISSING_INFORMATION_RECEIVED") return "View Patient Record";
    return "Inspect Alert";
  };

  const loadAlerts = async () => {
    setLoading(true);
    setError(null);
    try {
      const filters = {
        page,
        page_size: 15,
        search: searchQuery || undefined,
        category: activeCategory || undefined,
        severity: activeSeverity || undefined,
        status: activeStatus || undefined,
        village: activeVillage || undefined,
        sort_by: sortBy
      };

      const [listRes, sumRes] = await Promise.all([
        apiClient.getDoctorAlerts(filters),
        apiClient.getDoctorAlertsSummary()
      ]);

      const items = listRes?.items || listRes?.data?.items || [];
      const tot = listRes?.total || listRes?.data?.total || 0;
      const sumData = sumRes?.data || sumRes || {};

      setAlerts(items);
      setTotal(tot);
      setSummary(sumData);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err: any) {
      console.error("Failed to load doctor alerts:", err);
      setError(err?.message || "Failed to load alerts from server.");
    } finally {
      setLoading(false);
    }
  };

  useRealtime((event) => {
    if (
      [
        "URGENT_REFERRAL_CREATED",
        "PATIENT_WAIT_THRESHOLD_EXCEEDED",
        "FOLLOWUP_ESCALATED",
        "CRITICAL_RESULT_AVAILABLE",
        "DOCTOR_ALERT_UPDATED"
      ].includes(event)
    ) {
      loadAlerts();
    }
  });

  useEffect(() => {
    loadAlerts();
  }, [activeSeverity, activeStatus, activeCategory, activeVillage, searchQuery, sortBy, page]);

  const updateFilters = (updates: Record<string, string | number>) => {
    const params = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        params.set(k, String(v));
      } else {
        params.delete(k);
      }
    });
    // Reset to page 1 on filter changes if not explicitly passing page
    if (!updates.page) params.set("page", "1");
    setSearchParams(params);
  };

  const handleAcknowledge = async (alertId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setActionInProgress(alertId);
    try {
      await apiClient.acknowledgeDoctorAlert(alertId);
      loadAlerts();
    } catch (err) {
      console.error("Failed to acknowledge alert", err);
    } finally {
      setActionInProgress(null);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 1440, margin: "0 auto", width: "100%" }}>
      {/* 1. Header Row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
            PHC Clinical & Operational Alerts Workspace
          </h1>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
            PHC Clinical Center · Medical Officer Desk · Refreshed: {lastRefreshed} · Real-Time WS Active
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button
            onClick={() => loadAlerts()}
            style={{
              padding: "8px 14px",
              backgroundColor: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer"
            }}
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* 2. Dynamic Metric Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        {[
          { label: "Critical Alerts", count: summary.critical, color: "#DC2626", bg: "#FEF2F2", filter: { severity: "CRITICAL", status: "ACTIVE" } },
          { label: "Urgent Alerts", count: summary.urgent, color: "#EA580C", bg: "#FFF7ED", filter: { severity: "URGENT", status: "ACTIVE" } },
          { label: "New / Unread", count: summary.unread, color: "#1D4ED8", bg: "#EFF6FF", filter: { status: "UNREAD" } },
          { label: "Acknowledged", count: summary.acknowledged, color: "#0284C7", bg: "#F0F9FF", filter: { status: "ACKNOWLEDGED" } },
          { label: "Snoozed", count: summary.snoozed, color: "#D97706", bg: "#FFFBEB", filter: { status: "SNOOZED" } },
          { label: "System Alerts", count: summary.system, color: "#7C3AED", bg: "#F5F3FF", filter: { category: "SYSTEM", status: "ACTIVE" } },
          { label: "Resolved Today", count: summary.resolved_today, color: "#16A34A", bg: "#F0FDF4", filter: { status: "RESOLVED" } },
        ].map((card, idx) => (
          <div
            key={idx}
            onClick={() => updateFilters(card.filter as unknown as Record<string, string | number>)}
            style={{
              backgroundColor: card.bg,
              padding: "14px 16px",
              borderRadius: 10,
              border: `1px solid var(--border)`,
              cursor: "pointer",
              transition: "transform 0.15s ease"
            }}
          >
            <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 700 }}>{card.label}</div>
            <div style={{ fontSize: 26, fontWeight: 800, color: card.color, marginTop: 4 }}>{card.count}</div>
            <div style={{ fontSize: 11, color: card.color, marginTop: 4, fontWeight: 700 }}>Apply Filter →</div>
          </div>
        ))}
      </div>

      {/* 3. Search & Filter Bar */}
      <div style={{ backgroundColor: "var(--surface)", padding: "16px 20px", borderRadius: 12, border: "1px solid var(--border)", display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
        <input
          type="text"
          placeholder="Search patient, case ref, alert ref..."
          value={searchQuery}
          onChange={(e) => updateFilters({ search: e.target.value })}
          style={{ flex: "1 1 240px", minWidth: 200, padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
        />

        <select
          value={activeSeverity}
          onChange={(e) => updateFilters({ severity: e.target.value })}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13, backgroundColor: "var(--surface)" }}
        >
          <option value="">All Severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="URGENT">Urgent</option>
          <option value="HIGH">High</option>
          <option value="INFORMATION">Information</option>
        </select>

        <select
          value={activeCategory}
          onChange={(e) => updateFilters({ category: e.target.value })}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13, backgroundColor: "var(--surface)" }}
        >
          <option value="">All Categories</option>
          <option value="CLINICAL">Clinical</option>
          <option value="REFERRAL">Referral</option>
          <option value="INVESTIGATION">Investigation</option>
          <option value="FOLLOW_UP">Follow-up</option>
          <option value="PRESCRIPTION">Prescription</option>
          <option value="CITIZEN_REQUEST">Citizen Request</option>
          <option value="SYSTEM">System</option>
        </select>

        <select
          value={activeStatus}
          onChange={(e) => updateFilters({ status: e.target.value })}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13, backgroundColor: "var(--surface)" }}
        >
          <option value="ACTIVE">All Active Alerts</option>
          <option value="UNREAD">Unread (New/Seen)</option>
          <option value="ACKNOWLEDGED">Acknowledged</option>
          <option value="SNOOZED">Snoozed</option>
          <option value="RESOLVED">Resolved</option>
          <option value="DISMISSED">Dismissed</option>
          <option value="">All Statuses</option>
        </select>

        <select
          value={sortBy}
          onChange={(e) => updateFilters({ sort_by: e.target.value })}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13, backgroundColor: "var(--surface)" }}
        >
          <option value="newest">Sort by Newest</option>
          <option value="oldest">Sort by Oldest</option>
          <option value="severity">Sort by Severity</option>
          <option value="due_date">Sort by Deadline</option>
        </select>

        {(activeSeverity || activeCategory || searchQuery || activeVillage || activeStatus !== "ACTIVE") && (
          <button
            onClick={() => setSearchParams(new URLSearchParams())}
            style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--neutral-bg)", fontSize: 12, fontWeight: 600, cursor: "pointer" }}
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* 4. Main Alert List */}
      <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
            Loading doctor alerts from PostgreSQL...
          </div>
        ) : error ? (
          <div style={{ padding: 30, textAlign: "center", backgroundColor: "#FEF2F2", borderRadius: 8, border: "1px solid #FCA5A5" }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#991B1B" }}>Error Loading Alerts</div>
            <div style={{ fontSize: 13, color: "#B91C1C", marginTop: 4, marginBottom: 12 }}>{error}</div>
            <button
              onClick={loadAlerts}
              style={{ padding: "6px 14px", backgroundColor: "#991B1B", color: "#FFF", borderRadius: 6, border: "none", fontWeight: 700, cursor: "pointer" }}
            >
              Retry Loading
            </button>
          </div>
        ) : alerts.length === 0 ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
            <div style={{ fontSize: 16, fontWeight: 700 }}>No Doctor Alerts Match Selected Filters</div>
            <div style={{ fontSize: 13, marginTop: 4 }}>All clinical workflow items are current and up to date.</div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {alerts.map((alert) => {
              const primaryRoute = getPrimaryActionRoute(alert);
              const primaryLabel = getPrimaryActionLabel(alert);
              const isUnread = alert.status === "NEW" || alert.status === "SEEN";

              return (
                <div
                  key={alert.id}
                  onClick={() => navigate(`/doctor/alerts/${alert.id}`)}
                  style={{
                    padding: 16,
                    borderRadius: 10,
                    border: alert.severity === "CRITICAL" ? "2px solid #EF4444" : alert.severity === "URGENT" ? "1px solid #F97316" : "1px solid var(--border)",
                    backgroundColor: isUnread ? "#EFF6FF" : "var(--surface)",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                    transition: "all 0.15s ease"
                  }}
                >
                  {/* Top Badge Row */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span
                        style={{
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: 11,
                          fontWeight: 800,
                          backgroundColor: alert.severity === "CRITICAL" ? "#DC2626" : alert.severity === "URGENT" ? "#EA580C" : alert.severity === "HIGH" ? "#D97706" : "#0284C7",
                          color: "#FFF"
                        }}
                      >
                        {alert.severity}
                      </span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)" }}>
                        {alert.category} · Ref: {alert.alert_reference}
                      </span>
                      {isUnread && (
                        <span style={{ padding: "2px 6px", borderRadius: 4, fontSize: 10, fontWeight: 800, backgroundColor: "#1D4ED8", color: "#FFF" }}>
                          UNREAD
                        </span>
                      )}
                    </div>
                    <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                      {new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  {/* Title & Summary */}
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>{alert.title}</div>
                    <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>{alert.safe_summary}</div>
                  </div>

                  {/* Context & Actions Footer */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4, flexWrap: "wrap", gap: 10 }}>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                      Patient: <strong>{alert.citizen_name}</strong> · Village: <strong>{alert.village_name}</strong> · Status: <strong>{alert.status}</strong>
                    </div>

                    <div style={{ display: "flex", gap: 8, alignItems: "center" }} onClick={(e) => e.stopPropagation()}>
                      {isUnread && (
                        <button
                          disabled={actionInProgress === alert.id}
                          onClick={(e) => handleAcknowledge(alert.id, e)}
                          style={{
                            padding: "6px 12px",
                            backgroundColor: "var(--surface)",
                            border: "1px solid var(--border)",
                            borderRadius: 6,
                            fontSize: 12,
                            fontWeight: 700,
                            cursor: "pointer"
                          }}
                        >
                          Acknowledge
                        </button>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(primaryRoute);
                        }}
                        style={{
                          padding: "6px 14px",
                          backgroundColor: "var(--primary)",
                          color: "#FFF",
                          border: "none",
                          borderRadius: 6,
                          fontSize: 12,
                          fontWeight: 700,
                          cursor: "pointer"
                        }}
                      >
                        {primaryLabel} →
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination */}
        {total > 15 && (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 20 }}>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              Showing {((page - 1) * 15) + 1} - {Math.min(page * 15, total)} of {total} alerts
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                disabled={page <= 1}
                onClick={() => updateFilters({ page: page - 1 })}
                style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)", cursor: page <= 1 ? "not-allowed" : "pointer" }}
              >
                Previous
              </button>
              <button
                disabled={page * 15 >= total}
                onClick={() => updateFilters({ page: page + 1 })}
                style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)", cursor: page * 15 >= total ? "not-allowed" : "pointer" }}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
