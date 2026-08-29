import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { doctorRoutes } from "./doctorRoutes";

export function DoctorAlertDetailScreen() {
  const { alertId } = useParams<{ alertId: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [alert, setAlert] = useState<any>(null);

  // Form states for status transitions
  const [showSnoozeModal, setShowSnoozeModal] = useState(false);
  const [snoozeHours, setSnoozeHours] = useState(4);
  const [snoozeReason, setSnoozeReason] = useState("");

  const [showResolveModal, setShowResolveModal] = useState(false);
  const [resolutionNote, setResolutionNote] = useState("");

  const [showDismissModal, setShowDismissModal] = useState(false);
  const [dismissalReason, setDismissalReason] = useState("");

  const [phoneRevealed, setPhoneRevealed] = useState<string | null>(null);

  const loadAlertDetail = async () => {
    if (!alertId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getDoctorAlert(alertId);
      const data = res?.data || res;
      setAlert(data);
      if (data.citizen_phone && !data.citizen_phone.includes("XXXXXX")) {
        setPhoneRevealed(data.citizen_phone);
      }
    } catch (err: any) {
      console.error("Failed to load alert detail:", err);
      setError(err?.message || "Failed to load alert detail.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlertDetail();
  }, [alertId]);

  const handleAcknowledge = async () => {
    try {
      const res = await apiClient.acknowledgeDoctorAlert(alert.id);
      setAlert(res?.data || res);
    } catch (err) {
      console.error("Failed to acknowledge alert", err);
    }
  };

  const handleSnooze = async () => {
    try {
      const res = await apiClient.snoozeDoctorAlert(alert.id, snoozeHours, snoozeReason);
      setAlert(res?.data || res);
      setShowSnoozeModal(false);
    } catch (err) {
      console.error("Failed to snooze alert", err);
    }
  };

  const handleResolve = async () => {
    if (!resolutionNote) return;
    try {
      const res = await apiClient.resolveDoctorAlert(alert.id, resolutionNote);
      setAlert(res?.data || res);
      setShowResolveModal(false);
    } catch (err) {
      console.error("Failed to resolve alert", err);
    }
  };

  const handleDismiss = async () => {
    if (alert.severity === "CRITICAL" && !dismissalReason) return;
    try {
      const res = await apiClient.dismissDoctorAlert(alert.id, dismissalReason);
      setAlert(res?.data || res);
      setShowDismissModal(false);
    } catch (err: any) {
      alert(err?.message || "Failed to dismiss alert.");
    }
  };

  const handleRevealPhone = async () => {
    try {
      const res = await apiClient.revealDoctorAlertPhone(alert.id);
      const data = res?.data || res;
      setPhoneRevealed(data.citizen_phone);
    } catch (err) {
      console.error("Failed to reveal phone", err);
    }
  };

  const getPrimaryActionRoute = () => {
    if (!alert) return "/doctor/alerts";
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

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
        Loading clinical alert detail...
      </div>
    );
  }

  if (error || !alert) {
    return (
      <div style={{ padding: 30, backgroundColor: "#FEF2F2", borderRadius: 8, border: "1px solid #FCA5A5", margin: "20px auto", maxWidth: 800 }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: "#991B1B" }}>Error Loading Alert Detail</div>
        <div style={{ fontSize: 13, color: "#B91C1C", marginTop: 4, marginBottom: 12 }}>{error || "Alert not found."}</div>
        <button onClick={() => navigate("/doctor/alerts")} style={{ padding: "6px 14px", backgroundColor: "#991B1B", color: "#FFF", borderRadius: 6, border: "none", fontWeight: 700, cursor: "pointer" }}>
          Return to Alerts Workspace
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 1000, margin: "0 auto", width: "100%" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <button
          onClick={() => navigate("/doctor/alerts")}
          style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)", backgroundColor: "var(--surface)", fontSize: 12, fontWeight: 700, cursor: "pointer" }}
        >
          ← Back to Alerts List
        </button>
        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)" }}>
          Ref: {alert.alert_reference} · Status: <strong>{alert.status}</strong>
        </span>
      </div>

      {/* Main Alert Detail Card */}
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: alert.severity === "CRITICAL" ? "2px solid #EF4444" : "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
          <div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 800, backgroundColor: alert.severity === "CRITICAL" ? "#DC2626" : alert.severity === "URGENT" ? "#EA580C" : "#0284C7", color: "#FFF" }}>
                {alert.severity}
              </span>
              <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)" }}>
                {alert.category}
              </span>
            </div>
            <h1 style={{ margin: "8px 0 0", fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>{alert.title}</h1>
          </div>

          <div style={{ textAlign: "right", fontSize: 12, color: "var(--text-secondary)" }}>
            <div>Created: {new Date(alert.created_at).toLocaleString()}</div>
            {alert.response_due_at && <div>Deadline: {new Date(alert.response_due_at).toLocaleString()}</div>}
          </div>
        </div>

        <div style={{ fontSize: 14, color: "var(--text-primary)", backgroundColor: "var(--neutral-bg)", padding: 16, borderRadius: 8, border: "1px solid var(--border)" }}>
          <strong>Safe Clinical Summary:</strong> {alert.safe_summary}
        </div>

        {/* Patient & Case Context */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, backgroundColor: "#F8FAFC", padding: 16, borderRadius: 8, border: "1px solid var(--border)" }}>
          <div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 700 }}>PATIENT</div>
            <div style={{ fontSize: 14, fontWeight: 700, marginTop: 2 }}>{alert.citizen_name}</div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Age: {alert.citizen_age || "N/A"} · {alert.village_name}</div>
          </div>

          <div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 700 }}>CASE REFERENCE</div>
            <div style={{ fontSize: 14, fontWeight: 700, marginTop: 2 }}>{alert.case_reference || "N/A"}</div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Source: {alert.source_entity_type} ({alert.source_entity_id})</div>
          </div>

          <div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 700 }}>CONTACT PATIENT</div>
            {phoneRevealed ? (
              <div style={{ fontSize: 14, fontWeight: 800, color: "#15803D", marginTop: 2 }}>📞 {phoneRevealed}</div>
            ) : (
              <button
                onClick={handleRevealPhone}
                style={{ marginTop: 4, padding: "4px 10px", backgroundColor: "#F0FDF4", color: "#166534", border: "1px solid #BBF7D0", borderRadius: 6, fontSize: 12, fontWeight: 700, cursor: "pointer" }}
              >
                Reveal Phone Number
              </button>
            )}
          </div>
        </div>

        {/* Action Trigger Buttons */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
          <button
            onClick={() => navigate(getPrimaryActionRoute())}
            style={{ padding: "8px 16px", backgroundColor: "var(--primary)", color: "#FFF", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 700, cursor: "pointer" }}
          >
            Open Primary Source Action →
          </button>

          {alert.case_id && (
            <button
              onClick={() => navigate(doctorRoutes.timeline(alert.case_id))}
              style={{ padding: "8px 14px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer" }}
            >
              View Case Timeline
            </button>
          )}

          {alert.status !== "ACKNOWLEDGED" && alert.status !== "RESOLVED" && (
            <button
              onClick={handleAcknowledge}
              style={{ padding: "8px 14px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer" }}
            >
              Acknowledge Alert
            </button>
          )}

          {alert.status !== "RESOLVED" && (
            <button
              onClick={() => setShowSnoozeModal(true)}
              style={{ padding: "8px 14px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer" }}
            >
              Snooze Alert
            </button>
          )}

          {alert.status !== "RESOLVED" && (
            <button
              onClick={() => setShowResolveModal(true)}
              style={{ padding: "8px 16px", backgroundColor: "#16A34A", color: "#FFF", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 700, cursor: "pointer" }}
            >
              Resolve Alert
            </button>
          )}

          {alert.status !== "RESOLVED" && alert.status !== "DISMISSED" && (
            <button
              onClick={() => setShowDismissModal(true)}
              style={{ padding: "8px 14px", backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "#DC2626", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer" }}
            >
              Dismiss Alert
            </button>
          )}
        </div>

        {/* Audit History */}
        {alert.actions_history?.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <h4 style={{ margin: "0 0 10px", fontSize: 14, fontWeight: 700 }}>Alert Lifecycle Audit Log</h4>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {alert.actions_history.map((act: any) => (
                <div key={act.id} style={{ padding: 10, borderRadius: 6, backgroundColor: "var(--neutral-bg)", fontSize: 12, display: "flex", justifyContent: "space-between" }}>
                  <div>
                    <strong>{act.action}</strong> ({act.actor_role}) · {act.note || "No note provided"}
                  </div>
                  <span style={{ color: "var(--text-secondary)" }}>
                    {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Snooze Modal */}
      {showSnoozeModal && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, maxWidth: 400, width: "90%", display: "flex", flexDirection: "column", gap: 14 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Snooze Alert</h3>
            <div>
              <label style={{ fontSize: 12, fontWeight: 700 }}>Snooze Duration (Hours):</label>
              <select value={snoozeHours} onChange={(e) => setSnoozeHours(Number(e.target.value))} style={{ width: "100%", padding: 8, marginTop: 4, borderRadius: 6, border: "1px solid var(--border)" }}>
                <option value={1}>1 Hour</option>
                <option value={4}>4 Hours</option>
                <option value={8}>8 Hours</option>
                <option value={24}>24 Hours</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: 12, fontWeight: 700 }}>Snooze Reason:</label>
              <input type="text" value={snoozeReason} onChange={(e) => setSnoozeReason(e.target.value)} placeholder="e.g. Patient arriving in afternoon" style={{ width: "100%", padding: 8, marginTop: 4, borderRadius: 6, border: "1px solid var(--border)" }} />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button onClick={() => setShowSnoozeModal(false)} style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)" }}>Cancel</button>
              <button onClick={handleSnooze} style={{ padding: "6px 14px", borderRadius: 6, border: "none", backgroundColor: "var(--primary)", color: "#FFF", fontWeight: 700 }}>Confirm Snooze</button>
            </div>
          </div>
        </div>
      )}

      {/* Resolve Modal */}
      {showResolveModal && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, maxWidth: 450, width: "90%", display: "flex", flexDirection: "column", gap: 14 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Resolve Alert</h3>
            <div>
              <label style={{ fontSize: 12, fontWeight: 700 }}>Resolution Note (Required):</label>
              <textarea value={resolutionNote} onChange={(e) => setResolutionNote(e.target.value)} placeholder="Describe clinical action taken..." style={{ width: "100%", height: 80, padding: 8, marginTop: 4, borderRadius: 6, border: "1px solid var(--border)" }} />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button onClick={() => setShowResolveModal(false)} style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)" }}>Cancel</button>
              <button onClick={handleResolve} disabled={!resolutionNote} style={{ padding: "6px 14px", borderRadius: 6, border: "none", backgroundColor: "#16A34A", color: "#FFF", fontWeight: 700, cursor: resolutionNote ? "pointer" : "not-allowed" }}>Confirm Resolve</button>
            </div>
          </div>
        </div>
      )}

      {/* Dismiss Modal */}
      {showDismissModal && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, maxWidth: 450, width: "90%", display: "flex", flexDirection: "column", gap: 14 }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Dismiss Alert</h3>
            <div>
              <label style={{ fontSize: 12, fontWeight: 700 }}>Dismissal Reason {alert.severity === "CRITICAL" ? "(Required for Critical)" : ""}:</label>
              <textarea value={dismissalReason} onChange={(e) => setDismissalReason(e.target.value)} placeholder="Explain why this alert is being dismissed..." style={{ width: "100%", height: 80, padding: 8, marginTop: 4, borderRadius: 6, border: "1px solid var(--border)" }} />
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button onClick={() => setShowDismissModal(false)} style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)" }}>Cancel</button>
              <button onClick={handleDismiss} disabled={alert.severity === "CRITICAL" && !dismissalReason} style={{ padding: "6px 14px", borderRadius: 6, border: "none", backgroundColor: "#DC2626", color: "#FFF", fontWeight: 700 }}>Confirm Dismissal</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
