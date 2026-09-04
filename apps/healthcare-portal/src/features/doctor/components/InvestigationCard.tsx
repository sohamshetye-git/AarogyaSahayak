import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { doctorRoutes } from "../doctorRoutes";
import { formatIndiaDateTime } from "../utils/dateFormatter";

export interface InvestigationCardProps {
  item: any;
  onRecordSample?: (item: any) => void;
  onEnterResult?: (item: any) => void;
  onReviewResult?: (item: any) => void;
  onAcknowledgeCritical?: (item: any) => void;
  onRequestRecollection?: (item: any) => void;
}

export const InvestigationCard: React.FC<InvestigationCardProps> = ({
  item,
  onRecordSample,
  onEnterResult,
  onReviewResult,
  onAcknowledgeCritical,
  onRequestRecollection,
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleViewTimeline = () => {
    const caseId = item.case_id || item.case?.id || (typeof item.case === "string" ? item.case : null);
    if (!caseId) {
      alert("Canonical case ID is missing for this investigation order.");
      return;
    }
    const returnUrl = `${location.pathname}${location.search}`;
    const orderId = item.investigation_order_id || item.investigation_id || item.id;
    navigate(doctorRoutes.caseTimeline(caseId, returnUrl, orderId));
  };

  const getStatusBadgeStyle = (status: string) => {
    switch (status) {
      case "CRITICAL_RESULT":
        return { bg: "#fef2f2", color: "#dc2626", border: "#fca5a5" };
      case "RESULT_AVAILABLE":
      case "REVIEW_REQUIRED":
        return { bg: "#eff6ff", color: "#2563eb", border: "#93c5fd" };
      case "REVIEWED":
      case "CLOSED":
        return { bg: "#f0fdf4", color: "#16a34a", border: "#86efac" };
      case "RECOLLECTION_REQUIRED":
      case "SAMPLE_REJECTED":
        return { bg: "#fff7ed", color: "#ea580c", border: "#fdba74" };
      case "SAMPLE_COLLECTED":
      case "IN_PROCESS":
        return { bg: "#f5f3ff", color: "#7c3aed", border: "#ddd6fe" };
      default:
        return { bg: "#f8fafc", color: "#475569", border: "#cbd5e1" };
    }
  };

  const getPriorityBadgeStyle = (priority: string) => {
    switch (priority) {
      case "EMERGENCY":
      case "URGENT":
        return { bg: "#fee2e2", color: "#991b1b" };
      case "HIGH":
        return { bg: "#ffedd5", color: "#9a3412" };
      default:
        return { bg: "#e2e8f0", color: "#334155" };
    }
  };

  const stStyle = getStatusBadgeStyle(item.status);
  const prStyle = getPriorityBadgeStyle(item.priority);

  return (
    <div
      style={{
        background: "var(--card-bg, #ffffff)",
        borderRadius: "12px",
        border: item.status === "CRITICAL_RESULT" ? "2px solid #ef4444" : "1px solid var(--border, #e2e8f0)",
        padding: "1.25rem",
        boxShadow: item.status === "CRITICAL_RESULT" ? "0 4px 12px rgba(239, 68, 68, 0.15)" : "0 1px 3px rgba(0,0,0,0.05)",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
        transition: "transform 0.15s ease, box-shadow 0.15s ease",
      }}
    >
      {/* Header Row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.5rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <h3 style={{ margin: 0, fontSize: "1.1rem", fontWeight: 700, color: "var(--text-primary, #0f172a)" }}>
              {item.citizen_name}
            </h3>
            <span style={{ fontSize: "0.85rem", color: "var(--text-secondary, #64748b)" }}>
              ({item.citizen_age}y, {item.citizen_gender}) — {item.village_name}
            </span>
          </div>
          <div style={{ fontSize: "0.8rem", color: "#0284c7", fontWeight: 600, marginTop: "0.2rem" }}>
            Context: {item.clinical_context || "General"}
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
          <span
            style={{
              padding: "0.25rem 0.6rem",
              borderRadius: "9999px",
              fontSize: "0.75rem",
              fontWeight: 700,
              backgroundColor: prStyle.bg,
              color: prStyle.color,
            }}
          >
            {item.priority}
          </span>
          <span
            style={{
              padding: "0.25rem 0.6rem",
              borderRadius: "9999px",
              fontSize: "0.75rem",
              fontWeight: 700,
              backgroundColor: stStyle.bg,
              color: stStyle.color,
              border: `1px solid ${stStyle.border}`,
            }}
          >
            {item.status.replace("_", " ")}
          </span>
        </div>
      </div>

      {/* Investigation Details */}
      <div
        style={{
          background: "var(--bg-subtle, #f8fafc)",
          padding: "0.75rem 1rem",
          borderRadius: "8px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "0.75rem",
          fontSize: "0.85rem",
        }}
      >
        <div>
          <div style={{ color: "var(--text-secondary, #64748b)", fontSize: "0.75rem" }}>Order Reference</div>
          <div style={{ fontWeight: 600, color: "var(--primary, #0284c7)" }}>{item.investigation_reference || item.reference || "Not recorded"}</div>
        </div>

        <div>
          <div style={{ color: "var(--text-secondary, #64748b)", fontSize: "0.75rem" }}>Test & Category</div>
          <div style={{ fontWeight: 600 }}>
            {item.test_name || "Diagnostic Test"} <span style={{ fontSize: "0.75rem", color: "#64748b" }}>({item.category || "Other"})</span>
          </div>
        </div>

        <div>
          <div style={{ color: "var(--text-secondary, #64748b)", fontSize: "0.75rem" }}>Ordering Doctor</div>
          <div>{item.ordering_doctor_name || "Medical Officer"}</div>
        </div>

        <div>
          <div style={{ color: "var(--text-secondary, #64748b)", fontSize: "0.75rem" }}>Case / Consultation</div>
          <div>
            {item.case_reference || "N/A"} {item.consultation_reference ? `/ ${item.consultation_reference}` : ""}
          </div>
        </div>

        {item.assigned_asha_name && (
          <div>
            <div style={{ color: "var(--text-secondary, #64748b)", fontSize: "0.75rem" }}>Assigned ASHA</div>
            <div style={{ fontWeight: 500, color: "#059669" }}>{item.assigned_asha_name}</div>
          </div>
        )}

        <div>
          <div style={{ color: "var(--text-secondary, #64748b)", fontSize: "0.75rem" }}>Ordered At</div>
          <div>{formatIndiaDateTime(item.ordered_at)}</div>
        </div>
      </div>

      {/* Clinical Reason */}
      {item.clinical_reason && (
        <div style={{ fontSize: "0.85rem", color: "var(--text-primary, #1e293b)" }}>
          <strong>Clinical Reason:</strong> {item.clinical_reason}
        </div>
      )}

      {/* Safe Result Preview */}
      {item.result && (
        <div
          style={{
            padding: "0.75rem 1rem",
            borderRadius: "8px",
            background: item.is_abnormal ? "#fef2f2" : "#f0fdf4",
            border: item.is_abnormal ? "1px solid #fca5a5" : "1px solid #bbf7d0",
            fontSize: "0.85rem",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem" }}>
            <span style={{ fontWeight: 700, color: item.is_abnormal ? "#991b1b" : "#166534" }}>
              {item.is_abnormal ? "⚠️ Abnormal Result Flagged" : "✓ Normal Result"}
            </span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-secondary, #64748b)" }}>
              Source: {item.result?.result_source || "Source not recorded"}
            </span>
          </div>

          <div style={{ fontSize: "0.85rem", color: "#334155" }}>
            {item.result_preview || "Result details available in report panel."}
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", marginTop: "0.4rem", fontSize: "0.75rem", color: "#64748b" }}>
            <span>Resulted: {formatIndiaDateTime(item.result?.resulted_at)}</span>
            <span>Review Status: {item.review ? `Reviewed by ${item.review.doctor_name || "Doctor"}` : "Awaiting Doctor Review"}</span>
          </div>
        </div>
      )}

      {/* Actions Bar */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.5rem", paddingTop: "0.5rem", borderTop: "1px solid var(--border, #e2e8f0)" }}>
        <button
          onClick={() => navigate(doctorRoutes.investigationDetail(item.investigation_id || item.id))}
          style={{
            padding: "0.4rem 0.8rem",
            borderRadius: "6px",
            border: "1px solid var(--border, #cbd5e1)",
            background: "var(--button-bg, #ffffff)",
            color: "var(--text-primary, #0f172a)",
            fontWeight: 600,
            fontSize: "0.8rem",
            cursor: "pointer",
          }}
        >
          View Order
        </button>

        {(item.status === "SAMPLE_PENDING" || item.status === "ORDERED" || item.status === "RECOLLECTION_REQUIRED") && onRecordSample && (
          <button
            onClick={() => onRecordSample(item)}
            style={{
              padding: "0.4rem 0.8rem",
              borderRadius: "6px",
              border: "none",
              background: "#7c3aed",
              color: "#ffffff",
              fontWeight: 600,
              fontSize: "0.8rem",
              cursor: "pointer",
            }}
          >
            Record Sample
          </button>
        )}

        {(item.status === "SAMPLE_COLLECTED" || item.status === "IN_PROCESS") && onEnterResult && (
          <button
            onClick={() => onEnterResult(item)}
            style={{
              padding: "0.4rem 0.8rem",
              borderRadius: "6px",
              border: "none",
              background: "#2563eb",
              color: "#ffffff",
              fontWeight: 600,
              fontSize: "0.8rem",
              cursor: "pointer",
            }}
          >
            Enter Result
          </button>
        )}

        {item.status === "CRITICAL_RESULT" && onAcknowledgeCritical && (
          <button
            onClick={() => onAcknowledgeCritical(item)}
            style={{
              padding: "0.4rem 0.8rem",
              borderRadius: "6px",
              border: "none",
              background: "#dc2626",
              color: "#ffffff",
              fontWeight: 700,
              fontSize: "0.8rem",
              cursor: "pointer",
            }}
          >
            Acknowledge Critical Result
          </button>
        )}

        {(item.status === "RESULT_AVAILABLE" || item.status === "CRITICAL_RESULT" || item.status === "DOCTOR_ACKNOWLEDGED" || item.status === "REVIEW_REQUIRED") && onReviewResult && (
          <button
            onClick={() => onReviewResult(item)}
            style={{
              padding: "0.4rem 0.8rem",
              borderRadius: "6px",
              border: "none",
              background: "#0284c7",
              color: "#ffffff",
              fontWeight: 600,
              fontSize: "0.8rem",
              cursor: "pointer",
            }}
          >
            Review Result
          </button>
        )}

        {onRequestRecollection &&
          item.status !== "CANCELLED" &&
          item.status !== "CLOSED" &&
          item.status !== "REVIEWED" &&
          !(item.result && !item.is_abnormal && item.status !== "SAMPLE_REJECTED" && item.status !== "RECOLLECTION_REQUIRED") && (
            <button
              onClick={() => onRequestRecollection(item)}
              style={{
                padding: "0.4rem 0.8rem",
                borderRadius: "6px",
                border: "1px solid #fdba74",
                background: "#fff7ed",
                color: "#c2410c",
                fontWeight: 600,
                fontSize: "0.8rem",
                cursor: "pointer",
              }}
            >
              Request Recollection
            </button>
          )}

        {item.citizen_id && (
          <button
            onClick={() => navigate(doctorRoutes.patientRecord(item.citizen_id))}
            style={{
              padding: "0.4rem 0.8rem",
              borderRadius: "6px",
              border: "1px solid var(--border, #cbd5e1)",
              background: "none",
              color: "var(--text-secondary, #475569)",
              fontSize: "0.8rem",
              cursor: "pointer",
            }}
          >
            Open Patient Record
          </button>
        )}

        {item.consultation_id && (
          <button
            onClick={() => navigate(doctorRoutes.consultation(item.consultation_id))}
            style={{
              padding: "0.4rem 0.8rem",
              borderRadius: "6px",
              border: "1px solid var(--border, #cbd5e1)",
              background: "none",
              color: "var(--text-secondary, #475569)",
              fontSize: "0.8rem",
              cursor: "pointer",
            }}
          >
            Open Consultation
          </button>
        )}

        <button
          onClick={handleViewTimeline}
          style={{
            padding: "0.4rem 0.8rem",
            borderRadius: "6px",
            border: "1px solid var(--border, #cbd5e1)",
            background: "none",
            color: "var(--text-secondary, #475569)",
            fontSize: "0.8rem",
            cursor: "pointer",
          }}
        >
          View Timeline
        </button>
      </div>
    </div>
  );
};
