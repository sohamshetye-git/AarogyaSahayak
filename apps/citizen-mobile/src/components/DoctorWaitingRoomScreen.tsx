import React, { useState, useEffect, useRef } from "react";
import { useLanguage } from "@aarogya/i18n";
import {
  Clock, Users, User, Building, Phone, Video, Send, Plus,
  AlertTriangle, CheckCircle, RefreshCw, X, MessageSquare, ArrowRight,
  MapPin, Calendar, Check, ExternalLink, ShieldCheck, CheckCheck, RotateCcw,
  FileText, Wifi, WifiOff, Loader2
} from "lucide-react";
import { apiClient } from "@aarogya/api-client";
import { realtimeService } from "../services/realtimeService";

interface DoctorWaitingRoomScreenProps {
  requestId: string;
  onJoinConsultation: () => void;
  onViewSummary: () => void;
  onBackToHome: () => void;
}

interface LocalChatMessage {
  id: string;
  conversation_id?: string;
  service_request_id?: string;
  sender_role: "CITIZEN" | "PHC_DOCTOR" | "SYSTEM";
  sender_type?: string;
  sender_name?: string;
  body: string;
  message_text?: string;
  client_message_id: string;
  status: "SENDING" | "SENT" | "DELIVERED" | "READ" | "FAILED";
  created_at: string;
}

const formatDoctorName = (name?: string | null): string => {
  if (!name || name.trim() === "") return "PHC Medical Officer";
  let trimmed = name.trim();
  while (trimmed.toLowerCase().startsWith("dr. ") || trimmed.toLowerCase().startsWith("dr ")) {
    if (trimmed.toLowerCase().startsWith("dr. ")) {
      trimmed = trimmed.substring(4).trim();
    } else if (trimmed.toLowerCase().startsWith("dr ")) {
      trimmed = trimmed.substring(3).trim();
    }
  }
  return `Dr. ${trimmed}`;
};

