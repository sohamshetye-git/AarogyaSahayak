import React, { useEffect, useState } from "react";
import { apiClient } from "@aarogya/api-client";
import { ShieldCheckIcon, ActivityIcon, TrendingUpIcon, SchemeIcon } from "../../components/Icons";

export function AdminReferralAnalyticsScreen() {
  const [trends, setTrends] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiClient.getReferralAnalytics();
        setTrends(res);
      } catch (err) {
        console.error(err);
      }
    };
    load();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <h2 style={{ margin: "0 0 8px", fontSize: 18, fontWeight: 700 }}>Facility Referral & Response Analytics</h2>
        <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
          Anonymized performance and doctor review turnaround across Kalyanpur block facilities.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
        {trends.map((t, i) => (
          <div key={i} style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: "var(--primary)" }}>{t.facility}</div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 14, fontSize: 14 }}>
              <span style={{ color: "var(--urgent)", fontWeight: 600 }}>Urgent Cases:</span>
              <strong>{t.urgent}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 14 }}>
              <span style={{ color: "var(--text-secondary)" }}>Routine Referrals:</span>
              <strong>{t.routine}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 14, borderTop: "1px solid var(--divider)", paddingTop: 8 }}>
              <span>Avg Acknowledgment Time:</span>
              <strong style={{ color: "var(--success)" }}>{t.avg_response_mins} mins</strong>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AdminSchemeAnalyticsScreen() {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiClient.getSchemeAnalytics();
        setData(res);
      } catch (err) {
        console.error(err);
      }
    };
    load();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <h2 style={{ margin: "0 0 8px", fontSize: 18, fontWeight: 700 }}>Government Health Scheme Funnel</h2>
        <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
          Tracking potential beneficiaries identified by AI vs ASHA assistance and benefit disbursement.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {data.map((s, idx) => (
          <div key={idx} style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: "var(--primary)", marginBottom: 12 }}>{s.scheme}</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, textAlign: "center" }}>
              <div style={{ padding: 12, backgroundColor: "var(--primary-light)", borderRadius: 8 }}>
                <div style={{ fontSize: 24, fontWeight: 800, color: "var(--primary-dark)" }}>{s.eligible_identified}</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>Identified by AI</div>
              </div>
              <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)" }}>{s.assisted_by_asha}</div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>Assisted by ASHA</div>
              </div>
              <div style={{ padding: 12, backgroundColor: "var(--success-bg)", borderRadius: 8 }}>
                <div style={{ fontSize: 24, fontWeight: 800, color: "var(--success)" }}>{s.benefits_disbursed}</div>
                <div style={{ fontSize: 12, color: "var(--success)", fontWeight: 600, marginTop: 2 }}>Benefits Disbursed</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AdminSystemHealthScreen() {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiClient.getSystemHealth();
        setHealth(res);
      } catch (err) {
        console.error(err);
      }
    };
    load();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <h2 style={{ margin: "0 0 8px", fontSize: 18, fontWeight: 700 }}>Integration Diagnostics & Service Health</h2>
        <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
          Operational status of microservices, AI orchestrators, vector stores, and government sandboxes.
        </p>
      </div>

      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
          <span style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "var(--success)" }} />
          <span style={{ fontSize: 16, fontWeight: 700, color: "var(--success)" }}>Overall Platform Status: HEALTHY</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14 }}>
          {health?.services && Object.entries(health.services).map(([svc, mode]) => (
            <div key={svc} style={{ padding: 14, backgroundColor: "var(--neutral-bg)", borderRadius: 8, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>{svc.replace(/_/g, " ")}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                Mode: <strong style={{ color: "var(--primary)" }}>{String(mode).toUpperCase()}</strong>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
