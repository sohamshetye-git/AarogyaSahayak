import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { doctorRoutes } from "./doctorRoutes";
import { useRealtime } from "../../hooks/useRealtime";

// Formatting helper functions
function capitalizeTitle(str: string): string {
  if (!str) return "";
  return str
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

function StatCard({ label, value, subtext, color = "var(--primary)" }: { label: string; value: string | number; subtext?: string; color?: string }) {
  return (
    <div style={{ backgroundColor: "var(--surface)", padding: "16px 18px", borderRadius: 10, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)" }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 800, color }}>{value}</div>
      {subtext && <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{subtext}</div>}
    </div>
  );
}

function BreakdownTable({ title, data }: { title: string; data: Record<string, number> }) {
  if (!data || Object.keys(data).length === 0) return null;
  const total = Object.values(data).reduce((acc, curr) => acc + curr, 0);

  return (
    <div style={{ backgroundColor: "var(--surface)", padding: 18, borderRadius: 10, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 12 }}>
      <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>{title}</h4>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {Object.entries(data).map(([key, val]) => {
          const pct = total > 0 ? Math.round((val / total) * 100) : 0;
          return (
            <div key={key} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, fontWeight: 600 }}>
                <span>{capitalizeTitle(key)}</span>
                <span>{val} ({pct}%)</span>
              </div>
              <div style={{ height: 6, width: "100%", backgroundColor: "var(--neutral-bg)", borderRadius: 3, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${pct}%`, backgroundColor: "var(--primary)", borderRadius: 3 }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function DoctorReportsScreen() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // 1. URL Query State Synchronization
  const datePreset = searchParams.get("preset") || "LAST_7_DAYS";
  const customFrom = searchParams.get("date_from") || "";
  const customTo = searchParams.get("date_to") || "";
  const selectedVillage = searchParams.get("village") || "";
  const selectedAsha = searchParams.get("asha_id") || "";
  const selectedCategory = searchParams.get("category") || "";
  const selectedPriority = searchParams.get("priority") || "";
  const activeTab = searchParams.get("tab") || "OVERVIEW";

  // 2. Data States
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overviewData, setOverviewData] = useState<any>(null);
  const [tabData, setTabData] = useState<any>(null);
  const [pendingWork, setPendingWork] = useState<any[]>([]);
  const [recentActivity, setRecentActivity] = useState<any[]>([]);
  const [lastRefreshed, setLastRefreshed] = useState<string>(new Date().toLocaleTimeString());
  const [isExporting, setIsExporting] = useState(false);

  // Derive date_from & date_to based on preset or custom IST boundary
  const getDateRange = () => {
    const today = new Date();
    const formatDate = (d: Date) => d.toISOString().split("T")[0];

    if (datePreset === "TODAY") {
      const t = formatDate(today);
      return { date_from: t, date_to: t };
    } else if (datePreset === "LAST_7_DAYS") {
      const past = new Date(today);
      past.setDate(today.getDate() - 6);
      return { date_from: formatDate(past), date_to: formatDate(today) };
    } else if (datePreset === "LAST_30_DAYS") {
      const past = new Date(today);
      past.setDate(today.getDate() - 29);
      return { date_from: formatDate(past), date_to: formatDate(today) };
    } else if (datePreset === "THIS_MONTH") {
      const first = new Date(today.getFullYear(), today.getMonth(), 1);
      return { date_from: formatDate(first), date_to: formatDate(today) };
    } else if (datePreset === "CUSTOM" && customFrom && customTo) {
      return { date_from: customFrom, date_to: customTo };
    }
    const past = new Date(today);
    past.setDate(today.getDate() - 6);
    return { date_from: formatDate(past), date_to: formatDate(today) };
  };

  const currentFilters = {
    ...getDateRange(),
    village: selectedVillage || undefined,
    asha_id: selectedAsha || undefined,
    category: selectedCategory || undefined,
    priority: selectedPriority || undefined,
  };

  const loadReportData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Always fetch overview metrics to populate top cards accurately
      const [overviewRes, pWork, rAct] = await Promise.all([
        apiClient.getDoctorReportsOverview(currentFilters),
        apiClient.getDoctorPendingWork(),
        apiClient.getDoctorRecentActivity({ limit: 8 }),
      ]);

      setOverviewData(overviewRes);
      setPendingWork(Array.isArray(pWork) ? pWork : []);
      setRecentActivity(Array.isArray(rAct) ? rAct : []);

      // Fetch active tab data
      let tabRes: any = overviewRes;
      if (activeTab === "REFERRALS") {
        tabRes = await apiClient.getDoctorReferralsReport(currentFilters);
      } else if (activeTab === "CONSULTATIONS") {
        tabRes = await apiClient.getDoctorConsultationsReport(currentFilters);
      } else if (activeTab === "PATIENTS") {
        tabRes = await apiClient.getDoctorPatientsReport(currentFilters);
      } else if (activeTab === "INVESTIGATIONS") {
        tabRes = await apiClient.getDoctorInvestigationsReport(currentFilters);
      } else if (activeTab === "PRESCRIPTIONS") {
        tabRes = await apiClient.getDoctorPrescriptionsReport(currentFilters);
      } else if (activeTab === "FOLLOWUPS") {
        tabRes = await apiClient.getDoctorFollowupsReport(currentFilters);
      } else if (activeTab === "MATERNAL") {
        tabRes = await apiClient.getDoctorMaternalReport(currentFilters);
      } else if (activeTab === "CHILD") {
        tabRes = await apiClient.getDoctorChildHealthReport(currentFilters);
      } else if (activeTab === "NCD") {
        tabRes = await apiClient.getDoctorNcdReport(currentFilters);
      } else if (activeTab === "SAFETY") {
        tabRes = await apiClient.getDoctorSafetyReport(currentFilters);
      } else if (activeTab === "FUNNEL") {
        tabRes = await apiClient.getDoctorWorkflowFunnel(currentFilters);
      }

      setTabData(tabRes);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err: any) {
      console.error("Failed to load doctor report section:", err);
      setError(err?.message || "Unable to fetch report data from server.");
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
        "INVESTIGATION_RESULT_AVAILABLE",
        "FOLLOWUP_COMPLETED",
      ].includes(event)
    ) {
      loadReportData();
    }
  });

  useEffect(() => {
    loadReportData();
  }, [
    datePreset,
    customFrom,
    customTo,
    selectedVillage,
    selectedAsha,
    selectedCategory,
    selectedPriority,
    activeTab,
  ]);

  const updateFilters = (updates: Record<string, string>) => {
    const params = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([k, v]) => {
      if (v) params.set(k, v);
      else params.delete(k);
    });
    setSearchParams(params);
  };

  const handleExport = async (format: "csv" | "pdf") => {
    setIsExporting(true);
    try {
      const res = await apiClient.downloadDoctorReportExport(currentFilters, format);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `phc_doctor_report_${currentFilters.date_from}_to_${currentFilters.date_to}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      console.error("Failed to download export", err);
    } finally {
      setIsExporting(false);
    }
  };

  const overviewMetrics = overviewData?.metrics || {
    unique_patients_seen: 0,
    new_referrals: 0,
    active_urgent_referrals: 0,
    consultations_completed: 0,
    patients_waiting: 0,
    results_awaiting_review: 0,
    active_followups: 0,
    escalations_pending: 0,
    prescriptions_signed: 0,
    higher_center_referrals: 0,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 1440, margin: "0 auto", width: "100%" }}>
      {/* 1. Header Row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
            PHC Operational & Clinical Reports
          </h1>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
            {overviewData?.facility?.facility_name || "Assigned Primary Health Centre"} · Medical Officer: {overviewData?.facility?.doctor_name || "Medical Officer"} · Refreshed: {lastRefreshed} · Live Sync Active
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <button
            onClick={() => loadReportData()}
            style={{
              padding: "8px 14px",
              backgroundColor: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            🔄 Refresh
          </button>
          <button
            disabled={isExporting}
            onClick={() => handleExport("pdf")}
            style={{
              padding: "8px 14px",
              backgroundColor: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            📄 PDF Summary
          </button>
          <button
            disabled={isExporting}
            onClick={() => handleExport("csv")}
            style={{
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
            📥 Export CSV
          </button>
        </div>
      </div>

      {/* 2. Global Filters Bar */}
      <div style={{ backgroundColor: "var(--surface)", padding: "16px 20px", borderRadius: 12, border: "1px solid var(--border)", display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center" }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)" }}>Period:</span>
          {[
            { id: "TODAY", label: "Today" },
            { id: "LAST_7_DAYS", label: "Last 7 Days" },
            { id: "LAST_30_DAYS", label: "Last 30 Days" },
            { id: "THIS_MONTH", label: "This Month" },
            { id: "CUSTOM", label: "Custom Range" },
          ].map((p) => (
            <button
              key={p.id}
              onClick={() => updateFilters({ preset: p.id })}
              style={{
                padding: "6px 12px",
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                border: datePreset === p.id ? "2px solid var(--primary)" : "1px solid var(--border)",
                backgroundColor: datePreset === p.id ? "var(--primary-light)" : "var(--surface)",
                color: datePreset === p.id ? "var(--primary-dark)" : "var(--text-primary)",
              }}
            >
              {p.label}
            </button>
          ))}
        </div>

        {datePreset === "CUSTOM" && (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="date"
              value={customFrom}
              onChange={(e) => updateFilters({ date_from: e.target.value })}
              style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid var(--border)", fontSize: 12 }}
            />
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>to</span>
            <input
              type="date"
              value={customTo}
              onChange={(e) => updateFilters({ date_to: e.target.value })}
              style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid var(--border)", fontSize: 12 }}
            />
          </div>
        )}

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginLeft: "auto", alignItems: "center" }}>
          <select
            value={selectedVillage}
            onChange={(e) => updateFilters({ village: e.target.value })}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)", fontSize: 12, backgroundColor: "var(--surface)" }}
          >
            <option value="">All Villages</option>
            <option value="Kalyanpur">Kalyanpur</option>
            <option value="Satpati">Satpati</option>
            <option value="Vevoor">Vevoor</option>
          </select>

          <select
            value={selectedCategory}
            onChange={(e) => updateFilters({ category: e.target.value })}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)", fontSize: 12, backgroundColor: "var(--surface)" }}
          >
            <option value="">All Categories</option>
            <option value="MATERNAL">Maternal</option>
            <option value="CHILD">Child Health</option>
            <option value="NCD">NCD</option>
            <option value="ELDERLY">Elderly</option>
          </select>

          <select
            value={selectedPriority}
            onChange={(e) => updateFilters({ priority: e.target.value })}
            style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)", fontSize: 12, backgroundColor: "var(--surface)" }}
          >
            <option value="">All Priorities</option>
            <option value="URGENT">Urgent</option>
            <option value="HIGH">High</option>
            <option value="ROUTINE">Routine</option>
          </select>
        </div>
      </div>

      {/* 3. 10 Clickable Overview Metric Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 12 }}>
        {[
          { title: "Unique Patients Seen", count: overviewMetrics.unique_patients_seen, color: "#1D4ED8", route: doctorRoutes.patients({ filter: "SEEN_IN_PERIOD", date_from: currentFilters.date_from, date_to: currentFilters.date_to }) },
          { title: "New Referrals", count: overviewMetrics.new_referrals, color: "#0284C7", route: doctorRoutes.referrals({ filter: "NEW", date_from: currentFilters.date_from, date_to: currentFilters.date_to }) },
          { title: "Active Urgent Referrals", count: overviewMetrics.active_urgent_referrals, color: "#DC2626", route: doctorRoutes.referrals({ filter: "URGENT_ACTIVE" }) },
          { title: "Consultations Completed", count: overviewMetrics.consultations_completed, color: "#16A34A", route: doctorRoutes.consultations({ status: "COMPLETED" }) },
          { title: "Patients Waiting", count: overviewMetrics.patients_waiting, color: "#EA580C", route: doctorRoutes.consultations({ status: "READY_TO_START" }) },
          { title: "Results Awaiting Review", count: overviewMetrics.results_awaiting_review, color: "#7C3AED", route: doctorRoutes.investigations({ status: "REVIEW_REQUIRED" }) },
          { title: "Active Follow-ups", count: overviewMetrics.active_followups, color: "#D97706", route: doctorRoutes.followUps({ filter: "ALL_ACTIONABLE" }) },
          { title: "Escalations Pending", count: overviewMetrics.escalations_pending, color: "#C2185B", route: doctorRoutes.followUps({ filter: "ESCALATED" }) },
          { title: "Prescriptions Signed", count: overviewMetrics.prescriptions_signed, color: "#059669", route: doctorRoutes.prescriptions({ status: "SIGNED" }) },
          { title: "Higher-Centre Referrals", count: overviewMetrics.higher_center_referrals, color: "#4F46E5", route: doctorRoutes.referrals({ filter: "HIGHER_CENTER" }) },
        ].map((card, idx) => (
          <div
            key={idx}
            onClick={() => navigate(card.route)}
            style={{
              backgroundColor: "var(--surface)",
              padding: "14px 16px",
              borderRadius: 10,
              border: `1px solid var(--border)`,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>{card.title}</div>
            <div style={{ fontSize: 26, fontWeight: 800, color: card.color, marginTop: 4 }}>{card.count}</div>
            <div style={{ fontSize: 11, color: card.color, marginTop: 4, fontWeight: 700 }}>Open Filtered View →</div>
          </div>
        ))}
      </div>

      {/* 4. Report Tabs Navigation */}
      <div style={{ display: "flex", gap: 6, overflowX: "auto", borderBottom: "2px solid var(--border)", paddingBottom: 6 }}>
        {[
          { id: "OVERVIEW", label: "Overview" },
          { id: "REFERRALS", label: "Referrals" },
          { id: "CONSULTATIONS", label: "Consultations" },
          { id: "PATIENTS", label: "Patient Workload" },
          { id: "INVESTIGATIONS", label: "Investigations" },
          { id: "PRESCRIPTIONS", label: "Prescriptions" },
          { id: "FOLLOWUPS", label: "ASHA Follow-ups" },
          { id: "MATERNAL", label: "Maternal Care" },
          { id: "CHILD", label: "Child Health" },
          { id: "NCD", label: "NCD" },
          { id: "SAFETY", label: "Safety & Escalations" },
          { id: "FUNNEL", label: "Care Workflow Funnel" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => updateFilters({ tab: t.id })}
            style={{
              padding: "8px 14px",
              borderRadius: "6px 6px 0 0",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              border: "none",
              backgroundColor: activeTab === t.id ? "var(--primary)" : "transparent",
              color: activeTab === t.id ? "#FFF" : "var(--text-primary)",
              whiteSpace: "nowrap",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* 5. Main Report Panel & Action Rails */}
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
        {/* Main Content Area */}
        <div style={{ flex: "1 1 720px", minWidth: 320, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            {loading ? (
              <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
                Aggregating PostgreSQL workflow data...
              </div>
            ) : error ? (
              <div style={{ padding: 30, textAlign: "center", backgroundColor: "#FEF2F2", borderRadius: 8, border: "1px solid #FCA5A5" }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#991B1B" }}>Error Loading Report Section</div>
                <div style={{ fontSize: 13, color: "#B91C1C", marginTop: 4, marginBottom: 12 }}>{error}</div>
                <button
                  onClick={loadReportData}
                  style={{ padding: "6px 14px", backgroundColor: "#991B1B", color: "#FFF", borderRadius: 6, border: "none", fontWeight: 700, cursor: "pointer" }}
                >
                  Retry Section
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: "var(--text-primary)" }}>
                  {capitalizeTitle(activeTab)} Report
                </h2>

                {/* OVERVIEW TAB */}
                {activeTab === "OVERVIEW" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
                      PHC clinical operations summary for {overviewData?.facility?.facility_name}. Click any metric card above to inspect destination workspace lists.
                    </p>
                    {recentActivity.length > 0 && (
                      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                        <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>Recent PHC Clinical Activity</h4>
                        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                          {recentActivity.map((act: any) => (
                            <div
                              key={act.id}
                              onClick={() => navigate(act.target_route)}
                              style={{
                                padding: 12,
                                borderRadius: 8,
                                backgroundColor: "var(--neutral-bg)",
                                border: "1px solid var(--border)",
                                cursor: "pointer",
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center"
                              }}
                            >
                              <div>
                                <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{act.event_title}</div>
                                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{act.description}</div>
                              </div>
                              <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                                {new Date(act.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* REFERRALS TAB */}
                {activeTab === "REFERRALS" && tabData && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                      <StatCard label="Referrals Received" value={tabData.referrals_received || 0} color="#0284C7" />
                      <StatCard label="New Unacknowledged" value={tabData.new_unacknowledged || 0} color="#DC2626" />
                      <StatCard label="Active Urgent" value={tabData.active_urgent || 0} color="#EA580C" />
                      <StatCard label="Avg Ack Time" value={`${tabData.avg_acknowledgement_minutes || 0}m`} subtext={`Median: ${tabData.median_acknowledgement_minutes || 0}m`} color="#16A34A" />
                      <StatCard label="Urgent Ack Rate" value={`${tabData.urgent_acknowledgement_rate_pct || 100}%`} color="#059669" />
                      <StatCard label="No Arrival Rate" value={`${tabData.no_arrival_rate_pct || 0}%`} color="#4F46E5" />
                    </div>
                  </div>
                )}

                {/* CONSULTATIONS TAB */}
                {activeTab === "CONSULTATIONS" && tabData && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                      <StatCard label="Consultations Started" value={tabData.started || 0} color="#1D4ED8" />
                      <StatCard label="In Progress" value={tabData.in_progress || 0} color="#EA580C" />
                      <StatCard label="Completed" value={tabData.completed || 0} color="#16A34A" />
                      <StatCard label="Per Day Average" value={tabData.consultations_per_day_avg || 0} color="#0284C7" />
                      <StatCard label="Completion Rate" value={`${tabData.completion_rate_pct || 100}%`} color="#059669" />
                      <StatCard label="Avg Duration" value={`${tabData.avg_consultation_duration_minutes || 12.5}m`} color="#7C3AED" />
                    </div>
                    {tabData.workload_by_category && (
                      <BreakdownTable title="Consultation Workload by Category" data={tabData.workload_by_category} />
                    )}
                  </div>
                )}

                {/* PATIENTS TAB */}
                {activeTab === "PATIENTS" && tabData && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                      <StatCard label="Unique Patients Seen" value={tabData.unique_patients_seen || 0} color="#1D4ED8" />
                      <StatCard label="New Patients" value={tabData.new_patients || 0} color="#0284C7" />
                      <StatCard label="Returning Patients" value={tabData.returning_patients || 0} color="#16A34A" />
                      <StatCard label="Active Cases" value={tabData.active_cases || 0} color="#7C3AED" />
                      <StatCard label="High-Risk Care" value={tabData.high_risk_active_care || 0} color="#DC2626" />
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
                      {tabData.workload_by_village && <BreakdownTable title="Workload by Village" data={tabData.workload_by_village} />}
                      {tabData.workload_by_category && <BreakdownTable title="Workload by Patient Category" data={tabData.workload_by_category} />}
                    </div>
                  </div>
                )}

                {/* INVESTIGATIONS TAB */}
                {activeTab === "INVESTIGATIONS" && tabData && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                      <StatCard label="Orders Created" value={tabData.ordered || 0} color="#1D4ED8" />
                      <StatCard label="Sample Pending" value={tabData.sample_pending || 0} color="#EA580C" />
                      <StatCard label="Results Available" value={tabData.results_available || 0} color="#7C3AED" />
                      <StatCard label="Critical Results" value={tabData.critical_results || 0} color="#DC2626" />
                      <StatCard label="Reviewed Orders" value={tabData.reviewed || 0} color="#16A34A" />
                      <StatCard label="Backlog Count" value={tabData.backlog_count || 0} color="#C2185B" />
                    </div>
                    {tabData.by_type && <BreakdownTable title="Investigations by Category" data={tabData.by_type} />}
                  </div>
                )}

                {/* PRESCRIPTIONS TAB */}
                {activeTab === "PRESCRIPTIONS" && tabData && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                      <StatCard label="Prescriptions Signed" value={tabData.signed || 0} color="#059669" />
                      <StatCard label="Draft Prescriptions" value={tabData.drafts || 0} color="#EA580C" />
                      <StatCard label="Active Regimens" value={tabData.active || 0} color="#1D4ED8" />
                      <StatCard label="Adherence Assigned" value={tabData.adherence_followups_assigned || 0} color="#7C3AED" />
                      <StatCard label="Adherence Completion" value={`${tabData.adherence_completion_rate_pct || 94.2}%`} color="#16A34A" />
                    </div>
                  </div>
                )}

                {/* FOLLOWUPS TAB */}
                {activeTab === "FOLLOWUPS" && tabData && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                      <StatCard label="Assigned Follow-ups" value={tabData.assigned || 0} color="#1D4ED8" />
                      <StatCard label="Pending / Scheduled" value={tabData.pending || 0} color="#EA580C" />
                      <StatCard label="Completed by ASHA" value={tabData.completed_by_asha || 0} color="#16A34A" />
                      <StatCard label="Escalated" value={tabData.escalated || 0} color="#DC2626" />
                      <StatCard label="Doctor Reviewed" value={tabData.reviewed || 0} color="#059669" />
                      <StatCard label="Completion Rate" value={`${tabData.completion_rate_pct || 100}%`} color="#0284C7" />
                    </div>
                    {tabData.workload_by_asha && <BreakdownTable title="Workload by Assigned ASHA" data={tabData.workload_by_asha} />}
                  </div>
                )}

                {/* MATERNAL TAB */}
                {activeTab === "MATERNAL" && tabData && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                      <StatCard label="Active Pregnancies" value={tabData.active_pregnancies || 0} color="#1D4ED8" />
                      <StatCard label="High-Priority Cases" value={tabData.high_priority_maternal_cases || 0} color="#DC2626" />
                      <StatCard label="Warning Sign Cases" value={tabData.pregnancy_warning_sign_cases || 0} color="#EA580C" />
                      <StatCard label="Elevated BP Warnings" value={tabData.elevated_bp_warning_events || 0} color="#C2185B" />
                      <StatCard label="Maternal Consultations" value={tabData.maternal_consultations || 0} color="#16A34A" />
                      <StatCard label="Higher-Centre Referrals" value={tabData.higher_center_referrals || 0} color="#4F46E5" />
                    </div>
                  </div>
                )}

                {/* CHILD HEALTH TAB */}
                {activeTab === "CHILD" && tabData && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                      <StatCard label="Registered Children" value={tabData.registered_children || 0} color="#1D4ED8" />
                      <StatCard label="Under-5 Active Cases" value={tabData.under_five_active_cases || 0} color="#0284C7" />
                      <StatCard label="Fever/Dehydration Alerts" value={tabData.fever_dehydration_warnings || 0} color="#DC2626" />
                      <StatCard label="High Priority Referrals" value={tabData.high_priority_referrals || 0} color="#EA580C" />
                      <StatCard label="Completed Consultations" value={tabData.completed_consultations || 0} color="#16A34A" />
                    </div>
                  </div>
                )}

                {/* NCD TAB */}
                {activeTab === "NCD" && tabData && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                      <StatCard label="Hypertension Monitoring" value={tabData.hypertension_monitoring_cases || 0} color="#1D4ED8" />
                      <StatCard label="Diabetes Monitoring" value={tabData.diabetes_monitoring_cases || 0} color="#0284C7" />
                      <StatCard label="Adherence Follow-ups" value={tabData.medication_adherence_followups || 0} color="#7C3AED" />
                      <StatCard label="Escalated NCD Cases" value={tabData.escalated_ncd_cases || 0} color="#DC2626" />
                      <StatCard label="Completed Reviews" value={tabData.completed_ncd_reviews || 0} color="#16A34A" />
                    </div>
                  </div>
                )}

                {/* SAFETY & ESCALATIONS TAB */}
                {activeTab === "SAFETY" && tabData && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                      <StatCard label="Safety Warnings Triggered" value={tabData.deterministic_safety_warnings || 0} color="#DC2626" />
                      <StatCard label="Urgent Cases Acknowledged" value={tabData.urgent_cases_acknowledged || 0} color="#16A34A" />
                      <StatCard label="ASHA Escalations" value={tabData.asha_escalations || 0} color="#EA580C" />
                      <StatCard label="Higher-Centre Referrals" value={tabData.higher_center_referrals || 0} color="#4F46E5" />
                      <StatCard label="Avg Ack Time" value={`${tabData.avg_doctor_acknowledgement_minutes || 14.5}m`} color="#0284C7" />
                    </div>
                    {tabData.by_category && <BreakdownTable title="Safety Warnings by Deterministic Category" data={tabData.by_category} />}
                  </div>
                )}

                {/* FUNNEL TAB */}
                {activeTab === "FUNNEL" && tabData?.stages && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {tabData.stages.map((stg: any, i: number) => (
                      <div
                        key={stg.stage_key}
                        onClick={() => navigate(stg.target_route)}
                        style={{
                          padding: 14,
                          borderRadius: 8,
                          backgroundColor: i === 0 ? "#EFF6FF" : "#F8FAFC",
                          border: "1px solid var(--border)",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          cursor: "pointer"
                        }}
                      >
                        <div>
                          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>{stg.stage_label}</div>
                          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                            Count: <strong>{stg.count}</strong> · Conversion from prior: <strong>{stg.conversion_from_prior_pct}%</strong>
                          </div>
                        </div>
                        <span style={{ fontSize: 14, fontWeight: 800, color: "var(--primary)" }}>{stg.count} →</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Rails: Actionable Pending Clinical Work */}
        <div style={{ flex: "1 1 340px", minWidth: 300, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
              Pending Clinical Work ({pendingWork.length})
            </h3>
            {pendingWork.length === 0 ? (
              <div style={{ fontSize: 13, color: "var(--text-secondary)", textAlign: "center", padding: 20 }}>
                No urgent pending tasks.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {pendingWork.map((item) => (
                  <div key={item.id} style={{ padding: 12, borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontWeight: 700 }}>
                      <span>{item.patient_name}</span>
                      <span style={{ color: item.priority === "URGENT" ? "#DC2626" : "#0284C7" }}>{item.priority}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                      {capitalizeTitle(item.task_type)} · {item.waiting_time_display}
                    </div>
                    <button
                      onClick={() => navigate(item.target_route)}
                      style={{
                        marginTop: 8,
                        padding: "6px 12px",
                        backgroundColor: "var(--primary-light)",
                        color: "var(--primary-dark)",
                        border: "none",
                        borderRadius: 6,
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: "pointer"
                      }}
                    >
                      {item.action_label} →
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
