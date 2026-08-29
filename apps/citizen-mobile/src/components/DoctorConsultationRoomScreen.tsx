import React, { useState, useEffect } from "react";
import { useLanguage } from "@aarogya/i18n";
import { Phone, PhoneOff, Mic, MicOff, Video, Volume2, Shield, User, MessageSquare } from "lucide-react";
import { apiClient } from "@aarogya/api-client";

interface DoctorConsultationRoomScreenProps {
  requestId: string;
  onEndConsultation: () => void;
}

export const DoctorConsultationRoomScreen: React.FC<DoctorConsultationRoomScreenProps> = ({
  requestId,
  onEndConsultation
}) => {
  const { t, locale } = useLanguage();

  const [data, setData] = useState<any>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [callDuration, setCallDuration] = useState(0);

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const res = await apiClient.getDoctorRequest(requestId);
        setData(res?.data || res);
      } catch (err) {
        console.error("Failed to load consultation", err);
      }
    };
    fetchDetail();

    const timer = setInterval(() => {
      setCallDuration((d) => d + 1);
    }, 1000);

    const checkInterval = setInterval(async () => {
      try {
        const res = await apiClient.getDoctorRequest(requestId);
        const detail = res?.data || res;
        if (detail.status === "COMPLETED") {
          onEndConsultation();
        }
      } catch (err) {}
    }, 3000);

    return () => {
      clearInterval(timer);
      clearInterval(checkInterval);
    };
  }, [requestId]);

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0F172A", color: "#FFFFFF", display: "flex", flexDirection: "column", justifyContent: "space-between", padding: 20 }}>
      {/* Top Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 10, height: 10, borderRadius: "50%", backgroundColor: "#22C55E", animation: "pulse 1.5s infinite" }} />
          <span style={{ fontSize: 13, fontWeight: 700, color: "#86EFAC" }}>Live Teleconsultation (Simulated WebRTC)</span>
        </div>
        <div style={{ fontSize: 14, fontWeight: 800, backgroundColor: "rgba(255,255,255,0.1)", padding: "4px 10px", borderRadius: 12 }}>
          {formatDuration(callDuration)}
        </div>
      </div>

      {/* Middle Doctor Call Visualizer */}
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
        <div style={{ position: "relative" }}>
          <div style={{ width: 120, height: 120, borderRadius: "50%", backgroundColor: "#1E293B", border: "4px solid #2563EB", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 54, boxShadow: "0 0 32px rgba(37, 99, 235, 0.4)" }}>
            👨‍⚕️
          </div>
          <div style={{ position: "absolute", bottom: 0, right: 0, backgroundColor: "#2563EB", padding: 6, borderRadius: "50%", border: "2px solid #0F172A" }}>
            <Shield size={16} />
          </div>
        </div>

        <div>
          <h2 style={{ fontSize: 22, fontWeight: 900, margin: "0 0 4px" }}>
            {data?.doctor?.name || "Dr. Abhinav Sharma"}
          </h2>
          <div style={{ fontSize: 13, color: "#94A3B8" }}>
            Medical Officer • Kalyanpur PHC
          </div>
          <div style={{ fontSize: 12, color: "#38BDF8", marginTop: 4, fontWeight: 600 }}>
            Patient: {data?.patient?.name || "Sunita Devi"} ({data?.patient?.relationship || "Self"})
          </div>
        </div>

        {/* Audio Waveform Bars Simulation */}
        <div style={{ display: "flex", alignItems: "center", gap: 4, height: 32 }}>
          {[16, 28, 12, 32, 20, 30, 14, 24, 18].map((h, i) => (
            <div
              key={i}
              style={{
                width: 4,
                height: `${h}px`,
                backgroundColor: "#38BDF8",
                borderRadius: 4,
                animation: `pulse 0.8s ease-in-out infinite alternate ${i * 0.1}s`
              }}
            />
          ))}
        </div>
      </div>

      {/* Bottom Controls */}
      <div style={{ display: "flex", justifyContent: "center", gap: 20, paddingBottom: 20 }}>
        <button
          onClick={() => setIsMuted(!isMuted)}
          style={{
            width: 60,
            height: 60,
            borderRadius: "50%",
            backgroundColor: isMuted ? "#DC2626" : "rgba(255,255,255,0.15)",
            border: "none",
            color: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer"
          }}
        >
          {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
        </button>

        <button
          onClick={onEndConsultation}
          style={{
            width: 60,
            height: 60,
            borderRadius: "50%",
            backgroundColor: "#DC2626",
            border: "none",
            color: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            boxShadow: "0 0 20px rgba(220, 38, 38, 0.5)"
          }}
        >
          <PhoneOff size={24} />
        </button>
      </div>
    </div>
  );
};
