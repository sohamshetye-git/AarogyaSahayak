import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { doctorRoutes } from "./doctorRoutes";

export function DoctorPrescriptionsScreen() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const currentStatus = searchParams.get("status") || "ALL";
  const [searchQuery, setSearchQuery] = useState(searchParams.get("search") || "");
  const [sortBy, setSortBy] = useState(searchParams.get("sort_by") || "newest");

  const [summary, setSummary] = useState<any>(null);
  const [prescriptions, setPrescriptions] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    try {
      const res = await apiClient.getDoctorPrescriptionsSummary();
      setSummary(res);
    } catch (err: any) {
      console.error("Failed to load prescription summary", err);
    }
  };

  const fetchPrescriptions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = {};
      if (currentStatus !== "ALL") params.status = currentStatus;
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (sortBy) params.sort_by = sortBy;

      const res = await apiClient.getDoctorPrescriptions(params);
      setPrescriptions(res);
    } catch (err: any) {
      console.error("Failed to load prescriptions list", err);
      setError(err?.message || "Failed to load prescriptions list.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  useEffect(() => {
    fetchPrescriptions();
  }, [currentStatus, searchQuery, sortBy]);

  const handleStatusFilterChange = (statusKey: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (statusKey === "ALL") {
      newParams.delete("status");
    } else {
      newParams.set("status", statusKey);
    }
    setSearchParams(newParams);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "DRAFT":
        return { bg: "#F1F5F9", color: "#475569", label: "Draft" };
      case "READY_FOR_REVIEW":
        return { bg: "#EFF6FF", color: "#1D4ED8", label: "Awaiting Signature" };
      case "SIGNED":
      case "ACTIVE":
        return { bg: "#ECFDF5", color: "#047857", label: "Signed & Active" };
      case "AMENDED":
        return { bg: "#F3E8FF", color: "#7E22CE", label: "Amended" };
      case "PARTIALLY_STOPPED":
        return { bg: "#FFF7ED", color: "#C2410C", label: "Partially Stopped" };
      case "STOPPED":
        return { bg: "#FEF2F2", color: "#DC2626", label: "Stopped" };
      case "CANCELLED":
      case "VOIDED":
        return { bg: "#FEF2F2", color: "#991B1B", label: "Cancelled / Voided" };
      case "COMPLETED":
        return { bg: "#F8FAFC", color: "#64748B", label: "Completed" };
      default:
        return { bg: "#F1F5F9", color: "#475569", label: status };
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: "0 auto", fontFamily: "Inter, sans-serif" }}>
      {/* Workspace Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0, color: "#0F172A" }}>
            💊 Doctor Prescription Workspace
          </h1>
          <div style={{ fontSize: 13, color: "#64748B", marginTop: 4 }}>
            {summary?.phc_name || "Kalyanpur Primary Health Centre"} · Last Synced:{" "}
            {summary?.last_synchronized_at ? new Date(summary.last_synchronized_at).toLocaleTimeString() : "Just now"}
          </div>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <button
            onClick={() => {
              fetchSummary();
              fetchPrescriptions();
            }}
            style={{
              padding: "8px 16px",
              borderRadius: 6,
              border: "1px solid #CBD5E1",
              backgroundColor: "#FFFFFF",
              cursor: "pointer",
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            🔄 Refresh
          </button>
          <button
            onClick={() => navigate(doctorRoutes.consultations())}
            style={{
              padding: "8px 16px",
              borderRadius: 6,
              border: "none",
              backgroundColor: "#2563EB",
              color: "#FFFFFF",
              cursor: "pointer",
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            + New Prescription (Active Consultation)
          </button>
        </div>
      </div>

      {/* Dynamic Clickable Metric Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14, marginBottom: 24 }}>
        {[
          { key: "DRAFT", label: "Drafts", count: summary?.drafts_count ?? 0, color: "#64748B", bg: "#F8FAFC" },
          { key: "READY_FOR_REVIEW", label: "Awaiting Signature", count: summary?.awaiting_signature_count ?? 0, color: "#2563EB", bg: "#EFF6FF" },
          { key: "ACTIVE", label: "Signed & Active", count: summary?.active_count ?? 0, color: "#166534", bg: "#F0FDF4" },
          { key: "ENDING_SOON", label: "Ending Soon", count: summary?.ending_soon_count ?? 0, color: "#C2410C", bg: "#FFF7ED" },
          { key: "AMENDED", label: "Amended", count: summary?.amended_count ?? 0, color: "#7E22CE", bg: "#F3E8FF" },
          { key: "STOPPED", label: "Stopped / Cancelled", count: summary?.stopped_cancelled_count ?? 0, color: "#DC2626", bg: "#FEF2F2" },
        ].map((card) => {
          const isSelected = currentStatus === card.key;
          return (
            <div
              key={card.key}
              onClick={() => handleStatusFilterChange(card.key)}
              style={{
                padding: 16,
                borderRadius: 12,
                backgroundColor: card.bg,
                border: isSelected ? `2px solid ${card.color}` : "1px solid #E2E8F0",
                cursor: "pointer",
                transition: "all 150ms ease",
                boxShadow: isSelected ? "0 4px 12px rgba(0,0,0,0.05)" : "none",
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 600, color: "#475569" }}>{card.label}</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: card.color, marginTop: 4 }}>{card.count}</div>
            </div>
          );
        })}
      </div>

      {/* Toolbar: Search, Filters & Sorting */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          alignItems: "center",
          backgroundColor: "#FFFFFF",
          padding: 16,
          borderRadius: 12,
          border: "1px solid #E2E8F0",
          marginBottom: 20,
        }}
      >
        <div style={{ flex: 1, minWidth: 260 }}>
          <input
            type="text"
            placeholder="Search patient, prescription reference, medicine, village, ASHA..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: "100%",
              padding: "10px 14px",
              borderRadius: 8,
              border: "1px solid #CBD5E1",
              fontSize: 14,
            }}
          />
        </div>

        <select
          value={currentStatus}
          onChange={(e) => handleStatusFilterChange(e.target.value)}
          style={{
            padding: "10px 14px",
            borderRadius: 8,
            border: "1px solid #CBD5E1",
            fontSize: 14,
            fontWeight: 600,
            backgroundColor: "#F8FAFC",
          }}
        >
          <option value="ALL">All Statuses</option>
          <option value="DRAFT">Drafts</option>
          <option value="READY_FOR_REVIEW">Ready for Review</option>
          <option value="SIGNED">Signed</option>
          <option value="ACTIVE">Active</option>
          <option value="ENDING_SOON">Ending Soon</option>
          <option value="AMENDED">Amended</option>
          <option value="PARTIALLY_STOPPED">Partially Stopped</option>
          <option value="STOPPED">Stopped</option>
          <option value="CANCELLED">Cancelled</option>
        </select>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          style={{
            padding: "10px 14px",
            borderRadius: 8,
            border: "1px solid #CBD5E1",
            fontSize: 14,
            backgroundColor: "#F8FAFC",
          }}
        >
          <option value="newest">Sort: Newest First</option>
          <option value="oldest">Sort: Oldest First</option>
          <option value="patient">Sort: Patient Name</option>
        </select>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#64748B" }}>Loading prescriptions...</div>
      ) : error ? (
        <div
          style={{
            padding: 20,
            borderRadius: 8,
            backgroundColor: "#FEF2F2",
            border: "1px solid #FCA5A5",
            color: "#B91C1C",
          }}
        >
          <strong>Error loading prescriptions:</strong> {error}
        </div>
      ) : prescriptions.length === 0 ? (
        <div
          style={{
            padding: 40,
            textAlign: "center",
            backgroundColor: "#FFFFFF",
            borderRadius: 12,
            border: "1px solid #E2E8F0",
            color: "#64748B",
          }}
        >
          {currentStatus !== "ALL" || searchQuery
            ? "No prescriptions match these filters."
            : "No prescriptions are available for this PHC."}
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(420px, 1fr))", gap: 16 }}>
          {prescriptions.map((rx) => {
            const badge = getStatusBadge(rx.status);
            return (
              <div
                key={rx.id}
                style={{
                  backgroundColor: "#FFFFFF",
                  borderRadius: 12,
                  border: "1px solid #E2E8F0",
                  padding: 18,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.03)",
                }}
              >
                <div>
                  {/* Top Bar: Patient & Status Badge */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                    <div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: "#0F172A" }}>
                        {rx.patient_name} ({rx.patient_age ? `${rx.patient_age} yrs, ` : ""}{rx.patient_gender || "Gen"})
                      </div>
                      <div style={{ fontSize: 12, color: "#64748B" }}>
                        Village: {rx.patient_village} · Category: <span style={{ fontWeight: 600, color: "#2563EB" }}>{rx.patient_category}</span>
                      </div>
                    </div>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        padding: "4px 10px",
                        borderRadius: 12,
                        backgroundColor: badge.bg,
                        color: badge.color,
                      }}
                    >
                      {badge.label}
                    </span>
                  </div>

                  {/* Ref Metadata */}
                  <div style={{ fontSize: 12, color: "#475569", marginBottom: 12, backgroundColor: "#F8FAFC", padding: 8, borderRadius: 6 }}>
                    <strong>Ref:</strong> {rx.reference} | <strong>Prescriber:</strong> {rx.prescriber_doctor_name} | <strong>Ver:</strong> v{rx.version_number}
                  </div>

                  {/* Medicines Summary */}
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 4 }}>
                      Medications ({rx.items.length}):
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      {rx.items.map((it: any) => (
                        <div key={it.id} style={{ fontSize: 13, color: "#1E293B" }}>
                          • <strong>{it.generic_name_snapshot}</strong> {it.strength ? `(${it.strength})` : ""} - {it.dose} {it.frequency} ({it.duration_value} {it.duration_unit})
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Warnings Indicator */}
                  {rx.safety_checks && rx.safety_checks.length > 0 && (
                    <div style={{ fontSize: 11, color: "#C2410C", backgroundColor: "#FFF7ED", padding: 6, borderRadius: 6, marginBottom: 12 }}>
                      ⚠️ {rx.safety_checks.length} safety review check(s) flagged
                    </div>
                  )}
                </div>

                {/* Status-specific action buttons */}
                <div style={{ display: "flex", gap: 8, borderTop: "1px solid #F1F5F9", paddingTop: 12 }}>
                  <button
                    onClick={() => navigate(doctorRoutes.prescriptionDetail(rx.id))}
                    style={{
                      flex: 1,
                      padding: "8px",
                      borderRadius: 6,
                      border: "1px solid #CBD5E1",
                      backgroundColor: "#FFFFFF",
                      cursor: "pointer",
                      fontWeight: 600,
                      fontSize: 12,
                      color: "#334155",
                    }}
                  >
                    View Details
                  </button>
                  {rx.status === "DRAFT" && (
                    <button
                      onClick={() => navigate(doctorRoutes.prescriptionDetail(rx.id))}
                      style={{
                        flex: 1,
                        padding: "8px",
                        borderRadius: 6,
                        border: "none",
                        backgroundColor: "#2563EB",
                        color: "#FFFFFF",
                        cursor: "pointer",
                        fontWeight: 600,
                        fontSize: 12,
                      }}
                    >
                      Resume Draft
                    </button>
                  )}
                  {rx.status === "READY_FOR_REVIEW" && (
                    <button
                      onClick={() => navigate(doctorRoutes.prescriptionDetail(rx.id))}
                      style={{
                        flex: 1,
                        padding: "8px",
                        borderRadius: 6,
                        border: "none",
                        backgroundColor: "#166534",
                        color: "#FFFFFF",
                        cursor: "pointer",
                        fontWeight: 600,
                        fontSize: 12,
                      }}
                    >
                      Review & Sign
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default DoctorPrescriptionsScreen;
