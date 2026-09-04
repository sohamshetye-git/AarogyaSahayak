import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiClient as api } from "@aarogya/api-client";
import { doctorRoutes } from "./doctorRoutes";
import { SampleRecordModal } from "./components/SampleRecordModal";
import { ResultEntryModal } from "./components/ResultEntryModal";
import { RequestRecollectionModal } from "./components/RequestRecollectionModal";
import { formatIndiaDateTime } from "./utils/dateFormatter";

export const DoctorInvestigationDetailScreen: React.FC = () => {
  const { investigationId } = useParams<{ investigationId: string }>();
  const navigate = useNavigate();

  const [order, setOrder] = useState<any | null>(null);
  const [patientRecord, setPatientRecord] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isSampleModalOpen, setIsSampleModalOpen] = useState(false);
  const [isResultModalOpen, setIsResultModalOpen] = useState(false);
  const [isRecollectionModalOpen, setIsRecollectionModalOpen] = useState(false);

  // Doctor Review state
  const [reviewNote, setReviewNote] = useState("");
  const [reviewOutcome, setReviewOutcome] = useState("NO_CHANGE");
  const [updateCarePlan, setUpdateCarePlan] = useState(false);
  const [createFollowup, setCreateFollowup] = useState(false);
  const [followupInstructions, setFollowupInstructions] = useState("");
  const [submittingReview, setSubmittingReview] = useState(false);

  const fetchDetail = useCallback(async () => {
    if (!investigationId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getInvestigation(investigationId);
      const detail = data?.data || data;
      setOrder(detail);
      if (data.review) {
        setReviewNote(data.review.review_note || "");
        setReviewOutcome(data.review.outcome || "NO_CHANGE");
        setUpdateCarePlan(data.review.care_plan_updated || false);
      }

      if (data.citizen_id) {
        api.getPatientRecord(data.citizen_id).then(setPatientRecord).catch(() => null);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load investigation detail.");
    } finally {
      setLoading(false);
    }
  }, [investigationId]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleRecordSample = async (ordId: string, sampleData: any) => {
    await api.recordSampleCollection(ordId, sampleData);
    fetchDetail();
  };

  const handleEnterResult = async (ordId: string, resultData: any) => {
    await api.enterInvestigationResult(ordId, resultData);
    fetchDetail();
  };

  const handleAcknowledgeCritical = async () => {
    if (!order) return;
    await api.acknowledgeCriticalResult(order.id, { notes: "Critical result acknowledged on detail screen." });
    fetchDetail();
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!order) return;
    setSubmittingReview(true);
    try {
      await api.reviewInvestigationResult(order.id, {
        review_note: reviewNote,
        outcome: reviewOutcome,
        update_care_plan: updateCarePlan,
        create_followup: createFollowup,
        followup_instructions: followupInstructions || undefined,
      });
      fetchDetail();
    } catch (err: any) {
      alert(err.message || "Failed to submit review.");
    } finally {
      setSubmittingReview(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "3rem", textAlign: "center", color: "#64748b" }}>
        Loading investigation detail...
      </div>
    );
  }

  if (error || !order) {
    return (
      <div style={{ padding: "2.5rem 1.5rem", maxWidth: "800px", margin: "3rem auto", background: "#ffffff", borderRadius: "16px", border: "1px solid #fca5a5", boxShadow: "0 10px 15px -3px rgba(220,38,38,0.1)", textAlign: "center" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>⚠️</div>
        <h2 style={{ margin: "0 0 0.5rem 0", color: "#991b1b" }}>Investigation Order Not Found</h2>
        <p style={{ color: "#475569", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
          Attempted Investigation ID / Reference: <code style={{ background: "#f1f5f9", padding: "0.2rem 0.5rem", borderRadius: "4px", fontWeight: 600 }}>{investigationId}</code>
          <br />
          {error || "The requested investigation record does not exist in PHC database."}
        </p>
        <div style={{ display: "flex", justifyContent: "center", gap: "1rem" }}>
          <button
            onClick={() => navigate(doctorRoutes.investigations())}
            style={{ padding: "0.6rem 1.25rem", borderRadius: "8px", background: "#0284c7", color: "#fff", border: "none", fontWeight: 600, cursor: "pointer" }}
          >
            ← Back to Investigations
          </button>
          <button
            onClick={fetchDetail}
            style={{ padding: "0.6rem 1.25rem", borderRadius: "8px", background: "#f1f5f9", color: "#334155", border: "1px solid #cbd5e1", fontWeight: 600, cursor: "pointer" }}
          >
            ↻ Retry
          </button>
        </div>
      </div>
    );
  }

  const resultItems = order.result?.items || [];
  const latestVitals = patientRecord?.measurements_and_trends?.latest_vitals;

  return (
    <div style={{ padding: "1.5rem", maxWidth: "1200px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Header Panel */}
      <div
        style={{
          background: "var(--card-bg, #ffffff)",
          padding: "1.5rem",
          borderRadius: "16px",
          border: order.status === "CRITICAL_RESULT" ? "2px solid #ef4444" : "1px solid var(--border, #e2e8f0)",
          boxShadow: "0 2px 4px rgba(0,0,0,0.05)",
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.85rem", color: "var(--text-secondary, #64748b)", fontWeight: 600 }}>
              {order.investigation_reference || order.reference} • {order.test?.category || order.category || "Other"}
            </div>
            <h1 style={{ margin: "0.2rem 0", fontSize: "1.6rem", fontWeight: 800, color: "var(--text-primary, #0f172a)" }}>
              {order.patient?.name || order.citizen_name} ({order.patient?.age || order.citizen_age}y, {order.patient?.gender || order.citizen_gender}) — {order.test?.name || order.test_name}
            </h1>
            <div style={{ fontSize: "0.85rem", color: "#0284c7", fontWeight: 600 }}>
              Village: {order.patient?.village || order.village_name || "Kalyanpur"} • Context: {order.clinical_context || "General"}
            </div>
          </div>

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <span style={{ padding: "0.3rem 0.75rem", borderRadius: "9999px", fontSize: "0.8rem", fontWeight: 700, background: "#fee2e2", color: "#991b1b" }}>
              {order.priority}
            </span>
            <span style={{ padding: "0.3rem 0.75rem", borderRadius: "9999px", fontSize: "0.8rem", fontWeight: 700, background: "#eff6ff", color: "#2563eb", border: "1px solid #93c5fd" }}>
              {order.status.replace("_", " ")}
            </span>
          </div>
        </div>

        {/* Header Action Buttons */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", paddingTop: "0.75rem", borderTop: "1px solid var(--border, #e2e8f0)" }}>
          <button
            onClick={() => navigate(doctorRoutes.patientRecord(order.citizen_id || order.patient?.citizen_id))}
            style={{ padding: "0.4rem 0.85rem", borderRadius: "6px", border: "1px solid #cbd5e1", background: "#fff", cursor: "pointer", fontWeight: 600, fontSize: "0.8rem" }}
          >
            View Patient Record
          </button>
          {(order.consultation_id || order.consultation?.consultation_id) && (
            <button
              onClick={() => navigate(doctorRoutes.consultation(order.consultation_id || order.consultation?.consultation_id))}
              style={{ padding: "0.4rem 0.85rem", borderRadius: "6px", border: "1px solid #cbd5e1", background: "#fff", cursor: "pointer", fontWeight: 600, fontSize: "0.8rem" }}
            >
              Open Consultation
            </button>
          )}
          {(order.case_id || order.case?.case_id) && (
            <button
              onClick={() => {
                const cId = order.case_id || order.case?.case_id;
                const oId = order.investigation_order_id || order.investigation_id || order.id || investigationId;
                navigate(doctorRoutes.caseTimeline(cId, `/doctor/investigations/${encodeURIComponent(oId)}`, oId));
              }}
              style={{ padding: "0.4rem 0.85rem", borderRadius: "6px", border: "1px solid #cbd5e1", background: "#fff", cursor: "pointer", fontWeight: 600, fontSize: "0.8rem" }}
            >
              View Case Timeline
            </button>
          )}
          {order.status !== "CANCELLED" && order.status !== "CLOSED" && order.status !== "REVIEWED" && !(order.result && !order.result.critical_flag) && (
            <button
              onClick={() => setIsRecollectionModalOpen(true)}
              style={{ padding: "0.4rem 0.85rem", borderRadius: "6px", border: "1px solid #fdba74", background: "#fff7ed", color: "#c2410c", cursor: "pointer", fontWeight: 600, fontSize: "0.8rem" }}
            >
              Request Recollection
            </button>
          )}
          <button
            onClick={() => alert(`Initiating direct call to patient ${order.patient?.name || order.citizen_name} via PHC tele-line.`)}
            style={{ padding: "0.4rem 0.85rem", borderRadius: "6px", border: "1px solid #86efac", background: "#f0fdf4", color: "#166534", cursor: "pointer", fontWeight: 600, fontSize: "0.8rem" }}
          >
            📞 Call Patient
          </button>
          <button
            onClick={fetchDetail}
            style={{ padding: "0.4rem 0.85rem", borderRadius: "6px", border: "1px solid #cbd5e1", background: "#fff", cursor: "pointer", fontWeight: 600, fontSize: "0.8rem" }}
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Critical Banner */}
      {order.status === "CRITICAL_RESULT" && (
        <div style={{ padding: "1rem 1.25rem", background: "#fef2f2", border: "2px solid #ef4444", borderRadius: "12px", color: "#991b1b", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <strong style={{ fontSize: "1rem" }}>⚠️ Critical Result Requires Doctor Acknowledgement</strong>
            <div style={{ fontSize: "0.85rem", marginTop: "0.2rem" }}>Laboratory flagged critical parameters for this patient.</div>
          </div>
          <button
            onClick={handleAcknowledgeCritical}
            style={{ padding: "0.5rem 1rem", borderRadius: "8px", border: "none", background: "#dc2626", color: "#fff", fontWeight: 700, cursor: "pointer" }}
          >
            Acknowledge Now
          </button>
        </div>
      )}

      {/* Grid of Sections */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
        {/* Section A: Order Details */}
        <div style={{ background: "var(--card-bg, #ffffff)", padding: "1.25rem", borderRadius: "12px", border: "1px solid #e2e8f0" }}>
          <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.05rem", color: "#0f172a", borderBottom: "1px solid #f1f5f9", paddingBottom: "0.5rem" }}>
            A. Order Details
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.85rem" }}>
            <div><strong>Test Name:</strong> {order.test?.name || order.test_name}</div>
            <div><strong>Category:</strong> {order.test?.category || order.category || "Other"}</div>
            <div><strong>Priority:</strong> {order.priority || "ROUTINE"}</div>
            <div><strong>Clinical Reason:</strong> {order.order?.clinical_reason || order.clinical_reason || "Not recorded"}</div>
            <div><strong>Specimen Type:</strong> {order.order?.specimen_type || order.specimen_type || "Not recorded"}</div>
            <div><strong>Preparation Instructions:</strong> {order.order?.preparation_instructions || order.preparation_instructions || "Not recorded"}</div>
            <div><strong>Collection Location:</strong> {order.order?.collection_location || order.collection_location || "PHC Kalyanpur"}</div>
            <div><strong>Ordered Date:</strong> {formatIndiaDateTime(order.order?.ordered_at || order.ordered_at)}</div>
            <div><strong>Ordering Doctor:</strong> {order.order?.ordered_by || order.ordering_doctor_name || "Medical Officer"}</div>
          </div>
        </div>

        {/* Section B: Patient Context */}
        <div style={{ background: "var(--card-bg, #ffffff)", padding: "1.25rem", borderRadius: "12px", border: "1px solid #e2e8f0" }}>
          <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.05rem", color: "#0f172a", borderBottom: "1px solid #f1f5f9", paddingBottom: "0.5rem" }}>
            B. Patient Clinical Context
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.85rem" }}>
            <div><strong>Clinical Context:</strong> {order.clinical_context}</div>
            {latestVitals && (
              <div>
                <strong>Latest Vitals:</strong> BP {latestVitals.systolic_bp}/{latestVitals.diastolic_bp} mmHg, SpO2 {latestVitals.spo2}%, Temp {latestVitals.temperature_c}°C
              </div>
            )}
            <div><strong>Assigned ASHA Worker:</strong> {order.assigned_asha_name || "None assigned"}</div>
            <div><strong>Case Reference:</strong> {order.case_reference || "N/A"}</div>
            <div><strong>Consultation Reference:</strong> {order.consultation_reference || "N/A"}</div>
          </div>
        </div>

        {/* Section C: Sample Tracking */}
        <div style={{ background: "var(--card-bg, #ffffff)", padding: "1.25rem", borderRadius: "12px", border: "1px solid #e2e8f0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <h3 style={{ margin: 0, fontSize: "1.05rem", color: "#0f172a" }}>C. Sample Tracking</h3>
            {order.status !== "CLOSED" && order.status !== "CANCELLED" && (
              <button
                onClick={() => setIsSampleModalOpen(true)}
                style={{ padding: "0.25rem 0.6rem", borderRadius: "4px", border: "1px solid #7c3aed", background: "#f5f3ff", color: "#7c3aed", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}
              >
                Update Sample
              </button>
            )}
          </div>
          {order.sample ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.85rem" }}>
              <div><strong>Status:</strong> {order.sample.collection_status}</div>
              <div><strong>Barcode Ref:</strong> {order.sample.sample_reference || "N/A"}</div>
              <div><strong>Collector:</strong> {order.sample.collected_by_name || "PHC Staff"}</div>
              {order.sample.collected_at && <div><strong>Collected Time:</strong> {new Date(order.sample.collected_at).toLocaleString("en-IN")}</div>}
              {order.sample.rejection_reason && (
                <div style={{ color: "#dc2626" }}><strong>Rejection Reason:</strong> {order.sample.rejection_reason}</div>
              )}
            </div>
          ) : (
            <div style={{ fontSize: "0.85rem", color: "#64748b" }}>No sample collection recorded yet.</div>
          )}
        </div>
      </div>

      {/* Section D: Result Table */}
      <div style={{ background: "var(--card-bg, #ffffff)", padding: "1.25rem", borderRadius: "12px", border: "1px solid #e2e8f0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h3 style={{ margin: 0, fontSize: "1.1rem", color: "#0f172a" }}>D. Laboratory Result Parameters</h3>
          {order.status !== "CLOSED" && order.status !== "CANCELLED" && (
            <button
              onClick={() => setIsResultModalOpen(true)}
              style={{ padding: "0.35rem 0.85rem", borderRadius: "6px", border: "none", background: "#2563eb", color: "#fff", fontSize: "0.8rem", fontWeight: 600, cursor: "pointer" }}
            >
              + Enter / Edit Result
            </button>
          )}
        </div>

        {order.result ? (
          <div>
            <div style={{ fontSize: "0.8rem", color: "#64748b", marginBottom: "0.75rem" }}>
              Source: <strong>{order.result.result_source || "Source not recorded"}</strong> ({order.result.laboratory_name || "PHC Lab"}) • Resulted At: {formatIndiaDateTime(order.result.resulted_at)}
            </div>

            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", textAlign: "left" }}>
                <thead>
                  <tr style={{ background: "#f8fafc", borderBottom: "2px solid #e2e8f0" }}>
                    <th style={{ padding: "0.6rem" }}>Parameter</th>
                    <th style={{ padding: "0.6rem" }}>Value</th>
                    <th style={{ padding: "0.6rem" }}>Unit</th>
                    <th style={{ padding: "0.6rem" }}>Reference Range</th>
                    <th style={{ padding: "0.6rem" }}>Flag</th>
                  </tr>
                </thead>
                <tbody>
                  {resultItems.map((item: any) => (
                    <tr key={item.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                      <td style={{ padding: "0.6rem", fontWeight: 600 }}>{item.parameter_name}</td>
                      <td style={{ padding: "0.6rem", fontWeight: 700 }}>{item.value}</td>
                      <td style={{ padding: "0.6rem" }}>{item.unit || "—"}</td>
                      <td style={{ padding: "0.6rem", color: "#64748b" }}>
                        {item.reference_low && item.reference_high ? `${item.reference_low} - ${item.reference_high}` : "Standard"}
                      </td>
                      <td style={{ padding: "0.6rem" }}>
                        <span
                          style={{
                            padding: "0.2rem 0.5rem",
                            borderRadius: "4px",
                            fontSize: "0.75rem",
                            fontWeight: 700,
                            background: item.source_flag === "CRITICAL" || item.source_flag === "HIGH" || item.source_flag === "LOW" ? "#fee2e2" : "#f0fdf4",
                            color: item.source_flag === "CRITICAL" || item.source_flag === "HIGH" || item.source_flag === "LOW" ? "#991b1b" : "#166534",
                          }}
                        >
                          {item.source_flag}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div style={{ fontSize: "0.85rem", color: "#64748b", fontStyle: "italic" }}>
            Result pending. Sample is awaiting laboratory processing.
          </div>
        )}
      </div>

      {/* Section F: Doctor Review Panel */}
      <div style={{ background: "var(--card-bg, #ffffff)", padding: "1.25rem", borderRadius: "12px", border: "1px solid #e2e8f0" }}>
        <h3 style={{ margin: "0 0 1rem 0", fontSize: "1.1rem", color: "#0f172a" }}>F. Doctor Result Review</h3>

        <form onSubmit={handleSubmitReview} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Review Outcome *</label>
              <select
                value={reviewOutcome}
                onChange={(e) => setReviewOutcome(e.target.value)}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
              >
                <option value="NO_CHANGE">No immediate change</option>
                <option value="REPEAT_TEST">Repeat test</option>
                <option value="UPDATE_CARE_PLAN">Update treatment/care plan</option>
                <option value="PHC_REVIEW">Schedule PHC review</option>
                <option value="ASHA_FOLLOW_UP">Assign ASHA follow-up</option>
                <option value="REFER_HIGHER">Refer higher centre</option>
                <option value="EMERGENCY_ACTION">Emergency action required</option>
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Care Plan Update</label>
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", marginTop: "0.5rem", cursor: "pointer" }}>
                <input type="checkbox" checked={updateCarePlan} onChange={(e) => setUpdateCarePlan(e.target.checked)} />
                Flag Care Plan Updated in Patient Record
              </label>
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Doctor Review Note *</label>
            <textarea
              rows={3}
              value={reviewNote}
              onChange={(e) => setReviewNote(e.target.value)}
              placeholder="Enter official doctor review assessment..."
              required
              style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.85rem" }}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button
              type="submit"
              disabled={submittingReview}
              style={{ padding: "0.5rem 1.25rem", borderRadius: "6px", border: "none", background: "#0284c7", color: "#fff", fontWeight: 600, cursor: "pointer" }}
            >
              {submittingReview ? "Saving Review..." : "Submit Doctor Review"}
            </button>
          </div>
        </form>
      </div>

      {/* Modals */}
      <SampleRecordModal
        isOpen={isSampleModalOpen}
        order={order}
        onClose={() => setIsSampleModalOpen(false)}
        onSubmit={handleRecordSample}
      />

      <ResultEntryModal
        isOpen={isResultModalOpen}
        order={order}
        onClose={() => setIsResultModalOpen(false)}
        onSubmit={handleEnterResult}
      />

      {isRecollectionModalOpen && (
        <RequestRecollectionModal
          order={order}
          onClose={() => setIsRecollectionModalOpen(false)}
          onSuccess={() => fetchDetail()}
        />
      )}
    </div>
  );
};
