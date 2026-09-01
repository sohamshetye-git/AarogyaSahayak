import React, { useState, useEffect } from "react";
import { useLanguage } from "@aarogya/i18n";
import {
  X, Check, AlertTriangle, ShieldCheck, User, Users,
  Stethoscope, Home as HomeIcon, Phone, Video, MessageSquare,
  Clock, MapPin, ChevronRight, ChevronLeft, Loader2, Sparkles,
  Edit2, Eye, Info
} from "lucide-react";
import { apiClient } from "@aarogya/api-client";

import { useCitizenAuth } from "../context/CitizenAuthContext";

export interface CareHandoffReviewSheetProps {
  isOpen: boolean;
  onClose: () => void;
  requestType: "DOCTOR_CONSULTATION" | "ASHA_ASSISTANCE";
  sessionId?: string;
  needId?: string;
  onSuccess: (result: any) => void;
}

export const CareHandoffReviewSheet: React.FC<CareHandoffReviewSheetProps> = ({
  isOpen,
  onClose,
  requestType,
  sessionId,
  needId,
  onSuccess
}) => {
  const { t, locale } = useLanguage();
  const { user } = useCitizenAuth();

  // Wizard Steps: 1: Beneficiary -> 2: Preview Information -> 3: Channel / Delivery -> 4: Sharing Scope -> 5: Consent & Submit
  const [step, setStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Beneficiary Selection & Candidate Resolution
  const [beneficiaries, setBeneficiaries] = useState<any[]>([]);
  const [selectedBeneficiaryId, setSelectedBeneficiaryId] = useState<string | null>(null);
  const [showAddMember, setShowAddMember] = useState<boolean>(false);
  const [newMemberName, setNewMemberName] = useState<string>("");
  const [newMemberRelation, setNewMemberRelation] = useState<string>("CHILD");
  const [newMemberAge, setNewMemberAge] = useState<string>("");
  const [newMemberPhone, setNewMemberPhone] = useState<string>("");
  const [newMemberAbha, setNewMemberAbha] = useState<string>("");

  const selectedBeneficiary =
    beneficiaries.find((b) => b.beneficiary_id === selectedBeneficiaryId || b.beneficiaryId === selectedBeneficiaryId) ?? null;
  const isSelfSelected = !selectedBeneficiary || selectedBeneficiary?.relationship === "SELF";
  const selfDisplayName = user?.name || (user as any)?.display_name || "Myself";
  const selectedBeneficiaryName = isSelfSelected
    ? (selectedBeneficiary?.display_name && selectedBeneficiary.display_name !== "Sunita Devi" ? selectedBeneficiary.display_name : selfDisplayName)
    : (selectedBeneficiary?.display_name || selectedBeneficiary?.displayName || "Family Member");

  // Duplicate match warning state
  const [potentialDuplicateMatch, setPotentialDuplicateMatch] = useState<any>(null);
  const [confirmRegisterDuplicate, setConfirmRegisterDuplicate] = useState<boolean>(false);

  // Previewed & Editable Handoff Packet
  const [previewPacket, setPreviewPacket] = useState<any>(null);
  const [editedChiefConcern, setEditedChiefConcern] = useState<string>("");
  const [editedSymptoms, setEditedSymptoms] = useState<string[]>([]);
  const [newSymptomInput, setNewSymptomInput] = useState<string>("");
  const [isEditingConcern, setIsEditingConcern] = useState<boolean>(false);

  // Channel & Options
  const [doctorChannel, setDoctorChannel] = useState<"CALLBACK" | "AUDIO" | "VIDEO" | "CHAT">("CALLBACK");
  const [ashaAssistanceType, setAshaAssistanceType] = useState<"HOME_VISIT" | "CALLBACK" | "MEDICINE_DELIVERY">("HOME_VISIT");
  const [preferredTimeWindow, setPreferredTimeWindow] = useState<string>("MORNING");
  const [preferredDate, setPreferredDate] = useState<string>("");
  const [landmark, setLandmark] = useState<string>("");
  const [mobilityNote, setMobilityNote] = useState<string>("");

  // Granular Sharing Scope Checkboxes
  const [scopeStructuredSummary, setScopeStructuredSummary] = useState<boolean>(true);
  const [scopeProfile, setScopeProfile] = useState<boolean>(true);
  const [scopeLocation, setScopeLocation] = useState<boolean>(true);
  const [scopeRecentMessages, setScopeRecentMessages] = useState<boolean>(false);
  const [scopeHealthRecords, setScopeHealthRecords] = useState<boolean>(false);

  // Mandatory Explicit Consent (UNCHECKED BY DEFAULT)
  const [explicitConsent, setExplicitConsent] = useState<boolean>(false);

  // Fetch Preview and Beneficiaries
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    setStep(1);
    setLoading(true);
    setErrorMsg(null);
    setExplicitConsent(false);
    setPotentialDuplicateMatch(null);

    const initData = async () => {
      try {
        const bRes: any = await apiClient.getCitizenBeneficiaries();
        const bList = bRes?.items || bRes?.data?.items || (Array.isArray(bRes) ? bRes : []);
        if (isMounted) {
          setBeneficiaries(Array.isArray(bList) ? bList : []);
          if (bList.length > 0 && !selectedBeneficiaryId) {
            const selfOpt = bList.find((b: any) => b.relationship === "SELF");
            setSelectedBeneficiaryId(selfOpt ? (selfOpt.beneficiary_id || selfOpt.beneficiaryId) : (bList[0].beneficiary_id || bList[0].beneficiaryId));
          }
        }

        const prevRes = await apiClient.previewCareHandoff({
          session_id: sessionId,
          need_id: needId,
          beneficiary_id: selectedBeneficiaryId || undefined,
          request_type: requestType,
          requested_channel: requestType === "DOCTOR_CONSULTATION" ? doctorChannel : ashaAssistanceType
        });
        const packet = prevRes?.data || prevRes;
        if (isMounted && packet) {
          setPreviewPacket(packet);
          setEditedChiefConcern(packet.chief_concern || "");
          const syms = (packet.symptoms || []).map((s: any) => typeof s === "string" ? s : (s.display || s.code));
          setEditedSymptoms(syms);
          if (packet.location?.landmark) {
            setLandmark(packet.location.landmark);
          }
        }
      } catch (err: any) {
        console.error("Failed to load handoff preview:", err);
        const serverMsg = err?.message || err?.response?.data?.detail || err?.response?.data?.message;
        if (isMounted) {
          setErrorMsg(serverMsg || "Could not prepare care summary. Please describe your health concern first.");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    initData();
    return () => { isMounted = false; };
  }, [isOpen, requestType, sessionId, needId, selectedBeneficiaryId]);

  if (!isOpen) return null;

  const isDoc = requestType === "DOCTOR_CONSULTATION";

  const handleResolveNewMember = async () => {
    if (!newMemberName.trim()) {
      setErrorMsg("Please enter the person's name.");
      return;
    }

    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await apiClient.resolveCareHandoffCandidate({
        candidate_name: newMemberName.trim(),
        phone: newMemberPhone.trim() || undefined,
        abha_reference: newMemberAbha.trim() || undefined,
        age: newMemberAge ? parseInt(newMemberAge) : undefined,
        confirm_register_new_duplicate: confirmRegisterDuplicate
      });

      const data = res?.data || res;
      if (data.requires_duplicate_confirmation && data.potential_matches?.length > 0) {
        setPotentialDuplicateMatch(data);
        setLoading(false);
        return;
      }

      // If resolved or created new household member
      const newHm = await apiClient.addCitizenHouseholdMember({
        full_name: newMemberName.trim(),
        relationship_type: newMemberRelation,
        age: newMemberAge ? parseInt(newMemberAge) : undefined,
        sex: newMemberRelation === "MOTHER" || newMemberRelation === "DAUGHTER" ? "FEMALE" : "MALE"
      });

      const hmData = newHm?.data || newHm;
      setBeneficiaries((prev) => [
        ...prev,
        {
          beneficiary_id: hmData.id,
          display_name: hmData.full_name,
          relationship: hmData.relationship_type,
          age: hmData.age,
          gender: hmData.sex,
          is_registered_patient: true
        }
      ]);
      setSelectedBeneficiaryId(hmData.id);
      setShowAddMember(false);
      setPotentialDuplicateMatch(null);
      setNewMemberName("");
      setNewMemberPhone("");
      setNewMemberAbha("");
    } catch (err: any) {
      console.error("Failed to resolve candidate member:", err);
      setErrorMsg(err.message || "Failed to add person.");
    } finally {
      setLoading(false);
    }
  };

  const handleUseExistingDuplicate = (match: any) => {
    setSelectedBeneficiaryId(match.citizen_id || match.household_member_id);
    setPotentialDuplicateMatch(null);
    setShowAddMember(false);
  };

  const handleConfirmRegisterDuplicate = () => {
    setConfirmRegisterDuplicate(true);
    setPotentialDuplicateMatch(null);
    setTimeout(() => {
      handleResolveNewMember();
    }, 100);
  };

  const handleAddSymptom = () => {
    if (!newSymptomInput.trim()) return;
    if (!editedSymptoms.includes(newSymptomInput.trim())) {
      setEditedSymptoms([...editedSymptoms, newSymptomInput.trim()]);
    }
    setNewSymptomInput("");
  };

  const handleRemoveSymptom = (sym: string) => {
    setEditedSymptoms(editedSymptoms.filter(s => s !== sym));
  };

  const handleSubmit = async () => {
    if (!explicitConsent) {
      setErrorMsg("Please confirm explicit consent before submitting.");
      return;
    }

    setSubmitting(true);
    setErrorMsg(null);

    const sharingScope = {
      share_structured_summary: scopeStructuredSummary,
      share_profile: scopeProfile,
      share_location: scopeLocation,
      share_recent_messages: scopeRecentMessages,
      share_existing_health_records: scopeHealthRecords
    };

    const finalPacket = {
      ...(previewPacket || {}),
      chief_concern: editedChiefConcern,
      symptoms: editedSymptoms.map(s => ({
        code: s.toUpperCase().replace(/\s+/g, "_"),
        display: s,
        status: "CONFIRMED",
        source: "AI_STRUCTURED_CITIZEN_CONFIRMED"
      })),
      location: {
        ...(previewPacket?.location || {}),
        landmark: landmark || previewPacket?.location?.landmark
      },
      sharing_scope: sharingScope,
      requested_channel: isDoc ? doctorChannel : ashaAssistanceType,
      preferred_time_window: !isDoc ? preferredTimeWindow : undefined
    };

    try {
      let submitRes: any;
      if (isDoc) {
        submitRes = await apiClient.createCitizenDoctorRequest({
          beneficiary_id: selectedBeneficiaryId || undefined,
          chat_session_id: sessionId,
          citizen_need_id: needId,
          channel: doctorChannel,
          handoff_packet: finalPacket,
          sharing_scope: sharingScope,
          chief_complaint: editedChiefConcern,
          symptoms: editedSymptoms,
          preferred_language: locale || "mr-IN"
        });
      } else {
        submitRes = await apiClient.createCitizenAshaRequest({
          beneficiary_id: selectedBeneficiaryId || undefined,
          chat_session_id: sessionId,
          citizen_need_id: needId,
          assistance_type: ashaAssistanceType,
          preferred_time_window: preferredTimeWindow,
          handoff_packet: finalPacket,
          sharing_scope: sharingScope,
          chief_complaint: editedChiefConcern,
          symptoms: editedSymptoms,
          landmark: landmark || undefined,
          preferred_language: locale || "mr-IN"
        });
      }

      onSuccess(submitRes?.data || submitRes);
      onClose();
    } catch (err: any) {
      console.error("Failed to submit care request:", err);
      setErrorMsg(err.message || "Failed to submit care request. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.7)",
        backdropFilter: "blur(6px)",
        zIndex: 100,
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center"
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 480,
          maxHeight: "90vh",
          backgroundColor: "#FFFFFF",
          borderTopLeftRadius: 28,
          borderTopRightRadius: 28,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          boxShadow: "0 -8px 32px rgba(0,0,0,0.2)"
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid #E2E8F0",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            backgroundColor: isDoc ? "#EFF6FF" : "#ECFDF5"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 12,
                backgroundColor: isDoc ? "#DBEAFE" : "#D1FAE5",
                color: isDoc ? "#1D4ED8" : "#065F46",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}
            >
              {isDoc ? <Stethoscope size={20} /> : <Users size={20} />}
            </div>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 800, color: "#0F172A", margin: 0 }}>
                {isDoc
                  ? t("citizen.doctor_teleconsultation", "Request Doctor Teleconsultation")
                  : t("citizen.asha_assistance", "Request ASHA Assistance")}
              </h3>
              <div style={{ fontSize: 11, color: "#64748B", fontWeight: 600 }}>
                {t("common.step_indicator", { step: String(step), total: "5", defaultValue: `Step ${step} of 5` })}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              border: "none",
              backgroundColor: "#FFFFFF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              boxShadow: "0 1px 4px rgba(0,0,0,0.1)"
            }}
          >
            <X size={18} color="#64748B" />
          </button>
        </div>

        {/* Wizard Step Content */}
        <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
          {errorMsg && (
            <div
              style={{
                marginBottom: 16,
                padding: "12px 14px",
                borderRadius: 14,
                backgroundColor: "#FEF2F2",
                border: "1px solid #FCA5A5",
                color: "#991B1B",
                fontSize: 13,
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: 8
              }}
            >
              <AlertTriangle size={18} />
              <span>{errorMsg}</span>
            </div>
          )}

          {loading ? (
            <div style={{ padding: "40px 0", textAlign: "center" }}>
              <Loader2 size={36} color={isDoc ? "#2563EB" : "#059669"} className="animate-spin" style={{ margin: "0 auto 12px" }} />
              <p style={{ fontSize: 14, color: "#64748B", margin: 0 }}>
                {t("loading.loading_data", "Preparing verified care handoff summary...")}
              </p>
            </div>
          ) : (
            <>
              {/* STEP 1: BENEFICIARY SELECTION */}
              {step === 1 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>
                    {t("wizard.step1_desc", "Who needs to speak with the doctor today?")}
                  </div>

                  {beneficiaries.map((b) => {
                    const bId = b.beneficiary_id || b.beneficiaryId;
                    const isSelected = selectedBeneficiaryId === bId;
                    const isSelf = b.relationship === "SELF";
                    const rel = t(`beneficiary.relationship.${b.relationship || "OTHER"}`, b.relationship || "Other");
                    return (
                      <div
                        key={bId}
                        onClick={() => setSelectedBeneficiaryId(bId)}
                        style={{
                          padding: 14,
                          borderRadius: 16,
                          border: isSelected ? "2px solid #2563EB" : "1px solid #E2E8F0",
                          backgroundColor: isSelected ? "#EFF6FF" : "#FFFFFF",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          cursor: "pointer"
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                          <div style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: isSelf ? "#DBEAFE" : "#F1F5F9", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            {isSelf ? <User size={20} color="#2563EB" /> : <Users size={20} color="#475569" />}
                          </div>
                          <div>
                            <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B" }}>
                              {b.display_name || b.displayName} {isSelf && `(${t("common.myself", "Myself")})`}
                            </div>
                            <div style={{ fontSize: 12, color: "#64748B" }}>
                              {rel} {b.age ? `• ${b.age} ${t("common.age", "yrs")}` : ""}
                            </div>
                          </div>
                        </div>
                        {isSelected && <Check size={20} color="#2563EB" />}
                      </div>
                    );
                  })}

                  {/* Add Family Member Button / Form */}
                  {!showAddMember ? (
                    <button
                      onClick={() => setShowAddMember(true)}
                      style={{
                        padding: 12,
                        borderRadius: 14,
                        border: "1px dashed #CBD5E1",
                        backgroundColor: "#F8FAFC",
                        color: "#2563EB",
                        fontWeight: 700,
                        fontSize: 13,
                        cursor: "pointer"
                      }}
                    >
                      + {t("citizen.add_family_member", "Add another family member")}
                    </button>
                  ) : (
                    <div style={{ backgroundColor: "#F8FAFC", borderRadius: 16, padding: 14, border: "1px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 10 }}>
                      <div style={{ fontSize: 13, fontWeight: 800, color: "#0F172A" }}>
                        {t("citizen.family_member_details", "Family Member Details")}
                      </div>
                      <input
                        type="text"
                        placeholder={t("patient.full_name", "Full Name")}
                        value={newMemberName}
                        onChange={(e) => setNewMemberName(e.target.value)}
                        style={{ padding: 10, borderRadius: 10, border: "1px solid #CBD5E1", fontSize: 13 }}
                      />
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                        <select
                          value={newMemberRelation}
                          onChange={(e) => setNewMemberRelation(e.target.value)}
                          style={{ padding: 10, borderRadius: 10, border: "1px solid #CBD5E1", fontSize: 13 }}
                        >
                          <option value="SPOUSE">{t("beneficiary.relationship.SPOUSE", "Spouse")}</option>
                          <option value="CHILD">{t("beneficiary.relationship.CHILD", "Child")}</option>
                          <option value="MOTHER">{t("beneficiary.relationship.MOTHER", "Mother")}</option>
                          <option value="FATHER">{t("beneficiary.relationship.FATHER", "Father")}</option>
                          <option value="OTHER">{t("beneficiary.relationship.OTHER", "Other")}</option>
                        </select>
                        <input
                          type="number"
                          placeholder={t("common.age", "Age")}
                          value={newMemberAge}
                          onChange={(e) => setNewMemberAge(e.target.value)}
                          style={{ padding: 10, borderRadius: 10, border: "1px solid #CBD5E1", fontSize: 13 }}
                        />
                      </div>
                      <div style={{ display: "flex", gap: 8 }}>
                        <button
                          onClick={handleResolveNewMember}
                          style={{ flex: 1, padding: 10, borderRadius: 10, backgroundColor: "#2563EB", color: "#FFFFFF", border: "none", fontWeight: 700, fontSize: 13, cursor: "pointer" }}
                        >
                          {t("common.save", "Save")}
                        </button>
                        <button
                          onClick={() => setShowAddMember(false)}
                          style={{ padding: 10, borderRadius: 10, backgroundColor: "#E2E8F0", color: "#475569", border: "none", fontWeight: 700, fontSize: 13, cursor: "pointer" }}
                        >
                          {t("common.cancel", "Cancel")}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Duplicate Resolution Warning */}
                  {potentialDuplicateMatch && (
                    <div style={{ backgroundColor: "#FEF3C7", borderRadius: 16, padding: 14, border: "1px solid #FCD34D", display: "flex", flexDirection: "column", gap: 10 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#92400E", fontWeight: 800, fontSize: 13 }}>
                        <AlertTriangle size={18} />
                        Possible Existing Patient Match Found
                      </div>
                      <div style={{ fontSize: 12, color: "#78350F" }}>
                        A matching patient record already exists in Kalyanpur PHC for <b>{newMemberName}</b>. Would you like to link this existing record or create a distinct profile?
                      </div>
                      <div style={{ display: "flex", gap: 8 }}>
                        <button
                          onClick={() => handleUseExistingDuplicate(potentialDuplicateMatch.potential_matches[0])}
                          style={{ flex: 1, padding: "8px 10px", borderRadius: 10, backgroundColor: "#92400E", color: "#FFFFFF", border: "none", fontWeight: 700, fontSize: 12, cursor: "pointer" }}
                        >
                          Use Existing Profile
                        </button>
                        <button
                          onClick={handleConfirmRegisterDuplicate}
                          style={{ padding: "8px 10px", borderRadius: 10, backgroundColor: "#FDE68A", color: "#78350F", border: "none", fontWeight: 700, fontSize: 12, cursor: "pointer" }}
                        >
                          Create Distinct Profile
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* STEP 2: PREVIEW & EDIT HEALTH INFORMATION */}
              {step === 2 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>
                    {t("wizard.step2_title", "2. Describe Health Concern")}
                  </div>

                  {/* Editable Chief Concern */}
                  <div style={{ backgroundColor: "#F8FAFC", borderRadius: 16, padding: 14, border: "1px solid #E2E8F0" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                      <span style={{ fontSize: 12, fontWeight: 800, color: "#64748B" }}>
                        {t("wizard.step6_field_concern", "Primary Health Concern:")}
                      </span>
                      <button
                        onClick={() => setIsEditingConcern(!isEditingConcern)}
                        style={{ border: "none", background: "none", color: "#2563EB", fontSize: 12, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
                      >
                        <Edit2 size={12} />
                        {isEditingConcern ? t("common.save", "Done") : t("common.edit", "Edit")}
                      </button>
                    </div>
                    {isEditingConcern ? (
                      <textarea
                        value={editedChiefConcern}
                        onChange={(e) => setEditedChiefConcern(e.target.value)}
                        rows={2}
                        style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid #CBD5E1", fontSize: 13 }}
                      />
                    ) : (
                      <div style={{ fontSize: 14, fontWeight: 700, color: "#0F172A" }}>
                        {editedChiefConcern || t("common.value.UNKNOWN", "Not specified")}
                      </div>
                    )}
                  </div>

                  {/* Symptoms list */}
                  <div style={{ backgroundColor: "#F8FAFC", borderRadius: 16, padding: 14, border: "1px solid #E2E8F0" }}>
                    <span style={{ fontSize: 12, fontWeight: 800, color: "#64748B", display: "block", marginBottom: 8 }}>
                      {t("wizard.step2_identified_symptoms", "Identified Symptoms")}
                    </span>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
                      {editedSymptoms.map((sym, i) => {
                        const symKey = sym.toUpperCase().replace(/\s+/g, "_");
                        const symDisplay = t(`symptoms.${symKey}`, sym);
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
                              onClick={() => handleRemoveSymptom(sym)}
                              style={{ border: "none", background: "none", color: "#6B7280", cursor: "pointer", padding: 0 }}
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
                        onChange={(e) => setNewSymptomInput(e.target.value)}
                        placeholder={t("wizard.step2_add_symptom_placeholder", "Add symptom (e.g. Fever)")}
                        style={{
                          flex: 1,
                          padding: "8px 12px",
                          borderRadius: 10,
                          border: "1px solid #CBD5E1",
                          fontSize: 13,
                          outline: "none"
                        }}
                      />
                      <button
                        onClick={handleAddSymptom}
                        style={{
                          padding: "8px 14px",
                          borderRadius: 10,
                          backgroundColor: isDoc ? "#2563EB" : "#059669",
                          color: "#FFFFFF",
                          border: "none",
                          fontWeight: 700,
                          fontSize: 13,
                          cursor: "pointer"
                        }}
                      >
                        {t("common.add", "Add")}
                      </button>
                    </div>
                  </div>

                  {/* Deterministic Safety Badge */}
                  {previewPacket?.safety && (
                    <div
                      style={{
                        padding: 12,
                        borderRadius: 14,
                        backgroundColor: previewPacket.safety.priority === "URGENT" || previewPacket.safety.priority === "EMERGENCY" ? "#FEF2F2" : "#F0FDF4",
                        border: previewPacket.safety.priority === "URGENT" || previewPacket.safety.priority === "EMERGENCY" ? "1px solid #FCA5A5" : "1px solid #BBF7D0",
                        display: "flex",
                        alignItems: "center",
                        gap: 10
                      }}
                    >
                      <ShieldCheck size={20} color={previewPacket.safety.priority === "URGENT" ? "#DC2626" : "#166534"} />
                      <div style={{ fontSize: 13, color: "#1E293B", fontWeight: 600 }}>
                        <strong>{t("common.priority", "Priority")}:</strong> {t(`priority.${previewPacket.safety.priority}`, previewPacket.safety.priority)}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* STEP 3: CHANNEL & CONTACT DETAILS */}
              {step === 3 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>
                    {isDoc
                      ? t("wizard.step3_title", "3. Select Consultation Channel")
                      : t("citizen.asha_assistance", "Select Assistance Type & Time")}
                  </div>

                  {isDoc ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      {[
                        { id: "CALLBACK", label: t("consultation.channel.CALLBACK", "Doctor Phone Callback"), desc: t("wizard.step3_desc_callback", "Doctor will call your registered phone"), icon: Phone },
                        { id: "AUDIO", label: t("consultation.channel.AUDIO", "In-App Audio Consultation"), desc: t("wizard.step3_desc_audio", "Telehealth voice room (WebRTC)"), icon: Phone },
                        { id: "VIDEO", label: t("consultation.channel.VIDEO", "In-App Video Consultation"), desc: t("wizard.step3_desc_video", "Live video room (WebRTC)"), icon: Video },
                        { id: "CHAT", label: t("consultation.channel.CHAT", "Doctor Chat Advice"), desc: t("wizard.step3_desc_chat", "Structured written consultation guidance"), icon: MessageSquare }
                      ].map((ch) => {
                        const Icon = ch.icon;
                        const active = doctorChannel === ch.id;
                        return (
                          <div
                            key={ch.id}
                            onClick={() => setDoctorChannel(ch.id as any)}
                            style={{
                              padding: 14,
                              borderRadius: 16,
                              border: active ? "2px solid #2563EB" : "1px solid #E2E8F0",
                              backgroundColor: active ? "#EFF6FF" : "#FFFFFF",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              cursor: "pointer"
                            }}
                          >
                            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                              <Icon size={20} color={active ? "#2563EB" : "#64748B"} />
                              <div>
                                <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B" }}>{ch.label}</div>
                                <div style={{ fontSize: 12, color: "#64748B" }}>{ch.desc}</div>
                              </div>
                            </div>
                            {active && <Check size={18} color="#2563EB" />}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                      <div style={{ display: "flex", gap: 8 }}>
                        {[
                          { id: "HOME_VISIT", label: t("asha.home_visit", "Home Visit") },
                          { id: "CALLBACK", label: t("consultation.channel.CALLBACK", "Phone Call") },
                          { id: "MEDICINE_DELIVERY", label: t("asha.medicine_delivery", "Medicine Drop") }
                        ].map((item) => (
                          <button
                            key={item.id}
                            onClick={() => setAshaAssistanceType(item.id as any)}
                            style={{
                              flex: 1,
                              padding: "10px 8px",
                              borderRadius: 12,
                              border: ashaAssistanceType === item.id ? "2px solid #059669" : "1px solid #CBD5E1",
                              backgroundColor: ashaAssistanceType === item.id ? "#ECFDF5" : "#FFFFFF",
                              color: ashaAssistanceType === item.id ? "#065F46" : "#475569",
                              fontWeight: 800,
                              fontSize: 12,
                              cursor: "pointer"
                            }}
                          >
                            {item.label}
                          </button>
                        ))}
                      </div>

                      <div>
                        <label style={{ fontSize: 12, fontWeight: 800, color: "#475569", display: "block", marginBottom: 6 }}>
                          {t("common.time", "Preferred Time Window")}
                        </label>
                        <select
                          value={preferredTimeWindow}
                          onChange={(e) => setPreferredTimeWindow(e.target.value)}
                          style={{
                            width: "100%",
                            padding: 10,
                            borderRadius: 12,
                            border: "1px solid #CBD5E1",
                            fontSize: 14,
                            outline: "none"
                          }}
                        >
                          <option value="MORNING">Morning (9:00 AM - 12:00 PM)</option>
                          <option value="AFTERNOON">Afternoon (12:00 PM - 3:00 PM)</option>
                          <option value="EVENING">Evening (3:00 PM - 6:00 PM)</option>
                          <option value="ANYTIME">Anytime (Urgent)</option>
                        </select>
                      </div>

                      <div>
                        <label style={{ fontSize: 12, fontWeight: 800, color: "#475569", display: "block", marginBottom: 6 }}>
                          {t("wizard.step4_landmark_label", "Nearby Landmark / House Address")}
                        </label>
                        <input
                          type="text"
                          value={landmark}
                          onChange={(e) => setLandmark(e.target.value)}
                          placeholder={t("wizard.step4_landmark_placeholder", "e.g. Near Kalyanpur Gram Panchayat")}
                          style={{
                            width: "100%",
                            padding: 10,
                            borderRadius: 12,
                            border: "1px solid #CBD5E1",
                            fontSize: 14,
                            outline: "none"
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* STEP 4: GRANULAR SHARING SCOPE */}
              {step === 4 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>
                    {t("wizard.step5_title", "5. Consented Sharing Scope")}
                  </div>
                  <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.4 }}>
                    {t("wizard.step5_desc", "Select what clinical information will be shared with the PHC Medical Officer.")}
                  </div>

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
                        padding: 12,
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
              )}

              {/* STEP 5: EXPLICIT CONSENT & ATOMIC SUBMIT */}
              {step === 5 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>
                    {t("wizard.step6_title", "6. Explicit Consent & Submit")}
                  </div>

                  <div style={{ backgroundColor: "#F8FAFC", borderRadius: 16, padding: 14, border: "1px solid #E2E8F0" }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "#64748B", marginBottom: 4 }}>{t("common.details", "Recipient")}</div>
                    <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B" }}>
                      {isDoc ? "PHC Medical Officer (Kalyanpur PHC)" : "Jurisdiction ASHA Worker (Kalyanpur)"}
                    </div>

                    <div style={{ fontSize: 12, fontWeight: 700, color: "#64748B", marginTop: 10, marginBottom: 4 }}>{t("wizard.step6_field_patient", "Patient:")}</div>
                    <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B" }}>{selectedBeneficiaryName}</div>

                    <div style={{ fontSize: 12, fontWeight: 700, color: "#64748B", marginTop: 10, marginBottom: 4 }}>{t("wizard.step6_field_location", "Care Location:")}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "#0F172A", display: "flex", alignItems: "center", gap: 6 }}>
                      <MapPin size={14} color="#2563EB" />
                      <span>{landmark || previewPacket?.location?.village || previewPacket?.location?.formatted_address || "Kalyanpur"}</span>
                    </div>

                    <div style={{ fontSize: 12, fontWeight: 700, color: "#64748B", marginTop: 10, marginBottom: 4 }}>{t("wizard.step6_field_concern", "Primary Health Concern:")}</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "#334155" }}>{editedChiefConcern}</div>
                  </div>

                  <div
                    onClick={() => setExplicitConsent(!explicitConsent)}
                    style={{
                      padding: 14,
                      borderRadius: 16,
                      border: explicitConsent ? "2px solid #166534" : "2px solid #DC2626",
                      backgroundColor: explicitConsent ? "#F0FDF4" : "#FEF2F2",
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 12,
                      cursor: "pointer"
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={explicitConsent}
                      onChange={(e) => setExplicitConsent(e.target.checked)}
                      style={{ width: 22, height: 22, marginTop: 2, cursor: "pointer" }}
                    />
                    <div style={{ fontSize: 13, fontWeight: 700, color: "#1E293B", lineHeight: 1.4 }}>
                      {t("wizard.step6_consent_statement", "I explicitly consent to share the selected health concern and clinical details with the PHC Doctor for teleconsultation and medical care.")}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer Navigation */}
        <div
          style={{
            padding: 16,
            backgroundColor: "#FFFFFF",
            borderTop: "1px solid #E2E8F0",
            display: "flex",
            alignItems: "center",
            gap: 10
          }}
        >
          {step > 1 ? (
            <button
              onClick={() => setStep(step - 1)}
              disabled={submitting}
              style={{
                flex: 1,
                padding: "12px 16px",
                borderRadius: 14,
                backgroundColor: "#F1F5F9",
                color: "#334155",
                border: "1px solid #CBD5E1",
                fontWeight: 800,
                fontSize: 14,
                cursor: "pointer"
              }}
            >
              {t("common.back", "Back")}
            </button>
          ) : (
            <button
              onClick={onClose}
              disabled={submitting}
              style={{
                flex: 1,
                padding: "12px 16px",
                borderRadius: 14,
                backgroundColor: "#F1F5F9",
                color: "#334155",
                border: "1px solid #CBD5E1",
                fontWeight: 800,
                fontSize: 14,
                cursor: "pointer"
              }}
            >
              {t("common.cancel", "Cancel")}
            </button>
          )}

          {step < 5 ? (
            <button
              onClick={() => setStep(step + 1)}
              disabled={loading}
              style={{
                flex: 2,
                padding: "12px 16px",
                borderRadius: 14,
                backgroundColor: isDoc ? "#2563EB" : "#059669",
                color: "#FFFFFF",
                border: "none",
                fontWeight: 800,
                fontSize: 14,
                cursor: "pointer"
              }}
            >
              {t("common.continue", "Continue")}
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!explicitConsent || submitting}
              style={{
                flex: 2,
                padding: "12px 16px",
                borderRadius: 14,
                backgroundColor: !explicitConsent ? "#94A3B8" : (isDoc ? "#1E40AF" : "#047857"),
                color: "#FFFFFF",
                border: "none",
                fontWeight: 800,
                fontSize: 14,
                cursor: !explicitConsent || submitting ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6
              }}
            >
              {submitting ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>{t("loading.submitting", "Submitting...")}</span>
                </>
              ) : (
                <>
                  <Check size={18} />
                  <span>{t("wizard.step6_submit_btn", "Confirm & Submit")}</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
