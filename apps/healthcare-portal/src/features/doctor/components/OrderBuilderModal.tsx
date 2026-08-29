import React, { useState } from "react";

export interface OrderBuilderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (orderData: any) => Promise<void>;
  defaultCitizenId?: string;
  defaultCaseId?: string;
  defaultConsultationId?: string;
}

const TEST_CATALOG = [
  { name: "Complete Blood Count", code: "CBC", category: "HEMATOLOGY", specimen: "Whole Blood (EDTA)", prep: "Non-fasting sample acceptable" },
  { name: "Hemoglobin", code: "HGB", category: "HEMATOLOGY", specimen: "Capillary / Venous Blood", prep: "Standard preparation" },
  { name: "Blood Glucose", code: "GLUCOSE", category: "BIOCHEMISTRY", specimen: "Venous Blood / Plasma", prep: "10-12 hours overnight fasting" },
  { name: "HbA1c", code: "HBA1C", category: "BIOCHEMISTRY", specimen: "Venous Whole Blood", prep: "Fasting or non-fasting" },
  { name: "Urine Routine", code: "URINE_ROUTINE", category: "BIOCHEMISTRY", specimen: "Midstream Urine", prep: "Clean catch midstream sample" },
  { name: "Urine Albumin/Protein", code: "URINE_ALB", category: "BIOCHEMISTRY", specimen: "Midstream Urine", prep: "Clean catch morning sample" },
  { name: "Malaria Rapid Test", code: "MALARIA_RDT", category: "MICROBIOLOGY", specimen: "Capillary Blood", prep: "Immediate testing on symptom fever" },
  { name: "Sputum Test Referral", code: "SPUTUM_AFB", category: "MICROBIOLOGY", specimen: "Sputum Specimen", prep: "Early morning deep cough sputum" },
  { name: "Ultrasound Referral", code: "USG_ANC", category: "RADIOLOGY", specimen: "Imaging Non-specimen", prep: "Full bladder prep as instructed" },
  { name: "ECG Referral", code: "ECG", category: "CARDIOLOGY", specimen: "Electrode Tracing", prep: "Resting supine position" },
];

