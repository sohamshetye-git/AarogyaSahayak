import React, { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { doctorRoutes } from "./doctorRoutes";
import { PriorityBadge } from "../../components/StatusBadge";
import { SearchIcon, ActivityIcon, ChevronRightIcon, WarningIcon } from "../../components/Icons";


export function DoctorPatientsScreen() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // URL query params binding
  const currentFilter = searchParams.get("filter") || "ALL";
  const currentCategory = searchParams.get("category") || "";
  const currentSearch = searchParams.get("search") || "";
  const currentSort = searchParams.get("sort") || "priority_first";
  const currentPage = parseInt(searchParams.get("page") || "1", 10);

  const [summary, setSummary] = useState<any>(null);
  const [patientsData, setPatientsData] = useState<any>({ items: [], total: 0, total_pages: 1 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastSynced, setLastSynced] = useState<string>(new Date().toLocaleTimeString());

  // Search input local state for debouncing / typing responsiveness
  const [searchInput, setSearchInput] = useState(currentSearch);

  const updateQueryParams = (updates: Record<string, string | number | undefined>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([k, v]) => {
      if (v === undefined || v === "" || v === null) {
        newParams.delete(k);
      } else {
        newParams.set(k, String(v));
      }
    });
    setSearchParams(newParams);
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, pRes] = await Promise.all([
        apiClient.getDoctorPatientsSummary(),
        apiClient.getDoctorPatients({
          filter: currentFilter,
          category: currentCategory || undefined,
          search: currentSearch || undefined,
          sort_by: currentSort,
          page: currentPage,
          page_size: 15,
        }),
      ]);

      setSummary(sumRes || null);
      if (pRes) {
        if (Array.isArray(pRes)) {
          setPatientsData({ items: pRes, total: pRes.length, total_pages: 1 });
        } else {
          setPatientsData(pRes);
        }
      }
      setLastSynced(new Date().toLocaleTimeString());
    } catch (err: any) {
      console.error("Failed to load doctor patient workspace", err);
      setError(err?.message || "Failed to fetch PHC patient directory from server.");
    } finally {
      setLoading(false);
    }
  }, [currentFilter, currentCategory, currentSearch, currentSort, currentPage]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Keep search input synced if URL param changes externally
  useEffect(() => {
    setSearchInput(currentSearch);
  }, [currentSearch]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateQueryParams({ search: searchInput, page: 1 });
  };

  const handleFilterClick = (filterCode: string) => {
    updateQueryParams({ filter: filterCode, page: 1 });
  };

  const handleCategoryClick = (catCode: string) => {
    updateQueryParams({ category: catCode === currentCategory ? "" : catCode, page: 1 });
  };

  const metricCards = [
    { key: "ALL", label: "Total PHC Patients", value: summary?.total_phc_patients ?? 0, color: "#1D4ED8", bg: "#EFF6FF", border: "#BFDBFE" },
    { key: "ACTIVE_CASE", label: "Active Cases", value: summary?.active_cases ?? 0, color: "#0284C7", bg: "#F0F9FF", border: "#BAE6FD" },
    { key: "HIGH_RISK", label: "High-Risk Active Care", value: summary?.high_risk_active_care ?? 0, color: "#DC2626", bg: "#FEF2F2", border: "#FCA5A5" },
    { key: "WAITING_AT_PHC", label: "Patients Waiting at PHC", value: summary?.patients_waiting_at_phc ?? 0, color: "#0D9488", bg: "#F0FDFA", border: "#99F6E4" },
    { key: "FOLLOWUP_REQUIRED", label: "Follow-ups Required", value: summary?.followups_required ?? 0, color: "#D97706", bg: "#FFFBEB", border: "#FDE68A" },
    { key: "RESULT_READY", label: "Results Ready", value: summary?.results_ready ?? 0, color: "#7C3AED", bg: "#F5F3FF", border: "#DDD6FE" },
    { key: "CONSULTED_TODAY", label: "Consultations Today", value: summary?.consultations_today ?? 0, color: "#16A34A", bg: "#F0FDF4", border: "#BBF7D0" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 1440, margin: "0 auto", width: "100%", padding: "16px 20px 40px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
            Patients Directory
          </h1>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
            Kalyanpur Primary Health Centre · Authorized Patients: <strong>{patientsData.total || 0}</strong> · Last synced: {lastSynced}
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
            🔄 Refresh Directory
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(175px, 1fr))", gap: 12 }}>
        {metricCards.map((card) => {
          const isSelected = currentFilter === card.key;
          return (
            <div
              key={card.key}
              onClick={() => handleFilterClick(card.key)}
              style={{
                backgroundColor: isSelected ? card.bg : "var(--surface)",
                padding: "14px 16px",
                borderRadius: 10,
                border: isSelected ? `2px solid ${card.color}` : `1px solid ${card.border}`,
                cursor: "pointer",
                transition: "all 0.15s ease",
                boxShadow: isSelected ? "0 2px 6px rgba(0,0,0,0.06)" : "none",
              }}
            >
              <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>{card.label}</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: card.color, marginTop: 4 }}>
                {loading ? "..." : card.value}
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Filter & Search Control Panel */}
      <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 14 }}>
        {/* Search Bar & Sort selector */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
          <form onSubmit={handleSearchSubmit} style={{ flex: "1 1 320px", display: "flex", gap: 8 }}>
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                gap: 8,
                backgroundColor: "var(--neutral-bg)",
                padding: "0 12px",
                height: 40,
                borderRadius: 8,
                border: "1px solid var(--border)",
              }}
            >
              <SearchIcon size={16} color="var(--text-secondary)" />
              <input
                type="text"
                placeholder="Search patient name, reference, case, village, phone, ASHA..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                style={{ border: "none", outline: "none", width: "100%", fontSize: 13, backgroundColor: "transparent" }}
              />
            </div>
            <button
              type="submit"
              style={{
                padding: "0 16px",
                height: 40,
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

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>Sort by:</span>
            <select
              value={currentSort}
              onChange={(e) => updateQueryParams({ sort: e.target.value, page: 1 })}
              style={{
                padding: "8px 12px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                backgroundColor: "var(--surface)",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              <option value="priority_first">Priority First</option>
              <option value="latest_activity">Latest Activity</option>
              <option value="name">Patient Name</option>
            </select>
          </div>
        </div>

        {/* Category Pills */}
        <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 4 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", alignSelf: "center", marginRight: 4 }}>
            Category:
          </span>
          {[
            { id: "MATERNAL", label: "🤰 Maternal" },
            { id: "CHILD", label: "👶 Child" },
            { id: "NCD", label: "🩺 NCD" },
            { id: "ELDERLY", label: "👵 Elderly" },
            { id: "GENERAL", label: "🏥 General" },
          ].map((cat) => {
            const isActive = currentCategory === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => handleCategoryClick(cat.id)}
                style={{
                  padding: "4px 12px",
                  borderRadius: 16,
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                  border: isActive ? "2px solid var(--primary)" : "1px solid var(--border)",
                  backgroundColor: isActive ? "var(--primary-light)" : "var(--neutral-bg)",
                  color: isActive ? "var(--primary-dark)" : "var(--text-primary)",
                  whiteSpace: "nowrap",
                }}
              >
                {cat.label}
              </button>
            );
          })}
          {currentCategory && (
            <button
              onClick={() => updateQueryParams({ category: undefined, page: 1 })}
              style={{ padding: "4px 8px", fontSize: 11, color: "#DC2626", background: "none", border: "none", cursor: "pointer", fontWeight: 700 }}
            >
              Clear Category ✕
            </button>
          )}
        </div>
      </div>

      {/* Content Feed */}
      {error ? (
        <div style={{ padding: 40, textAlign: "center", backgroundColor: "#FEF2F2", border: "1.5px solid #FCA5A5", borderRadius: 12 }}>
          <WarningIcon size={36} color="#DC2626" />
          <h3 style={{ margin: "12px 0 6px", color: "#991B1B" }}>Error Loading Patient Directory</h3>
          <p style={{ margin: 0, color: "#7F1D1D", fontSize: 13, marginBottom: 16 }}>{error}</p>
          <button
            onClick={() => loadData()}
            style={{ padding: "8px 16px", backgroundColor: "#DC2626", color: "#FFF", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}
          >
            Retry Request
          </button>
        </div>
      ) : loading ? (
        <div style={{ padding: 60, textAlign: "center", color: "var(--text-secondary)" }}>
          Loading PHC patient directory...
        </div>
      ) : patientsData.items.length === 0 ? (
        <div style={{ padding: 60, textAlign: "center", backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
          <h3 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>No Patients Found</h3>
          <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: 14 }}>
            {currentSearch || currentFilter !== "ALL" || currentCategory
              ? "No registered patients match the selected filter criteria."
              : "No patients are currently assigned to this PHC."}
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {patientsData.items.map((patient: any) => {
            const careStatus = patient.current_care_status || "STABLE";

            // Visual State Colors
            let borderColor = "var(--border)";
            let bgColor = "var(--surface)";

            if (careStatus === "HIGH_RISK") {
              borderColor = "#DC2626";
              bgColor = "#FEF2F2";
            } else if (careStatus === "WAITING_AT_PHC") {
              borderColor = "#0D9488";
              bgColor = "#F0FDFA";
            } else if (careStatus === "CONSULTATION_IN_PROGRESS") {
              borderColor = "#7C3AED";
              bgColor = "#F5F3FF";
            } else if (careStatus === "ACTIVE_CASE") {
              borderColor = "#0284C7";
              bgColor = "#F0F9FF";
            }

            return (
              <div
                key={patient.citizen_id || patient.id}
                style={{
                  padding: 18,
                  borderRadius: 12,
                  border: `1.5px solid ${borderColor}`,
                  backgroundColor: bgColor,
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
                }}
              >
                {/* Header Row */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8 }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                      <span style={{ fontSize: 17, fontWeight: 800, color: "var(--text-primary)" }}>
                        {patient.display_name}
                      </span>
                      <span style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 600 }}>
                        {patient.age_estimate}y · {patient.sex} · {patient.village_name}
                      </span>

                      {patient.phone && (
                        <span style={{ fontSize: 13, color: "#0369A1", fontWeight: 700 }}>
                          📞 {patient.phone}
                        </span>
                      )}

                      <span
                        style={{
                          padding: "2px 8px",
                          borderRadius: 12,
                          fontSize: 11,
                          fontWeight: 800,
                          backgroundColor:
                            patient.patient_category === "MATERNAL"
                              ? "#FCE4EC"
                              : patient.patient_category === "CHILD"
                              ? "#E0F2FE"
                              : patient.patient_category === "NCD"
                              ? "#FEF3C7"
                              : "#F3F4F6",
                          color:
                            patient.patient_category === "MATERNAL"
                              ? "#C2185B"
                              : patient.patient_category === "CHILD"
                              ? "#0369A1"
                              : patient.patient_category === "NCD"
                              ? "#92400E"
                              : "#374151",
                        }}
                      >
                        {patient.patient_category === "MATERNAL"
                          ? `🤰 Maternal (${patient.gestational_weeks || 14}w)`
                          : patient.patient_category}
                      </span>
                    </div>

                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, display: "flex", gap: 12, flexWrap: "wrap" }}>
                      <span>Ref: <strong>{patient.patient_reference}</strong></span>
                      <span>Assigned ASHA: <strong>{patient.assigned_asha_name}</strong></span>
                      {patient.active_case_reference && (
                        <span>Active Case: <strong>{patient.active_case_reference}</strong></span>
                      )}
                    </div>
                  </div>

                  <div>
                    <span
                      style={{
                        padding: "4px 10px",
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 800,
                        backgroundColor:
                          careStatus === "WAITING_AT_PHC"
                            ? "#CCFBF1"
                            : careStatus === "CONSULTATION_IN_PROGRESS"
                            ? "#F3E8FF"
                            : careStatus === "HIGH_RISK"
                            ? "#FEE2E2"
                            : "#E0F2FE",
                        color:
                          careStatus === "WAITING_AT_PHC"
                            ? "#0F766E"
                            : careStatus === "CONSULTATION_IN_PROGRESS"
                            ? "#6B21A8"
                            : careStatus === "HIGH_RISK"
                            ? "#B91C1C"
                            : "#0369A1",
                      }}
                    >
                      {careStatus.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>

                {/* Middle Clinical Context */}
                <div style={{ padding: 12, backgroundColor: "var(--surface)", borderRadius: 8, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 6 }}>
                  <div style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 700 }}>
                    Current Concern: {patient.current_concern}
                  </div>
                  {patient.latest_measurements && (
                    <div style={{ fontSize: 12, color: "var(--primary-dark)", fontWeight: 600 }}>
                      Latest Vitals: {patient.latest_measurements}
                    </div>
                  )}
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", fontStyle: "italic" }}>
                    Next Action: <strong>{patient.next_required_action}</strong>
                  </div>
                </div>

                {/* Actions */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                    Last activity: {patient.last_clinical_activity ? new Date(patient.last_clinical_activity).toLocaleDateString() : "Not recorded"}
                  </div>

                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <button
                      onClick={() => navigate(doctorRoutes.patientRecord(patient.citizen_id || patient.id))}
                      style={{
                        padding: "6px 14px",
                        backgroundColor: "var(--surface)",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        fontSize: 12,
                        fontWeight: 700,
                        color: "var(--primary)",
                        cursor: "pointer",
                      }}
                    >
                      Open Patient Record →
                    </button>

                    {patient.active_case_id && (
                      <button
                        onClick={() => navigate(doctorRoutes.caseTimeline(patient.active_case_id))}
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
                    )}

                    {careStatus === "WAITING_AT_PHC" && (
                      <button
                        onClick={() => navigate(`/doctor/consultations?caseId=${patient.active_case_id}`)}
                        style={{
                          padding: "6px 14px",
                          backgroundColor: "#16A34A",
                          color: "#FFF",
                          border: "none",
                          borderRadius: 6,
                          fontSize: 12,
                          fontWeight: 800,
                          cursor: "pointer",
                        }}
                      >
                        ▶ Start Consultation
                      </button>
                    )}

                    {careStatus === "CONSULTATION_IN_PROGRESS" && (
                      <button
                        onClick={() => navigate(`/doctor/consultations?caseId=${patient.active_case_id}`)}
                        style={{
                          padding: "6px 14px",
                          backgroundColor: "#7C3AED",
                          color: "#FFF",
                          border: "none",
                          borderRadius: 6,
                          fontSize: 12,
                          fontWeight: 800,
                          cursor: "pointer",
                        }}
                      >
                        Resume Consultation
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Footer */}
      {patientsData.total_pages > 1 && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            Page {patientsData.page} of {patientsData.total_pages} ({patientsData.total} total patients)
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              disabled={currentPage <= 1}
              onClick={() => updateQueryParams({ page: currentPage - 1 })}
              style={{
                padding: "6px 12px",
                borderRadius: 6,
                border: "1px solid var(--border)",
                backgroundColor: "var(--surface)",
                fontSize: 12,
                fontWeight: 600,
                cursor: currentPage <= 1 ? "not-allowed" : "pointer",
              }}
            >
              ← Previous
            </button>
            <button
              disabled={currentPage >= patientsData.total_pages}
              onClick={() => updateQueryParams({ page: currentPage + 1 })}
              style={{
                padding: "6px 12px",
                borderRadius: 6,
                border: "1px solid var(--border)",
                backgroundColor: "var(--surface)",
                fontSize: 12,
                fontWeight: 600,
                cursor: currentPage >= patientsData.total_pages ? "not-allowed" : "pointer",
              }}
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
