import React, { useEffect, useState } from "react";
import { apiClient } from "@aarogya/api-client";
import { PeopleIcon, SearchIcon, CheckCircleIcon } from "../../components/Icons";
import { db } from "../../db/offlineDb";
import { ashaSyncService } from "../../services/AshaSyncService";
import { ConflictResolutionModal } from "./ConflictResolutionModal";

export function AshaPeopleScreen() {
  const [people, setPeople] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiClient.request<any[]>("/asha/people");
        setPeople(res);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <h2 style={{ margin: "0 0 8px", fontSize: 18, fontWeight: 700 }}>Kalyanpur Village Beneficiary Directory</h2>
        <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
          Registered citizens, maternal tracking, and linked ABHA identifiers under ASHA care.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
        {people.map((p) => (
          <div key={p.id} style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
              <div>
                <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>{p.name}</div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
                  Age: {p.age} · Phone: {p.phone}
                </div>
              </div>
              {p.is_pregnant && (
                <span style={{ padding: "3px 8px", borderRadius: 10, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                  Pregnant ({p.gestational_weeks ? `${p.gestational_weeks}w` : "7m"})
                </span>
              )}
            </div>

            <div style={{ fontSize: 12, color: "var(--text-secondary)", padding: "8px 12px", backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
              ABHA: {p.abha} · Village: {p.village}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AshaSchemesScreen() {
  const schemes = [
    {
      code: "JSY",
      name: "Janani Suraksha Yojana (JSY)",
      benefit: "₹1,400 Direct Benefit Transfer for institutional delivery + free PHC transport",
      target: "Pregnant women in rural areas",
      docs: ["Aadhaar Card", "MCP Card (Mother & Child Protection)", "Bank Account Passbook"],
      portal: "https://nhm.gov.in",
    },
    {
      code: "PM-JAY",
      name: "Ayushman Bharat PM-JAY",
      benefit: "Cashless coverage up to ₹5,00,000 per family per year for secondary/tertiary care",
      target: "Eligible rural households",
      docs: ["Ration Card", "Aadhaar Card", "ABHA Health Account"],
      portal: "https://pmjay.gov.in",
    },
    {
      code: "MJPJAY",
      name: "Mahatma Jyotirao Phule Jan Arogya Yojana",
      benefit: "State government cashless coverage for 996 medical & surgical packages",
      target: "Maharashtra state residents",
      docs: ["Yellow/Orange Ration Card", "Aadhaar / Voter ID"],
      portal: "https://www.jeevandayee.gov.in",
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <h2 style={{ margin: "0 0 8px", fontSize: 18, fontWeight: 700 }}>Government Health Schemes & Eligibility</h2>
        <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
          Guide rural citizens to applicable central and state welfare benefits.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {schemes.map((s) => (
          <div key={s.code} style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: "var(--primary)" }}>{s.name}</h3>
              <span style={{ padding: "4px 10px", borderRadius: 6, backgroundColor: "var(--success-bg)", color: "var(--success)", fontSize: 12, fontWeight: 700 }}>
                Active Scheme
              </span>
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginBottom: 8 }}>
              Benefit: {s.benefit}
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12 }}>
              Target Group: {s.target}
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
              Required Verification Documents:
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {s.docs.map((d, i) => (
                <span key={i} style={{ padding: "4px 10px", borderRadius: 6, backgroundColor: "var(--neutral-bg)", fontSize: 12, color: "var(--text-primary)" }}>
                  📄 {d}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AshaOfflineScreen() {
  const [pendingActions, setPendingActions] = useState<any[]>([]);
  const [conflicts, setConflicts] = useState<any[]>([]);
  const [selectedConflict, setSelectedConflict] = useState<any | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);

  const loadData = async () => {
    try {
      const actions = await db.pendingActions.toArray();
      const conList = await db.conflicts.filter(c => !c.resolved).toArray();
      setPendingActions(actions);
      setConflicts(conList);
    } catch (e) {
      console.error("Failed to load offline records", e);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleManualSync = async () => {
    setIsSyncing(true);
    try {
      await ashaSyncService.syncPendingActions();
      await loadData();
    } finally {
      setIsSyncing(false);
    }
  };

  const handleResolveConflict = async (conflictId: string, resolution: string) => {
    try {
      await db.conflicts.update(conflictId, { resolved: true });
      setSelectedConflict(null);
      await loadData();
    } catch (err) {
      console.error("Error resolving conflict", err);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <h2 style={{ margin: "0 0 8px", fontSize: 18, fontWeight: 700 }}>Offline Queue & IndexedDB Sync</h2>
        <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
          Local drafts, queued visits, and clinical conflict management during low or zero network connectivity.
        </p>
      </div>

      {conflicts.length > 0 && (
        <div style={{ backgroundColor: "var(--urgent-bg)", border: "1px solid #F5C6CB", borderRadius: 12, padding: 20 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: "var(--urgent)", marginBottom: 8 }}>
            ⚠️ {conflicts.length} Clinical Conflict(s) Require Review
          </div>
          <p style={{ fontSize: 13, color: "var(--text-primary)", marginBottom: 16 }}>
            The following records could not be auto-merged because server clinical data was finalized by a doctor.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {conflicts.map(c => (
              <div key={c.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", backgroundColor: "var(--surface)", padding: 14, borderRadius: 8, border: "1px solid var(--border)" }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>Case: {c.caseId} ({c.actionType})</div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Reason: {c.conflictReason}</div>
                </div>
                <button
                  onClick={() => setSelectedConflict(c)}
                  style={{ padding: "6px 14px", backgroundColor: "var(--primary)", color: "#FFF", borderRadius: 6, border: "none", fontSize: 12, fontWeight: 700, cursor: "pointer" }}
                >
                  Resolve Conflict
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ padding: 24, backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Pending & Retryable Queue ({pendingActions.length})</h3>
          <button
            onClick={handleManualSync}
            disabled={isSyncing}
            style={{
              padding: "8px 16px",
              backgroundColor: "var(--primary)",
              color: "#FFF",
              borderRadius: 8,
              border: "none",
              fontSize: 13,
              fontWeight: 700,
              cursor: isSyncing ? "not-allowed" : "pointer",
            }}
          >
            {isSyncing ? "Syncing..." : "Sync Pending Records"}
          </button>
        </div>

        {pendingActions.length === 0 ? (
          <div style={{ textAlign: "center", padding: "20px 0", color: "var(--success)" }}>
            <div style={{ fontSize: 15, fontWeight: 700 }}>✓ All Local Records Synchronized</div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>No unsynced offline records on this device.</div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {pendingActions.map(a => (
              <div key={a.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700 }}>{a.type} — Case {a.caseId}</div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Status: {a.status} · Retries: {a.retryCount} · Created: {new Date(a.createdAt).toLocaleTimeString()}</div>
                </div>
                <span style={{ fontSize: 12, fontWeight: 700, color: a.status === 'SYNCHRONIZED' ? 'var(--success)' : a.status === 'CONFLICT_REQUIRES_REVIEW' ? 'var(--urgent)' : 'var(--warning)' }}>
                  {a.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <ConflictResolutionModal
        isOpen={!!selectedConflict}
        conflict={selectedConflict}
        onResolve={handleResolveConflict}
        onClose={() => setSelectedConflict(null)}
      />
    </div>
  );
}

export function AshaNotificationsScreen() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
        <h2 style={{ margin: "0 0 4px", fontSize: 18, fontWeight: 700 }}>Notifications & Alerts</h2>
        <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>Real-time case assignments and clinical updates</p>
      </div>

      <div style={{ backgroundColor: "var(--urgent-bg)", padding: 16, borderRadius: 10, border: "1px solid #F5C6CB", display: "flex", gap: 12 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: "var(--urgent)" }}>🚨 Urgent Case Alert: CASE-2026-001</div>
        <div style={{ fontSize: 13, color: "var(--text-primary)" }}>
          Maternal warning signs detected for Sunita Devi. Please conduct field visit immediately.
        </div>
      </div>
    </div>
  );
}
