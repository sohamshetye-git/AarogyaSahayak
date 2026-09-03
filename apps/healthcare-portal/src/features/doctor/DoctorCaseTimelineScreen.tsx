import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge } from "../../components/StatusBadge";
import { useRealtime } from "../../hooks/useRealtime";
import { doctorPaths } from "./doctorRoutes";

export function DoctorCaseTimelineScreen() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const returnTo = searchParams.get("returnTo");
  const highlightOrder = searchParams.get("highlightOrder");
  const backTarget = returnTo || doctorPaths.dashboard();
  const backLabel = returnTo && returnTo.includes("investigations")
    ? "← Back to Investigations"
    : returnTo && returnTo.includes("consultations")
    ? "← Back to Consultations"
    : returnTo
    ? "← Back"
    : "← Back to Dashboard";

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [activeCategory, setActiveCategory] = useState<string>("ALL");

  const fetchTimeline = async () => {
    if (!caseId) {
      setLoading(false);
      return;
    }
    try {
      setErrorStatus(null);
      const res = await apiClient.getDoctorCaseTimeline(caseId);
      setData(res);
    } catch (err: any) {
      console.error("Failed to load doctor case timeline", err);
      const status = err?.status || (err?.code === "FORBIDDEN_FACILITY_ACCESS" ? 403 : err?.code === "CASE_NOT_FOUND" ? 404 : 500);
      setErrorStatus(status);
      setErrorMessage(err?.message || "Failed to load patient case timeline.");
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
        "FOLLOW_UP_ASSIGNED",
        "FOLLOWUP_COMPLETED",
        "FOLLOWUP_ESCALATED",
        "VISIT_COMPLETED",
      ].includes(event)
    ) {
      fetchTimeline();
    }
  });

  useEffect(() => {
    fetchTimeline();
    const timer = setInterval(fetchTimeline, 8000);
    return () => clearInterval(timer);
  }, [caseId]);

  if (!caseId) {
    return (
      <div style={{ padding: 40, maxWidth: 600, margin: "40px auto", backgroundColor: "#FEF2F2", borderRadius: 12, border: "1px solid #FCA5A5", textAlign: "center" }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
        <h2 style={{ margin: "0 0 12px", color: "#991B1B" }}>Timeline Unavailable</h2>
        <p style={{ color: "#7F1D1D", marginBottom: 24 }}>
          Timeline unavailable because this consultation is not linked to a case.
        </p>
        <button
          onClick={() => navigate(backTarget)}
          style={{ padding: "10px 20px", backgroundColor: "#DC2626", color: "#FFF", borderRadius: 8, border: "none", fontWeight: 700, cursor: "pointer" }}
        >
          {backLabel}
        </button>
      </div>
    );
  }

  if (loading && !data && !errorStatus) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
        <div style={{ fontSize: 24, marginBottom: 12 }}>⏳</div>
        Loading Case Timeline...
      </div>
    );
  }

  // 404 Case Not Found Page
  if (errorStatus === 404) {
    return (
      <div style={{ padding: 40, maxWidth: 600, margin: "40px auto", backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", textAlign: "center" }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🔍</div>
        <h2 style={{ margin: "0 0 12px", color: "var(--urgent)" }}>Case Record Not Found (404)</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>
          No case matching ID <strong>{caseId}</strong> was found in the PostgreSQL database.
        </p>
        <button
          onClick={() => navigate(backTarget)}
          style={{ padding: "10px 20px", backgroundColor: "var(--primary)", color: "#FFF", borderRadius: 8, border: "none", fontWeight: 700, cursor: "pointer" }}
        >
          {backLabel}
        </button>
      </div>
    );
  }

  // 403 Forbidden Jurisdiction Page
  if (errorStatus === 403) {
    return (
      <div style={{ padding: 40, maxWidth: 600, margin: "40px auto", backgroundColor: "#FEE2E2", borderRadius: 12, border: "1px solid #FCA5A5", textAlign: "center" }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🛡️</div>
        <h2 style={{ margin: "0 0 12px", color: "#991B1B" }}>Access Forbidden (403)</h2>
        <p style={{ color: "#7F1D1D", marginBottom: 24 }}>
          {errorMessage || "You do not have clinical jurisdiction over this case. Access is restricted to assigned PHC facility doctors."}
        </p>
        <button
          onClick={() => navigate(backTarget)}
          style={{ padding: "10px 20px", backgroundColor: "#991B1B", color: "#FFF", borderRadius: 8, border: "none", fontWeight: 700, cursor: "pointer" }}
        >
          {backLabel}
        </button>
      </div>
    );
  }

  // Generic Error Page with Retry
  if (errorStatus && errorStatus >= 500) {
    return (
      <div style={{ padding: 40, maxWidth: 600, margin: "40px auto", backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", textAlign: "center" }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
        <h2 style={{ margin: "0 0 12px", color: "var(--urgent)" }}>Failed to Load Timeline</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>{errorMessage}</p>
        <button
          onClick={fetchTimeline}
          style={{ padding: "10px 20px", backgroundColor: "var(--primary)", color: "#FFF", borderRadius: 8, border: "none", fontWeight: 700, cursor: "pointer" }}
        >
          Retry Loading
        </button>
      </div>
    );
  }

  const events: any[] = data?.events || [];
  const filteredEvents = events.filter((ev) => {
    if (activeCategory === "ALL") return true;
    return ev.category?.toUpperCase() === activeCategory.toUpperCase();
  });

  const getCategoryBadge = (cat: string) => {
    switch (cat?.toUpperCase()) {
      case "CITIZEN":
        return { icon: "🙋‍♀️", label: "Citizen", bg: "#EFF6FF", color: "#1D4ED8" };
      case "ASHA":
        return { icon: "🏡", label: "ASHA Worker", bg: "#F0FDF4", color: "#15803D" };
      case "DOCTOR":
        return { icon: "👩‍⚕️", label: "PHC Doctor", bg: "#EEF2FF", color: "#4338CA" };
      case "REFERRAL":
        return { icon: "🚑", label: "Referral", bg: "#FEF3C7", color: "#B45309" };
      case "CONSULTATION":
        return { icon: "🩺", label: "Consultation", bg: "#F3E8FF", color: "#6B21A8" };
      case "INVESTIGATION":
        return { icon: "🧪", label: "Investigation", bg: "#E0F2FE", color: "#0369A1" };
      case "FOLLOWUP":
        return { icon: "📋", label: "Follow-up", bg: "#FCE4EC", color: "#C2185B" };
      default:
        return { icon: "📌", label: "Event", bg: "var(--neutral-bg)", color: "var(--text-primary)" };
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 1200, margin: "0 auto", width: "100%" }}>
      {/* Header Banner */}
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
          <button
            onClick={() => navigate(backTarget)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--primary)",
              fontWeight: 700,
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              fontSize: 14,
            }}
          >
            {backLabel}
          </button>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            {data?.citizen_id && (
              <button
                onClick={() => navigate(doctorPaths.patient(data.citizen_id))}
                style={{
                  padding: "6px 14px",
                  backgroundColor: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  fontWeight: 600,
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                👁 View Patient Record
              </button>
            )}
            {(data?.consultation_id || data?.active_consultation_id) && (
              <button
                onClick={() => navigate(doctorPaths.consultation(data.consultation_id || data.active_consultation_id))}
                style={{
                  padding: "6px 14px",
                  backgroundColor: "#16A34A",
                  color: "#FFF",
                  border: "none",
                  borderRadius: 6,
                  fontWeight: 700,
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                ▶ Resume Consultation
              </button>
            )}
            <button
              onClick={fetchTimeline}
              style={{
                padding: "6px 14px",
                backgroundColor: "var(--neutral-bg)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                fontWeight: 600,
                fontSize: 12,
                cursor: "pointer",
              }}
            >
              ↻ Refresh
            </button>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>
                {data?.citizen_name}
              </span>
              <span style={{ fontSize: 14, color: "var(--text-secondary)" }}>
                ({data?.citizen_age}y · {data?.citizen_gender} · {data?.village_name})
              </span>
              {data?.is_pregnant && (
                <span style={{ padding: "3px 10px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 12, fontWeight: 700 }}>
                  🤰 Maternal ({data?.gestational_weeks ? `${data.gestational_weeks}w` : "28w"})
                </span>
              )}
              <PriorityBadge priority={data?.priority} size="sm" />
              <span style={{ padding: "3px 10px", borderRadius: 8, backgroundColor: "#E0E7FF", color: "#3730A3", fontSize: 12, fontWeight: 700 }}>
                {data?.status}
              </span>
            </div>
            <div style={{ fontSize: 14, color: "var(--text-secondary)", display: "flex", gap: 16, flexWrap: "wrap" }}>
              <span>Case Ref: <strong>{data?.case_reference}</strong></span>
              <span>Assigned ASHA: <strong>{data?.assigned_asha_name}</strong></span>
              <span>Facility: <strong>{data?.assigned_facility_name}</strong></span>
            </div>
          </div>

          {data?.assigned_asha_phone && (
            <a
              href={`tel:${data.assigned_asha_phone}`}
              style={{
                padding: "8px 16px",
                backgroundColor: "#E0F2FE",
                color: "#0369A1",
                border: "none",
                borderRadius: 8,
                fontWeight: 700,
                textDecoration: "none",
                fontSize: 13,
              }}
            >
              📞 Call ASHA ({data.assigned_asha_phone})
            </a>
          )}
        </div>
      </div>

      {/* Summary Card */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
        <div style={{ padding: 18, backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 700, textTransform: "uppercase", marginBottom: 6 }}>
            Primary Complaint & Concern
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
            "{data?.primary_concern}"
          </div>
        </div>

        <div style={{ padding: 18, backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 700, textTransform: "uppercase", marginBottom: 6 }}>
            Latest Recorded Vitals
          </div>
          {data?.latest_vitals ? (
            <div style={{ fontSize: 14, fontWeight: 700, display: "flex", gap: 12, flexWrap: "wrap", color: "var(--primary-dark)" }}>
              {data.latest_vitals.systolic_bp && <span>BP: {data.latest_vitals.systolic_bp}/{data.latest_vitals.diastolic_bp} mmHg</span>}
              {data.latest_vitals.spo2 && <span>SpO₂: {data.latest_vitals.spo2}%</span>}
              {data.latest_vitals.pulse && <span>Pulse: {data.latest_vitals.pulse} bpm</span>}
            </div>
          ) : (
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>No vitals recorded yet.</div>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 12, border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Case History Timeline ({filteredEvents.length})</h3>
        </div>
        <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 4 }}>
          {[
            { id: "ALL", label: "All Events" },
            { id: "CITIZEN", label: "Citizen" },
            { id: "ASHA", label: "ASHA Worker" },
            { id: "DOCTOR", label: "Doctor" },
            { id: "REFERRAL", label: "Referral" },
            { id: "CONSULTATION", label: "Consultation" },
            { id: "INVESTIGATION", label: "Investigation" },
            { id: "FOLLOWUP", label: "Follow-up" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveCategory(tab.id)}
              style={{
                padding: "6px 14px",
                borderRadius: 20,
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                border: activeCategory === tab.id ? "2px solid var(--primary)" : "1px solid var(--border)",
                backgroundColor: activeCategory === tab.id ? "var(--primary-light)" : "var(--surface)",
                color: activeCategory === tab.id ? "var(--primary-dark)" : "var(--text-primary)",
                whiteSpace: "nowrap",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Timeline Stream */}
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        {filteredEvents.length === 0 ? (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)", backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
            No timeline events match the selected category.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 18, position: "relative" }}>
            {/* Vertical Line */}
            <div style={{ position: "absolute", top: 10, bottom: 10, left: 19, width: 2, backgroundColor: "var(--border)", zIndex: 0 }} />

            {filteredEvents.map((ev: any) => {
              const badge = getCategoryBadge(ev.category);
              const isHighlighted = Boolean(
                highlightOrder &&
                (ev.source_entity_id === highlightOrder ||
                  ev.event_id?.includes(highlightOrder) ||
                  ev.safe_description?.includes(highlightOrder) ||
                  ev.title?.includes(highlightOrder))
              );
              return (
                <div key={ev.event_id} style={{ display: "flex", gap: 16, alignItems: "flex-start", zIndex: 1 }}>
                  {/* Category Circle Icon */}
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: "50%",
                      backgroundColor: badge.bg,
                      color: badge.color,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 18,
                      flexShrink: 0,
                      border: `1px solid ${badge.color}`,
                    }}
                  >
                    {badge.icon}
                  </div>

                  {/* Content Box */}
                  <div
                    style={{
                      flex: 1,
                      backgroundColor: isHighlighted ? "#f0f9ff" : "var(--neutral-bg)",
                      padding: 14,
                      borderRadius: 10,
                      border: isHighlighted ? "2px solid #0284c7" : "1px solid var(--border)",
                      boxShadow: isHighlighted ? "0 0 0 3px rgba(2, 132, 199, 0.15)" : undefined,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 8, marginBottom: 4 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                        <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                          {ev.title}
                        </span>
                        {isHighlighted && (
                          <span style={{ padding: "2px 8px", backgroundColor: "#0284c7", color: "#ffffff", borderRadius: 4, fontSize: 11, fontWeight: 700 }}>
                            Linked Investigation Order
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>
                        {new Date(ev.occurred_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}
                      </div>
                    </div>

                    <div style={{ fontSize: 13, color: "var(--text-primary)", marginBottom: 8 }}>
                      {ev.safe_description}
                    </div>

                    <div style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", gap: 12, flexWrap: "wrap" }}>
                      <span>Actor: <strong>{ev.actor_name}</strong> ({ev.actor_role})</span>
                      <span>Category: <strong>{badge.label}</strong></span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
