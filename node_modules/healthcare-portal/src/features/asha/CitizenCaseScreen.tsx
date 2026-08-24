import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import { WarningIcon, CheckCircleIcon, VisitIcon, HospitalIcon, StethoscopeIcon } from "../../components/Icons";
import { db } from "../../db/offlineDb";

export function AshaCitizenCaseScreen() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAcknowledging, setIsAcknowledging] = useState(false);

  const fetchCase = async () => {
    if (!caseId) return;
    try {
      const [res, tRes] = await Promise.all([
        apiClient.getAshaCase(caseId),
        apiClient.getCaseTimeline(caseId).catch(() => []),
      ]);
      setCaseData(res);
      setTimeline(tRes || []);
      await db.cachedCases.put({
        id: res.id,
        reference: res.reference,
        priority: res.priority,
        status: res.status,
        primary_concern: res.primary_concern,
        citizen_name: res.citizen_name,
        citizen_age: res.citizen_age,
        citizen_phone: res.citizen_phone,
        village_name: res.village_name,
        is_pregnant: res.is_pregnant,
        gestational_weeks: res.gestational_weeks,
        safety_rule_triggered: res.safety_rule_triggered,
        safety_rule_reason: res.safety_rule_reason,
        symptoms: res.symptoms || [],
        vitals: res.vitals || [],
        created_at: res.created_at
      });
    } catch (err) {
      console.error("Failed to load case online, trying offline...", err);
      const cached = await db.cachedCases.get(caseId);
      if (cached) {
        setCaseData(cached);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCase();
  }, [caseId]);

  const handleAcknowledge = async () => {
    if (!caseId) return;
    setIsAcknowledging(true);
    try {
      await apiClient.acknowledgeAshaCase(caseId);
      await fetchCase();
    } catch (err) {
      console.error("Failed to acknowledge case", err);
    } finally {
      setIsAcknowledging(false);
    }
  };

  if (loading || !caseData) {
    return <div style={{ padding: "40px 0", textAlign: "center" }}>Loading case details...</div>;
  }

  const isUrgent = caseData.priority === "URGENT";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Top Banner / Actions Bar */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          padding: 24,
          borderRadius: 12,
          border: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: "var(--text-primary)" }}>
              {caseData.citizen_name}
            </h1>
            <PriorityBadge priority={caseData.priority} />
            <StatusBadge status={caseData.status} />
          </div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            Case Ref: <strong>{caseData.reference}</strong> · Village: {caseData.village_name} · Age: {caseData.citizen_age}
            {caseData.is_pregnant && (
              <span style={{ color: "#C2185B", fontWeight: 700, marginLeft: 8 }}>
                · Pregnant ({caseData.gestational_weeks ? `${caseData.gestational_weeks} weeks` : "7 months"})
              </span>
            )}
          </div>
        </div>

        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          {caseData.status === "NEW" && (
            <button
              onClick={handleAcknowledge}
              disabled={isAcknowledging}
              style={{
                padding: "10px 20px",
                backgroundColor: "var(--primary)",
                color: "#FFF",
                borderRadius: 8,
                border: "none",
                fontSize: 14,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {isAcknowledging ? "Acknowledging..." : "✓ Acknowledge Case"}
            </button>
          )}

          {caseData.status === "ASHA_ACKNOWLEDGED" && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: 8, backgroundColor: "var(--neutral-bg)", borderRadius: 8, border: "1px solid var(--border)" }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>Record Call:</span>
              <button
                onClick={async () => {
                  try {
                    await apiClient.request(`/asha/cases/${caseData.id}/contact-result`, {
                      method: "POST",
                      body: JSON.stringify({ outcome: "SPOKE_TO_CITIZEN", next_action: "PLAN_VISIT", notes: "ASHA Worker spoke to citizen via phone." })
                    });
                    await fetchCase();
                  } catch (err) {
                    console.error("Failed to save contact result", err);
                  }
                }}
                style={{ padding: "6px 12px", backgroundColor: "var(--primary)", color: "#FFF", border: "none", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer" }}
              >
                📞 Spoke to Citizen
              </button>
              <button
                onClick={async () => {
                  try {
                    await apiClient.request(`/asha/cases/${caseData.id}/contact-result`, {
                      method: "POST",
                      body: JSON.stringify({ outcome: "CITIZEN_UNREACHABLE", next_action: "RESCHEDULE", notes: "Citizen phone went unanswered." })
                    });
                    await fetchCase();
                  } catch (err) {
                    console.error("Failed to save contact result", err);
                  }
                }}
                style={{ padding: "6px 12px", backgroundColor: "#E53E3E", color: "#FFF", border: "none", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer" }}
              >
                🚫 Unreachable
              </button>
            </div>
          )}

          <button
            onClick={() => navigate(`/asha/visit?caseId=${caseData.id}`)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 20px",
              backgroundColor: "var(--teal)",
              color: "#FFF",
              borderRadius: 8,
              border: "none",
              fontSize: 14,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            <VisitIcon size={18} color="#FFF" />
            <span>Start Field Visit</span>
          </button>
        </div>
      </div>

      {/* Deterministic Safety Trigger Alert */}
      {caseData.safety_rule_triggered && (
        <div
          style={{
            backgroundColor: "var(--urgent-bg)",
            border: "1px solid #F5C6CB",
            borderRadius: 12,
            padding: 20,
            display: "flex",
            alignItems: "flex-start",
            gap: 16,
          }}
        >
          <WarningIcon size={24} color="var(--urgent)" />
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "var(--urgent)", marginBottom: 4 }}>
              Deterministic Clinical Red Flag Triggered
            </div>
            <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: "22px" }}>
              {caseData.safety_rule_reason}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 6 }}>
              Rule Policy: Pregnancy + Elevated BP + Visual/Cerebral symptoms $\rightarrow$ Immediate PHC referral advised.
            </div>
          </div>
        </div>
      )}

      {/* Grid: Citizen Reported vs Vitals Recorded */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Citizen Voice Concern */}
        <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
          <h2 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
            🗣 Citizen Spoken Concern & Symptoms
          </h2>
          <div
            style={{
              padding: 14,
              backgroundColor: "var(--neutral-bg)",
              borderRadius: 8,
              fontSize: 14,
              fontStyle: "italic",
              color: "var(--text-primary)",
              marginBottom: 16,
              lineHeight: "22px",
            }}
          >
            "{caseData.primary_concern}"
          </div>

          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>
            Extracted Symptoms:
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {caseData.symptoms?.map((s: any, idx: number) => (
              <span
                key={idx}
                style={{
                  padding: "6px 12px",
                  borderRadius: 6,
                  backgroundColor: "var(--primary-light)",
                  color: "var(--primary-dark)",
                  fontSize: 13,
                  fontWeight: 600,
                }}
              >
                {s.term}
              </span>
            ))}
          </div>
        </div>

        {/* Vitals Record */}
        <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
          <h2 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
            🩺 Recorded Vital Signs
          </h2>
          {caseData.vitals && caseData.vitals.length > 0 ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div style={{ padding: 12, backgroundColor: "var(--urgent-bg)", borderRadius: 8, border: "1px solid #F5C6CB" }}>
                <div style={{ fontSize: 12, color: "var(--urgent)", fontWeight: 600 }}>Blood Pressure (BP)</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "var(--urgent)", marginTop: 2 }}>
                  {caseData.vitals[0].systolic_bp}/{caseData.vitals[0].diastolic_bp}
                  <span style={{ fontSize: 12, fontWeight: 500, marginLeft: 4 }}>mmHg</span>
                </div>
              </div>

              <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>SpO₂ Level</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                  {caseData.vitals[0].spo2 || 97}%
                </div>
              </div>

              <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>Pulse Rate</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                  {caseData.vitals[0].pulse || 88} <span style={{ fontSize: 12, fontWeight: 500 }}>bpm</span>
                </div>
              </div>

              <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 600 }}>Temperature</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                  {caseData.vitals[0].temperature_c || 37.0}°C
                </div>
              </div>
            </div>
          ) : (
            <div style={{ color: "var(--text-secondary)", fontSize: 14 }}>
              No vitals recorded yet. Please record vitals during field visit.
            </div>
          )}
        </div>
      </div>

      {/* Case Timeline / Clinical Audit Trail */}
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <h2 style={{ margin: "0 0 16px", fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
          🕒 Longitudinal Case Timeline & Audit History
        </h2>

        {timeline.length === 0 ? (
          <div style={{ color: "var(--text-secondary)", fontSize: 13 }}>Timeline events are being compiled...</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16, position: "relative", paddingLeft: 20 }}>
            <div style={{ position: "absolute", left: 7, top: 8, bottom: 8, width: 2, backgroundColor: "var(--border)" }} />
            {timeline.map((evt, idx) => (
              <div key={evt.id || idx} style={{ position: "relative", display: "flex", flexDirection: "column", gap: 4 }}>
                <div
                  style={{
                    position: "absolute",
                    left: -19,
                    top: 4,
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    backgroundColor: evt.badge_type === "danger" ? "var(--urgent)" : evt.badge_type === "success" ? "var(--success)" : "var(--primary)",
                    border: "2px solid var(--surface)",
                  }}
                />
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>{evt.title}</span>
                  <span
                    style={{
                      padding: "2px 8px",
                      borderRadius: 6,
                      fontSize: 10,
                      fontWeight: 700,
                      backgroundColor: "var(--primary-light)",
                      color: "var(--primary-dark)",
                    }}
                  >
                    {evt.actor_role}
                  </span>
                  <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                    {new Date(evt.timestamp).toLocaleString()}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: "18px" }}>
                  {evt.description}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
