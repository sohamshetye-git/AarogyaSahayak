import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import { StethoscopeIcon, ActivityIcon, PillIcon, ChevronRightIcon, WarningIcon, CheckCircleIcon } from "../../components/Icons";
import { useRealtime } from "../../hooks/useRealtime";

export function DoctorDashboardScreen() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = async () => {
    try {
      const res = await apiClient.getDoctorDashboard();
      setData(res);
    } catch (err) {
      console.error("Failed to load doctor dashboard", err);
    } finally {
      setLoading(false);
    }
  };

  useRealtime((event, eventData) => {
    if (["REFERRAL_CREATED", "VISIT_COMPLETED", "ASHA_ACKNOWLEDGED", "CITIZEN_CONTACTED"].includes(event)) {
      console.log(`[RealTime] Doctor dashboard invalidation: ${event}`);
      fetchDashboard();
    }
  });

  useEffect(() => {
    fetchDashboard();
  }, []);

  if (loading && !data) {
    return <div style={{ padding: 40, textAlign: "center" }}>Loading PHC clinical queue...</div>;
  }

  const urgentReferrals = data?.referrals?.filter((r: any) => r.urgency === "URGENT") || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Urgent Referral Banner */}
      {urgentReferrals.length > 0 && (
        <div
          style={{
            backgroundColor: "var(--urgent-bg)",
            border: "1px solid #F5C6CB",
            borderRadius: 12,
            padding: "16px 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "50%",
                backgroundColor: "var(--urgent)",
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
              <div style={{ fontSize: 16, fontWeight: 700, color: "var(--urgent)" }}>
                {urgentReferrals.length} Urgent PHC Referral Waiting
              </div>
              <div style={{ fontSize: 13, color: "var(--text-primary)", marginTop: 2 }}>
                Patient: <strong>{urgentReferrals[0].citizen_name}</strong> · Reason: {urgentReferrals[0].reason}
              </div>
            </div>
          </div>
          <Link
            to={`/doctor/consultation?caseId=${urgentReferrals[0].case_id}`}
            style={{
              padding: "10px 20px",
              backgroundColor: "var(--urgent)",
              color: "#FFF",
              borderRadius: 8,
              textDecoration: "none",
              fontSize: 13,
              fontWeight: 700,
              whiteSpace: "nowrap",
            }}
          >
            Start Clinical Review →
          </Link>
        </div>
      )}

      {/* Metrics Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
        <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid #F5C6CB" }}>
          <div style={{ fontSize: 13, color: "var(--urgent)", fontWeight: 600 }}>Urgent Referrals Queue</div>
          <div style={{ fontSize: 32, fontWeight: 800, color: "var(--urgent)", marginTop: 4 }}>
            {data?.urgent_referrals_count || 0}
          </div>
        </div>

        <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>Today's Consultations</div>
          <div style={{ fontSize: 32, fontWeight: 800, color: "var(--success)", marginTop: 4 }}>
            {data?.today_consultations_count || 0}
          </div>
        </div>

        <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>Assigned Follow-ups</div>
          <div style={{ fontSize: 32, fontWeight: 800, color: "var(--primary)", marginTop: 4 }}>
            {data?.pending_followups_count || 0}
          </div>
        </div>
      </div>

      {/* Referral Queue Table / List */}
      <div style={{ backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
              Incoming ASHA Referrals
            </h2>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
              Patients triaged in the field requiring medical officer consultation
            </div>
          </div>
          <Link
            to="/doctor/referrals"
            style={{ fontSize: 13, fontWeight: 600, color: "var(--primary)", textDecoration: "none" }}
          >
            View All Referrals →
          </Link>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {data?.referrals?.map((ref: any) => (
            <div
              key={ref.id}
              onClick={() => navigate(`/doctor/consultation?caseId=${ref.case_id}`)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "16px 20px",
                borderRadius: 10,
                border: ref.urgency === "URGENT" ? "1px solid #F5C6CB" : "1px solid var(--border)",
                backgroundColor: ref.urgency === "URGENT" ? "var(--urgent-bg)" : "var(--surface)",
                cursor: "pointer",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
                    {ref.citizen_name}
                  </span>
                  {ref.is_pregnant && (
                    <span style={{ padding: "2px 8px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                      Pregnant ({ref.gestational_weeks ? `${ref.gestational_weeks}w` : "7m"})
                    </span>
                  )}
                  <PriorityBadge priority={ref.urgency} size="sm" />
                  <StatusBadge status={ref.status} />
                </div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                  Ref: <strong>{ref.reference}</strong> · Case: {ref.case_reference} · Referring ASHA: {ref.referring_asha_name || "Sita Patel"}
                </div>
                <div style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 500, marginTop: 2 }}>
                  Reason: {ref.reason}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--primary)", fontWeight: 700, fontSize: 13 }}>
                <span>Review & Consult</span>
                <ChevronRightIcon size={18} color="var(--primary)" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
