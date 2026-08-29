import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { doctorRoutes } from "./doctorRoutes";
import { useLanguage } from "../../context/LanguageContext";

export function DoctorPrescriptionDetailScreen() {
  const { t } = useLanguage();
  const { prescriptionId } = useParams<{ prescriptionId: string }>();
  const navigate = useNavigate();

  const [prescription, setPrescription] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [showSignModal, setShowSignModal] = useState(false);
  const [showAmendModal, setShowAmendModal] = useState(false);
  const [showStopModal, setShowStopModal] = useState(false);
  const [selectedItemToStop, setSelectedItemToStop] = useState<any>(null);
  const [showFollowUpModal, setShowFollowUpModal] = useState(false);
  const [showPrintView, setShowPrintView] = useState(false);

  // Form states
  const [amendReasonCode, setAmendReasonCode] = useState("DOSE_ADJUSTED");
  const [amendReasonNote, setAmendReasonNote] = useState("");
  const [stopReason, setStopReason] = useState("ALLERGY_CONCERN");
  const [stopDoctorNote, setStopDoctorNote] = useState("");
  const [stopPatientGuidance, setStopPatientGuidance] = useState("");
  const [followUpInstructions, setFollowUpInstructions] = useState("Verify patient is taking medications as prescribed.");

  const fetchDetail = async () => {
    if (!prescriptionId) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.getDoctorPrescriptionDetail(prescriptionId);
      setPrescription(res);
    } catch (err: any) {
      console.error("Failed to load prescription detail", err);
      setError(err?.message || "Failed to load prescription record.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [prescriptionId]);

  const handleSign = async () => {
    try {
      await apiClient.signPrescription(prescriptionId!, { instructions_reviewed: true }, `KEY-${Date.now()}`);
      setShowSignModal(false);
      fetchDetail();
    } catch (err) {
      console.error("Failed to sign prescription", err);
    }
  };

  const handleAmend = async () => {
    try {
      const currentItems = prescription?.items?.map((it: any) => ({
        generic_name_snapshot: it.generic_name_snapshot,
        brand_name_snapshot: it.brand_name_snapshot,
        formulation: it.formulation,
        strength: it.strength,
        dose: it.dose,
        dose_unit: it.dose_unit,
        route: it.route,
        frequency: it.frequency,
        timing: it.timing,
        duration_value: it.duration_value,
        duration_unit: it.duration_unit,
        quantity: it.quantity,
        instructions: it.instructions,
        indication: it.indication,
        adherence_monitoring_required: it.adherence_monitoring_required
      })) || [];

      const res = await apiClient.amendPrescription(prescriptionId!, {
        reason_code: amendReasonCode,
        reason_note: amendReasonNote,
        items: currentItems
      });
      setShowAmendModal(false);
      navigate(doctorRoutes.prescriptionDetail(res.id));
    } catch (err) {
      console.error("Failed to amend prescription", err);
    }
  };

  const handleStopItem = async () => {
    if (!selectedItemToStop) return;
    try {
      await apiClient.stopPrescriptionItem(prescriptionId!, selectedItemToStop.id, {
        stop_reason: stopReason,
        doctor_note: stopDoctorNote,
        patient_guidance: stopPatientGuidance,
        asha_notification_required: true
      });
      setShowStopModal(false);
      setSelectedItemToStop(null);
      fetchDetail();
    } catch (err) {
      console.error("Failed to stop medication item", err);
    }
  };

  const handleAssignFollowUp = async () => {
    try {
      await apiClient.assignPrescriptionAdherenceFollowup(prescriptionId!, {
        instructions: followUpInstructions,
        due_in_days: 3
      });
      setShowFollowUpModal(false);
      fetchDetail();
    } catch (err) {
      console.error("Failed to create follow-up task", err);
    }
  };

  if (isLoading) {
    return <div style={{ padding: 40, textAlign: "center", color: "#64748B" }}>{t("loading.submitting", "Loading prescription detail...")}</div>;
  }

  if (error || !prescription) {
    return (
      <div style={{ padding: 40, textAlign: "center" }}>
        <h3>{t("messages.ERROR", "Prescription Not Found")}</h3>
        <p style={{ color: "#64748B" }}>{error || "The requested prescription record could not be located."}</p>
        <button
          onClick={() => navigate(doctorRoutes.prescriptions())}
          style={{ padding: "8px 16px", borderRadius: 6, border: "none", backgroundColor: "#2563EB", color: "#FFF", cursor: "pointer" }}
        >
          {t("navigation.prescriptions", "Back to Prescriptions")}
        </button>
      </div>
    );
  }

  if (showPrintView) {
    return (
      <div style={{ padding: 40, maxWidth: 800, margin: "0 auto", backgroundColor: "#FFF", border: "1px solid #000", fontFamily: "serif" }}>
        <div style={{ textAlign: "center", borderBottom: "2px solid #000", paddingBottom: 12, marginBottom: 20 }}>
          <h2 style={{ margin: 0 }}>AAROGYA SAHAYAK DEMONSTRATION PRESCRIPTION</h2>
          <div style={{ fontSize: 13 }}>Kalyanpur Primary Health Centre · Government of Maharashtra</div>
          <div style={{ fontSize: 11, fontStyle: "italic", color: "#555" }}>Demonstration Record - Non-Production Hackathon Build</div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20, fontSize: 13 }}>
          <div>
            <strong>Patient:</strong> {prescription.patient_name} ({prescription.patient_age} yrs, {prescription.patient_gender})<br />
            <strong>Village:</strong> {prescription.patient_village}<br />
            <strong>Case Ref:</strong> {prescription.case_reference}
          </div>
          <div>
            <strong>Prescription Ref:</strong> {prescription.reference}<br />
            <strong>Date Signed:</strong> {prescription.signed_at ? new Date(prescription.signed_at).toLocaleDateString() : "Draft"}<br />
            <strong>Prescriber:</strong> {prescription.prescriber_doctor_name}
          </div>
        </div>

        <h3 style={{ borderBottom: "1px solid #000", paddingBottom: 4 }}>Rx (Medications)</h3>
        <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 20, fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #000" }}>
              <th style={{ textAlign: "left" }}>Medicine</th>
              <th style={{ textAlign: "left" }}>Dose / Route</th>
              <th style={{ textAlign: "left" }}>Frequency & Timing</th>
              <th style={{ textAlign: "left" }}>Duration</th>
            </tr>
          </thead>
          <tbody>
            {prescription.items.map((it: any) => (
              <tr key={it.id} style={{ borderBottom: "1px solid #ddd" }}>
                <td style={{ padding: "6px 0" }}><strong>{it.generic_name_snapshot}</strong> {it.strength}</td>
                <td>{it.dose} ({it.route})</td>
                <td>{it.frequency} - {it.timing}</td>
                <td>{it.duration_value} {it.duration_unit}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div style={{ borderTop: "1px solid #000", paddingTop: 12, marginTop: 40, display: "flex", justifyContent: "space-between", fontSize: 12 }}>
          <div>
            <strong>Patient Instructions:</strong> Take medicines as directed with clean water. Contact ASHA or PHC if difficulty arises.
          </div>
          <div style={{ textAlign: "right" }}>
            _______________________<br />
            <strong>{prescription.prescriber_doctor_name}</strong><br />
            Digital Signature Verified
          </div>
        </div>

        <div style={{ marginTop: 30, textAlign: "center" }}>
          <button onClick={() => window.print()} style={{ padding: "8px 16px", cursor: "pointer", marginRight: 10 }}>🖨️ Print Document</button>
          <button onClick={() => setShowPrintView(false)} style={{ padding: "8px 16px", cursor: "pointer" }}>Back to Portal</button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto", fontFamily: "Inter, sans-serif" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 13, color: "#64748B", fontWeight: 600 }}>Prescription Record</div>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: "4px 0", color: "#0F172A" }}>
            {prescription.reference} <span style={{ fontSize: 14, color: "#64748B" }}>(v{prescription.version_number})</span>
          </h1>
          <div style={{ fontSize: 13, color: "#475569" }}>
            Patient: <strong>{prescription.patient_name}</strong> ({prescription.patient_age} yrs, {prescription.patient_gender}) · Category: <span style={{ fontWeight: 600, color: "#2563EB" }}>{prescription.patient_category}</span>
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            onClick={() => navigate(doctorRoutes.patientRecord(prescription.citizen_id))}
            style={{ padding: "8px 14px", borderRadius: 6, border: "1px solid #CBD5E1", backgroundColor: "#FFF", cursor: "pointer", fontSize: 13, fontWeight: 600 }}
          >
            📋 Patient Record
          </button>
          <button
            onClick={() => navigate(doctorRoutes.consultation(prescription.consultation_id))}
            style={{ padding: "8px 14px", borderRadius: 6, border: "1px solid #CBD5E1", backgroundColor: "#FFF", cursor: "pointer", fontSize: 13, fontWeight: 600 }}
          >
            🩺 Consultation
          </button>
          <button
            onClick={() => navigate(doctorRoutes.caseTimeline(prescription.case_id))}
            style={{ padding: "8px 14px", borderRadius: 6, border: "1px solid #CBD5E1", backgroundColor: "#FFF", cursor: "pointer", fontSize: 13, fontWeight: 600 }}
          >
            ⏱️ Case Timeline
          </button>

          {["SIGNED", "ACTIVE", "COMPLETED", "PARTIALLY_STOPPED"].includes(prescription.status) && (
            <button
              onClick={() => setShowPrintView(true)}
              style={{ padding: "8px 14px", borderRadius: 6, border: "1px solid #0284C7", backgroundColor: "#F0F9FF", color: "#0284C7", cursor: "pointer", fontSize: 13, fontWeight: 600 }}
            >
              🖨️ Print / Download
            </button>
          )}

          {["DRAFT", "READY_FOR_REVIEW"].includes(prescription.status) && (
            <button
              onClick={handleSign}
              style={{ padding: "8px 14px", borderRadius: 6, border: "none", backgroundColor: "#166534", color: "#FFF", cursor: "pointer", fontSize: 13, fontWeight: 700 }}
            >
              ✍️ Review & Sign
            </button>
          )}

          {["SIGNED", "ACTIVE"].includes(prescription.status) && (
            <>
              <button
                onClick={() => setShowAmendModal(true)}
                style={{ padding: "8px 14px", borderRadius: 6, border: "none", backgroundColor: "#7E22CE", color: "#FFF", cursor: "pointer", fontSize: 13, fontWeight: 600 }}
              >
                ✏️ Amend Prescription
              </button>
              <button
                onClick={() => setShowFollowUpModal(true)}
                style={{ padding: "8px 14px", borderRadius: 6, border: "none", backgroundColor: "#2563EB", color: "#FFF", cursor: "pointer", fontSize: 13, fontWeight: 600 }}
              >
                📌 Assign ASHA Follow-up
              </button>
            </>
          )}
        </div>
      </div>

      {/* Main Content Layout */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 20 }}>
        {/* Left Column: Schedule & Instructions */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Medication Schedule Card */}
          <div style={{ backgroundColor: "#FFF", padding: 20, borderRadius: 12, border: "1px solid #E2E8F0" }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 14px 0", color: "#0F172A" }}>
              💊 Medication Schedule ({prescription.items.length})
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {prescription.items.map((it: any) => (
                <div
                  key={it.id}
                  style={{
                    padding: 14,
                    borderRadius: 8,
                    backgroundColor: it.status === "STOPPED" ? "#FEF2F2" : "#F8FAFC",
                    border: it.status === "STOPPED" ? "1px solid #FECACA" : "1px solid #E2E8F0",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ fontSize: 15, fontWeight: 700, color: it.status === "STOPPED" ? "#991B1B" : "#0F172A" }}>
                      {it.generic_name_snapshot} {it.brand_name_snapshot ? `(${it.brand_name_snapshot})` : ""}
                    </div>
                    {it.status === "STOPPED" ? (
                      <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 10, backgroundColor: "#FEE2E2", color: "#DC2626" }}>
                        STOPPED: {it.stop_reason}
                      </span>
                    ) : (
                      ["SIGNED", "ACTIVE"].includes(prescription.status) && (
                        <button
                          onClick={() => {
                            setSelectedItemToStop(it);
                            setShowStopModal(true);
                          }}
                          style={{ fontSize: 11, fontWeight: 600, color: "#DC2626", border: "1px solid #FCA5A5", backgroundColor: "#FFF", borderRadius: 4, padding: "4px 8px", cursor: "pointer" }}
                        >
                          Stop Medicine
                        </button>
                      )
                    )}
                  </div>
                  <div style={{ fontSize: 13, color: "#334155", marginTop: 4 }}>
                    <strong>Form:</strong> {it.formulation} · <strong>Dose:</strong> {it.dose} {it.dose_unit} ({it.route}) · <strong>Frequency:</strong> {it.frequency} ({it.timing})
                  </div>
                  <div style={{ fontSize: 12, color: "#64748B", marginTop: 4 }}>
                    <strong>Duration:</strong> {it.duration_value} {it.duration_unit} (Qty: {it.quantity}) · <strong>Instructions:</strong> {it.instructions || "None"}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Multilingual Patient Instructions Card */}
          <div style={{ backgroundColor: "#FFF", padding: 20, borderRadius: 12, border: "1px solid #E2E8F0" }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 14px 0", color: "#0F172A" }}>
              🗣️ Patient Instructions (Multilingual Preview)
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ padding: 12, backgroundColor: "#F8FAFC", borderRadius: 8, borderLeft: "4px solid #2563EB" }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#2563EB" }}>English:</div>
                <div style={{ fontSize: 13, color: "#1E293B", marginTop: 2 }}>
                  Take medicines as scheduled after food with clean water. Complete the entire course.
                </div>
              </div>
              <div style={{ padding: 12, backgroundColor: "#F8FAFC", borderRadius: 8, borderLeft: "4px solid #166534" }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#166534" }}>मराठी (Marathi):</div>
                <div style={{ fontSize: 13, color: "#1E293B", marginTop: 2 }}>
                  जेवणानंतर स्वच्छ पाण्यासोबत वेळेवर औषध घ्या. डॉक्टरांच्या सल्ल्याशिवाय औषध बंद करू नका.
                </div>
              </div>
              <div style={{ padding: 12, backgroundColor: "#F8FAFC", borderRadius: 8, borderLeft: "4px solid #D97706" }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#D97706" }}>हिंदी (Hindi):</div>
                <div style={{ fontSize: 13, color: "#1E293B", marginTop: 2 }}>
                  भोजन के बाद साफ पानी के साथ समय पर दवा लें। पूरा कोर्स पूरा करें।
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Safety Review & History */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Safety Review Card */}
          <div style={{ backgroundColor: "#FFF", padding: 20, borderRadius: 12, border: "1px solid #E2E8F0" }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 14px 0", color: "#0F172A" }}>
              🛡️ Deterministic Safety Review
            </h3>
            {prescription.safety_checks && prescription.safety_checks.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {prescription.safety_checks.map((sc: any) => (
                  <div
                    key={sc.id}
                    style={{
                      padding: 10,
                      borderRadius: 6,
                      backgroundColor: sc.severity === "BLOCKING_ERROR" ? "#FEF2F2" : "#FFF7ED",
                      border: sc.severity === "BLOCKING_ERROR" ? "1px solid #FECACA" : "1px solid #FED7AA",
                      fontSize: 12,
                    }}
                  >
                    <div style={{ fontWeight: 700, color: sc.severity === "BLOCKING_ERROR" ? "#DC2626" : "#C2410C" }}>
                      {sc.check_type.replace(/_/g, " ")} ({sc.severity})
                    </div>
                    <div style={{ color: "#334155", marginTop: 2 }}>{sc.message}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 13, color: "#166534", backgroundColor: "#F0FDF4", padding: 12, borderRadius: 6, border: "1px solid #BBF7D0" }}>
                ✓ All deterministic safety checks passed.
              </div>
            )}
          </div>

          {/* Clinical Context & Reason */}
          <div style={{ backgroundColor: "#FFF", padding: 20, borderRadius: 12, border: "1px solid #E2E8F0" }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 10px 0", color: "#0F172A" }}>
              📝 Clinical Context
            </h3>
            <div style={{ fontSize: 13, color: "#334155", lineHeight: "20px" }}>
              {prescription.clinical_context || "Routine clinical encounter prescription."}
            </div>
          </div>
        </div>
      </div>

      {/* Stop Medicine Modal */}
      {showStopModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "#FFF", width: "100%", maxWidth: 480, padding: 24, borderRadius: 12 }}>
            <h3 style={{ margin: "0 0 12px 0", color: "#DC2626" }}>Stop Medication</h3>
            <div style={{ fontSize: 13, color: "#475569", marginBottom: 14 }}>
              Selected Item: <strong>{selectedItemToStop?.generic_name_snapshot}</strong>
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Reason for Stopping:</label>
              <select
                value={stopReason}
                onChange={(e) => setStopReason(e.target.value)}
                style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #CBD5E1" }}
              >
                <option value="ALLERGY_CONCERN">Adverse Side-Effect / Allergy Concern</option>
                <option value="INEFFECTIVE">Clinically Ineffective</option>
                <option value="DOSAGE_ADJUSTMENT">Replacing with Different Dose</option>
                <option value="TREATMENT_COMPLETE">Treatment Complete</option>
              </select>
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Doctor Note:</label>
              <textarea
                value={stopDoctorNote}
                onChange={(e) => setStopDoctorNote(e.target.value)}
                rows={2}
                style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #CBD5E1" }}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Patient Guidance:</label>
              <input
                type="text"
                value={stopPatientGuidance}
                onChange={(e) => setStopPatientGuidance(e.target.value)}
                placeholder="Discontinue medicine immediately..."
                style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #CBD5E1" }}
              />
            </div>

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={() => setShowStopModal(false)} style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid #CBD5E1", backgroundColor: "#FFF", cursor: "pointer" }}>Cancel</button>
              <button onClick={handleStopItem} style={{ padding: "8px 16px", borderRadius: 6, border: "none", backgroundColor: "#DC2626", color: "#FFF", cursor: "pointer", fontWeight: 700 }}>Confirm Stop</button>
            </div>
          </div>
        </div>
      )}

      {/* Amend Prescription Modal */}
      {showAmendModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "#FFF", width: "100%", maxWidth: 480, padding: 24, borderRadius: 12 }}>
            <h3 style={{ margin: "0 0 12px 0", color: "#7E22CE" }}>Amend Prescription</h3>
            <p style={{ fontSize: 13, color: "#475569", marginBottom: 14 }}>
              Signed prescription v{prescription.version_number} will become immutable superseded version. A new draft v{prescription.version_number + 1} will be created.
            </p>

            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Amendment Reason Code:</label>
              <select
                value={amendReasonCode}
                onChange={(e) => setAmendReasonCode(e.target.value)}
                style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #CBD5E1" }}
              >
                <option value="DOSE_ADJUSTED">Dose Adjusted</option>
                <option value="MEDICINE_REPLACED">Medicine Replaced</option>
                <option value="DURATION_CHANGED">Duration Changed</option>
                <option value="REPORTED_DIFFICULTY">Reported Difficulty Taking Medicine</option>
                <option value="INVESTIGATION_REVIEW">Investigation Review Outcome</option>
                <option value="CLINICAL_REASSESSMENT">Clinical Reassessment</option>
              </select>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 4 }}>Clinical Reason Note:</label>
              <textarea
                value={amendReasonNote}
                onChange={(e) => setAmendReasonNote(e.target.value)}
                rows={3}
                placeholder="Detail reason for prescription amendment..."
                style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #CBD5E1" }}
              />
            </div>

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={() => setShowAmendModal(false)} style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid #CBD5E1", backgroundColor: "#FFF", cursor: "pointer" }}>Cancel</button>
              <button onClick={handleAmend} style={{ padding: "8px 16px", borderRadius: 6, border: "none", backgroundColor: "#7E22CE", color: "#FFF", cursor: "pointer", fontWeight: 700 }}>Create Amended Draft</button>
            </div>
          </div>
        </div>
      )}

      {/* Assign Follow-up Modal */}
      {showFollowUpModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div style={{ backgroundColor: "#FFF", width: "100%", maxWidth: 480, padding: 24, borderRadius: 12 }}>
            <h3 style={{ margin: "0 0 12px 0", color: "#2563EB" }}>Assign ASHA Adherence Monitoring</h3>
            <p style={{ fontSize: 13, color: "#475569", marginBottom: 14 }}>
              Create an adherence monitoring task for assigned ASHA Sita Patel.
            </p>

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 4 }}>ASHA Directive / Instructions:</label>
              <textarea
                value={followUpInstructions}
                onChange={(e) => setFollowUpInstructions(e.target.value)}
                rows={3}
                style={{ width: "100%", padding: 8, borderRadius: 6, border: "1px solid #CBD5E1" }}
              />
            </div>

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={() => setShowFollowUpModal(false)} style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid #CBD5E1", backgroundColor: "#FFF", cursor: "pointer" }}>Cancel</button>
              <button onClick={handleAssignFollowUp} style={{ padding: "8px 16px", borderRadius: 6, border: "none", backgroundColor: "#2563EB", color: "#FFF", cursor: "pointer", fontWeight: 700 }}>Assign Task</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DoctorPrescriptionDetailScreen;
