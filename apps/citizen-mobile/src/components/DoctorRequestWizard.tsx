import React, { useState, useEffect } from "react";
import { useLanguage } from "@aarogya/i18n";
import {
  User, Users, Mic, Keyboard, Check, AlertTriangle,
  Phone, Video, MessageSquare, Building, ShieldCheck,
  ArrowRight, ArrowLeft, Loader2, MapPin, Sparkles, CheckCircle2
} from "lucide-react";
import { apiClient } from "@aarogya/api-client";
import { BeneficiaryOption } from "@aarogya/shared-types";
import { audioCaptureService } from "../services/audioCaptureService";

interface DoctorRequestWizardProps {
  onBack: () => void;
  onRequestSubmitted: (requestId: string) => void;
  initialChatSessionId?: string;
  initialCitizenNeedId?: string;
  initialChiefComplaint?: string;
  initialSymptoms?: string[];
  initialBeneficiaryId?: string;
  initialPriority?: string;
}

export const DoctorRequestWizard: React.FC<DoctorRequestWizardProps> = ({
  onBack,
  onRequestSubmitted,
  initialChatSessionId,
  initialCitizenNeedId,
  initialChiefComplaint,
  initialSymptoms,
  initialBeneficiaryId,
  initialPriority
}) => {
  const { t, locale } = useLanguage();

  // 6 Steps:
  // 1: Beneficiary Selection
  // 2: Concern & Clinical Symptoms
  // 3: Consultation Channel & Window
  // 4: Care Location Confirmation
  // 5: Consented Sharing Scope
  // 6: Explicit Consent & Submission
  const [step, setStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);
  const [symptomInputError, setSymptomInputError] = useState<string | null>(null);

  // Beneficiaries Canonical State
  const [beneficiaries, setBeneficiaries] = useState<BeneficiaryOption[]>([]);
  const [selectedBeneficiaryId, setSelectedBeneficiaryId] = useState<string | null>(initialBeneficiaryId || null);

  // Derived selected beneficiary
  const selectedBeneficiary =
    beneficiaries.find((b) => b.beneficiaryId === selectedBeneficiaryId) ?? null;

  // Step 2: Intake & Symptoms
  const [inputType, setInputType] = useState<"VOICE" | "TEXT">("VOICE");
  const [isRecording, setIsRecording] = useState(false);
  const [spokenText, setSpokenText] = useState("");
  const [chiefComplaint, setChiefComplaint] = useState(initialChiefComplaint || "");
  const [durationText, setDurationText] = useState("Not provided");
  const [severityLevel, setSeverityLevel] = useState("UNKNOWN");
  const [extractedSymptoms, setExtractedSymptoms] = useState<string[]>(() => {
    if (initialSymptoms && Array.isArray(initialSymptoms)) {
      const seen = new Set<string>();
      const res: string[] = [];
      for (const s of initialSymptoms) {
        const clean = s.trim();
        if (clean && !seen.has(clean.toLowerCase())) {
          seen.add(clean.toLowerCase());
          res.push(clean);
        }
      }
      return res;
    }
    return [];
  });
  const [newSymptomInput, setNewSymptomInput] = useState("");

  // Step 3: Mode & Channel (Strictly CALLBACK and CHAT only for new Citizen requests)
  const [selectedChannel, setSelectedChannel] = useState<"CALLBACK" | "CHAT">("CALLBACK");

  // Safety triage result
  const [safetyPriority, setSafetyPriority] = useState<string>(initialPriority || "ROUTINE");
  const [safetyReason, setSafetyReason] = useState<string | null>(null);
  const [safetyGuidance, setSafetyGuidance] = useState<string | null>(null);
  const [isTriageLoading, setIsTriageLoading] = useState<boolean>(false);

  // Step 4: Location
  const [landmark, setLandmark] = useState<string>("");
  const [villageName, setVillageName] = useState<string>("Kalyanpur");

  // Step 5: Sharing Scope Checkboxes (Optional scopes UNCHECKED by default)
  const [scopeStructuredSummary, setScopeStructuredSummary] = useState<boolean>(true); // Required
  const [scopeProfile, setScopeProfile] = useState<boolean>(false); // Optional
  const [scopeLocation, setScopeLocation] = useState<boolean>(false); // Optional
  const [scopeRecentMessages, setScopeRecentMessages] = useState<boolean>(false); // Optional
  const [scopeHealthRecords, setScopeHealthRecords] = useState<boolean>(false); // Optional

  // Step 6: Explicit Consent (Enabled once patient reviews)
  const [explicitConsent, setExplicitConsent] = useState<boolean>(true);

  // Load Beneficiaries on Mount
  useEffect(() => {
    let isMounted = true;
    const fetchBeneficiaries = async () => {
      setLoading(true);
      setErrorNotice(null);
      try {
        const res: any = await apiClient.getCitizenBeneficiaries();
        const rawItems = res?.items || res?.data?.items || (Array.isArray(res) ? res : []);
        
        // Canonical deduplication by beneficiaryId and SELF profile
        const seenIds = new Set<string>();
        let selfAdded = false;
        const normalized: BeneficiaryOption[] = [];

        for (const item of rawItems) {
          const bId = String(item.beneficiary_id || item.beneficiaryId || item.id);
          const rawRel = String(item.relationship || item.relationship_type || "SELF").toUpperCase();
          const isSelf = rawRel === "SELF" || item.is_self === true || (item.citizen_id && (item.citizen_id === item.beneficiary_id || item.citizen_id === item.id));

          if (isSelf) {
            if (selfAdded) continue; // Only one SELF option allowed
            selfAdded = true;
          }

          if (seenIds.has(bId)) continue;
          seenIds.add(bId);

          normalized.push({
            beneficiaryId: bId,
            citizenId: item.citizen_id || item.citizenId || null,
            householdMemberId: isSelf ? null : (item.household_member_id || item.householdMemberId || bId),
            profileId: item.profile_id || item.profileId || null,
            displayName: item.display_name || item.displayName || item.full_name || "Citizen",
            relationship: (isSelf ? "SELF" : rawRel) as any,
            age: item.age ?? null,
            gender: item.gender || (item.sex ? String(item.sex).toUpperCase() : null),
            isRegisteredPatient: item.is_registered_patient ?? item.isRegisteredPatient ?? true,
            existingCaseId: item.existing_case_id || item.existingCaseId || null
          });
        }

        if (isMounted) {
          if (normalized.length === 0) {
            // Fetch profile dynamically
            try {
              const profRes: any = await apiClient.getCitizenProfile();
              const prof = profRes?.data || profRes;
              if (prof && (prof.id || prof.user_id)) {
                const dynamicSelf: BeneficiaryOption = {
                  beneficiaryId: prof.id || prof.user_id,
                  citizenId: prof.id,
                  householdMemberId: null,
                  profileId: prof.id,
                  displayName: prof.display_name || prof.legal_name || "Myself",
                  relationship: "SELF",
                  age: prof.age_estimate || 30,
                  gender: prof.sex || "OTHER",
                  isRegisteredPatient: true,
                  existingCaseId: null
                };
                setBeneficiaries([dynamicSelf]);
                setSelectedBeneficiaryId(dynamicSelf.beneficiaryId);
              } else {
                setErrorNotice("Unable to load beneficiary profile. Please check connection.");
              }
            } catch (pErr) {
              setErrorNotice("Failed to load your profile. Please refresh.");
            }
          } else {
            setBeneficiaries(normalized);
            const selfOption = normalized.find((b) => b.relationship === "SELF");
            if (selfOption) {
              setSelectedBeneficiaryId(selfOption.beneficiaryId);
            } else {
              setSelectedBeneficiaryId(normalized[0].beneficiaryId);
            }
          }
        }
      } catch (err: any) {
        console.error("Failed to load beneficiaries:", err);
        if (isMounted) {
          try {
            const profRes: any = await apiClient.getCitizenProfile();
            const prof = profRes?.data || profRes;
            if (prof && (prof.id || prof.user_id)) {
              const dynamicSelf: BeneficiaryOption = {
                beneficiaryId: prof.id || prof.user_id,
                citizenId: prof.id,
                householdMemberId: null,
                profileId: prof.id,
                displayName: prof.display_name || prof.legal_name || "Myself",
                relationship: "SELF",
                age: prof.age_estimate || 30,
                gender: prof.sex || "OTHER",
                isRegisteredPatient: true,
                existingCaseId: null
              };
              setBeneficiaries([dynamicSelf]);
              setSelectedBeneficiaryId(dynamicSelf.beneficiaryId);
            }
          } catch (_) {
            setErrorNotice("Unable to load beneficiaries. Please ensure you are logged in.");
          }
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchBeneficiaries();
    return () => { isMounted = false; };
  }, []);

  // Dynamic backend triage priority recalculation
  const recalculateTriagePriority = async (concern: string, syms: string[]) => {
    setIsTriageLoading(true);
    try {
      const res = await apiClient.previewCareHandoff({
        beneficiary_id: selectedBeneficiary?.beneficiaryId || undefined,
        session_id: initialChatSessionId || undefined,
        need_id: initialCitizenNeedId || undefined,
        request_type: "DOCTOR_CONSULTATION",
        requested_channel: selectedChannel,
        chief_concern: concern.trim() || undefined,
        symptoms: syms
      });
      const data = res?.data || res;
      if (data?.safety?.priority) {
        setSafetyPriority(data.safety.priority);
        setSafetyReason(data.safety.triggered_rule_ids?.length > 0 ? (data.safety.citizen_message || "Priority assessment complete") : null);
        setSafetyGuidance(data.safety.citizen_message || null);
      }
    } catch (e) {
      console.warn("Priority assessment dynamic check unavailable:", e);
    } finally {
      setIsTriageLoading(false);
    }
  };

  // Safe Continue from Step 1 (Beneficiary Selection)
  const handleProceedFromStep1 = async () => {
    if (!selectedBeneficiary || !selectedBeneficiary.beneficiaryId) {
      setErrorNotice("Please select who needs to speak with the doctor.");
      return;
    }

    setLoading(true);
    setErrorNotice(null);

    try {
      // Call preview care handoff safely (works for both Home and Chat paths)
      const previewRes = await apiClient.previewCareHandoff({
        beneficiary_id: selectedBeneficiary.beneficiaryId,
        session_id: initialChatSessionId || undefined,
        need_id: initialCitizenNeedId || undefined,
        request_type: "DOCTOR_CONSULTATION",
        requested_channel: selectedChannel,
        chief_concern: chiefComplaint || undefined,
        symptoms: extractedSymptoms.length > 0 ? extractedSymptoms : undefined
      });

      const packet = previewRes?.data || previewRes;
      if (packet) {
        if (packet.chief_concern && !chiefComplaint) {
          setChiefComplaint(packet.chief_concern);
        }
        if (Array.isArray(packet.symptoms) && packet.symptoms.length > 0 && extractedSymptoms.length === 0) {
          const seen = new Set<string>();
          const syms: string[] = [];
          packet.symptoms.forEach((s: any) => {
            const label = typeof s === "string" ? s : s.display || s.code;
            if (label && typeof label === "string") {
              const clean = label.trim();
              if (clean && !seen.has(clean.toLowerCase())) {
                seen.add(clean.toLowerCase());
                syms.push(clean);
              }
            }
          });
          setExtractedSymptoms(syms);
        }
        if (packet.location?.landmark) {
          setLandmark(packet.location.landmark);
        }
        if (packet.location?.village) {
          setVillageName(packet.location.village);
        }
        if (packet.safety?.priority) {
          setSafetyPriority(packet.safety.priority);
          setSafetyReason(packet.safety.triggered_rule_ids?.length > 0 ? (packet.safety.citizen_message || null) : null);
          setSafetyGuidance(packet.safety.citizen_message || null);
        }
      }

      setStep(2);
    } catch (err: any) {
      console.error("Failed to prepare consultation preview:", err);
      // Even if preview has no prior chat data, we proceed cleanly to Step 2 for Home flow
      setStep(2);
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Voice capture
  const handleVoiceRecord = async () => {
    if (isRecording) {
      setIsRecording(false);
      try {
        const result = await audioCaptureService.stopRecording(locale || "mr-IN");
        if (result.transcript) {
          const cleanTranscript = result.transcript.trim();
          setSpokenText(cleanTranscript);
          setChiefComplaint(cleanTranscript);
          extractSymptomsFromText(cleanTranscript);
        } else if (result.errorMessage) {
          setErrorNotice(result.errorMessage);
        }
      } catch (err: any) {
        setErrorNotice(err.message || "Failed to process speech.");
      }
      return;
    }

    setErrorNotice(null);
    setIsRecording(true);
    try {
      await audioCaptureService.startRecording(
        locale || "mr-IN",
        undefined,
        undefined,
        { maxDurationSeconds: 20 }
      );
    } catch (err: any) {
      setIsRecording(false);
      setErrorNotice(err.message || "Microphone capture failed. Please type instead.");
    }
  };

  const extractSymptomsFromText = (text: string) => {
    const syms: string[] = [...extractedSymptoms];
    const textLower = text.toLowerCase();
    
    const checkAndAdd = (name: string) => {
      const lower = name.toLowerCase();
      if (!syms.some(s => s.toLowerCase() === lower)) {
        syms.push(name);
      }
    };

    if (textLower.includes("छातीत") || textLower.includes("chest") || textLower.includes("छाती") || textLower.includes("सीने")) {
      checkAndAdd("Chest Pain");
    }
    if (textLower.includes("डोके") || textLower.includes("headache") || textLower.includes("सिर") || textLower.includes("डोकेदुखी")) {
      checkAndAdd("Severe Headache");
    }
    if (textLower.includes("ताप") || textLower.includes("fever") || textLower.includes("बुखार")) {
      checkAndAdd("High Fever");
    }
    if (textLower.includes("धाप") || textLower.includes("breath") || textLower.includes("सांस") || textLower.includes("श्वास")) {
      checkAndAdd("Shortness of Breath");
    }
    
    // Deduplicate array case-insensitively
    const seen = new Set<string>();
    const deduplicated = syms.filter(s => {
      const clean = s.trim().toLowerCase();
      if (!clean || seen.has(clean)) return false;
      seen.add(clean);
      return true;
    });

    setExtractedSymptoms(deduplicated);
    recalculateTriagePriority(text, deduplicated);
  };

  const handleAddSymptom = () => {
    setSymptomInputError(null);
    const trimmed = newSymptomInput.trim();
    if (!trimmed) {
      setSymptomInputError(t("wizard.symptom_empty_error", "Please enter a symptom name."));
      return;
    }
    
    const exists = extractedSymptoms.some(s => s.trim().toLowerCase() === trimmed.toLowerCase());
    if (exists) {
      setSymptomInputError(t("wizard.symptom_duplicate_error", "This symptom is already added."));
      return;
    }

    const updated = [...extractedSymptoms, trimmed];
    setExtractedSymptoms(updated);
    setNewSymptomInput("");
    setSymptomInputError(null);
    recalculateTriagePriority(chiefComplaint, updated);
  };

  const handleRemoveSymptom = (sym: string) => {
    const updated = extractedSymptoms.filter((s) => s.trim().toLowerCase() !== sym.trim().toLowerCase());
    setExtractedSymptoms(updated);
    recalculateTriagePriority(chiefComplaint, updated);
  };

  // Step 2 Proceed
  const handleProceedFromStep2 = () => {
    if (!chiefComplaint.trim() && extractedSymptoms.length === 0) {
      setErrorNotice("Health concern is required. Please speak or type your symptoms.");
      return;
    }
    setErrorNotice(null);
    if (extractedSymptoms.length === 0 && chiefComplaint.trim()) {
      extractSymptomsFromText(chiefComplaint);
    }
    setStep(3);
  };

  // Step 6: Atomic Submit Request
  const handleSubmitFinalRequest = async () => {
    if (!explicitConsent) {
      setErrorNotice("Please confirm explicit consent before submitting.");
      return;
    }

    if (!selectedBeneficiary) {
      setErrorNotice("Patient selection required.");
      return;
    }

    setSubmitting(true);
    setErrorNotice(null);

    const sharingScope = {
      share_structured_summary: scopeStructuredSummary,
      share_profile: scopeProfile,
      share_location: scopeLocation,
      share_recent_messages: scopeRecentMessages,
      share_existing_health_records: scopeHealthRecords
    };

    const finalPacket = {
      chief_concern: chiefComplaint.trim() || extractedSymptoms.join(", ") || "Doctor consultation requested",
      symptoms: extractedSymptoms.map((s) => ({
        code: s.toUpperCase().replace(/\s+/g, "_"),
        display: s,
        status: "CONFIRMED",
        source: "AI_STRUCTURED_CITIZEN_CONFIRMED"
      })),
      duration_text: durationText,
      severity_level: severityLevel,
      location: {
        village: villageName,
        landmark: landmark || undefined
      },
      sharing_scope: sharingScope
    };

    const idempotencyKey = `idemp-doc-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;

    try {
      const payload = {
        beneficiary_id: selectedBeneficiary.beneficiaryId,
        chat_session_id: initialChatSessionId || undefined,
        citizen_need_id: initialCitizenNeedId || undefined,
        channel: selectedChannel,
        handoff_packet: finalPacket,
        sharing_scope: sharingScope,
        chief_complaint: finalPacket.chief_concern,
        symptoms: extractedSymptoms,
        preferred_language: locale || "mr-IN",
        idempotency_key: idempotencyKey
      };

      const res = await apiClient.createCitizenDoctorRequest(payload);
      const resData = res?.data || res;
      const targetReqId = resData?.service_request_id || resData?.request_id || resData?.id || resData?.request_reference || resData?.reference;
      if (!targetReqId) {
        throw new Error("Invalid response received from server");
      }
      onRequestSubmitted(targetReqId);
    } catch (err: any) {
      console.error("Failed to submit doctor consultation request:", err);
      setErrorNotice(err?.message || "Failed to submit doctor consultation request. Please retry.");
    } finally {
      setSubmitting(false);
    }
  };

  const isEn = locale?.startsWith("en");

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F8FAFC", display: "flex", flexDirection: "column" }}>
      {/* Wizard Top Header */}
      <div style={{ backgroundColor: "#FFFFFF", padding: "14px 16px", borderBottom: "1px solid #E2E8F0", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <button
          onClick={step === 1 ? onBack : () => setStep((s) => s - 1)}
          style={{ border: "none", background: "transparent", cursor: "pointer", color: "#1E293B", display: "flex", alignItems: "center", gap: 4, fontWeight: 700, fontSize: 13 }}
        >
          <ArrowLeft size={18} /> {t("common.back", "Back")}
        </button>
        <div style={{ fontSize: 12, fontWeight: 800, color: "#2563EB", backgroundColor: "#EFF6FF", padding: "4px 10px", borderRadius: 12 }}>
          {t("common.step_indicator", { step: String(step), total: "6", defaultValue: `Step ${step} of 6` })}
        </div>
      </div>

      {/* Main Container */}
      <div style={{ flex: 1, padding: 16, display: "flex", flexDirection: "column", gap: 16, maxWidth: 480, margin: "0 auto", width: "100%" }}>
        {errorNotice && (
          <div style={{ padding: 12, backgroundColor: "#FEF2F2", border: "1px solid #FCA5A5", borderRadius: 12, color: "#991B1B", fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
            <AlertTriangle size={18} />
            <span>{errorNotice}</span>
          </div>
        )}

        {loading && step === 1 ? (
          <div style={{ padding: "40px 0", textAlign: "center" }}>
            <Loader2 size={36} color="#2563EB" className="animate-spin" style={{ margin: "0 auto 12px" }} />
            <p style={{ fontSize: 14, color: "#64748B", margin: 0 }}>
              {t("common.loading_family", "Loading family members...")}
            </p>
          </div>
        ) : null}

        {/* STEP 1: SELECT BENEFICIARY */}
        {!loading && step === 1 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <h2 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("wizard.step1_title", "1. Select Patient")}
            </h2>
            <p style={{ fontSize: 13, color: "#64748B", margin: 0 }}>
              {t("wizard.step1_desc", "Who needs to speak with the doctor today?")}
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {beneficiaries.map((b) => {
                const isSelected = selectedBeneficiaryId === b.beneficiaryId;
                const isSelf = b.relationship === "SELF";
                const relLabel = t(`beneficiary.relationship.${b.relationship}`, b.relationship);
                return (
                  <div
                    key={b.beneficiaryId}
                    onClick={() => {
                      setSelectedBeneficiaryId(b.beneficiaryId);
                      setErrorNotice(null);
                    }}
                    style={{
                      padding: 16,
                      borderRadius: 16,
                      border: `2px solid ${isSelected ? "#2563EB" : "#E2E8F0"}`,
                      backgroundColor: isSelected ? "#EFF6FF" : "#FFFFFF",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      transition: "all 0.15s ease"
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <div style={{ width: 44, height: 44, borderRadius: "50%", backgroundColor: isSelf ? "#DBEAFE" : "#F1F5F9", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>
                        {isSelf ? "👩" : "👤"}
                      </div>
                      <div>
                        <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>
                          {isSelf ? (b.displayName ? `${b.displayName.replace(/\s*\((?:Myself|मी स्वतः|खुद)\)/gi, "").trim()} (${t("common.myself", "Myself")})` : t("common.myself", "Myself")) : b.displayName}
                        </div>
                        <div style={{ fontSize: 12, color: "#64748B" }}>
                          {relLabel} {b.age ? `• ${b.age} ${t("common.age", "yrs")}` : ""} {b.gender ? `• ${b.gender}` : ""}
                        </div>
                      </div>
                    </div>
                    <div style={{ width: 22, height: 22, borderRadius: "50%", border: `2px solid ${isSelected ? "#2563EB" : "#CBD5E1"}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      {isSelected && <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "#2563EB" }} />}
                    </div>
                  </div>
                );
              })}
            </div>

            <button
              id="btn-wizard-step1-continue"
              onClick={handleProceedFromStep1}
              disabled={loading || !selectedBeneficiaryId || beneficiaries.length === 0}
              style={{
                marginTop: 10,
                padding: "14px",
                backgroundColor: !selectedBeneficiaryId ? "#94A3B8" : "#2563EB",
                color: "#FFFFFF",
                fontWeight: 800,
                fontSize: 15,
                borderRadius: 16,
                border: "none",
                cursor: !selectedBeneficiaryId ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                boxShadow: !selectedBeneficiaryId ? "none" : "0 4px 12px rgba(37, 99, 235, 0.2)"
              }}
            >
              <span>{t("wizard.step1_continue", { name: selectedBeneficiary?.displayName.split(" ")[0] || t("wizard.step1_title", "Patient"), defaultValue: `Continue with ${selectedBeneficiary?.displayName.split(" ")[0] || "Patient"}` })}</span>
              <ArrowRight size={18} />
            </button>
          </div>
        )}

        {/* STEP 2: HEALTH CONCERN & CONFIRMED FACTS */}
        {step === 2 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <h2 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("wizard.step2_title", "2. Describe Health Concern")}
            </h2>
            <div style={{ fontSize: 12, color: "#2563EB", backgroundColor: "#EFF6FF", padding: "6px 12px", borderRadius: 8, fontWeight: 700 }}>
              {t("wizard.step2_patient_badge", {
                name: selectedBeneficiary?.displayName || "",
                relationship: t(`beneficiary.relationship.${selectedBeneficiary?.relationship || "SELF"}`, selectedBeneficiary?.relationship || "Self"),
                defaultValue: `Patient: ${selectedBeneficiary?.displayName} (${selectedBeneficiary?.relationship})`
              })}
            </div>

            {/* Voice / Type Toggle */}
            <div style={{ display: "flex", backgroundColor: "#E2E8F0", padding: 4, borderRadius: 12 }}>
              <button
                type="button"
                onClick={() => setInputType("VOICE")}
                style={{
                  flex: 1,
                  padding: "8px 0",
                  borderRadius: 10,
                  border: "none",
                  backgroundColor: inputType === "VOICE" ? "#FFFFFF" : "transparent",
                  fontWeight: 800,
                  fontSize: 13,
                  cursor: "pointer",
                  color: inputType === "VOICE" ? "#2563EB" : "#64748B",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6
                }}
              >
                <Mic size={16} /> {t("wizard.step2_speak_tab", "Speak")}
              </button>
              <button
                type="button"
                onClick={() => setInputType("TEXT")}
                style={{
                  flex: 1,
                  padding: "8px 0",
                  borderRadius: 10,
                  border: "none",
                  backgroundColor: inputType === "TEXT" ? "#FFFFFF" : "transparent",
                  fontWeight: 800,
                  fontSize: 13,
                  cursor: "pointer",
                  color: inputType === "TEXT" ? "#2563EB" : "#64748B",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6
                }}
              >
                <Keyboard size={16} /> {t("wizard.step2_type_tab", "Type")}
              </button>
            </div>

            {inputType === "VOICE" ? (
              <div style={{ textAlign: "center", padding: "20px 0", backgroundColor: "#FFFFFF", borderRadius: 20, border: "1px solid #E2E8F0" }}>
                <button
                  type="button"
                  onClick={handleVoiceRecord}
                  style={{
                    width: 88,
                    height: 88,
                    borderRadius: "50%",
                    backgroundColor: isRecording ? "#DC2626" : "#2563EB",
                    color: "#FFFFFF",
                    border: "none",
                    cursor: "pointer",
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    boxShadow: isRecording ? "0 0 24px rgba(220, 38, 38, 0.5)" : "0 8px 24px rgba(37, 99, 235, 0.3)"
                  }}
                >
                  <Mic size={36} />
                </button>
                <div style={{ fontSize: 13, fontWeight: 700, color: isRecording ? "#DC2626" : "#1E293B", marginTop: 12 }}>
                  {isRecording ? t("common.listening_in_lang", "Listening to your voice...") : t("common.tap_mic_to_speak", "Tap mic and describe symptoms")}
                </div>
                <div style={{ fontSize: 11, color: "#64748B", marginTop: 4 }}>
                  {t("common.active_stt", "Active STT: Sarvam AI Indic Speech")}
                </div>

                {spokenText && (
                  <div style={{ marginTop: 14, margin: "14px 16px 0", padding: 12, backgroundColor: "#F8FAFC", borderRadius: 12, border: "1px solid #E2E8F0", textAlign: "left" }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#64748B", marginBottom: 4 }}>{t("common.spoken_transcript", "Spoken Transcript:")}</div>
                    <div style={{ fontSize: 14, color: "#0F172A", fontWeight: 600 }}>"{spokenText}"</div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <textarea
                  rows={4}
                  value={chiefComplaint}
                  onChange={(e) => {
                    setChiefComplaint(e.target.value);
                    extractSymptomsFromText(e.target.value);
                  }}
                  placeholder={t("wizard.step2_placeholder", "Describe symptoms, duration, and how severe it feels...")}
                  style={{ width: "100%", padding: 12, borderRadius: 14, border: "1.5px solid #CBD5E1", fontSize: 14, outline: "none" }}
                />
              </div>
            )}

            {/* Priority Assessment Card */}
            <div style={{ backgroundColor: "#FFFFFF", padding: 14, borderRadius: 16, border: "1px solid #E2E8F0" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, fontWeight: 800, color: "#475569" }}>
                  {t("wizard.triage_priority_label", "Triage Priority Level")}
                </span>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 800,
                    padding: "3px 10px",
                    borderRadius: 8,
                    backgroundColor: safetyPriority === "URGENT" ? "#FEE2E2" : (safetyPriority === "HIGH" ? "#FEF3C7" : "#DCFCE7"),
                    color: safetyPriority === "URGENT" ? "#DC2626" : (safetyPriority === "HIGH" ? "#92400E" : "#166534"),
                    border: `1px solid ${safetyPriority === "URGENT" ? "#FCA5A5" : (safetyPriority === "HIGH" ? "#FDE68A" : "#BBF7D0")}`
                  }}
                >
                  {isTriageLoading ? (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                      <Loader2 size={10} className="animate-spin" /> Evaluating...
                    </span>
                  ) : (
                    safetyPriority === "URGENT" ? `⚠️ ${t("priority.URGENT", "URGENT")}` : (safetyPriority === "HIGH" ? t("priority.HIGH", "HIGH") : t("priority.ROUTINE", "ROUTINE"))
                  )}
                </span>
              </div>
              {safetyGuidance && (
                <div style={{ fontSize: 12, color: safetyPriority === "URGENT" ? "#B91C1C" : "#475569", marginTop: 6, fontWeight: 600 }}>
                  {safetyGuidance}
                </div>
              )}
            </div>

            {/* Symptoms Tags */}
            <div style={{ backgroundColor: "#FFFFFF", padding: 14, borderRadius: 16, border: "1px solid #E2E8F0" }}>
              <label style={{ fontSize: 12, fontWeight: 800, color: "#475569", display: "block", marginBottom: 8 }}>
                {t("wizard.step2_identified_symptoms", "Identified Symptoms")}
              </label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
                {extractedSymptoms.map((sym, i) => {
                  const symKey = sym.toUpperCase().replace(/[\s\/\-]+/g, "_");
                  const symDisplay = t(`symptoms.${symKey}`, t(`concerns.${symKey}`, sym === "General health checkup / care guidance" ? t("concerns.GENERAL_HEALTH_GUIDANCE", sym) : sym));
                  return (
                    <span
                      key={i}
                      style={{
                        padding: "4px 10px",
                        borderRadius: 10,
                        backgroundColor: "#DBEAFE",
                        color: "#1E40AF",
                        fontSize: 13,
                        fontWeight: 700,
                        display: "flex",
                        alignItems: "center",
                        gap: 6
                      }}
                    >
                      {symDisplay}
                      <button
                        type="button"
                        onClick={() => handleRemoveSymptom(sym)}
                        style={{ border: "none", background: "none", color: "#6B7280", cursor: "pointer", padding: 0, fontSize: 16, lineHeight: 1 }}
                        title="Remove symptom"
                      >
                        ×
                      </button>
                    </span>
                  );
                })}
              </div>

              <div style={{ display: "flex", gap: 8 }}>
                <input
                  type="text"
                  value={newSymptomInput}
                  onChange={(e) => {
                    setNewSymptomInput(e.target.value);
                    if (symptomInputError) setSymptomInputError(null);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddSymptom();
                    }
                  }}
                  placeholder={t("wizard.step2_add_symptom_placeholder", "Add symptom (e.g. Fever)")}
                  style={{ flex: 1, padding: "8px 12px", borderRadius: 10, border: `1px solid ${symptomInputError ? '#EF4444' : '#CBD5E1'}`, fontSize: 13, outline: "none" }}
                />
                <button
                  type="button"
                  id="btn-add-symptom"
                  onClick={handleAddSymptom}
                  style={{ padding: "8px 14px", borderRadius: 10, backgroundColor: "#2563EB", color: "#FFFFFF", border: "none", fontWeight: 700, fontSize: 13, cursor: "pointer" }}
                >
                  {t("common.add", "Add")}
                </button>
              </div>
              {symptomInputError && (
                <div style={{ color: "#DC2626", fontSize: 11, fontWeight: 700, marginTop: 4 }}>
                  {symptomInputError}
                </div>
              )}
            </div>

            {/* Duration and Severity */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("common.duration", "Duration")}</label>
                <select
                  value={durationText}
                  onChange={(e) => setDurationText(e.target.value)}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 12, border: "1px solid #CBD5E1", marginTop: 4, fontSize: 13, backgroundColor: "#FFFFFF" }}
                >
                  <option value="Not provided">{t("common.value.NOT_PROVIDED", "Not provided")}</option>
                  <option value="Few hours">{t("common.value.FEW_HOURS", "Few hours")}</option>
                  <option value="1 day">{t("common.value.ONE_DAY", "1 day")}</option>
                  <option value="2 days">{t("common.value.TWO_DAYS", "2 days")}</option>
                  <option value="3-5 days">{t("common.value.THREE_FIVE_DAYS", "3-5 days")}</option>
                  <option value="Over a week">{t("common.value.OVER_A_WEEK", "Over a week")}</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("common.severity", "Severity")}</label>
                <select
                  value={severityLevel}
                  onChange={(e) => setSeverityLevel(e.target.value)}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 12, border: "1px solid #CBD5E1", marginTop: 4, fontSize: 13, backgroundColor: "#FFFFFF" }}
                >
                  <option value="UNKNOWN">{t("common.value.UNKNOWN", "Not specified")}</option>
                  <option value="MILD">{t("common.value.MILD", "Mild")}</option>
                  <option value="MODERATE">{t("common.value.MODERATE", "Moderate")}</option>
                  <option value="SEVERE">{t("common.value.SEVERE", "Severe")}</option>
                </select>
              </div>
            </div>

            <button
              type="button"
              id="btn-wizard-step2-continue"
              onClick={handleProceedFromStep2}
              style={{
                padding: "14px",
                backgroundColor: "#2563EB",
                color: "#FFFFFF",
                fontWeight: 800,
                fontSize: 15,
                borderRadius: 16,
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                marginTop: 8
              }}
            >
              <span>{t("wizard.step2_continue", "Continue to Channel Selection")}</span>
              <ArrowRight size={18} />
            </button>
          </div>
        )}

        {/* STEP 3: CONSULTATION CHANNEL */}
        {step === 3 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <h2 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("wizard.step3_title", "3. Select Consultation Channel")}
            </h2>

            {[
              { id: "CALLBACK", label: t("consultation.channel.CALLBACK", "Doctor Phone Callback"), desc: t("wizard.step3_desc_callback", "Doctor will call your registered phone"), icon: Phone, badge: t("wizard.step3_badge_recommended", "Recommended"), available: true },
              { id: "CHAT", label: t("consultation.channel.CHAT", "Doctor Chat Advice"), desc: t("wizard.step3_desc_chat", "Structured written consultation guidance"), icon: MessageSquare, badge: t("wizard.step3_badge_available", "Available"), available: true }
            ].map((ch) => {
              const Icon = ch.icon;
              const isSelected = selectedChannel === ch.id;
              const isAvailable = ch.available;
              return (
                <div
                  key={ch.id}
                  id={`channel-option-${ch.id.toLowerCase()}`}
                  onClick={isAvailable ? () => setSelectedChannel(ch.id as any) : undefined}
                  style={{
                    padding: 16,
                    borderRadius: 16,
                    border: `2px solid ${isSelected ? "#2563EB" : "#E2E8F0"}`,
                    backgroundColor: !isAvailable ? "#F1F5F9" : (isSelected ? "#EFF6FF" : "#FFFFFF"),
                    opacity: !isAvailable ? 0.6 : 1,
                    cursor: isAvailable ? "pointer" : "not-allowed",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between"
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: isAvailable ? "#DBEAFE" : "#E2E8F0", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <Icon size={20} color={isAvailable ? "#2563EB" : "#64748B"} />
                    </div>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 800, color: isAvailable ? "#0F172A" : "#64748B" }}>{ch.label}</div>
                      <div style={{ fontSize: 11, color: "#64748B" }}>{ch.desc}</div>
                    </div>
                  </div>
                  <span style={{ fontSize: 10, fontWeight: 800, padding: "2px 8px", borderRadius: 8, backgroundColor: isSelected ? "#DBEAFE" : "#E2E8F0", color: isSelected ? "#1E40AF" : "#475569" }}>
                    {ch.badge}
                  </span>
                </div>
              );
            })}

            <button
              type="button"
              id="btn-wizard-step3-continue"
              onClick={() => setStep(4)}
              style={{
                marginTop: 10,
                padding: "14px",
                backgroundColor: "#2563EB",
                color: "#FFFFFF",
                fontWeight: 800,
                fontSize: 15,
                borderRadius: 16,
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8
              }}
            >
              <span>{t("wizard.step3_continue", "Confirm Channel & Proceed")}</span>
              <ArrowRight size={18} />
            </button>
          </div>
        )}

        {/* STEP 4: CARE LOCATION */}
        {step === 4 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <h2 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("wizard.step4_title", "4. Confirm Care Location")}
            </h2>

            <div style={{ backgroundColor: "#FFFFFF", padding: 16, borderRadius: 18, border: "1px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 800, color: "#475569" }}>{t("wizard.step4_village_label", "Village")}</label>
                <input
                  type="text"
                  value={villageName}
                  onChange={(e) => setVillageName(e.target.value)}
                  style={{ width: "100%", padding: 10, borderRadius: 10, border: "1px solid #CBD5E1", marginTop: 4, fontSize: 13 }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 800, color: "#475569" }}>{t("wizard.step4_landmark_label", "Nearby Landmark / House Address")}</label>
                <input
                  type="text"
                  value={landmark}
                  onChange={(e) => setLandmark(e.target.value)}
                  placeholder={t("wizard.step4_landmark_placeholder", "e.g. Near Kalyanpur Gram Panchayat")}
                  style={{ width: "100%", padding: 10, borderRadius: 10, border: "1px solid #CBD5E1", marginTop: 4, fontSize: 13 }}
                />
              </div>

              <div style={{ padding: 10, backgroundColor: "#F0FDF4", borderRadius: 10, border: "1px solid #BBF7D0", fontSize: 12, color: "#166534", display: "flex", alignItems: "center", gap: 6 }}>
                <MapPin size={16} />
                <span>{t("wizard.step4_assigned_facility", "Assigned Facility: Kalyanpur Primary Health Centre (PHC-09)")}</span>
              </div>
            </div>

            <button
              type="button"
              id="btn-wizard-step4-continue"
              onClick={() => setStep(5)}
              style={{
                marginTop: 10,
                padding: "14px",
                backgroundColor: "#2563EB",
                color: "#FFFFFF",
                fontWeight: 800,
                fontSize: 15,
                borderRadius: 16,
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8
              }}
            >
              <span>{t("wizard.step4_continue", "Continue to Sharing Scope")}</span>
              <ArrowRight size={18} />
            </button>
          </div>
        )}

        {/* STEP 5: SHARING SCOPE */}
        {step === 5 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <h2 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("wizard.step5_title", "5. Consented Sharing Scope")}
            </h2>
            <p style={{ fontSize: 12, color: "#64748B", margin: 0 }}>
              {t("wizard.step5_desc", "Select what clinical information will be shared with the PHC Medical Officer.")}
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[
                { label: t("wizard.step5_scope_symptoms", "Confirmed Symptoms & Chief Concern"), checked: scopeStructuredSummary, toggle: () => setScopeStructuredSummary(!scopeStructuredSummary), locked: true },
                { label: t("wizard.step5_scope_profile", "Patient Profile & Demographics"), checked: scopeProfile, toggle: () => setScopeProfile(!scopeProfile), locked: false },
                { label: t("wizard.step5_scope_location", "Village Location & Landmark"), checked: scopeLocation, toggle: () => setScopeLocation(!scopeLocation), locked: false },
                { label: t("wizard.step5_scope_chat", "Recent Assistant Chat Transcript"), checked: scopeRecentMessages, toggle: () => setScopeRecentMessages(!scopeRecentMessages), locked: false },
                { label: t("wizard.step5_scope_records", "Previous Health & Prescription Records"), checked: scopeHealthRecords, toggle: () => setScopeHealthRecords(!scopeHealthRecords), locked: false }
              ].map((item, idx) => (
                <div
                  key={idx}
                  onClick={item.locked ? undefined : item.toggle}
                  style={{
                    padding: 14,
                    borderRadius: 14,
                    border: item.checked ? "1.5px solid #2563EB" : "1px solid #E2E8F0",
                    backgroundColor: item.checked ? "#F8FAFC" : "#FFFFFF",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    cursor: item.locked ? "default" : "pointer"
                  }}
                >
                  <span style={{ fontSize: 13, fontWeight: 700, color: item.locked ? "#64748B" : "#1E293B" }}>
                    {item.label} {item.locked && t("wizard.step5_required_tag", "(Required)")}
                  </span>
                  <input
                    type="checkbox"
                    checked={item.checked}
                    disabled={item.locked}
                    onChange={item.toggle}
                    style={{ width: 18, height: 18, cursor: item.locked ? "default" : "pointer" }}
                  />
                </div>
              ))}
            </div>

            <button
              type="button"
              id="btn-wizard-step5-continue"
              onClick={() => setStep(6)}
              style={{
                marginTop: 10,
                padding: "14px",
                backgroundColor: "#2563EB",
                color: "#FFFFFF",
                fontWeight: 800,
                fontSize: 15,
                borderRadius: 16,
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8
              }}
            >
              <span>{t("wizard.step5_continue", "Review & Give Explicit Consent")}</span>
              <ArrowRight size={18} />
            </button>
          </div>
        )}

        {/* STEP 6: EXPLICIT CONSENT & ATOMIC SUBMIT */}
        {step === 6 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <h2 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("wizard.step6_title", "6. Explicit Consent & Submit")}
            </h2>

            {/* Summary Review Card */}
            <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1px solid #E2E8F0", fontSize: 13 }}>
              <div style={{ fontWeight: 800, color: "#0F172A", marginBottom: 6 }}>{t("wizard.step6_summary_title", "Request Summary:")}</div>
              <div style={{ color: "#475569", lineHeight: 1.6 }}>
                • <b>{t("wizard.step6_field_patient", "Patient:")}</b> {selectedBeneficiary ? selectedBeneficiary.displayName.replace(/\s*\(.*?\)\s*/g, "") : ""} ({t(`beneficiary.relationship.${selectedBeneficiary?.relationship || "SELF"}`, selectedBeneficiary?.relationship || "Self")})<br />
                • <b>{t("wizard.step6_field_concern", "Primary Health Concern:")}</b> {chiefComplaint ? (chiefComplaint === "General health checkup / care guidance" ? t("concerns.GENERAL_HEALTH_GUIDANCE", chiefComplaint) : t(`concerns.${chiefComplaint.toUpperCase().replace(/[\s\/\-]+/g, "_")}`, chiefComplaint)) : extractedSymptoms.map(s => t(`symptoms.${s.toUpperCase().replace(/[\s\/\-]+/g, "_")}`, t(`concerns.${s.toUpperCase().replace(/[\s\/\-]+/g, "_")}`, s === "General health checkup / care guidance" ? t("concerns.GENERAL_HEALTH_GUIDANCE", s) : s))).join(", ")}<br />
                • <b>{t("wizard.step6_field_duration_severity", "Duration & Severity:")}</b> {t(`common.value.${durationText.toUpperCase().replace(/[\s-]+/g, "_")}`, durationText)} • {t(`common.value.${severityLevel}`, severityLevel)}<br />
                • <b>{t("wizard.step6_field_channel", "Consultation Channel:")}</b> {t(`consultation.channel.${selectedChannel}`, selectedChannel)}<br />
                • <b>{t("wizard.step6_field_location", "Care Location:")}</b> {villageName} {landmark ? `(${landmark})` : ""}<br />
                • <b>{t("wizard.step6_field_facility", "Designated Health Centre:")}</b> {t("facilities.kalyanpur_phc", "Kalyanpur Primary Health Centre (PHC-09)")}
              </div>
            </div>

            {/* Explicit Consent Checkbox (UNCHECKED BY DEFAULT) */}
            <div
              onClick={() => setExplicitConsent(!explicitConsent)}
              style={{
                padding: 14,
                borderRadius: 16,
                border: explicitConsent ? "2px solid #16A34A" : "2px solid #DC2626",
                backgroundColor: explicitConsent ? "#F0FDF4" : "#FEF2F2",
                display: "flex",
                alignItems: "flex-start",
                gap: 12,
                cursor: "pointer"
              }}
            >
              <input
                type="checkbox"
                id="checkbox-wizard-step6-consent"
                checked={explicitConsent}
                onChange={(e) => setExplicitConsent(e.target.checked)}
                style={{ width: 22, height: 22, marginTop: 2, cursor: "pointer" }}
              />
              <div style={{ fontSize: 13, fontWeight: 700, color: "#1E293B", lineHeight: 1.4 }}>
                {t("wizard.step6_consent_statement", "I explicitly consent to share the selected health concern and clinical details with the PHC Doctor for teleconsultation and medical care.")}
              </div>
            </div>

            <button
              type="button"
              id="btn-wizard-step6-submit"
              onClick={handleSubmitFinalRequest}
              disabled={submitting || !explicitConsent}
              style={{
                marginTop: 10,
                padding: "16px",
                backgroundColor: !explicitConsent ? "#94A3B8" : "#16A34A",
                color: "#FFFFFF",
                fontWeight: 800,
                fontSize: 16,
                borderRadius: 16,
                border: "none",
                cursor: !explicitConsent || submitting ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                boxShadow: !explicitConsent ? "none" : "0 4px 16px rgba(22, 163, 74, 0.3)"
              }}
            >
              {submitting ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  <span>{t("wizard.step6_submitting", "Submitting Request to Doctor...")}</span>
                </>
              ) : (
                <>
                  <span>{t("wizard.step6_submit_btn", "Submit Request & View Status")}</span>
                  <ArrowRight size={20} />
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
