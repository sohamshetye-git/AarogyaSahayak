import React, { useState, useEffect, useRef } from "react";
import { useLanguage } from "@aarogya/i18n";
import {
  Mic, MicOff, Send, Phone, Stethoscope, MapPin, Home as HomeIcon,
  Volume2, VolumeX, ArrowLeft, Plus, Edit3, CheckCircle2, RotateCcw,
  AlertTriangle, Check, ShieldAlert, ShieldCheck, HelpCircle, Sparkles, User, RefreshCw, Paperclip,
  Activity, X
} from "lucide-react";
import { apiClient } from "@aarogya/api-client";
import { audioCaptureService, AudioRecordingState } from "../services/audioCaptureService";
import { CareHandoffReviewSheet } from "./CareHandoffReviewSheet";

interface AssistantScreenProps {
  onBack: () => void;
  onOpenDoctor: (prefillData?: {
    sessionId?: string;
    needId?: string;
    chiefComplaint?: string;
    symptoms?: string[];
    priority?: string;
    beneficiaryId?: string;
  }) => void;
  onOpenEmergency: () => void;
  onOpenAsha: () => void;
  onOpenFacilities: () => void;
  onViewServiceRequest?: (serviceRequestId: string) => void;
}

interface MessageItem {
  id: string;
  sender: "CITIZEN" | "ASSISTANT" | "SYSTEM";
  input_type: "VOICE" | "TEXT" | "SYSTEM";
  original_text?: string;
  confirmed_text?: string;
  message_type: "TEXT" | "TRANSCRIPT" | "UNDERSTANDING" | "SAFETY_ALERT" | "QUESTION";
  structured_payload?: any;
  confirmation_status: "PENDING" | "CONFIRMED" | "EDITED" | "REJECTED";
  created_at?: string;
}

