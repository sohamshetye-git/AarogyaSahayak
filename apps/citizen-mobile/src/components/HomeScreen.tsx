import React, { useState, useEffect } from "react";
import { useLanguage } from "@aarogya/i18n";
import { Mic, Keyboard, Stethoscope, AlertTriangle, UserCheck, MapPin, Award, Pill, Bell, Wifi, ChevronRight } from "lucide-react";
import { apiClient } from "@aarogya/api-client";

import { useCitizenAuth } from "../context/CitizenAuthContext";

interface HomeScreenProps {
  onStartVoiceChat: () => void;
  onOpenTypeChat: () => void;
  onNavigate: (tab: string) => void;
  onOpenDoctor: () => void;
  onOpenEmergency: () => void;
  onOpenAsha: () => void;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({
  onStartVoiceChat,
  onOpenTypeChat,
  onNavigate,
  onOpenDoctor,
  onOpenEmergency,
  onOpenAsha
}) => {
  const { t } = useLanguage();
  const { user, activeBeneficiary, isGuest } = useCitizenAuth();
  const [homeData, setHomeData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadHomeData = async () => {
      try {
        const res = await apiClient.getCitizenHomeSummary();
        setHomeData(res?.data || res);
      } catch (err) {
        console.error("Failed to load home summary", err);
      } finally {
        setLoading(false);
      }
    };
    loadHomeData();
  }, []);

  const citizenName = activeBeneficiary?.displayName || user?.name || homeData?.citizen_name || (isGuest ? t("citizen.guest_user", "Guest") : "Citizen");
  const activeCase = homeData?.active_case;
  const responsiblePerson = homeData?.responsible_person;

  // Localized role helper
  const getLocalizedRole = (roleKey?: string) => {
    if (!roleKey) return "";
    return t(`roles.${roleKey}`, roleKey);
  };

