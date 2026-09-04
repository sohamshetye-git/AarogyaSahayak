import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams, Link } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { doctorPaths, doctorRoutes } from "./doctorRoutes";
import {
  ActivityIcon,
  ChevronRightIcon,
  WarningIcon,
  CheckCircleIcon,
  ShieldCheckIcon,
  SearchIcon,
  StethoscopeIcon,
  PillIcon,
  PeopleIcon
} from "../../components/Icons";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import { useLanguage } from "../../context/LanguageContext";

export function DoctorPatientRecordScreen() {
  const { t } = useLanguage();
  const { citizenId, patientProfileId } = useParams<{ citizenId?: string; patientProfileId?: string }>();
  const rawId = (patientProfileId || citizenId || "").trim();
  const effectivePatientId = rawId.replace(/^CP\s+/i, "CP-").replace(/\s+/g, "-");

  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const returnTo = searchParams.get("returnTo");

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("summary");

  // Call Modal state
  const [callModalOpen, setCallModalOpen] = useState(false);
  const [callTarget, setCallTarget] = useState<{ name: string; role: string; phone: string } | null>(null);

  const fetchRecord = async (isRefresh = false) => {
    if (!effectivePatientId) {
      setError("Invalid patient identifier provided.");
      setLoading(false);
      return;
    }
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const res: any = await apiClient.getPatientRecord(effectivePatientId);
      setData(res);
    } catch (err: any) {
      console.error("Failed to load patient record", err);
      setError(err?.message || "Failed to load patient record. Access denied or network error.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchRecord();
  }, [effectivePatientId]);

  const handleCallAsha = () => {
    if (!data?.demographics) return;
    setCallTarget({
      name: data.demographics.assigned_asha_name || "Sita Patel",
      role: "Assigned ASHA Worker",
      phone: data.demographics.assigned_asha_phone || "+91 9823012345"
    });
    setCallModalOpen(true);
  };

  const handleCallCitizen = () => {
    if (!data?.demographics) return;
    setCallTarget({
      name: data.demographics.display_name,
      role: "Citizen / Patient",
      phone: data.demographics.phone_masked || "Masked Phone"
    });
    setCallModalOpen(true);
  };

  const confirmCall = () => {
    if (callTarget?.phone && callTarget.phone.includes("+91")) {
      window.location.href = `tel:${callTarget.phone.replace(/\s+/g, "")}`;
    } else {
      alert(`Initiating secure tele-consult call to ${callTarget?.name} (${callTarget?.phone})...`);
    }
    setCallModalOpen(false);
  };

  const safeReturnTo = () => {
    if (returnTo && returnTo.startsWith("/doctor/")) {
      navigate(returnTo);
    } else {
      navigate(doctorPaths.consultations());
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: "center", minHeight: "60vh" }}>
        <div className="spinner" style={{ margin: "0 auto 16px" }} />
        <h3 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>Loading Patient Record...</h3>
        <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: 14 }}>
          Retrieving longitudinal health profile, field vitals, and care history from database...
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: 40, textAlign: "center", maxWidth: 600, margin: "40px auto" }}>
        <WarningIcon size={48} color="#DC2626" />
        <h2 style={{ margin: "0 0 8px", color: "var(--text-primary)" }}>Patient Record Unavailable</h2>
        <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>{error || "Unable to fetch requested patient record."}</p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
          <button
            onClick={() => safeReturnTo()}
            style={{
              padding: "8px 16px",
              backgroundColor: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              cursor: "pointer"
            }}
          >
            ← Go Back
          </button>
          <button
            onClick={() => fetchRecord()}
            style={{
              padding: "8px 16px",
              backgroundColor: "var(--primary)",
              color: "#FFF",
              border: "none",
              borderRadius: 6,
              cursor: "pointer"
            }}
          >
            Retry Loading
          </button>
        </div>
      </div>
    );
  }

  const { demographics, active_care, health_history, dynamic_clinical_context, measurements_and_trends, cases, field_visits, referrals_and_consultations, investigations, prescriptions, follow_ups } = data;

  const categoryColorMap: Record<string, { bg: string; text: string; border: string }> = {
    MATERNAL: { bg: "#FCE7F3", text: "#9D174D", border: "#FBCFE8" },
    CHILD: { bg: "#E0F2FE", text: "#0369A1", border: "#BAE6FD" },
    NCD: { bg: "#FEF3C7", text: "#B45309", border: "#FDE68A" },
    ELDERLY: { bg: "#EDE9FE", text: "#6D28D9", border: "#DDD6FE" },
    GENERAL: { bg: "#F3F4F6", text: "#374151", border: "#E5E7EB" }
  };
  const catTheme = categoryColorMap[demographics.patient_category] || categoryColorMap.GENERAL;

  return (
    <div style={{ padding: "16px 24px 40px", maxWidth: 1400, margin: "0 auto" }}>

      {/* Top Breadcrumb & Action Toolbar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-secondary)" }}>
          <button
            onClick={safeReturnTo}
            style={{
              background: "none",
              border: "none",
              color: "var(--primary)",
              cursor: "pointer",
              fontWeight: 600,
              padding: 0,
              display: "flex",
              alignItems: "center",
              gap: 4
            }}
          >
            ← {returnTo && returnTo.includes("/direct-requests") ? "Back to Citizen Requests" : (returnTo && returnTo.includes("/consultations/") ? t("consultation.consultation_notes", "Back to Active Consultation") : t("common.back", "Back"))}
          </button>
          <span>/</span>
          <span>{t("roles.PHC_DOCTOR", "Doctor Portal")}</span>
          <span>/</span>
          <span>{t("navigation.patients", "Patient Record")}</span>
          <span>/</span>
          <strong style={{ color: "var(--text-primary)" }}>{demographics.display_name}</strong>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          {refreshing && (
            <span style={{ fontSize: 12, color: "var(--primary)", fontWeight: 600, display: "flex", alignItems: "center", gap: 4 }}>
              <span className="spinner" style={{ width: 12, height: 12 }} /> Refreshing record...
            </span>
          )}
          <button
            onClick={() => fetchRecord(true)}
            disabled={refreshing}
            style={{
              padding: "6px 12px",
              backgroundColor: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              cursor: refreshing ? "not-allowed" : "pointer"
            }}
          >
            🔄 Refresh Record
          </button>
          <button
            onClick={handleCallCitizen}
            style={{
              padding: "6px 12px",
              backgroundColor: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer"
            }}
          >
            📞 Call Patient
          </button>
          <button
            onClick={handleCallAsha}
            style={{
              padding: "6px 12px",
              backgroundColor: "#E0F2FE",
              color: "#0369A1",
              border: "1px solid #BAE6FD",
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer"
            }}
          >
            💬 Call ASHA ({demographics.assigned_asha_name})
          </button>

          {active_care?.active_case_id && (
            <button
              onClick={() => navigate(doctorPaths.caseTimeline(active_care.active_case_id))}
              style={{
                padding: "6px 12px",
                backgroundColor: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer"
              }}
            >
              📜 View Full Timeline
            </button>
          )}

          {active_care?.active_consultation_id ? (
            <button
              onClick={() => navigate(doctorPaths.consultation(active_care.active_consultation_id))}
              style={{
                padding: "6px 14px",
                backgroundColor: "#16A34A",
                color: "#FFF",
                border: "none",
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer"
              }}
            >
              ▶ Resume Consultation
            </button>
          ) : (
            returnTo && returnTo.includes("/consultations/") && (
              <button
                onClick={safeReturnTo}
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
                ← Return to Consultation
              </button>
            )
          )}
        </div>
      </div>

      {/* What Should Happen Next? Deterministic Guidance Banner */}
      <div
        style={{
          backgroundColor: "#F0FDFA",
          border: "2px solid #0D9488",
          borderRadius: 12,
          padding: "14px 18px",
          marginBottom: 16,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
          flexWrap: "wrap"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 20 }}>💡</div>
          <div>
            <div style={{ fontSize: 11, textTransform: "uppercase", fontWeight: 800, color: "#0F766E", letterSpacing: 0.5 }}>
              Deterministic Next Required Action
            </div>
            <div style={{ fontSize: 15, fontWeight: 800, color: "#115E59", marginTop: 2 }}>
              {data?.next_required_action || "No active clinical task."}
            </div>
          </div>
        </div>

        {active_care?.active_referral_id && active_care?.current_referral_status === "PATIENT_ARRIVED" && (
          <button
            onClick={() => navigate(`/doctor/consultations?caseId=${active_care.active_case_id}`)}
            style={{
              padding: "8px 16px",
              backgroundColor: "#16A34A",
              color: "#FFF",
              border: "none",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 800,
              cursor: "pointer"
            }}
          >
            ▶ Start Consultation Now
          </button>
        )}
      </div>

      {/* Main Patient Header Card */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: 20,
          marginBottom: 20,
          boxShadow: "0 2px 8px rgba(0,0,0,0.04)"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <div
              style={{
                width: 60,
                height: 60,
                borderRadius: 30,
                backgroundColor: catTheme.bg,
                color: catTheme.text,
                border: `1px solid ${catTheme.border}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 24,
                fontWeight: 800
              }}
            >
              {demographics.display_name.charAt(0)}
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>
                  {demographics.display_name}
                </h1>
                <span
                  style={{
                    padding: "3px 10px",
                    borderRadius: 12,
                    fontSize: 11,
                    fontWeight: 700,
                    backgroundColor: catTheme.bg,
                    color: catTheme.text,
                    border: `1px solid ${catTheme.border}`
                  }}
                >
                  {demographics.patient_category} TRACK
                </span>
                <span style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>
                  {demographics.age_estimate ? `${demographics.age_estimate} Yrs` : "Age unrecorded"} • {demographics.sex}
                </span>
              </div>

              <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: 13, color: "var(--text-secondary)", flexWrap: "wrap" }}>
                <span>📍 <strong>Village:</strong> {demographics.village_name}</span>
                <span>🗣️ <strong>Language:</strong> {demographics.preferred_language}</span>
                <span>📞 <strong>Mobile:</strong> {demographics.phone || demographics.phone_masked}</span>
                {demographics.abha_reference_masked && (
                  <span>🆔 <strong>ABHA:</strong> {demographics.abha_reference_masked}</span>
                )}
              </div>
            </div>
          </div>

          {/* Header Quick Meta */}
          <div style={{ display: "flex", gap: 20, textAlign: "right", flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase", fontWeight: 700 }}>
                Assigned ASHA
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                {demographics.assigned_asha_name}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase", fontWeight: 700 }}>
                Linked PHC
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
                {demographics.assigned_facility_name}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", textTransform: "uppercase", fontWeight: 700 }}>
                Consent Status
              </div>
              <div style={{ fontSize: 13, fontWeight: 700, color: demographics.consent_status === "OBTAINED" ? "#16A34A" : "#D97706" }}>
                ✓ {demographics.consent_status} ({demographics.consent_method})
              </div>
            </div>
          </div>
        </div>

        {/* Active Safety Alerts Banner if any */}
        {active_care?.active_safety_warnings && active_care.active_safety_warnings.length > 0 && (
          <div
            style={{
              marginTop: 16,
              padding: "10px 14px",
              backgroundColor: "#FEF2F2",
              border: "1px solid #FECACA",
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              gap: 10
            }}
          >
            <WarningIcon size={18} color="#DC2626" />
            <div style={{ fontSize: 13, color: "#991B1B", fontWeight: 600 }}>
              <strong>Deterministic Safety Warning Triggered:</strong>{" "}
              {active_care.active_safety_warnings.map((w: any) => w.reason).join(" | ")}
            </div>
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--border)", marginBottom: 20, overflowX: "auto", paddingBottom: 2 }}>
        {[
          { id: "summary", label: "Patient Summary" },
          { id: "activeCare", label: `Active Care (${active_care?.active_case_reference || "1 Case"})` },
          { id: "clinicalContext", label: `${demographics.patient_category} Track` },
          { id: "vitals", label: `Vitals & Trends (${measurements_and_trends.length})` },
          { id: "prescriptions", label: `Signed Prescriptions (${prescriptions.length})` },
          { id: "investigations", label: `Investigations (${investigations.length})` },
          { id: "visits", label: `ASHA Visits (${field_visits.length})` },
          { id: "followups", label: `Follow-ups (${follow_ups.length})` },
          { id: "referrals", label: `Referrals & Consultations (${referrals_and_consultations.length})` },
          { id: "history", label: "Health History" }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "10px 16px",
              border: "none",
              borderBottom: activeTab === tab.id ? "3px solid var(--primary)" : "3px solid transparent",
              background: "none",
              color: activeTab === tab.id ? "var(--primary)" : "var(--text-secondary)",
              fontWeight: activeTab === tab.id ? 700 : 500,
              fontSize: 13,
              cursor: "pointer",
              whiteSpace: "nowrap"
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>


      {/* TAB CONTENT SECTIONS */}

      {/* SECTION A & B: PATIENT SUMMARY & ACTIVE CARE */}
      {activeTab === "summary" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: 20 }}>
          {/* Card 1: Demographics & Social */}
          <div style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 18 }}>
            <h3 style={{ margin: "0 0 14px", fontSize: 16, fontWeight: 700, borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
              📋 Demographics & Social Context
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13 }}>
              <div>
                <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Full Name</div>
                <div style={{ fontWeight: 600 }}>{demographics.display_name}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Gender & Age</div>
                <div style={{ fontWeight: 600 }}>{demographics.sex} • {demographics.age_estimate} years</div>
              </div>
              <div>
                <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Date of Birth</div>
                <div style={{ fontWeight: 600 }}>{demographics.date_of_birth}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Preferred Language</div>
                <div style={{ fontWeight: 600 }}>{demographics.preferred_language}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Head of Household</div>
                <div style={{ fontWeight: 600 }}>{demographics.head_of_household_name}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Household Category</div>
                <div style={{ fontWeight: 600 }}>{demographics.household_category}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Ration Card</div>
                <div style={{ fontWeight: 600 }}>{demographics.ration_card_category}</div>
              </div>
              <div>
                <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Registration Date</div>
                <div style={{ fontWeight: 600 }}>{new Date(demographics.registration_date).toLocaleDateString()}</div>
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Full Address</div>
                <div style={{ fontWeight: 600 }}>
                  {demographics.address !== "Not recorded" ? demographics.address : `${demographics.village_name}, ${demographics.gram_panchayat}, ${demographics.block_taluka}, ${demographics.district} - ${demographics.pincode}`}
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Active Care Summary */}
          <div style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 18 }}>
            <h3 style={{ margin: "0 0 14px", fontSize: 16, fontWeight: 700, borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
              ⚡ Active Care Status
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12, fontSize: 13 }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", backgroundColor: "var(--background)", borderRadius: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>Active Case:</span>
                <strong style={{ color: "var(--primary)" }}>{active_care?.active_case_reference || "No active case"}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", backgroundColor: "var(--background)", borderRadius: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>Primary Concern:</span>
                <strong style={{ maxWidth: 220, textAlign: "right" }}>{active_care?.current_concern || "Not recorded"}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", backgroundColor: "var(--background)", borderRadius: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>Referral Status:</span>
                <strong style={{ color: "#D97706" }}>{active_care?.current_referral_status || "None"} ({active_care?.current_referral_reference || "N/A"})</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", backgroundColor: "var(--background)", borderRadius: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>Pending Lab Orders:</span>
                <strong>{active_care?.pending_investigations_count || 0} pending</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", backgroundColor: "var(--background)", borderRadius: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>Signed Doctor Prescriptions:</span>
                <strong style={{ color: "#16A34A" }}>{active_care?.active_prescriptions_count || 0} active</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", backgroundColor: "var(--background)", borderRadius: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>Pending ASHA Follow-ups:</span>
                <strong style={{ color: "#0369A1" }}>{active_care?.pending_asha_followups_count || 0} assigned</strong>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SECTION B: ACTIVE CARE DETAILS */}
      {activeTab === "activeCare" && (
        <div style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 700 }}>Active Care Overview</h3>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16, marginBottom: 20 }}>
            <div style={{ padding: 14, border: "1px solid var(--border)", borderRadius: 8, backgroundColor: "#FFF" }}>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Active Case Ref</div>
              <div style={{ fontSize: 16, fontWeight: 800, color: "var(--primary)", marginTop: 4 }}>
                {active_care?.active_case_reference || "N/A"}
              </div>
              <div style={{ fontSize: 12, marginTop: 4 }}>Concern: {active_care?.current_concern}</div>
            </div>

            <div style={{ padding: 14, border: "1px solid var(--border)", borderRadius: 8, backgroundColor: "#FFF" }}>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Current Referral</div>
              <div style={{ fontSize: 16, fontWeight: 800, color: "#D97706", marginTop: 4 }}>
                {active_care?.current_referral_reference || "No Referral"}
              </div>
              <div style={{ fontSize: 12, marginTop: 4 }}>Status: {active_care?.current_referral_status || "N/A"}</div>
            </div>

            <div style={{ padding: 14, border: "1px solid var(--border)", borderRadius: 8, backgroundColor: "#FFF" }}>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Consultation State</div>
              <div style={{ fontSize: 16, fontWeight: 800, color: "#16A34A", marginTop: 4 }}>
                {active_care?.consultation_status || "COMPLETED"}
              </div>
              <div style={{ fontSize: 12, marginTop: 4 }}>Facility: Kalyanpur PHC</div>
            </div>
          </div>

          {active_care?.active_case_id && (
            <div style={{ textAlign: "right" }}>
              <button
                onClick={() => navigate(doctorPaths.caseTimeline(active_care.active_case_id))}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "var(--primary)",
                  color: "#FFF",
                  border: "none",
                  borderRadius: 6,
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: "pointer"
                }}
              >
                Open Case Timeline ({active_care.active_case_reference}) →
              </button>
            </div>
          )}
        </div>
      )}

      {/* SECTION D: DYNAMIC CLINICAL CONTEXT */}
      {activeTab === "clinicalContext" && (
        <div style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 700 }}>
            🩺 Dynamic Clinical Context — {demographics.patient_category} TRACK
          </h3>

          {dynamic_clinical_context?.maternal && (
            <div style={{ padding: 16, backgroundColor: "#FCE7F3", border: "1px solid #FBCFE8", borderRadius: 8 }}>
              <h4 style={{ margin: "0 0 12px", color: "#9D174D", fontSize: 15, fontWeight: 800 }}>
                🤰 Maternal Care Profile (High Priority Track)
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12, fontSize: 13 }}>
                <div><strong>Pregnancy Status:</strong> {dynamic_clinical_context.maternal.pregnancy_status}</div>
                <div><strong>Gestational Age:</strong> {dynamic_clinical_context.maternal.gestational_age_text}</div>
                <div><strong>ANC Registration:</strong> {dynamic_clinical_context.maternal.anc_registration_number}</div>
                <div><strong>Gravida / Parity:</strong> {dynamic_clinical_context.maternal.gravida_parity}</div>
                <div><strong>IFA / Calcium Adherence:</strong> {dynamic_clinical_context.maternal.ifa_calcium_adherence}</div>
                <div><strong>Recorded Danger Signs:</strong> {dynamic_clinical_context.maternal.maternal_danger_signs.join(", ")}</div>
              </div>
            </div>
          )}

          {dynamic_clinical_context?.child && (
            <div style={{ padding: 16, backgroundColor: "#E0F2FE", border: "1px solid #BAE6FD", borderRadius: 8 }}>
              <h4 style={{ margin: "0 0 12px", color: "#0369A1", fontSize: 15, fontWeight: 800 }}>
                👶 Child Care Profile
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12, fontSize: 13 }}>
                <div><strong>Exact Age:</strong> {dynamic_clinical_context.child.exact_age}</div>
                <div><strong>Date of Birth:</strong> {dynamic_clinical_context.child.date_of_birth}</div>
                <div><strong>Growth Metrics:</strong> {dynamic_clinical_context.child.weight_height}</div>
                <div><strong>Immunization Summary:</strong> {dynamic_clinical_context.child.immunization_summary}</div>
                <div><strong>Nutrition Status:</strong> {dynamic_clinical_context.child.nutrition_status}</div>
              </div>
            </div>
          )}

          {dynamic_clinical_context?.ncd && (
            <div style={{ padding: 16, backgroundColor: "#FEF3C7", border: "1px solid #FDE68A", borderRadius: 8 }}>
              <h4 style={{ margin: "0 0 12px", color: "#B45309", fontSize: 15, fontWeight: 800 }}>
                🫀 Non-Communicable Disease (NCD) Track
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12, fontSize: 13 }}>
                <div><strong>Condition History:</strong> {dynamic_clinical_context.ncd.condition_history.join(", ")}</div>
                <div><strong>BP / Glucose Trend:</strong> {dynamic_clinical_context.ncd.bp_glucose_trends}</div>
                <div><strong>Medication Adherence:</strong> {dynamic_clinical_context.ncd.medication_adherence}</div>
                <div><strong>Planned Screening:</strong> {dynamic_clinical_context.ncd.planned_screening_review}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SECTION E: MEASUREMENTS & TRENDS WITH VISIBLE SOURCE LABELS */}
      {activeTab === "vitals" && (
        <div style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>📊 Longitudinal Vitals & Field Measurements</h3>
            <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              Sorted newest first • Clear source attribution
            </span>
          </div>

          {measurements_and_trends.length === 0 ? (
            <div style={{ padding: 30, textAlign: "center", color: "var(--text-secondary)" }}>
              No longitudinal vital measurements recorded yet for this patient.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ backgroundColor: "var(--background)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                    <th style={{ padding: "10px 12px" }}>Measurement</th>
                    <th style={{ padding: "10px 12px" }}>Value</th>
                    <th style={{ padding: "10px 12px" }}>Recorded Time</th>
                    <th style={{ padding: "10px 12px" }}>Recorder & Role</th>
                    <th style={{ padding: "10px 12px" }}>Data Source Label</th>
                  </tr>
                </thead>
                <tbody>
                  {measurements_and_trends.map((m: any) => {
                    let sourceBadgeBg = "#E0F2FE";
                    let sourceBadgeText = "#0369A1";
                    if (m.source_label === "PHC Doctor") {
                      sourceBadgeBg = "#F3E8FF";
                      sourceBadgeText = "#6B21A8";
                    } else if (m.source_label === "Citizen Reported") {
                      sourceBadgeBg = "#DCFCE7";
                      sourceBadgeText = "#15803D";
                    }

                    return (
                      <tr key={m.id} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={{ padding: "10px 12px", fontWeight: 700 }}>{m.type}</td>
                        <td style={{ padding: "10px 12px" }}>
                          <span
                            style={{
                              fontWeight: 800,
                              fontSize: 14,
                              color: m.is_warning ? "#DC2626" : "var(--text-primary)"
                            }}
                          >
                            {m.value} {m.unit}
                          </span>
                          {m.is_warning && <span style={{ marginLeft: 6, fontSize: 11, color: "#DC2626", fontWeight: 700 }}>⚠️ Warning</span>}
                        </td>
                        <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>
                          {m.recorded_at ? new Date(m.recorded_at).toLocaleString() : "Not recorded"}
                        </td>
                        <td style={{ padding: "10px 12px" }}>
                          <strong>{m.recorder_name}</strong> ({m.recorder_role})
                        </td>
                        <td style={{ padding: "10px 12px" }}>
                          <span
                            style={{
                              padding: "3px 8px",
                              borderRadius: 12,
                              fontSize: 11,
                              fontWeight: 700,
                              backgroundColor: sourceBadgeBg,
                              color: sourceBadgeText
                            }}
                          >
                            🏷️ {m.source_label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* SECTION J: DOCTOR-SIGNED PRESCRIPTIONS ONLY */}
      {activeTab === "prescriptions" && (
        <div style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 700 }}>
            💊 Doctor-Signed Prescriptions
          </h3>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 16 }}>
            Only finalized, doctor-signed prescriptions are listed below. Unsigned drafts are excluded.
          </p>

          {prescriptions.length === 0 ? (
            <div style={{ padding: 30, textAlign: "center", color: "var(--text-secondary)" }}>
              No doctor-signed prescriptions recorded for this patient.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {prescriptions.map((p: any) => (
                <div key={p.prescription_id} style={{ border: "1px solid #BBF7D0", borderRadius: 8, padding: 16, backgroundColor: "#F0FDF4" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #DCFCE7", paddingBottom: 10, marginBottom: 10 }}>
                    <div>
                      <strong style={{ color: "#166534" }}>Prescribed by: {p.doctor_name || p.prescriber_doctor_name}</strong>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                        Ref: {p.reference || p.prescription_id} · Signed: {p.signed_at ? new Date(p.signed_at).toLocaleString() : "Signed"}
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ padding: "4px 10px", backgroundColor: "#DCFCE7", color: "#15803D", borderRadius: 12, fontSize: 12, fontWeight: 800 }}>
                        ✓ {p.status || "SIGNED"}
                      </span>
                      <button
                        onClick={() => navigate(doctorRoutes.prescriptionDetail(p.prescription_id || p.id))}
                        style={{ padding: "4px 10px", backgroundColor: "#2563EB", color: "#FFF", border: "none", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer" }}
                      >
                        View Prescription
                      </button>
                    </div>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}>
                    {p.items?.map((item: any, idx: number) => (
                      <div key={idx} style={{ backgroundColor: "#FFF", padding: 12, borderRadius: 6, border: "1px solid #E5E7EB" }}>
                        <div style={{ fontWeight: 800, fontSize: 14, color: "var(--text-primary)" }}>
                          💊 {item.medicine} ({item.strength})
                        </div>
                        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                          Form: {item.form} • Dose: {item.dose}
                        </div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: "#0369A1", marginTop: 4 }}>
                          Frequency: {item.frequency} • Duration: {item.duration}
                        </div>
                        {item.instructions && (
                          <div style={{ fontSize: 11, fontStyle: "italic", marginTop: 4 }}>
                            Instructions: {item.instructions}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SECTION I: INVESTIGATIONS */}
      {activeTab === "investigations" && (
        <div style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 700 }}>🧪 Ordered Lab Investigations</h3>

          {investigations.length === 0 ? (
            <div style={{ padding: 30, textAlign: "center", color: "var(--text-secondary)" }}>
              No lab investigations ordered for this patient.
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ backgroundColor: "var(--background)", borderBottom: "1px solid var(--border)", textAlign: "left" }}>
                  <th style={{ padding: "10px 12px" }}>Test Name</th>
                  <th style={{ padding: "10px 12px" }}>Priority</th>
                  <th style={{ padding: "10px 12px" }}>Status</th>
                  <th style={{ padding: "10px 12px" }}>Order Date</th>
                  <th style={{ padding: "10px 12px" }}>Ordering Doctor</th>
                  <th style={{ padding: "10px 12px" }}>Result / Status</th>
                  <th style={{ padding: "10px 12px" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {investigations.map((inv: any) => (
                  <tr key={inv.investigation_id || inv.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 12px", fontWeight: 700 }}>🧪 {inv.test_name}</td>
                    <td style={{ padding: "10px 12px" }}>
                      <span style={{ padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 700, backgroundColor: "#FEF3C7", color: "#B45309" }}>
                        {inv.priority}
                      </span>
                    </td>
                    <td style={{ padding: "10px 12px" }}>{inv.status}</td>
                    <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>
                      {inv.ordered_at ? new Date(inv.ordered_at).toLocaleDateString() : "Today"}
                    </td>
                    <td style={{ padding: "10px 12px" }}>{inv.ordering_doctor_name || "Medical Officer"}</td>
                    <td style={{ padding: "10px 12px", fontWeight: 600 }}>{inv.result_preview || inv.result || "Pending"}</td>
                    <td style={{ padding: "10px 12px" }}>
                      <button
                        onClick={() => navigate(doctorPaths.investigationDetail(inv.id || inv.investigation_id))}
                        style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid var(--border)", background: "none", cursor: "pointer", fontSize: 11, fontWeight: 600 }}
                      >
                        View Order
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* SECTION G: FIELD VISITS */}
      {activeTab === "visits" && (
        <div style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 700 }}>🏠 ASHA Field Visits</h3>

          {field_visits.length === 0 ? (
            <div style={{ padding: 30, textAlign: "center", color: "var(--text-secondary)" }}>
              No home visits recorded by ASHA for this patient.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {field_visits.map((fv: any) => (
                <div key={fv.visit_id} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 14, backgroundColor: "var(--background)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <strong style={{ fontSize: 14 }}>📌 {fv.reference} ({fv.visit_type})</strong>
                    <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                      {fv.date ? new Date(fv.date).toLocaleString() : "Recent"}
                    </span>
                  </div>
                  <div style={{ fontSize: 13, marginBottom: 8 }}>
                    <strong>ASHA Observations:</strong> {fv.asha_observations}
                  </div>
                  <div style={{ display: "flex", gap: 12, fontSize: 12, color: "var(--text-secondary)" }}>
                    <span>Consent Obtained: {fv.consent_obtained ? "Yes" : "No"}</span>
                    <span>Next Action: {fv.next_action}</span>
                    {fv.voice_transcript_available && <span style={{ color: "#0369A1", fontWeight: 600 }}>🎙️ Voice Transcript Recorded</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SECTION K: FOLLOW-UPS */}
      {activeTab === "followups" && (
        <div style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 700 }}>📋 ASHA Follow-up Directives</h3>

          {follow_ups.length === 0 ? (
            <div style={{ padding: 30, textAlign: "center", color: "var(--text-secondary)" }}>
              No follow-up directives assigned for this patient.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {follow_ups.map((fup: any) => (
                <div key={fup.followup_id} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 14, backgroundColor: "#FFF" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <strong style={{ fontSize: 14, color: "var(--primary)" }}>Directive: {fup.directive}</strong>
                    <span style={{ padding: "2px 8px", backgroundColor: "#E0F2FE", color: "#0369A1", borderRadius: 10, fontSize: 11, fontWeight: 700 }}>
                      {fup.status}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                    Source: {fup.source} • Assigned to ASHA: {fup.assigned_asha_name} • Due Date: {fup.due_date ? new Date(fup.due_date).toLocaleDateString() : "Within 3 days"}
                  </div>
                  <div style={{ fontSize: 12, marginTop: 6, fontWeight: 600 }}>
                    Doctor Review Outcome: {fup.doctor_review_outcome}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SECTION H: REFERRALS & CONSULTATIONS */}
      {activeTab === "referrals" && (
        <div style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 700 }}>🏥 Referrals & Consultations</h3>

          {referrals_and_consultations.length === 0 ? (
            <div style={{ padding: 30, textAlign: "center", color: "var(--text-secondary)" }}>
              No referrals or consultations recorded.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {referrals_and_consultations.map((item: any) => (
                <div key={item.referral_id} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 14, backgroundColor: "#FFF" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <strong style={{ fontSize: 14 }}>
                      Referral: {item.referral_reference} → {item.target_facility}
                    </strong>
                    <span style={{ fontSize: 12, fontWeight: 700, color: "#D97706" }}>{item.referral_status}</span>
                  </div>
                  <div style={{ fontSize: 13, marginBottom: 6 }}>Reason: {item.reason}</div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                    Referring ASHA: {item.referring_asha_name} • Doctor: {item.doctor_name} • Consultation: {item.consultation_reference || "N/A"}
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "#16A34A", marginTop: 6 }}>
                    Confirmed Assessment: {item.confirmed_assessment}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SECTION C: HEALTH HISTORY */}
      {activeTab === "history" && (
        <div style={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 700 }}>📖 Full Health History</h3>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16, fontSize: 13 }}>
            <div>
              <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Blood Group</div>
              <div style={{ fontWeight: 700 }}>{health_history.blood_group}</div>
            </div>
            <div>
              <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Known Allergies</div>
              <div style={{ fontWeight: 700 }}>{health_history.allergies.length > 0 ? health_history.allergies.join(", ") : "Not recorded"}</div>
            </div>
            <div>
              <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Chronic Conditions</div>
              <div style={{ fontWeight: 700 }}>{health_history.chronic_conditions.length > 0 ? health_history.chronic_conditions.join(", ") : "Not recorded"}</div>
            </div>
            <div>
              <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Previous Illnesses</div>
              <div style={{ fontWeight: 700 }}>{health_history.previous_illnesses}</div>
            </div>
            <div>
              <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Previous Surgeries</div>
              <div style={{ fontWeight: 700 }}>{health_history.previous_surgeries}</div>
            </div>
            <div>
              <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Tobacco / Alcohol</div>
              <div style={{ fontWeight: 700 }}>Tobacco: {health_history.tobacco_use} • Alcohol: {health_history.alcohol_use}</div>
            </div>
            <div style={{ gridColumn: "1 / -1" }}>
              <div style={{ color: "var(--text-secondary)", fontSize: 11 }}>Disability Information</div>
              <div style={{ fontWeight: 700 }}>{health_history.disability_notes}</div>
            </div>
          </div>
        </div>
      )}

      {/* CALL CONFIRMATION MODAL */}
      {callModalOpen && callTarget && (
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
            zIndex: 9999
          }}
        >
          <div
            style={{
              backgroundColor: "var(--surface)",
              borderRadius: 12,
              padding: 24,
              maxWidth: 420,
              width: "90%",
              boxShadow: "0 10px 25px rgba(0,0,0,0.2)"
            }}
          >
            <h3 style={{ margin: "0 0 12px", fontSize: 18, fontWeight: 800 }}>
              📞 Initiate Call to {callTarget.role}
            </h3>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 16 }}>
              You are about to place a tele-consultation call to <strong>{callTarget.name}</strong>.
            </p>
            <div style={{ padding: 12, backgroundColor: "var(--background)", borderRadius: 8, fontSize: 13, marginBottom: 20 }}>
              <div><strong>Recipient:</strong> {callTarget.name}</div>
              <div><strong>Role:</strong> {callTarget.role}</div>
              <div><strong>Phone Number:</strong> {callTarget.phone}</div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
              <button
                onClick={() => setCallModalOpen(false)}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  cursor: "pointer"
                }}
              >
                Cancel
              </button>
              <button
                onClick={confirmCall}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "var(--primary)",
                  color: "#FFF",
                  border: "none",
                  borderRadius: 6,
                  fontWeight: 700,
                  cursor: "pointer"
                }}
              >
                Confirm & Call
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