export const OrderBuilderModal: React.FC<OrderBuilderModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  defaultCitizenId = "",
  defaultCaseId = "",
  defaultConsultationId = "",
}) => {
  const [citizenId, setCitizenId] = useState(defaultCitizenId);
  const [caseId, setCaseId] = useState(defaultCaseId);
  const [consultationId, setConsultationId] = useState(defaultConsultationId);

  const [selectedTestName, setSelectedTestName] = useState(TEST_CATALOG[0].name);
  const [category, setCategory] = useState(TEST_CATALOG[0].category);
  const [priority, setPriority] = useState("ROUTINE");
  const [clinicalReason, setClinicalReason] = useState("");
  const [specimenType, setSpecimenType] = useState(TEST_CATALOG[0].specimen);
  const [prepInstructions, setPrepInstructions] = useState(TEST_CATALOG[0].prep);
  const [collectionLocation, setCollectionLocation] = useState("PHC Kalyanpur Sample Counter");

  const [assignAsha, setAssignAsha] = useState(false);
  const [ashaInstructions, setAshaInstructions] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  if (!isOpen) return null;

  const handleTestSelect = (testName: string) => {
    setSelectedTestName(testName);
    const cat = TEST_CATALOG.find((t) => t.name === testName);
    if (cat) {
      setCategory(cat.category);
      setSpecimenType(cat.specimen);
      setPrepInstructions(cat.prep);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!citizenId.trim() || !caseId.trim()) {
      setErrorMsg("Valid Patient ID and Case ID are required to submit an order.");
      return;
    }
    if (!clinicalReason.trim()) {
      setErrorMsg("Please enter a valid clinical reason for ordering this investigation.");
      return;
    }

    setSubmitting(true);
    setErrorMsg("");
    try {
      const selected = TEST_CATALOG.find((t) => t.name === selectedTestName);
      await onSubmit({
        citizen_id: citizenId.trim(),
        case_id: caseId.trim(),
        consultation_id: consultationId.trim() || undefined,
        test_name: selectedTestName,
        test_code: selected?.code,
        category,
        priority,
        clinical_reason: clinicalReason,
        specimen_type: specimenType,
        preparation_instructions: prepInstructions,
        collection_location: collectionLocation,
        assign_asha_assistance: assignAsha,
        asha_instructions: ashaInstructions || undefined,
      });
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit investigation order.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(15, 23, 42, 0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "Center",
        zIndex: 1000,
        padding: "1rem",
      }}
    >
      <div
        style={{
          background: "var(--modal-bg, #ffffff)",
          borderRadius: "16px",
          width: "100%",
          maxWidth: "650px",
          maxHeight: "90vh",
          overflowY: "auto",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--border, #e2e8f0)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.25rem", fontWeight: 700, color: "var(--text-primary, #0f172a)" }}>
              New Investigation Order Builder
            </h2>
            <div style={{ fontSize: "0.85rem", color: "var(--text-secondary, #64748b)" }}>
              Create a standalone or consultation-linked laboratory order
            </div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: "1.5rem", cursor: "pointer", color: "#64748b" }}>
            &times;
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: "1.5rem", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {errorMsg && (
            <div style={{ padding: "0.75rem 1rem", background: "#fef2f2", color: "#991b1b", border: "1px solid #fca5a5", borderRadius: "8px", fontSize: "0.85rem" }}>
              {errorMsg}
            </div>
          )}

          {/* Identifier Row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Patient ID (citizenId) *</label>
              <input
                type="text"
                value={citizenId}
                onChange={(e) => setCitizenId(e.target.value)}
                placeholder="e.g. CIT-SUNITA-001"
                required
                style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border, #cbd5e1)" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Case ID (caseId) *</label>
              <input
                type="text"
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
                placeholder="e.g. CASE-SUNITA-001"
                required
                style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border, #cbd5e1)" }}
              />
            </div>
          </div>

          {/* Test Selector */}
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Test Catalogue *</label>
            <select
              value={selectedTestName}
              onChange={(e) => handleTestSelect(e.target.value)}
              style={{ width: "100%", padding: "0.6rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border, #cbd5e1)", fontSize: "0.9rem" }}
            >
              {TEST_CATALOG.map((t) => (
                <option key={t.name} value={t.name}>
                  {t.name} ({t.category})
                </option>
              ))}
            </select>
          </div>

          {/* Priority & Category */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Priority</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border, #cbd5e1)" }}
              >
                <option value="ROUTINE">ROUTINE</option>
                <option value="URGENT">URGENT</option>
                <option value="EMERGENCY">EMERGENCY</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Category</label>
              <input
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border, #cbd5e1)" }}
              />
            </div>
          </div>

          {/* Clinical Reason */}
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Clinical Reason *</label>
            <textarea
              rows={2}
              value={clinicalReason}
              onChange={(e) => setClinicalReason(e.target.value)}
              placeholder="e.g. Antenatal anemia screening, evaluation of fatigue & dizziness in 24w pregnancy"
              required
              style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border, #cbd5e1)", fontSize: "0.85rem" }}
            />
          </div>

          {/* Specimen & Instructions */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Specimen Type</label>
              <input
                type="text"
                value={specimenType}
                onChange={(e) => setSpecimenType(e.target.value)}
                style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border, #cbd5e1)" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Collection Location</label>
              <input
                type="text"
                value={collectionLocation}
                onChange={(e) => setCollectionLocation(e.target.value)}
                style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border, #cbd5e1)" }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Preparation / Fasting Instructions</label>
            <input
              type="text"
              value={prepInstructions}
              onChange={(e) => setPrepInstructions(e.target.value)}
              style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border, #cbd5e1)" }}
            />
          </div>

          {/* ASHA Assistance Toggle */}
          <div style={{ padding: "0.75rem", background: "var(--bg-subtle, #f8fafc)", borderRadius: "8px", border: "1px solid var(--border, #e2e8f0)" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 600, cursor: "pointer", fontSize: "0.85rem" }}>
              <input type="checkbox" checked={assignAsha} onChange={(e) => setAssignAsha(e.target.checked)} />
              Assign ASHA Worker Assistance Task
            </label>

            {assignAsha && (
              <div style={{ marginTop: "0.75rem" }}>
                <input
                  type="text"
                  value={ashaInstructions}
                  onChange={(e) => setAshaInstructions(e.target.value)}
                  placeholder="e.g. Assist beneficiary with PHC transportation and explain morning fasting requirements"
                  style={{ width: "100%", padding: "0.5rem 0.75rem", borderRadius: "6px", border: "1px solid var(--border, #cbd5e1)", fontSize: "0.85rem" }}
                />
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1rem" }}>
            <button
              type="button"
              onClick={onClose}
              style={{ padding: "0.5rem 1rem", borderRadius: "6px", border: "1px solid var(--border, #cbd5e1)", background: "none", cursor: "pointer" }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              style={{
                padding: "0.5rem 1.25rem",
                borderRadius: "6px",
                border: "none",
                background: "#0284c7",
                color: "#ffffff",
                fontWeight: 600,
                cursor: submitting ? "not-allowed" : "pointer",
              }}
            >
              {submitting ? "Submitting..." : "Submit Order"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
