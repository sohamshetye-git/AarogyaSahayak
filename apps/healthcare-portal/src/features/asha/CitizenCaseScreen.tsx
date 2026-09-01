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
          age: currentCase.citizen_age || 22,
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

  if (loading || !caseData) {
    return (
      <div style={{ padding: "60px 0", textAlign: "center", color: "var(--text-secondary)" }}>
        <div style={{ fontSize: 16, fontWeight: 600 }}>Loading patient case review...</div>
      </div>
    );
  }

  const maskPhone = (phone: string) => {
    if (!phone) return "9876543212";
    if (phoneRevealed) return phone;
    return phone.length >= 10 ? `******${phone.slice(-4)}` : phone;
  };

  const maskAbha = (abha: string) => {
    if (!abha) return "12-3456-7890-3212";
    return abha.length >= 14 ? `${abha.slice(0, 4)}-****-****-${abha.slice(-4)}` : abha;
  };

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
          onClick={() => navigate(`/asha/visit?caseId=${caseData.id}`)}
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
          <span>{t("asha.start_field_visit", "Start Field Visit")}</span>
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
      return (
        <button
          onClick={() => navigate(`/asha/followups?citizenId=${caseData.citizen_id}`)}
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
          🔄 Start Follow-up
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

  // Next Task Category resolution
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
        task: "Conduct Comprehensive 7-Step Field Visit",
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
        worker: "Dr. Abhinav Sharma (Kalyanpur PHC)"
      };
    }
    if (status === "NEW") {
      return {
        task: "Acknowledge New Incident Report",
        category: "Urgent Triage",
        due: "Immediate",
        source: "Citizen Mobile Voice Intake",
        worker: "Sita Patel (ASHA Worker)"
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
            {caseData.is_pregnant && (
              <span style={{ padding: "3px 10px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 12, fontWeight: 700 }}>
                Pregnant ({caseData.gestational_weeks ? `${caseData.gestational_weeks}w` : "14w"} · Trimester 2)
              </span>
            )}
          </div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", display: "flex", gap: 12, flexWrap: "wrap" }}>
            <span>Ref: <strong>{caseData.reference}</strong></span>
            <span>·</span>
            <span>Village: {caseData.village_name || "Ganeshpur"}</span>
            <span>·</span>
            <span>Age: {caseData.citizen_age || 22}y ({caseData.citizen_gender || "Female"})</span>
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
                {caseData.safety_rule_reason || "Elevated blood pressure observed in pregnancy assessment (BP: 150/100 mmHg)."}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
                Matched Rule: Maternal Hypertension Screening (Rule ID: SAFETY-MAT-01, v2026.1)
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
                <strong>{caseData.village_name || "Ganeshpur"}</strong>
              </div>
            </div>

            <div style={{ padding: "8px 12px", backgroundColor: "var(--neutral-bg)", borderRadius: 6, fontSize: 12, color: "var(--text-secondary)", marginBottom: 14 }}>
              📍 Landmark: Near Ganesh Mandir, House #42 · Last contact: Today 10:30 AM (Citizen Spoke)
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
                  <button
                    onClick={() => navigate("/asha/schemes")}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 6,
                      border: "1px solid var(--border)",
                      backgroundColor: "var(--surface)",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer"
                    }}
                  >
                    🏛 Evaluate Schemes
                  </button>
                  <button
                    onClick={() => navigate("/asha/people")}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 6,
                      border: "1px solid var(--border)",
                      backgroundColor: "var(--surface)",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer"
                    }}
                  >
                    📁 Directory
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
                        ✓ {s.term}
                      </span>
                    ))
                  ) : (
                    <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                      None recorded yet (Pending in-person confirmation during field visit).
                    </span>
                  )}
                </div>

                <button
                  onClick={() => navigate(`/asha/visit?caseId=${caseData.id}&step=2`)}
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

          {/* C. Dynamic Patient Context (Pregnancy / Maternal) */}
          <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <h3 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
              🤰 Dynamic Context: Antenatal Maternal Tracking
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 13 }}>
              <div>
                <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Gestational Age</span>
                <strong>{caseData.gestational_weeks || 14} Weeks (Trimester 2)</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Estimated Due Date (EDD)</span>
                <strong>24 Feb 2027 (Consistent)</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>ANC Registration</span>
                <strong style={{ color: "#2E7D32" }}>✓ Registered (ANC-1 Done)</strong>
              </div>
              <div>
                <span style={{ color: "var(--text-secondary)", display: "block", fontSize: 11 }}>Next Scheduled ANC</span>
                <strong>ANC-2 Due (16-18 Weeks)</strong>
              </div>
            </div>
          </div>

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
                  Evaluating 29 schemes against PostgreSQL criteria...
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
              <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>Verified</span>
            </div>

            {caseData.vitals && caseData.vitals.length > 0 ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
                <div style={{ padding: 10, backgroundColor: "var(--urgent-bg)", borderRadius: 8, border: "1px solid #F5C6CB" }}>
                  <div style={{ fontSize: 11, color: "var(--urgent)", fontWeight: 700 }}>Blood Pressure (BP)</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: "var(--urgent)", marginTop: 2 }}>
                    {caseData.vitals[0].systolic_bp}/{caseData.vitals[0].diastolic_bp}
                    <span style={{ fontSize: 11, fontWeight: 500, marginLeft: 4 }}>mmHg</span>
                  </div>
                </div>

                <div style={{ padding: 10, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 600 }}>SpO₂ Level</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                    {caseData.vitals[0].spo2 || 97}%
                  </div>
                </div>

                <div style={{ padding: 10, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 600 }}>Pulse Rate</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                    {caseData.vitals[0].pulse || 88} <span style={{ fontSize: 11, fontWeight: 500 }}>bpm</span>
                  </div>
                </div>

                <div style={{ padding: 10, backgroundColor: "var(--neutral-bg)", borderRadius: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 600 }}>Temperature / Weight</div>
                  <div style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", marginTop: 2 }}>
                    {caseData.vitals[0].temperature_c || 37.0}°C · 52 kg
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ padding: 14, backgroundColor: "var(--neutral-bg)", borderRadius: 8, fontSize: 13, color: "var(--text-secondary)", marginBottom: 14 }}>
                No vitals recorded yet. Record vitals during field visit.
              </div>
            )}

            <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 12, fontStyle: "italic" }}>
              Recorded by Sita Patel (ASHA) · Source: Manual Validated Cuff
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => navigate(`/asha/visit?caseId=${caseData.id}&step=3`)}
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
                onClick={() => navigate(`/asha/visit?caseId=${caseData.id}&step=3`)}
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
                <strong>{caseData.status === "CITIZEN_CONTACTED" ? "Scheduled (Today)" : "In Progress / Done"}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>PHC Referral</span>
                <strong>{caseData.status === "REFERRED_TO_PHC" ? "Referred (PHC-09 Kalyanpur)" : "Not Created"}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", backgroundColor: "var(--neutral-bg)", borderRadius: 6 }}>
                <span style={{ color: "var(--text-secondary)" }}>Doctor Review Status</span>
                <strong>{caseData.status === "DOCTOR_ACKNOWLEDGED" ? "Reviewed by Dr. Sharma" : "Pending Referral Submission"}</strong>
              </div>
            </div>

            {caseData.status !== "REFERRED_TO_PHC" ? (
              <button
                onClick={() => navigate(`/asha/visit?caseId=${caseData.id}&step=6`)}
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
                🏥 Prepare Referral to Kalyanpur PHC
              </button>
            ) : (
              <div style={{ padding: "10px", backgroundColor: "#E8F5E9", color: "#2E7D32", borderRadius: 6, fontSize: 12, fontWeight: 700, textAlign: "center" }}>
                ✓ Referral active at Kalyanpur PHC. Duplicate referral prevented.
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

            <div style={{ padding: "12px 14px", backgroundColor: "var(--neutral-bg)", borderRadius: 8, border: "1px solid var(--border)", marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 13, fontWeight: 700 }}>Repeat BP Check & Warning Signs</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: "var(--urgent)" }}>URGENT</span>
              </div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                Due in 2 days · Assigned to Sita Patel (ASHA) · Source: Antenatal Triage
              </div>
            </div>

            <button
              onClick={() => navigate(`/asha/followups?citizenId=${caseData.citizen_id}`)}
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
              Start Follow-up Task
            </button>
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
            {Array.from(new Map(timeline.map((evt) => [evt.event_type + evt.timestamp, evt])).values()).map((evt, idx) => (
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
                    {new Date(evt.timestamp).toLocaleString()}
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
              <strong>Rule Triggered:</strong> Maternal Antenatal Danger Signs & Stage 2 Hypertension.<br />
              <strong>Observed Vitals:</strong> Blood Pressure 150/100 mmHg.<br />
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
