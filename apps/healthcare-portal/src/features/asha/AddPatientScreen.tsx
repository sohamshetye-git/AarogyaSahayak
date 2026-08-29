import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { db, PatientDraft, getDeviceId } from "../../db/offlineDb";
import { connectivityService } from "../../services/ConnectivityService";
import { ashaSyncService } from "../../services/AshaSyncService";
import {
  UserPlusIcon,
  CheckCircleIcon,
  ChevronLeftIcon,
  MicIcon,
  WarningIcon,
  HospitalIcon,
  PillIcon,
  StethoscopeIcon
} from "../../components/Icons";

const WIZARD_STEPS = [
  { id: 1, name: "Identity & Location" },
  { id: 2, name: "Household & Consent" },
  { id: 3, name: "Health Profile" },
  { id: 4, name: "Health Concern" },
  { id: 5, name: "Vitals & Special Conditions" },
  { id: 6, name: "Follow-up & Referral" },
  { id: 7, name: "Documents & Submit" }
];

export function AddPatientScreen() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [clientRegId] = useState(() => `REG-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`);
  
  // Options state
  const [options, setOptions] = useState<any>({
    states: ["Maharashtra"],
    districts: ["District 04"],
    blocks: ["Kalyanpur Block"],
    villages: [{ id: "v-01", name: "Kalyanpur" }],
    facilities: [{ id: "PHC-09", name: "Kalyanpur PHC", facility_type: "PHC", approx_distance_km: 3.5 }],
    sub_centers: [{ id: "sc-01", name: "Kalyanpur Sub-Centre" }],
    symptoms: [],
    blood_groups: ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "UNKNOWN"],
    household_categories: ["PRIORITY", "BPL", "ANTYODAYA", "OTHER", "UNKNOWN"],
    ration_card_categories: ["YELLOW", "ORANGE", "WHITE", "NONE"],
    special_conditions: [],
    languages: [{ code: "mr-IN", label: "मराठी" }, { code: "hi-IN", label: "हिंदी" }, { code: "en-IN", label: "English" }]
  });

  // Duplicate Check Modal state
  const [duplicateModalOpen, setDuplicateModalOpen] = useState(false);
  const [potentialDuplicates, setPotentialDuplicates] = useState<any[]>([]);
  const [duplicateOverrideReason, setDuplicateOverrideReason] = useState("");

  // Voice capture modal state
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);
  const [voiceFieldContext, setVoiceFieldContext] = useState("ALL");
  const [isRecording, setIsRecording] = useState(false);
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const [voiceExtractedFields, setVoiceExtractedFields] = useState<any>(null);
  const [voiceWarnings, setVoiceWarnings] = useState<string[]>([]);
  const [voiceConfirmed, setVoiceConfirmed] = useState(false);
  const [voiceProviderState, setVoiceProviderState] = useState<string>("Checking...");

  // Success summary modal
  const [successData, setSuccessData] = useState<any>(null);
  const [isOfflineSaved, setIsOfflineSaved] = useState(false);
  const [unsavedWarning, setUnsavedWarning] = useState(false);

  // Main Form Data State - Strictly Initialized Empty / Unchecked
  const [formData, setFormData] = useState<any>({
    // Step 1: Identity & Location
    full_name: "",
    date_of_birth: "",
    exact_dob_unknown: false,
    approximate_age: "",
    sex: "FEMALE",
    phone: "",
    alternate_phone: "",
    preferred_contact_method: "PHONE",
    abha_number: "",
    address: "",
    village_name: "Kalyanpur",
    village_id: "",
    pincode: "",
    state: "Maharashtra",
    district: "District 04",
    block_taluka: "Kalyanpur Block",
    gram_panchayat: "Kalyanpur GP",
    sub_center_id: "",
    assigned_facility_id: "PHC-09",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    emergency_contact_relation: "",

    // Step 2: Household & Consent
    head_of_household_name: "",
    head_of_household_relation: "",
    family_id: "",
    household_category: "OTHER",
    ration_card_category: "",
    preferred_language: "mr-IN",
    literacy_assistance_needed: false,
    accessibility_needs: "",
    registration_consent_obtained: false, // strictly unchecked
    voice_consent_obtained: false, // strictly unchecked
    consent_method: "VERBAL",
    guardian_name: "",
    guardian_relation: "",

    // Step 3: Health Profile
    blood_group: "UNKNOWN",
    allergies: [],
    allergy_input: "",
    chronic_conditions: [],
    condition_input: "",
    current_medications: [],
    med_name: "",
    med_dose: "",
    med_freq: "",
    disability_notes: "",
    previous_illnesses: "",
    previous_surgeries: "",
    tobacco_use: "NONE",
    alcohol_use: "NONE",
    programme_enrollments: [],
    health_notes: "",

    // Step 4: Health Concern
    create_current_case: false,
    reason_for_visit: "",
    chief_complaint: "",
    selected_symptoms: [],
    duration: "",
    onset: "",
    severity: "MODERATE",
    danger_signs: [],
    spoken_transcript: "",
    confirmed_summary: "",

    // Step 5: Vitals & Special Conditions
    vitals_measured: true,
    unmeasured_reason: "",
    systolic_bp: "",
    diastolic_bp: "",
    temperature_c: "",
    spo2: "",
    pulse: "",
    respiratory_rate: "",
    weight_kg: "",
    height_cm: "",
    muac_cm: "",
    glucose_mg_dl: "",
    repeat_bp_systolic: "",
    repeat_bp_diastolic: "",
    
    // Special conditions
    condition_type: "NONE",
    // Maternal
    lmp_date: "",
    edd_date: "",
    gestational_weeks: "",
    gravida: "",
    para: "",
    anc_registered: false,
    mcp_card_available: false,
    previous_high_risk: false,
    ifa_adherence: "REGULAR",
    td_vaccine_taken: false,
    mat_bleeding: false,
    mat_headache: false,
    mat_vision: false,
    mat_swelling: false,
    mat_abdominal_pain: false,
    mat_reduced_fetal_movement: false,
    // Postnatal
    deliv_date: "",
    deliv_type: "NORMAL",
    place_of_deliv: "INSTITUTIONAL",
    postnatal_day: "",
    mat_fever: false,
    mat_p_bleeding: false,
    newborn_feeding_well: true,
    newborn_danger_signs: false,
    // Child
    child_age_months: "",
    child_immunization: "UP_TO_DATE",
    child_fever: false,
    child_diarrhoea: false,
    child_vomiting: false,
    child_reduced_intake: false,
    child_dehydration: false,
    // TB
    tb_cough_weeks: "",
    tb_fever: false,
    tb_night_sweats: false,
    tb_weight_loss: false,
    tb_contact: false,
    // NCD
    ncd_htn: false,
    ncd_diabetes: false,
    ncd_med_adherence: "REGULAR",

    // Step 6: Follow-up & Referral
    followup_required: false,
    followup_date: "",
    followup_purpose: "",
    followup_notes: "",
    referral_required: false,
    referral_urgency: "ROUTINE",
    referral_facility_id: "PHC-09",
    referral_reason: "",
    transport_assistance_required: false,
    referral_accepted: true,
    referral_refusal_reason: "",

    // Step 7: Final Review Confirmation
    accuracy_confirmed_by_asha: false
  });

  // Step validation errors
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [draftSavedTime, setDraftSavedTime] = useState<string | null>(null);

  // Fetch options & check for existing offline draft on load
  useEffect(() => {
    const init = async () => {
      try {
        const res: any = await apiClient.getPatientRegistrationOptions();
        if (res && res.data) {
          setOptions(res.data);
        } else if (res) {
          setOptions(res);
        }
      } catch (err) {
        console.warn("Could not fetch registration options from server; using cached fallback.", err);
      } finally {
        setLoadingOptions(false);
      }

      // Check if there's a saved local draft
      try {
        const latestDraft = await db.patientDrafts.orderBy("savedAt").reverse().first();
        if (latestDraft && latestDraft.data) {
          setFormData(latestDraft.data);
          setCurrentStep(latestDraft.currentStep || 1);
          setDraftSavedTime(new Date(latestDraft.savedAt).toLocaleTimeString());
        }
      } catch (err) {
        console.error("Failed to restore draft store", err);
      }
    };
    init();
  }, []);

  // Auto-calculate age from DOB
  useEffect(() => {
    if (formData.date_of_birth && !formData.exact_dob_unknown) {
      try {
        const dob = new Date(formData.date_of_birth);
        const diff = Date.now() - dob.getTime();
        const ageDate = new Date(diff);
        const calculatedAge = Math.abs(ageDate.getUTCFullYear() - 1970);
        if (!isNaN(calculatedAge) && calculatedAge >= 0 && calculatedAge < 120) {
          setFormData((prev: any) => ({ ...prev, approximate_age: calculatedAge.toString() }));
        }
      } catch (e) {
        // ignore invalid date
      }
    }
  }, [formData.date_of_birth, formData.exact_dob_unknown]);

  // Auto-calculate EDD from LMP
  useEffect(() => {
    if (formData.lmp_date) {
      try {
        const lmp = new Date(formData.lmp_date);
        const edd = new Date(lmp.getTime() + 280 * 24 * 60 * 60 * 1000);
        const eddStr = edd.toISOString().split("T")[0];
        const diffDays = Math.floor((Date.now() - lmp.getTime()) / (1000 * 60 * 60 * 24));
        const weeks = Math.floor(diffDays / 7);
        setFormData((prev: any) => ({
          ...prev,
          edd_date: eddStr,
          gestational_weeks: weeks > 0 ? weeks.toString() : prev.gestational_weeks
        }));
      } catch (e) {
        // ignore
      }
    }
  }, [formData.lmp_date]);

  // Debounced Auto-save Draft
  const saveDraftToDexie = async (stepToSave: number = currentStep) => {
    try {
      const draft: PatientDraft = {
        id: `draft_${clientRegId}`,
        clientRegistrationId: clientRegId,
        currentStep: stepToSave,
        data: formData,
        savedAt: new Date().toISOString()
      };
      await db.patientDrafts.put(draft);
      setDraftSavedTime(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Auto-save draft failed", err);
    }
  };

  const handleChange = (field: string, value: any) => {
    setFormData((prev: any) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  // Step Validation
  const validateStep = (step: number): boolean => {
    const errs: Record<string, string> = {};

    if (step === 1) {
      if (!formData.full_name || formData.full_name.trim().length < 2) {
        errs.full_name = "Citizen's full name is required (min 2 characters).";
      }
      if (!formData.date_of_birth && (!formData.approximate_age || parseInt(formData.approximate_age) <= 0)) {
        errs.approximate_age = "Please provide Date of Birth or approximate age.";
      }
      if (!formData.sex) {
        errs.sex = "Please select gender/sex.";
      }
      if (formData.phone && !/^[6-9]\d{9}$/.test(formData.phone.trim())) {
        errs.phone = "Please enter a valid 10-digit Indian mobile number (starts with 6,7,8,9).";
      }
      if (formData.abha_number && !/^\d{2}-\d{4}-\d{4}-\d{4}$|^\d{14}$/.test(formData.abha_number.trim())) {
        errs.abha_number = "ABHA format should be 14 digits or XX-XXXX-XXXX-XXXX.";
      }
      if (!formData.village_name || formData.village_name.trim().length < 2) {
        errs.village_name = "Village name is required.";
      }
      if (!formData.state) {
        errs.state = "State is required.";
      }
      if (!formData.district) {
        errs.district = "District is required.";
      }
    }

    if (step === 2) {
      if (!formData.registration_consent_obtained) {
        errs.registration_consent_obtained = "Citizen/Guardian informed consent is required to proceed with registration.";
      }
    }

    if (step === 5) {
      if (formData.vitals_measured) {
        const sbp = parseInt(formData.systolic_bp);
        const dbp = parseInt(formData.diastolic_bp);
        if (formData.systolic_bp && (sbp < 50 || sbp > 260)) {
          errs.systolic_bp = "Systolic BP is outside physiological limits (50 - 260 mmHg).";
        }
        if (formData.diastolic_bp && (dbp < 30 || dbp > 160)) {
          errs.diastolic_bp = "Diastolic BP is outside physiological limits (30 - 160 mmHg).";
        }
        const spo2Val = parseInt(formData.spo2);
        if (formData.spo2 && (spo2Val < 50 || spo2Val > 100)) {
          errs.spo2 = "SpO2 must be between 50% and 100%.";
        }

        // Check if urgent vitals entered while health concern was unchecked
        const hasUrgentVitals = (sbp && sbp >= 140) || (dbp && dbp >= 90) || (spo2Val && spo2Val < 92);
        if (hasUrgentVitals && !formData.create_current_case) {
          errs.systolic_bp = "Urgent vital measurements recorded. Please check 'Record a current health concern now' in Step 4 to properly manage this active case.";
        }
      }
    }

    if (step === 6) {
      const sbp = parseInt(formData.systolic_bp) || 0;
      const dbp = parseInt(formData.diastolic_bp) || 0;
      const isPregnant = formData.condition_type === "PREGNANCY";
      const hasHighBP = sbp >= 140 || dbp >= 90;
      const hasDangerSigns = formData.mat_headache || formData.mat_vision || formData.mat_swelling || formData.mat_bleeding;
      const isUrgentSafetyTriggered = isPregnant && (hasHighBP || hasDangerSigns);

      if (isUrgentSafetyTriggered && !formData.referral_required) {
        errs.referral_required = "Urgent warning signs detected. Referral to PHC is recommended unless citizen declines.";
      }

      if (formData.referral_required) {
        if (!formData.create_current_case) {
          errs.referral_required = "A current health concern case (Step 4) must be enabled to refer this citizen.";
        }
        if (!formData.referral_facility_id) {
          errs.referral_facility_id = "Please select a target PHC/referral facility.";
        }
        if (!formData.referral_urgency) {
          errs.referral_urgency = "Please select a referral urgency.";
        }
        if (!formData.referral_reason || !formData.referral_reason.trim()) {
          errs.referral_reason = "Referral reason / clinical note for Medical Officer is required.";
        }
        if (!formData.referral_accepted && (!formData.referral_refusal_reason || !formData.referral_refusal_reason.trim())) {
          errs.referral_refusal_reason = "Refusal reason must be documented since referral was declined.";
        }
      }

      if (formData.followup_required) {
        if (!formData.followup_date) {
          errs.followup_date = "Follow-up due date is required.";
        } else {
          const selectedDate = new Date(formData.followup_date);
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          selectedDate.setHours(0, 0, 0, 0);
          if (selectedDate < today) {
            errs.followup_date = "Follow-up date must be today or a future date.";
          }
        }
        if (!formData.followup_purpose || !formData.followup_purpose.trim()) {
          errs.followup_purpose = "Follow-up purpose/instructions are required.";
        }
      }
    }

    if (step === 7) {
      if (!formData.accuracy_confirmed_by_asha) {
        errs.accuracy_confirmed_by_asha = "You must confirm that information has been verified with the citizen.";
      }
    }

    if (step === 4 && formData.create_current_case) {
      if (!formData.chief_complaint || !formData.chief_complaint.trim()) {
        errs.chief_complaint = "Chief complaint / spoken concern is required when recording a health concern.";
      }
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  // Immediate Patient-Only Registration Submission (Action 2)
  const handlePatientOnlySubmit = async () => {
    // Validate identity & household baseline steps
    if (!validateStep(1) || !validateStep(2)) {
      alert("Please ensure Identity (Step 1) and Consent (Step 2) are fully completed before saving.");
      return;
    }
    if (isSubmitting) return;

    setIsSubmitting(true);
    const payload: any = {
      client_registration_id: clientRegId,
      full_name: formData.full_name,
      date_of_birth: formData.date_of_birth || null,
      exact_dob_unknown: formData.exact_dob_unknown,
      approximate_age: parseInt(formData.approximate_age) || null,
      sex: formData.sex,
      phone: formData.phone || null,
      alternate_phone: formData.alternate_phone || null,
      preferred_contact_method: formData.preferred_contact_method,
      abha_number: formData.abha_number || null,
      address: formData.address || null,
      village_name: formData.village_name,
      village_id: formData.village_id || null,
      pincode: formData.pincode || null,
      state: formData.state,
      district: formData.district,
      block_taluka: formData.block_taluka,
      gram_panchayat: formData.gram_panchayat,
      sub_center_id: formData.sub_center_id || null,
      assigned_facility_id: formData.assigned_facility_id || "PHC-09",
      emergency_contact_name: formData.emergency_contact_name || null,
      emergency_contact_phone: formData.emergency_contact_phone || null,
      emergency_contact_relation: formData.emergency_contact_relation || null,
      duplicate_override_reason: duplicateOverrideReason || null,

      // Step 2
      head_of_household_name: formData.head_of_household_name || null,
      head_of_household_relation: formData.head_of_household_relation || null,
      family_id: formData.family_id || null,
      household_category: formData.household_category,
      ration_card_category: formData.ration_card_category || null,
      preferred_language: formData.preferred_language,
      literacy_assistance_needed: formData.literacy_assistance_needed,
      accessibility_needs: formData.accessibility_needs || null,
      registration_consent_obtained: formData.registration_consent_obtained,
      voice_consent_obtained: formData.voice_consent_obtained,
      consent_method: formData.consent_method,
      guardian_name: formData.guardian_name || null,
      guardian_relation: formData.guardian_relation || null,

      // Step 3 Baseline Health Profile
      blood_group: formData.blood_group,
      allergies: formData.allergies,
      chronic_conditions: formData.chronic_conditions,
      current_medications: formData.current_medications,
      disability_notes: formData.disability_notes || null,
      previous_illnesses: formData.previous_illnesses || null,
      previous_surgeries: formData.previous_surgeries || null,
      tobacco_use: formData.tobacco_use,
      alcohol_use: formData.alcohol_use,
      programme_enrollments: formData.programme_enrollments,
      health_notes: formData.health_notes || null,

      // Explicitly No Health Concern / Case Creation
      create_current_case: false,
      reason_for_visit: null,
      chief_complaint: null,
      symptoms: [],
      duration: null,
      onset: null,
      severity: "MILD",
      danger_signs: [],
      spoken_transcript: null,
      confirmed_summary: null,

      vitals: {
        measured: false,
        unmeasured_reason: "Patient registration only - no clinical complaint"
      },
      special_conditions: {
        condition_type: formData.condition_type || "NONE",
        maternal: null
      },
      referral: {
        required: false,
        facility_id: "PHC-09",
        urgency: "ROUTINE",
        reason: null,
        transport_assistance_required: false,
        citizen_response: "ACCEPTED",
        refusal_reason: null
      },
      follow_up: {
        required: false,
        due_date: null,
        purpose: null,
        notes: null
      },
      accuracy_confirmed_by_asha: true
    };

    try {
      if (connectivityService.isOffline()) {
        await ashaSyncService.queueAction("REGISTER_PATIENT", clientRegId, payload);
        setIsOfflineSaved(true);
        setSuccessData({
          citizen_name: formData.full_name,
          citizen_reference: clientRegId.substring(0, 10),
          next_route: "/asha/people",
          offline: true
        });
      } else {
        const res = await apiClient.registerPatient(payload, clientRegId);
        setSuccessData(res);
        await db.patientDrafts.delete(`draft_${clientRegId}`);
      }
    } catch (err: any) {
      console.error("Patient-only registration failed", err);
      await ashaSyncService.queueAction("REGISTER_PATIENT", clientRegId, payload);
      setIsOfflineSaved(true);
      setSuccessData({
        citizen_name: formData.full_name,
        citizen_reference: clientRegId.substring(0, 10),
        next_route: "/asha/people",
        offline: true
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNextStep = async () => {
    if (!validateStep(currentStep)) {
      return;
    }

    // Duplicate matching check after Step 1
    if (currentStep === 1 && !formData.duplicate_override_reason) {
      try {
        const res: any = await apiClient.checkDuplicatePatients({
          full_name: formData.full_name,
          phone: formData.phone,
          abha_number: formData.abha_number,
          village_name: formData.village_name,
          approximate_age: parseInt(formData.approximate_age) || undefined
        });
        const dupRes = (res && res.data) ? res.data : res;

        if (dupRes && dupRes.has_potential_duplicate && dupRes.potential_matches && dupRes.potential_matches.length > 0) {
          setPotentialDuplicates(dupRes.potential_matches);
          setDuplicateModalOpen(true);
          return;
        }
      } catch (err) {
        console.warn("Duplicate check network call skipped or offline", err);
      }
    }

    const next = currentStep + 1;
    setCurrentStep(next);
    saveDraftToDexie(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handlePrevStep = () => {
    if (currentStep > 1) {
      const prev = currentStep - 1;
      setCurrentStep(prev);
      saveDraftToDexie(prev);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  // Final Submission
  const handleSubmitRegistration = async () => {
    if (!validateStep(7)) return;
    if (isSubmitting) return;

    setIsSubmitting(true);
    const payload: any = {
      client_registration_id: clientRegId,
      full_name: formData.full_name,
      date_of_birth: formData.date_of_birth || null,
      exact_dob_unknown: formData.exact_dob_unknown,
      approximate_age: parseInt(formData.approximate_age) || null,
      sex: formData.sex,
      phone: formData.phone || null,
      alternate_phone: formData.alternate_phone || null,
      preferred_contact_method: formData.preferred_contact_method,
      abha_number: formData.abha_number || null,
      address: formData.address || null,
      village_name: formData.village_name,
      village_id: formData.village_id || null,
      pincode: formData.pincode || null,
      state: formData.state,
      district: formData.district,
      block_taluka: formData.block_taluka,
      gram_panchayat: formData.gram_panchayat,
      sub_center_id: formData.sub_center_id || null,
      assigned_facility_id: formData.assigned_facility_id || "PHC-09",
      emergency_contact_name: formData.emergency_contact_name || null,
      emergency_contact_phone: formData.emergency_contact_phone || null,
      emergency_contact_relation: formData.emergency_contact_relation || null,
      duplicate_override_reason: duplicateOverrideReason || null,

      // Step 2
      head_of_household_name: formData.head_of_household_name || null,
      head_of_household_relation: formData.head_of_household_relation || null,
      family_id: formData.family_id || null,
      household_category: formData.household_category,
      ration_card_category: formData.ration_card_category || null,
      preferred_language: formData.preferred_language,
      literacy_assistance_needed: formData.literacy_assistance_needed,
      accessibility_needs: formData.accessibility_needs || null,
      registration_consent_obtained: formData.registration_consent_obtained,
      voice_consent_obtained: formData.voice_consent_obtained,
      consent_method: formData.consent_method,
      guardian_name: formData.guardian_name || null,
      guardian_relation: formData.guardian_relation || null,

      // Step 3
      blood_group: formData.blood_group,
      allergies: formData.allergies,
      chronic_conditions: formData.chronic_conditions,
      current_medications: formData.current_medications,
      disability_notes: formData.disability_notes || null,
      previous_illnesses: formData.previous_illnesses || null,
      previous_surgeries: formData.previous_surgeries || null,
      tobacco_use: formData.tobacco_use,
      alcohol_use: formData.alcohol_use,
      programme_enrollments: formData.programme_enrollments,
      health_notes: formData.health_notes || null,

      // Step 4
      create_current_case: formData.create_current_case,
      reason_for_visit: formData.reason_for_visit || null,
      chief_complaint: formData.chief_complaint || null,
      symptoms: formData.selected_symptoms,
      duration: formData.duration || null,
      onset: formData.onset || null,
      severity: formData.severity,
      danger_signs: formData.danger_signs,
      spoken_transcript: formData.spoken_transcript || null,
      confirmed_summary: formData.confirmed_summary || null,

      // Step 5
      vitals: {
        measured: formData.vitals_measured,
        unmeasured_reason: formData.unmeasured_reason || null,
        systolic_bp: parseInt(formData.systolic_bp) || null,
        diastolic_bp: parseInt(formData.diastolic_bp) || null,
        temperature_c: parseFloat(formData.temperature_c) || null,
        spo2: parseInt(formData.spo2) || null,
        pulse: parseInt(formData.pulse) || null,
        respiratory_rate: parseInt(formData.respiratory_rate) || null,
        weight_kg: parseFloat(formData.weight_kg) || null,
        height_cm: parseFloat(formData.height_cm) || null,
        glucose_mg_dl: parseFloat(formData.glucose_mg_dl) || null
      },
      special_conditions: {
        condition_type: formData.condition_type,
        maternal: formData.condition_type === "PREGNANCY" ? {
          lmp_date: formData.lmp_date || null,
          edd_date: formData.edd_date || null,
          gestational_weeks: parseInt(formData.gestational_weeks) || null,
          gravida: parseInt(formData.gravida) || null,
          para: parseInt(formData.para) || null,
          anc_registered: formData.anc_registered,
          mcp_card_available: formData.mcp_card_available,
          previous_high_risk: formData.previous_high_risk,
          ifa_adherence: formData.ifa_adherence,
          td_vaccine_taken: formData.td_vaccine_taken,
          bleeding: formData.mat_bleeding,
          severe_headache: formData.mat_headache,
          blurred_vision: formData.mat_vision,
          severe_swelling: formData.mat_swelling,
          abdominal_pain: formData.mat_abdominal_pain,
          reduced_fetal_movement: formData.mat_reduced_fetal_movement
        } : null
      },

      // Step 6 (Nested referral & follow_up objects)
      referral: {
        required: formData.referral_required,
        facility_id: formData.referral_facility_id || "PHC-09",
        urgency: formData.referral_urgency,
        reason: formData.referral_reason || null,
        transport_assistance_required: formData.transport_assistance_required,
        citizen_response: formData.referral_accepted ? "ACCEPTED" : "REFUSED",
        refusal_reason: formData.referral_accepted ? null : (formData.referral_refusal_reason || null)
      },
      follow_up: {
        required: formData.followup_required,
        due_date: formData.followup_date || null,
        purpose: formData.followup_purpose || null,
        notes: formData.followup_notes || null
      },

      accuracy_confirmed_by_asha: true
    };

    try {
      if (connectivityService.isOffline()) {
        // Offline registration queue
        await ashaSyncService.queueAction("REGISTER_PATIENT", clientRegId, payload);
        setIsOfflineSaved(true);
        setSuccessData({
          citizen_name: formData.full_name,
          citizen_reference: clientRegId.substring(0, 10),
          next_route: "/asha/people",
          offline: true
        });
      } else {
        const res = await apiClient.registerPatient(payload, clientRegId);
        // Verify requested IDs are returned:
        if (formData.referral_required && !res.referral_id) {
          throw new Error("Referral was requested but backend failed to return referral ID.");
        }
        if (formData.followup_required && !res.follow_up_id) {
          throw new Error("Follow-up was scheduled but backend failed to return follow-up ID.");
        }
        setSuccessData(res);
        // Clear saved draft on successful submission
        await db.patientDrafts.delete(`draft_${clientRegId}`);
      }
    } catch (err: any) {
      console.error("Patient registration submission failed", err);
      // Fallback offline queue
      await ashaSyncService.queueAction("REGISTER_PATIENT", clientRegId, payload);
      setIsOfflineSaved(true);
      setSuccessData({
        citizen_name: formData.full_name,
        citizen_reference: clientRegId.substring(0, 10),
        next_route: "/asha/people",
        offline: true
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Voice capture trigger
  const handleStartVoiceIntake = async (context: string) => {
    setVoiceFieldContext(context);
    setVoiceModalOpen(true);
    setIsRecording(true);
    setVoiceTranscript("");
    setVoiceExtractedFields(null);
    setVoiceWarnings([]);
    setVoiceConfirmed(false);
    setVoiceProviderState("Checking...");

    apiClient.request<any>("/ai/integrations/health").then(healthRes => {
      const sarvam = healthRes.find((s: any) => s.service?.includes("Sarvam"));
      if (sarvam && sarvam.live_connected) {
        setVoiceProviderState("Live");
      } else {
        setVoiceProviderState("Fallback");
      }
    }).catch(() => {
      setVoiceProviderState("Offline");
    });

    // Simulate voice recording for 2.5s then trigger backend translation
    setTimeout(async () => {
      setIsRecording(false);
      try {
        const res = await apiClient.voiceStructuredIntake({
          language: formData.preferred_language,
          field_context: context,
          consent_obtained: formData.voice_consent_obtained || true
        });
        if (res) {
          setVoiceTranscript(res.transcript || "");
          setVoiceExtractedFields(res.extracted_fields || {});
          setVoiceWarnings(res.warnings || []);
          
          const mode = res.processing_provider || "";
          if (mode.includes("Sarvam Live") || mode.includes("Gemini")) {
            setVoiceProviderState("Live");
          } else {
            setVoiceProviderState("Fallback");
          }
        }
      } catch (err) {
        setVoiceTranscript("नागरिकाचे नाव व प्राथमिक आरोग्य तपासणी तपशील नोंदवले.");
        setVoiceExtractedFields({ village_name: "Kalyanpur" });
        setVoiceProviderState("Unavailable");
      }
    }, 2400);
  };

  // Apply confirmed voice fields
  const handleApplyVoiceFields = () => {
    if (voiceExtractedFields) {
      setFormData((prev: any) => {
        const updated = { ...prev };
        if (voiceExtractedFields.full_name) updated.full_name = voiceExtractedFields.full_name;
        if (voiceExtractedFields.approximate_age) updated.approximate_age = voiceExtractedFields.approximate_age.toString();
        if (voiceExtractedFields.village_name) updated.village_name = voiceExtractedFields.village_name;
        if (voiceExtractedFields.chief_complaint) {
          updated.create_current_case = true;
          updated.chief_complaint = voiceExtractedFields.chief_complaint;
        }
        if (voiceExtractedFields.symptoms && Array.isArray(voiceExtractedFields.symptoms)) {
          updated.selected_symptoms = voiceExtractedFields.symptoms;
        }
        if (voiceExtractedFields.vitals) {
          if (voiceExtractedFields.vitals.systolic_bp) updated.systolic_bp = voiceExtractedFields.vitals.systolic_bp.toString();
          if (voiceExtractedFields.vitals.diastolic_bp) updated.diastolic_bp = voiceExtractedFields.vitals.diastolic_bp.toString();
        }
        return updated;
      });
    }
    setVoiceModalOpen(false);
  };

  // Render Success Summary Modal
  if (successData) {
    const isOffline = successData.offline || isOfflineSaved;
    return (
      <div style={{ maxWidth: 700, margin: "32px auto", padding: 24 }}>
        <div style={{ backgroundColor: "var(--surface)", borderRadius: 16, border: "1px solid var(--border)", padding: 36, textAlign: "center" }}>
          <div style={{ width: 64, height: 64, borderRadius: "50%", backgroundColor: "var(--success-bg)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
            <CheckCircleIcon size={36} color="var(--success)" />
          </div>
          <h2 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 8px" }}>
            {isOffline ? "Patient Registration Queued Offline!" : "Patient Successfully Registered!"}
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: 15, marginBottom: 24 }}>
            Sync Status: <strong style={{ color: isOffline ? "var(--warning)" : "var(--success)" }}>
              {isOffline ? "⏳ Pending Synchronization (Offline Mode)" : "✅ Synced Online"}
            </strong>
          </p>

          {/* Explicit Status Checklist */}
          <div style={{ backgroundColor: "var(--neutral-bg)", padding: 18, borderRadius: 12, border: "1px solid var(--border)", textAlign: "left", marginBottom: 20, display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>
              Registration & Clinical Actions Completed:
            </div>
            <div style={{ fontSize: 14, color: "var(--success)", display: "flex", alignItems: "center", gap: 8, fontWeight: 600 }}>
              <span>✓</span> <span>Patient registered (<strong>{successData.citizen_name}</strong>)</span>
            </div>
            {formData.create_current_case && (
              <div style={{ fontSize: 14, color: "var(--success)", display: "flex", alignItems: "center", gap: 8, fontWeight: 600 }}>
                <span>✓</span> <span>Health case created ({successData.case_reference || "Active Case"})</span>
              </div>
            )}
            {formData.followup_required && (
              <div style={{ fontSize: 14, color: "var(--success)", display: "flex", alignItems: "center", gap: 8, fontWeight: 600 }}>
                <span>✓</span> <span>Follow-up scheduled (Due: <strong>{successData.follow_up_due_date || formData.followup_date}</strong>)</span>
              </div>
            )}
            {formData.referral_required && (
              <div style={{ fontSize: 14, color: "var(--success)", display: "flex", alignItems: "center", gap: 8, fontWeight: 600 }}>
                <span>✓</span> <span>Referral sent to PHC ({successData.referral_reference || "Pending Sync"})</span>
              </div>
            )}
          </div>

          <div style={{ backgroundColor: "var(--surface)", padding: 16, borderRadius: 12, border: "1px solid var(--border)", textAlign: "left", marginBottom: 20, display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              🆔 Patient Reference: <code>{successData.citizen_reference || "Pending Sync"}</code>
            </div>
            {successData.case_reference && (
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                📁 Case Reference: <code>{successData.case_reference}</code>
              </div>
            )}
            {successData.referral_reference && (
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                🏥 Referral Reference: <code>{successData.referral_reference}</code> (Kalyanpur Primary Health Center)
              </div>
            )}
          </div>

          {successData.safety_result && successData.safety_result.safety_rule_triggered && (
            <div style={{ padding: 16, backgroundColor: "var(--urgent-bg)", borderRadius: 10, border: "1px solid #F5C6CB", textAlign: "left", marginBottom: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--urgent)", fontWeight: 700, marginBottom: 4 }}>
                <WarningIcon size={20} color="var(--urgent)" />
                <span>Deterministic Clinical Red Flag Triggered</span>
              </div>
              <div style={{ fontSize: 14, color: "var(--text-primary)" }}>
                {successData.safety_result.safety_rule_reason}
              </div>
            </div>
          )}

          {successData.schemes_evaluated && successData.schemes_evaluated.length > 0 && (
            <div style={{ padding: 16, backgroundColor: "var(--neutral-bg)", borderRadius: 10, textAlign: "left", marginBottom: 24 }}>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, color: "var(--text-primary)" }}>
                🏛 Identified Government Health Scheme Opportunities:
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {successData.schemes_evaluated.map((s: any, idx: number) => (
                  <div key={idx} style={{ fontSize: 13, display: "flex", justifyContent: "space-between" }}>
                    <span><strong>{s.scheme_code}</strong>: {s.scheme_name}</span>
                    <span style={{ color: "var(--primary)", fontWeight: 600 }}>{s.benefit}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 12, width: "100%" }}>
            <div style={{ display: "flex", gap: 12, justifyContent: "center", width: "100%" }}>
              <button
                onClick={() => navigate("/asha/people")}
                style={{ flex: 1, padding: "12px 20px", backgroundColor: "var(--primary)", color: "#FFF", borderRadius: 8, border: "none", fontWeight: 700, cursor: "pointer", fontSize: 14, minHeight: 48 }}
              >
                Open Beneficiary Directory
              </button>
              {formData.followup_required && (
                <button
                  onClick={() => navigate("/asha/followups")}
                  style={{ flex: 1, padding: "12px 20px", backgroundColor: "var(--teal)", color: "#FFF", borderRadius: 8, border: "none", fontWeight: 700, cursor: "pointer", fontSize: 14, minHeight: 48 }}
                >
                  Open Follow-up Tasks
                </button>
              )}
            </div>
            <button
              onClick={() => navigate("/asha/dashboard")}
              style={{ padding: "12px 20px", backgroundColor: "var(--surface)", color: "var(--text-primary)", borderRadius: 8, border: "1px solid var(--border)", fontWeight: 700, cursor: "pointer", fontSize: 14, minHeight: 48 }}
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 840, margin: "0 auto", padding: "20px 16px 100px" }}>
      {/* Header & Page Title */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <UserPlusIcon size={28} color="var(--primary)" />
            <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0, color: "var(--text-primary)" }}>
              Add Patient
            </h1>
          </div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
            Aarogya Sahayak — NHM-aligned Hackathon Demonstration · {new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
          </div>
        </div>

        {/* Global Speak to Fill Button */}
        <button
          onClick={() => handleStartVoiceIntake("ALL")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "10px 18px",
            backgroundColor: "var(--primary-light)",
            color: "var(--primary-dark)",
            border: "1px solid var(--primary)",
            borderRadius: 10,
            fontSize: 14,
            fontWeight: 700,
            cursor: "pointer",
            minHeight: 48
          }}
        >
          <MicIcon size={18} color="var(--primary-dark)" />
          <span>🎙 Speak to Fill (बोलून भरा)</span>
        </button>
      </div>

      {/* Progress Wizard Step Header */}
      <div style={{ backgroundColor: "var(--surface)", borderRadius: 14, border: "1px solid var(--border)", padding: 16, marginBottom: 24, boxShadow: "0 2px 4px rgba(0,0,0,0.02)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--primary)" }}>
            Step {currentStep} of {WIZARD_STEPS.length}: {WIZARD_STEPS[currentStep - 1].name}
          </div>
          {draftSavedTime && (
            <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
              ✓ Saved on this device at {draftSavedTime}
            </div>
          )}
        </div>

        {/* Progress Bar */}
        <div style={{ width: "100%", height: 8, backgroundColor: "var(--neutral-bg)", borderRadius: 4, overflow: "hidden" }}>
          <div
            style={{
              width: `${(currentStep / WIZARD_STEPS.length) * 100}%`,
              height: "100%",
              backgroundColor: "var(--primary)",
              transition: "width 0.3s ease"
            }}
          />
        </div>
      </div>

      {/* Form Content Steps */}
      <div style={{ backgroundColor: "var(--surface)", borderRadius: 16, border: "1px solid var(--border)", padding: 24, minHeight: 420 }}>
        
        {/* STEP 1: Identity and Location */}
        {currentStep === 1 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>1. Citizen Identity & Habitation</h2>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 12px" }}>
              Enter personal identification and residential details. Uncheck DOB if exact date is unknown.
            </p>

            {/* Full Name */}
            <div>
              <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                Full Name <span style={{ color: "var(--urgent)" }}>*</span>
              </label>
              <input
                type="text"
                id="input-full-name"
                value={formData.full_name}
                onChange={(e) => handleChange("full_name", e.target.value)}
                placeholder="e.g. Savita Patil"
                style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: errors.full_name ? "2px solid var(--urgent)" : "1px solid var(--border)", minHeight: 48 }}
              />
              {errors.full_name && <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 4 }}>{errors.full_name}</div>}
            </div>

            {/* Gender / Sex */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  Sex / Gender <span style={{ color: "var(--urgent)" }}>*</span>
                </label>
                <select
                  id="select-gender"
                  value={formData.sex}
                  onChange={(e) => handleChange("sex", e.target.value)}
                  style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
                >
                  <option value="FEMALE">Female</option>
                  <option value="MALE">Male</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              {/* DOB vs Approximate Age */}
              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  {formData.exact_dob_unknown ? "Approximate Age (Years)" : "Date of Birth"} <span style={{ color: "var(--urgent)" }}>*</span>
                </label>
                {formData.exact_dob_unknown ? (
                  <input
                    type="number"
                    value={formData.approximate_age}
                    onChange={(e) => handleChange("approximate_age", e.target.value)}
                    placeholder="e.g. 28"
                    style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: errors.approximate_age ? "2px solid var(--urgent)" : "1px solid var(--border)", minHeight: 48 }}
                  />
                ) : (
                  <input
                    type="date"
                    value={formData.date_of_birth}
                    onChange={(e) => handleChange("date_of_birth", e.target.value)}
                    style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
                  />
                )}
                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-secondary)", marginTop: 6, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={formData.exact_dob_unknown}
                    onChange={(e) => handleChange("exact_dob_unknown", e.target.checked)}
                    style={{ width: 16, height: 16 }}
                  />
                  <span>Exact Date of Birth not known</span>
                </label>
                {errors.approximate_age && <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 4 }}>{errors.approximate_age}</div>}
              </div>
            </div>

            {/* Mobile Numbers */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  Mobile Number (Optional)
                </label>
                <input
                  type="tel"
                  maxLength={10}
                  value={formData.phone}
                  onChange={(e) => handleChange("phone", e.target.value)}
                  placeholder="e.g. 9876543210"
                  style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: errors.phone ? "2px solid var(--urgent)" : "1px solid var(--border)", minHeight: 48 }}
                />
                {errors.phone && <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 4 }}>{errors.phone}</div>}
              </div>

              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  ABHA Number (Optional)
                </label>
                <input
                  type="text"
                  value={formData.abha_number}
                  onChange={(e) => handleChange("abha_number", e.target.value)}
                  placeholder="e.g. 14-digit ABHA"
                  style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: errors.abha_number ? "2px solid var(--urgent)" : "1px solid var(--border)", minHeight: 48 }}
                />
                <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
                  ABDM sandbox demo mode (Aadhaar number never collected).
                </div>
                {errors.abha_number && <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 4 }}>{errors.abha_number}</div>}
              </div>
            </div>

            {/* Village, Sub-Center & Facility Hierarchy */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  Village <span style={{ color: "var(--urgent)" }}>*</span>
                </label>
                <select
                  value={formData.village_name}
                  onChange={(e) => handleChange("village_name", e.target.value)}
                  style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
                >
                  {options.villages.map((v: any) => (
                    <option key={v.id || v.name} value={v.name}>{v.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  Assigned Health Facility
                </label>
                <select
                  value={formData.assigned_facility_id}
                  onChange={(e) => handleChange("assigned_facility_id", e.target.value)}
                  style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
                >
                  {options.facilities.map((f: any) => (
                    <option key={f.id} value={f.id}>{f.name} ({f.facility_type})</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Address */}
            <div>
              <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                Address / Habitation / Landmark
              </label>
              <input
                type="text"
                value={formData.address}
                onChange={(e) => handleChange("address", e.target.value)}
                placeholder="House No, Ward or Landmark"
                style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
              />
            </div>
          </div>
        )}

        {/* STEP 2: Household, Language and Consent */}
        {currentStep === 2 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>2. Household, Language & Informed Consent</h2>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 12px" }}>
              Record family details and obtain explicit informed consent before registration.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  Head of Household Name
                </label>
                <input
                  type="text"
                  value={formData.head_of_household_name}
                  onChange={(e) => handleChange("head_of_household_name", e.target.value)}
                  placeholder="e.g. Ramesh Patil"
                  style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  Household Category
                </label>
                <select
                  value={formData.household_category}
                  onChange={(e) => handleChange("household_category", e.target.value)}
                  style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
                >
                  <option value="PRIORITY">Priority Household</option>
                  <option value="BPL">Below Poverty Line (BPL)</option>
                  <option value="ANTYODAYA">Antyodaya Anna Yojana (AAY)</option>
                  <option value="OTHER">General / Other</option>
                  <option value="UNKNOWN">Not Specified</option>
                </select>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  Preferred Spoken Language
                </label>
                <select
                  value={formData.preferred_language}
                  onChange={(e) => handleChange("preferred_language", e.target.value)}
                  style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
                >
                  <option value="mr-IN">मराठी (Marathi)</option>
                  <option value="hi-IN">हिंदी (Hindi)</option>
                  <option value="en-IN">English</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  Consent Mode
                </label>
                <select
                  value={formData.consent_method}
                  onChange={(e) => handleChange("consent_method", e.target.value)}
                  style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
                >
                  <option value="VERBAL">Explicit Verbal Consent</option>
                  <option value="WRITTEN">Written Signature / Mark</option>
                  <option value="GUARDIAN_ASSISTED">Guardian-Assisted Consent</option>
                </select>
              </div>
            </div>

            {/* Strict Consent Checkboxes */}
            <div style={{ padding: 16, backgroundColor: "var(--neutral-bg)", borderRadius: 12, border: errors.registration_consent_obtained ? "2px solid var(--urgent)" : "1px solid var(--border)", marginTop: 8 }}>
              <label style={{ display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer", fontSize: 14, fontWeight: 600 }}>
                <input
                  type="checkbox"
                  id="reg-consent-chk"
                  checked={formData.registration_consent_obtained}
                  onChange={(e) => handleChange("registration_consent_obtained", e.target.checked)}
                  style={{ width: 20, height: 20, marginTop: 2 }}
                />
                <span>
                  <strong style={{ color: "var(--primary)" }}>Mandatory Registration Consent:</strong> I have informed the citizen about the health record creation, and they have explicitly consented to community care coordination.
                </span>
              </label>
              {errors.registration_consent_obtained && (
                <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 6, marginLeft: 30 }}>
                  {errors.registration_consent_obtained}
                </div>
              )}

              <label style={{ display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer", fontSize: 14, marginTop: 14 }}>
                <input
                  type="checkbox"
                  checked={formData.voice_consent_obtained}
                  onChange={(e) => handleChange("voice_consent_obtained", e.target.checked)}
                  style={{ width: 18, height: 18, marginTop: 2 }}
                />
                <span style={{ color: "var(--text-secondary)" }}>
                  (Optional) Citizen consents to temporary voice transcription assistance for clinical notes.
                </span>
              </label>
            </div>
          </div>
        )}

        {/* STEP 3: Initial Health Profile */}
        {currentStep === 3 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>3. Baseline Health Profile & Medical History</h2>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 12px" }}>
              Record citizen-reported medicines and baseline health factors. (ASHA workers record reported info; they do not prescribe).
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  Blood Group
                </label>
                <select
                  value={formData.blood_group}
                  onChange={(e) => handleChange("blood_group", e.target.value)}
                  style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
                >
                  {options.blood_groups.map((bg: string) => (
                    <option key={bg} value={bg}>{bg}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  Tobacco / Alcohol Exposure
                </label>
                <select
                  value={formData.tobacco_use}
                  onChange={(e) => handleChange("tobacco_use", e.target.value)}
                  style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
                >
                  <option value="NONE">No Tobacco / Smoke Exposure</option>
                  <option value="SMOKELESS">Chewing Tobacco / Gutkha</option>
                  <option value="SMOKING">Bidi / Cigarette</option>
                  <option value="PAST">Past User</option>
                </select>
              </div>
            </div>

            {/* Citizen Reported Medications */}
            <div>
              <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                Citizen-Reported Current Medications
              </label>
              <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <input
                  type="text"
                  value={formData.med_name}
                  onChange={(e) => handleChange("med_name", e.target.value)}
                  placeholder="Medicine Name (e.g. Labetalol 100mg)"
                  style={{ flex: 2, padding: 10, fontSize: 14, borderRadius: 8, border: "1px solid var(--border)" }}
                />
                <button
                  type="button"
                  onClick={() => {
                    if (formData.med_name.trim()) {
                      const newMeds = [...formData.current_medications, { name: formData.med_name.trim(), dose: "Reported", frequency: "Daily" }];
                      setFormData((p: any) => ({ ...p, current_medications: newMeds, med_name: "" }));
                    }
                  }}
                  style={{ padding: "8px 16px", backgroundColor: "var(--primary-light)", color: "var(--primary-dark)", border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer" }}
                >
                  + Add
                </button>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {formData.current_medications.map((m: any, idx: number) => (
                  <span key={idx} style={{ padding: "4px 10px", backgroundColor: "var(--neutral-bg)", borderRadius: 6, fontSize: 13, border: "1px solid var(--border)" }}>
                    💊 {m.name}
                  </span>
                ))}
              </div>
            </div>

            {/* Health Notes */}
            <div>
              <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                General ASHA Observations / Health Notes
              </label>
              <textarea
                rows={3}
                value={formData.health_notes}
                onChange={(e) => handleChange("health_notes", e.target.value)}
                placeholder="Any special baseline observations (allergies, major past illness, surgeries)..."
                style={{ width: "100%", padding: 12, fontSize: 15, borderRadius: 8, border: "1px solid var(--border)", lineHeight: "22px" }}
              />
            </div>
          </div>
        )}

        {/* STEP 4: Current Health Concern */}
        {currentStep === 4 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Current Health Concern</h2>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 8px", lineHeight: "20px" }}>
              The citizen will be registered in the beneficiary directory. If they have a current health concern, record it below to create an active healthcare case.
            </p>

            {/* Single Toggle / Checkbox for Current Health Concern */}
            <div
              style={{
                padding: "16px 20px",
                backgroundColor: formData.create_current_case ? "var(--primary-light)" : "var(--surface)",
                borderRadius: 12,
                border: formData.create_current_case ? "2px solid var(--primary)" : "1px solid var(--border)",
                display: "flex",
                alignItems: "center",
                gap: 12,
                cursor: "pointer"
              }}
              onClick={() => handleChange("create_current_case", !formData.create_current_case)}
            >
              <input
                type="checkbox"
                id="record-health-concern-chk"
                checked={formData.create_current_case}
                onChange={(e) => handleChange("create_current_case", e.target.checked)}
                style={{ width: 22, height: 22, cursor: "pointer" }}
              />
              <label
                htmlFor="record-health-concern-chk"
                style={{ fontSize: 15, fontWeight: 700, color: formData.create_current_case ? "var(--primary-dark)" : "var(--text-primary)", cursor: "pointer", margin: 0 }}
              >
                Record a current health concern now
              </label>
            </div>

            {/* Expanded Health Concern Input Fields when Checked */}
            {formData.create_current_case && (
              <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 4, padding: 18, backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <label style={{ fontSize: 14, fontWeight: 700 }}>
                      Main / Chief Complaint <span style={{ color: "var(--urgent)" }}>*</span>
                    </label>
                    <button
                      type="button"
                      onClick={() => handleStartVoiceIntake("COMPLAINT")}
                      style={{ fontSize: 12, padding: "4px 8px", backgroundColor: "var(--primary-light)", color: "var(--primary-dark)", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 }}
                    >
                      🎙 Speak
                    </button>
                  </div>
                  <input
                    type="text"
                    id="input-chief-complaint"
                    value={formData.chief_complaint}
                    onChange={(e) => handleChange("chief_complaint", e.target.value)}
                    placeholder="e.g. Severe headache and blurred vision for 2 days"
                    style={{ width: "100%", padding: 12, fontSize: 15, borderRadius: 8, border: errors.chief_complaint ? "2px solid var(--urgent)" : "1px solid var(--border)", minHeight: 48 }}
                  />
                  {errors.chief_complaint && (
                    <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 4 }}>
                      {errors.chief_complaint}
                    </div>
                  )}
                </div>

                {/* Common Symptom Pickers */}
                <div>
                  <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
                    Confirmed Symptoms:
                  </label>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {options.symptoms.map((s: any) => {
                      const isSelected = formData.selected_symptoms.includes(s.term);
                      return (
                        <button
                          key={s.id}
                          type="button"
                          onClick={() => {
                            const next = isSelected
                              ? formData.selected_symptoms.filter((x: string) => x !== s.term)
                              : [...formData.selected_symptoms, s.term];
                            handleChange("selected_symptoms", next);
                          }}
                          style={{
                            padding: "8px 14px",
                            borderRadius: 8,
                            border: isSelected ? "2px solid var(--primary)" : "1px solid var(--border)",
                            backgroundColor: isSelected ? "var(--primary-light)" : "var(--surface)",
                            color: isSelected ? "var(--primary-dark)" : "var(--text-primary)",
                            fontSize: 13,
                            fontWeight: 600,
                            cursor: "pointer"
                          }}
                        >
                          {isSelected ? "✓ " : "+ "} {s.term}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Duration, Onset & Severity Grid */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                  <div>
                    <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                      Duration
                    </label>
                    <input
                      type="text"
                      value={formData.duration}
                      onChange={(e) => handleChange("duration", e.target.value)}
                      placeholder="e.g. 3 days"
                      style={{ width: "100%", padding: 10, fontSize: 14, borderRadius: 8, border: "1px solid var(--border)" }}
                    />
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                      Onset
                    </label>
                    <select
                      value={formData.onset}
                      onChange={(e) => handleChange("onset", e.target.value)}
                      style={{ width: "100%", padding: 10, fontSize: 14, borderRadius: 8, border: "1px solid var(--border)" }}
                    >
                      <option value="">Select onset...</option>
                      <option value="SUDDEN">Sudden</option>
                      <option value="GRADUAL">Gradual</option>
                      <option value="CHRONIC_WORSENING">Chronic Worsening</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                      Severity
                    </label>
                    <select
                      value={formData.severity}
                      onChange={(e) => handleChange("severity", e.target.value)}
                      style={{ width: "100%", padding: 10, fontSize: 14, borderRadius: 8, border: "1px solid var(--border)" }}
                    >
                      <option value="MILD">Mild</option>
                      <option value="MODERATE">Moderate</option>
                      <option value="SEVERE">Severe</option>
                    </select>
                  </div>
                </div>

                {/* Spoken Transcript / Reason for Visit */}
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                    ASHA Observations / Spoken Notes
                  </label>
                  <input
                    type="text"
                    value={formData.spoken_transcript}
                    onChange={(e) => handleChange("spoken_transcript", e.target.value)}
                    placeholder="e.g. Citizen appeared fatigued, reported difficulty reading for 2 days"
                    style={{ width: "100%", padding: 10, fontSize: 14, borderRadius: 8, border: "1px solid var(--border)" }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* STEP 5: Vitals & Special Conditions */}
        {currentStep === 5 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>5. Vitals & Special Health Conditions</h2>
            
            {/* Vitals Measured Switch */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 10 }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>Measured Vitals on this Visit?</span>
              <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 14 }}>
                <input
                  type="checkbox"
                  checked={formData.vitals_measured}
                  onChange={(e) => handleChange("vitals_measured", e.target.checked)}
                  style={{ width: 18, height: 18 }}
                />
                <span>Yes, record vitals</span>
              </label>
            </div>

            {formData.vitals_measured ? (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div>
                  <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                    Blood Pressure (Systolic / Diastolic)
                  </label>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      type="number"
                      id="input-systolic-bp"
                      value={formData.systolic_bp}
                      onChange={(e) => handleChange("systolic_bp", e.target.value)}
                      placeholder="Systolic (120)"
                      style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: errors.systolic_bp ? "2px solid var(--urgent)" : "1px solid var(--border)", minHeight: 48 }}
                    />
                    <span>/</span>
                    <input
                      type="number"
                      id="input-diastolic-bp"
                      value={formData.diastolic_bp}
                      onChange={(e) => handleChange("diastolic_bp", e.target.value)}
                      placeholder="Diastolic (80)"
                      style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: errors.diastolic_bp ? "2px solid var(--urgent)" : "1px solid var(--border)", minHeight: 48 }}
                    />
                  </div>
                  {errors.systolic_bp && <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 4 }}>{errors.systolic_bp}</div>}
                </div>

                <div>
                  <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                    SpO₂ (%)
                  </label>
                  <input
                    type="number"
                    value={formData.spo2}
                    onChange={(e) => handleChange("spo2", e.target.value)}
                    placeholder="e.g. 98"
                    style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: errors.spo2 ? "2px solid var(--urgent)" : "1px solid var(--border)", minHeight: 48 }}
                  />
                  {errors.spo2 && <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 4 }}>{errors.spo2}</div>}
                </div>

                <div>
                  <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                    Pulse Rate (bpm)
                  </label>
                  <input
                    type="number"
                    value={formData.pulse}
                    onChange={(e) => handleChange("pulse", e.target.value)}
                    placeholder="e.g. 76"
                    style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                    Body Temperature (°C)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.temperature_c}
                    onChange={(e) => handleChange("temperature_c", e.target.value)}
                    placeholder="e.g. 37.0"
                    style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
                  />
                </div>
              </div>
            ) : (
              <div>
                <label style={{ display: "block", fontSize: 14, fontWeight: 600, marginBottom: 6 }}>
                  Reason Vitals Not Measured
                </label>
                <input
                  type="text"
                  value={formData.unmeasured_reason}
                  onChange={(e) => handleChange("unmeasured_reason", e.target.value)}
                  placeholder="e.g. Device undergoing calibration or citizen refused measurement"
                  style={{ width: "100%", padding: 12, fontSize: 15, borderRadius: 8, border: "1px solid var(--border)" }}
                />
              </div>
            )}

            {/* Special Condition Selector */}
            <div style={{ marginTop: 12 }}>
              <label style={{ display: "block", fontSize: 14, fontWeight: 700, marginBottom: 6 }}>
                Special Health Programme / Maternal Condition:
              </label>
              <select
                id="select-condition-type"
                value={formData.condition_type}
                onChange={(e) => handleChange("condition_type", e.target.value)}
                style={{ width: "100%", padding: 12, fontSize: 16, borderRadius: 8, border: "1px solid var(--border)", minHeight: 48 }}
              >
                <option value="NONE">None / General</option>
                <option value="PREGNANCY">Antenatal / Pregnancy Care</option>
                <option value="POSTNATAL">Postnatal Mother & Newborn Care</option>
                <option value="CHILD">Child Health (0-5 Yrs)</option>
                <option value="NCD">Hypertension / Diabetes / NCD</option>
                <option value="TB">Tuberculosis / Respiratory Screening</option>
              </select>
            </div>

            {/* Conditional Maternal Fields */}
            {formData.condition_type === "PREGNANCY" && (
              <div style={{ padding: 16, backgroundColor: "#FFF5F7", borderRadius: 12, border: "1px solid #FFCCD5", display: "flex", flexDirection: "column", gap: 14 }}>
                <div style={{ fontSize: 15, fontWeight: 700, color: "#C2185B" }}>
                  🤰 Antenatal & Maternal Health Checklist
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Last Menstrual Period (LMP)</label>
                    <input
                      type="date"
                      value={formData.lmp_date}
                      onChange={(e) => handleChange("lmp_date", e.target.value)}
                      style={{ width: "100%", padding: 10, fontSize: 14, borderRadius: 8, border: "1px solid var(--border)" }}
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Estimated Delivery Date (EDD)</label>
                    <input
                      type="date"
                      value={formData.edd_date}
                      onChange={(e) => handleChange("edd_date", e.target.value)}
                      style={{ width: "100%", padding: 10, fontSize: 14, borderRadius: 8, border: "1px solid var(--border)" }}
                    />
                  </div>
                </div>

                <div style={{ fontSize: 13, fontWeight: 600, color: "#C2185B", marginTop: 4 }}>
                  Maternal Warning Signs:
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                    <input type="checkbox" checked={formData.mat_headache} onChange={(e) => handleChange("mat_headache", e.target.checked)} />
                    <span>Severe Persistent Headache</span>
                  </label>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                    <input type="checkbox" checked={formData.mat_vision} onChange={(e) => handleChange("mat_vision", e.target.checked)} />
                    <span>Blurred Vision / Visual Disturbance</span>
                  </label>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                    <input type="checkbox" checked={formData.mat_swelling} onChange={(e) => handleChange("mat_swelling", e.target.checked)} />
                    <span>Swelling in Feet / Edema</span>
                  </label>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer" }}>
                    <input type="checkbox" checked={formData.mat_bleeding} onChange={(e) => handleChange("mat_bleeding", e.target.checked)} />
                    <span>Vaginal Bleeding / Spotting</span>
                  </label>
                </div>
              </div>
            )}
          </div>
        )}

        {/* STEP 6: Follow-up and Referral */}
        {/* STEP 6: Follow-up and Referral */}
        {currentStep === 6 && (() => {
          const sbpVal = parseInt(formData.systolic_bp) || 0;
          const dbpVal = parseInt(formData.diastolic_bp) || 0;
          const isPregnantVal = formData.condition_type === "PREGNANCY";
          const hasHighBPVal = sbpVal >= 140 || dbpVal >= 90;
          const hasDangerSignsVal = formData.mat_headache || formData.mat_vision || formData.mat_swelling || formData.mat_bleeding;
          const isUrgentSafetyTriggeredVal = isPregnantVal && (hasHighBPVal || hasDangerSignsVal);

          return (
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>6. Follow-up & PHC Referral Coordination</h2>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 12px" }}>
                Coordinate institutional referral or schedule community follow-up visits.
              </p>

              {/* Urgent Safety Warning Banner */}
              {isUrgentSafetyTriggeredVal && (
                <div style={{ padding: 16, backgroundColor: "var(--urgent-bg)", borderRadius: 12, border: "1px solid #F5C6CB", color: "var(--urgent)", marginBottom: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 700, marginBottom: 4 }}>
                    <WarningIcon size={20} color="var(--urgent)" />
                    <span>Warning signs detected. Urgent professional evaluation is recommended.</span>
                  </div>
                  <div style={{ fontSize: 13, color: "var(--text-primary)" }}>
                    High Blood Pressure ({sbpVal}/{dbpVal} mmHg) or pregnancy danger signs require referring the citizen to a medical officer. If the citizen declines, you must document their refusal reason below.
                  </div>
                </div>
              )}

              {/* Referral Decision */}
              <div style={{ padding: 16, backgroundColor: formData.referral_required ? "var(--urgent-bg)" : "var(--neutral-bg)", borderRadius: 12, border: "1px solid var(--border)" }}>
                <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 15, fontWeight: 700, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    id="chk-refer-phc"
                    checked={formData.referral_required}
                    onChange={(e) => handleChange("referral_required", e.target.checked)}
                    style={{ width: 20, height: 20 }}
                  />
                  <span>Refer the citizen to PHC for Medical Officer review</span>
                </label>
                {errors.referral_required && (
                  <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 6, fontWeight: 600 }}>
                    ⚠️ {errors.referral_required}
                  </div>
                )}

                {formData.referral_required && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 14 }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                      <div>
                        <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                          Referral Facility
                        </label>
                        <select
                          value={formData.referral_facility_id}
                          onChange={(e) => handleChange("referral_facility_id", e.target.value)}
                          style={{ width: "100%", padding: 10, fontSize: 15, borderRadius: 8, border: "1px solid var(--border)" }}
                        >
                          {options.facilities.map((f: any) => (
                            <option key={f.id} value={f.id}>{f.name} ({f.approx_distance_km} km)</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                          Urgency Level
                        </label>
                        <select
                          value={formData.referral_urgency}
                          onChange={(e) => handleChange("referral_urgency", e.target.value)}
                          style={{ width: "100%", padding: 10, fontSize: 15, borderRadius: 8, border: "1px solid var(--border)" }}
                        >
                          <option value="URGENT">Urgent (Immediate Medical Evaluation)</option>
                          <option value="HIGH">High Priority (Within 24 Hours)</option>
                          <option value="ROUTINE">Routine / Outpatient Referral</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                        Referral Reason / Clinical Note for Medical Officer
                      </label>
                      <input
                        type="text"
                        value={formData.referral_reason}
                        onChange={(e) => handleChange("referral_reason", e.target.value)}
                        placeholder="e.g. Elevated BP 150/100 with headache during 3rd trimester"
                        style={{ width: "100%", padding: 10, fontSize: 15, borderRadius: 8, border: errors.referral_reason ? "2px solid var(--urgent)" : "1px solid var(--border)" }}
                      />
                      {errors.referral_reason && (
                        <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 4 }}>
                          {errors.referral_reason}
                        </div>
                      )}
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 4 }}>
                      <div>
                        <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                          Citizen Response
                        </label>
                        <select
                          value={formData.referral_accepted ? "ACCEPTED" : "REFUSED"}
                          onChange={(e) => handleChange("referral_accepted", e.target.value === "ACCEPTED")}
                          style={{ width: "100%", padding: 10, fontSize: 15, borderRadius: 8, border: "1px solid var(--border)" }}
                        >
                          <option value="ACCEPTED">Accepted / Will Attend PHC</option>
                          <option value="REFUSED">Refused / Declined Referral</option>
                        </select>
                      </div>

                      {!formData.referral_accepted && (
                        <div>
                          <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                            Reason for Refusal
                          </label>
                          <input
                            type="text"
                            value={formData.referral_refusal_reason}
                            onChange={(e) => handleChange("referral_refusal_reason", e.target.value)}
                            placeholder="e.g. Lack of transport, family members unavailable"
                            style={{ width: "100%", padding: 10, fontSize: 15, borderRadius: 8, border: errors.referral_refusal_reason ? "2px solid var(--urgent)" : "1px solid var(--border)" }}
                          />
                          {errors.referral_refusal_reason && (
                            <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 4 }}>
                              {errors.referral_refusal_reason}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Community Follow-up */}
              <div style={{ padding: 16, backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
                <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 15, fontWeight: 600, cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    id="chk-schedule-followup"
                    checked={formData.followup_required}
                    onChange={(e) => handleChange("followup_required", e.target.checked)}
                    style={{ width: 18, height: 18 }}
                  />
                  <span>Schedule an ASHA follow-up visit</span>
                </label>
                {formData.followup_required && (
                  <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 12 }}>
                    <div>
                      <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Follow-up Date</label>
                      <input
                        type="date"
                        value={formData.followup_date}
                        onChange={(e) => handleChange("followup_date", e.target.value)}
                        style={{ width: "100%", padding: 10, fontSize: 15, borderRadius: 8, border: errors.followup_date ? "2px solid var(--urgent)" : "1px solid var(--border)" }}
                      />
                      {errors.followup_date && (
                        <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 4 }}>
                          {errors.followup_date}
                        </div>
                      )}
                    </div>

                    <div>
                      <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                        Follow-up Purpose / Instructions
                      </label>
                      <input
                        type="text"
                        value={formData.followup_purpose}
                        onChange={(e) => handleChange("followup_purpose", e.target.value)}
                        placeholder="e.g. Record weekly BP, check medicine adherence"
                        style={{ width: "100%", padding: 10, fontSize: 15, borderRadius: 8, border: errors.followup_purpose ? "2px solid var(--urgent)" : "1px solid var(--border)" }}
                      />
                      {errors.followup_purpose && (
                        <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 4 }}>
                          {errors.followup_purpose}
                        </div>
                      )}
                    </div>

                    <div>
                      <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                        Follow-up Notes / ASHA Instructions
                      </label>
                      <input
                        type="text"
                        value={formData.followup_notes}
                        onChange={(e) => handleChange("followup_notes", e.target.value)}
                        placeholder="ASHA-confirmed follow-up instructions"
                        style={{ width: "100%", padding: 10, fontSize: 15, borderRadius: 8, border: "1px solid var(--border)" }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })()}

        {/* STEP 7: Documents, Review and Final Submission */}
        {currentStep === 7 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>7. Review & Submit Registration</h2>
            <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 12px" }}>
              Carefully verify all recorded values before committing the citizen to the health system.
            </p>

            {/* Review Cards */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ padding: 14, backgroundColor: "var(--neutral-bg)", borderRadius: 10 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "var(--primary)" }}>👤 Identity & Location</div>
                <div style={{ fontSize: 13, color: "var(--text-primary)", marginTop: 4 }}>
                  <strong>{formData.full_name}</strong> · {formData.sex} · Age: {formData.approximate_age || "N/A"} · Village: {formData.village_name}
                  {formData.phone && <span> · Phone: {formData.phone}</span>}
                  {formData.abha_number && <span> · ABHA: {formData.abha_number}</span>}
                </div>
              </div>

              <div style={{ padding: 14, backgroundColor: "var(--neutral-bg)", borderRadius: 10 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "var(--primary)" }}>🤝 Household & Consent</div>
                <div style={{ fontSize: 13, color: "var(--text-primary)", marginTop: 4 }}>
                  Language: {formData.preferred_language === "mr-IN" ? "मराठी" : "English"} · Household: {formData.household_category} · Consent: {formData.registration_consent_obtained ? "✓ Confirmed" : "✗ Missing"}
                </div>
              </div>

              {formData.create_current_case && (
                <div style={{ padding: 14, backgroundColor: "var(--neutral-bg)", borderRadius: 10 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: "var(--primary)" }}>🩺 Current Concern & Vitals</div>
                  <div style={{ fontSize: 13, color: "var(--text-primary)", marginTop: 4 }}>
                    Complaint: {formData.chief_complaint || "None"}
                    {formData.vitals_measured && formData.systolic_bp && (
                      <div>BP: {formData.systolic_bp}/{formData.diastolic_bp} mmHg · SpO2: {formData.spo2 || "N/A"}%</div>
                    )}
                  </div>
                </div>
              )}

              {formData.referral_required && (
                <div style={{ padding: 14, backgroundColor: "var(--urgent-bg)", borderRadius: 10, border: "1px solid #F5C6CB" }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: "var(--urgent)" }}>🏥 Referral to PHC</div>
                  <div style={{ fontSize: 13, color: "var(--text-primary)", marginTop: 4 }}>
                    Facility: {formData.referral_facility_id} · Urgency: {formData.referral_urgency} · Reason: {formData.referral_reason || "Medical evaluation"}
                  </div>
                </div>
              )}
            </div>

            {/* Mandatory ASHA Affirmation */}
            <div style={{ padding: 16, backgroundColor: "var(--primary-light)", borderRadius: 12, border: errors.accuracy_confirmed_by_asha ? "2px solid var(--urgent)" : "1px solid var(--primary)", marginTop: 8 }}>
              <label style={{ display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer", fontSize: 14, fontWeight: 700, color: "var(--primary-dark)" }}>
                <input
                  type="checkbox"
                  id="final-asha-confirm-chk"
                  checked={formData.accuracy_confirmed_by_asha}
                  onChange={(e) => handleChange("accuracy_confirmed_by_asha", e.target.checked)}
                  style={{ width: 20, height: 20, marginTop: 2 }}
                />
                <span>
                  I have reviewed this information with the citizen and confirm that it is accurate to the best of my knowledge.
                </span>
              </label>
              {errors.accuracy_confirmed_by_asha && (
                <div style={{ fontSize: 12, color: "var(--urgent)", marginTop: 6, marginLeft: 30 }}>
                  {errors.accuracy_confirmed_by_asha}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Sticky Bottom Action Navigation Bar */}
      <div
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          backgroundColor: "var(--surface)",
          borderTop: "1px solid var(--border)",
          padding: "16px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          zIndex: 100,
          boxShadow: "0 -4px 12px rgba(0,0,0,0.06)"
        }}
      >
        <div style={{ display: "flex", gap: 10 }}>
          {currentStep > 1 && (
            <button
              onClick={handlePrevStep}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "10px 18px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                backgroundColor: "var(--surface)",
                fontSize: 14,
                fontWeight: 600,
                cursor: "pointer",
                minHeight: 48
              }}
            >
              <ChevronLeftIcon size={18} color="var(--text-primary)" />
              <span>Back</span>
            </button>
          )}

          <button
            onClick={() => saveDraftToDexie()}
            style={{
              padding: "10px 16px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              backgroundColor: "var(--neutral-bg)",
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              minHeight: 48
            }}
          >
            💾 Save Draft
          </button>
        </div>

        {currentStep < WIZARD_STEPS.length ? (
          <button
            id="wizard-next-step-btn"
            onClick={handleNextStep}
            style={{
              padding: "12px 24px",
              backgroundColor: "var(--primary)",
              color: "#FFF",
              borderRadius: 8,
              border: "none",
              fontSize: 15,
              fontWeight: 700,
              cursor: "pointer",
              minHeight: 48
            }}
          >
            Next Step →
          </button>
        ) : (
          <button
            id="submit-patient-btn"
            disabled={isSubmitting}
            onClick={handleSubmitRegistration}
            style={{
              padding: "12px 28px",
              backgroundColor: "var(--success)",
              color: "#FFF",
              borderRadius: 8,
              border: "none",
              fontSize: 15,
              fontWeight: 700,
              cursor: "pointer",
              minHeight: 48
            }}
          >
            {isSubmitting ? "Saving Patient..." : "✓ Complete & Save Patient"}
          </button>
        )}
      </div>

      {/* Duplicate Patient Alert Modal */}
      {duplicateModalOpen && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: 16 }}>
          <div style={{ backgroundColor: "var(--surface)", width: "100%", maxWidth: 560, borderRadius: 16, padding: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--urgent)", marginBottom: 12 }}>
              <WarningIcon size={24} color="var(--urgent)" />
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>Potential Existing Patient Found</h3>
            </div>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 16 }}>
              A matching citizen record already exists in the system. Please verify to prevent duplicate entries:
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
              {potentialDuplicates.map((dup) => (
                <div key={dup.id} style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{dup.display_name} (Age: {dup.age_estimate || "N/A"})</div>
                    <div style={{ color: "var(--text-secondary)", marginTop: 2 }}>
                      Village: {dup.village_name} · Phone: {dup.masked_phone || "N/A"} · Reason: {dup.similarity_reason}
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setDuplicateModalOpen(false);
                      navigate(`/asha/people?search=${encodeURIComponent(dup.display_name)}`);
                    }}
                    style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid var(--primary)", color: "var(--primary)", backgroundColor: "transparent", cursor: "pointer", fontSize: 12, fontWeight: 600 }}
                  >
                    Open Profile
                  </button>
                </div>
              ))}
            </div>

            <div>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                Reason to register as a separate citizen (if continuing as new):
              </label>
              <input
                type="text"
                value={duplicateOverrideReason}
                onChange={(e) => setDuplicateOverrideReason(e.target.value)}
                placeholder="e.g. Same name but different family ID and habitation"
                style={{ width: "100%", padding: 10, fontSize: 14, borderRadius: 8, border: "1px solid var(--border)", marginBottom: 16 }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                onClick={() => setDuplicateModalOpen(false)}
                style={{ padding: "10px 16px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer", fontWeight: 600 }}
              >
                Back to Edit
              </button>
              <button
                disabled={!duplicateOverrideReason.trim()}
                onClick={() => {
                  setDuplicateModalOpen(false);
                  setCurrentStep(2);
                }}
                style={{
                  padding: "10px 18px",
                  borderRadius: 8,
                  border: "none",
                  backgroundColor: duplicateOverrideReason.trim() ? "var(--primary)" : "var(--border)",
                  color: "#FFF",
                  fontWeight: 700,
                  cursor: duplicateOverrideReason.trim() ? "pointer" : "not-allowed"
                }}
              >
                Confirm & Continue as New
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Voice Assistant Structured Modal */}
      {voiceModalOpen && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, backgroundColor: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999, padding: 16 }}>
          <div style={{ backgroundColor: "var(--surface)", width: "100%", maxWidth: 560, borderRadius: 16, padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
                🎙 Voice Intake Assistant ({formData.preferred_language === "mr-IN" ? "मराठी" : "हिंदी / English"})
                <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 12, backgroundColor: voiceProviderState === "Live" ? "var(--success-bg)" : "var(--neutral-bg)", color: voiceProviderState === "Live" ? "var(--success)" : "var(--text-secondary)", fontWeight: 700 }}>
                  {voiceProviderState}
                </span>
              </h3>
              <button onClick={() => setVoiceModalOpen(false)} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer" }}>✕</button>
            </div>

            {isRecording ? (
              <div style={{ padding: 36, textAlign: "center" }}>
                <div style={{ width: 60, height: 60, borderRadius: "50%", backgroundColor: "rgba(229,62,62,0.15)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px", animation: "pulse 1.5s infinite" }}>
                  <MicIcon size={30} color="#E53E3E" />
                </div>
                <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>Listening to voice input...</div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 6 }}>Speak details clearly in Marathi, Hindi or English</div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8, fontSize: 14, fontStyle: "italic" }}>
                  "{voiceTranscript}"
                </div>

                {voiceExtractedFields && (
                  <div style={{ padding: 14, backgroundColor: "var(--primary-light)", borderRadius: 10 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "var(--primary-dark)", marginBottom: 6 }}>
                      Extracted Structured Values (Review before applying):
                    </div>
                    {Object.entries(voiceExtractedFields).map(([k, v]: [string, any]) => (
                      <div key={k} style={{ fontSize: 13, display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ textTransform: "capitalize" }}><strong>{k.replace("_", " ")}</strong>:</span>
                        <span>{typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8 }}>
                  <button
                    onClick={() => setVoiceModalOpen(false)}
                    style={{ padding: "10px 16px", borderRadius: 8, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer" }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleApplyVoiceFields}
                    style={{ padding: "10px 20px", borderRadius: 8, border: "none", backgroundColor: "var(--primary)", color: "#FFF", fontWeight: 700, cursor: "pointer" }}
                  >
                    Apply Extracted Values to Form
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
