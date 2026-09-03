import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge } from "../../components/StatusBadge";
import {
  Phone, Video, MessageSquare, Clock, CheckCircle, AlertTriangle,
  User, Check, X, ArrowRight, Play, RefreshCw, Filter, FileText, Plus, Trash2, Send, Building
} from "lucide-react";
import { useRealtime } from "../../hooks/useRealtime";
import { useLanguage } from "../../context/LanguageContext";

interface RxItem {
  medicine_name: string;
  formulation: string;
  dosage: string;
  frequency: string;
  duration_days: number;
  instructions: string;
}

interface CustomInvestigationItem {
  test_name: string;
  category: string;
  priority: "ROUTINE" | "URGENT";
  clinical_reason?: string;
  preparation_instructions?: string;
}

export function DirectCitizenRequestsScreen() {
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [requests, setRequests] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>("ALL");
  const [isProcessing, setIsProcessing] = useState<string | null>(null);

  // Complete Consultation Modal State
  const [selectedReq, setSelectedReq] = useState<any>(null);
  const [showCompleteModal, setShowCompleteModal] = useState(false);
  const [diagnosis, setDiagnosis] = useState("Acute Upper Respiratory Infection");
  const [guidance, setGuidance] = useState("Take adequate rest, maintain hydration, and complete prescribed course.");
  const [prescriptions, setPrescriptions] = useState<RxItem[]>([
    {
      medicine_name: "Paracetamol 500mg",
      formulation: "Tablet",
      dosage: "1 tablet",
      frequency: "1-0-1",
      duration_days: 3,
      instructions: "Take after food"
    }
  ]);
  const [labOrders, setLabOrders] = useState<string[]>([]);
  const [customLabOrders, setCustomLabOrders] = useState<CustomInvestigationItem[]>([]);
  const [showAddCustomLabModal, setShowAddCustomLabModal] = useState(false);
  const [newLabTestName, setNewLabTestName] = useState("");
  const [newLabCategory, setNewLabCategory] = useState("PATHOLOGY");
  const [newLabPriority, setNewLabPriority] = useState<"ROUTINE" | "URGENT">("ROUTINE");
  const [newLabClinicalReason, setNewLabClinicalReason] = useState("");
  const [newLabPrepInstructions, setNewLabPrepInstructions] = useState("");
  const [labFormError, setLabFormError] = useState<string | null>(null);

  const [assignAsha, setAssignAsha] = useState(false);
  const [ashaInstructions, setAshaInstructions] = useState("Visit home on Day 3, check temperature and recovery.");

  // Connection status & Realtime hook
  const { connectionStatus } = useRealtime((event, data) => {
    handleRealtimeEvent(event, data);
  });

  // Live Chat Drawer State with stable scalar canonical identities
  const [activeChatReq, setActiveChatReq] = useState<any>(null);
  const activeChatReqRef = React.useRef<any>(null);
  activeChatReqRef.current = activeChatReq;

  // Stable scalar IDs
  const activeConversationId = activeChatReq?.conversation_id || activeChatReq?.id || null;
  const activeServiceRequestId = activeChatReq?.service_request_id || activeChatReq?.id || null;
  const activeRequestRef = activeChatReq?.request_reference || activeChatReq?.public_reference || null;

  const [chatMessage, setChatMessage] = useState("");
  const [sendingMsg, setSendingMsg] = useState(false);
  const [isManualRefreshing, setIsManualRefreshing] = useState(false);
  const [refreshFeedback, setRefreshFeedback] = useState<string | null>(null);
  const chatDrawerScrollRef = React.useRef<HTMLDivElement>(null);
  const isChatPollingRef = React.useRef<boolean>(false);

  // Canonical message merge and deduplication helper
  // Rules: deduplicate primarily by server id / client_message_id, sort by created_at with id as tie-breaker
  const mergeMessagesCanonical = (existing: any[] = [], incoming: any[] = []) => {
    const map = new Map<string, any>();
    for (const m of existing) {
      if (!m) continue;
      const key = m.id || m.client_message_id || m.message_id;
      if (key) map.set(String(key), m);
    }
    for (const m of incoming) {
      if (!m) continue;
      // Reconcile optimistic messages using client_message_id
      const clientKey = m.client_message_id ? String(m.client_message_id) : null;
      const idKey = m.id || m.message_id ? String(m.id || m.message_id) : null;
      
      let matchedKey = (clientKey && map.has(clientKey)) ? clientKey : (idKey && map.has(idKey) ? idKey : null);
      if (matchedKey) {
        const prev = map.get(matchedKey);
        map.set(matchedKey, { ...prev, ...m });
      } else {
        const key = idKey || clientKey;
        if (key) map.set(key, m);
      }
    }
    const combined = Array.from(map.values());
    combined.sort((a, b) => {
      const timeA = new Date(a.created_at || 0).getTime();
      const timeB = new Date(b.created_at || 0).getTime();
      if (timeA !== timeB) return timeA - timeB;
      return String(a.id || "").localeCompare(String(b.id || ""));
    });
    return combined;
  };

  const fetchRequests = async () => {
    try {
      setError(null);
      const res = await apiClient.getDoctorDirectRequests({ status: activeFilter });
      const rawData = res?.data || res;
      const items = Array.isArray(rawData?.items) ? rawData.items : (Array.isArray(rawData) ? rawData : []);
      setRequests(items);

      if (rawData?.counts) {
        setSummary({
          total: rawData.total ?? items.length,
          waiting: rawData.counts.waiting ?? 0,
          urgent: rawData.counts.urgent ?? 0,
          accepted: rawData.counts.accepted ?? 0,
          in_consultation: rawData.counts.in_consultation ?? 0,
          completed: rawData.counts.completed ?? 0
        });
      } else {
        const sum = await apiClient.getDoctorDirectRequestsSummary();
        const sumData = sum?.data || sum;
        if (sumData) {
          setSummary({
            total: sumData.total ?? 0,
            waiting: sumData.waiting ?? sumData.new ?? 0,
            urgent: sumData.urgent ?? 0,
            accepted: sumData.accepted ?? 0,
            in_consultation: sumData.in_consultation ?? 0,
            completed: sumData.completed ?? 0
          });
        }
      }

      // If active chat drawer is open, refresh its status and metadata without losing messages
      const currentActive = activeChatReqRef.current;
      if (currentActive) {
        const updated = items.find((r: any) =>
          r.id === currentActive.id ||
          r.conversation_id === currentActive.conversation_id ||
          r.service_request_id === currentActive.id ||
          r.id === currentActive.service_request_id ||
          (currentActive.request_reference && r.request_reference === currentActive.request_reference)
        );
        if (updated) {
          setActiveChatReq((prev: any) => {
            if (!prev) return prev;
            return {
              ...prev,
              ...updated,
              messages: prev.messages || []
            };
          });
        }
      }
    } catch (err: any) {
      console.error("Failed to load direct requests", err);
      setError(err?.message || "Failed to load requests from server. Please retry.");
    } finally {
      setLoading(false);
    }
  };

  const fetchChatConversation = async (targetId?: string) => {
    const currentActive = activeChatReqRef.current;
    const reqId = targetId || currentActive?.conversation_id || currentActive?.id || currentActive?.service_request_id;
    if (!reqId) return;

    try {
      let detail: any = null;
      try {
        const res = await apiClient.getDoctorDirectRequestDetail(reqId);
        detail = res?.data || res;
      } catch (_) {
        const res = await apiClient.getDoctorChatThread(reqId);
        const threadData = res?.data || res;
        if (threadData?.thread) {
          detail = {
            ...threadData.request_details,
            ...threadData.thread,
            messages: threadData.messages || threadData.thread.messages || []
          };
        } else if (threadData) {
          detail = threadData;
        }
      }

      if (detail) {
        setActiveChatReq((prev: any) => {
          if (!prev) return prev;
          // Ensure target conversation matches current open drawer
          const isTargetMatch =
            !prev.id ||
            prev.id === reqId ||
            prev.conversation_id === reqId ||
            prev.service_request_id === reqId ||
            prev.id === detail.id ||
            prev.conversation_id === detail.conversation_id;
          if (!isTargetMatch) return prev;

          const prevMessages = prev?.messages || [];
          const newMessages = Array.isArray(detail.messages) ? detail.messages : [];
          const merged = mergeMessagesCanonical(prevMessages, newMessages);
          return {
            ...prev,
            ...detail,
            messages: merged
          };
        });
      }
    } catch (err) {
      console.error("Failed to load chat details", err);
      throw err;
    }
  };

  // Realtime WebSocket event normalization & handler
  const handleRealtimeEvent = (event: string, data: any) => {
    const currentActive = activeChatReqRef.current;

    if (
      [
        "DOCTOR_REQUEST_CREATED",
        "DOCTOR_REQUEST_ACCEPTED",
        "CONSULTATION_STARTED",
        "CONSULTATION_COMPLETED",
        "CARE_HANDOFF_UPDATED",
        "REQUEST_CONTEXT_UPDATED",
        "CITIZEN_DOCTOR_REQUEST_SUBMITTED",
        "DOCTOR_DIRECT_REQUEST_STATUS_UPDATED"
      ].includes(event)
    ) {
      fetchRequests();
      if (currentActive) {
        const convId = data?.conversation_id || data?.request_id;
        const srvId = data?.service_request_id;
        if (
          !convId ||
          convId === currentActive.id ||
          convId === currentActive.conversation_id ||
          srvId === currentActive.id ||
          srvId === currentActive.service_request_id ||
          (data?.request_reference && data.request_reference === currentActive.request_reference)
        ) {
          fetchChatConversation(currentActive.conversation_id || currentActive.id);
        }
      }
    }

    if (
      [
        "doctor_chat.message_created",
        "CHAT_MESSAGE_CREATED",
        "DOCTOR_REQUEST_MESSAGE_SENT",
        "conversation.message.created"
      ].includes(event)
    ) {
      fetchRequests();
      if (currentActive && data) {
        const convId = data?.conversation_id || data?.request_id;
        const srvId = data?.service_request_id;
        const reqRef = data?.request_reference;

        const isMatch =
          convId === currentActive.id ||
          convId === currentActive.conversation_id ||
          srvId === currentActive.id ||
          srvId === currentActive.service_request_id ||
          (reqRef && reqRef === currentActive.request_reference);

        if (isMatch) {
          // Normalize incoming message payload
          const incomingMsg = {
            id: data.id || data.message_id || `msg-${Date.now()}`,
            conversation_id: convId || currentActive.conversation_id || currentActive.id,
            service_request_id: srvId || currentActive.service_request_id || currentActive.id,
            sender_role: data.sender_role || (data.sender_type === "DOCTOR" || data.sender_role === "PHC_DOCTOR" ? "PHC_DOCTOR" : "CITIZEN"),
            sender_type: data.sender_type || (data.sender_role === "PHC_DOCTOR" ? "DOCTOR" : "CITIZEN"),
            sender_name: data.sender_name || (data.sender_type === "DOCTOR" || data.sender_role === "PHC_DOCTOR" ? "Dr. Medical Officer" : "Patient"),
            body: data.body || data.message_text || "",
            message_text: data.message_text || data.body || "",
            client_message_id: data.client_message_id || data.id,
            status: data.status || "DELIVERED",
            created_at: data.created_at || new Date().toISOString()
          };

          // Functional update to avoid stale closures
          setActiveChatReq((prev: any) => {
            if (!prev) return prev;
            const updated = mergeMessagesCanonical(prev.messages || [], [incomingMsg]);
            return {
              ...prev,
              messages: updated
            };
          });

          // Mark read if it is from citizen
          if (incomingMsg.sender_role === "CITIZEN" || incomingMsg.sender_type === "CITIZEN") {
            apiClient.markDoctorChatRead(currentActive.conversation_id || currentActive.id, incomingMsg.id).catch(() => {});
          }

          // Background sync for complete consistency
          fetchChatConversation(currentActive.conversation_id || currentActive.id).catch(() => {});
        }
      }
    }

    if (
      [
        "doctor_chat.message_read",
        "CHAT_MESSAGE_READ",
        "conversation.message.read"
      ].includes(event)
    ) {
      if (currentActive && data) {
        const convId = data?.conversation_id || data?.request_id;
        if (convId === currentActive.id || convId === currentActive.conversation_id) {
          setActiveChatReq((prev: any) => {
            if (!prev || !prev.messages) return prev;
            return {
              ...prev,
              messages: prev.messages.map((m: any) =>
                m.sender_role === "PHC_DOCTOR" || m.sender_type === "DOCTOR"
                  ? { ...m, status: "READ" }
                  : m
              )
            };
          });
        }
      }
    }
  };

  // 3-second active chat polling fallback while drawer is open
  useEffect(() => {
    if (!activeChatReq?.id && !activeChatReq?.conversation_id) return;
    const reqId = activeChatReq.conversation_id || activeChatReq.id;

    // Immediately fetch when drawer opens
    fetchChatConversation(reqId).catch(() => {});

    const pollChat = async () => {
      if (isChatPollingRef.current) return;
      isChatPollingRef.current = true;
      try {
        await fetchChatConversation(reqId);
      } catch (err) {
        console.error("Chat polling error", err);
      } finally {
        isChatPollingRef.current = false;
      }
    };

    const chatInterval = setInterval(pollChat, 3000);
    return () => clearInterval(chatInterval);
  }, [activeChatReq?.id, activeChatReq?.conversation_id]);

  // Manual Refresh Chat Action with spinner and feedback toast
  const handleManualRefreshChat = async () => {
    if (!activeChatReq || isManualRefreshing) return;
    setIsManualRefreshing(true);
    setRefreshFeedback(null);
    try {
      const targetId = activeChatReq.conversation_id || activeChatReq.id;
      await fetchChatConversation(targetId);
      setRefreshFeedback("Chat updated");
      setTimeout(() => {
        setRefreshFeedback(null);
      }, 3000);
      if (chatDrawerScrollRef.current) {
        chatDrawerScrollRef.current.scrollTop = chatDrawerScrollRef.current.scrollHeight;
      }
    } catch (err: any) {
      console.error("Manual chat refresh failed", err);
      setRefreshFeedback("Refresh failed. Tap to retry.");
      setTimeout(() => {
        setRefreshFeedback(null);
      }, 4000);
    } finally {
      setIsManualRefreshing(false);
    }
  };

  // Auto-scroll doctor chat drawer when messages change
  React.useEffect(() => {
    if (chatDrawerScrollRef.current) {
      chatDrawerScrollRef.current.scrollTop = chatDrawerScrollRef.current.scrollHeight;
    }
  }, [activeChatReq?.messages?.length]);

  useEffect(() => {
    fetchRequests();
    const interval = setInterval(fetchRequests, 5000);
    return () => clearInterval(interval);
  }, [activeFilter]);

  const handleAccept = async (e: React.MouseEvent, req: any) => {
    e.stopPropagation();
    setIsProcessing(req.id);
    try {
      if ((req.requested_channel || req.mode) === "CHAT") {
        setActiveChatReq(req);
      }
      await apiClient.acceptDoctorDirectRequest(req.id);
      await fetchRequests();
      if ((req.requested_channel || req.mode) === "CHAT") {
        await fetchChatConversation(req.id);
      }
    } catch (err) {
      console.error("Failed to accept request", err);
    } finally {
      setIsProcessing(null);
    }
  };

  const handleStart = async (e: React.MouseEvent, req: any) => {
    e.stopPropagation();
    setIsProcessing(req.id);
    try {
      if ((req.requested_channel || req.mode) === "CHAT") {
        setActiveChatReq(req);
      }
      await apiClient.startDoctorDirectConsultation(req.id);
      await fetchRequests();
      if ((req.requested_channel || req.mode) === "CHAT") {
        await fetchChatConversation(req.id);
      }
    } catch (err) {
      console.error("Failed to start consultation", err);
    } finally {
      setIsProcessing(null);
    }
  };

  const handleOpenChat = async (e: React.MouseEvent, req: any) => {
    e.stopPropagation();
    setActiveChatReq(req);
    await fetchChatConversation(req.id);
  };

  const handleMarkArrived = async (e: React.MouseEvent, reqId: string) => {
    e.stopPropagation();
    setIsProcessing(reqId);
    try {
      await apiClient.patchDoctorDirectRequestStatus(reqId, { action: "START_CONSULTATION" });
      await fetchRequests();
    } catch (err) {
      console.error("Failed to update status", err);
    } finally {
      setIsProcessing(null);
    }
  };

  const handleOpenCompleteModal = (e: React.MouseEvent, req: any) => {
    e.stopPropagation();
    setSelectedReq(req);
    setDiagnosis(req.chief_complaint || "Clinical Assessment Complete");
    setLabOrders([]);
    setCustomLabOrders([]);
    setShowAddCustomLabModal(false);
    setLabFormError(null);
    setShowCompleteModal(true);
  };

  const handleAddCustomLabOrder = () => {
    setLabFormError(null);
    const trimmedName = newLabTestName.trim();
    if (!trimmedName) {
      setLabFormError("Investigation test name is required.");
      return;
    }

    // Check duplicate in standard lab orders
    const existsStandard = labOrders.some(t => t.toLowerCase() === trimmedName.toLowerCase());
    // Check duplicate in custom lab orders
    const existsCustom = customLabOrders.some(c => c.test_name.toLowerCase() === trimmedName.toLowerCase());
    
    if (existsStandard || existsCustom) {
      setLabFormError("This investigation order is already added.");
      return;
    }

    setCustomLabOrders([
      ...customLabOrders,
      {
        test_name: trimmedName,
        category: newLabCategory || "PATHOLOGY",
        priority: newLabPriority || "ROUTINE",
        clinical_reason: newLabClinicalReason.trim() || undefined,
        preparation_instructions: newLabPrepInstructions.trim() || undefined
      }
    ]);

    setNewLabTestName("");
    setNewLabCategory("PATHOLOGY");
    setNewLabPriority("ROUTINE");
    setNewLabClinicalReason("");
    setNewLabPrepInstructions("");
    setShowAddCustomLabModal(false);
  };

  const handleRemoveCustomLabOrder = (index: number) => {
    setCustomLabOrders(customLabOrders.filter((_, i) => i !== index));
  };

  const handleAddRxItem = () => {
    setPrescriptions([
      ...prescriptions,
      {
        medicine_name: "",
        formulation: "Tablet",
        dosage: "1",
        frequency: "1-0-1",
        duration_days: 3,
        instructions: "Take after meals"
      }
    ]);
  };

  const handleRemoveRxItem = (index: number) => {
    setPrescriptions(prescriptions.filter((_, i) => i !== index));
  };

  const handleUpdateRxItem = (index: number, field: keyof RxItem, value: any) => {
    const next = [...prescriptions];
    next[index] = { ...next[index], [field]: value };
    setPrescriptions(next);
  };

  const handleSendDoctorMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim() || sendingMsg || !activeChatReq) return;
    const textToSend = chatMessage.trim();
    const reqId = activeChatReq.id || activeChatReq.conversation_id || activeChatReq.service_request_id;
    const clientMsgId = `dmsg-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;

    // Optimistic local doctor bubble
    const optimisticMsg = {
      id: clientMsgId,
      client_message_id: clientMsgId,
      conversation_id: activeChatReq.id || activeChatReq.conversation_id,
      service_request_id: activeChatReq.service_request_id || activeChatReq.id,
      sender_role: "PHC_DOCTOR",
      sender_type: "DOCTOR",
      sender_name: "Dr. Medical Officer",
      body: textToSend,
      message_text: textToSend,
      status: "SENDING",
      created_at: new Date().toISOString()
    };

    setActiveChatReq((prev: any) => {
      if (!prev) return prev;
      return {
        ...prev,
        messages: mergeMessagesCanonical(prev.messages || [], [optimisticMsg])
      };
    });

    setChatMessage("");
    setSendingMsg(true);

    try {
      try {
        await apiClient.sendDoctorChatMessage(reqId, textToSend, clientMsgId);
      } catch (_) {
        await apiClient.sendDoctorReplyMessage(reqId, textToSend, clientMsgId);
      }
      await fetchChatConversation(reqId);
      await fetchRequests();
    } catch (err) {
      console.error("Failed to send doctor message", err);
    } finally {
      setSendingMsg(false);
    }
  };


  const handleSubmitComplete = async () => {
    if (!selectedReq) return;
    setIsProcessing(selectedReq.id);

    // Combine standard selected lab orders with custom added lab orders
    const combinedInvestigationOrders = [
      ...labOrders.map(test => ({
        test_name: test,
        category: "PATHOLOGY",
        urgency: "ROUTINE",
        priority: "ROUTINE",
        clinical_reason: diagnosis
      })),
      ...customLabOrders.map(c => ({
        test_name: c.test_name,
        category: c.category,
        urgency: c.priority,
        priority: c.priority,
        clinical_reason: c.clinical_reason || diagnosis,
        preparation_instructions: c.preparation_instructions
      }))
    ];

    try {
      await apiClient.completeDoctorDirectConsultation(selectedReq.id, {
        provisional_diagnosis: diagnosis,
        clinical_summary: `${diagnosis}. Consultation completed with Dr. Medical Officer.`,
        patient_guidance: guidance,
        disposition: assignAsha ? "FOLLOW_UP_REQUIRED" : "COMPLETED",
        prescriptions: prescriptions.filter(p => p.medicine_name.trim().length > 0),
        investigation_orders: combinedInvestigationOrders,
        assign_asha_followup: assignAsha,
        asha_task_type: "POST_CONSULTATION_CHECK",
        asha_due_days: 3,
        asha_instructions: ashaInstructions,
        asha_escalation_conditions: "Escalate if symptoms worsen or red flags emerge."
      });
      setShowCompleteModal(false);
      if (activeChatReq?.id === selectedReq.id) {
        setActiveChatReq(null);
      }
      await fetchRequests();
    } catch (err) {
      console.error("Failed to complete consultation", err);
    } finally {
      setIsProcessing(null);
    }
  };

  return (
    <div className="p-6 bg-slate-50 min-h-screen">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-3">
            <span>{t("navigation.direct_requests", "Direct Citizen Teleconsultation Requests")}</span>
            <span className="text-xs font-bold px-3 py-1 bg-blue-100 text-blue-800 rounded-full">
              {t("common.live", "Live Queue")}
            </span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time direct consultation requests from citizens & household members in Kalyanpur PHC catchment area.
          </p>
        </div>

        <button
          onClick={fetchRequests}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 shadow-sm"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          <span>{t("common.refresh", "Refresh")}</span>
        </button>
      </div>

      {/* Error State Banner */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl flex items-center justify-between gap-3 text-red-800">
          <div className="flex items-center gap-3">
            <AlertTriangle className="text-red-600 flex-shrink-0" size={20} />
            <div>
              <div className="text-sm font-bold">Failed to load requests</div>
              <div className="text-xs text-red-600">{error}</div>
            </div>
          </div>
          <button
            onClick={fetchRequests}
            className="px-3 py-1.5 bg-red-600 text-white text-xs font-bold rounded-xl hover:bg-red-700 transition-colors shadow-sm"
          >
            Retry
          </button>
        </div>
      )}

      {/* Metric Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {[
          { id: "ALL", label: "Total Requests", count: summary?.total ?? 0, color: "text-slate-900", bg: "bg-white" },
          { id: "NEW", label: "New / Waiting", count: summary?.waiting ?? summary?.new ?? 0, color: "text-blue-600", bg: "bg-blue-50/50" },
          { id: "URGENT", label: "Urgent Triage", count: summary?.urgent ?? 0, color: "text-red-600", bg: "bg-red-50/50" },
          { id: "ACCEPTED", label: "Accepted", count: summary?.accepted ?? 0, color: "text-emerald-600", bg: "bg-emerald-50/50" },
          { id: "IN_CONSULTATION", label: "In Consultation", count: summary?.in_consultation ?? 0, color: "text-purple-600", bg: "bg-purple-50/50" },
          { id: "COMPLETED", label: "Completed", count: summary?.completed ?? 0, color: "text-slate-600", bg: "bg-slate-100/50" },
        ].map((m) => (
          <button
            key={m.id}
            onClick={() => setActiveFilter(m.id)}
            className={`p-4 rounded-2xl border text-left transition-all ${
              activeFilter === m.id
                ? "border-blue-600 ring-2 ring-blue-500/20 bg-white shadow-md"
                : "border-slate-200 bg-white hover:border-slate-300"
            }`}
          >
            <div className="text-xs font-bold text-slate-500">{m.label}</div>
            <div className={`text-2xl font-black mt-1 ${m.color}`}>{m.count}</div>
          </button>
        ))}
      </div>

      {/* Requests Queue List */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="text-sm font-bold text-slate-700">
            Queue: {requests.length} request(s)
          </div>
        </div>

        {loading && requests.length === 0 ? (
          <div className="p-6 space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse flex flex-col md:flex-row items-start md:items-center justify-between p-4 bg-slate-50 rounded-2xl gap-4">
                <div className="space-y-2 flex-1">
                  <div className="h-4 bg-slate-200 rounded w-1/4"></div>
                  <div className="h-5 bg-slate-200 rounded w-1/2"></div>
                  <div className="h-3 bg-slate-200 rounded w-3/4"></div>
                </div>
                <div className="h-8 bg-slate-200 rounded w-28"></div>
              </div>
            ))}
          </div>
        ) : requests.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <User size={48} className="mx-auto mb-3 opacity-40" />
            <div className="text-base font-bold text-slate-600">No requests in this queue</div>
            <div className="text-xs mt-1">Direct teleconsultation requests from citizens will appear here in real time.</div>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {requests.map((req) => {
              const reqChannel = req.requested_channel || req.mode || "CALLBACK";
              const isCallback = reqChannel === "CALLBACK";
              const isChat = reqChannel === "CHAT";
              const isPhcVisit = reqChannel === "IN_PERSON_PHC";

              return (
                <div
                  key={req.id}
                  className="p-5 hover:bg-slate-50/80 transition-colors flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
                >
                  {/* Patient & Request Meta */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs font-mono font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                        {req.request_reference || req.public_reference || req.id}
                      </span>
                      <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                        req.priority === "EMERGENCY" ? "bg-red-100 text-red-800" :
                        req.priority === "HIGH" || req.priority === "URGENT" ? "bg-orange-100 text-orange-800" :
                        "bg-blue-100 text-blue-800"
                      }`}>
                        {t(`priority.${req.priority}`, req.priority)}
                      </span>
                      <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 flex items-center gap-1">
                        {isCallback && <Phone size={12} />}
                        {isChat && <MessageSquare size={12} />}
                        {isPhcVisit && <Building size={12} />}
                        <span>{t(`consultation.channel.${reqChannel}`, reqChannel)}</span>
                      </span>
                      <span className="text-xs font-semibold text-slate-400">
                        {t("common.village", "Village")}: {req.village_name || "Kalyanpur"}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 flex-wrap">
                      <div className="text-base font-extrabold text-slate-900">
                        {(req.beneficiary_name && req.beneficiary_name.trim().toLowerCase() !== "self" && req.beneficiary_name.trim().toLowerCase() !== "myself") ? req.beneficiary_name : (req.citizen_name || req.patient?.name || "Patient")}
                        <span className="text-sm font-normal text-slate-500 ml-1.5">
                          ({t(`beneficiary.relationship.${req.beneficiary_relationship || req.patient?.relationship || "SELF"}`, req.beneficiary_relationship || req.patient?.relationship || "Self")} • {req.village_name || "Kalyanpur"})
                        </span>
                      </div>

                      {req.patient_profile_id || req.patient_id || req.citizen_id ? (
                        <Link
                          to={`/doctor/patients/${req.patient_profile_id || req.patient_id || req.citizen_id}?returnTo=/doctor/direct-requests`}
                          className="text-xs font-bold text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1 bg-blue-50/60 hover:bg-blue-100/80 px-2 py-1 rounded-lg border border-blue-200/60 transition-colors"
                          title="Open complete longitudinal patient record"
                        >
                          <span>{t("patient.view_details", "View Patient Record")}</span>
                          <ArrowRight size={12} />
                        </Link>
                      ) : (
                        <span
                          className="text-xs font-medium text-slate-400 inline-flex items-center gap-1 bg-slate-100 px-2 py-1 rounded-lg cursor-not-allowed"
                          title="Patient profile relationship unavailable"
                        >
                          <span>{t("common.value.UNKNOWN", "Record unavailable")}</span>
                        </span>
                      )}
                    </div>

                    <div className="text-sm text-slate-700 mt-1 font-medium">
                      "{req.chief_complaint || req.chief_concern || "Care Handoff Request"}"
                    </div>

                    {req.citizen_summary && (
                      <div className="text-xs text-slate-500 mt-1 italic">
                        Confirmed summary: {req.citizen_summary}
                      </div>
                    )}
                  </div>

                  {/* Channel-Specific Status & Action Buttons */}
                  <div className="flex items-center gap-2 flex-wrap self-end md:self-center">
                    {/* Status Badge */}
                    <span className="text-xs font-bold px-3 py-1 rounded-full bg-slate-100 text-slate-700">
                      {t("common.status", "Status")}: {t(`status.${req.status}`, req.status)}
                    </span>

                    {/* NEW / WAITING */}
                    {(req.status === "WAITING_FOR_DOCTOR" || req.status === "SUBMITTED" || req.status === "NEW") && (
                      <button
                        onClick={(e) => handleAccept(e, req)}
                        disabled={isProcessing === req.id}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm"
                      >
                        <Check size={14} />
                        <span>
                          {isCallback ? "Accept & Call" : (isChat ? "Accept & Open Chat" : "Accept OPD Appointment")}
                        </span>
                      </button>
                    )}

                    {/* ACCEPTED */}
                    {req.status === "DOCTOR_ACCEPTED" && (
                      <div className="flex items-center gap-2">
                        {isCallback && req.citizen_phone && (
                          <a
                            href={`tel:${req.citizen_phone}`}
                            onClick={(e) => handleStart(e, req)}
                            className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm"
                          >
                            <Phone size={13} />
                            <span>Call ({req.citizen_phone})</span>
                          </a>
                        )}

                        {isChat && (
                          <button
                            onClick={() => setActiveChatReq(req)}
                            className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm"
                          >
                            <MessageSquare size={13} />
                            <span>Open Chat</span>
                          </button>
                        )}

                        <button
                          onClick={(e) => handleStart(e, req)}
                          disabled={isProcessing === req.id}
                          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm"
                        >
                          <Play size={14} />
                          <span>{isPhcVisit ? "Mark Arrived & Start" : t("doctor.start_consultation", "Start Consultation")}</span>
                        </button>
                      </div>
                    )}

                    {/* IN_CONSULTATION */}
                    {req.status === "IN_CONSULTATION" && (
                      <div className="flex items-center gap-2">
                        {isChat && (
                          <button
                            onClick={() => setActiveChatReq(req)}
                            className="px-3.5 py-2 bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 rounded-xl text-xs font-bold flex items-center gap-1.5"
                          >
                            <MessageSquare size={13} />
                            <span>Live Chat</span>
                          </button>
                        )}
                        <button
                          onClick={(e) => handleOpenCompleteModal(e, req)}
                          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm"
                        >
                          <FileText size={14} /> Complete & Prescribe
                        </button>
                      </div>
                    )}

                    {/* COMPLETED */}
                    {req.status === "COMPLETED" && (
                      <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200 flex items-center gap-1">
                        <CheckCircle size={14} /> Completed
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Live Chat Drawer for CHAT channel */}
      {activeChatReq && (
        <div className="fixed inset-y-0 right-0 max-w-lg w-full bg-white shadow-2xl z-50 border-l border-slate-200 flex flex-col sm:rounded-l-2xl">
          <div className="p-4 bg-gradient-to-r from-blue-600 to-indigo-700 text-white flex items-center justify-between shadow-md">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center font-bold">
                <MessageSquare size={20} />
              </div>
              <div>
                <div className="text-sm font-black flex items-center gap-2 flex-wrap">
                  <span>
                    {(activeChatReq.beneficiary_name && activeChatReq.beneficiary_name.trim().toLowerCase() !== "self" && activeChatReq.beneficiary_name.trim().toLowerCase() !== "myself") ? activeChatReq.beneficiary_name : (activeChatReq.citizen_name || "Patient Consultation")}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/40 border border-white/20 uppercase font-bold">
                    {activeChatReq.status || "ACTIVE"}
                  </span>
                  {/* Connection Status Badge */}
                  <span
                    id="doctor-chat-connection-status"
                    className={`text-[10px] px-2 py-0.5 rounded-full font-bold flex items-center gap-1 border ${
                      connectionStatus === "ONLINE"
                        ? "bg-emerald-500/30 text-emerald-100 border-emerald-300/40"
                        : connectionStatus === "RECONNECTING"
                        ? "bg-amber-500/30 text-amber-100 border-amber-300/40 animate-pulse"
                        : "bg-sky-500/30 text-sky-100 border-sky-300/40"
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      connectionStatus === "ONLINE" ? "bg-emerald-400" : (connectionStatus === "RECONNECTING" ? "bg-amber-400" : "bg-sky-400")
                    }`} />
                    {connectionStatus === "ONLINE" ? "Live" : (connectionStatus === "RECONNECTING" ? "Reconnecting" : "Polling")}
                  </span>
                </div>
                <div className="text-[11px] opacity-85 font-mono">
                  {activeChatReq.request_reference || activeChatReq.public_reference || activeChatReq.id}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Manual Refresh Chat Fallback Button */}
              <button
                id="btn-refresh-doctor-chat"
                type="button"
                onClick={handleManualRefreshChat}
                disabled={isManualRefreshing}
                className="px-2.5 py-1.5 bg-white/15 hover:bg-white/25 active:bg-white/30 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all border border-white/20 disabled:opacity-50"
                title="Manually fetch latest messages"
              >
                <RefreshCw size={13} className={isManualRefreshing ? "animate-spin" : ""} />
                <span>{isManualRefreshing ? "Refreshing…" : "Refresh Chat"}</span>
              </button>

              <button
                id="btn-close-doctor-chat-drawer"
                onClick={() => setActiveChatReq(null)}
                className="p-1.5 hover:bg-white/20 rounded-xl transition-colors text-white"
                title="Close chat drawer"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          {/* Refresh Feedback Alert */}
          {refreshFeedback && (
            <div className={`px-4 py-1.5 text-xs font-semibold flex items-center justify-between transition-all ${
              refreshFeedback.includes("failed") ? "bg-red-50 text-red-700 border-b border-red-200" : "bg-emerald-50 text-emerald-800 border-b border-emerald-200"
            }`}>
              <span>{refreshFeedback}</span>
              <button onClick={() => setRefreshFeedback(null)} className="text-slate-400 hover:text-slate-600">
                <X size={12} />
              </button>
            </div>
          )}

          {/* Patient Complaint Header */}
          <div className="bg-blue-50/70 px-4 py-2.5 border-b border-blue-100/60 flex items-center justify-between text-xs">
            <div className="truncate text-slate-700">
              <span className="font-bold text-blue-900">Chief Complaint:</span> {activeChatReq.chief_complaint || activeChatReq.chief_concern || "General consultation requested"}
            </div>
            {activeChatReq.status !== "COMPLETED" && (
              <button
                onClick={(e) => handleOpenCompleteModal(e, activeChatReq)}
                className="shrink-0 px-2.5 py-1 bg-emerald-600 text-white rounded-lg font-bold text-[11px] hover:bg-emerald-700 shadow-sm"
              >
                Sign & Complete
              </button>
            )}
          </div>

          <div ref={chatDrawerScrollRef} className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-50">
            {(!activeChatReq.messages || activeChatReq.messages.length === 0) ? (
              <div className="text-xs text-slate-400 text-center py-16">
                <MessageSquare size={32} className="mx-auto mb-2 opacity-40 text-slate-400" />
                <div className="font-semibold">No chat messages exchanged yet.</div>
                <div className="text-[11px] text-slate-400 mt-1">Send clinical advice or ask follow-up questions below.</div>
              </div>
            ) : (
              activeChatReq.messages.map((m: any) => {
                const isDoc = m.sender_type === "DOCTOR" || m.sender_role === "PHC_DOCTOR";
                return (
                  <div
                    key={m.id || m.client_message_id || Math.random()}
                    className={`p-3.5 rounded-2xl max-w-[85%] text-xs shadow-sm ${
                      isDoc
                        ? "ml-auto bg-blue-600 text-white rounded-br-sm"
                        : "mr-auto bg-white text-slate-800 border border-slate-200 rounded-bl-sm"
                    }`}
                  >
                    <div className="text-[10px] font-bold opacity-80 mb-1 flex justify-between gap-4">
                      <span>{m.sender_name || (isDoc ? "Dr. Medical Officer" : "Patient")}</span>
                      <span>{m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}</span>
                    </div>
                    <div className="text-xs leading-relaxed break-words">{m.body || m.message_text}</div>
                    {isDoc && (
                      <div className="text-[9px] opacity-75 text-right mt-1">
                        {m.status || "DELIVERED"}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {activeChatReq.status === "COMPLETED" ? (
            <div className="p-3 bg-slate-100 text-center text-xs text-slate-500 font-semibold border-t border-slate-200">
              This consultation is completed and archived.
            </div>
          ) : (
            <form onSubmit={handleSendDoctorMessage} className="p-3 bg-white border-t border-slate-200 flex gap-2">
              <input
                type="text"
                id="input-doctor-chat-reply"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                placeholder="Type medical guidance / instructions..."
                className="flex-1 px-3.5 py-2.5 border border-slate-200 rounded-xl text-xs outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                id="btn-doctor-send-reply"
                disabled={sendingMsg || !chatMessage.trim()}
                className="px-4 py-2.5 bg-blue-600 text-white rounded-xl text-xs font-bold flex items-center gap-1 hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm"
              >
                <Send size={14} /> Send
              </button>
            </form>
          )}
        </div>
      )}

      {/* Comprehensive Consultation Completion & Prescribing Modal */}
      {showCompleteModal && selectedReq && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 shadow-2xl border border-slate-100 my-8">
            <div className="flex justify-between items-center mb-4 pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-lg font-black text-slate-900">Sign & Complete Consultation</h3>
                <p className="text-xs text-slate-500">
                  Patient: <span className="font-bold text-slate-700">{selectedReq.beneficiary_name || selectedReq.citizen_name}</span> ({selectedReq.request_reference || selectedReq.id})
                </p>
              </div>
              <button onClick={() => setShowCompleteModal(false)} className="p-1 hover:bg-slate-100 rounded-lg">
                <X size={20} className="text-slate-400" />
              </button>
            </div>

            <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
              {/* Diagnosis */}
              <div>
                <label className="text-xs font-bold text-slate-700">Provisional Diagnosis *</label>
                <input
                  type="text"
                  value={diagnosis}
                  onChange={(e) => setDiagnosis(e.target.value)}
                  placeholder="e.g. Viral URI, Acute Gastritis, Tension Headache"
                  className="w-full mt-1 p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Patient Care Plan */}
              <div>
                <label className="text-xs font-bold text-slate-700">Patient Guidance / Care Plan *</label>
                <textarea
                  rows={2}
                  value={guidance}
                  onChange={(e) => setGuidance(e.target.value)}
                  placeholder="Precautions, dietary advice, warning red flags..."
                  className="w-full mt-1 p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Dynamic Prescriptions List */}
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-extrabold text-slate-800">Prescription Medicines</span>
                  <button
                    type="button"
                    onClick={handleAddRxItem}
                    className="px-2.5 py-1 bg-blue-600 text-white rounded-lg text-xs font-bold flex items-center gap-1 hover:bg-blue-700"
                  >
                    <Plus size={13} /> Add Medicine
                  </button>
                </div>

                <div className="space-y-2">
                  {prescriptions.map((rx, idx) => (
                    <div key={idx} className="p-3 bg-white rounded-xl border border-slate-200 grid grid-cols-1 sm:grid-cols-6 gap-2 items-center">
                      <div className="sm:col-span-2">
                        <input
                          type="text"
                          value={rx.medicine_name}
                          onChange={(e) => handleUpdateRxItem(idx, "medicine_name", e.target.value)}
                          placeholder="Medicine Name (e.g. Paracetamol 500mg)"
                          className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-bold outline-none"
                        />
                      </div>
                      <div>
                        <input
                          type="text"
                          value={rx.dosage}
                          onChange={(e) => handleUpdateRxItem(idx, "dosage", e.target.value)}
                          placeholder="Dose (1 tab)"
                          className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs outline-none"
                        />
                      </div>
                      <div>
                        <select
                          value={rx.frequency}
                          onChange={(e) => handleUpdateRxItem(idx, "frequency", e.target.value)}
                          className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold outline-none"
                        >
                          <option value="1-0-1">1-0-1 (BD)</option>
                          <option value="1-1-1">1-1-1 (TDS)</option>
                          <option value="1-0-0">1-0-0 (OD Morn)</option>
                          <option value="0-0-1">0-0-1 (OD Night)</option>
                          <option value="SOS">SOS (When needed)</option>
                        </select>
                      </div>
                      <div>
                        <input
                          type="number"
                          value={rx.duration_days}
                          onChange={(e) => handleUpdateRxItem(idx, "duration_days", parseInt(e.target.value) || 1)}
                          placeholder="Days"
                          className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs outline-none"
                        />
                      </div>
                      <div className="flex items-center justify-end">
                        <button
                          type="button"
                          onClick={() => handleRemoveRxItem(idx)}
                          className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Lab / Investigation Orders */}
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-extrabold text-slate-800">Diagnostic Investigation Orders</span>
                  <button
                    type="button"
                    id="btn-add-more-investigation"
                    onClick={() => {
                      setLabFormError(null);
                      setShowAddCustomLabModal(!showAddCustomLabModal);
                    }}
                    className="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  >
                    <Plus size={14} /> + Add More Investigation
                  </button>
                </div>

                {/* Common / Quick Select Tests */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-3">
                  {["Complete Blood Count (CBC)", "Blood Glucose (RBS)", "Malaria Smear / RDT", "Urine Routine", "Serum Electrolytes"].map((test) => {
                    const isSelected = labOrders.includes(test);
                    return (
                      <button
                        key={test}
                        type="button"
                        onClick={() => {
                          if (isSelected) setLabOrders(labOrders.filter(t => t !== test));
                          else setLabOrders([...labOrders, test]);
                        }}
                        className={`p-2 rounded-xl text-xs font-bold text-left border transition-all ${
                          isSelected ? "bg-blue-600 text-white border-blue-600 shadow-sm" : "bg-white text-slate-700 border-slate-200 hover:bg-slate-100"
                        }`}
                      >
                        {test}
                      </button>
                    );
                  })}
                </div>

                {/* Custom Added Tests Cards */}
                {customLabOrders.length > 0 && (
                  <div className="flex flex-col gap-2 mb-3">
                    <span className="text-[11px] font-bold text-slate-600">Custom Ordered Investigations:</span>
                    {customLabOrders.map((customTest, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2.5 bg-white rounded-xl border border-slate-200 shadow-sm text-xs"
                      >
                        <div>
                          <div className="font-extrabold text-slate-900 flex items-center gap-2">
                            <span>🧪 {customTest.test_name}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${customTest.priority === "URGENT" ? "bg-red-100 text-red-700" : "bg-blue-100 text-blue-700"}`}>
                              {customTest.priority}
                            </span>
                            <span className="text-[10px] text-slate-500 font-semibold uppercase">
                              [{customTest.category}]
                            </span>
                          </div>
                          {customTest.clinical_reason && (
                            <div className="text-[11px] text-slate-600 mt-0.5">
                              Reason: {customTest.clinical_reason}
                            </div>
                          )}
                          {customTest.preparation_instructions && (
                            <div className="text-[11px] text-amber-700 mt-0.5">
                              Instructions: {customTest.preparation_instructions}
                            </div>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveCustomLabOrder(idx)}
                          className="p-1 text-slate-400 hover:text-red-600 rounded transition-colors"
                          title="Remove custom investigation"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Inline Add Custom Investigation Form */}
                {showAddCustomLabModal && (
                  <div className="p-3 bg-white rounded-xl border border-blue-200 shadow-sm flex flex-col gap-2.5 mt-2">
                    <div className="text-xs font-bold text-blue-900 flex justify-between items-center">
                      <span>Add New Investigation Order</span>
                      <button
                        type="button"
                        onClick={() => setShowAddCustomLabModal(false)}
                        className="text-slate-400 hover:text-slate-600"
                      >
                        <X size={14} />
                      </button>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] font-bold text-slate-600 block mb-1">Test Name *</label>
                        <input
                          type="text"
                          id="input-custom-lab-name"
                          value={newLabTestName}
                          onChange={(e) => {
                            setNewLabTestName(e.target.value);
                            if (labFormError) setLabFormError(null);
                          }}
                          placeholder="e.g. Thyroid Profile (T3, T4, TSH)"
                          className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs outline-none focus:border-blue-500"
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[10px] font-bold text-slate-600 block mb-1">Category</label>
                          <select
                            value={newLabCategory}
                            onChange={(e) => setNewLabCategory(e.target.value)}
                            className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold outline-none"
                          >
                            <option value="PATHOLOGY">Pathology</option>
                            <option value="BIOCHEMISTRY">Biochemistry</option>
                            <option value="MICROBIOLOGY">Microbiology</option>
                            <option value="RADIOLOGY">Radiology / Imaging</option>
                            <option value="GENERAL">General</option>
                          </select>
                        </div>

                        <div>
                          <label className="text-[10px] font-bold text-slate-600 block mb-1">Priority</label>
                          <select
                            value={newLabPriority}
                            onChange={(e) => setNewLabPriority(e.target.value as any)}
                            className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold outline-none"
                          >
                            <option value="ROUTINE">Routine</option>
                            <option value="URGENT">Urgent</option>
                          </select>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] font-bold text-slate-600 block mb-1">Clinical Reason (Optional)</label>
                        <input
                          type="text"
                          value={newLabClinicalReason}
                          onChange={(e) => setNewLabClinicalReason(e.target.value)}
                          placeholder="e.g. Evaluate chronic fatigue"
                          className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs outline-none"
                        />
                      </div>

                      <div>
                        <label className="text-[10px] font-bold text-slate-600 block mb-1">Preparation Instructions (Optional)</label>
                        <input
                          type="text"
                          value={newLabPrepInstructions}
                          onChange={(e) => setNewLabPrepInstructions(e.target.value)}
                          placeholder="e.g. 10-12 hours overnight fasting"
                          className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-xs outline-none"
                        />
                      </div>
                    </div>

                    {labFormError && (
                      <div className="text-[11px] font-bold text-red-600">
                        {labFormError}
                      </div>
                    )}

                    <div className="flex justify-end gap-2 mt-1">
                      <button
                        type="button"
                        onClick={() => setShowAddCustomLabModal(false)}
                        className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        id="btn-confirm-add-custom-lab"
                        onClick={handleAddCustomLabOrder}
                        className="px-4 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm"
                      >
                        Add Test Order
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* ASHA Follow-up Assignment Directive */}
              <div className="p-4 bg-blue-50/60 rounded-2xl border border-blue-100">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={assignAsha}
                    onChange={(e) => setAssignAsha(e.target.checked)}
                    className="w-4 h-4 rounded text-blue-600"
                  />
                  <span className="text-xs font-bold text-blue-900">Assign ASHA Home Follow-up Directive (3 Days)</span>
                </label>

                {assignAsha && (
                  <div className="mt-3">
                    <label className="text-[11px] font-semibold text-blue-800">ASHA Instructions</label>
                    <input
                      type="text"
                      value={ashaInstructions}
                      onChange={(e) => setAshaInstructions(e.target.value)}
                      className="w-full mt-1 p-2 bg-white border border-blue-200 rounded-xl text-xs outline-none"
                    />
                  </div>
                )}
              </div>
            </div>

            <div className="mt-6 pt-3 border-t border-slate-100 flex justify-end gap-3">
              <button
                onClick={() => setShowCompleteModal(false)}
                className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitComplete}
                disabled={isProcessing === selectedReq.id || !diagnosis.trim()}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-xs shadow-lg shadow-blue-500/20 flex items-center gap-2 disabled:opacity-50"
              >
                <Check size={16} /> Sign & Complete Consultation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