  // Localized status helper
  const getLocalizedStatus = (statusKey?: string, fallback?: string) => {
    if (!statusKey) return fallback || "";
    return t(`status.${statusKey}`, fallback || statusKey);
  };

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header Info */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 800, color: "#0F172A" }}>
            {t("citizen.welcome_greeting", { name: citizenName.split(" ")[0] })}
          </div>
          <div style={{ fontSize: 13, color: "#64748B", fontWeight: 600 }}>
            {t("citizen.how_can_we_help")}
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4, padding: "4px 8px", borderRadius: 12, backgroundColor: "#DCFCE7", color: "#166534", fontSize: 11, fontWeight: 700 }}>
            <Wifi size={12} /> {t("common.live")}
          </div>
          <button style={{ border: "none", background: "#F1F5F9", padding: 8, borderRadius: "50%", cursor: "pointer", position: "relative" }}>
            <Bell size={18} color="#334155" />
            {homeData?.unread_notifications_count > 0 && (
              <span style={{ position: "absolute", top: 2, right: 2, width: 8, height: 8, borderRadius: "50%", backgroundColor: "#EF4444" }} />
            )}
          </button>
        </div>
      </div>

      {/* Voice-First Main Action Box */}
      <div
        style={{
          backgroundColor: "#EFF6FF",
          borderRadius: 24,
          padding: "24px 16px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          border: "2px solid #BFDBFE",
          boxShadow: "0 8px 24px rgba(37, 99, 235, 0.12)",
          textAlign: "center"
        }}
      >
        <button
          onClick={onStartVoiceChat}
          style={{
            width: 100,
            height: 100,
            borderRadius: "50%",
            backgroundColor: "#2563EB",
            color: "#FFFFFF",
            border: "6px solid #93C5FD",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            marginBottom: 12,
            boxShadow: "0 8px 24px rgba(37, 99, 235, 0.35)",
            transition: "transform 0.15s ease"
          }}
        >
          <Mic size={44} />
        </button>

        <div style={{ fontSize: 18, fontWeight: 800, color: "#1E3A8A", marginBottom: 2 }}>
          {t("citizen.speak")}
        </div>
        <div style={{ fontSize: 12, color: "#3B82F6", fontWeight: 600, marginBottom: 14 }}>
          {t("citizen.tap_to_talk_hint")}
        </div>

        <button
          onClick={onOpenTypeChat}
          style={{
            padding: "8px 18px",
            borderRadius: 20,
            backgroundColor: "#FFFFFF",
            border: "1px solid #93C5FD",
            color: "#1D4ED8",
            fontSize: 13,
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            gap: 6,
            cursor: "pointer"
          }}
        >
          <Keyboard size={16} />
          {t("citizen.type_action")}
        </button>
      </div>

      {/* Primary Action Buttons */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <button
          id="btn-home-speak-to-doctor"
          onClick={onOpenDoctor}
          style={{
            padding: "16px",
            borderRadius: 18,
            backgroundColor: "#F0FDF4",
            border: "1.5px solid #86EFAC",
            display: "flex",
            flexDirection: "column",
            gap: 8,
            cursor: "pointer",
            textAlign: "left"
          }}
        >
          <div style={{ width: 36, height: 36, borderRadius: "50%", backgroundColor: "#DCFCE7", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Stethoscope size={20} color="#166534" />
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: "#14532D" }}>{t("citizen.speak_to_doctor")}</div>
            <div style={{ fontSize: 12, color: "#166534", fontWeight: 600 }}>{t("roles.PHC_DOCTOR")}</div>
          </div>
        </button>

        <button
          onClick={onOpenEmergency}
          style={{
            padding: "16px",
            borderRadius: 18,
            backgroundColor: "#FEF2F2",
            border: "1.5px solid #FCA5A5",
            display: "flex",
            flexDirection: "column",
            gap: 8,
            cursor: "pointer",
            textAlign: "left"
          }}
        >
          <div style={{ width: 36, height: 36, borderRadius: "50%", backgroundColor: "#FEE2E2", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <AlertTriangle size={20} color="#991B1B" />
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: "#7F1D1D" }}>{t("citizen.emergency_help")}</div>
            <div style={{ fontSize: 12, color: "#991B1B", fontWeight: 600 }}>{t("citizen.call_108_ambulance")}</div>
          </div>
        </button>

        <button
          onClick={onOpenAsha}
          style={{
            padding: "14px",
            borderRadius: 16,
            backgroundColor: "#F8FAFC",
            border: "1px solid #E2E8F0",
            display: "flex",
            alignItems: "center",
            gap: 12,
            cursor: "pointer",
            textAlign: "left"
          }}
        >
          <div style={{ width: 34, height: 34, borderRadius: "50%", backgroundColor: "#E2E8F0", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <UserCheck size={18} color="#334155" />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#1E293B" }}>{t("citizen.call_asha")}</div>
            <div style={{ fontSize: 11, color: "#64748B" }}>Sita Patel</div>
          </div>
        </button>

        <button
          id="btn-home-find-health-centre"
          onClick={() => onNavigate("facilities")}
          style={{
            padding: "14px",
            borderRadius: 16,
            backgroundColor: "#F8FAFC",
            border: "1px solid #E2E8F0",
            display: "flex",
            alignItems: "center",
            gap: 12,
            cursor: "pointer",
            textAlign: "left"
          }}
        >
          <div style={{ width: 34, height: 34, borderRadius: "50%", backgroundColor: "#E2E8F0", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <MapPin size={18} color="#334155" />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#1E293B" }}>{t("citizen.find_health_center_card")}</div>
            <div style={{ fontSize: 11, color: "#64748B" }}>{t("citizen.nearby_phc")}</div>
          </div>
        </button>
      </div>

      {/* Active Care Episode Card */}
      {activeCase ? (
        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0", boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <span style={{ fontSize: 11, fontWeight: 800, padding: "3px 8px", borderRadius: 10, backgroundColor: "#DBEAFE", color: "#1E40AF" }}>
              {t("citizen.active_care")}
            </span>
            <span style={{ fontSize: 11, color: "#64748B" }}>{t("citizen.reference")}: {activeCase.reference}</span>
          </div>

          <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", marginBottom: 4 }}>
            {activeCase.primary_concern}
          </div>
          <div style={{ fontSize: 13, color: "#2563EB", fontWeight: 700, marginBottom: 12 }}>
            {t("common.status")}: {getLocalizedStatus(activeCase.status, activeCase.display_status)}
          </div>

          {responsiblePerson && (
            <div style={{ fontSize: 12, color: "#475569", backgroundColor: "#F8FAFC", padding: 8, borderRadius: 10, marginBottom: 10 }}>
              👤 {t("citizen.assigned")}: <strong>{responsiblePerson.name}</strong> ({getLocalizedRole(responsiblePerson.role)})
            </div>
          )}

          <button
            onClick={() => onNavigate("care")}
            style={{
              width: "100%",
              padding: "10px",
              borderRadius: 12,
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
            {t("citizen.track_care_progress")} <ChevronRight size={16} />
          </button>
        </div>
      ) : (
        <div style={{ backgroundColor: "#F8FAFC", padding: 14, borderRadius: 16, border: "1px dashed #CBD5E1", textAlign: "center", color: "#64748B", fontSize: 13 }}>
          {t("citizen.no_active_case")}
        </div>
      )}

      {/* Extra Services Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <button
          id="btn-home-govt-schemes"
          onClick={() => onNavigate("schemes")}
          style={{ padding: 12, borderRadius: 14, border: "1px solid #E2E8F0", backgroundColor: "#FFFFFF", display: "flex", alignItems: "center", gap: 10, cursor: "pointer", textAlign: "left" }}
        >

          <Award size={20} color="#D97706" />
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#1E293B" }}>{t("citizen.govt_schemes")}</div>
            <div style={{ fontSize: 11, color: "#64748B" }}>{t("citizen.pmjay_and_more")}</div>
          </div>
        </button>

        <button
          onClick={() => onNavigate("medicines")}
          style={{ padding: 12, borderRadius: 14, border: "1px solid #E2E8F0", backgroundColor: "#FFFFFF", display: "flex", alignItems: "center", gap: 10, cursor: "pointer", textAlign: "left" }}
        >
          <Pill size={20} color="#7C3AED" />
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#1E293B" }}>{t("citizen.my_medicines")}</div>
            <div style={{ fontSize: 11, color: "#64748B" }}>{t("citizen.prescriptions_sub")}</div>
          </div>
        </button>
      </div>
    </div>
  );
};

