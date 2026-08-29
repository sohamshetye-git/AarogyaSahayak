import React, { useState } from "react";

export interface SampleRecordModalProps {
  isOpen: boolean;
  order: any;
  onClose: () => void;
  onSubmit: (orderId: string, sampleData: any) => Promise<void>;
}

export const SampleRecordModal: React.FC<SampleRecordModalProps> = ({
  isOpen,
  order,
  onClose,
  onSubmit,
}) => {
  const [isRejection, setIsRejection] = useState(false);
  const [sampleRef, setSampleRef] = useState(order?.sample?.sample_reference || `SMP-${order?.reference || "INV-001"}`);
  const [specimenType, setSpecimenType] = useState(order?.specimen_type || "Whole Blood");
  const [rejectionReason, setRejectionReason] = useState("");
  const [recollectionRequired, setRecollectionRequired] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen || !order) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (isRejection) {
        await onSubmit(order.id, {
          rejection_reason: rejectionReason || "Specimen rejected by laboratory",
          recollection_required: recollectionRequired,
        });
      } else {
        await onSubmit(order.id, {
          sample_reference: sampleRef,
          specimen_type: specimenType,
          collected_at: new Date().toISOString(),
        });
      }
      onClose();
    } catch (err) {
      console.error(err);
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
        justifyContent: "center",
        zIndex: 1000,
        padding: "1rem",
      }}
    >
      <div
        style={{
          background: "var(--modal-bg, #ffffff)",
          borderRadius: "16px",
          width: "100%",
          maxWidth: "500px",
          padding: "1.5rem",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700 }}>Record Sample Collection / Status</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: "1.5rem", cursor: "pointer" }}>
            &times;
          </button>
        </div>

        <div style={{ background: "#eff6ff", padding: "0.5rem 0.75rem", borderRadius: "6px", fontSize: "0.8rem", color: "#1d4ed8", marginBottom: "1rem", fontWeight: 600 }}>
          PHC Manual / Demonstration Entry
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div>
            <strong>Test:</strong> {order.test_name} ({order.reference})
          </div>

          <div style={{ display: "flex", gap: "1rem" }}>
            <label style={{ cursor: "pointer", fontSize: "0.85rem", fontWeight: 600 }}>
              <input type="radio" name="mode" checked={!isRejection} onChange={() => setIsRejection(false)} /> Record Sample Collection
            </label>
            <label style={{ cursor: "pointer", fontSize: "0.85rem", fontWeight: 600, color: "#dc2626" }}>
              <input type="radio" name="mode" checked={isRejection} onChange={() => setIsRejection(true)} /> Record Specimen Rejection
            </label>
          </div>

          {!isRejection ? (
            <>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Sample Reference Barcode</label>
                <input
                  type="text"
                  value={sampleRef}
                  onChange={(e) => setSampleRef(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Specimen Type</label>
                <input
                  type="text"
                  value={specimenType}
                  onChange={(e) => setSpecimenType(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                />
              </div>
            </>
          ) : (
            <>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Rejection Reason *</label>
                <textarea
                  rows={2}
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="e.g. Hemolyzed specimen, insufficient quantity, incorrect container"
                  required
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                />
              </div>

              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", cursor: "pointer" }}>
                <input type="checkbox" checked={recollectionRequired} onChange={(e) => setRecollectionRequired(e.target.checked)} />
                Flag Fresh Sample Recollection Required
              </label>
            </>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1rem" }}>
            <button type="button" onClick={onClose} style={{ padding: "0.5rem 1rem", borderRadius: "6px", border: "1px solid #cbd5e1", background: "none" }}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              style={{
                padding: "0.5rem 1rem",
                borderRadius: "6px",
                border: "none",
                background: isRejection ? "#dc2626" : "#7c3aed",
                color: "#ffffff",
                fontWeight: 600,
              }}
            >
              {submitting ? "Saving..." : isRejection ? "Reject Specimen" : "Confirm Sample Collected"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
