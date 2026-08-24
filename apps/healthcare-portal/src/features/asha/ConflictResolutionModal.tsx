import React from "react";
import { WarningIcon, CheckCircleIcon } from "../../components/Icons";

export interface ConflictResolutionModalProps {
  isOpen: boolean;
  conflict: {
    id: string;
    caseId: string;
    actionType: string;
    conflictReason: string;
    localPayload: any;
    serverData: any;
  } | null;
  onResolve: (conflictId: string, resolution: "ACCEPT_SERVER" | "OVERWRITE_WITH_ADDENDUM") => void;
  onClose: () => void;
}

export const ConflictResolutionModal: React.FC<ConflictResolutionModalProps> = ({
  isOpen,
  conflict,
  onResolve,
  onClose
}) => {
  if (!isOpen || !conflict) return null;

  const localVitals = conflict.localPayload?.vitals || {};
  const serverStatus = conflict.serverData?.status || "DOCTOR_ACKNOWLEDGED";
  const doctorDiagnosis = conflict.serverData?.confirmed_diagnosis || "Under Direct Medical Care";

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.65)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: 20
      }}
    >
      <div
        style={{
          backgroundColor: "var(--surface, #FFFFFF)",
          borderRadius: 16,
          maxWidth: 720,
          width: "100%",
          padding: 28,
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
          border: "1px solid var(--border, #E2E8F0)",
          maxHeight: "90vh",
          overflowY: "auto"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: "50%",
              backgroundColor: "var(--urgent-bg, #FFEBEE)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--urgent, #D32F2F)"
            }}
          >
            <WarningIcon size={26} color="var(--urgent, #D32F2F)" />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
              Clinical Record Conflict Detected
            </h3>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
              Case state was modified by a Doctor or Senior Clinician while this device was offline.
            </div>
          </div>
        </div>

        <div
          style={{
            padding: 14,
            backgroundColor: "var(--neutral-bg, #F7FAFC)",
            borderRadius: 8,
            borderLeft: "4px solid var(--primary, #0052CC)",
            marginBottom: 20,
            fontSize: 13,
            color: "var(--text-primary)"
          }}
        >
          <strong>Safety Policy:</strong> ASHA offline submissions cannot overwrite signed Doctor diagnoses, completed consultations, or prescription orders.
        </div>

        {/* Side by side comparison */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
          {/* Local Information */}
          <div
            style={{
              padding: 16,
              borderRadius: 10,
              border: "1px solid var(--border)",
              backgroundColor: "var(--surface)"
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--primary)", marginBottom: 10 }}>
              📱 Local Field Submission
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 6 }}>
              Action: <strong>{conflict.actionType}</strong>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 6 }}>
              Recorded BP: <strong>{localVitals.systolic_bp || 150}/{localVitals.diastolic_bp || 100} mmHg</strong>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              Notes: <em>{conflict.localPayload?.notes || "Urgent pre-eclampsia triage notes"}</em>
            </div>
          </div>

          {/* Server Information */}
          <div
            style={{
              padding: 16,
              borderRadius: 10,
              border: "1px solid #C3DAFE",
              backgroundColor: "#EBF8FF"
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 700, color: "#2B6CB0", marginBottom: 10 }}>
              🏥 Authoritative PHC Server State
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 6 }}>
              Case Status: <strong>{serverStatus}</strong>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 6 }}>
              Diagnosis: <strong>{doctorDiagnosis}</strong>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              Consultation Status: <strong>Signed & Finalized by Doctor</strong>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
          <button
            onClick={() => onResolve(conflict.id, "ACCEPT_SERVER")}
            style={{
              padding: "10px 18px",
              backgroundColor: "var(--primary, #0052CC)",
              color: "#FFF",
              borderRadius: 8,
              border: "none",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer"
            }}
          >
            Accept Server Authority & Keep ASHA Notes as Addendum
          </button>

          <button
            onClick={onClose}
            style={{
              padding: "10px 16px",
              backgroundColor: "transparent",
              color: "var(--text-secondary)",
              borderRadius: 8,
              border: "1px solid var(--border)",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer"
            }}
          >
            Review Later
          </button>
        </div>
      </div>
    </div>
  );
};
