import React, { useEffect, useState, useRef } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import {
  WarningIcon,
  CheckCircleIcon,
  VisitIcon,
  HospitalIcon,
  StethoscopeIcon,
  ActivityIcon,
  SearchIcon,
  ChevronRightIcon,
  ShieldCheckIcon
} from "../../components/Icons";
import { db } from "../../db/offlineDb";

export function AshaCitizenCaseScreen() {
  const { t } = useTranslation();
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const returnTo = searchParams.get("returnTo");
  const initialTab = searchParams.get("tab");

  const timelineRef = useRef<HTMLDivElement | null>(null);

  const [caseData, setCaseData] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAcknowledging, setIsAcknowledging] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [phoneRevealed, setPhoneRevealed] = useState(false);

  // Scheme evaluation state
  const [schemeResults, setSchemeResults] = useState<any[]>([]);
  const [evaluatingSchemes, setEvaluatingSchemes] = useState(false);

  // Contact Modal States
  const [showContactModal, setShowContactModal] = useState(false);
  const [contactOutcome, setContactOutcome] = useState<"SPOKE_TO_CITIZEN" | "CITIZEN_UNREACHABLE">("SPOKE_TO_CITIZEN");
  const [whoAnswered, setWhoAnswered] = useState("CITIZEN");
  const [conditionUpdate, setConditionUpdate] = useState("Headache slightly better after rest, but blurred vision persists.");
  const [visitRequired, setVisitRequired] = useState(true);
  const [preferredVisitTime, setPreferredVisitTime] = useState("Today Afternoon (2:00 PM - 4:00 PM)");
  const [contactNotes, setContactNotes] = useState("");
  const [unreachableReason, setUnreachableReason] = useState("NO_ANSWER");
  const [attemptNumber, setAttemptNumber] = useState(1);
  const [nextAttemptDate, setNextAttemptDate] = useState(new Date().toISOString().split("T")[0]);
  const [escalatePhc, setEscalatePhc] = useState(false);
  const [isSubmittingContact, setIsSubmittingContact] = useState(false);

  // Safety modal state
  const [showSafetyModal, setShowSafetyModal] = useState(false);

  // 1. Symptoms Modal State
  const [showSymptomsModal, setShowSymptomsModal] = useState(false);
  const [symptomInput, setSymptomInput] = useState("");
  const [symptomList, setSymptomList] = useState<string[]>([]);
  const [symptomSeverity, setSymptomSeverity] = useState("Moderate");
  const [symptomDuration, setSymptomDuration] = useState("2 days");
  const [symptomNotes, setSymptomNotes] = useState("");
  const [isSubmittingSymptoms, setIsSubmittingSymptoms] = useState(false);
  const [symptomError, setSymptomError] = useState<string | null>(null);

  // 2. Vitals Modal State
  const [showVitalsModal, setShowVitalsModal] = useState(false);
  const [systolic, setSystolic] = useState<number | "">("");
  const [diastolic, setDiastolic] = useState<number | "">("");
  const [spo2, setSpo2] = useState<number | "">("");
  const [pulse, setPulse] = useState<number | "">("");
  const [temp, setTemp] = useState<number | "">("");
  const [weight, setWeight] = useState<number | "">("");
  const [glucose, setGlucose] = useState<number | "">("");
  const [respRate, setRespRate] = useState<number | "">("");
  const [vitalNotes, setVitalNotes] = useState("");
  const [isSubmittingVitals, setIsSubmittingVitals] = useState(false);
  const [vitalsError, setVitalsError] = useState<string | null>(null);

  // 3. Trends Modal State
  const [showTrendsModal, setShowTrendsModal] = useState(false);
  const [trendsData, setTrendsData] = useState<any[]>([]);
  const [loadingTrends, setLoadingTrends] = useState(false);
  const [trendsError, setTrendsError] = useState<string | null>(null);
  const [trendsFilter, setTrendsFilter] = useState("ALL");

  // 4. Referral Modal State
  const [showReferralModal, setShowReferralModal] = useState(false);
  const [referralUrgency, setReferralUrgency] = useState("URGENT");
  const [referralReason, setReferralReason] = useState("");
  const [referralTransport, setReferralTransport] = useState(false);
  const [isSubmittingReferral, setIsSubmittingReferral] = useState(false);
  const [referralError, setReferralError] = useState<string | null>(null);

  // 5. Follow-up state
  const [isStartingFollowup, setIsStartingFollowup] = useState(false);

  const fetchCase = async () => {
    if (!caseId) return;
    try {
      const [rawRes, rawTRes] = await Promise.all([
        apiClient.getAshaCase(caseId),
        apiClient.getCaseTimeline(caseId).catch(() => []),
      ]);
      const res = rawRes?.data || rawRes;
      const tRes = Array.isArray(rawTRes?.data?.events) ? rawTRes.data.events : Array.isArray(rawTRes?.data) ? rawTRes.data : Array.isArray(rawTRes) ? rawTRes : [];
      setCaseData(res);
      setTimeline(tRes || []);

      // Cache in Dexie for offline
      await db.cachedCases.put({
        id: res.id,
        reference: res.reference,
        priority: res.priority,
        status: res.status,
        primary_concern: res.primary_concern,
        citizen_name: res.citizen_name,
        citizen_age: res.citizen_age,
        citizen_phone: res.citizen_phone,
        village_name: res.village_name,
        is_pregnant: res.is_pregnant,
        gestational_weeks: res.gestational_weeks,
        safety_rule_triggered: res.safety_rule_triggered,
        safety_rule_reason: res.safety_rule_reason,
        symptoms: res.symptoms || [],
        vitals: res.vitals || [],
        created_at: res.created_at,
      });

      // Trigger deterministic scheme evaluation
      loadSchemes(res);
    } catch (err) {
      console.error("Failed to load case online, trying offline...", err);
      const cached = await db.cachedCases.get(caseId);
      if (cached) {
        setCaseData(cached);
      }
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  const loadSchemes = async (currentCase: any) => {
    if (!currentCase) return;
    setEvaluatingSchemes(true);
    try {
      const payload = {
        citizen_id: currentCase.citizen_id || null,
        case_id: currentCase.id?.startsWith("citizen-") ? null : currentCase.id,
        additional_facts: {
          age: currentCase.citizen_age || 28,
          gender: currentCase.citizen_gender ? String(currentCase.citizen_gender).toUpperCase() : "FEMALE",
          sex: currentCase.citizen_gender ? String(currentCase.citizen_gender).toUpperCase() : "FEMALE",
          is_pregnant: Boolean(currentCase.is_pregnant),
          pregnancy: Boolean(currentCase.is_pregnant),
          gestational_weeks: currentCase.gestational_weeks || 14,
          state: "Maharashtra",
          resident_state: "Maharashtra",
          district: "District 04",
        },
        locale: "mr-IN",
        persist: false,
      };
      const res: any = await apiClient.evaluateSchemes(payload);
      if (res && res.results) {
        setSchemeResults(res.results);
      } else if (res && res.evaluations) {
        setSchemeResults(res.evaluations);
      }
    } catch (err) {
      console.error("Scheme evaluation error:", err);
    } finally {
      setEvaluatingSchemes(false);
    }
  };

  useEffect(() => {
    fetchCase();
    window.addEventListener("sync_completed", fetchCase);
    return () => {
      window.removeEventListener("sync_completed", fetchCase);
    };
  }, [caseId]);

  useEffect(() => {
    if (!loading && initialTab === "timeline" && timelineRef.current) {
      setTimeout(() => {
        timelineRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 150);
    }
  }, [loading, initialTab]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchCase();
  };

  const handleAcknowledge = async () => {
    if (!caseId) return;
    setIsAcknowledging(true);
    try {
      await apiClient.acknowledgeAshaCase(caseId);
      await fetchCase();
    } catch (err) {
      console.error("Failed to acknowledge case", err);
    } finally {
      setIsAcknowledging(false);
    }
  };

  const handleRevealAndCall = () => {
    setPhoneRevealed(true);
    if (caseData?.citizen_phone) {
      window.open(`tel:${caseData.citizen_phone}`, "_self");
    }
    setShowContactModal(true);
  };

  const handleSubmitContactResult = async () => {
    if (!caseId) return;
    setIsSubmittingContact(true);
    try {
      const payload =
        contactOutcome === "SPOKE_TO_CITIZEN"
          ? {
              outcome: "SPOKE_TO_CITIZEN",
              next_action: visitRequired ? "PLAN_VISIT" : "MONITOR",
              respondent_type: whoAnswered,
              current_condition_update: conditionUpdate,
              preferred_visit_time: preferredVisitTime,
              notes: contactNotes || "Spoke to citizen directly via phone. Confirmed symptoms and scheduled home visit.",
            }
          : {
              outcome: "CITIZEN_UNREACHABLE",
              next_action: escalatePhc ? "ESCALATE" : "RESCHEDULE",
              attempt_number: attemptNumber,
              reason_unreachable: unreachableReason,
              next_attempt_date: nextAttemptDate,
              escalate_to_phc: escalatePhc,
              notes: contactNotes || `Call attempt ${attemptNumber} unanswered. Reason: ${unreachableReason}.`,
            };

      await apiClient.request(`/asha/cases/${caseData.id}/contact-result`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setShowContactModal(false);
      await fetchCase();
    } catch (err) {
      console.error("Failed to save contact result", err);
    } finally {
      setIsSubmittingContact(false);
    }
  };

  // Symptoms Handlers
  const handleOpenSymptomsModal = () => {
    const existing = caseData?.symptoms?.map((s: any) => s.term || s.normalized_term) || [];
    setSymptomList(existing);
    setSymptomInput("");
    setSymptomError(null);
    setShowSymptomsModal(true);
  };

  const handleAddSymptomTag = () => {
    const trimmed = symptomInput.trim();
    if (!trimmed) return;
    if (symptomList.some((s) => s.toLowerCase() === trimmed.toLowerCase())) {
      setSymptomError("Symptom is already in the list.");
      return;
    }
    setSymptomList([...symptomList, trimmed]);
    setSymptomInput("");
    setSymptomError(null);
  };

  const handleRemoveSymptomTag = (index: number) => {
    setSymptomList(symptomList.filter((_, i) => i !== index));
  };

  const handleSaveSymptoms = async () => {
    if (symptomList.length === 0) {
      setSymptomError("Please add at least one symptom.");
      return;
    }
    setIsSubmittingSymptoms(true);
    setSymptomError(null);
    try {
      const activeFup = caseData.followups?.find((f: any) => f.status !== "COMPLETED");
      const res = await apiClient.addAshaCaseSymptoms(caseData.id, {
        symptoms: symptomList,
        onset_duration: symptomDuration,
        severity: symptomSeverity,
        notes: symptomNotes || `Field visit confirmed symptoms: ${symptomList.join(", ")}`,
        followup_id: activeFup?.id,
      });
      setShowSymptomsModal(false);
      await fetchCase();
    } catch (err: any) {
      setSymptomError(err.message || "Failed to save symptoms.");
    } finally {
      setIsSubmittingSymptoms(false);
    }
  };

  // Vitals Handlers
  const handleOpenVitalsModal = () => {
    setSystolic("");
    setDiastolic("");
    setSpo2("");
    setPulse("");
    setTemp("");
    setWeight("");
    setGlucose("");
    setRespRate("");
    setVitalNotes("");
    setVitalsError(null);
    setShowVitalsModal(true);
  };

  const handleSaveVitals = async () => {
    const hasAny = systolic !== "" || diastolic !== "" || spo2 !== "" || pulse !== "" || temp !== "" || weight !== "" || glucose !== "" || respRate !== "";
    if (!hasAny) {
      setVitalsError("At least one vital measurement must be provided.");
      return;
    }
    if ((systolic !== "" && diastolic === "") || (diastolic !== "" && systolic === "")) {
      setVitalsError("Both systolic and diastolic blood pressure are required when recording blood pressure.");
      return;
    }
    if (systolic !== "" && (Number(systolic) < 50 || Number(systolic) > 300)) {
      setVitalsError("Systolic BP must be between 50 and 300 mmHg.");
      return;
    }
    if (diastolic !== "" && (Number(diastolic) < 30 || Number(diastolic) > 200)) {
      setVitalsError("Diastolic BP must be between 30 and 200 mmHg.");
      return;
    }
    if (spo2 !== "" && (Number(spo2) < 50 || Number(spo2) > 100)) {
      setVitalsError("SpO2 must be between 50% and 100%.");
      return;
    }
    if (pulse !== "" && (Number(pulse) < 30 || Number(pulse) > 250)) {
      setVitalsError("Pulse must be between 30 and 250 bpm.");
      return;
    }
    if (temp !== "" && (Number(temp) < 30 || Number(temp) > 45)) {
      setVitalsError("Temperature must be between 30.0°C and 45.0°C.");
      return;
    }
    if (weight !== "" && (Number(weight) < 1 || Number(weight) > 300)) {
      setVitalsError("Weight must be between 1.0 and 300.0 kg.");
      return;
    }
    if (glucose !== "" && (Number(glucose) < 20 || Number(glucose) > 1000)) {
      setVitalsError("Blood glucose must be between 20 and 1000 mg/dL.");
      return;
    }

    setIsSubmittingVitals(true);
    setVitalsError(null);
    try {
      const activeFup = caseData.followups?.find((f: any) => f.status !== "COMPLETED");
      const payload: any = {};
      if (systolic !== "") payload.systolic_bp = Number(systolic);
      if (diastolic !== "") payload.diastolic_bp = Number(diastolic);
      if (spo2 !== "") payload.spo2 = Number(spo2);
      if (pulse !== "") payload.pulse = Number(pulse);
      if (temp !== "") payload.temperature_c = Number(temp);
      if (weight !== "") payload.weight_kg = Number(weight);
      if (glucose !== "") payload.glucose_mg_dl = Number(glucose);
      if (respRate !== "") payload.respiratory_rate = Number(respRate);
      if (vitalNotes) payload.notes = vitalNotes;
      if (activeFup?.id) payload.followup_id = activeFup.id;

      await apiClient.recordAshaCaseVitals(caseData.id, payload);
      setShowVitalsModal(false);
      await fetchCase();
    } catch (err: any) {
      setVitalsError(err.message || "Failed to record vitals.");
    } finally {
      setIsSubmittingVitals(false);
    }
  };

  // Trends Handlers
  const handleOpenTrendsModal = async () => {
    setShowTrendsModal(true);
    setLoadingTrends(true);
    setTrendsError(null);
    try {
      const res = await apiClient.getAshaCaseVitalsTrends(caseData.id);
      const data = res?.data || res;
      setTrendsData(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setTrendsError(err.message || "Failed to load vitals trends.");
    } finally {
      setLoadingTrends(false);
    }
  };

  // Referral Handlers
  const [referralSuccessBanner, setReferralSuccessBanner] = useState<{ reference: string; facilityName: string } | null>(null);

  const handleOpenReferralModal = () => {
    setReferralUrgency(caseData.priority === "URGENT" ? "URGENT" : "ROUTINE");
    setReferralReason(caseData.safety_rule_reason || caseData.primary_concern || "Clinical evaluation recommended at PHC.");
    setReferralTransport(false);
    setReferralError(null);
    setShowReferralModal(true);
  };

  const handleSaveReferral = async () => {
    if (!referralReason.trim()) {
      setReferralError("Please provide a clinical reason for referral.");
      return;
    }
    setIsSubmittingReferral(true);
    setReferralError(null);
    const targetFacilityId = caseData.assigned_facility_id || caseData.facility_id || "PHC-09";
    const idempotencyKey = `ref-${caseData.id}-${Date.now()}`;
    try {
      const resp = await apiClient.referAshaCase(
        caseData.id,
        {
          facility_id: targetFacilityId,
          urgency: referralUrgency,
          reason: referralReason.trim(),
          transport_required: referralTransport,
        },
        idempotencyKey
      );
      const refData = resp?.data || resp;
      setShowReferralModal(false);
      setReferralSuccessBanner({
        reference: refData?.referral_reference || refData?.reference || "REF-CREATED",
        facilityName: refData?.facility_name || caseData.assigned_facility_name || "Kalyanpur Primary Health Center",
      });
      await fetchCase();
    } catch (err: any) {
      setReferralError(err.message || "Failed to submit referral. Please retry.");
    } finally {
      setIsSubmittingReferral(false);
    }
  };

  // Start Followup Handler
  const handleStartFollowup = async (fupId: string) => {
    setIsStartingFollowup(true);
    try {
      await apiClient.startAshaFollowup(fupId);
      await fetchCase();
    } catch (err) {
      console.error("Failed to start follow-up", err);
    } finally {
      setIsStartingFollowup(false);
    }
  };

  if (loading || !caseData) {
    return (
      <div style={{ padding: "60px 0", textAlign: "center", color: "var(--text-secondary)" }}>
        <div style={{ fontSize: 16, fontWeight: 600 }}>Loading patient case review...</div>
      </div>
    );
  }

  const isMale = caseData.citizen_gender && ["male", "m"].includes(String(caseData.citizen_gender).trim().toLowerCase());
  const isPregnant = !isMale && Boolean(caseData.is_pregnant);

  const maskPhone = (phone: string) => {
    if (!phone) return "9876543210";
    if (phoneRevealed) return phone;
    return phone.length >= 10 ? `******${phone.slice(-4)}` : phone;
  };

  const maskAbha = (abha: string) => {
    if (!abha) return "12-3456-7890-1234";
    return abha.length >= 14 ? `${abha.slice(0, 4)}-****-****-${abha.slice(-4)}` : abha;
  };

  const activeFollowup = caseData.followups?.find((f: any) => f.status !== "COMPLETED") || caseData.followups?.[0];

  const renderPrimaryAction = () => {
    const status = caseData.status;
    if (status === "NEW") {
      return (
        <button
          onClick={handleAcknowledge}
          disabled={isAcknowledging}
          style={{
            padding: "10px 18px",
            backgroundColor: "var(--primary)",
            color: "#FFF",
            borderRadius: 8,
            border: "none",
            fontSize: 13,
            fontWeight: 700,
            cursor: "pointer",
            minHeight: 42,
          }}
        >
          {isAcknowledging ? "Acknowledging..." : "✓ Acknowledge Case"}
        </button>
      );
    }
    if (status === "ASHA_ACKNOWLEDGED") {
      return (
        <button
          onClick={handleRevealAndCall}
          style={{
            padding: "10px 18px",
            backgroundColor: "var(--primary)",
            color: "#FFF",
            borderRadius: 8,
            border: "none",
            fontSize: 13,
            fontWeight: 700,
            cursor: "pointer",
            minHeight: 42,
          }}
        >
          📞 Contact Citizen
        </button>
      );
    }
    if (status === "CITIZEN_CONTACTED" || status === "ASHA_REVIEWED") {
      return (
        <button
          onClick={handleOpenSymptomsModal}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "10px 18px",
            backgroundColor: "var(--teal)",
            color: "#FFF",
            borderRadius: 8,
            border: "none",
            fontSize: 13,
            fontWeight: 700,
            cursor: "pointer",
            minHeight: 42,
          }}
        >
          <VisitIcon size={16} color="#FFF" />
          <span>Conduct Field Visit</span>
        </button>
      );
    }
    if (status === "REFERRED_TO_PHC") {
      return (
        <button
          onClick={() => {
            const el = document.getElementById("care-coordination-section");
            if (el) el.scrollIntoView({ behavior: "smooth" });
          }}
          style={{
            padding: "10px 18px",
            backgroundColor: "var(--primary-light)",
            color: "var(--primary-dark)",
            borderRadius: 8,
            border: "1px solid var(--primary)",
            fontSize: 13,
            fontWeight: 700,
            cursor: "pointer",
            minHeight: 42,
          }}
        >
          🏥 View Referral Status
        </button>
      );
    }
    if (status === "DOCTOR_ACKNOWLEDGED") {
      return (
        <button
          onClick={() => {
            const el = document.getElementById("care-coordination-section");
            if (el) el.scrollIntoView({ behavior: "smooth" });
          }}
          style={{
            padding: "10px 18px",
            backgroundColor: "#E8F5E9",
            color: "#2E7D32",
            borderRadius: 8,
            border: "1px solid #A5D6A7",
            fontSize: 13,
            fontWeight: 700,
            cursor: "pointer",
            minHeight: 42,
          }}
        >
          👩‍⚕️ View Doctor Response
        </button>
      );
    }
    if (status === "FOLLOW_UP_REQUIRED") {
      const activeFollowup = caseData.active_followup || (caseData.follow_ups && caseData.follow_ups.length > 0 ? caseData.follow_ups[0] : null);
      if (activeFollowup && activeFollowup.status === "IN_PROGRESS") {
        return (
          <button
            onClick={() => navigate(`/asha/followups/${activeFollowup.id}`)}
            style={{
              padding: "10px 18px",
              backgroundColor: "#E0F2F1",
              color: "var(--teal)",
              borderRadius: 8,
              border: "1px solid var(--teal)",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              minHeight: 42,
            }}
          >
            📋 Continue Follow-up Visit →
          </button>
        );
      }
      return (
        <button
          onClick={() => {
            if (activeFollowup && activeFollowup.id) {
              handleStartFollowup(activeFollowup.id);
            } else {
              navigate(`/asha/followups?citizenId=${caseData.citizen_id}`);
            }
          }}
          disabled={isStartingFollowup}
          style={{
            padding: "10px 18px",
            backgroundColor: "var(--primary)",
            color: "#FFF",
            borderRadius: 8,
            border: "none",
            fontSize: 13,
            fontWeight: 700,
            cursor: isStartingFollowup ? "wait" : "pointer",
            minHeight: 42,
            opacity: isStartingFollowup ? 0.7 : 1,
          }}
        >
          {isStartingFollowup ? "⏳ Starting..." : "🔄 Start Follow-up"}
        </button>
      );
    }
    if (status === "NO_ACTIVE_CASE") {
      return (
        <button
          onClick={() => navigate(`/asha/add-patient`)}
          style={{
            padding: "10px 18px",
            backgroundColor: "var(--primary)",
            color: "#FFF",
            borderRadius: 8,
            border: "none",
            fontSize: 13,
            fontWeight: 700,
            cursor: "pointer",
            minHeight: 42,
          }}
        >
          + Record Health Concern
        </button>
      );
    }
    return (
      <button
        onClick={() => navigate("/asha/people")}
        style={{
          padding: "10px 18px",
          backgroundColor: "var(--surface)",
          color: "var(--text-primary)",
          borderRadius: 8,
          border: "1px solid var(--border)",
          fontSize: 13,
          fontWeight: 700,
          cursor: "pointer",
          minHeight: 42,
        }}
      >
        View People Directory
      </button>
    );
  };

  const getNextTaskDetails = () => {
    const status = caseData.status;
    if (status === "NO_ACTIVE_CASE") {
      return {
        task: "Citizen Profile Active · Ready for Routine Services",
        category: "Community Monitoring",
        due: "Routine",
        source: "Beneficiary Directory",
        worker: "Sita Patel (ASHA Worker)"
      };
    }
    if (status === "CITIZEN_CONTACTED") {
      return {
        task: "Conduct In-Person Field Visit & Triage",
        category: "Field Visit Scheduled",
        due: "Today (Afternoon 2:00 PM - 4:00 PM)",
        source: "Citizen Phone Triage",
        worker: "Sita Patel (ASHA Worker)"
      };
    }
    if (status === "REFERRED_TO_PHC") {
      return {
        task: "Awaiting PHC Medical Officer Review",
        category: "Clinical Escalation",
        due: "Within 24 Hours",
        source: "ASHA Field Referral",
        worker: "PHC Medical Officer"
      };
    }
    if (status === "NEW") {
      return {
        task: "Acknowledge New Incident Report",
        category: "Urgent Triage",
        due: "Immediate",
        source: "Citizen Mobile Voice Intake",
        worker: "Assigned ASHA Worker"
      };
    }
    return {
      task: "Active Case Management",
      category: "Longitudinal Follow-up",
      due: "Within 48 Hours",
      source: "Clinical Protocol",
      worker: "Sita Patel (ASHA Worker)"
    };
  };

  const nextTask = getNextTaskDetails();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 1280, margin: "0 auto" }}>
      
      {/* 1. Header with Breadcrumbs and Synchronized Status */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, borderBottom: "1px solid var(--border)", paddingBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-secondary)" }}>
          <button
            id="breadcrumb-back-btn"
            onClick={() => {
              if (returnTo) {
                navigate(returnTo);
              } else {
                navigate("/asha/tasks");
              }
            }}
            style={{
              border: "none",
              backgroundColor: "transparent",
              color: "var(--primary)",
              fontWeight: 600,
              cursor: "pointer",
              padding: 0,
            }}
          >
            {returnTo?.includes("followups") ? "← Back to Follow-ups" : "Tasks"}
          </button>
          <span>/</span>
          <span>{caseData.reference}</span>
          <span>/</span>
          <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>{caseData.citizen_name}</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-secondary)" }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "#4CAF50" }} />
            <span>Last synced: Just now</span>
          </div>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            style={{
              padding: "6px 14px",
              borderRadius: 6,
              border: "1px solid var(--border)",
              backgroundColor: "var(--surface)",
              color: "var(--text-primary)",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isRefreshing ? "Refreshing..." : "↻ Refresh"}
          </button>
        </div>
      </div>

      {referralSuccessBanner && (
        <div
          id="referral-success-banner"
          style={{
            backgroundColor: "#E8F5E9",
            border: "1px solid #A5D6A7",
            borderRadius: 10,
            padding: "14px 20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 20 }}>✅</span>
            <div>
              <strong style={{ color: "#2E7D32", fontSize: 14 }}>PHC Referral Submitted Successfully</strong>
              <div style={{ color: "#1B5E20", fontSize: 13, marginTop: 2 }}>
                Referral Reference: <strong>{referralSuccessBanner.reference}</strong> · Sent to <strong>{referralSuccessBanner.facilityName}</strong>. Case status updated to <strong>REFERRED_TO_PHC</strong> (Doctor Review Pending).
              </div>
            </div>
          </div>
          <button
            onClick={() => setReferralSuccessBanner(null)}
            style={{
              border: "none",
              backgroundColor: "transparent",
              color: "#2E7D32",
              fontWeight: 700,
              cursor: "pointer",
              fontSize: 16,
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* 2. Patient Header Card */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          padding: "20px 24px",
          borderRadius: 12,
          border: "1px solid var(--border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 6 }}>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: "var(--text-primary)" }}>
              {caseData.citizen_name}
            </h1>
            <PriorityBadge priority={caseData.priority} />
            <StatusBadge status={caseData.status} />
            {isPregnant && (
              <span style={{ padding: "3px 10px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 12, fontWeight: 700 }}>
                Pregnant ({caseData.gestational_weeks ? `${caseData.gestational_weeks}w` : "Trimester 2"})
              </span>
            )}
          </div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", display: "flex", gap: 12, flexWrap: "wrap" }}>
            <span>Ref: <strong>{caseData.reference}</strong></span>
            <span>·</span>
            <span>Village: {caseData.village_name || "Kalyanpur"}</span>
            <span>·</span>
            <span>Age: {caseData.citizen_age || 31}y ({caseData.citizen_gender || (isMale ? "Male" : "Female")})</span>
            <span>·</span>
            <span>Language: Marathi (mr-IN)</span>
            <span>·</span>
            <span>Phone: {maskPhone(caseData.citizen_phone)}</span>
          </div>
        </div>

        {/* Action Buttons in Header */}
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          {renderPrimaryAction()}
          <button
            onClick={handleRevealAndCall}
            style={{
              padding: "10px 16px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              backgroundColor: "var(--surface)",
              color: "var(--text-primary)",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              minHeight: 42,
            }}
          >
            📞 Call Citizen
          </button>
          <button
            onClick={() => navigate("/asha/followups")}
            style={{
              padding: "10px 14px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              backgroundColor: "var(--surface)",
              color: "var(--text-secondary)",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              minHeight: 42,
            }}
          >
            More Actions ▾
          </button>
        </div>
      </div>

      {/* 3. Next Action Banner Card */}
      <div
        style={{
          backgroundColor: "#E8F0FE",
          border: "1px solid #D2E3FC",
          borderRadius: 10,
          padding: "14px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: "50%", backgroundColor: "var(--primary)", color: "#FFF", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700 }}>
            ➔
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--primary-dark)", textTransform: "uppercase" }}>
              Next Action: {nextTask.category}
            </div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginTop: 2 }}>
              {nextTask.task}
            </div>
          </div>
        </div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)", textAlign: "right" }}>
          <div>Due: <strong>{nextTask.due}</strong> · Source: {nextTask.source}</div>
          <div style={{ marginTop: 2 }}>Assigned: {nextTask.worker}</div>
        </div>
      </div>

      {/* 4. Deterministic Non-Diagnostic Safety Alert Banner */}
      {caseData.safety_rule_triggered && (
        <div
          style={{
            backgroundColor: "var(--urgent-bg)",
            border: "1px solid #F5C6CB",
            borderRadius: 10,
            padding: "16px 20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
            <WarningIcon size={22} color="var(--urgent)" />
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "var(--urgent)" }}>
                Warning signs detected. Urgent professional evaluation is recommended.
              </div>
              <div style={{ fontSize: 13, color: "var(--text-primary)", marginTop: 4, lineHeight: "20px" }}>
                {caseData.safety_rule_reason || "Elevated blood pressure observed during clinical evaluation."}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
                Matched Rule: Deterministic Clinical Safety Protocol (Rule Engine v2026.1)
              </div>
            </div>
          </div>
          <button
            onClick={() => setShowSafetyModal(true)}
            style={{
              padding: "6px 12px",
              borderRadius: 6,
              border: "1px solid #F5C6CB",
              backgroundColor: "var(--surface)",
              color: "var(--urgent)",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            View Safety Details
          </button>
        </div>
      )}

      {/* 5. Main 2-Column Responsive Layout */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 20 }}>
        
        {/* Left Column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          
          {/* A. Citizen & Contact */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                👤 Citizen & Contact
              </h3>
              <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>ABDM Linked</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13, marginBottom: 14 }}>
              <div>
                <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Phone Number</span>
                <strong>{maskPhone(caseData.citizen_phone)}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Preferred Language</span>
                <strong>Marathi (mr-IN)</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>ABHA ID</span>
                <strong>{maskAbha(caseData.abha)}</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Village / Ward</span>
                <strong>{caseData.village_name || "Kalyanpur"}</strong>
              </div>
            </div>

            <div style={{ padding: "8px 12px", backgroundColor: "var(--neutral-bg)", borderRadius: 6, fontSize: 12, color: "var(--text-secondary)", marginBottom: 14 }}>
              📍 Landmark: Near Gram Panchayat, House #18 · Last contact: Today 10:30 AM
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={handleRevealAndCall}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                  backgroundColor: "var(--surface)",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                📞 Reveal & Call
              </button>
              <button
                onClick={() => setShowContactModal(true)}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                  backgroundColor: "var(--surface)",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                📅 Schedule Visit
              </button>
            </div>
          </div>

          {/* B. Current Concern */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
              🗣 Citizen Health Status & Concern
            </h3>
            
            {caseData.status === "NO_ACTIVE_CASE" ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div
                  style={{
                    padding: "14px 16px",
                    backgroundColor: "var(--neutral-bg)",
                    borderRadius: 8,
                    fontSize: 14,
                    fontWeight: 600,
                    color: "var(--text-secondary)",
                    display: "flex",
                    alignItems: "center",
                    gap: 10
                  }}
                >
                  <span>ℹ️</span>
                  <span>No active health concern registered for this citizen.</span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <button
                    onClick={() => navigate("/asha/add-patient")}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 6,
                      border: "none",
                      backgroundColor: "var(--primary)",
                      color: "#FFF",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer"
                    }}
                  >
                    + Record Health Concern
                  </button>
                  <button
                    onClick={() => navigate(`/asha/followups?citizenId=${caseData.citizen_id}`)}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 6,
                      border: "1px solid var(--primary)",
                      backgroundColor: "var(--primary-light)",
                      color: "var(--primary-dark)",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer"
                    }}
                  >
                    📅 Schedule Routine Visit
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div
                  style={{
                    padding: "12px 14px",
                    backgroundColor: "var(--neutral-bg)",
                    borderRadius: 8,
                    fontSize: 13,
                    fontStyle: "italic",
                    color: "var(--text-primary)",
                    lineHeight: "20px",
                    marginBottom: 14,
                  }}
                >
                  "{caseData.primary_concern || "Routine health check-up"}"
                </div>

                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 6 }}>
                  ASHA-Confirmed Symptoms:
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
                  {caseData.symptoms && caseData.symptoms.length > 0 ? (
                    caseData.symptoms.map((s: any, idx: number) => (
                      <span
                        key={idx}
                        style={{
                          padding: "4px 10px",
                          borderRadius: 6,
                          backgroundColor: "var(--primary-light)",
                          color: "var(--primary-dark)",
                          fontSize: 12,
                          fontWeight: 600,
                        }}
                      >
                        ✓ {s.term || s.normalized_term}
                      </span>
                    ))
                  ) : (
                    <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                      None recorded yet (Pending in-person confirmation during field visit).
                    </span>
                  )}
                </div>

                <button
                  id="confirm-add-symptoms-btn"
                  onClick={handleOpenSymptomsModal}
                  style={{
                    width: "100%",
                    padding: "8px",
                    borderRadius: 6,
                    border: "1px dashed var(--border)",
                    backgroundColor: "transparent",
                    color: "var(--primary)",
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  + Confirm & Add Symptoms in Field Visit
                </button>
              </>
            )}
          </div>

          {/* C. Dynamic Patient Context Card */}
          {isPregnant ? (
            <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
              <h3 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                🤰 Dynamic Context: Antenatal Maternal Tracking
              </h3>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13 }}>
                <div>
                  <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Gestational Age</span>
                  <strong>{caseData.gestational_weeks} Weeks (Trimester {caseData.gestational_weeks <= 12 ? "1" : caseData.gestational_weeks <= 26 ? "2" : "3"})</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Estimated Due Date (EDD)</span>
                  <strong>{caseData.dynamic_context?.edd || "Calculated at PHC"}</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>ANC Registration</span>
                  <strong style={{ color: "#2E7D32" }}>✓ Registered ({caseData.dynamic_context?.anc_stage || "ANC-1"})</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Scheduled ANC Phase</span>
                  <strong>{caseData.dynamic_context?.anc_stage || "Next Routine ANC"}</strong>
                </div>
              </div>
            </div>
          ) : caseData.dynamic_context?.type === "NCD_MONITORING" || /hypertension|bp|blood pressure|diabetes|sugar|heart/i.test(caseData.primary_concern || "") ? (
            <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
              <h3 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                🫀 Dynamic Context: NCD & Chronic Care Monitoring
              </h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13 }}>
                <div>
                  <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Protocol Track</span>
                  <strong>Hypertension & Cardiovascular Triage</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Frequency</span>
                  <strong>Bi-weekly Field BP Monitoring</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Medication Status</span>
                  <strong>Adherence Review Active</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Care Facility</span>
                  <strong>Kalyanpur PHC</strong>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
              <h3 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                📋 Dynamic Context: General Longitudinal Care
              </h3>
              <div style={{ padding: "12px 14px", backgroundColor: "var(--neutral-bg)", borderRadius: 8, fontSize: 13, color: "var(--text-secondary)" }}>
                No additional program-specific context recorded.
              </div>
            </div>
          )}

          {/* D. Scheme Support */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                🏛 Government Health Schemes (3-Valued Engine)
              </h3>
              <button
                onClick={() => loadSchemes(caseData)}
                disabled={evaluatingSchemes}
                style={{
                  border: "none",
                  backgroundColor: "transparent",
                  color: "var(--primary)",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {evaluatingSchemes ? "Evaluating..." : "↻ Re-Evaluate"}
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {schemeResults && schemeResults.length > 0 ? (
                schemeResults.slice(0, 4).map((s: any) => {
                  const isEligible = ["LIKELY_ELIGIBLE", "SERVICE_AVAILABLE", "OFFICIAL_VERIFICATION_REQUIRED", "POTENTIALLY_ELIGIBLE"].includes(s.status);
                  const isMoreInfo = s.status === "MORE_INFORMATION_REQUIRED";
                  const badgeColor = isEligible ? { bg: "#E8F5E9", text: "#2E7D32" } : isMoreInfo ? { bg: "#FFF3E0", text: "#E65100" } : { bg: "#FFEBEE", text: "#C62828" };
                  const statusLabel = s.status === "SERVICE_AVAILABLE" ? "SERVICE" : s.status === "LIKELY_ELIGIBLE" ? "ELIGIBLE" : s.status === "OFFICIAL_VERIFICATION_REQUIRED" ? "VERIFICATION GATE" : isMoreInfo ? "MORE INFO REQ." : "NOT ELIGIBLE";

                  return (
                    <div
                      key={s.scheme_code}
                      style={{
                        padding: "10px 12px",
                        borderRadius: 8,
                        backgroundColor: "var(--neutral-bg)",
                        border: "1px solid var(--border)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center"
                      }}
                    >
                      <div style={{ flex: 1, paddingRight: 8 }}>
                        <div style={{ fontSize: 13, fontWeight: 700 }}>{s.canonical_name || s.short_name || s.scheme_code}</div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{s.explanation || s.description}</div>
                      </div>
                      <span style={{ padding: "3px 8px", borderRadius: 6, backgroundColor: badgeColor.bg, color: badgeColor.text, fontSize: 11, fontWeight: 700, whiteSpace: "nowrap" }}>
                        {statusLabel}
                      </span>
                    </div>
                  );
                })
              ) : evaluatingSchemes ? (
                <div style={{ padding: 12, textAlign: "center", fontSize: 12, color: "var(--text-secondary)" }}>
                  Evaluating schemes against criteria...
                </div>
              ) : (
                <div style={{ padding: 12, textAlign: "center", fontSize: 12, color: "var(--text-secondary)" }}>
                  Click Re-Evaluate to screen patient for government health schemes.
                </div>
              )}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", fontStyle: "italic" }}>
                Official verification required before final sanction.
              </div>
              <button
                onClick={() => navigate(`/asha/schemes?citizenId=${caseData.citizen_id}`)}
                style={{
                  border: "none",
                  backgroundColor: "transparent",
                  color: "var(--primary)",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer"
                }}
              >
                View All {schemeResults.length || 29} Schemes →
              </button>
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          
          {/* E. Latest Measurements */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                🩺 Latest Vital Signs & Measurements
              </h3>
              <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                {caseData.vitals && caseData.vitals.length > 0 ? "Verified" : "Pending Entry"}
              </span>
            </div>

            {caseData.vitals && caseData.vitals.length > 0 ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
                <div style={{ padding: 10, backgroundColor: caseData.vitals[0].is_warning_sign ? "var(--urgent-bg)" : "var(--neutral-bg)", borderRadius: 8, border: caseData.vitals[0].is_warning_sign ? "1px solid #F5C6CB" : "1px solid var(--border)" }}>
                  <div style={{ fontSize: 11, color: caseData.vitals[0].is_warning_sign ? "var(--urgent)" : "var(--text-secondary)", fontWeight: 700 }}>Blood Pressure (BP)</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: caseData.vitals[0].is_warning_sign ? "var(--urgent)" : "var(--text-primary)", marginTop: 2 }}>
                    {caseData.vitals[0].systolic_bp && caseData.vitals[0].diastolic_bp ? `${caseData.vitals[0].systolic_bp}/${caseData.vitals[0].diastolic_bp}` : "Not recorded"}
                    {caseData.vitals[0].systolic_bp && <span style={{ fontSize: 11, fontWeight: 500, marginLeft: 4 }}>mmHg</span>}
                  </div>
                </div>

                <div style={{ padding: 10, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 600 }}>SpO₂ Level</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                    {caseData.vitals[0].spo2 ? `${caseData.vitals[0].spo2}%` : "Not recorded"}
                  </div>
                </div>

                <div style={{ padding: 10, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 600 }}>Pulse Rate</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                    {caseData.vitals[0].pulse ? `${caseData.vitals[0].pulse} bpm` : "Not recorded"}
                  </div>
                </div>

                <div style={{ padding: 10, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 600 }}>Temperature / Weight</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                    {caseData.vitals[0].temperature_c ? `${caseData.vitals[0].temperature_c}°C` : "Not recorded"} · {caseData.vitals[0].weight_kg ? `${caseData.vitals[0].weight_kg} kg` : "Not recorded"}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ padding: 14, backgroundColor: "var(--neutral-bg)", borderRadius: 8, fontSize: 13, color: "var(--text-secondary)", marginBottom: 14 }}>
                No vitals recorded yet. Record vitals during field visit.
              </div>
            )}

            {caseData.vitals && caseData.vitals.length > 0 && (
              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 12, fontStyle: "italic" }}>
                Recorded by {caseData.vitals[0].recorded_by || "ASHA"} · Source: {caseData.vitals[0].source_type || "Field Entry"}
              </div>
            )}

            <div style={{ display: "flex", gap: 8 }}>
              <button
                id="view-trends-btn"
                onClick={handleOpenTrendsModal}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                  backgroundColor: "var(--surface)",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                📊 View Trends
              </button>
              <button
                id="record-vitals-btn"
                onClick={handleOpenVitalsModal}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "none",
                  backgroundColor: "var(--teal)",
                  color: "#FFF",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                + Record Vitals
              </button>
            </div>
          </div>

          {/* F. Care Coordination */}
          <div id="care-coordination-section" style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
              🏥 Care Coordination & Escalation
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 13, marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>Field Visit Status</span>
                <strong>{caseData.field_visit_status || (caseData.status === "CITIZEN_CONTACTED" ? "Scheduled (Today)" : "Not Started")}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>PHC Referral</span>
                <strong>{caseData.phc_referral_status || (caseData.status === "REFERRED_TO_PHC" ? "Referred (PHC-09 Kalyanpur)" : "Not Created")}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>Doctor Review Status</span>
                <strong>{caseData.doctor_review_status || "Not Required"}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>Follow-up Task</span>
                <strong>{caseData.followup_status || "Not Assigned"}</strong>
              </div>
            </div>

            {caseData.status !== "REFERRED_TO_PHC" && (!caseData.referrals || caseData.referrals.length === 0) ? (
              <button
                id="prepare-referral-btn"
                onClick={handleOpenReferralModal}
                style={{
                  width: "100%",
                  padding: "10px",
                  borderRadius: 6,
                  border: "none",
                  backgroundColor: "var(--urgent)",
                  color: "#FFF",
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                🏥 Prepare Referral to {caseData.assigned_facility_name || caseData.facility_name || "Kalyanpur Primary Health Center"}
              </button>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ padding: "10px", backgroundColor: "#E8F5E9", color: "#2E7D32", borderRadius: 6, fontSize: 12, fontWeight: 700, textAlign: "center" }}>
                  ✓ Referral active at {caseData.assigned_facility_name || caseData.facility_name || "Kalyanpur Primary Health Center"}. Doctor review pending.
                </div>
                {caseData.referrals && caseData.referrals.length > 0 && (
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", textAlign: "center" }}>
                    Ref: <strong>{caseData.referrals[0].reference || caseData.referrals[0].id}</strong> · Status: <strong>{caseData.referrals[0].status}</strong>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* G. Active Follow-up */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                🔄 Active Follow-up Tasks
              </h3>
              <button
                onClick={() => navigate(`/asha/followups?citizenId=${caseData.citizen_id}`)}
                style={{
                  border: "none",
                  backgroundColor: "transparent",
                  color: "var(--primary)",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                View All
              </button>
            </div>

            {activeFollowup ? (
              <>
                <div style={{ padding: "12px 14px", backgroundColor: "var(--neutral-bg)", borderRadius: 8, border: "1px solid var(--border)", marginBottom: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 13, fontWeight: 700 }}>{activeFollowup.instructions || "Active Health Monitoring Follow-up"}</span>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        padding: "2px 6px",
                        borderRadius: 4,
                        backgroundColor: activeFollowup.status === "IN_PROGRESS" ? "#E3F2FD" : "var(--urgent-bg)",
                        color: activeFollowup.status === "IN_PROGRESS" ? "#1976D2" : "var(--urgent)",
                      }}
                    >
                      {activeFollowup.status}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                    {activeFollowup.due_at ? `Due by ${new Date(activeFollowup.due_at).toLocaleDateString()}` : "Due in 2 days"} · Assigned to Sita Patel (ASHA)
                  </div>
                </div>

                {activeFollowup.status === "IN_PROGRESS" ? (
                  <button
                    onClick={() => navigate(`/asha/followups/${activeFollowup.id}`)}
                    style={{
                      width: "100%",
                      padding: "8px",
                      borderRadius: 6,
                      border: "1px solid var(--teal)",
                      backgroundColor: "#E0F2F1",
                      color: "var(--teal)",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Continue Follow-up Visit →
                  </button>
                ) : (
                  <button
                    id="start-followup-btn"
                    onClick={() => handleStartFollowup(activeFollowup.id)}
                    disabled={isStartingFollowup}
                    style={{
                      width: "100%",
                      padding: "8px",
                      borderRadius: 6,
                      border: "1px solid var(--primary)",
                      backgroundColor: "var(--primary-light)",
                      color: "var(--primary-dark)",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    {isStartingFollowup ? "Starting..." : "Start Follow-up Task"}
                  </button>
                )}
              </>
            ) : (
              <div style={{ padding: "12px 14px", backgroundColor: "var(--neutral-bg)", borderRadius: 8, fontSize: 13, color: "var(--text-secondary)" }}>
                No pending follow-up task. Follow-up instructions will appear after PHC review.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 6. Bottom Case Timeline */}
      <div
        id="case-timeline-section"
        ref={timelineRef}
        style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)", marginTop: 10 }}
      >
        <h3 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
          🕒 Deduplicated Longitudinal Case Timeline
        </h3>

        {timeline.length === 0 ? (
          <div style={{ color: "var(--text-secondary)", fontSize: 13 }}>Compiling timeline events...</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 14, position: "relative", paddingLeft: 20 }}>
            <div style={{ position: "absolute", left: 7, top: 6, bottom: 6, width: 2, backgroundColor: "var(--border)" }} />
            {timeline.map((evt, idx) => (
              <div key={evt.id || idx} style={{ position: "relative", display: "flex", flexDirection: "column", gap: 2 }}>
                <div
                  style={{
                    position: "absolute",
                    left: -19,
                    top: 4,
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    backgroundColor:
                      evt.badge_type === "danger"
                        ? "var(--urgent)"
                        : evt.badge_type === "success"
                        ? "var(--success)"
                        : "var(--primary)",
                    border: "2px solid var(--surface)",
                  }}
                />
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{evt.title}</span>
                  <span
                    style={{
                      padding: "1px 6px",
                      borderRadius: 4,
                      fontSize: 10,
                      fontWeight: 700,
                      backgroundColor: "var(--primary-light)",
                      color: "var(--primary-dark)",
                    }}
                  >
                    {evt.actor_role}
                  </span>
                  <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                    {evt.timestamp ? new Date(evt.timestamp).toLocaleString() : ""}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  {evt.description}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Symptoms Confirmation Modal */}
      {showSymptomsModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 300,
            padding: 16,
          }}
          onClick={() => setShowSymptomsModal(false)}
        >
          <div
            style={{
              backgroundColor: "var(--surface)",
              borderRadius: 12,
              padding: 24,
              maxWidth: 520,
              width: "100%",
              boxShadow: "0 10px 25px rgba(0,0,0,0.2)",
              display: "flex",
              flexDirection: "column",
              gap: 14,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
              🩺 Confirm & Add Field Visit Symptoms
            </h3>
            
            <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              Citizen Concern: <em>"{caseData.primary_concern || "Health check"}"</em>
            </div>

            {symptomError && (
              <div style={{ padding: "8px 12px", backgroundColor: "var(--urgent-bg)", color: "var(--urgent)", borderRadius: 6, fontSize: 12 }}>
                {symptomError}
              </div>
            )}

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
                Add Confirmed Symptom:
              </label>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  id="symptom-input-field"
                  type="text"
                  value={symptomInput}
                  onChange={(e) => setSymptomInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddSymptomTag();
                    }
                  }}
                  placeholder="e.g., Severe Headache, Blurry Vision, Chest Pain"
                  style={{ flex: 1, padding: 10, borderRadius: 8, border: "1px solid var(--border)" }}
                />
                <button
                  type="button"
                  id="add-symptom-tag-btn"
                  onClick={handleAddSymptomTag}
                  style={{
                    padding: "10px 16px",
                    borderRadius: 8,
                    border: "none",
                    backgroundColor: "var(--primary)",
                    color: "#FFF",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  + Add
                </button>
              </div>
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
                Active Symptom Observations:
              </label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, minHeight: 36, padding: 8, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                {symptomList.length > 0 ? (
                  symptomList.map((sym, idx) => (
                    <span
                      key={idx}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        padding: "4px 10px",
                        borderRadius: 6,
                        backgroundColor: "var(--primary-light)",
                        color: "var(--primary-dark)",
                        fontSize: 12,
                        fontWeight: 700,
                      }}
                    >
                      {sym}
                      <button
                        type="button"
                        onClick={() => handleRemoveSymptomTag(idx)}
                        style={{
                          border: "none",
                          backgroundColor: "transparent",
                          cursor: "pointer",
                          color: "var(--primary-dark)",
                          fontWeight: 700,
                          padding: 0,
                          fontSize: 12,
                        }}
                      >
                        ✕
                      </button>
                    </span>
                  ))
                ) : (
                  <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>No symptoms added yet. Type above and press Add.</span>
                )}
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Severity:
                </label>
                <select
                  value={symptomSeverity}
                  onChange={(e) => setSymptomSeverity(e.target.value)}
                  style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)" }}
                >
                  <option value="Mild">Mild</option>
                  <option value="Moderate">Moderate</option>
                  <option value="Severe">Severe</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Onset / Duration:
                </label>
                <input
                  type="text"
                  value={symptomDuration}
                  onChange={(e) => setSymptomDuration(e.target.value)}
                  placeholder="e.g. 2 days, 1 week"
                  style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                />
              </div>
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                Clinical Notes:
              </label>
              <textarea
                rows={2}
                value={symptomNotes}
                onChange={(e) => setSymptomNotes(e.target.value)}
                placeholder="Field observations, citizen description, or warning signs..."
                style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
              />
            </div>

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
              <button
                type="button"
                onClick={() => setShowSymptomsModal(false)}
                style={{ padding: "10px 16px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer", fontWeight: 600 }}
              >
                Cancel
              </button>
              <button
                id="save-symptoms-submit-btn"
                type="button"
                onClick={handleSaveSymptoms}
                disabled={isSubmittingSymptoms}
                style={{
                  padding: "10px 20px",
                  borderRadius: 8,
                  border: "none",
                  backgroundColor: "var(--primary)",
                  color: "#FFF",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {isSubmittingSymptoms ? "Saving..." : "Confirm & Save Symptoms"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Record Vitals Modal */}
      {showVitalsModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 300,
            padding: 16,
          }}
          onClick={() => setShowVitalsModal(false)}
        >
          <div
            style={{
              backgroundColor: "var(--surface)",
              borderRadius: 12,
              padding: 24,
              maxWidth: 540,
              width: "100%",
              boxShadow: "0 10px 25px rgba(0,0,0,0.2)",
              display: "flex",
              flexDirection: "column",
              gap: 14,
              maxHeight: "90vh",
              overflowY: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
              🩺 Record Field Vitals Observation
            </h3>

            {vitalsError && (
              <div style={{ padding: "8px 12px", backgroundColor: "var(--urgent-bg)", color: "var(--urgent)", borderRadius: 6, fontSize: 12 }}>
                {vitalsError}
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Systolic BP (mmHg)
                </label>
                <input
                  id="vitals-systolic-input"
                  type="number"
                  placeholder="e.g. 120"
                  value={systolic}
                  onChange={(e) => setSystolic(e.target.value === "" ? "" : Number(e.target.value))}
                  style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Diastolic BP (mmHg)
                </label>
                <input
                  id="vitals-diastolic-input"
                  type="number"
                  placeholder="e.g. 80"
                  value={diastolic}
                  onChange={(e) => setDiastolic(e.target.value === "" ? "" : Number(e.target.value))}
                  style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  SpO₂ (%)
                </label>
                <input
                  id="vitals-spo2-input"
                  type="number"
                  placeholder="e.g. 98"
                  value={spo2}
                  onChange={(e) => setSpo2(e.target.value === "" ? "" : Number(e.target.value))}
                  style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Pulse Rate (bpm)
                </label>
                <input
                  id="vitals-pulse-input"
                  type="number"
                  placeholder="e.g. 76"
                  value={pulse}
                  onChange={(e) => setPulse(e.target.value === "" ? "" : Number(e.target.value))}
                  style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Temperature (°C)
                </label>
                <input
                  id="vitals-temp-input"
                  type="number"
                  step="0.1"
                  placeholder="e.g. 37.0"
                  value={temp}
                  onChange={(e) => setTemp(e.target.value === "" ? "" : Number(e.target.value))}
                  style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Weight (kg)
                </label>
                <input
                  id="vitals-weight-input"
                  type="number"
                  step="0.5"
                  placeholder="e.g. 65"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value === "" ? "" : Number(e.target.value))}
                  style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Random Blood Glucose (mg/dL)
                </label>
                <input
                  id="vitals-glucose-input"
                  type="number"
                  placeholder="e.g. 110"
                  value={glucose}
                  onChange={(e) => setGlucose(e.target.value === "" ? "" : Number(e.target.value))}
                  style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                  Respiratory Rate (/min)
                </label>
                <input
                  id="vitals-resprate-input"
                  type="number"
                  placeholder="e.g. 18"
                  value={respRate}
                  onChange={(e) => setRespRate(e.target.value === "" ? "" : Number(e.target.value))}
                  style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                />
              </div>
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                Observation Notes:
              </label>
              <textarea
                rows={2}
                value={vitalNotes}
                onChange={(e) => setVitalNotes(e.target.value)}
                placeholder="Field measurement equipment notes or observations..."
                style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
              />
            </div>

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
              <button
                type="button"
                onClick={() => setShowVitalsModal(false)}
                style={{ padding: "10px 16px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer", fontWeight: 600 }}
              >
                Cancel
              </button>
              <button
                id="save-vitals-submit-btn"
                type="button"
                onClick={handleSaveVitals}
                disabled={isSubmittingVitals}
                style={{
                  padding: "10px 20px",
                  borderRadius: 8,
                  border: "none",
                  backgroundColor: "var(--teal)",
                  color: "#FFF",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {isSubmittingVitals ? "Saving..." : "Save Vitals Observation"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Trends Modal */}
      {showTrendsModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 300,
            padding: 16,
          }}
          onClick={() => setShowTrendsModal(false)}
        >
          <div
            style={{
              backgroundColor: "var(--surface)",
              borderRadius: 12,
              padding: 24,
              maxWidth: 720,
              width: "100%",
              boxShadow: "0 10px 25px rgba(0,0,0,0.2)",
              display: "flex",
              flexDirection: "column",
              gap: 16,
              maxHeight: "90vh",
              overflowY: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
                📊 Longitudinal Vital Trends ({caseData.citizen_name})
              </h3>
              <button
                onClick={() => setShowTrendsModal(false)}
                style={{ border: "none", backgroundColor: "transparent", fontSize: 18, cursor: "pointer" }}
              >
                ✕
              </button>
            </div>

            {/* Filter Tabs */}
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {["ALL", "BP", "SPO2", "PULSE", "TEMP", "GLUCOSE", "WEIGHT"].map((f) => (
                <button
                  key={f}
                  onClick={() => setTrendsFilter(f)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 6,
                    border: trendsFilter === f ? "2px solid var(--primary)" : "1px solid var(--border)",
                    backgroundColor: trendsFilter === f ? "var(--primary-light)" : "var(--surface)",
                    color: trendsFilter === f ? "var(--primary-dark)" : "var(--text-secondary)",
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  {f}
                </button>
              ))}
            </div>

            {loadingTrends ? (
              <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
                Loading vital trends from PostgreSQL...
              </div>
            ) : trendsError ? (
              <div style={{ padding: 20, textAlign: "center", color: "var(--urgent)" }}>
                <div>{trendsError}</div>
                <button
                  onClick={handleOpenTrendsModal}
                  style={{ marginTop: 10, padding: "6px 14px", borderRadius: 6, backgroundColor: "var(--primary)", color: "#FFF", border: "none", cursor: "pointer", fontWeight: 700 }}
                >
                  Retry
                </button>
              </div>
            ) : trendsData.length === 0 ? (
              <div style={{ padding: 30, textAlign: "center", color: "var(--text-secondary)", backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                No historical vitals observations recorded yet for this beneficiary.
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ backgroundColor: "var(--neutral-bg)", textAlign: "left", borderBottom: "2px solid var(--border)" }}>
                      <th style={{ padding: "8px 12px" }}>Date & Time</th>
                      <th style={{ padding: "8px 12px" }}>BP (mmHg)</th>
                      <th style={{ padding: "8px 12px" }}>SpO₂</th>
                      <th style={{ padding: "8px 12px" }}>Pulse</th>
                      <th style={{ padding: "8px 12px" }}>Temp</th>
                      <th style={{ padding: "8px 12px" }}>Glucose</th>
                      <th style={{ padding: "8px 12px" }}>Recorded By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trendsData
                      .filter((v) => {
                        if (trendsFilter === "BP") return v.systolic_bp !== null;
                        if (trendsFilter === "SPO2") return v.spo2 !== null;
                        if (trendsFilter === "PULSE") return v.pulse !== null;
                        if (trendsFilter === "TEMP") return v.temperature_c !== null;
                        if (trendsFilter === "GLUCOSE") return v.glucose_mg_dl !== null;
                        if (trendsFilter === "WEIGHT") return v.weight_kg !== null;
                        return true;
                      })
                      .map((v, idx) => (
                        <tr key={v.id || idx} style={{ borderBottom: "1px solid var(--border)" }}>
                          <td style={{ padding: "10px 12px", whiteSpace: "nowrap" }}>
                            {v.recorded_at ? new Date(v.recorded_at).toLocaleString() : "Recent"}
                          </td>
                          <td style={{ padding: "10px 12px", fontWeight: v.is_warning_sign ? 700 : 500, color: v.is_warning_sign ? "var(--urgent)" : "inherit" }}>
                            {v.systolic_bp && v.diastolic_bp ? `${v.systolic_bp}/${v.diastolic_bp}` : "-"}
                          </td>
                          <td style={{ padding: "10px 12px" }}>{v.spo2 ? `${v.spo2}%` : "-"}</td>
                          <td style={{ padding: "10px 12px" }}>{v.pulse ? `${v.pulse} bpm` : "-"}</td>
                          <td style={{ padding: "10px 12px" }}>{v.temperature_c ? `${v.temperature_c}°C` : "-"}</td>
                          <td style={{ padding: "10px 12px" }}>{v.glucose_mg_dl ? `${v.glucose_mg_dl} mg/dL` : "-"}</td>
                          <td style={{ padding: "10px 12px", fontSize: 12, color: "var(--text-secondary)" }}>
                            {v.recorded_by || "ASHA"}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowTrendsModal(false)}
                style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer", fontWeight: 600 }}
              >
                Close Trends
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Prepare Referral Modal */}
      {showReferralModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 300,
            padding: 16,
          }}
          onClick={() => setShowReferralModal(false)}
        >
          <div
            style={{
              backgroundColor: "var(--surface)",
              borderRadius: 12,
              padding: 24,
              maxWidth: 540,
              width: "100%",
              boxShadow: "0 10px 25px rgba(0,0,0,0.2)",
              display: "flex",
              flexDirection: "column",
              gap: 14,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--urgent)" }}>
              🏥 Prepare Referral to Primary Health Center
            </h3>

            {referralError && (
              <div style={{ padding: "8px 12px", backgroundColor: "var(--urgent-bg)", color: "var(--urgent)", borderRadius: 6, fontSize: 12 }}>
                {referralError}
              </div>
            )}

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                Target Facility:
              </label>
              <div style={{ padding: "10px 12px", backgroundColor: "var(--neutral-bg)", borderRadius: 8, fontWeight: 700, fontSize: 14 }}>
                {caseData.facility_name || caseData.assigned_facility_name || "Kalyanpur Primary Health Center"} ({caseData.assigned_facility_id || caseData.facility_id || "PHC-09"})
              </div>
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                Referral Urgency:
              </label>
              <div style={{ display: "flex", gap: 8 }}>
                {["ROUTINE", "URGENT", "EMERGENCY"].map((u) => (
                  <button
                    key={u}
                    type="button"
                    onClick={() => setReferralUrgency(u)}
                    style={{
                      flex: 1,
                      padding: "8px",
                      borderRadius: 8,
                      border: referralUrgency === u ? "2px solid var(--urgent)" : "1px solid var(--border)",
                      backgroundColor: referralUrgency === u ? "var(--urgent-bg)" : "var(--surface)",
                      color: referralUrgency === u ? "var(--urgent)" : "var(--text-primary)",
                      fontWeight: 700,
                      fontSize: 12,
                      cursor: "pointer",
                    }}
                  >
                    {u}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                Clinical Reason for Referral:
              </label>
              <textarea
                id="referral-reason-textarea"
                rows={3}
                value={referralReason}
                onChange={(e) => setReferralReason(e.target.value)}
                placeholder="Clinical indications and reason for doctor review..."
                style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
              />
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                id="referral-transport-chk"
                checked={referralTransport}
                onChange={(e) => setReferralTransport(e.target.checked)}
              />
              <label htmlFor="referral-transport-chk" style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 600 }}>
                108/102 Emergency Ambulance or Transport Assistance Required
              </label>
            </div>

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
              <button
                type="button"
                onClick={() => setShowReferralModal(false)}
                style={{ padding: "10px 16px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer", fontWeight: 600 }}
              >
                Cancel
              </button>
              <button
                id="submit-referral-confirm-btn"
                type="button"
                onClick={handleSaveReferral}
                disabled={isSubmittingReferral}
                style={{
                  padding: "10px 20px",
                  borderRadius: 8,
                  border: "none",
                  backgroundColor: "var(--urgent)",
                  color: "#FFF",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {isSubmittingReferral ? "Submitting..." : "Submit Referral"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Safety Details Modal */}
      {showSafetyModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 200,
            padding: 16,
          }}
          onClick={() => setShowSafetyModal(false)}
        >
          <div
            style={{
              backgroundColor: "var(--surface)",
              borderRadius: 12,
              padding: 24,
              maxWidth: 520,
              width: "100%",
              boxShadow: "0 10px 25px rgba(0,0,0,0.2)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: "0 0 12px", fontSize: 17, fontWeight: 700, color: "var(--urgent)" }}>
              🚨 Deterministic Safety Assessment
            </h3>
            <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: "20px", marginBottom: 14 }}>
              <strong>Rule Triggered:</strong> {caseData.safety_rule_reason || "Elevated clinical warning signs observed."}<br />
              <strong>Required Next Action:</strong> Priority PHC Medical Officer clinical evaluation within 24 hours.
            </div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 16 }}>
              Note: This is a non-diagnostic safety triage alert designed to prevent delayed referrals. Final diagnosis is established by the PHC Doctor.
            </div>
            <button
              onClick={() => setShowSafetyModal(false)}
              style={{
                width: "100%",
                padding: "10px",
                borderRadius: 8,
                border: "none",
                backgroundColor: "var(--primary)",
                color: "#FFF",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Close Details
            </button>
          </div>
        </div>
      )}

      {/* Citizen Contact Outcome Modal */}
      {showContactModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: 16,
          }}
          onClick={() => setShowContactModal(false)}
        >
          <div
            style={{
              backgroundColor: "var(--surface)",
              borderRadius: 12,
              padding: 24,
              maxWidth: 500,
              width: "100%",
              maxHeight: "90vh",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 16,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>
              📞 Record Citizen Contact Outcome
            </h3>

            {/* Outcome Toggle */}
            <div style={{ display: "flex", gap: 8 }}>
              <button
                type="button"
                onClick={() => setContactOutcome("SPOKE_TO_CITIZEN")}
                style={{
                  flex: 1,
                  padding: "10px",
                  borderRadius: 8,
                  border: contactOutcome === "SPOKE_TO_CITIZEN" ? "2px solid var(--primary)" : "1px solid var(--border)",
                  backgroundColor: contactOutcome === "SPOKE_TO_CITIZEN" ? "var(--primary-light)" : "var(--surface)",
                  color: contactOutcome === "SPOKE_TO_CITIZEN" ? "var(--primary-dark)" : "var(--text-primary)",
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                ✓ Spoke to Citizen
              </button>
              <button
                type="button"
                onClick={() => setContactOutcome("CITIZEN_UNREACHABLE")}
                style={{
                  flex: 1,
                  padding: "10px",
                  borderRadius: 8,
                  border: contactOutcome === "CITIZEN_UNREACHABLE" ? "2px solid var(--urgent)" : "1px solid var(--border)",
                  backgroundColor: contactOutcome === "CITIZEN_UNREACHABLE" ? "var(--urgent-bg)" : "var(--surface)",
                  color: contactOutcome === "CITIZEN_UNREACHABLE" ? "var(--urgent)" : "var(--text-primary)",
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                🚫 Citizen Unreachable
              </button>
            </div>

            {contactOutcome === "SPOKE_TO_CITIZEN" ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                    Who Answered?
                  </label>
                  <select
                    value={whoAnswered}
                    onChange={(e) => setWhoAnswered(e.target.value)}
                    style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)" }}
                  >
                    <option value="CITIZEN">Citizen (Self)</option>
                    <option value="SPOUSE">Spouse / Partner</option>
                    <option value="PARENT">Parent / Family Member</option>
                    <option value="NEIGHBOUR">Neighbour</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                    Current Condition Update
                  </label>
                  <input
                    type="text"
                    value={conditionUpdate}
                    onChange={(e) => setConditionUpdate(e.target.value)}
                    style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                    Preferred Home Visit Timing
                  </label>
                  <input
                    type="text"
                    value={preferredVisitTime}
                    onChange={(e) => setPreferredVisitTime(e.target.value)}
                    style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                    ASHA Call Notes
                  </label>
                  <textarea
                    rows={2}
                    value={contactNotes}
                    onChange={(e) => setContactNotes(e.target.value)}
                    placeholder="Enter observations from phone conversation..."
                    style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                  />
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                      Attempt Number
                    </label>
                    <select
                      value={attemptNumber}
                      onChange={(e) => setAttemptNumber(Number(e.target.value))}
                      style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)" }}
                    >
                      <option value={1}>1st Attempt</option>
                      <option value={2}>2nd Attempt</option>
                      <option value={3}>3rd Attempt</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                      Reason Unreachable
                    </label>
                    <select
                      value={unreachableReason}
                      onChange={(e) => setUnreachableReason(e.target.value)}
                      style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)" }}
                    >
                      <option value="NO_ANSWER">No Answer / Ringing</option>
                      <option value="SWITCHED_OFF">Switched Off</option>
                      <option value="OUT_OF_COVERAGE">Out of Network Coverage</option>
                      <option value="WRONG_NUMBER">Invalid / Wrong Number</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", display: "block", marginBottom: 4 }}>
                    Next Attempt Date
                  </label>
                  <input
                    type="date"
                    value={nextAttemptDate}
                    onChange={(e) => setNextAttemptDate(e.target.value)}
                    style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid var(--border)", boxSizing: "border-box" }}
                  />
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
                  <input
                    type="checkbox"
                    id="escalate-phc-chk"
                    checked={escalatePhc}
                    onChange={(e) => setEscalatePhc(e.target.checked)}
                  />
                  <label htmlFor="escalate-phc-chk" style={{ fontSize: 13, color: "var(--urgent)", fontWeight: 600 }}>
                    Escalate to PHC / Gram Panchayat if citizen remains unreachable after multiple attempts
                  </label>
                </div>
              </div>
            )}

            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 8 }}>
              <button
                type="button"
                onClick={() => setShowContactModal(false)}
                style={{ padding: "10px 16px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer", fontWeight: 600 }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmitContactResult}
                disabled={isSubmittingContact}
                style={{
                  padding: "10px 20px",
                  borderRadius: 8,
                  border: "none",
                  backgroundColor: "var(--primary)",
                  color: "#FFF",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                {isSubmittingContact ? "Saving..." : "Save Outcome"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
