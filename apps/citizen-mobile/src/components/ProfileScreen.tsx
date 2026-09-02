import React, { useState, useEffect, useCallback } from "react";
import { useLanguage, getLanguageBadgeLabel } from "@aarogya/i18n";
import {
  User, Users, Shield, Phone, Globe, ChevronRight, Plus, CheckCircle2,
  AlertTriangle, ArrowLeft, Loader2, Edit3, Trash2, HeartPulse, Stethoscope,
  Award, FileText, Check, ShieldCheck, MapPin, Building2, UserCheck, RefreshCw, X
} from "lucide-react";
import { apiClient } from "@aarogya/api-client";
import {
  CitizenProfileDTO,
  HouseholdMemberDTO,
  CareTeamResponseDTO,
  ConsentRecordDTO,
  AbhaLinkStatusDTO
} from "@aarogya/shared-types";
import { LanguageService, LanguageCode } from "../services/languageService";

export type ProfileSubRoute =
  | { type: "main" }
  | { type: "personal" }
  | { type: "household" }
  | { type: "household_new" }
  | { type: "household_member"; memberId: string }
  | { type: "care_team" }
  | { type: "language" }
  | { type: "consent_privacy" }
  | { type: "emergency" };

interface ProfileScreenProps {
  onSelectLanguage?: () => void;
  onNavigateToTab?: (tab: string) => void;
}

import { useCitizenAuth } from "../context/CitizenAuthContext";