export const AssistantScreen: React.FC<AssistantScreenProps> = ({
  onBack,
  onOpenDoctor,
  onOpenEmergency,
  onOpenAsha,
  onOpenFacilities,
  onViewServiceRequest
}) => {
  const { t, locale, i18n } = useLanguage();



  const [sessionId, setSessionId] = useState<string | null>(null);
  const [activeNeedId, setActiveNeedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [inputText, setInputText] = useState<string>("");
  const [inputPlaceholder, setInputPlaceholder] = useState<string>("");
  const [readAloudEnabled, setReadAloudEnabled] = useState<boolean>(false);
  const inputRef = React.useRef<HTMLInputElement | null>(null);

  // Audio recording states
  const [recState, setRecState] = useState<AudioRecordingState>("IDLE");
  const [recSeconds, setRecSeconds] = useState<number>(0);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Care Handoff Review Sheet State
  const [handoffSheetOpen, setHandoffSheetOpen] = useState<boolean>(false);
  const [handoffRequestType, setHandoffRequestType] = useState<"DOCTOR_CONSULTATION" | "ASHA_ASSISTANCE">("DOCTOR_CONSULTATION");

  // Draft transcript currently awaiting confirmation
  const [pendingDraft, setPendingDraft] = useState<{
    text: string;
    isEditing: boolean;
    editedText: string;
    detectedLanguage: string;
    audioBlob?: Blob;
  } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<any>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, pendingDraft, isProcessing, recState]);

  // Load active session or start new one
  useEffect(() => {
    let isMounted = true;

    const loadSession = async () => {
      setLoading(true);
      try {
        const activeRes = await apiClient.getActiveCitizenChatSession();
        const activeData = activeRes?.data || activeRes;

        if (activeData && activeData.session_id && activeData.messages?.length > 0) {
          if (isMounted) {
            setSessionId(activeData.session_id);
            if (activeData.active_need_id || activeData.linked_need_id) {
              setActiveNeedId(activeData.active_need_id || activeData.linked_need_id);
            }
            setMessages(activeData.messages);
          }
        } else {
          // Start a fresh session
          const newSessionRes = await apiClient.startCitizenChatSession({
            preferred_language: locale || "mr-IN",
            channel: "MIXED"
          });
          const sessionData = newSessionRes?.data || newSessionRes;
          if (isMounted && sessionData?.session_id) {
            setSessionId(sessionData.session_id);
            const welcomeText = t("chat.welcome_message");

            setMessages([
              {
                id: `welcome-${Date.now()}`,
                sender: "ASSISTANT",
                input_type: "SYSTEM",
                original_text: welcomeText,
                confirmed_text: welcomeText,
                message_type: "TEXT",
                structured_payload: {
                  purpose: "GREETING",
                  actions: [
                    { type: "HEALTH_HELP", action: "HEALTH_HELP", style: "PRIMARY" },
                    { type: "SPEAK_TO_DOCTOR", action: "SPEAK_TO_DOCTOR", style: "SECONDARY" },
                    { type: "FIND_FACILITY", action: "FIND_FACILITY", style: "OUTLINE" },
                    { type: "CHECK_SCHEMES", action: "CHECK_SCHEMES", style: "OUTLINE" }
                  ],
                  suggested_replies: [
                    "HIGH_FEVER_2_DAYS",
                    "SPEAK_TO_DOCTOR",
                    "FIND_HEALTH_CENTRE",
                    "CHECK_SCHEMES"
                  ]
                },
                confirmation_status: "CONFIRMED",
                created_at: new Date().toISOString()
              }
            ]);
          }
        }
      } catch (err) {
        console.error("Failed to load or initialize chat session:", err);
        // Local fallback session
        if (isMounted) {
          const welcomeText = t("chat.welcome_message");

          setSessionId(`local-${Date.now()}`);
          setMessages([
            {
              id: `welcome-${Date.now()}`,
              sender: "ASSISTANT",
              input_type: "SYSTEM",
              original_text: welcomeText,
              confirmed_text: welcomeText,
              message_type: "TEXT",
              structured_payload: {
                purpose: "GREETING",
                actions: [
                  { type: "HEALTH_HELP", action: "HEALTH_HELP", style: "PRIMARY" },
                  { type: "SPEAK_TO_DOCTOR", action: "SPEAK_TO_DOCTOR", style: "SECONDARY" },
                  { type: "FIND_FACILITY", action: "FIND_FACILITY", style: "OUTLINE" },
                  { type: "CHECK_SCHEMES", action: "CHECK_SCHEMES", style: "OUTLINE" }
                ],
                suggested_replies: [
                  "HIGH_FEVER_2_DAYS",
                  "SPEAK_TO_DOCTOR",
                  "FIND_HEALTH_CENTRE",
                  "CHECK_SCHEMES"
                ]
              },
              confirmation_status: "CONFIRMED",
              created_at: new Date().toISOString()
            }
          ]);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadSession();

    return () => {
      isMounted = false;
      if (timerRef.current) clearInterval(timerRef.current);
      audioCaptureService.cancelRecording();
    };
  }, [i18n.language]);

  // Start a fresh conversation
  const handleStartNewConversation = async () => {
    setLoading(true);
    setPendingDraft(null);
    try {
      const res = await apiClient.startCitizenChatSession({
        preferred_language: i18n.language || "mr-IN",
        channel: "MIXED"
      });
      const data = res?.data || res;
      setSessionId(data.session_id);
      setMessages([
        {
          id: `welcome-${Date.now()}`,
          sender: "ASSISTANT",
          input_type: "SYSTEM",
          original_text: t(
            "assistant:welcome_message",
            "नमस्कार! मी आपला आरोग्य सहाय्यक आहे. तुम्हाला किंवा तुमच्या कुटुंबियांस काय त्रास होत आहे? बोलून किंवा टाइप करून सांगा."
          ),
          confirmed_text: t(
            "assistant:welcome_message",
            "नमस्कार! मी आपला आरोग्य सहाय्यक आहे. तुम्हाला किंवा तुमच्या कुटुंबियांस काय त्रास होत आहे? बोलून किंवा टाइप करून सांगा."
          ),
          message_type: "TEXT",
          confirmation_status: "CONFIRMED",
          created_at: new Date().toISOString()
        }
      ]);
    } catch (err) {
      console.error("Failed to reset session:", err);
    } finally {
      setLoading(false);
    }
  };

  // TTS Read Aloud
  const speakText = (text?: string) => {
    if (!text || typeof window === "undefined" || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = i18n.language || "mr-IN";
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
  };

  // Mic Click: Start Recording
  const handleStartMic = async () => {
    setErrorMessage(null);
    setRecSeconds(0);

    try {
      await audioCaptureService.startRecording(
        i18n.language || "mr-IN",
        (level) => setAudioLevel(level),
        (state) => setRecState(state),
        { maxDurationSeconds: 30 }
      );

      // Start duration counter
      timerRef.current = setInterval(() => {
        setRecSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err: any) {
      if (timerRef.current) clearInterval(timerRef.current);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setErrorMessage(t("assistant:permission_denied_msg", "Microphone permission denied. Please allow access or type below."));
      } else {
        setErrorMessage(err.message || t("assistant:no_audio_msg", "Could not start microphone."));
      }
    }
  };

  // Mic Click: Stop and Process
  const handleStopMic = async () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setIsProcessing(true);

    try {
      const result = await audioCaptureService.stopRecording(i18n.language || "mr-IN", (state) => setRecState(state));

      if (result.status === "TRANSCRIPT_READY" && result.transcript) {
        setPendingDraft({
          text: result.transcript,
          isEditing: false,
          editedText: result.transcript,
          detectedLanguage: result.detectedLanguage,
          audioBlob: result.blob
        });
      } else if (result.status === "NO_AUDIO") {
        setErrorMessage(t("assistant:no_audio_msg", "No sound was captured. Please speak again or type."));
      } else {
        setErrorMessage(
          result.errorMessage || t("assistant:no_audio_msg", "Speech recognition unavailable. Please type your message.")
        );
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to process audio.");
    } finally {
      setIsProcessing(false);
      setRecState("IDLE");
      setAudioLevel(0);
    }
  };

  // Mic Click: Cancel Recording
  const handleCancelMic = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    audioCaptureService.cancelRecording((state) => setRecState(state));
    setRecState("IDLE");
    setRecSeconds(0);
    setAudioLevel(0);
  };

  // Core Process Confirmed Message Function
  const processConfirmedMessage = async (confirmedText: string, isVoice: boolean = false, audioBlob?: Blob) => {
    setIsProcessing(true);
    setErrorMessage(null);

    // Optimistically append Citizen message
    const userMsg: MessageItem = {
      id: `citizen-${Date.now()}`,
      sender: "CITIZEN",
      input_type: isVoice ? "VOICE" : "TEXT",
      original_text: confirmedText,
      confirmed_text: confirmedText,
      message_type: "TRANSCRIPT",
      confirmation_status: "CONFIRMED",
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      let data: any = null;

      if (sessionId && !sessionId.startsWith("local-")) {
        try {
          // Post message to backend session
          await apiClient.addCitizenChatMessage(sessionId, {
            input_type: isVoice ? "VOICE" : "TEXT",
            original_text: confirmedText,
            language: i18n.language || "mr-IN"
          });

          // Run structured understanding & deterministic safety routing
          const res = await apiClient.confirmCitizenTranscript(sessionId, {
            confirmed_text: confirmedText,
            action: "CONFIRM"
          });

          data = res?.data || res;
        } catch (apiErr) {
          console.warn("Backend API chat call failed, falling back to local clinical engine:", apiErr);
        }
      }

      if (data && (data.text || data.message || data.assistant_message || data.blocks)) {
        const assistantText = data.assistant_message?.text || data.text || data.message || "";
        const assistantMsg: MessageItem = {
          id: data.message_id || `asst-${Date.now()}`,
          sender: "ASSISTANT",
          input_type: "SYSTEM",
          original_text: assistantText,
          confirmed_text: assistantText,
          message_type: data.purpose === "NEW_HEALTH_CONCERN" ? "UNDERSTANDING" : "TEXT",
          structured_payload: {
            purpose: data.purpose || data.understanding?.intent,
            blocks: data.blocks || [],
            understanding: data.understanding,
            safety: data.safety,
            actions: data.actions || [],
            suggested_replies: data.suggested_replies || []
          },
          confirmation_status: "CONFIRMED",
          created_at: new Date().toISOString()
        };
        if (data.active_need_id) {
          setActiveNeedId(data.active_need_id);
        }
        setMessages((prev) => [...prev, assistantMsg]);

        if (readAloudEnabled && (data.read_aloud_text || assistantText)) {
          speakText(data.read_aloud_text || assistantText);
        }
      } else {
        // Fallback local processing with deterministic safety, facility matching, and multilingual care guidance
        const textLower = confirmedText.toLowerCase();
        const isEmergency =
          textLower.includes("छातीत") ||
          textLower.includes("chest") ||
          textLower.includes("सीने में") ||
          textLower.includes("दुखत") ||
          textLower.includes("श्वास") ||
          textLower.includes("breath");

        const isFacilityQuery =
          textLower.includes("phc") ||
          textLower.includes("आरोग्य केंद्र") ||
          textLower.includes("रुग्णालय") ||
          textLower.includes("hospital") ||
          textLower.includes("लसीकरण") ||
          textLower.includes("vaccin") ||
          textLower.includes("delivery") ||
          textLower.includes("प्रसूती") ||
          textLower.includes("दवाखाना") ||
          textLower.includes("center") ||
          textLower.includes("centre");

        const lang = i18n.language || "mr-IN";
        let replyText = "";
        let structuredBlocks: any[] = [];
        let purpose = "GENERAL";

        if (isEmergency) {
          purpose = "EMERGENCY_HELP";
          replyText = lang.startsWith("hi")
            ? "⚠️ गंभीर लक्षण पाए गए हैं। तुरंत 108 पर कॉल करें या नजदीकी आपातकालीन केंद्र पर जाएं।"
            : lang.startsWith("en")
            ? "⚠️ Critical warning signs detected. Please call 108 Emergency immediately or proceed to the nearest emergency facility."
            : "⚠️ गंभीर व तात्काळ काळजीची लक्षणे आढळली आहेत. त्वरित १०८ वर कॉल करा किंवा जवळच्या २४x७ आपत्कालीन केंद्रात जा.";

          structuredBlocks = [
            {
              block_type: "SAFETY_ALERT",
              title: "Emergency Alert (108)",
              content: replyText
            },
            {
              block_type: "FACILITY_RESULTS",
              title: lang.startsWith("en") ? "Nearest Emergency Facilities" : "जवळची २४x७ आपत्कालीन आरोग्य केंद्रे",
              facilities: [
                {
                  id: "fac-2026-002",
                  name: "Kalyanpur Primary Health Centre (PHC)",
                  distance_km: 2.8,
                  emergency: true,
                  reason: "Verified 24x7 Emergency & Stabilization"
                },
                {
                  id: "fac-2026-003",
                  name: "Kalyanpur Community Health Centre (CHC)",
                  distance_km: 8.5,
                  emergency: true,
                  reason: "Comprehensive Emergency & Inpatient Trauma"
                }
              ]
            },
            {
              block_type: "ACTION_CHOICES",
              actions: [
                { type: "EMERGENCY_HELP", label: t("assistant:call_108", "Call 108"), style: "DANGER" },
                { type: "FIND_FACILITY", label: "Open Health Centre Finder", style: "PRIMARY" }
              ]
            }
          ];
        } else if (isFacilityQuery) {
          purpose = "FACILITY_SEARCH";
          let serviceType = "GENERAL_OPD";
          if (textLower.includes("लसीकरण") || textLower.includes("vaccin")) serviceType = "CHILD_VACCINATION";
          if (textLower.includes("delivery") || textLower.includes("प्रसूती")) serviceType = "MATERNITY_DELIVERY";

          replyText = lang.startsWith("hi")
            ? `आपके स्थान के आधार पर सबसे उपयुक्त स्वास्थ्य केंद्र खोजे गए हैं:`
            : lang.startsWith("en")
            ? `Found the closest verified health centres for your requirement:`
            : `तुमच्या गरजेनुसार सर्वात योग्य जवळची आरोग्य केंद्रे शोधली आहेत:`;

          structuredBlocks = [
            {
              block_type: "FACILITY_RESULTS",
              title: lang.startsWith("en") ? "Recommended Health Centres" : "शिफारस केलेली आरोग्य केंद्रे",
              facilities: [
                {
                  id: "fac-2026-002",
                  name: "Kalyanpur Primary Health Centre (PHC)",
                  distance_km: 2.8,
                  open_status: "Open 24x7",
                  reason: serviceType === "MATERNITY_DELIVERY" ? "Verified 24x7 Labor Room & Delivery Ward" : serviceType === "CHILD_VACCINATION" ? "Universal Child Immunization & Cold Chain" : "Verified Primary Health Centre"
                },
                {
                  id: "fac-2026-001",
                  name: "Ganeshpur Sub-Centre",
                  distance_km: 1.2,
                  open_status: "Open • 9:00 AM - 2:00 PM",
                  reason: serviceType === "MATERNITY_DELIVERY" ? "ANC Screening only (No Delivery beds)" : "Closest village primary post"
                }
              ]
            },
            {
              block_type: "ACTION_CHOICES",
              actions: [
                { type: "FIND_FACILITY", label: lang.startsWith("en") ? "View All Health Centres" : "सर्व केंद्रे पहा (Find Health Centre)", style: "PRIMARY" },
                { type: "REQUEST_ASHA", label: t("assistant:request_asha_visit", "Request ASHA Visit"), style: "SECONDARY" }
              ]
            }
          ];
        } else {
          purpose = "LIMITED_FALLBACK";
          replyText = lang.startsWith("hi")
            ? "बातचीत सहायता अस्थायी रूप से सीमित है। आप पुनः प्रयास कर सकते हैं या सीधे नीचे दी गई स्वास्थ्य सेवाओं का उपयोग कर सकते हैं।"
            : lang.startsWith("en")
            ? "Conversational assistance is temporarily limited. You can try again or directly use health services below."
            : "संभाषण सहाय्य सध्या मर्यादित मोडमध्ये आहे. आपण पुन्हा प्रयत्न करू शकता किंवा खालील आरोग्य सेवांचा थेट वापर करू शकता.";

          structuredBlocks = [
            {
              block_type: "ACTION_CHOICES",
              actions: [
                { type: "SPEAK_TO_DOCTOR", label: lang.startsWith("en") ? "Speak to Doctor" : (lang.startsWith("hi") ? "डॉक्टर से बात करें" : "डॉक्टरांशी बोला"), style: "PRIMARY" },
                { type: "FIND_FACILITY", label: lang.startsWith("en") ? "Find Health Centre" : (lang.startsWith("hi") ? "स्वास्थ्य केंद्र खोजें" : "आरोग्य केंद्र शोधा"), style: "SECONDARY" },
                { type: "CHECK_SCHEMES", label: lang.startsWith("en") ? "Check Schemes" : (lang.startsWith("hi") ? "सरकारी योजनाएं" : "शासकीय योजना"), style: "OUTLINE" }
              ]
            }
          ];
        }

        const localAssistantMsg: MessageItem = {
          id: `asst-${Date.now()}`,
          sender: "ASSISTANT",
          input_type: "SYSTEM",
          original_text: replyText,
          confirmed_text: replyText,
          message_type: "TEXT",
          structured_payload: {
            purpose: purpose,
            blocks: structuredBlocks,
            safety: {
              level: isEmergency ? "EMERGENCY" : "NORMAL",
              reason: isEmergency ? "Critical warning signs" : "Routine"
            },
            actions: structuredBlocks.flatMap((b: any) => b.actions || [])
          },
          confirmation_status: "CONFIRMED",
          created_at: new Date().toISOString()
        };
        setMessages((prev) => [...prev, localAssistantMsg]);

        if (readAloudEnabled) {
          speakText(replyText);
        }

      }
    } catch (err) {
      console.error("Failed to process message:", err);
      setErrorMessage("Could not submit message. Please try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  // Send Direct Text Message (directly submits and replies)
  const handleSendText = async (textToSend?: string) => {
    const content = (textToSend || inputText).trim();
    if (!content) return;

    setInputText("");
    setErrorMessage(null);
    await processConfirmedMessage(content, false);
  };

  // Confirm Transcript for Voice Recordings
  const handleConfirmTranscript = async () => {
    if (!pendingDraft || !pendingDraft.editedText.trim()) return;

    const confirmedText = pendingDraft.editedText.trim();
    const currentDraft = pendingDraft;
    setPendingDraft(null);
    await processConfirmedMessage(confirmedText, !!currentDraft.audioBlob, currentDraft.audioBlob);
  };


  // Quick Reply Click
  const handleQuickReply = (text: string) => {
    handleSendText(text);
  };

  // Execute Direct Action Card Action
  const handleActionClick = (actionType: string, payload?: any) => {
    if (actionType === "EMERGENCY_HELP" || actionType === "CALL_108") {
      onOpenEmergency();
    } else if (actionType === "SPEAK_TO_DOCTOR") {
      // Find latest confirmed health understanding facts from messages
      let extractedChiefComplaint: string | undefined = undefined;
      let extractedSymptoms: string[] = [];
      let extractedPriority: string | undefined = undefined;

      for (let i = messages.length - 1; i >= 0; i--) {
        const msg = messages[i];
        const under = msg.structured_payload?.understanding;
        if (under) {
          if (under.new_facts?.symptoms && Array.isArray(under.new_facts.symptoms)) {
            extractedSymptoms.push(...under.new_facts.symptoms);
          }
          if (under.primary_concern) {
            extractedChiefComplaint = under.primary_concern;
          }
        }
        if (msg.structured_payload?.safety?.priority) {
          extractedPriority = msg.structured_payload.safety.priority;
        }
        if (msg.sender === "CITIZEN" && msg.confirmed_text && !extractedChiefComplaint) {
          extractedChiefComplaint = msg.confirmed_text;
        }
      }

      onOpenDoctor({
        sessionId: sessionId || undefined,
        needId: activeNeedId || undefined,
        chiefComplaint: extractedChiefComplaint,
        symptoms: extractedSymptoms.length > 0 ? Array.from(new Set(extractedSymptoms)) : undefined,
        priority: extractedPriority
      });
    } else if (actionType === "REQUEST_ASHA" || actionType === "CALL_ASHA") {
      setHandoffRequestType("ASHA_ASSISTANCE");
      setHandoffSheetOpen(true);
    } else if (actionType === "FIND_FACILITY" || actionType === "FIND_FACILITIES") {
      onOpenFacilities();
    } else if (actionType === "VIEW_CARE_RECORD" || actionType === "VIEW_IN_MY_CARE") {
      const srId = payload?.service_request_id || payload?.id;
      if (onViewServiceRequest && srId) {
        onViewServiceRequest(srId);
      } else {
        onBack();
      }
    } else if (actionType === "ASK_ANOTHER_QUESTION") {
      // 1. Close/reset completed handoff state & clear transient UI
      setHandoffSheetOpen(false);
      setPendingDraft(null);
      setErrorMessage(null);
      // 2. Set composer to empty and set placeholder
      setInputText("");
      const isHi = i18n.language?.startsWith("hi");
      const isEn = i18n.language?.startsWith("en");
      setInputPlaceholder(
        isHi
          ? "आप और क्या मदद चाहते हैं?"
          : isEn
          ? "What else would you like help with?"
          : "तुम्हाला आणखी काय मदत हवी आहे?"
      );
      // 3. Focus the text input
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 100);
    } else if (actionType === "HEALTH_HELP") {
      handleSendText(i18n.language?.startsWith("hi") ? "मुझे स्वास्थ्य मार्गदर्शन चाहिए" : (i18n.language?.startsWith("en") ? "I need health guidance" : "मला आरोग्य मार्गदर्शन हवे आहे"));
    } else if (actionType === "CHECK_SCHEMES") {
      handleSendText(i18n.language?.startsWith("hi") ? "आयुष्मान भारत योजना की जानकारी दें" : (i18n.language?.startsWith("en") ? "Check Ayushman Bharat scheme eligibility" : "आयुष्यमान भारत योजनेची माहिती सांगा"));
    }
  };

  const handleHandoffSuccess = (result: any) => {
    const isHi = i18n.language?.startsWith("hi");
    const isEn = i18n.language?.startsWith("en");
    const isDoc = result?.assigned_role === "PHC_DOCTOR" || handoffRequestType === "DOCTOR_CONSULTATION";
    const srvId = result.service_request_id || result.request_id || result.id;

    const successMsgText = isDoc
      ? (isHi
        ? `✅ डॉक्टर परामर्श अनुरोध सफलतापूर्वक दर्ज किया गया है (संदर्भ: ${result.reference || result.request_reference || "DOCREQ"}). पीएचसी डॉक्टर जल्द ही आपसे संपर्क करेंगे।`
        : isEn
        ? `✅ Doctor consultation request submitted successfully (Ref: ${result.reference || result.request_reference || "DOCREQ"}). PHC Doctor will contact you shortly.`
        : `✅ डॉक्टर सल्लामसलत विनंती यशस्वीरित्या नोंदवली गेली (संदर्भ: ${result.reference || result.request_reference || "DOCREQ"}). प्राथमिक आरोग्य केंद्र डॉक्टर लवकरच संपर्क साधतील.`)
      : (isHi
        ? `✅ आशा कार्यकर्ती भेट अनुरोध सफलतापूर्वक दर्ज किया गया है (संदर्भ: ${result.reference || result.request_reference || "ASHAREQ"}). आशा कार्यकर्ती: ${result.assigned_asha || "संबधित आशा ताई"}.`
        : isEn
        ? `✅ ASHA home visit request submitted successfully (Ref: ${result.reference || result.request_reference || "ASHAREQ"}). Assigned: ${result.assigned_asha || "Local ASHA Worker"}.`
        : `✅ आशा ताई भेट विनंती यशस्वीरित्या नोंदवली गेली (संदर्भ: ${result.reference || result.request_reference || "ASHAREQ"}). नियुक्त: ${result.assigned_asha || "स्थानिक आशा ताई"}.`);

    const confirmationMessage: MessageItem = {
      id: `handoff-ack-${Date.now()}`,
      sender: "ASSISTANT",
      input_type: "SYSTEM",
      original_text: successMsgText,
      confirmed_text: successMsgText,
      message_type: "TEXT",
      structured_payload: {
        purpose: "HANDOFF_CONFIRMATION",
        service_request_id: srvId,
        reference: result.reference || result.request_reference,
        status: result.status || (isDoc ? "WAITING_FOR_DOCTOR" : "ASHA_ASSIGNED"),
        actions: [
          { type: "VIEW_CARE_RECORD", action: "VIEW_CARE_RECORD", service_request_id: srvId, label: isHi ? "मेरी देखभाल स्थिति देखें" : (isEn ? "View In My Care" : "माझी काळजी स्थिती पहा"), style: "PRIMARY" },
          { type: "ASK_ANOTHER_QUESTION", action: "ASK_ANOTHER_QUESTION", label: isHi ? "और सवाल पूछें" : (isEn ? "Ask Another Question" : "आणखी विचारा"), style: "OUTLINE" }
        ]
      },
      confirmation_status: "CONFIRMED",
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, confirmationMessage]);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: "720px",
        backgroundColor: "#F8FAFC",
        position: "relative"
      }}
    >
      {/* Header Bar */}
      <header
        style={{
          padding: "12px 16px",
          backgroundColor: "#1565C0",
          color: "#FFFFFF",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
          zIndex: 10
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            onClick={onBack}
            aria-label={t("common:back", "Back")}
            style={{
              border: "none",
              background: "rgba(255,255,255,0.15)",
              color: "#FFFFFF",
              width: 36,
              height: 36,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer"
            }}
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, letterSpacing: -0.2 }}>
              {t("assistant:guided_title", "आरोग्य सहाय्यक")}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, opacity: 0.9 }}>
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  backgroundColor: "#4ADE80",
                  display: "inline-block"
                }}
              />
              <span>{t("assistant:online_status", "Online")}</span>
              <span>•</span>
              <span style={{ textTransform: "uppercase", fontWeight: 700 }}>
                {i18n.language ? i18n.language.substring(0, 2) : "MR"}
              </span>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {/* Read Aloud Toggle */}
          <button
            onClick={() => setReadAloudEnabled(!readAloudEnabled)}
            title={t("common:read_aloud", "Read aloud")}
            style={{
              border: "none",
              background: readAloudEnabled ? "#FFFFFF" : "rgba(255,255,255,0.2)",
              color: readAloudEnabled ? "#1565C0" : "#FFFFFF",
              width: 36,
              height: 36,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              transition: "all 0.2s ease"
            }}
          >
            {readAloudEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
          </button>

          {/* New Chat */}
          <button
            onClick={handleStartNewConversation}
            title={t("assistant:new_conversation", "New Chat")}
            style={{
              border: "none",
              background: "rgba(255,255,255,0.2)",
              color: "#FFFFFF",
              width: 36,
              height: 36,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer"
            }}
          >
            <RefreshCw size={16} />
          </button>

          {/* Direct 108 Emergency Action */}
          <button
            onClick={onOpenEmergency}
            style={{
              padding: "6px 12px",
              backgroundColor: "#DC2626",
              color: "#FFFFFF",
              borderRadius: 20,
              fontSize: 12,
              fontWeight: 800,
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
              boxShadow: "0 2px 8px rgba(220, 38, 38, 0.4)"
            }}
          >
            <Phone size={13} /> 108
          </button>
        </div>
      </header>

      {/* Error / Alert Banner */}
      {errorMessage && (
        <div
          style={{
            backgroundColor: "#FEF2F2",
            borderBottom: "1px solid #FCA5A5",
            padding: "8px 16px",
            color: "#991B1B",
            fontSize: 12,
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <AlertTriangle size={15} color="#DC2626" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            style={{ border: "none", background: "none", cursor: "pointer", color: "#991B1B" }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Chat Messages Stream */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px 14px 100px",
          display: "flex",
          flexDirection: "column",
          gap: 14
        }}
      >
        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: "20px 0" }}>
            <div style={{ width: "70%", height: 48, borderRadius: 16, backgroundColor: "#E2E8F0", animation: "pulse 1.5s infinite" }} />
            <div style={{ width: "50%", height: 36, borderRadius: 16, backgroundColor: "#E2E8F0", alignSelf: "flex-end", animation: "pulse 1.5s infinite" }} />
            <div style={{ width: "80%", height: 72, borderRadius: 16, backgroundColor: "#E2E8F0", animation: "pulse 1.5s infinite" }} />
          </div>
        ) : (
          <>
            {messages.map((msg) => {
              const isAssistant = msg.sender === "ASSISTANT";

              return (
                <div
                  key={msg.id}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: isAssistant ? "flex-start" : "flex-end",
                    maxWidth: "100%"
                  }}
                >
                  <div
                    style={{
                      maxWidth: "86%",
                      backgroundColor: isAssistant ? "#FFFFFF" : "#2563EB",
                      color: isAssistant ? "#0F172A" : "#FFFFFF",
                      borderRadius: isAssistant ? "18px 18px 18px 4px" : "18px 18px 4px 18px",
                      padding: "12px 14px",
                      boxShadow: isAssistant ? "0 2px 8px rgba(0,0,0,0.06)" : "0 3px 12px rgba(37,99,235,0.25)",
                      border: isAssistant ? "1px solid #E2E8F0" : "none",
                      fontSize: 14,
                      lineHeight: 1.45,
                      position: "relative"
                    }}
                  >
                    {/* Assistant Message Header / Speaker */}
                    {isAssistant && (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          marginBottom: 6,
                          fontSize: 11,
                          fontWeight: 700,
                          color: "#64748B"
                        }}
                      >
                        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                          <Sparkles size={13} color="#2563EB" /> {t("assistant:guided_title", "आरोग्य सहाय्यक")}
                        </span>
                        <button
                          onClick={() => speakText(msg.confirmed_text || msg.original_text)}
                          style={{
                            border: "none",
                            background: "#F1F5F9",
                            borderRadius: "50%",
                            padding: 4,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center"
                          }}
                        >
                          <Volume2 size={12} color="#475569" />
                        </button>
                      </div>
                    )}

                    {/* Main Bubble Text */}
                    <div style={{ fontWeight: isAssistant ? 500 : 600 }}>
                      {msg.confirmed_text || msg.original_text}
                    </div>

                    {/* DYNAMIC TYPED UI BLOCKS FROM BACKEND RESPONSE ORCHESTRATOR */}
                    {msg.structured_payload?.blocks && msg.structured_payload.blocks.map((block: any, bIdx: number) => {
                      if (block.block_type === "SAFE_GUIDANCE") {
                        return (
                          <div
                            key={bIdx}
                            style={{
                              marginTop: 10,
                              backgroundColor: "#EFF6FF",
                              border: "1.5px solid #93C5FD",
                              borderRadius: 14,
                              padding: "12px 14px",
                              color: "#1E3A8A"
                            }}
                          >
                            <div style={{ fontSize: 13, fontWeight: 800, marginBottom: 6, display: "flex", alignItems: "center", gap: 6, color: "#1D4ED8" }}>
                              <ShieldCheck size={16} color="#1D4ED8" />
                              {block.title || t("assistant:safe_guidance_title", "काळजी मार्गदर्शन / Safe Guidance")}
                            </div>
                            {block.content && (
                              <div style={{ fontSize: 13, marginBottom: 6, color: "#1E293B", fontWeight: 500 }}>
                                {block.content}
                              </div>
                            )}
                            {block.data?.points && (
                              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, lineHeight: 1.5, display: "flex", flexDirection: "column", gap: 4 }}>
                                {block.data.points.map((p: string, pIdx: number) => (
                                  <li key={pIdx}>{p}</li>
                                ))}
                              </ul>
                            )}
                            {block.data?.warning && (
                              <div style={{ marginTop: 8, fontSize: 11, fontWeight: 700, color: "#B91C1C", backgroundColor: "#FEF2F2", padding: "6px 8px", borderRadius: 8 }}>
                                ⚠️ {block.data.warning}
                              </div>
                            )}
                          </div>
                        );
                      }

                      if (block.block_type === "CLARIFYING_QUESTION") {
                        return (
                          <div
                            key={bIdx}
                            style={{
                              marginTop: 10,
                              backgroundColor: "#FEF9C3",
                              border: "1.5px solid #FDE047",
                              borderRadius: 14,
                              padding: "10px 12px",
                              color: "#713F12"
                            }}
                          >
                            <div style={{ fontSize: 12, fontWeight: 800, marginBottom: 4, display: "flex", alignItems: "center", gap: 4, color: "#854D0E" }}>
                              <HelpCircle size={15} color="#854D0E" />
                              {block.title || t("assistant:clarifying_question", "महत्त्वाचा प्रश्न / Clarification")}
                            </div>
                            <div style={{ fontSize: 13, fontWeight: 600, color: "#1E293B" }}>
                              {block.content}
                            </div>
                          </div>
                        );
                      }

                      if (block.block_type === "UNDERSTANDING_CONFIRMATION") {
                        return (
                          <div
                            key={bIdx}
                            style={{
                              marginTop: 10,
                              backgroundColor: "#F0FDF4",
                              border: "1.5px solid #86EFAC",
                              borderRadius: 14,
                              padding: "10px 12px",
                              color: "#14532D"
                            }}
                          >
                            <div style={{ fontSize: 12, fontWeight: 800, marginBottom: 6, display: "flex", alignItems: "center", gap: 4, color: "#166534" }}>
                              <CheckCircle2 size={14} color="#166534" />
                              {block.title || t("assistant:what_i_understood", "What we understood:")}
                            </div>
                            <div style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12 }}>
                              <div>
                                <span style={{ fontWeight: 600, color: "#475569" }}>{t("assistant:patient_label", "Patient")}: </span>
                                <span style={{ fontWeight: 700 }}>{block.data?.person || "Self"}</span>
                              </div>
                              <div>
                                <span style={{ fontWeight: 600, color: "#475569" }}>{t("assistant:concern_label", "Concern")}: </span>
                                <span style={{ fontWeight: 700, color: "#DC2626" }}>
                                  {Array.isArray(block.data?.symptoms)
                                    ? block.data.symptoms.join(", ")
                                    : block.data?.symptoms || "Health concern reported"}
                                </span>
                              </div>
                              <div>
                                <span style={{ fontWeight: 600, color: "#475569" }}>{t("assistant:duration_label", "Duration")}: </span>
                                <span style={{ fontWeight: 700 }}>{block.data?.duration || "Recent"}</span>
                              </div>
                            </div>
                          </div>
                        );
                      }

                      if (block.block_type === "SAFETY_ALERT") {
                        return (
                          <div
                            key={bIdx}
                            style={{
                              marginTop: 10,
                              backgroundColor: "#FEF2F2",
                              border: "2px solid #FCA5A5",
                              borderRadius: 14,
                              padding: "10px 12px",
                              color: "#991B1B"
                            }}
                          >
                            <div style={{ display: "flex", alignItems: "center", gap: 6, fontWeight: 800, fontSize: 13, marginBottom: 4 }}>
                              <ShieldAlert size={16} color="#DC2626" />
                              {block.title || t("assistant:emergency_warning", "⚠️ Urgent warning signs detected!")}
                            </div>
                            <div style={{ fontSize: 12, color: "#7F1D1B", lineHeight: 1.35, fontWeight: 600 }}>
                              {block.content || block.data?.reason || "Please select an immediate emergency or doctor action below."}
                            </div>
                          </div>
                        );
                      }

                      if (block.block_type === "ACTION_CHOICES" && block.actions && block.actions.length > 0) {
                        return (
                          <div key={bIdx} style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
                            {block.actions.map((act: any, idx: number) => {
                              const actCode = act.action || act.type || "";
                              const isDanger = act.style === "DANGER" || actCode === "EMERGENCY_HELP" || actCode === "CALL_108" || actCode === "CALL_14416";
                              const isPrimary = act.style === "PRIMARY" || actCode === "SPEAK_TO_DOCTOR";
                              const translatedLabel = t(`chat.actions.${actCode}`, act.label || actCode);

                              return (
                                <button
                                  key={idx}
                                  onClick={() => handleActionClick(act.type || act.action, { ...msg.structured_payload, ...act })}
                                  style={{
                                    padding: "10px 14px",
                                    borderRadius: 12,
                                    backgroundColor: isDanger ? "#DC2626" : isPrimary ? "#2563EB" : "#F1F5F9",
                                    color: isDanger || isPrimary ? "#FFFFFF" : "#1E293B",
                                    border: isDanger || isPrimary ? "none" : "1px solid #CBD5E1",
                                    fontWeight: 800,
                                    fontSize: 13,
                                    cursor: "pointer",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    gap: 6,
                                    boxShadow: isDanger ? "0 2px 8px rgba(220,38,38,0.3)" : "none"
                                  }}
                                >
                                  {(actCode === "EMERGENCY_HELP" || actCode === "CALL_108" || actCode === "CALL_14416") && <Phone size={15} />}
                                  {actCode === "SPEAK_TO_DOCTOR" && <Stethoscope size={15} />}
                                  {actCode === "REQUEST_ASHA" && <HomeIcon size={15} />}
                                  {actCode === "CALL_ASHA" && <Phone size={15} />}
                                  {actCode === "FIND_FACILITY" && <MapPin size={15} />}
                                  {actCode === "HEALTH_HELP" && <Activity size={15} />}
                                  {actCode === "CHECK_SCHEMES" && <CheckCircle2 size={15} />}
                                  {actCode === "VIEW_CARE_RECORD" && <Activity size={15} />}
                                  <span>{translatedLabel}</span>
                                </button>
                              );
                            })}
                          </div>
                        );
                      }

                      return null;
                    })}

                    {/* Fallback Action Buttons if no blocks present */}
                    {(!msg.structured_payload?.blocks || msg.structured_payload.blocks.length === 0) && msg.structured_payload?.actions && msg.structured_payload.actions.length > 0 && (
                      <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
                        {msg.structured_payload.actions.map((act: any, idx: number) => {
                          const actCode = act.action || act.type || "";
                          const isDanger = act.style === "DANGER" || actCode === "EMERGENCY_HELP" || actCode === "CALL_108" || actCode === "CALL_14416";
                          const isPrimary = act.style === "PRIMARY" || actCode === "SPEAK_TO_DOCTOR";
                          const translatedLabel = t(`chat.actions.${actCode}`, act.label || actCode);

                          return (
                            <button
                              key={idx}
                              onClick={() => handleActionClick(act.type || act.action)}
                              style={{
                                padding: "10px 14px",
                                borderRadius: 12,
                                backgroundColor: isDanger ? "#DC2626" : isPrimary ? "#2563EB" : "#F1F5F9",
                                color: isDanger || isPrimary ? "#FFFFFF" : "#1E293B",
                                border: isDanger || isPrimary ? "none" : "1px solid #CBD5E1",
                                fontWeight: 800,
                                fontSize: 13,
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                gap: 6,
                                boxShadow: isDanger ? "0 2px 8px rgba(220,38,38,0.3)" : "none"
                              }}
                            >
                              {(actCode === "EMERGENCY_HELP" || actCode === "CALL_108" || actCode === "CALL_14416") && <Phone size={15} />}
                              {actCode === "SPEAK_TO_DOCTOR" && <Stethoscope size={15} />}
                              {actCode === "REQUEST_ASHA" && <HomeIcon size={15} />}
                              {actCode === "CALL_ASHA" && <Phone size={15} />}
                              {actCode === "FIND_FACILITY" && <MapPin size={15} />}
                              {actCode === "HEALTH_HELP" && <Activity size={15} />}
                              {actCode === "CHECK_SCHEMES" && <CheckCircle2 size={15} />}
                              {actCode === "VIEW_CARE_RECORD" && <Activity size={15} />}
                              <span>{translatedLabel}</span>
                            </button>
                          );
                        })}
                      </div>
                    )}

                    {/* Contextual Suggested Quick Replies Chips */}
                    {isAssistant && msg.structured_payload?.suggested_replies && msg.structured_payload.suggested_replies.length > 0 && (
                      <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {msg.structured_payload.suggested_replies.map((reply: string, rIdx: number) => {
                          const translatedReply = t(`chat.quickReplies.${reply}`, reply);
                          return (
                            <button
                              key={rIdx}
                              onClick={() => handleQuickReply(translatedReply)}
                              style={{
                                padding: "6px 12px",
                                backgroundColor: "#EFF6FF",
                                border: "1px solid #93C5FD",
                                borderRadius: 16,
                                color: "#1D4ED8",
                                fontSize: 12,
                                fontWeight: 700,
                                cursor: "pointer",
                                boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
                              }}
                            >
                              💬 {translatedReply}
                            </button>
                          );
                        })}
                      </div>
                    )}

                    {/* Timestamp & Status */}
                    <div
                      style={{
                        fontSize: 10,
                        marginTop: 4,
                        textAlign: "right",
                        opacity: isAssistant ? 0.6 : 0.85,
                        fontWeight: 600
                      }}
                    >
                      {msg.created_at
                        ? new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                        : "Just now"}
                      {!isAssistant && " • ✓✓"}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* DRAFT TRANSCRIPT CONFIRMATION BUBBLE */}
            {pendingDraft && (
              <div
                style={{
                  alignSelf: "flex-end",
                  maxWidth: "90%",
                  backgroundColor: "#FFFBEB",
                  border: "2px solid #FCD34D",
                  borderRadius: 18,
                  padding: "14px",
                  boxShadow: "0 4px 16px rgba(245, 158, 11, 0.15)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 8
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11, fontWeight: 700, color: "#92400E" }}>
                  <span>🎙️ {t("assistant:transcript_label", "Spoken words (Draft):")}</span>
                  <span style={{ padding: "2px 6px", borderRadius: 8, backgroundColor: "#FDE68A" }}>
                    {pendingDraft.detectedLanguage || "mr-IN"}
                  </span>
                </div>

                {pendingDraft.isEditing ? (
                  <textarea
                    value={pendingDraft.editedText}
                    onChange={(e) =>
                      setPendingDraft({ ...pendingDraft, editedText: e.target.value })
                    }
                    rows={3}
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      borderRadius: 10,
                      border: "1.5px solid #2563EB",
                      fontSize: 14,
                      fontFamily: "inherit",
                      outline: "none"
                    }}
                  />
                ) : (
                  <div style={{ fontSize: 15, fontWeight: 700, color: "#1E293B", lineHeight: 1.4 }}>
                    "{pendingDraft.editedText}"
                  </div>
                )}

                {/* Draft Actions */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
                  <button
                    onClick={handleConfirmTranscript}
                    disabled={isProcessing}
                    style={{
                      flex: 1,
                      padding: "10px 14px",
                      backgroundColor: "#166534",
                      color: "#FFFFFF",
                      borderRadius: 12,
                      border: "none",
                      fontWeight: 800,
                      fontSize: 13,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 4
                    }}
                  >
                    <Check size={16} />
                    {isProcessing ? t("assistant:processing", "Processing...") : t("assistant:confirm_transcript", "Yes, Confirm")}
                  </button>

                  <button
                    onClick={() =>
                      setPendingDraft({ ...pendingDraft, isEditing: !pendingDraft.isEditing })
                    }
                    style={{
                      padding: "10px 12px",
                      backgroundColor: "#FFFFFF",
                      color: "#334155",
                      borderRadius: 12,
                      border: "1px solid #CBD5E1",
                      fontWeight: 700,
                      fontSize: 12,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 4
                    }}
                  >
                    <Edit3 size={14} />
                    {t("assistant:edit_transcript", "Edit")}
                  </button>

                  <button
                    onClick={() => {
                      setPendingDraft(null);
                      handleStartMic();
                    }}
                    style={{
                      padding: "10px 12px",
                      backgroundColor: "#FFFFFF",
                      color: "#334155",
                      borderRadius: 12,
                      border: "1px solid #CBD5E1",
                      fontWeight: 700,
                      fontSize: 12,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 4
                    }}
                  >
                    <RotateCcw size={14} />
                    {t("assistant:speak_again", "Speak Again")}
                  </button>
                </div>
              </div>
            )}

            {/* Processing Indicator */}
            {isProcessing && (
              <div
                style={{
                  alignSelf: "flex-start",
                  backgroundColor: "#FFFFFF",
                  borderRadius: "18px 18px 18px 4px",
                  padding: "10px 16px",
                  border: "1px solid #E2E8F0",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  fontSize: 12,
                  color: "#64748B",
                  fontWeight: 600
                }}
              >
                <Activity size={16} className="animate-spin" color="#2563EB" />
                <span>{t("assistant:processing", "Analyzing clinical intent & safety rules...")}</span>
              </div>
            )}

            {/* Contextual Quick Reply Suggestions (Only on Initial Stage) */}
            {!pendingDraft && !isProcessing && messages.length <= 1 && (
              <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
                {[
                  t("assistant:quick_reply_chest_pain", "छातीत दुखत आहे"),
                  t("assistant:quick_reply_fever", "दोन दिवसांपासून ताप आहे"),
                  t("assistant:quick_reply_doctor", "मला डॉक्टरांशी बोलायचे आहे"),
                  t("assistant:quick_reply_asha", "आशा ताईंची मदत हवी आहे")
                ].map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleQuickReply(chip)}
                    style={{
                      padding: "6px 12px",
                      backgroundColor: "#FFFFFF",
                      border: "1px solid #BFDBFE",
                      borderRadius: 16,
                      color: "#1D4ED8",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer",
                      boxShadow: "0 1px 4px rgba(0,0,0,0.03)"
                    }}
                  >
                    {chip}
                  </button>
                ))}
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Sticky Bottom Recording Waveform Overlay */}
      {recState === "RECORDING" && (
        <div
          style={{
            position: "absolute",
            bottom: 74,
            left: 12,
            right: 12,
            backgroundColor: "#FFFFFF",
            borderRadius: 20,
            padding: "12px 16px",
            boxShadow: "0 8px 30px rgba(0,0,0,0.18)",
            border: "2px solid #EF4444",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            zIndex: 30,
            animation: "pulse 1.2s infinite"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 14,
                height: 14,
                borderRadius: "50%",
                backgroundColor: "#DC2626",
                animation: "ping 1s infinite"
              }}
            />
            <div>
              <div style={{ fontSize: 13, fontWeight: 800, color: "#991B1B" }}>
                {t("assistant:recording_active", "Listening to your voice...")}
              </div>
              <div style={{ fontSize: 11, color: "#64748B", fontWeight: 600 }}>
                {recSeconds}s / 30s • Level: {audioLevel}%
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              onClick={handleCancelMic}
              style={{
                padding: "6px 12px",
                borderRadius: 14,
                backgroundColor: "#F1F5F9",
                border: "none",
                color: "#64748B",
                fontWeight: 700,
                fontSize: 12,
                cursor: "pointer"
              }}
            >
              {t("assistant:cancel_recording", "Cancel")}
            </button>
            <button
              onClick={handleStopMic}
              style={{
                padding: "8px 16px",
                borderRadius: 14,
                backgroundColor: "#DC2626",
                border: "none",
                color: "#FFFFFF",
                fontWeight: 800,
                fontSize: 13,
                cursor: "pointer"
              }}
            >
              {t("assistant:stop_recording", "Stop & Done")}
            </button>
          </div>
        </div>
      )}

      {/* Sticky Bottom Composer */}
      <footer
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          backgroundColor: "#FFFFFF",
          borderTop: "1px solid #E2E8F0",
          padding: "10px 12px 14px",
          display: "flex",
          alignItems: "center",
          gap: 8,
          zIndex: 20,
          boxShadow: "0 -4px 16px rgba(0,0,0,0.06)"
        }}
      >
        {/* Real Microphone Button (48px) */}
        <button
          onClick={recState === "RECORDING" ? handleStopMic : handleStartMic}
          aria-label={recState === "RECORDING" ? "Stop microphone" : "Start microphone"}
          style={{
            width: 48,
            height: 48,
            minWidth: 48,
            borderRadius: "50%",
            backgroundColor: recState === "RECORDING" ? "#DC2626" : "#2563EB",
            color: "#FFFFFF",
            border: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            boxShadow: recState === "RECORDING" ? "0 0 16px rgba(220, 38, 38, 0.6)" : "0 4px 12px rgba(37, 99, 235, 0.35)",
            transition: "all 0.2s ease"
          }}
        >
          {recState === "RECORDING" ? <MicOff size={22} /> : <Mic size={24} />}
        </button>

        {/* Input Text Box */}
        <input
          ref={inputRef}
          type="text"
          value={inputText}
          onChange={(e) => {
            setInputText(e.target.value);
            if (inputPlaceholder) setInputPlaceholder("");
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSendText();
          }}
          placeholder={inputPlaceholder || t("assistant:input_placeholder", "Type your message or tap mic...")}
          style={{
            flex: 1,
            height: 46,
            borderRadius: 24,
            backgroundColor: "#F1F5F9",
            border: "1px solid #CBD5E1",
            padding: "0 16px",
            fontSize: 14,
            color: "#0F172A",
            outline: "none",
            fontFamily: "inherit"
          }}
        />

        {/* Send Button */}
        <button
          onClick={() => handleSendText()}
          disabled={!inputText.trim()}
          aria-label="Send message"
          style={{
            width: 46,
            height: 46,
            minWidth: 46,
            borderRadius: "50%",
            backgroundColor: inputText.trim() ? "#2563EB" : "#E2E8F0",
            color: inputText.trim() ? "#FFFFFF" : "#94A3B8",
            border: "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: inputText.trim() ? "pointer" : "default",
            transition: "all 0.2s ease"
          }}
        >
          <Send size={18} />
        </button>
      </footer>

      {/* Structured Multi-Turn Care Handoff Sheet */}
      <CareHandoffReviewSheet
        isOpen={handoffSheetOpen}
        onClose={() => setHandoffSheetOpen(false)}
        requestType={handoffRequestType}
        sessionId={sessionId || undefined}
        needId={activeNeedId || undefined}
        onSuccess={handleHandoffSuccess}
      />
    </div>
  );
};
