import React, { useState } from "react";

export interface ResultEntryModalProps {
  isOpen: boolean;
  order: any;
  onClose: () => void;
  onSubmit: (orderId: string, resultData: any) => Promise<void>;
}

export const ResultEntryModal: React.FC<ResultEntryModalProps> = ({
  isOpen,
  order,
  onClose,
  onSubmit,
}) => {
  const [labSource, setLabSource] = useState("PHC Manual/Demonstration Entry");
  const [labName, setLabName] = useState("PHC Kalyanpur Central Lab");
  const [criticalFlag, setCriticalFlag] = useState(false);

  const [items, setItems] = useState<any[]>([
    {
      parameter_name: order?.test_name === "Complete Blood Count (CBC)" ? "Hemoglobin" : (order?.test_name || "Parameter 1"),
      parameter_code: "P1",
      value: "11.2",
      unit: order?.test_name?.includes("CBC") || order?.test_name?.includes("Hemoglobin") ? "g/dL" : "mg/dL",
      reference_low: "12.0",
      reference_high: "15.0",
      source_flag: "LOW",
      remarks: "Routine entry",
    },
  ]);

  const [submitting, setSubmitting] = useState(false);

  if (!isOpen || !order) return null;

  const handleAddItem = () => {
    setItems([
      ...items,
      {
        parameter_name: "",
        parameter_code: "",
        value: "",
        unit: "",
        reference_low: "",
        reference_high: "",
        source_flag: "NORMAL",
        remarks: "",
      },
    ]);
  };

  const handleItemChange = (index: number, field: string, val: string) => {
    const updated = [...items];
    updated[index][field] = val;
    setItems(updated);
  };

  const handleRemoveItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit(order.id, {
        result_source: labSource,
        laboratory_name: labName,
        critical_flag: criticalFlag,
        items,
      });
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
          maxWidth: "650px",
          maxHeight: "90vh",
          overflowY: "auto",
          padding: "1.5rem",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h2 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700 }}>Enter Laboratory Results</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: "1.5rem", cursor: "pointer" }}>
            &times;
          </button>
        </div>

        <div style={{ background: "#eff6ff", padding: "0.5rem 0.75rem", borderRadius: "6px", fontSize: "0.8rem", color: "#1d4ed8", marginBottom: "1rem", fontWeight: 600 }}>
          PHC Manual / Demonstration Entry
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div>
            <strong>Test:</strong> {order.test_name} ({order.reference}) — Patient: {order.citizen_name}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Result Source</label>
              <input
                type="text"
                value={labSource}
                onChange={(e) => setLabSource(e.target.value)}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Laboratory Name</label>
              <input
                type="text"
                value={labName}
                onChange={(e) => setLabName(e.target.value)}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
              />
            </div>
          </div>

          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", fontWeight: 700, color: "#dc2626", cursor: "pointer" }}>
            <input type="checkbox" checked={criticalFlag} onChange={(e) => setCriticalFlag(e.target.checked)} />
            ⚠️ Mark Result as CRITICAL (Triggers urgent Doctor acknowledgement alert)
          </label>

          {/* Result Items Table */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 700 }}>Structured Parameter Items</span>
              <button
                type="button"
                onClick={handleAddItem}
                style={{ padding: "0.25rem 0.6rem", borderRadius: "4px", border: "1px solid #0284c7", background: "#f0f9ff", color: "#0284c7", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}
              >
                + Add Parameter
              </button>
            </div>

            {items.map((item, idx) => (
              <div
                key={idx}
                style={{
                  padding: "0.75rem",
                  background: "#f8fafc",
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  marginBottom: "0.5rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.5rem",
                }}
              >
                <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: "0.5rem" }}>
                  <input
                    type="text"
                    placeholder="Parameter Name (e.g. Hemoglobin)"
                    value={item.parameter_name}
                    onChange={(e) => handleItemChange(idx, "parameter_name", e.target.value)}
                    required
                    style={{ padding: "0.4rem", borderRadius: "4px", border: "1px solid #cbd5e1", fontSize: "0.8rem" }}
                  />
                  <input
                    type="text"
                    placeholder="Value (e.g. 8.7)"
                    value={item.value}
                    onChange={(e) => handleItemChange(idx, "value", e.target.value)}
                    required
                    style={{ padding: "0.4rem", borderRadius: "4px", border: "1px solid #cbd5e1", fontSize: "0.8rem" }}
                  />
                  <input
                    type="text"
                    placeholder="Unit (e.g. g/dL)"
                    value={item.unit}
                    onChange={(e) => handleItemChange(idx, "unit", e.target.value)}
                    style={{ padding: "0.4rem", borderRadius: "4px", border: "1px solid #cbd5e1", fontSize: "0.8rem" }}
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: "0.5rem", alignItems: "center" }}>
                  <input
                    type="text"
                    placeholder="Ref Low (e.g. 12.0)"
                    value={item.reference_low}
                    onChange={(e) => handleItemChange(idx, "reference_low", e.target.value)}
                    style={{ padding: "0.4rem", borderRadius: "4px", border: "1px solid #cbd5e1", fontSize: "0.8rem" }}
                  />
                  <input
                    type="text"
                    placeholder="Ref High (e.g. 15.0)"
                    value={item.reference_high}
                    onChange={(e) => handleItemChange(idx, "reference_high", e.target.value)}
                    style={{ padding: "0.4rem", borderRadius: "4px", border: "1px solid #cbd5e1", fontSize: "0.8rem" }}
                  />
                  <select
                    value={item.source_flag}
                    onChange={(e) => handleItemChange(idx, "source_flag", e.target.value)}
                    style={{ padding: "0.4rem", borderRadius: "4px", border: "1px solid #cbd5e1", fontSize: "0.8rem" }}
                  >
                    <option value="NORMAL">NORMAL</option>
                    <option value="LOW">LOW</option>
                    <option value="HIGH">HIGH</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>

                  {items.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveItem(idx)}
                      style={{ background: "none", border: "none", color: "#dc2626", fontWeight: 700, cursor: "pointer" }}
                    >
                      &times;
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1rem" }}>
            <button type="button" onClick={onClose} style={{ padding: "0.5rem 1rem", borderRadius: "6px", border: "1px solid #cbd5e1", background: "none" }}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              style={{
                padding: "0.5rem 1.25rem",
                borderRadius: "6px",
                border: "none",
                background: "#2563eb",
                color: "#ffffff",
                fontWeight: 600,
              }}
            >
              {submitting ? "Submitting Result..." : "Submit Result Entry"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
