import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import { SearchIcon, CheckCircleIcon, ActivityIcon, WarningIcon } from "../../components/Icons";
import { VoiceInputModal } from "../../components/VoiceInputModal";

export function AshaFollowupsScreen() {
  const navigate = useNavigate();
  const [followups, setFollowups] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("ALL");
  const [search, setSearch] = useState<string>("");

  // Modal State for Completing Follow-up
  const [activeFollowup, setActiveFollowup] = useState<any>(null);
  const [systolic, setSystolic] = useState<number>(130);
  const [diastolic, setDiastolic] = useState<number>(85);
  const [spo2, setSpo2] = useState<number>(98);
  const [pulse, setPulse] = useState<number>(76);
  const [medicationAdherent, setMedicationAdherent] = useState(true);
  const [symptomsImproved, setSymptomsImproved] = useState(true);
  const [notes, setNotes] = useState("Home follow-up conducted. Patient taking prescribed medication regularly.");
  const [escalate, setEscalate] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showVoiceModal, setShowVoiceModal] = useState(false);

  const loadFollowups = async () => {
    try {
      const res = await apiClient.getAshaFollowups();
      setFollowups(res || []);
    } catch (err) {
      console.error("Failed to load followups", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFollowups();
    // 5-second polling for live updates
    const interval = setInterval(loadFollowups, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleOpenCompleteModal = (fup: any) => {
    setActiveFollowup(fup);
    setSystolic(130);
    setDiastolic(85);
    setSpo2(98);
    setPulse(76);
    setMedicationAdherent(true);
    setSymptomsImproved(true);
    setNotes("Home follow-up conducted. Patient taking prescribed medication regularly.");
    setEscalate(false);
  };

  const handleSubmitFollowup = async () => {
    if (!activeFollowup) return;
    setIsSubmitting(true);
    try {
      await apiClient.completeAshaFollowup(activeFollowup.id, {
        vitals: {
          systolic_bp: Number(systolic),
          diastolic_bp: Number(diastolic),
          spo2: Number(spo2),
          pulse: Number(pulse),
        },
        medication_adherent: medicationAdherent,
        symptoms_improved: symptomsImproved,
        notes: notes,
        escalate_to_doctor: escalate,
      });
      setActiveFollowup(null);
      await loadFollowups();
    } catch (err) {
      console.error("Failed to complete follow-up", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredFollowups = followups.filter((f) => {
    if (filter === "PENDING" && f.status !== "PENDING") return false;
    if (filter === "COMPLETED" && f.status !== "COMPLETED") return false;
    if (search && !f.citizen_name.toLowerCase().includes(search.toLowerCase()) && !f.case_reference.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    return true;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Top Header */}
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <h2 style={{ margin: "0 0 8px", fontSize: 20, fontWeight: 700 }}>
          👩‍⚕️ Doctor-Assigned Follow-up Tasks
        </h2>
        <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
          Perform home checkups, verify medicine adherence, record repeat vitals, and report outcomes directly to PHC.
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <div
          style={{
            flex: 1,
            minWidth: 260,
            display: "flex",
            alignItems: "center",
            gap: 10,
            backgroundColor: "var(--surface)",
            padding: "0 14px",
            height: 44,
            borderRadius: 8,
            border: "1px solid var(--border)",
          }}
        >
          <SearchIcon size={18} color="var(--text-secondary)" />
          <input
            type="text"
            placeholder="Search patient name or case reference..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ border: "none", outline: "none", width: "100%", fontSize: 14, backgroundColor: "transparent" }}
          />
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          {["ALL", "PENDING", "COMPLETED"].map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border: filter === tab ? "2px solid var(--primary)" : "1px solid var(--border)",
                backgroundColor: filter === tab ? "var(--primary-light)" : "var(--surface)",
                color: filter === tab ? "var(--primary-dark)" : "var(--text-primary)",
                fontWeight: 600,
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              {tab === "ALL" ? "All Follow-ups" : tab === "PENDING" ? "⏳ Pending Review" : "✓ Completed"}
            </button>
          ))}
        </div>
      </div>

      {/* Follow-up List */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: 40, color: "var(--text-secondary)" }}>Loading follow-ups...</div>
        ) : filteredFollowups.length === 0 ? (
          <div style={{ textAlign: "center", padding: 40, backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
            No follow-up assignments found.
          </div>
        ) : (
          filteredFollowups.map((fup) => {
            const isPending = fup.status === "PENDING";
            return (
              <div
                key={fup.id}
                style={{
                  backgroundColor: "var(--surface)",
                  padding: 20,
                  borderRadius: 12,
                  border: isPending ? "1px solid var(--border)" : "1px solid #C6F6D5",
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                      <span style={{ fontSize: 16, fontWeight: 700 }}>{fup.citizen_name}</span>
                      {fup.is_pregnant && (
                        <span style={{ padding: "2px 8px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                          Pregnant
                        </span>
                      )}
                      <PriorityBadge priority={fup.priority} size="sm" />
                      <span
                        style={{
                          padding: "2px 8px",
                          borderRadius: 6,
                          fontSize: 11,
                          fontWeight: 700,
                          backgroundColor: isPending ? "#FEF3C7" : "#DEF7EC",
                          color: isPending ? "#92400E" : "#03543F",
                        }}
                      >
                        {isPending ? "ACTION REQUIRED" : "COMPLETED"}
                      </span>
                    </div>
                    <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                      Case: <strong>{fup.case_reference}</strong> · Village: {fup.village_name} · Due Date: {new Date(fup.due_at).toLocaleDateString()}
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      onClick={() => navigate(`/asha/cases/${fup.case_id}`)}
                      style={{
                        padding: "8px 14px",
                        backgroundColor: "var(--neutral-bg)",
                        border: "1px solid var(--border)",
                        borderRadius: 6,
                        fontSize: 13,
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      View Case Timeline
                    </button>
                    {isPending && (
                      <button
                        onClick={() => handleOpenCompleteModal(fup)}
                        style={{
                          padding: "8px 16px",
                          backgroundColor: "var(--primary)",
                          color: "#FFF",
                          border: "none",
                          borderRadius: 6,
                          fontSize: 13,
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                      >
                        ✓ Complete Follow-up
                      </button>
                    )}
                  </div>
                </div>

                <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8, fontSize: 13, color: "var(--text-primary)" }}>
                  <strong>Doctor's Directive:</strong> {fup.instructions}
                </div>

                {fup.result && (
                  <div style={{ fontSize: 12, color: "var(--success)", fontWeight: 600 }}>
                    Outcome: {fup.result} (Completed on {new Date(fup.completed_at).toLocaleDateString()})
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Complete Follow-up Modal */}
      {activeFollowup && (
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
            zIndex: 999,
            padding: 16,
          }}
        >
          <div
            style={{
              backgroundColor: "var(--surface)",
              width: "100%",
              maxWidth: 580,
              borderRadius: 16,
              padding: 24,
              display: "flex",
              flexDirection: "column",
              gap: 16,
              maxHeight: "90vh",
              overflowY: "auto",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>
                Complete Home Follow-up: {activeFollowup.citizen_name}
              </h3>
              <button
                onClick={() => setActiveFollowup(null)}
                style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "var(--text-secondary)" }}
              >
                ✕
              </button>
            </div>

            <div style={{ padding: 10, backgroundColor: "var(--primary-light)", borderRadius: 8, fontSize: 13, color: "var(--primary-dark)" }}>
              <strong>Doctor Instructions:</strong> {activeFollowup.instructions}
            </div>

            {/* Repeat Vitals Form */}
            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 700, marginBottom: 8 }}>
                Repeat Vital Signs
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 10 }}>
                <div>
                  <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Systolic BP</label>
                  <input
                    type="number"
                    value={systolic}
                    onChange={(e) => setSystolic(Number(e.target.value))}
                    style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", fontWeight: 700 }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Diastolic BP</label>
                  <input
                    type="number"
                    value={diastolic}
                    onChange={(e) => setDiastolic(Number(e.target.value))}
                    style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", fontWeight: 700 }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>SpO₂ (%)</label>
                  <input
                    type="number"
                    value={spo2}
                    onChange={(e) => setSpo2(Number(e.target.value))}
                    style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", fontWeight: 700 }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 11, color: "var(--text-secondary)" }}>Pulse (bpm)</label>
                  <input
                    type="number"
                    value={pulse}
                    onChange={(e) => setPulse(Number(e.target.value))}
                    style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid var(--border)", fontWeight: 700 }}
                  />
                </div>
              </div>
            </div>

            {/* Compliance Checkboxes */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={medicationAdherent}
                  onChange={(e) => setMedicationAdherent(e.target.checked)}
                />
                <span>Patient has taken all prescribed medicines on schedule</span>
              </label>

              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={symptomsImproved}
                  onChange={(e) => setSymptomsImproved(e.target.checked)}
                />
                <span>Patient reports overall improvement in symptoms</span>
              </label>

              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer", color: "var(--urgent)", fontWeight: 600 }}>
                <input
                  type="checkbox"
                  checked={escalate}
                  onChange={(e) => setEscalate(e.target.checked)}
                />
                <span>⚠️ Escalate back to PHC Medical Officer (New Warning Signs Detected)</span>
              </label>
            </div>

            {/* Notes with Voice Option */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 700 }}>ASHA Observations & Advice</label>
                <button
                  type="button"
                  onClick={() => setShowVoiceModal(true)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    padding: "3px 8px",
                    backgroundColor: "var(--primary-light)",
                    color: "var(--primary-dark)",
                    border: "1px solid var(--primary)",
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  🎙 Speak Notes
                </button>
              </div>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
              />
            </div>

            <VoiceInputModal
              isOpen={showVoiceModal}
              onClose={() => setShowVoiceModal(false)}
              preferredLanguage="mr-IN"
              fieldLabel="Follow-up Notes"
              onConfirmText={(text) => setNotes(prev => prev ? `${prev} ${text}` : text)}
            />

            {/* Submission Actions */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                onClick={() => setActiveFollowup(null)}
                style={{ padding: "10px 16px", backgroundColor: "transparent", border: "1px solid var(--border)", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitFollowup}
                disabled={isSubmitting}
                style={{ padding: "10px 20px", backgroundColor: "var(--success)", color: "#FFF", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 700, cursor: "pointer" }}
              >
                {isSubmitting ? "Submitting..." : "Sign & Finalize Follow-up"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
