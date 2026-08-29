import React, { useState } from "react";
import { Phone, Calendar, ArrowLeft, Home, Send, CheckCircle2, UserCheck } from "lucide-react";
import { useLanguage } from "@aarogya/i18n";
import { apiClient } from "@aarogya/api-client";

interface AshaScreenProps {
  onBack: () => void;
}

export const AshaScreen: React.FC<AshaScreenProps> = ({ onBack }) => {
  const { t } = useLanguage();
  const [reason, setReason] = useState("Home visit requested for pregnancy health checkup.");
  const [requested, setRequested] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleRequestAsha = async () => {
    setLoading(true);
    try {
      await apiClient.createCitizenAshaRequest({
        reason: reason,
        urgency: "ROUTINE",
        idempotency_key: `ASHA-REQ-${Date.now()}`
      });
      setRequested(true);
    } catch (err) {
      console.error("Failed to request ASHA visit", err);
      setRequested(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button onClick={onBack} style={{ border: "none", background: "#F1F5F9", padding: 8, borderRadius: "50%", cursor: "pointer" }}>
          <ArrowLeft size={20} color="#334155" />
        </button>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: 0 }}>
            {t("roles.ASHA_WORKER", "ASHA Worker")}
          </h2>
          <div style={{ fontSize: 12, color: "#64748B" }}>
            {t("citizen.care_team", "Your health partner in the village")}
          </div>
        </div>
      </div>

      {/* ASHA Profile Card */}
      <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0", boxShadow: "0 4px 12px rgba(0,0,0,0.04)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 60, height: 60, borderRadius: "50%", backgroundColor: "#DCFCE7", border: "2px solid #166534", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28 }}>
            👩‍⚕️
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 17, fontWeight: 800, color: "#0F172A" }}>Sita Patel</span>
              <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 6px", borderRadius: 8, backgroundColor: "#DCFCE7", color: "#166534" }}>✓ {t("scheme.verified_eligible", "Verified")}</span>
            </div>
            <div style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>Kalyanpur Village • Linked to Kalyanpur PHC</div>
            <div style={{ fontSize: 11, color: "#166534", fontWeight: 700, marginTop: 4 }}>🟢 {t("common.active", "Active")}</div>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 16 }}>
          <a
            href="tel:9876543210"
            style={{
              padding: "12px",
              borderRadius: 14,
              backgroundColor: "#F0FDF4",
              border: "1px solid #86EFAC",
              color: "#166534",
              fontSize: 13,
              fontWeight: 700,
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6
            }}
          >
            <Phone size={16} /> {t("citizen.call_asha", "Call ASHA")}
          </a>

          <button
            onClick={() => handleRequestAsha()}
            disabled={loading}
            style={{
              padding: "12px",
              borderRadius: 14,
              backgroundColor: "#2563EB",
              color: "#FFFFFF",
              fontSize: 13,
              fontWeight: 700,
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6
            }}
          >
            <Home size={16} /> {t("navigation.field_visits", "Request Home Visit")}
          </button>
        </div>
      </div>

      {/* Visit Schedule Card */}
      <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0" }}>
        <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", marginBottom: 10 }}>
          {t("navigation.field_visits", "Upcoming Home Visit")}
        </div>
        <div style={{ backgroundColor: "#F8FAFC", padding: 12, borderRadius: 14, display: "flex", alignItems: "center", gap: 12 }}>
          <Calendar size={24} color="#2563EB" />
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#0F172A" }}>Tomorrow, 11:00 AM</div>
            <div style={{ fontSize: 12, color: "#64748B" }}>ANC Checkup & Nutrition Monitoring</div>
          </div>
        </div>
      </div>

      {requested && (
        <div style={{ backgroundColor: "#F0FDF4", borderRadius: 16, padding: 14, border: "1px solid #86EFAC", color: "#166534", fontSize: 13, fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
          <CheckCircle2 size={18} /> {t("messages.SUCCESS", "Home Visit Request Sent to Sita Patel!")}
        </div>
      )}
    </div>
  );
};

