import React, { useState, useEffect } from "react";
import { useLanguage } from "@aarogya/i18n";
import {
  Clock, Users, User, Building, Phone, Video, Send, Plus,
  AlertTriangle, CheckCircle, RefreshCw, X, MessageSquare, ArrowRight
} from "lucide-react";
import { apiClient } from "@aarogya/api-client";

interface DoctorWaitingRoomScreenProps {
  requestId: string;
  onJoinConsultation: () => void;
  onViewSummary: () => void;
  onBackToHome: () => void;
}

export const DoctorWaitingRoomScreen: React.FC<DoctorWaitingRoomScreenProps> = ({
  requestId,
  onJoinConsultation,
  onViewSummary,
  onBackToHome
}) => {
  const { t, locale } = useLanguage();

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [chatMessage, setChatMessage] = useState("");
  const [showSymptomModal, setShowSymptomModal] = useState(false);
  const [newSymptomText, setNewSymptomText] = useState("");

  const fetchStatus = async () => {
    try {
      const res = await apiClient.getDoctorRequest(requestId);
      const detail = res?.data || res;
      setData(detail);
      if (detail.status === "IN_CONSULTATION") {
        onJoinConsultation();
      } else if (detail.status === "COMPLETED") {
        onViewSummary();
      }
    } catch (err) {
      console.error("Failed to fetch request status", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000); // Live polling fallback
    return () => clearInterval(interval);
  }, [requestId]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;
    try {
      await apiClient.sendDoctorRequestMessage(requestId, chatMessage.trim());
      setChatMessage("");
      fetchStatus();
    } catch (err) {
      console.error("Failed to send message", err);
    }
  };

  const handleUpdateSymptoms = async () => {
    if (!newSymptomText.trim()) return;
    try {
      await apiClient.updateDoctorRequestSymptoms(requestId, [newSymptomText.trim()]);
      setNewSymptomText("");
      setShowSymptomModal(false);
      fetchStatus();
    } catch (err) {
      console.error("Failed to update symptoms", err);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm("Are you sure you want to cancel this request?")) return;
    try {
      await apiClient.cancelDoctorRequest(requestId, "Cancelled by citizen");
      onBackToHome();
    } catch (err) {
      console.error("Failed to cancel request", err);
    }
  };

  if (loading && !data) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "#64748B", fontSize: 14 }}>
        Loading Doctor Waiting Room...
      </div>
    );
  }

  const isAccepted = data?.status === "DOCTOR_ACCEPTED" || data?.status === "READY_TO_CONNECT";

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F8FAFC", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{ backgroundColor: "#1565C0", color: "#FFFFFF", padding: "16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800 }}>PHC Doctor Waiting Room</div>
          <div style={{ fontSize: 11, opacity: 0.9 }}>Ref: {data?.public_reference || requestId}</div>
        </div>
        <button
          onClick={handleCancel}
          style={{ padding: "6px 12px", backgroundColor: "rgba(255,255,255,0.2)", border: "none", color: "#FFFFFF", borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: "pointer" }}
        >
          Cancel
        </button>
      </div>

      <div style={{ flex: 1, padding: 16, display: "flex", flexDirection: "column", gap: 14, maxWidth: 480, margin: "0 auto", width: "100%" }}>
        {/* Status Hero Card */}
        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 20, border: "1px solid #E2E8F0", textAlign: "center", boxShadow: "0 4px 16px rgba(0,0,0,0.04)" }}>
          {isAccepted ? (
            <div>
              <div style={{ width: 64, height: 64, borderRadius: "50%", backgroundColor: "#DCFCE7", color: "#166534", margin: "0 auto 12px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <CheckCircle size={36} />
              </div>
              <h3 style={{ fontSize: 18, fontWeight: 800, color: "#166534", margin: "0 0 6px" }}>
                Doctor Accepted Your Request!
              </h3>
              <p style={{ fontSize: 13, color: "#475569", margin: "0 0 16px" }}>
                Dr. {data?.doctor?.name || "Medical Officer"} is ready to connect with you.
              </p>
              <button
                onClick={onJoinConsultation}
                style={{
                  width: "100%",
                  padding: "14px",
                  backgroundColor: "#16A34A",
                  color: "#FFFFFF",
                  fontWeight: 800,
                  fontSize: 16,
                  borderRadius: 16,
                  border: "none",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  boxShadow: "0 4px 16px rgba(22, 163, 74, 0.3)"
                }}
              >
                <Phone size={20} />
                <span>{t("doctor.join_call", "Join Consultation Now")}</span>
              </button>
            </div>
          ) : (
            <div>
              <div style={{ width: 64, height: 64, borderRadius: "50%", backgroundColor: "#DBEAFE", color: "#2563EB", margin: "0 auto 12px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Clock size={36} className="animate-spin" />
              </div>
              <h3 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: "0 0 6px" }}>
                {t("status.WAITING_FOR_DOCTOR", "Waiting for PHC Doctor...")}
              </h3>
              <p style={{ fontSize: 13, color: "#64748B", margin: "0 0 14px" }}>
                {t("facility.phc", "Primary Health Centre")} • #{data?.queue_position || 1}
              </p>
              <div style={{ display: "flex", justifyContent: "center", gap: 20, borderTop: "1px solid #F1F5F9", paddingTop: 14 }}>
                <div>
                  <div style={{ fontSize: 11, color: "#64748B", fontWeight: 700 }}>{t("doctor.queue", "Queue Position")}</div>
                  <div style={{ fontSize: 20, fontWeight: 900, color: "#2563EB" }}>
                    {data?.queue_position !== undefined && data?.queue_position !== null ? `#${data.queue_position}` : "#1"}
                  </div>
                </div>
                <div style={{ width: 1, backgroundColor: "#E2E8F0" }} />
                <div>
                  <div style={{ fontSize: 11, color: "#64748B", fontWeight: 700 }}>{t("doctor.estimated_wait", "Estimated Wait")}</div>
                  <div style={{ fontSize: 13, fontWeight: 800, color: "#475569", marginTop: 4 }}>
                    {typeof data?.estimated_wait_minutes === "number"
                      ? `~${data.estimated_wait_minutes} min`
                      : "Waiting time unavailable"}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Patient & Concern Summary */}
        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 16, padding: 14, border: "1px solid #E2E8F0" }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: "#64748B", marginBottom: 6 }}>PATIENT & CONCERN</div>
          <div style={{ fontSize: 14, fontWeight: 800, color: "#0F172A" }}>{data?.patient?.name} ({data?.patient?.relationship})</div>
          <div style={{ fontSize: 13, color: "#475569", marginTop: 4 }}>"{data?.chief_complaint}"</div>
          
          <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
            <button
              onClick={() => setShowSymptomModal(true)}
              style={{ padding: "6px 12px", backgroundColor: "#EFF6FF", color: "#2563EB", border: "1px solid #BFDBFE", borderRadius: 10, fontSize: 12, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
            >
              <Plus size={14} /> Update Symptoms
            </button>
            <a
              href="tel:108"
              style={{ padding: "6px 12px", backgroundColor: "#FEF2F2", color: "#DC2626", border: "1px solid #FECACA", borderRadius: 10, fontSize: 12, fontWeight: 700, textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}
            >
              <AlertTriangle size={14} /> 108 Emergency
            </a>
          </div>
        </div>

        {/* In-Waiting Room Chat / Messages */}
        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 16, padding: 14, border: "1px solid #E2E8F0", flex: 1, display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: "#64748B", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
            <MessageSquare size={14} /> Doctor Updates & Messages
          </div>

          <div style={{ flex: 1, minHeight: 120, maxHeight: 180, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, padding: 4 }}>
            {(!data?.messages || data.messages.length === 0) ? (
              <div style={{ fontSize: 12, color: "#94A3B8", textAlign: "center", margin: "auto" }}>
                No messages yet. Send a note to the doctor while waiting.
              </div>
            ) : (
              data.messages.map((m: any) => (
                <div
                  key={m.id}
                  style={{
                    alignSelf: m.sender_type === "CITIZEN" ? "flex-end" : "flex-start",
                    backgroundColor: m.sender_type === "CITIZEN" ? "#2563EB" : "#F1F5F9",
                    color: m.sender_type === "CITIZEN" ? "#FFFFFF" : "#0F172A",
                    padding: "8px 12px",
                    borderRadius: 12,
                    fontSize: 13,
                    maxWidth: "80%"
                  }}
                >
                  <div style={{ fontSize: 10, opacity: 0.8, marginBottom: 2 }}>{m.sender_name}</div>
                  <div>{m.message_text}</div>
                </div>
              ))
            )}
          </div>

          <form onSubmit={handleSendMessage} style={{ display: "flex", gap: 8, marginTop: 10 }}>
            <input
              type="text"
              value={chatMessage}
              onChange={(e) => setChatMessage(e.target.value)}
              placeholder="Send message to doctor..."
              style={{ flex: 1, padding: "8px 12px", borderRadius: 10, border: "1px solid #CBD5E1", fontSize: 13, outline: "none" }}
            />
            <button
              type="submit"
              style={{ padding: "8px 14px", backgroundColor: "#2563EB", color: "#FFFFFF", border: "none", borderRadius: 10, cursor: "pointer" }}
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>

      {/* Symptom Update Modal */}
      {showSymptomModal && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: 16 }}>
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 20, width: "100%", maxWidth: 380 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ fontSize: 16, fontWeight: 800 }}>Update Symptoms</div>
              <button onClick={() => setShowSymptomModal(false)} style={{ border: "none", background: "transparent", cursor: "pointer" }}>
                <X size={20} />
              </button>
            </div>
            <p style={{ fontSize: 13, color: "#64748B", margin: "0 0 10px" }}>
              Are you experiencing any new or worsening symptoms?
            </p>
            <input
              type="text"
              value={newSymptomText}
              onChange={(e) => setNewSymptomText(e.target.value)}
              placeholder="e.g. Fever increased, dizziness..."
              style={{ width: "100%", padding: 10, borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginBottom: 14 }}
            />
            <button
              onClick={handleUpdateSymptoms}
              style={{ width: "100%", padding: 12, backgroundColor: "#2563EB", color: "#FFFFFF", fontWeight: 800, borderRadius: 12, border: "none", cursor: "pointer" }}
            >
              Submit & Re-triage
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