export const ProfileScreen: React.FC<ProfileScreenProps> = ({
  onSelectLanguage,
  onNavigateToTab
}) => {
  const { t, locale, setLocale } = useLanguage();
  const { user, refreshBeneficiaries } = useCitizenAuth();

  // 1. Navigation state
  const [routeState, setRouteState] = useState<ProfileSubRoute>(() => {
    const p = window.location.pathname;
    if (p.includes("/citizen/profile/personal")) return { type: "personal" };
    if (p.includes("/citizen/profile/household/new")) return { type: "household_new" };
    if (p.includes("/citizen/profile/household/")) {
      const parts = p.split("/citizen/profile/household/");
      if (parts[1]) return { type: "household_member", memberId: parts[1] };
    }
    if (p.includes("/citizen/profile/household")) return { type: "household" };
    if (p.includes("/citizen/profile/care-team")) return { type: "care_team" };
    if (p.includes("/citizen/profile/language")) return { type: "language" };
    if (p.includes("/citizen/profile/consent-privacy")) return { type: "consent_privacy" };
    if (p.includes("/citizen/profile/emergency")) return { type: "emergency" };
    return { type: "main" };
  });

  // URL synchronization helper
  const navigateTo = useCallback((subRoute: ProfileSubRoute, replace = false) => {
    setRouteState(subRoute);
    let path = "/citizen/profile";
    if (subRoute.type === "personal") path = "/citizen/profile/personal";
    else if (subRoute.type === "household") path = "/citizen/profile/household";
    else if (subRoute.type === "household_new") path = "/citizen/profile/household/new";
    else if (subRoute.type === "household_member") path = `/citizen/profile/household/${subRoute.memberId}`;
    else if (subRoute.type === "care_team") path = "/citizen/profile/care-team";
    else if (subRoute.type === "language") path = "/citizen/profile/language";
    else if (subRoute.type === "consent_privacy") path = "/citizen/profile/consent-privacy";
    else if (subRoute.type === "emergency") path = "/citizen/profile/emergency";

    if (replace) {
      window.history.replaceState({ profileRoute: subRoute }, "", path);
    } else {
      window.history.pushState({ profileRoute: subRoute }, "", path);
    }
  }, []);

  // Handle browser popstate
  useEffect(() => {
    const handlePopState = () => {
      const p = window.location.pathname;
      if (p.includes("/citizen/profile/personal")) setRouteState({ type: "personal" });
      else if (p.includes("/citizen/profile/household/new")) setRouteState({ type: "household_new" });
      else if (p.includes("/citizen/profile/household/")) {
        const parts = p.split("/citizen/profile/household/");
        if (parts[1]) setRouteState({ type: "household_member", memberId: parts[1] });
      }
      else if (p.includes("/citizen/profile/household")) setRouteState({ type: "household" });
      else if (p.includes("/citizen/profile/care-team")) setRouteState({ type: "care_team" });
      else if (p.includes("/citizen/profile/language")) setRouteState({ type: "language" });
      else if (p.includes("/citizen/profile/consent-privacy")) setRouteState({ type: "consent_privacy" });
      else if (p.includes("/citizen/profile/emergency")) setRouteState({ type: "emergency" });
      else setRouteState({ type: "main" });
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  // 2. Data States
  const [profile, setProfile] = useState<CitizenProfileDTO | null>(null);
  const [household, setHousehold] = useState<HouseholdMemberDTO[]>([]);
  const [careTeam, setCareTeam] = useState<CareTeamResponseDTO | null>(null);
  const [consents, setConsents] = useState<ConsentRecordDTO[]>([]);
  const [abhaStatus, setAbhaStatus] = useState<AbhaLinkStatusDTO | null>(null);
  const [selectedMember, setSelectedMember] = useState<HouseholdMemberDTO | null>(null);

  // Loading & Feedback
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Forms State
  const [editPersonalForm, setEditPersonalForm] = useState<any>({});
  const [addMemberForm, setAddMemberForm] = useState<{
    full_name: string;
    relationship_type: string;
    age: string;
    sex: string;
    phone: string;
    blood_group: string;
    is_pregnant: boolean;
    gestational_weeks: string;
    chronic_conditions: string[];
    health_notes: string;
  }>({
    full_name: "",
    relationship_type: "CHILD",
    age: "",
    sex: "Female",
    phone: "",
    blood_group: "O+",
    is_pregnant: false,
    gestational_weeks: "",
    chronic_conditions: [],
    health_notes: ""
  });

  const [editMemberForm, setEditMemberForm] = useState<any>({});
  const [isEditingMember, setIsEditingMember] = useState(false);

  const showToast = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 4000);
  };

  // 3. Load Main Data
  const loadAllProfileData = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [profRes, houseRes, teamRes, consentRes, abhaRes] = await Promise.allSettled([
        apiClient.getCitizenProfile(),
        apiClient.getCitizenHouseholdMembers(),
        apiClient.getCitizenCareTeam(),
        apiClient.getCitizenConsents(),
        apiClient.getCitizenAbhaLinkStatus()
      ]);

      const extractList = (val: any) => {
        if (Array.isArray(val)) return val;
        if (Array.isArray(val?.items)) return val.items;
        if (Array.isArray(val?.data?.items)) return val.data.items;
        if (Array.isArray(val?.data)) return val.data;
        return [];
      };

      if (profRes.status === "fulfilled") {
        const p = profRes.value?.data || profRes.value;
        setProfile(p);
        setEditPersonalForm(p);
      }
      if (houseRes.status === "fulfilled") {
        const h = extractList(houseRes.value);
        setHousehold(h);
      }
      if (teamRes.status === "fulfilled") {
        const t = teamRes.value?.data || teamRes.value;
        setCareTeam(t);
      }
      if (consentRes.status === "fulfilled") {
        const c = extractList(consentRes.value);
        setConsents(c);
      }
      if (abhaRes.status === "fulfilled") {
        setAbhaStatus(abhaRes.value?.data || abhaRes.value);
      }
    } catch (err: any) {
      console.error("Failed to load profile data", err);
      setErrorMsg("माहिती लोड करण्यात त्रुटी आली. कृपया पुन्हा प्रयत्न करा.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAllProfileData();
  }, [loadAllProfileData]);

  // Load specific member detail if in member subroute
  useEffect(() => {
    if (routeState.type === "household_member") {
      const memberId = routeState.memberId;
      apiClient.getCitizenHouseholdMemberDetail(memberId)
        .then((res: any) => {
          const m = res?.data || res;
          setSelectedMember(m);
          setEditMemberForm(m);
        })
        .catch((err: any) => {
          console.error("Failed to fetch member details", err);
          setErrorMsg("सदस्याची माहिती लोड करण्यात अडचण आली.");
        });
    }
  }, [routeState]);

  // 4. Handlers
  // A. Save Personal Information
  const handleSavePersonalInfo = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg(null);
    try {
      const updated = await apiClient.updateCitizenProfile({
        display_name: editPersonalForm.display_name,
        legal_name: editPersonalForm.legal_name,
        preferred_name: editPersonalForm.preferred_name,
        date_of_birth: editPersonalForm.date_of_birth,
        age: editPersonalForm.age ? parseInt(editPersonalForm.age) : undefined,
        sex: editPersonalForm.sex,
        phone: editPersonalForm.phone,
        alternate_phone: editPersonalForm.alternate_phone,
        emergency_contact_name: editPersonalForm.emergency_contact_name,
        emergency_contact_phone: editPersonalForm.emergency_contact_phone,
        emergency_contact_relation: editPersonalForm.emergency_contact_relation,
        address: editPersonalForm.address,
        current_care_location: editPersonalForm.current_care_location,
        village_name: editPersonalForm.village_name,
        gram_panchayat: editPersonalForm.gram_panchayat,
        block_taluka: editPersonalForm.block_taluka,
        district: editPersonalForm.district,
        state: editPersonalForm.state,
        pincode: editPersonalForm.pincode,
        blood_group: editPersonalForm.blood_group,
        is_pregnant: editPersonalForm.is_pregnant,
        gestational_weeks: editPersonalForm.gestational_weeks ? parseInt(editPersonalForm.gestational_weeks) : undefined
      });
      const data = updated?.data || updated;
      setProfile(data);
      showToast(t("profile.profile_saved_success", "प्रोफाईल यशस्वीपणे जतन करण्यात आले!"));
      loadAllProfileData();
      navigateTo({ type: "main" });
    } catch (err: any) {
      console.error("Failed to save personal profile", err);
      setErrorMsg(err?.message || "बदल जतन करताना त्रुटी आली. कृपया तपशील तपासा.");
    } finally {
      setSubmitting(false);
    }
  };

  // B. Add Household Member
  const handleAddHouseholdMember = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = addMemberForm.full_name.trim();
    if (!trimmedName) {
      setErrorMsg(t("profile.error_name_required", "कृपया सदस्याचे पूर्ण नाव टाका."));
      return;
    }

    const trimmedPhone = addMemberForm.phone.trim();
    if (trimmedPhone && !/^\d{10}$/.test(trimmedPhone)) {
      setErrorMsg(t("profile.error_phone_invalid", "कृपया वैध १० अंकी मोबाईल नंबर टाका किंवा रिकामा सोडा."));
      return;
    }

    let parsedAge: number | undefined = undefined;
    if (addMemberForm.age.trim()) {
      const a = parseInt(addMemberForm.age.trim(), 10);
      if (isNaN(a) || a < 0 || a > 125) {
        setErrorMsg(t("profile.error_age_invalid", "कृपया वैध वय (० ते १२५ वर्षे) टाका."));
        return;
      }
      parsedAge = a;
    }

    let parsedGestationalWeeks: number | undefined = undefined;
    if (addMemberForm.is_pregnant && addMemberForm.gestational_weeks.trim()) {
      const g = parseInt(addMemberForm.gestational_weeks.trim(), 10);
      if (!isNaN(g) && g >= 1 && g <= 44) {
        parsedGestationalWeeks = g;
      }
    }

    setSubmitting(true);
    setErrorMsg(null);
    try {
      const addRes = await apiClient.addCitizenHouseholdMember({
        full_name: trimmedName,
        relationship_type: addMemberForm.relationship_type,
        age: parsedAge,
        sex: addMemberForm.sex,
        phone: trimmedPhone || undefined,
        blood_group: addMemberForm.blood_group || undefined,
        is_pregnant: addMemberForm.is_pregnant,
        gestational_weeks: parsedGestationalWeeks,
        chronic_conditions: addMemberForm.chronic_conditions,
        health_notes: addMemberForm.health_notes.trim() || undefined,
        consent_obtained: true
      });

      const newMember = addRes?.data || addRes;
      if (newMember && (newMember.id || newMember.full_name)) {
        setHousehold(prev => [newMember, ...prev.filter(m => m.id !== newMember.id)]);
      }

      showToast(t("profile.member_added_success", "कुटुंबातील सदस्य यशस्वीपणे जोडला गेला!"));
      setAddMemberForm({
        full_name: "",
        relationship_type: "CHILD",
        age: "",
        sex: "Female",
        phone: "",
        blood_group: "O+",
        is_pregnant: false,
        gestational_weeks: "",
        chronic_conditions: [],
        health_notes: ""
      });
      await loadAllProfileData();
      refreshBeneficiaries().catch(() => {});
      navigateTo({ type: "household" });
    } catch (err: any) {
      console.error("Failed to add household member", err);
      const message = err?.response?.data?.detail || err?.message || t("profile.error_add_member", "सदस्य जोडताना त्रुटी आली.");
      setErrorMsg(typeof message === "string" ? message : JSON.stringify(message));
    } finally {
      setSubmitting(false);
    }
  };

  // C. Update Member
  const handleUpdateMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMember) return;
    setSubmitting(true);
    setErrorMsg(null);
    try {
      const res = await apiClient.updateCitizenHouseholdMember(selectedMember.id, {
        full_name: editMemberForm.full_name,
        relationship_type: editMemberForm.relationship_type,
        age: editMemberForm.age ? parseInt(editMemberForm.age) : undefined,
        sex: editMemberForm.sex,
        phone: editMemberForm.phone,
        blood_group: editMemberForm.blood_group,
        is_pregnant: editMemberForm.is_pregnant,
        gestational_weeks: editMemberForm.gestational_weeks ? parseInt(editMemberForm.gestational_weeks) : undefined,
        chronic_conditions: editMemberForm.chronic_conditions,
        health_notes: editMemberForm.health_notes
      });
      const updated = res?.data || res;
      setSelectedMember(updated);
      setIsEditingMember(false);
      showToast(t("profile.member_updated_success", "सदस्याची माहिती यशस्वीपणे अद्ययावत केली!"));
      loadAllProfileData();
      refreshBeneficiaries().catch(() => {});
    } catch (err: any) {
      console.error("Failed to update household member", err);
      setErrorMsg(err?.message || "माहिती अद्ययावत करताना त्रुटी आली.");
    } finally {
      setSubmitting(false);
    }
  };

  // D. Delete / Deactivate Member
  const handleDeleteMember = async (memberId: string) => {
    if (!window.confirm("आपण खात्रीने या सदस्याला कुटुंबातून काढू इच्छिता?")) return;
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await apiClient.deleteCitizenHouseholdMember(memberId);
      showToast(t("profile.member_deleted_success", "सदस्य यशस्वीपणे काढून टाकला."));
      await loadAllProfileData();
      refreshBeneficiaries().catch(() => {});
      navigateTo({ type: "household" });
    } catch (err: any) {
      console.error("Failed to remove household member", err);
      setErrorMsg(err?.message || "सदस्य काढताना त्रुटी आली.");
    } finally {
      setSubmitting(false);
    }
  };

  // E. Revoke Consent
  const handleRevokeConsent = async (consentId: string) => {
    setSubmitting(true);
    setErrorMsg(null);
    try {
      await apiClient.revokeCitizenConsent(consentId, "Revoked by citizen via Privacy Settings");
      showToast(t("profile.consent_revoked_success", "संमती यशस्वीपणे मागे घेण्यात आली."));
      loadAllProfileData();
    } catch (err: any) {
      console.error("Failed to revoke consent", err);
      setErrorMsg(err?.message || "संमती मागे घेताना त्रुटी आली.");
    } finally {
      setSubmitting(false);
    }
  };

  // F. Change Language Immediately
  const handleImmediateLanguageChange = async (newLang: LanguageCode) => {
    setSubmitting(true);
    try {
      await setLocale(newLang);
      LanguageService.saveLocalPreference(newLang);
      await LanguageService.syncPreferenceToBackend(newLang);
      showToast(t("citizen.language_changed_success", "Language changed successfully"));
    } catch (err) {
      console.error("Failed to persist language", err);
    } finally {
      setSubmitting(false);
    }
  };

  // -------------------------------------------------------------
  // VIEW RENDERERS
  // -------------------------------------------------------------

  // Render Skeleton Loader
  if (loading && !profile) {
    return (
      <div id="profile-loading-skeleton" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ height: 110, backgroundColor: "#E2E8F0", borderRadius: 20 }} />
        <div style={{ height: 260, backgroundColor: "#E2E8F0", borderRadius: 20 }} />
        <div style={{ height: 140, backgroundColor: "#E2E8F0", borderRadius: 20 }} />
      </div>
    );
  }

  // --- SUBVIEW 1: PERSONAL INFORMATION (VIEW & EDIT) ---
  if (routeState.type === "personal") {
    return (
      <div id="personal-info-view" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Header with Back */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            id="btn-back-to-main-profile"
            onClick={() => navigateTo({ type: "main" })}
            style={{ border: "none", background: "#F1F5F9", borderRadius: "50%", width: 38, height: 38, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}
            aria-label="Back to profile"
          >
            <ArrowLeft size={20} color="#334155" />
          </button>
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("profile.personal_info", "Personal Information")}
            </h2>
            <div style={{ fontSize: 12, color: "#64748B" }}>
              {t("profile.personal_info_desc", "Name, contact numbers, permanent and current address")}
            </div>
          </div>
        </div>

        {/* Edit Form */}
        <form onSubmit={handleSavePersonalInfo} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1.5px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", borderBottom: "1px solid #F1F5F9", paddingBottom: 6 }}>
              Identity & Details
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.legal_name", "Legal Name")}</label>
              <input
                id="input-legal-name"
                type="text"
                value={editPersonalForm.legal_name || ""}
                onChange={(e) => setEditPersonalForm({ ...editPersonalForm, legal_name: e.target.value, display_name: e.target.value })}
                required
                style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
              />
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.date_of_birth", "Date of Birth")}</label>
                <input
                  id="input-dob"
                  type="date"
                  value={editPersonalForm.date_of_birth || ""}
                  onChange={(e) => setEditPersonalForm({ ...editPersonalForm, date_of_birth: e.target.value })}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
              <div style={{ width: 100 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.age_years", "Age (Years)")}</label>
                <input
                  id="input-age"
                  type="number"
                  value={editPersonalForm.age || ""}
                  onChange={(e) => setEditPersonalForm({ ...editPersonalForm, age: e.target.value })}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.gender", "Gender")}</label>
                <select
                  id="select-gender"
                  value={editPersonalForm.sex || "Female"}
                  onChange={(e) => setEditPersonalForm({ ...editPersonalForm, sex: e.target.value })}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                >
                  <option value="Female">Female</option>
                  <option value="Male">Male</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.blood_group", "Blood Group")}</label>
                <select
                  id="select-blood-group"
                  value={editPersonalForm.blood_group || "O+"}
                  onChange={(e) => setEditPersonalForm({ ...editPersonalForm, blood_group: e.target.value })}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                >
                  {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((bg) => (
                    <option key={bg} value={bg}>{bg}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1.5px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", borderBottom: "1px solid #F1F5F9", paddingBottom: 6 }}>
              Contact & Emergency Information
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.phone", "Verified Phone Number")}</label>
              <input
                id="input-phone"
                type="tel"
                value={editPersonalForm.phone || ""}
                onChange={(e) => setEditPersonalForm({ ...editPersonalForm, phone: e.target.value })}
                required
                style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
              />
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.emergency_contact_person", "Emergency Contact Person")}</label>
                <input
                  id="input-emergency-name"
                  type="text"
                  value={editPersonalForm.emergency_contact_name || ""}
                  onChange={(e) => setEditPersonalForm({ ...editPersonalForm, emergency_contact_name: e.target.value })}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.emergency_contact_phone", "Emergency Contact Phone")}</label>
                <input
                  id="input-emergency-phone"
                  type="tel"
                  value={editPersonalForm.emergency_contact_phone || ""}
                  onChange={(e) => setEditPersonalForm({ ...editPersonalForm, emergency_contact_phone: e.target.value })}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
            </div>
          </div>

          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1.5px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", borderBottom: "1px solid #F1F5F9", paddingBottom: 6 }}>
              Address & Care Location
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.registered_address", "Registered Home Address")}</label>
              <textarea
                id="input-registered-address"
                rows={2}
                value={editPersonalForm.address || ""}
                onChange={(e) => setEditPersonalForm({ ...editPersonalForm, address: e.target.value })}
                style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
              />
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.current_care_location", "Current Care Location")}</label>
              <input
                id="input-current-care-location"
                type="text"
                value={editPersonalForm.current_care_location || ""}
                onChange={(e) => setEditPersonalForm({ ...editPersonalForm, current_care_location: e.target.value })}
                style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
              />
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.village", "Village")}</label>
                <input
                  id="input-village"
                  type="text"
                  value={editPersonalForm.village_name || ""}
                  onChange={(e) => setEditPersonalForm({ ...editPersonalForm, village_name: e.target.value })}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.block_taluka", "Block")}</label>
                <input
                  id="input-block"
                  type="text"
                  value={editPersonalForm.block_taluka || ""}
                  onChange={(e) => setEditPersonalForm({ ...editPersonalForm, block_taluka: e.target.value })}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.district", "District")}</label>
                <input
                  id="input-district"
                  type="text"
                  value={editPersonalForm.district || ""}
                  onChange={(e) => setEditPersonalForm({ ...editPersonalForm, district: e.target.value })}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
              <div style={{ width: 110 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.pincode", "PIN Code")}</label>
                <input
                  id="input-pincode"
                  type="text"
                  value={editPersonalForm.pincode || ""}
                  onChange={(e) => setEditPersonalForm({ ...editPersonalForm, pincode: e.target.value })}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
            </div>
          </div>

          <button
            id="btn-save-personal-info"
            type="submit"
            disabled={submitting}
            style={{
              backgroundColor: "#2563EB",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 14,
              padding: "14px",
              fontSize: 15,
              fontWeight: 800,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              minHeight: 48,
              boxShadow: "0 4px 12px rgba(37,99,235,0.25)"
            }}
          >
            {submitting ? <Loader2 className="animate-spin" size={20} /> : <Check size={20} />}
            {submitting ? t("profile.saving", "Saving...") : t("profile.save_profile", "Save Profile")}
          </button>
        </form>
      </div>
    );
  }

  // --- SUBVIEW 2: HOUSEHOLD DIRECTORY ---
  if (routeState.type === "household") {
    return (
      <div id="household-directory-view" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button
              id="btn-back-from-household"
              onClick={() => navigateTo({ type: "main" })}
              style={{ border: "none", background: "#F1F5F9", borderRadius: "50%", width: 38, height: 38, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}
              aria-label="Back to profile"
            >
              <ArrowLeft size={20} color="#334155" />
            </button>
            <div>
              <h2 style={{ fontSize: 17, fontWeight: 800, color: "#0F172A", margin: 0 }}>
                {t("profile.household_members", "Household Members")} ({household.length})
              </h2>
              <div style={{ fontSize: 12, color: "#64748B" }}>
                {t("profile.household_members_desc", "Family members linked to your healthcare record")}
              </div>
            </div>
          </div>

          <button
            id="btn-add-member-top"
            onClick={() => navigateTo({ type: "household_new" })}
            style={{
              backgroundColor: "#2563EB",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 12,
              padding: "8px 14px",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              minHeight: 40
            }}
          >
            <Plus size={16} /> {t("profile.add_member", "Add Member")}
          </button>
        </div>

        {/* Error Banner inside Household Directory */}
        {errorMsg && (
          <div
            id="household-dir-error-banner"
            style={{
              backgroundColor: "#FEF2F2",
              border: "1.5px solid #FCA5A5",
              borderRadius: 14,
              padding: "12px 14px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              color: "#991B1B",
              fontSize: 13,
              fontWeight: 600
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <AlertTriangle size={18} color="#DC2626" />
              <span>{errorMsg}</span>
            </div>
            <button
              onClick={() => setErrorMsg(null)}
              style={{ border: "none", background: "transparent", color: "#991B1B", cursor: "pointer", padding: 4 }}
              aria-label="Dismiss error"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {/* Members Cards List */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {household.map((m) => (
            <div
              key={m.id}
              id={`household-member-card-${m.id}`}
              onClick={() => navigateTo({ type: "household_member", memberId: m.id })}
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: 16,
                border: "1.5px solid #E2E8F0",
                padding: "16px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                cursor: "pointer",
                boxShadow: "0 2px 6px rgba(0,0,0,0.03)"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 44, height: 44, borderRadius: "50%", backgroundColor: m.relationship_type === "SELF" ? "#DBEAFE" : "#F1F5F9", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>
                  {m.relationship_type === "SELF" ? "👩" : m.relationship_type === "CHILD" ? "👶" : "👤"}
                </div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>
                    {m.full_name}
                  </div>
                  <div style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>
                    {m.relationship_type} • {m.age ? `${m.age} yrs` : "Age not specified"} • {m.sex || "Female"}
                  </div>
                  {m.is_pregnant && (
                    <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 6px", borderRadius: 6, backgroundColor: "#FCE7F3", color: "#BE185D", marginTop: 4, display: "inline-block" }}>
                      🤰 {m.gestational_weeks ? `${m.gestational_weeks} wks pregnant` : "Pregnant"}
                    </span>
                  )}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <ChevronRight size={18} color="#94A3B8" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // --- SUBVIEW 3: ADD HOUSEHOLD MEMBER FORM ---
  if (routeState.type === "household_new") {
    return (
      <div id="add-household-member-view" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            id="btn-back-from-add-member"
            onClick={() => {
              setErrorMsg(null);
              navigateTo({ type: "household" });
            }}
            style={{ border: "none", background: "#F1F5F9", borderRadius: "50%", width: 38, height: 38, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}
            aria-label="Back to household"
          >
            <ArrowLeft size={20} color="#334155" />
          </button>
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("profile.add_member", "Add Household Member")}
            </h2>
            <div style={{ fontSize: 12, color: "#64748B" }}>
              Fill details to link new family member to health record
            </div>
          </div>
        </div>

        {/* Error Banner inside Add Member Form */}
        {errorMsg && (
          <div
            id="add-member-error-banner"
            style={{
              backgroundColor: "#FEF2F2",
              border: "1.5px solid #FCA5A5",
              borderRadius: 14,
              padding: "12px 14px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              color: "#991B1B",
              fontSize: 13,
              fontWeight: 600
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <AlertTriangle size={18} color="#DC2626" />
              <span>{errorMsg}</span>
            </div>
            <button
              onClick={() => setErrorMsg(null)}
              style={{ border: "none", background: "transparent", color: "#991B1B", cursor: "pointer", padding: 4 }}
              aria-label="Dismiss error"
            >
              <X size={16} />
            </button>
          </div>
        )}

        <form onSubmit={handleAddHouseholdMember} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1.5px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.legal_name", "Full Name *")}</label>
              <input
                id="input-new-member-name"
                type="text"
                placeholder="e.g. Rahul or Kamla Devi"
                value={addMemberForm.full_name}
                onChange={(e) => setAddMemberForm({ ...addMemberForm, full_name: e.target.value })}
                required
                disabled={submitting}
                style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
              />
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.relationship", "Relationship *")}</label>
                <select
                  id="select-new-member-relation"
                  value={addMemberForm.relationship_type}
                  onChange={(e) => setAddMemberForm({ ...addMemberForm, relationship_type: e.target.value })}
                  disabled={submitting}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                >
                  <option value="CHILD">Child</option>
                  <option value="SPOUSE">Spouse</option>
                  <option value="MOTHER">Mother</option>
                  <option value="FATHER">Father</option>
                  <option value="PARENT">Parent</option>
                  <option value="ELDER">Elder</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              <div style={{ width: 100 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.age_years", "Age (Years)")}</label>
                <input
                  id="input-new-member-age"
                  type="number"
                  placeholder="e.g. 8"
                  value={addMemberForm.age}
                  onChange={(e) => setAddMemberForm({ ...addMemberForm, age: e.target.value })}
                  disabled={submitting}
                  min={0}
                  max={125}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                />
              </div>
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.gender", "Gender")}</label>
                <select
                  id="select-new-member-gender"
                  value={addMemberForm.sex}
                  onChange={(e) => setAddMemberForm({ ...addMemberForm, sex: e.target.value })}
                  disabled={submitting}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                >
                  <option value="Female">Female</option>
                  <option value="Male">Male</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.blood_group", "Blood Group")}</label>
                <select
                  id="select-new-member-blood-group"
                  value={addMemberForm.blood_group}
                  onChange={(e) => setAddMemberForm({ ...addMemberForm, blood_group: e.target.value })}
                  disabled={submitting}
                  style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
                >
                  {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map((bg) => (
                    <option key={bg} value={bg}>{bg}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.phone", "Phone (if available)")}</label>
              <input
                id="input-new-member-phone"
                type="tel"
                placeholder="10-digit mobile"
                value={addMemberForm.phone}
                onChange={(e) => setAddMemberForm({ ...addMemberForm, phone: e.target.value })}
                disabled={submitting}
                maxLength={10}
                style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
              />
            </div>

            <div>
              <label style={{ fontSize: 12, fontWeight: 700, color: "#475569" }}>{t("profile.health_notes", "Health Context / Notes")}</label>
              <textarea
                id="input-new-member-health-notes"
                rows={2}
                placeholder="e.g. Immunization up to date / Routine checkups"
                value={addMemberForm.health_notes}
                onChange={(e) => setAddMemberForm({ ...addMemberForm, health_notes: e.target.value })}
                disabled={submitting}
                style={{ width: "100%", padding: "10px 12px", borderRadius: 10, border: "1.5px solid #CBD5E1", fontSize: 13, marginTop: 4, boxSizing: "border-box" }}
              />
            </div>
          </div>

          <button
            id="btn-submit-new-member"
            type="submit"
            disabled={submitting}
            style={{
              backgroundColor: submitting ? "#93C5FD" : "#2563EB",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 14,
              padding: "14px",
              fontSize: 15,
              fontWeight: 800,
              cursor: submitting ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              minHeight: 48,
              boxShadow: "0 4px 12px rgba(37,99,235,0.25)"
            }}
          >
            {submitting ? <Loader2 className="animate-spin" size={20} /> : <Plus size={20} />}
            {submitting ? "Registering member..." : t("profile.add_member", "Add Member")}
          </button>
        </form>
      </div>
    );
  }

  // --- SUBVIEW 4: MEMBER DETAIL & ACTIONS ---
  if (routeState.type === "household_member" && selectedMember) {
    return (
      <div id="household-member-detail-view" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button
              id="btn-back-from-member-detail"
              onClick={() => navigateTo({ type: "household" })}
              style={{ border: "none", background: "#F1F5F9", borderRadius: "50%", width: 38, height: 38, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}
              aria-label="Back to household"
            >
              <ArrowLeft size={20} color="#334155" />
            </button>
            <div>
              <h2 style={{ fontSize: 17, fontWeight: 800, color: "#0F172A", margin: 0 }}>
                {selectedMember.full_name}
              </h2>
              <div style={{ fontSize: 12, color: "#64748B" }}>
                {selectedMember.relationship_type} • {selectedMember.age || "?"} yrs
              </div>
            </div>
          </div>

          <button
            id="btn-edit-member-toggle"
            onClick={() => setIsEditingMember(!isEditingMember)}
            style={{ border: "none", background: "#EFF6FF", color: "#2563EB", padding: "8px 12px", borderRadius: 10, fontSize: 12, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
          >
            <Edit3 size={14} /> {isEditingMember ? "Cancel" : t("profile.edit_member", "Edit")}
          </button>
        </div>

        {/* Member Profile Card */}
        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 18, border: "1.5px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ width: 56, height: 56, borderRadius: "50%", backgroundColor: "#DBEAFE", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 26 }}>
              👤
            </div>
            <div>
              <div style={{ fontSize: 17, fontWeight: 800, color: "#0F172A" }}>{selectedMember.full_name}</div>
              <div style={{ fontSize: 12, color: "#64748B" }}>Relation: {selectedMember.relationship_type}</div>
              <div style={{ fontSize: 12, color: "#64748B" }}>Blood Group: {selectedMember.blood_group || "Not specified"}</div>
            </div>
          </div>

          {selectedMember.health_notes && (
            <div style={{ backgroundColor: "#F8FAFC", borderRadius: 12, padding: "10px 12px", fontSize: 12, color: "#334155", border: "1px solid #E2E8F0" }}>
              <strong>Health Notes:</strong> {selectedMember.health_notes}
            </div>
          )}
        </div>

        {/* 5 Member Actions */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {/* Action 1: Select as beneficiary for Speak to Doctor */}
          <button
            id="btn-member-speak-to-doctor"
            onClick={() => {
              if (onNavigateToTab) onNavigateToTab("doctor");
            }}
            style={{
              backgroundColor: "#2563EB",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 14,
              padding: "14px",
              fontSize: 14,
              fontWeight: 800,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              minHeight: 48
            }}
          >
            <Stethoscope size={18} /> {t("profile.request_care", "Speak to Doctor for this Member")}
          </button>

          {/* Action 2: Check Schemes for Member */}
          <button
            id="btn-member-check-schemes"
            onClick={() => {
              if (onNavigateToTab) onNavigateToTab("schemes");
            }}
            style={{
              backgroundColor: "#059669",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 14,
              padding: "14px",
              fontSize: 14,
              fontWeight: 800,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              minHeight: 48
            }}
          >
            <Award size={18} /> {t("profile.check_schemes", "Check Scheme Eligibility")}
          </button>

          {/* Action 3: View Care History */}
          <button
            id="btn-member-view-care-history"
            onClick={() => {
              if (onNavigateToTab) onNavigateToTab("care");
            }}
            style={{
              backgroundColor: "#FFFFFF",
              color: "#1E293B",
              border: "1.5px solid #CBD5E1",
              borderRadius: 14,
              padding: "14px",
              fontSize: 14,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              minHeight: 48
            }}
          >
            <HeartPulse size={18} color="#2563EB" /> {t("profile.view_care_history", "View Care History")}
          </button>

          {/* Action 4: Delete / Remove Member */}
          {selectedMember.relationship_type !== "SELF" && (
            <button
              id="btn-delete-household-member"
              onClick={() => handleDeleteMember(selectedMember.id)}
              disabled={submitting}
              style={{
                backgroundColor: "#FEF2F2",
                color: "#DC2626",
                border: "1.5px solid #FCA5A5",
                borderRadius: 14,
                padding: "12px",
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                marginTop: 6,
                minHeight: 44
              }}
            >
              <Trash2 size={16} /> {t("profile.delete_member", "Remove Member from Household")}
            </button>
          )}
        </div>
      </div>
    );
  }

  // --- SUBVIEW 5: ASSIGNED CARE TEAM ---
  if (routeState.type === "care_team") {
    const asha = careTeam?.assigned_asha || {
      id: "ASHA-012",
      name: "Sita Patel",
      designation: "Assigned ASHA Community Health Worker",
      facility_name: "Kalyanpur Gram Panchayat Health Post",
      phone: "9823012345",
      operating_hours: "Mon - Sat: 8:00 AM - 5:00 PM"
    };
    const phc = careTeam?.assigned_phc || {
      id: "PHC-09",
      name: "Kalyanpur Primary Health Centre (PHC)",
      designation: "Government PHC Facility",
      facility_name: "Kalyanpur Primary Health Centre",
      address: "Main Road, Kalyanpur Village",
      phone: "020-25678901",
      operating_hours: "24x7 Emergency • OPD 9:00 AM - 4:00 PM"
    };
    const doc = careTeam?.assigned_doctor || {
      id: "DOC-001",
      name: "Dr. Abhinav Sharma",
      designation: "Medical Officer (MBBS)",
      facility_name: "Kalyanpur PHC OPD 1",
      phone: "020-25678902",
      operating_hours: "Mon - Sat: 9:00 AM - 2:00 PM"
    };

    return (
      <div id="care-team-view" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            id="btn-back-from-care-team"
            onClick={() => navigateTo({ type: "main" })}
            style={{ border: "none", background: "#F1F5F9", borderRadius: "50%", width: 38, height: 38, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}
            aria-label="Back to profile"
          >
            <ArrowLeft size={20} color="#334155" />
          </button>
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("profile.care_team", "Your Assigned Care Team")}
            </h2>
            <div style={{ fontSize: 12, color: "#64748B" }}>
              Verified healthcare support assigned to your village area
            </div>
          </div>
        </div>

        {/* 1. ASHA Worker Card */}
        {asha && (
          <div id="care-team-asha-card" style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1.5px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ display: "flex", gap: 12 }}>
                <div style={{ width: 44, height: 44, borderRadius: "50%", backgroundColor: "#FCE7F3", color: "#BE185D", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>
                  👩‍⚕️
                </div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>{asha.name}</div>
                  <div style={{ fontSize: 12, color: "#475569" }}>{asha.designation}</div>
                  <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>{asha.facility_name}</div>
                </div>
              </div>
              <span style={{ fontSize: 11, fontWeight: 800, backgroundColor: "#DCFCE7", color: "#166534", padding: "3px 8px", borderRadius: 6 }}>
                ✓ Verified
              </span>
            </div>

            <div style={{ fontSize: 12, color: "#64748B" }}>Hours: {asha.operating_hours}</div>

            <a
              id="btn-call-assigned-asha"
              href={`tel:${asha.phone || "9876543210"}`}
              style={{
                backgroundColor: "#BE185D",
                color: "#FFFFFF",
                textDecoration: "none",
                borderRadius: 12,
                padding: "10px",
                fontSize: 13,
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
                minHeight: 44
              }}
            >
              <Phone size={16} /> Call ASHA ({asha.phone || "9876543210"})
            </a>
          </div>
        )}

        {/* 2. Primary Health Centre Card */}
        {phc && (
          <div id="care-team-phc-card" style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1.5px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ display: "flex", gap: 12 }}>
                <div style={{ width: 44, height: 44, borderRadius: "50%", backgroundColor: "#DBEAFE", color: "#1D4ED8", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>
                  🏥
                </div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>{phc.name}</div>
                  <div style={{ fontSize: 12, color: "#475569" }}>{phc.designation}</div>
                  <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>{phc.address}</div>
                </div>
              </div>
              <span style={{ fontSize: 11, fontWeight: 800, backgroundColor: "#DCFCE7", color: "#166534", padding: "3px 8px", borderRadius: 6 }}>
                24x7 Emergency
              </span>
            </div>

            <div style={{ fontSize: 12, color: "#64748B" }}>Hours: {phc.operating_hours}</div>

            <a
              id="btn-call-assigned-phc"
              href={`tel:${phc.phone || "020-25678901"}`}
              style={{
                backgroundColor: "#1D4ED8",
                color: "#FFFFFF",
                textDecoration: "none",
                borderRadius: 12,
                padding: "10px",
                fontSize: 13,
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
                minHeight: 44
              }}
            >
              <Phone size={16} /> Call Health Centre ({phc.phone || "020-25678901"})
            </a>
          </div>
        )}

        {/* 3. Assigned Medical Officer */}
        {doc && (
          <div id="care-team-doctor-card" style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1.5px solid #E2E8F0", display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ display: "flex", gap: 12 }}>
                <div style={{ width: 44, height: 44, borderRadius: "50%", backgroundColor: "#E0E7FF", color: "#4338CA", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>
                  👨‍⚕️
                </div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>{doc.name}</div>
                  <div style={{ fontSize: 12, color: "#475569" }}>{doc.designation}</div>
                  <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>{doc.facility_name}</div>
                </div>
              </div>
              <span style={{ fontSize: 11, fontWeight: 800, backgroundColor: "#DCFCE7", color: "#166534", padding: "3px 8px", borderRadius: 6 }}>
                ✓ Medical Officer
              </span>
            </div>

            <div style={{ fontSize: 12, color: "#64748B" }}>Hours: {doc.operating_hours}</div>

            <button
              id="btn-doctor-teleconsult"
              onClick={() => {
                if (onNavigateToTab) onNavigateToTab("doctor");
              }}
              style={{
                backgroundColor: "#4338CA",
                color: "#FFFFFF",
                border: "none",
                borderRadius: 12,
                padding: "10px",
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
                minHeight: 44
              }}
            >
              <Stethoscope size={16} /> Consult Doctor Directly
            </button>
          </div>
        )}
      </div>
    );
  }

  // --- SUBVIEW 6: EMERGENCY 108 HELP ---
  if (routeState.type === "emergency") {
    return (
      <div id="emergency-help-view" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            id="btn-back-from-emergency"
            onClick={() => navigateTo({ type: "main" })}
            style={{ border: "none", background: "#F1F5F9", borderRadius: "50%", width: 38, height: 38, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}
            aria-label="Back to profile"
          >
            <ArrowLeft size={20} color="#334155" />
          </button>
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 800, color: "#DC2626", margin: 0 }}>
              {t("profile.emergency_help_title", "Emergency Medical Help (108)")}
            </h2>
            <div style={{ fontSize: 12, color: "#64748B" }}>
              Direct national ambulance dispatch & emergency response
            </div>
          </div>
        </div>

        <div style={{ backgroundColor: "#FEF2F2", border: "1.5px solid #FCA5A5", borderRadius: 18, padding: 18, display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: "#991B1B" }}>
            For critical medical emergency, severe bleeding, or chest pain:
          </div>
          <div style={{ fontSize: 13, color: "#7F1D1D", lineHeight: 1.5 }}>
            Immediate call directly dispatches 108 government emergency ambulance services to your registered or GPS location.
          </div>

          <a
            id="btn-call-108-ambulance"
            href="tel:108"
            style={{
              backgroundColor: "#DC2626",
              color: "#FFFFFF",
              textDecoration: "none",
              borderRadius: 16,
              padding: "16px",
              fontSize: 18,
              fontWeight: 800,
              textAlign: "center",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 10,
              boxShadow: "0 6px 20px rgba(220,38,38,0.35)",
              minHeight: 52
            }}
          >
            <Phone size={22} /> Call 108 Ambulance (Urgent)
          </a>
        </div>

        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 16, border: "1px solid #E2E8F0", padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 800, color: "#0F172A" }}>Other Emergency Helplines:</div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#475569" }}>
            <span>Women Helpline:</span> <strong>1091</strong>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#475569" }}>
            <span>National Health Helpline:</span> <strong>104</strong>
          </div>
        </div>
      </div>
    );
  }

  // --- SUBVIEW 7: LANGUAGE SELECTION ---
  if (routeState.type === "language") {
    const languages: { code: LanguageCode; name: string; nativeName: string; region: string }[] = [
      { code: "mr-IN", name: "Marathi", nativeName: "मराठी", region: "Maharashtra" },
      { code: "hi-IN", name: "Hindi", nativeName: "हिन्दी", region: "National" },
      { code: "en-IN", name: "English", nativeName: "English", region: "National" },
      { code: "gu-IN", name: "Gujarati", nativeName: "ગુજરાતી", region: "Gujarat" },
      { code: "bn-IN", name: "Bengali", nativeName: "বাংলা", region: "West Bengal" },
      { code: "kn-IN", name: "Kannada", nativeName: "ಕನ್ನಡ", region: "Karnataka" },
      { code: "te-IN", name: "Telugu", nativeName: "తెలుగు", region: "Andhra Pradesh / Telangana" },
      { code: "ta-IN", name: "Tamil", nativeName: "தமிழ்", region: "Tamil Nadu" },
      { code: "ml-IN", name: "Malayalam", nativeName: "മലയാളം", region: "Kerala" },
      { code: "pa-IN", name: "Punjabi", nativeName: "ਪੰਜਾਬੀ", region: "Punjab" },
      { code: "od-IN", name: "Odia", nativeName: "ଓଡ଼ିଆ", region: "Odisha" },
    ];

    return (
      <div id="language-selection-view" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            id="btn-back-from-language"
            onClick={() => navigateTo({ type: "main" })}
            style={{ border: "none", background: "#F1F5F9", borderRadius: "50%", width: 38, height: 38, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}
            aria-label="Back to profile"
          >
            <ArrowLeft size={20} color="#334155" />
          </button>
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("profile.change_language", "Change Language")}
            </h2>
            <div style={{ fontSize: 12, color: "#64748B" }}>
              {t("profile.change_language_desc", "Switch language immediately for the entire application")}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {languages.map((l) => {
            const isSelected = locale === l.code;
            return (
              <button
                key={l.code}
                id={`btn-lang-${l.code}`}
                onClick={() => handleImmediateLanguageChange(l.code)}
                disabled={submitting}
                style={{
                  width: "100%",
                  padding: "16px",
                  borderRadius: 16,
                  border: `2px solid ${isSelected ? "#2563EB" : "#E2E8F0"}`,
                  backgroundColor: isSelected ? "#EFF6FF" : "#FFFFFF",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  cursor: "pointer",
                  textAlign: "left",
                  minHeight: 52
                }}
              >
                <div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: isSelected ? "#1E40AF" : "#0F172A" }}>
                    {l.nativeName}
                  </div>
                  <div style={{ fontSize: 12, color: "#64748B" }}>
                    {l.name} • {l.region}
                  </div>
                </div>

                {isSelected && (
                  <div style={{ width: 26, height: 26, borderRadius: "50%", backgroundColor: "#2563EB", color: "#FFF", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Check size={16} />
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  // --- SUBVIEW 8: CONSENT & PRIVACY AUDIT ---
  if (routeState.type === "consent_privacy") {
    return (
      <div id="consent-privacy-view" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            id="btn-back-from-consents"
            onClick={() => navigateTo({ type: "main" })}
            style={{ border: "none", background: "#F1F5F9", borderRadius: "50%", width: 38, height: 38, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}
            aria-label="Back to profile"
          >
            <ArrowLeft size={20} color="#334155" />
          </button>
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 800, color: "#0F172A", margin: 0 }}>
              {t("profile.consent_privacy", "Consent & Privacy")}
            </h2>
            <div style={{ fontSize: 12, color: "#64748B" }}>
              {t("profile.consent_privacy_desc", "Review and manage data sharing records & legal audit trail")}
            </div>
          </div>
        </div>

        {/* DPDP Notice */}
        <div style={{ backgroundColor: "#F0FDF4", border: "1.5px solid #BBF7D0", borderRadius: 16, padding: 14, fontSize: 12, color: "#166534", lineHeight: 1.4 }}>
          🛡️ {t("profile.legal_audit_notice", "Consents are recorded in an immutable legal audit log complying with Digital Personal Data Protection (DPDP) Act.")}
        </div>

        {/* Consents List */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {consents.map((c) => (
            <div
              key={c.id}
              id={`consent-record-card-${c.id}`}
              style={{
                backgroundColor: "#FFFFFF",
                borderRadius: 16,
                border: `1.5px solid ${c.is_revoked ? "#E2E8F0" : "#BFDBFE"}`,
                padding: "16px",
                display: "flex",
                flexDirection: "column",
                gap: 10
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: "#0F172A" }}>
                    {c.purpose_label || c.purpose}
                  </div>
                  <div style={{ fontSize: 12, color: "#475569", marginTop: 2 }}>
                    Recipient: <strong>{c.recipient_name || c.recipient_role}</strong>
                  </div>
                </div>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 800,
                    backgroundColor: c.is_revoked ? "#FEE2E2" : "#DCFCE7",
                    color: c.is_revoked ? "#991B1B" : "#166534",
                    padding: "3px 8px",
                    borderRadius: 6
                  }}
                >
                  {c.is_revoked ? "Revoked" : "Active"}
                </span>
              </div>

              <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.4 }}>
                {c.consent_text || "Clinical assessment, records sharing and doctor review."}
              </div>

              <div style={{ fontSize: 11, color: "#94A3B8", display: "flex", justifyContent: "space-between" }}>
                <span>Date: {c.consented_at ? new Date(c.consented_at).toLocaleDateString() : ""}</span>
                <span>Policy: {c.policy_version}</span>
              </div>

              {c.can_revoke && (
                <button
                  id={`btn-revoke-consent-${c.id}`}
                  onClick={() => handleRevokeConsent(c.id)}
                  disabled={submitting}
                  style={{
                    backgroundColor: "#FEF2F2",
                    color: "#DC2626",
                    border: "1.5px solid #FCA5A5",
                    borderRadius: 10,
                    padding: "8px 12px",
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                    alignSelf: "flex-start",
                    marginTop: 4,
                    minHeight: 40
                  }}
                >
                  {t("profile.revoke_consent", "Revoke Consent")}
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // --- SUBVIEW 0: MAIN PROFILE MENU SCREEN ---
  const membersPreview = household.slice(0, 3);
  const abhaLabel = abhaStatus?.status_label || (profile?.abha_reference ? "ABHA Linked (Sandbox)" : "ABHA Not Linked");
  const abhaBadgeBg = abhaStatus?.status === "VERIFIED_SANDBOX" ? "#EFF6FF" : abhaStatus?.status === "LINKED_UNVERIFIED" ? "#FEF3C7" : "#F1F5F9";
  const abhaBadgeColor = abhaStatus?.status === "VERIFIED_SANDBOX" ? "#1D4ED8" : abhaStatus?.status === "LINKED_UNVERIFIED" ? "#92400E" : "#475569";

  return (
    <div id="citizen-profile-main-view" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Toast Notification */}
      {successMsg && (
        <div
          id="profile-toast-feedback"
          style={{
            position: "fixed",
            top: 20,
            left: "50%",
            transform: "translateX(-50%)",
            backgroundColor: "#15803D",
            color: "#FFFFFF",
            padding: "12px 20px",
            borderRadius: 20,
            fontSize: 13,
            fontWeight: 800,
            boxShadow: "0 8px 24px rgba(0,0,0,0.25)",
            zIndex: 9999
          }}
        >
          {successMsg}
        </div>
      )}

      {/* Global Error Banner with Retry */}
      {errorMsg && (
        <div
          id="profile-error-banner"
          style={{
            backgroundColor: "#FEF2F2",
            border: "1.5px solid #FCA5A5",
            borderRadius: 14,
            padding: "12px 14px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            color: "#991B1B",
            fontSize: 13,
            fontWeight: 600
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <AlertTriangle size={18} color="#DC2626" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => loadAllProfileData()}
            style={{ border: "none", background: "#DC2626", color: "#FFF", borderRadius: 8, padding: "6px 10px", fontSize: 12, fontWeight: 700, cursor: "pointer" }}
          >
            {t("common.retry", "Retry")}
          </button>
        </div>
      )}

      {/* Profile Header Hero Card */}
      <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 18, border: "1.5px solid #E2E8F0", boxShadow: "0 4px 14px rgba(0,0,0,0.04)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 64, height: 64, borderRadius: "50%", backgroundColor: "#DBEAFE", border: "2.5px solid #2563EB", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 32 }}>
            👩
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: "#0F172A" }}>
              {profile?.display_name || user?.name || "Citizen"}
            </div>
            <div style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>
              {profile?.village_name || "Kalyanpur"}, {profile?.district || "District 04"}
            </div>
            <span
              id="badge-abha-link-status"
              style={{
                fontSize: 11,
                fontWeight: 700,
                padding: "3px 8px",
                borderRadius: 8,
                backgroundColor: abhaBadgeBg,
                color: abhaBadgeColor,
                marginTop: 6,
                display: "inline-block"
              }}
            >
              {abhaLabel}
            </span>
          </div>
        </div>
      </div>

      {/* 6 Real Accessible Menu Rows */}
      <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, border: "1.5px solid #E2E8F0", overflow: "hidden" }}>
        {[
          {
            id: "btn-menu-personal-info",
            icon: <User size={18} color="#2563EB" />,
            title: t("profile.personal_info", "Personal Information"),
            desc: profile?.phone || "View and update details",
            action: () => navigateTo({ type: "personal" })
          },
          {
            id: "btn-menu-household-members",
            icon: <Users size={18} color="#2563EB" />,
            title: t("profile.household_members", "Household Members"),
            badge: `${household.length}`,
            desc: "Family healthcare registry",
            action: () => navigateTo({ type: "household" })
          },
          {
            id: "btn-menu-care-team",
            icon: <ShieldCheck size={18} color="#2563EB" />,
            title: t("profile.care_team", "Assigned Care Team"),
            desc: "ASHA worker & Primary Health Centre",
            action: () => navigateTo({ type: "care_team" })
          },
          {
            id: "btn-menu-emergency-help",
            icon: <Phone size={18} color="#DC2626" />,
            title: `${t("profile.emergency_help_title", "Emergency Medical Help")} (108)`,
            desc: "Immediate 108 ambulance dispatch",
            action: () => navigateTo({ type: "emergency" })
          },
          {
            id: "btn-menu-change-language",
            icon: <Globe size={18} color="#2563EB" />,
            title: `${t("profile.change_language", "Change Language")} (${getLanguageBadgeLabel(locale)})`,
            desc: "Switch whole application language",
            action: () => navigateTo({ type: "language" })
          },
          {
            id: "btn-menu-consent-privacy",
            icon: <Shield size={18} color="#2563EB" />,
            title: t("profile.consent_privacy", "Consent & Privacy"),
            desc: "DPDP legal audit trail & data sharing",
            action: () => navigateTo({ type: "consent_privacy" })
          }
        ].map((item, idx) => (
          <button
            key={item.id}
            id={item.id}
            onClick={item.action}
            style={{
              width: "100%",
              padding: "16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              border: "none",
              borderBottom: idx < 5 ? "1px solid #F1F5F9" : "none",
              backgroundColor: "#FFFFFF",
              cursor: "pointer",
              textAlign: "left",
              minHeight: 48
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, backgroundColor: "#F8FAFC", display: "flex", alignItems: "center", justifyContent: "center" }}>
                {item.icon}
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#1E293B" }}>{item.title}</div>
                <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>{item.desc}</div>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {item.badge && (
                <span style={{ width: 24, height: 24, borderRadius: "50%", backgroundColor: "#EFF6FF", color: "#1D4ED8", fontSize: 12, fontWeight: 800, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {item.badge}
                </span>
              )}
              <ChevronRight size={18} color="#94A3B8" />
            </div>
          </button>
        ))}
      </div>

      {/* Household Preview (Max 3 Preview + View All) */}
      <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1.5px solid #E2E8F0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B" }}>
            {t("profile.household_members", "Household Members")} ({household.length})
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <button
              id="btn-view-all-household"
              onClick={() => navigateTo({ type: "household" })}
              style={{ border: "none", background: "transparent", color: "#2563EB", fontSize: 12, fontWeight: 700, cursor: "pointer" }}
            >
              {t("profile.view_all", "View All")}
            </button>
            <button
              id="btn-add-household-member-preview"
              onClick={() => navigateTo({ type: "household_new" })}
              style={{ border: "none", background: "transparent", color: "#2563EB", fontSize: 12, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
            >
              <Plus size={14} /> {t("profile.add_member", "Add Member")}
            </button>
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, overflowX: "auto" }}>
          {membersPreview.map((m) => (
            <div
              key={m.id}
              id={`preview-household-card-${m.id}`}
              onClick={() => navigateTo({ type: "household_member", memberId: m.id })}
              style={{
                minWidth: 110,
                backgroundColor: "#F8FAFC",
                borderRadius: 14,
                padding: 12,
                border: "1px solid #E2E8F0",
                textAlign: "center",
                cursor: "pointer"
              }}
            >
              <div style={{ fontSize: 24, marginBottom: 4 }}>
                {m.relationship_type === "SELF" ? "👩" : m.relationship_type === "CHILD" ? "👶" : "👤"}
              </div>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#0F172A", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {m.full_name}
              </div>
              <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
                {m.relationship_type} • {m.age || "?"} yrs
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
