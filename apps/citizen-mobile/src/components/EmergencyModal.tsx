import React from "react";
import { PhoneCall, AlertTriangle, MapPin, X } from "lucide-react";
import { useLanguage } from "@aarogya/i18n";

interface EmergencyModalProps {
  onClose: () => void;
  onOpenFacilities: () => void;
}

export const EmergencyModal: React.FC<EmergencyModalProps> = ({ onClose, onOpenFacilities }) => {
  const { t } = useLanguage();

  return (
    <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.6)", display: "flex", alignItems: "flex-end", justifyContent: "center", zIndex: 200 }}>
      <div
        style={{
          width: "100%",
          maxWidth: 480,
          backgroundColor: "#FFFFFF",
          borderTopLeftRadius: 28,
          borderTopRightRadius: 28,
          padding: "24px 20px",
          display: "flex",
          flexDirection: "column",
          gap: 16,
          boxShadow: "0 -8px 32px rgba(0,0,0,0.2)",
          animation: "slideUp 0.2s ease-out"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, color: "#DC2626", fontSize: 18, fontWeight: 800 }}>
            <AlertTriangle size={24} color="#DC2626" />
            <span>{t("citizen.emergency_help", "Emergency Help")}</span>
          </div>
          <button onClick={onClose} style={{ border: "none", background: "#F1F5F9", padding: 8, borderRadius: "50%", cursor: "pointer" }}>
            <X size={18} color="#334155" />
          </button>
        </div>

        <div style={{ backgroundColor: "#FEF2F2", padding: 14, borderRadius: 16, border: "1.5px solid #FCA5A5", color: "#991B1B", fontSize: 13, lineHeight: 1.4 }}>
          {t("safety.chestPainEmergency", "If experiencing severe chest pain, heavy bleeding, or breathing difficulty, call 108 national ambulance immediately.")}
        </div>

        <a
          href="tel:108"
          style={{
            padding: "18px",
            borderRadius: 18,
            backgroundColor: "#DC2626",
            color: "#FFFFFF",
            fontSize: 18,
            fontWeight: 800,
            textAlign: "center",
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
            boxShadow: "0 6px 20px rgba(220, 38, 38, 0.4)"
          }}
        >
          <PhoneCall size={24} />
          {t("citizen.call_108_ambulance", "Call 108 Ambulance Now")}
        </a>

        <button
          onClick={() => {
            onClose();
            onOpenFacilities();
          }}
          style={{
            padding: "14px",
            borderRadius: 16,
            backgroundColor: "#F8FAFC",
            color: "#334155",
            fontSize: 14,
            fontWeight: 700,
            border: "1px solid #CBD5E1",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8
          }}
        >
          <MapPin size={18} color="#2563EB" />
          {t("facility.facilities_title", "Find Nearest 24x7 Hospital")}
        </button>
      </div>
    </div>
  );
};

