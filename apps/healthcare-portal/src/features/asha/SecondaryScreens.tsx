import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PeopleIcon, SearchIcon, CheckCircleIcon, ChevronRightIcon } from "../../components/Icons";
import { db } from "../../db/offlineDb";
import { ashaSyncService } from "../../services/AshaSyncService";
import { ConflictResolutionModal } from "./ConflictResolutionModal";

export function AshaPeopleScreen() {
  const navigate = useNavigate();
  const [people, setPeople] = useState<any[]>([]);
  const [search, setSearch] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiClient.request<any[]>("/asha/people");
        setPeople(res || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filteredPeople = people.filter((p) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      p.name?.toLowerCase().includes(s) ||
      p.village?.toLowerCase().includes(s) ||
      p.phone?.includes(s) ||
      p.abha?.includes(s)
    );
  });

  const maskPhone = (phone: string) => {
    if (!phone) return "";
    return phone.length >= 10 ? `******${phone.slice(-4)}` : phone;
  };

  const maskAbha = (abha: string) => {
    if (!abha) return "";
    return abha.length >= 14 ? `${abha.slice(0, 4)}-****-****-${abha.slice(-4)}` : abha;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header Banner */}
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h2 style={{ margin: "0 0 8px", fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}>
            👥 Kalyanpur Village Beneficiary Directory
          </h2>
          <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
            Registered citizens, maternal tracking, and linked ABHA identifiers under your ASHA care area. Click any card to view detailed patient profile & longitudinal workspace.
          </p>
        </div>
        <button
          onClick={() => navigate("/asha/patients/new")}
          style={{
            padding: "10px 18px",
            borderRadius: 8,
            backgroundColor: "var(--primary)",
            color: "#FFF",
            border: "none",
            fontSize: 14,
            fontWeight: 700,
            cursor: "pointer",
          }}
        >
          + Add New Beneficiary
        </button>
      </div>

      {/* Search Input */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, backgroundColor: "var(--surface)", padding: "10px 16px", borderRadius: 10, border: "1px solid var(--border)" }}>
        <SearchIcon size={18} color="var(--text-secondary)" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search beneficiaries by name, village, phone, or ABHA..."
          style={{ border: "none", outline: "none", width: "100%", fontSize: 14, backgroundColor: "transparent", color: "var(--text-primary)" }}
        />
      </div>

      {/* Beneficiary Grid */}
      {loading ? (
        <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>Loading beneficiaries...</div>
      ) : filteredPeople.length === 0 ? (
        <div style={{ padding: 40, textAlign: "center", backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
          No beneficiaries match your search criteria.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16 }}>
          {filteredPeople.map((p) => {
            const targetCaseId = p.latest_case_id || `citizen-${p.id}`;
            return (
              <div
                key={p.id}
                onClick={() => navigate(`/asha/cases/${targetCaseId}`)}
                style={{
                  backgroundColor: "var(--surface)",
                  padding: 20,
                  borderRadius: 12,
                  border: p.is_pregnant ? "1px solid #F8BBD0" : "1px solid var(--border)",
                  cursor: "pointer",
                  transition: "transform 150ms ease, box-shadow 150ms ease",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  gap: 12,
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                    <div>
                      <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)" }}>{p.name}</div>
                      <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
                        Age: {p.age}y · {p.sex || "Female"} · Phone: {maskPhone(p.phone)}
                      </div>
                    </div>
                    {p.is_pregnant && (
                      <span style={{ padding: "4px 10px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                        Pregnant ({p.gestational_weeks ? `${p.gestational_weeks}w` : "7m"})
                      </span>
                    )}
                  </div>

                  <div style={{ fontSize: 12, color: "var(--text-secondary)", padding: "10px 12px", backgroundColor: "var(--neutral-bg)", borderRadius: 8, marginTop: 8, display: "flex", flexDirection: "column", gap: 4 }}>
                    <div><strong>ABHA ID:</strong> {maskAbha(p.abha)}</div>
                    <div><strong>Village / Ward:</strong> {p.village || "Kalyanpur"}</div>
                    <div><strong>Active Cases:</strong> {p.active_cases_count || 1} registered case(s)</div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 8, borderTop: "1px dashed var(--border)" }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: "var(--primary)" }}>
                    Open Patient Detailed View
                  </span>
                  <ChevronRightIcon size={16} color="var(--primary)" />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export { AshaSchemesScreen } from "./AshaSchemesScreen";

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