export const DoctorWaitingRoomScreen: React.FC<DoctorWaitingRoomScreenProps> = ({
  requestId,
  onJoinConsultation,
  onViewSummary,
  onBackToHome
}) => {
  const { t, locale } = useLanguage();

  const [data, setData] = useState<any>(null);
  const [messages, setMessages] = useState<LocalChatMessage[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [chatMessage, setChatMessage] = useState("");
  const [showSymptomModal, setShowSymptomModal] = useState(false);
  const [newSymptomText, setNewSymptomText] = useState("");
  const [isSubmittingMessage, setIsSubmittingMessage] = useState(false);
  const [isUpdatingSymptoms, setIsUpdatingSymptoms] = useState(false);
  const [symptomModalError, setSymptomModalError] = useState<string | null>(null);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);
  const [connectionState, setConnectionState] = useState<"ONLINE" | "RECONNECTING" | "OFFLINE">("ONLINE");

  const chatScrollRef = useRef<HTMLDivElement>(null);
  const canonicalConversationIdRef = useRef<string>(requestId);

  const fetchStatus = async () => {
    try {
      let detail: any = null;
      let threadData: any = null;

      // 1. Try canonical /citizen/doctor/requests/{requestId} endpoint
      try {
        const res = await apiClient.getCitizenDoctorRequest(requestId);
        threadData = res?.data || res;
        if (threadData?.thread) {
          detail = {
            ...threadData.request_details,
            ...threadData.thread,
            messages: threadData.messages || threadData.thread.messages || []
          };
          canonicalConversationIdRef.current = threadData.thread.id || threadData.thread.conversation_id || requestId;
        } else if (threadData) {
          detail = threadData;
          canonicalConversationIdRef.current = threadData.id || threadData.conversation_id || requestId;
        }
      } catch (err) {
        // Fallback to /care-requests/{requestId}/conversation
        try {
          const threadRes = await apiClient.getDoctorChatThread(requestId);
          threadData = threadRes?.data || threadRes;
          if (threadData?.thread) {
            detail = {
              ...threadData.request_details,
              ...threadData.thread,
              messages: threadData.messages || threadData.thread.messages || []
            };
            canonicalConversationIdRef.current = threadData.thread.id || threadData.thread.conversation_id || requestId;
          } else if (threadData) {
            detail = threadData;
            canonicalConversationIdRef.current = threadData.id || threadData.conversation_id || requestId;
          }
        } catch (_2) {
          try {
            const sRes = await apiClient.getCitizenServiceRequestDetail(requestId);
            detail = sRes?.data || sRes;
            if (detail?.conversation_id || detail?.id) {
              canonicalConversationIdRef.current = detail.conversation_id || detail.id;
            }
          } catch (_3) {
            console.error("Failed to load doctor request:", _3);
          }
        }
      }

      if (detail && (detail.id || detail.request_id || detail.service_request_id || detail.request_reference || detail.chief_complaint || detail.chief_concern)) {
        setData(detail);

        // Merge server messages with local optimistic messages
        if (Array.isArray(detail.messages)) {
          setMessages((prevLocal) => {
            const serverMsgs: LocalChatMessage[] = detail.messages.map((m: any) => ({
              id: m.id || m.client_message_id || `srv-${Math.random()}`,
              conversation_id: m.conversation_id || detail.id,
              service_request_id: m.service_request_id || detail.service_request_id,
              sender_role: m.sender_role || (m.sender_type === "DOCTOR" ? "PHC_DOCTOR" : "CITIZEN"),
              sender_type: m.sender_type || (m.sender_role === "PHC_DOCTOR" ? "DOCTOR" : "CITIZEN"),
              sender_name: m.sender_name,
              body: m.body || m.message_text || "",
              message_text: m.message_text || m.body || "",
              client_message_id: m.client_message_id || m.id,
              status: m.status || "DELIVERED",
              created_at: m.created_at || new Date().toISOString()
            }));

            // Keep any currently SENDING or FAILED messages that haven't landed yet
            const pendingOptimistic = prevLocal.filter(
              (p) => (p.status === "SENDING" || p.status === "FAILED") &&
                     !serverMsgs.some((s) => s.client_message_id === p.client_message_id || s.id === p.id)
            );

            // Deduplicate by message id & client_message_id
            const seen = new Set<string>();
            const deduplicated: LocalChatMessage[] = [];
            for (const msg of [...serverMsgs, ...pendingOptimistic]) {
              const key = msg.client_message_id || msg.id;
              if (!seen.has(key)) {
                seen.add(key);
                deduplicated.push(msg);
              }
            }

            deduplicated.sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""));
            return deduplicated;
          });
        }

        if (detail.status === "IN_CONSULTATION") {
          if (detail.channel === "AUDIO" || detail.channel === "VIDEO" || detail.requested_channel === "AUDIO" || detail.requested_channel === "VIDEO") {
            onJoinConsultation();
          }
        }
      }
    } catch (err) {
      console.error("Failed to fetch request status", err);
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and Realtime WebSocket setup
  useEffect(() => {
    fetchStatus();

    // Connect WebSocket
    realtimeService.connect();

    // Subscribe to realtime domain events
    const unsubscribe = realtimeService.subscribe((event: string, eventData: any) => {
      if (event === "REALTIME_STATE") {
        const state = eventData.status === "ONLINE" ? "ONLINE" : (eventData.status === "RECONNECTING" ? "RECONNECTING" : "OFFLINE");
        setConnectionState(state);
        if (state === "ONLINE") {
          fetchStatus();
        }
        return;
      }

      if (
        event === "conversation.message.created" ||
        event === "doctor_chat.message_created" ||
        event === "CHAT_MESSAGE_CREATED" ||
        event === "DOCTOR_REQUEST_MESSAGE_SENT"
      ) {
        const convId = eventData?.conversation_id || eventData?.request_id;
        const srvId = eventData?.service_request_id;
        
        // Match event against our active conversation or service request
        if (
          convId === canonicalConversationIdRef.current ||
          convId === requestId ||
          srvId === requestId ||
          srvId === data?.service_request_id ||
          eventData?.request_reference === data?.request_reference
        ) {
          const newMsg: LocalChatMessage = {
            id: eventData.id || eventData.message_id || `msg-${Date.now()}`,
            conversation_id: convId,
            service_request_id: srvId,
            sender_role: eventData.sender_role || (eventData.sender_type === "DOCTOR" ? "PHC_DOCTOR" : "CITIZEN"),
            sender_type: eventData.sender_type,
            sender_name: eventData.sender_name,
            body: eventData.body || eventData.message_text || "",
            message_text: eventData.message_text || eventData.body || "",
            client_message_id: eventData.client_message_id || eventData.id,
            status: eventData.status || "DELIVERED",
            created_at: eventData.created_at || new Date().toISOString()
          };

          setMessages((prev) => {
            const exists = prev.some(
              (m) => m.client_message_id === newMsg.client_message_id || m.id === newMsg.id
            );
            if (exists) {
              return prev.map((m) =>
                m.client_message_id === newMsg.client_message_id || m.id === newMsg.id
                  ? { ...m, ...newMsg, status: newMsg.status }
                  : m
              );
            }
            const updated = [...prev, newMsg];
            updated.sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""));
            return updated;
          });

          // If doctor sent the message, mark it read
          if (newMsg.sender_role === "PHC_DOCTOR") {
            apiClient.markDoctorChatRead(canonicalConversationIdRef.current, newMsg.id).catch(() => {});
          }
        }
      }

      if (
        event === "conversation.message.read" ||
        event === "doctor_chat.message_read" ||
        event === "CHAT_MESSAGE_READ"
      ) {
        if (eventData?.conversation_id === canonicalConversationIdRef.current || eventData?.conversation_id === requestId) {
          setMessages((prev) =>
            prev.map((m) => (m.sender_role === "CITIZEN" ? { ...m, status: "READ" } : m))
          );
        }
      }

      if (
        event === "DOCTOR_REQUEST_ACCEPTED" ||
        event === "CONSULTATION_STARTED" ||
        event === "CONSULTATION_COMPLETED" ||
        event === "DOCTOR_DIRECT_REQUEST_STATUS_UPDATED" ||
        event === "REQUEST_CONTEXT_UPDATED" ||
        event === "CARE_HANDOFF_UPDATED"
      ) {
        fetchStatus();
      }
    });

    // 3s Polling fallback to guarantee zero message loss
    const interval = setInterval(fetchStatus, 3000);

    return () => {
      unsubscribe();
      clearInterval(interval);
    };
  }, [requestId]);

  // Auto-scroll to bottom of chat when new messages appear
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSendMessage = async (e?: React.FormEvent, retryMsg?: LocalChatMessage) => {
    if (e) e.preventDefault();
    const textToSend = retryMsg ? retryMsg.body : chatMessage.trim();
    if (!textToSend || isSubmittingMessage) return;

    const clientMsgId = retryMsg?.client_message_id || `cmsg-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    const conversationId = canonicalConversationIdRef.current || requestId;

    // Optimistically append message to state
    if (!retryMsg) {
      const optimisticMsg: LocalChatMessage = {
        id: clientMsgId,
        conversation_id: conversationId,
        sender_role: "CITIZEN",
        sender_type: "CITIZEN",
        sender_name: data?.beneficiary?.name || data?.beneficiary_name || data?.patient?.name || t("common.you", "You"),
        body: textToSend,
        message_text: textToSend,
        client_message_id: clientMsgId,
        status: "SENDING",
        created_at: new Date().toISOString()
      };
      setMessages((prev) => [...prev, optimisticMsg]);
      setChatMessage("");
    } else {
      setMessages((prev) =>
        prev.map((m) => (m.client_message_id === retryMsg.client_message_id ? { ...m, status: "SENDING" } : m))
      );
    }

    setIsSubmittingMessage(true);
    setErrorNotice(null);

    try {
      let res: any = null;
      try {
        res = await apiClient.sendDoctorChatMessage(conversationId, textToSend, clientMsgId);
      } catch (err1) {
        // Fallback to request-ref chat endpoint
        res = await apiClient.sendDoctorRequestChatMessage(requestId, textToSend, clientMsgId);
      }
      const resData = res?.data || res;

      // Update message to server-confirmed state
      setMessages((prev) =>
        prev.map((m) =>
          m.client_message_id === clientMsgId
            ? {
                ...m,
                id: resData.id || m.id,
                conversation_id: resData.conversation_id || conversationId,
                status: resData.status || "DELIVERED",
                created_at: resData.created_at || m.created_at
              }
            : m
        )
      );
    } catch (err: any) {
      console.error("Failed to send citizen chat message", err);
      setMessages((prev) =>
        prev.map((m) => (m.client_message_id === clientMsgId ? { ...m, status: "FAILED" } : m))
      );
      const errMsg = err?.message || err?.error?.message || t("waiting_room.send_failed", "Message failed to send. Tap Retry to send again.");
      setErrorNotice(errMsg);
    } finally {
      setIsSubmittingMessage(false);
    }
  };

  const handleUpdateSymptoms = async () => {
    const trimmed = newSymptomText.trim();
    if (!trimmed) {
      setSymptomModalError(t("waiting_room.symptom_empty_error", "Please enter a symptom description."));
      return;
    }

    setIsUpdatingSymptoms(true);
    setSymptomModalError(null);

    try {
      await apiClient.updateDoctorRequestSymptoms(requestId, [trimmed]);
      setNewSymptomText("");
      setShowSymptomModal(false);
      setSymptomModalError(null);
      await fetchStatus();
    } catch (err: any) {
      console.error("Failed to update symptoms", err);
      const safeMsg = err?.message || err?.error?.message || t("waiting_room.update_symptom_failed", "Failed to update symptoms. Please tap Retry.");
      setSymptomModalError(safeMsg);
    } finally {
      setIsUpdatingSymptoms(false);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm(t("common.confirm_cancel", "Are you sure you want to cancel this consultation request?"))) return;
    try {
      try {
        await apiClient.cancelCitizenServiceRequest(requestId, "Cancelled by citizen");
      } catch (_) {
        await apiClient.cancelDoctorRequest(requestId, "Cancelled by citizen");
      }
      onBackToHome();
    } catch (err) {
      console.error("Failed to cancel request", err);
    }
  };

  if (!requestId) {
    return (
      <div style={{ minHeight: "100vh", backgroundColor: "#F8FAFC", display: "flex", flexDirection: "column" }}>
        <div style={{ backgroundColor: "#1565C0", color: "#FFFFFF", padding: "16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: 16, fontWeight: 800 }}>{t("waiting_room.title", "PHC Doctor Waiting Room")}</div>
          <button
            id="btn-waiting-room-home"
            onClick={onBackToHome}
            style={{ padding: "6px 12px", backgroundColor: "rgba(255,255,255,0.2)", border: "none", color: "#FFFFFF", borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: "pointer" }}
          >
            {t("navigation.home", "Home")}
          </button>
        </div>
        <div style={{ padding: 48, textAlign: "center", color: "#64748B", fontSize: 14 }}>
          <MessageSquare size={36} style={{ margin: "0 auto 12px", color: "#94A3B8" }} />
          <div style={{ fontSize: 15, fontWeight: 700, color: "#1E293B", marginBottom: 6 }}>
            {t("waiting_room.no_active_consultation", "No active consultation selected")}
          </div>
          <div style={{ fontSize: 13, color: "#64748B", marginBottom: 16 }}>
            {t("waiting_room.start_from_home", "Please request a consultation from Home or select a consultation in My Care.")}
          </div>
          <button
            onClick={onBackToHome}
            style={{ padding: "10px 20px", backgroundColor: "#2563EB", color: "#FFFFFF", border: "none", borderRadius: 12, fontWeight: 700, cursor: "pointer" }}
          >
            {t("navigation.home", "Back to Home")}
          </button>
        </div>
      </div>
    );
  }

  if (loading && !data) {
    return (
      <div style={{ minHeight: "100vh", backgroundColor: "#F8FAFC", display: "flex", flexDirection: "column" }}>
        <div style={{ backgroundColor: "#1565C0", color: "#FFFFFF", padding: "16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: 16, fontWeight: 800 }}>{t("waiting_room.title", "PHC Doctor Waiting Room")}</div>
          <button
            id="btn-waiting-room-home"
            onClick={onBackToHome}
            style={{ padding: "6px 12px", backgroundColor: "rgba(255,255,255,0.2)", border: "none", color: "#FFFFFF", borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: "pointer" }}
          >
            {t("navigation.home", "Home")}
          </button>
        </div>
        <div style={{ padding: 48, textAlign: "center", color: "#64748B", fontSize: 14 }}>
          <Loader2 size={36} className="animate-spin" style={{ margin: "0 auto 12px", color: "#2563EB" }} />
          <div>{t("loading.loading_data", "Connecting with Medical Officer...")}</div>
        </div>
      </div>
    );
  }

  if (!data && !loading) {
    return (
      <div style={{ minHeight: "100vh", backgroundColor: "#F8FAFC", display: "flex", flexDirection: "column" }}>
        <div style={{ backgroundColor: "#1565C0", color: "#FFFFFF", padding: "16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: 16, fontWeight: 800 }}>{t("waiting_room.title", "PHC Doctor Waiting Room")}</div>
          <button
            id="btn-waiting-room-home"
            onClick={onBackToHome}
            style={{ padding: "6px 12px", backgroundColor: "rgba(255,255,255,0.2)", border: "none", color: "#FFFFFF", borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: "pointer" }}
          >
            {t("navigation.home", "Home")}
          </button>
        </div>
        <div style={{ padding: 48, textAlign: "center", color: "#64748B", fontSize: 14 }}>
          <AlertTriangle size={36} style={{ margin: "0 auto 12px", color: "#DC2626" }} />
          <div style={{ fontSize: 15, fontWeight: 700, color: "#1E293B", marginBottom: 6 }}>
            {t("waiting_room.consultation_not_found", "Consultation record could not be loaded")}
          </div>
          <div style={{ fontSize: 13, color: "#64748B", marginBottom: 16 }}>
            {errorNotice || t("waiting_room.retry_or_home", "Please verify your connection and try again.")}
          </div>
          <button
            onClick={fetchStatus}
            style={{ padding: "10px 20px", backgroundColor: "#2563EB", color: "#FFFFFF", border: "none", borderRadius: 12, fontWeight: 700, cursor: "pointer", marginRight: 8 }}
          >
            {t("common.retry", "Retry")}
          </button>
          <button
            onClick={onBackToHome}
            style={{ padding: "10px 20px", backgroundColor: "#F1F5F9", color: "#1E293B", border: "1px solid #CBD5E1", borderRadius: 12, fontWeight: 700, cursor: "pointer" }}
          >
            {t("navigation.home", "Back to Home")}
          </button>
        </div>
      </div>
    );
  }

  const channel = String(data?.requested_channel || data?.channel || data?.mode || "CHAT").toUpperCase();
  const isChatMode = channel === "CHAT" || channel === "DOCTOR_CHAT" || channel === "CHAT_ADVICE" || (channel !== "AUDIO" && channel !== "VIDEO" && channel !== "CALLBACK" && channel !== "IN_PERSON_PHC");
  const isCallbackMode = channel === "CALLBACK";
  const isPhcMode = channel === "IN_PERSON_PHC";
  const isAccepted = data?.status === "DOCTOR_ACCEPTED" || data?.status === "IN_CONSULTATION" || data?.status === "READY_TO_CONNECT";
  const isCompleted = data?.status === "COMPLETED";
  const rawName = data?.beneficiary?.name || data?.beneficiary_name || data?.patient?.name || data?.beneficiary?.displayName || data?.citizen_name || "";
  const patientName = (rawName && rawName.trim().toLowerCase() !== "self" && rawName.trim().toLowerCase() !== "myself") ? rawName : (data?.citizen_name || "Patient");
  const phone = data?.citizen?.phone || data?.patient?.phone || data?.citizen_phone || data?.phone || "";

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F8FAFC", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{ backgroundColor: "#1565C0", color: "#FFFFFF", padding: "14px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800 }}>{t("waiting_room.title", "PHC Doctor Waiting Room")}</div>
          <div style={{ fontSize: 11, opacity: 0.9 }}>
            {t("waiting_room.ref", "Ref:")} <span style={{ fontFamily: "monospace", fontWeight: 700 }}>{data?.request_reference || data?.public_reference || requestId}</span>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Connection Status Indicator */}
          <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 700 }}>
            {connectionState === "ONLINE" ? (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#86EFAC" }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", backgroundColor: "#22C55E", boxShadow: "0 0 6px #22C55E" }} />
                {t("common.connected", "Live")}
              </span>
            ) : connectionState === "RECONNECTING" ? (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#FDE047" }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", backgroundColor: "#EAB308" }} />
                {t("common.reconnecting", "Reconnecting...")}
              </span>
            ) : (
              <span style={{ display: "inline-flex", alignItems: "center", gap: 4, color: "#FCA5A5" }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", backgroundColor: "#EF4444" }} />
                {t("common.offline", "Offline")}
              </span>
            )}
          </div>
          <button
            id="btn-waiting-room-home"
            onClick={onBackToHome}
            style={{ padding: "6px 12px", backgroundColor: "rgba(255,255,255,0.2)", border: "none", color: "#FFFFFF", borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: "pointer" }}
          >
            {t("navigation.home", "Home")}
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, padding: "14px", display: "flex", flexDirection: "column", gap: 12, maxWidth: 640, margin: "0 auto", width: "100%", boxSizing: "border-box" }}>
        
        {/* Channel: CHAT Mode (Doctor Chat Advice) */}
        {isChatMode && (
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0", flex: 1, display: "flex", flexDirection: "column", minHeight: 420, boxShadow: "0 4px 16px rgba(0,0,0,0.03)" }}>
            
            {/* Header / Doctor Status Banner */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: 12, borderBottom: "1px solid #F1F5F9", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ width: 38, height: 38, borderRadius: "50%", backgroundColor: isAccepted ? "#DCFCE7" : "#DBEAFE", color: isAccepted ? "#16A34A" : "#2563EB", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <MessageSquare size={20} />
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: "#0F172A" }}>
                    {formatDoctorName(data?.doctor?.name || data?.assigned_doctor_name || data?.doctor_name)}
                  </div>
                  <div style={{ fontSize: 11, color: isCompleted ? "#64748B" : (isAccepted ? "#16A34A" : "#D97706"), fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", backgroundColor: isCompleted ? "#94A3B8" : (isAccepted ? "#16A34A" : "#F59E0B") }} />
                    {isCompleted
                      ? t("status.COMPLETED", "Consultation Completed")
                      : (isAccepted
                          ? t("waiting_room.online_ready", "Doctor Accepted • Online")
                          : t("waiting_room.awaiting_doctor", "Awaiting Doctor Connection"))}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {isCompleted && (
                  <button
                    onClick={onViewSummary}
                    style={{ padding: "6px 12px", backgroundColor: "#EDE9FE", color: "#7C3AED", border: "1px solid #DDD6FE", borderRadius: 10, fontSize: 12, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
                  >
                    <FileText size={14} /> {t("care.view_plan", "View Care Plan")}
                  </button>
                )}
              </div>
            </div>

            {/* Error Notice */}
            {errorNotice && (
              <div style={{ padding: "8px 12px", backgroundColor: "#FEF2F2", border: "1px solid #FECACA", borderRadius: 10, color: "#DC2626", fontSize: 12, fontWeight: 600, marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                <AlertTriangle size={14} />
                <span>{errorNotice}</span>
              </div>
            )}

            {/* Chat Thread Bubbles */}
            <div
              ref={chatScrollRef}
              style={{ flex: 1, minHeight: 250, maxHeight: 380, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10, padding: "6px 2px" }}
            >
              {messages.length === 0 ? (
                <div style={{ fontSize: 13, color: "#94A3B8", textAlign: "center", margin: "auto", maxWidth: 280, padding: "20px 0" }}>
                  <MessageSquare size={32} style={{ margin: "0 auto 8px", opacity: 0.4 }} />
                  {t("waiting_room.chat_empty_prompt", "Start writing your health questions or symptoms. The doctor will reply directly here.")}
                </div>
              ) : (
                messages.map((m) => {
                  const isCitizenMsg = m.sender_role === "CITIZEN" || m.sender_type === "CITIZEN" || m.sender_type === "PATIENT";
                  return (
                    <div
                      key={m.id || m.client_message_id}
                      style={{
                        alignSelf: isCitizenMsg ? "flex-end" : "flex-start",
                        backgroundColor: isCitizenMsg ? (m.status === "FAILED" ? "#FEF2F2" : "#2563EB") : "#F1F5F9",
                        color: isCitizenMsg ? (m.status === "FAILED" ? "#991B1B" : "#FFFFFF") : "#0F172A",
                        border: m.status === "FAILED" ? "1px solid #FCA5A5" : "none",
                        padding: "10px 14px",
                        borderRadius: 16,
                        borderBottomRightRadius: isCitizenMsg ? 4 : 16,
                        borderBottomLeftRadius: isCitizenMsg ? 16 : 4,
                        fontSize: 13,
                        maxWidth: "85%",
                        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
                        wordBreak: "break-word"
                      }}
                    >
                      <div style={{ fontSize: 10, opacity: 0.85, marginBottom: 3, fontWeight: 700, display: "flex", justifyContent: "space-between", gap: 8 }}>
                        <span>{isCitizenMsg ? (m.sender_name || t("common.you", "You")) : (formatDoctorName(m.sender_name) || t("common.doctor", "Dr. Medical Officer"))}</span>
                        <span>
                          {m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}
                        </span>
                      </div>
                      <div style={{ fontSize: 13, lineHeight: 1.4 }}>{m.body || m.message_text}</div>

                      {/* Delivery Status Indicator for outgoing citizen messages */}
                      {isCitizenMsg && (
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 4, marginTop: 4, fontSize: 10, opacity: 0.9 }}>
                          {m.status === "SENDING" && (
                            <span style={{ fontStyle: "italic" }}>{t("chat.sending", "Sending...")}</span>
                          )}
                          {m.status === "SENT" && (
                            <Check size={12} />
                          )}
                          {(m.status === "DELIVERED" || !m.status) && (
                            <CheckCheck size={12} />
                          )}
                          {m.status === "READ" && (
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 2, color: "#93C5FD" }}>
                              <CheckCheck size={12} /> {t("chat.read", "Read")}
                            </span>
                          )}
                          {m.status === "FAILED" && (
                            <button
                              type="button"
                              onClick={() => handleSendMessage(undefined, m)}
                              style={{ border: "none", background: "none", color: "#DC2626", fontWeight: 800, fontSize: 11, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 3, textDecoration: "underline", padding: 0 }}
                            >
                              <RotateCcw size={11} /> {t("common.retry", "Retry")}
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            {/* Input Composer */}
            {isCompleted ? (
              <div style={{ marginTop: 12, padding: "12px", backgroundColor: "#F8FAFC", borderRadius: 12, border: "1px solid #E2E8F0", textAlign: "center", fontSize: 12, color: "#64748B", fontWeight: 700 }}>
                {t("waiting_room.consultation_closed", "This consultation is completed and archived. You can view your clinical notes and prescriptions in My Care.")}
              </div>
            ) : (
              <form onSubmit={(e) => handleSendMessage(e)} style={{ display: "flex", gap: 8, marginTop: 12, paddingTop: 10, borderTop: "1px solid #F1F5F9" }}>
                <input
                  type="text"
                  id="input-citizen-chat-message"
                  value={chatMessage}
                  disabled={loading || isSubmittingMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  placeholder={loading ? t("waiting_room.loading_chat", "Loading chat session...") : t("waiting_room.message_placeholder", "Type your query or describe symptoms...")}
                  style={{ flex: 1, padding: "10px 14px", borderRadius: 12, border: "1px solid #CBD5E1", fontSize: 13, outline: "none" }}
                />
                <button
                  type="submit"
                  id="btn-citizen-send-chat"
                  disabled={isSubmittingMessage || !chatMessage.trim() || loading}
                  style={{ padding: "10px 16px", backgroundColor: (!chatMessage.trim() || loading) ? "#94A3B8" : "#2563EB", color: "#FFFFFF", border: "none", borderRadius: 12, cursor: (!chatMessage.trim() || loading) ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", transition: "background 0.2s" }}
                >
                  <Send size={16} />
                </button>
              </form>
            )}
          </div>
        )}

        {/* Channel: CALLBACK Mode (Phone Callback) */}
        {isCallbackMode && (
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 20, border: "1px solid #E2E8F0", boxShadow: "0 4px 16px rgba(0,0,0,0.03)", display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 44, height: 44, borderRadius: "50%", backgroundColor: "#DBEAFE", color: "#2563EB", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Phone size={22} />
              </div>
              <div>
                <div style={{ fontSize: 16, fontWeight: 800, color: "#0F172A" }}>
                  {t("waiting_room.callback_title", "Phone Consultation Callback")}
                </div>
                <div style={{ fontSize: 12, color: "#64748B" }}>
                  {data?.assigned_facility || "Kalyanpur Primary Health Centre (PHC)"}
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: "#F8FAFC", borderRadius: 14, padding: 14, border: "1px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <span style={{ color: "#64748B" }}>{t("waiting_room.callback_status", "Callback Status")}:</span>
                <span style={{ fontWeight: 800, color: isAccepted ? "#16A34A" : "#D97706" }}>
                  {isAccepted ? t("waiting_room.call_queued", "Doctor Assigned • Calling Soon") : t("waiting_room.waiting_doctor", "Waiting for Medical Officer")}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <span style={{ color: "#64748B" }}>{t("waiting_room.phone_number", "Calling Number")}:</span>
                <span style={{ fontWeight: 700, color: "#0F172A", fontFamily: "monospace" }}>{phone || "+91 98230 12345"}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <span style={{ color: "#64748B" }}>{t("waiting_room.est_wait", "Estimated Time")}:</span>
                <span style={{ fontWeight: 700, color: "#0F172A" }}>{t("waiting_room.est_wait_time", "10 - 15 minutes")}</span>
              </div>
            </div>

            <p style={{ fontSize: 12, color: "#64748B", margin: 0, lineHeight: 1.5 }}>
              {t("waiting_room.callback_instruction", "The PHC Medical Officer will call you on your registered phone number. Please keep your phone reachable and answer when called.")}
            </p>
          </div>
        )}

        {/* Channel: IN_PERSON_PHC Mode (PHC OPD Visit) */}
        {isPhcMode && (
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 20, border: "1px solid #E2E8F0", boxShadow: "0 4px 16px rgba(0,0,0,0.03)", display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 44, height: 44, borderRadius: "50%", backgroundColor: "#DCFCE7", color: "#16A34A", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Building size={22} />
              </div>
              <div>
                <div style={{ fontSize: 16, fontWeight: 800, color: "#0F172A" }}>
                  {t("waiting_room.phc_visit_title", "PHC OPD In-Person Visit")}
                </div>
                <div style={{ fontSize: 12, color: "#64748B" }}>
                  {data?.assigned_facility || "Kalyanpur Primary Health Centre (PHC)"}
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: "#F8FAFC", borderRadius: 14, padding: 14, border: "1px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <span style={{ color: "#64748B" }}>{t("waiting_room.token_number", "OPD Token Reference")}:</span>
                <span style={{ fontWeight: 800, color: "#1E40AF", fontFamily: "monospace" }}>{data?.request_reference || requestId}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <span style={{ color: "#64748B" }}>{t("waiting_room.opd_timings", "OPD Timings")}:</span>
                <span style={{ fontWeight: 700, color: "#0F172A" }}>09:00 AM - 02:00 PM</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <span style={{ color: "#64748B" }}>{t("waiting_room.facility_location", "Facility Location")}:</span>
                <span style={{ fontWeight: 700, color: "#0F172A" }}>Kalyanpur PHC Main Building</span>
              </div>
            </div>

            <p style={{ fontSize: 12, color: "#64748B", margin: 0, lineHeight: 1.5 }}>
              {t("waiting_room.phc_instructions", "Please present this digital token reference at the PHC OPD Registration Counter upon your arrival. Direct priority queueing applies.")}
            </p>
          </div>
        )}

        {/* Patient & Concern Summary Card */}
        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 16, padding: 14, border: "1px solid #E2E8F0" }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: "#64748B", marginBottom: 6 }}>{t("waiting_room.patient_concern_title", "PATIENT & CONCERN")}</div>
          <div style={{ fontSize: 14, fontWeight: 800, color: "#0F172A" }}>
            {patientName}
          </div>
          <div style={{ fontSize: 13, color: "#475569", marginTop: 4 }}>
            "{data?.chief_complaint || data?.chief_concern || data?.details?.chief_complaint || t("concerns.GENERAL_HEALTH_GUIDANCE", "General health checkup / care guidance")}"
          </div>
          
          {!isCompleted && (
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <button
                id="btn-waiting-room-update-symptoms"
                onClick={() => {
                  setSymptomModalError(null);
                  setShowSymptomModal(true);
                }}
                style={{ padding: "6px 12px", backgroundColor: "#EFF6FF", color: "#2563EB", border: "1px solid #BFDBFE", borderRadius: 10, fontSize: 12, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
              >
                <Plus size={14} /> {t("waiting_room.update_symptoms", "Update Symptoms")}
              </button>
              <a
                href="tel:108"
                style={{ padding: "6px 12px", backgroundColor: "#FEF2F2", color: "#DC2626", border: "1px solid #FECACA", borderRadius: 10, fontSize: 12, fontWeight: 700, textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}
              >
                <AlertTriangle size={14} /> {t("waiting_room.emergency_108", "108 Emergency")}
              </a>
            </div>
          )}
        </div>
      </div>

      {/* Symptom Update Modal */}
      {showSymptomModal && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: 16 }}>
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 20, width: "100%", maxWidth: 380, boxShadow: "0 20px 40px rgba(0,0,0,0.2)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ fontSize: 16, fontWeight: 800 }}>{t("waiting_room.update_symptoms_title", "Update Symptoms")}</div>
              <button onClick={() => !isUpdatingSymptoms && setShowSymptomModal(false)} disabled={isUpdatingSymptoms} style={{ border: "none", background: "transparent", cursor: isUpdatingSymptoms ? "not-allowed" : "pointer" }}>
                <X size={20} />
              </button>
            </div>
            <p style={{ fontSize: 13, color: "#64748B", margin: "0 0 10px" }}>
              {t("waiting_room.update_symptoms_desc", "Are you experiencing any new or worsening symptoms?")}
            </p>
            <input
              type="text"
              id="input-waiting-room-symptom"
              value={newSymptomText}
              disabled={isUpdatingSymptoms}
              onChange={(e) => {
                setNewSymptomText(e.target.value);
                if (symptomModalError) setSymptomModalError(null);
              }}
              placeholder={t("waiting_room.update_symptoms_placeholder", "e.g. Fever increased, dizziness...")}
              style={{ width: "100%", padding: 10, borderRadius: 10, border: `1.5px solid ${symptomModalError ? "#EF4444" : "#CBD5E1"}`, fontSize: 13, marginBottom: 10, boxSizing: "border-box" }}
            />
            {symptomModalError && (
              <div style={{ padding: "6px 10px", backgroundColor: "#FEF2F2", border: "1px solid #FECACA", borderRadius: 8, color: "#DC2626", fontSize: 12, fontWeight: 600, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
                <AlertTriangle size={13} />
                <span>{symptomModalError}</span>
              </div>
            )}
            <button
              id="btn-waiting-room-submit-symptom"
              onClick={handleUpdateSymptoms}
              disabled={isUpdatingSymptoms || !newSymptomText.trim()}
              style={{
                width: "100%",
                padding: 12,
                backgroundColor: (isUpdatingSymptoms || !newSymptomText.trim()) ? "#94A3B8" : "#2563EB",
                color: "#FFFFFF",
                fontWeight: 800,
                borderRadius: 12,
                border: "none",
                cursor: (isUpdatingSymptoms || !newSymptomText.trim()) ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6
              }}
            >
              {isUpdatingSymptoms ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>{t("common.updating", "Updating & Re-triaging...")}</span>
                </>
              ) : (
                <span>{t("waiting_room.submit_retriage", "Submit & Re-triage")}</span>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
