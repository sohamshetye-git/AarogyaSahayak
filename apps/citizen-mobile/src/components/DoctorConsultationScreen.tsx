import React, { useState } from "react";
import { Stethoscope, PhoneCall, Headphones, CheckCircle2, FileText, ArrowLeft, Clock } from "lucide-react";
import { useLanguage } from "@aarogya/i18n";
import { apiClient } from "@aarogya/api-client";

interface DoctorConsultationScreenProps {
  onBack: () => void;
}

export const DoctorConsultationScreen: React.FC<DoctorConsultationScreenProps> = ({ onBack }) => {
  const { t } = useLanguage();
  const [complaint, setComplaint] = useState("Severe headache and shortness of breath since morning.");
  const [requestType, setRequestType] = useState<"TELECONSULTATION" | "CALLBACK">("TELECONSULTATION");
  const [requested, setRequested] = useState(false);
  const [loading, setLoading] = useState(false);
  const [requestData, setRequestData] = useState<any>(null);

  const handleRequestDoctor = async () => {
    setLoading(true);
    try {
      const res = await apiClient.createCitizenDoctorRequest({
        chief_complaint: complaint,
        request_type: requestType,
        symptoms: ["headache", "shortness of breath"],
        idempotency_key: `DOC-REQ-${Date.now()}`
      });
      setRequestData(res?.data || res);
      setRequested(true);
    } catch (err) {
      console.error("Failed to request doctor", err);
      setRequested(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Top Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button onClick={onBack} style={{ border: "none", background: "#F1F5F9", padding: 8, borderRadius: "50%", cursor: "pointer" }}>
          <ArrowLeft size={20} color="#334155" />
        </button>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: 0 }}>
            {t("citizen.speak_to_doctor", "Doctor Consultation")}
          </h2>
          <div style={{ fontSize: 12, color: "#64748B" }}>Kalyanpur PHC</div>
        </div>
      </div>

      {/* Doctor Card */}
      <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 56, height: 56, borderRadius: "50%", backgroundColor: "#DBEAFE", border: "2px solid #2563EB", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, fontWeight: 800, color: "#1D4ED8" }}>
            👨‍⚕️
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 16, fontWeight: 800, color: "#0F172A" }}>Dr. Abhinav Sharma</span>
              <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 6px", borderRadius: 8, backgroundColor: "#DCFCE7", color: "#166534" }}>✓ {t("scheme.verified_eligible", "Verified")}</span>
            </div>
            <div style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>{t("roles.PHC_DOCTOR")}, Kalyanpur PHC</div>
            <div style={{ fontSize: 11, color: "#166534", fontWeight: 700, marginTop: 4 }}>🟢 {t("common.live", "Live")}</div>
          </div>
        </div>
      </div>

      {!requested ? (
        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B" }}>
            {t("citizen.speak_to_doctor", "Request Doctor Teleconsultation")}
          </div>

          <div>
            <label style={{ fontSize: 12, fontWeight: 700, color: "#475569", display: "block", marginBottom: 6 }}>
              {t("citizen.how_can_we_help", "What is your primary health concern?")}
            </label>
            <textarea
              value={complaint}
              onChange={(e) => setComplaint(e.target.value)}
              rows={3}
              style={{ width: "100%", padding: 10, borderRadius: 12, border: "1px solid #CBD5E1", fontSize: 14, fontFamily: "inherit" }}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <button
              onClick={() => setRequestType("TELECONSULTATION")}
              style={{
                padding: "12px",
                borderRadius: 14,
                border: requestType === "TELECONSULTATION" ? "2px solid #2563EB" : "1px solid #CBD5E1",
                backgroundColor: requestType === "TELECONSULTATION" ? "#EFF6FF" : "#FFFFFF",
                color: requestType === "TELECONSULTATION" ? "#1E40AF" : "#475569",
                fontWeight: 700,
                fontSize: 13,
                cursor: "pointer"
              }}
            >
              🎧 {t("common.speak", "Audio Call")}
            </button>

            <button
              onClick={() => setRequestType("CALLBACK")}
              style={{
                padding: "12px",
                borderRadius: 14,
                border: requestType === "CALLBACK" ? "2px solid #2563EB" : "1px solid #CBD5E1",
                backgroundColor: requestType === "CALLBACK" ? "#EFF6FF" : "#FFFFFF",
                color: requestType === "CALLBACK" ? "#1E40AF" : "#475569",
                fontWeight: 700,
                fontSize: 13,
                cursor: "pointer"
              }}
            >
              📞 {t("citizen.call_asha", "Callback")}
            </button>
          </div>

          <button
            onClick={handleRequestDoctor}
            disabled={loading}
            style={{
              width: "100%",
              padding: "16px",
              borderRadius: 16,
              backgroundColor: "#2563EB",
              color: "#FFFFFF",
              fontSize: 15,
              fontWeight: 800,
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              boxShadow: "0 4px 16px rgba(37, 99, 235, 0.3)"
            }}
          >
            <Stethoscope size={20} />
            {loading ? t("loading.submitting", "Sending...") : t("citizen.speak_to_doctor", "Connect to Doctor")}
          </button>
        </div>
      ) : (
        <div style={{ backgroundColor: "#F0FDF4", borderRadius: 20, padding: 16, border: "2px solid #86EFAC", display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, color: "#166534", fontWeight: 800, fontSize: 16 }}>
            <CheckCircle2 size={24} color="#166534" />
            {t("messages.SUCCESS", "Doctor Request Submitted!")}
          </div>

          <div style={{ fontSize: 13, color: "#14532D" }}>
            {t("facility.phc", "Primary Health Centre")} • #{requestData?.id || "DOC-1"}
          </div>

          <button
            onClick={() => alert("Connecting live audio consultation stream...")}
            style={{
              width: "100%",
              padding: "16px",
              borderRadius: 16,
              backgroundColor: "#166534",
              color: "#FFFFFF",
              fontSize: 16,
              fontWeight: 800,
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
              boxShadow: "0 4px 16px rgba(22, 101, 52, 0.3)"
            }}
          >
            <Headphones size={22} />
            {t("doctor.join_call", "Join Audio Consultation")}
          </button>

          <div style={{ fontSize: 12, color: "#64748B", textAlign: "center" }}>
            {t("citizen.call_108_ambulance", "Helpline: 108")}
          </div>
        </div>
      )}
    </div>
  );
};

