import React, { useState } from "react";
import { apiClient as api } from "@aarogya/api-client";

interface RequestRecollectionModalProps {
  order: any;
  onClose: () => void;
  onSuccess: (updatedOrder: any) => void;
}

const REASON_OPTIONS = [
  { code: "INSUFFICIENT_SAMPLE", label: "Insufficient Sample Volume" },
  { code: "INCORRECT_CONTAINER", label: "Incorrect Container / Tube" },
  { code: "HEMOLYSED_SAMPLE", label: "Hemolysed or Contaminated Specimen" },
  { code: "LABELLING_MISMATCH", label: "Labelling / Identification Mismatch" },
  { code: "EXPIRED_SAMPLE", label: "Sample Expired / Delay in Processing" },
  { code: "INVALID_RESULT", label: "Result Invalid / Inconclusive" },
  { code: "OTHER", label: "Other Clinical Reason" },
];

export function RequestRecollectionModal({ order, onClose, onSuccess }: RequestRecollectionModalProps) {
  const [reasonCode, setReasonCode] = useState<string>("INSUFFICIENT_SAMPLE");
  const [reasonNote, setReasonNote] = useState<string>("");
  const [priority, setPriority] = useState<string>("HIGH");
  const [dueDate, setDueDate] = useState<string>(
    new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().split("T")[0]
  );
  const [location, setLocation] = useState<string>(
    order?.collection_location || order?.order?.collection_location || "Kalyanpur PHC"
  );
  const [assignAsha, setAssignAsha] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const invId = order?.investigation_id || order?.id;
  const invRef = order?.investigation_reference || order?.reference || "INV-Order";
  const patientName = order?.patient?.name || order?.citizen_name || "Patient";
  const testName = order?.test?.name || order?.test_name || "Diagnostic Test";
  const sampleRef = order?.sample?.sample_reference || "SMP-Pending";
  const currentStatus = order?.status || "ORDERED";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reasonNote.trim()) {
      setErrorMsg("Please provide a detailed clinical note explaining the recollection requirement.");
      return;
    }

    setSaving(true);
    setErrorMsg(null);

    try {
      const res = await api.requestInvestigationRecollection(invId, {
        sample_id: order?.sample?.id || order?.sample_id,
        reason_code: reasonCode,
        reason_note: reasonNote.trim(),
        priority,
        due_at: dueDate ? new Date(dueDate).toISOString() : undefined,
        collection_location: location,
        assign_asha_assistance: assignAsha,
      });

      const updated = res?.data || res;
      onSuccess(updated);
      onClose();
    } catch (err: any) {
      console.error("Recollection request failed:", err);
      const msg = err?.response?.data?.detail?.message || err?.message || "Failed to submit recollection request.";
      setErrorMsg(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.6)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1100,
        padding: "1rem",
      }}
    >
      <div
        style={{
          background: "#ffffff",
          borderRadius: "16px",
          width: "100%",
          maxWidth: "600px",
          maxHeight: "90vh",
          overflowY: "auto",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
          border: "1px solid #e2e8f0",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid #e2e8f0", background: "#f8fafc" }}>
          <h2 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700, color: "#0f172a" }}>
            Request Sample Recollection
          </h2>
          <div style={{ fontSize: "0.85rem", color: "#64748b", marginTop: "0.25rem" }}>
            Order <strong>{invRef}</strong> • Patient: <strong>{patientName}</strong>
          </div>
        </div>

        {/* Content Form */}
        <form onSubmit={handleSubmit} style={{ padding: "1.5rem", display: "flex", flexDirection: "column", gap: "1.2rem" }}>
          {errorMsg && (
            <div style={{ padding: "0.75rem 1rem", borderRadius: "8px", background: "#fef2f2", color: "#991b1b", fontSize: "0.85rem", border: "1px solid #fecaca" }}>
              ⚠️ {errorMsg}
            </div>
          )}

          {/* Context Card */}
          <div style={{ background: "#f1f5f9", borderRadius: "10px", padding: "0.85rem 1rem", fontSize: "0.85rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
            <div><strong>Test Name:</strong> {testName}</div>
            <div><strong>Original Sample Ref:</strong> {sampleRef}</div>
            <div><strong>Current Status:</strong> <span style={{ fontWeight: 600, color: "#b45309" }}>{currentStatus}</span></div>
            <div><strong>Location:</strong> {location}</div>
          </div>

          {/* Reason Selector */}
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.4rem" }}>
              Recollection Reason Code <span style={{ color: "#dc2626" }}>*</span>
            </label>
            <select
              value={reasonCode}
              onChange={(e) => setReasonCode(e.target.value)}
              style={{
                width: "100%",
                padding: "0.6rem 0.8rem",
                borderRadius: "8px",
                border: "1px solid #cbd5e1",
                fontSize: "0.9rem",
                background: "#fff",
              }}
            >
              {REASON_OPTIONS.map((opt) => (
                <option key={opt.code} value={opt.code}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Detailed Note */}
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.4rem" }}>
              Detailed Clinical & Lab Rejection Note <span style={{ color: "#dc2626" }}>*</span>
            </label>
            <textarea
              required
              rows={3}
              value={reasonNote}
              onChange={(e) => setReasonNote(e.target.value)}
              placeholder="e.g. Hemolysed blood sample received. Fresh EDTA tube required for repeat Complete Blood Count."
              style={{
                width: "100%",
                padding: "0.6rem 0.8rem",
                borderRadius: "8px",
                border: "1px solid #cbd5e1",
                fontSize: "0.875rem",
                resize: "vertical",
              }}
            />
          </div>

          {/* Priority & Due Date */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.4rem" }}>
                Recollection Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                style={{ width: "100%", padding: "0.6rem 0.8rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem", background: "#fff" }}
              >
                <option value="URGENT">URGENT</option>
                <option value="HIGH">HIGH</option>
                <option value="ROUTINE">ROUTINE</option>
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.4rem" }}>
                Expected Collection Date
              </label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                style={{ width: "100%", padding: "0.55rem 0.8rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem" }}
              />
            </div>
          </div>

          {/* Collection Location */}
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.4rem" }}>
              Collection Location
            </label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              style={{ width: "100%", padding: "0.6rem 0.8rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem" }}
            />
          </div>

          {/* ASHA Assistance Toggle */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", background: "#eff6ff", padding: "0.75rem 1rem", borderRadius: "8px", border: "1px solid #bfdbfe" }}>
            <input
              type="checkbox"
              id="assignAshaCheck"
              checked={assignAsha}
              onChange={(e) => setAssignAsha(e.target.checked)}
              style={{ width: "18px", height: "18px", accentColor: "#2563eb", cursor: "pointer" }}
            />
            <label htmlFor="assignAshaCheck" style={{ fontSize: "0.85rem", fontWeight: 600, color: "#1e40af", cursor: "pointer" }}>
              Assign ASHA Worker task to assist patient & confirm PHC attendance
            </label>
          </div>

          {/* Citizen Guidance Preview */}
          <div style={{ background: "#faf5ff", border: "1px solid #e9d5ff", borderRadius: "8px", padding: "0.75rem 1rem", fontSize: "0.8rem", color: "#6b21a8" }}>
            ℹ️ <strong>Patient View Preview:</strong> “Another sample is required for {testName}. Please visit {location} by {dueDate || "tomorrow"}.”
          </div>

          {/* Actions */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "0.5rem", paddingTop: "1rem", borderTop: "1px solid #e2e8f0" }}>
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              style={{
                padding: "0.6rem 1.2rem",
                borderRadius: "8px",
                border: "1px solid #cbd5e1",
                background: "#fff",
                color: "#475569",
                fontWeight: 600,
                cursor: saving ? "not-allowed" : "pointer",
                fontSize: "0.875rem",
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              style={{
                padding: "0.6rem 1.4rem",
                borderRadius: "8px",
                border: "none",
                background: saving ? "#94a3b8" : "#dc2626",
                color: "#ffffff",
                fontWeight: 600,
                cursor: saving ? "not-allowed" : "pointer",
                fontSize: "0.875rem",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              {saving ? "Submitting..." : "Submit Recollection Request"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
