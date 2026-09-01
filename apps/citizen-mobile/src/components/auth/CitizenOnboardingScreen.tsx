import React, { useState } from "react";
import { useLanguage } from "@aarogya/i18n";
import { User, Check, ArrowRight, Loader2, AlertCircle, Shield } from "lucide-react";
import { useCitizenAuth } from "../../context/CitizenAuthContext";

interface CitizenOnboardingScreenProps {
  onSuccess: () => void;
}

export const CitizenOnboardingScreen: React.FC<CitizenOnboardingScreenProps> = ({ onSuccess }) => {
  const { t, locale } = useLanguage();
  const { pendingPhone, completeOnboarding } = useCitizenAuth();

  const [fullName, setFullName] = useState<string>("");
  const [age, setAge] = useState<string>("");
  const [gender, setGender] = useState<string>("FEMALE");
  const [village, setVillage] = useState<string>("Kalyanpur");
  const [district, setDistrict] = useState<string>("District 04");
  const [pincode, setPincode] = useState<string>("411001");
  const [emergencyName, setEmergencyName] = useState<string>("");
  const [emergencyPhone, setEmergencyPhone] = useState<string>("");
  const [emergencyRelation, setEmergencyRelation] = useState<string>("SPOUSE");
  const [abhaReference, setAbhaReference] = useState<string>("");
  const [consentObtained, setConsentObtained] = useState<boolean>(true);

  const [loading, setLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim()) {
      setErrorMessage(t("citizen.full_name_required", "Please enter your full name"));
      return;
    }

    if (!consentObtained) {
      setErrorMessage(t("citizen.consent_required", "Please accept the privacy consent to continue"));
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await completeOnboarding({
        full_name: fullName.trim(),
        age: age ? parseInt(age, 10) : undefined,
        gender,
        village,
        district,
        pincode,
        preferred_language: locale || "mr-IN",
        emergency_contact_name: emergencyName ? emergencyName.trim() : undefined,
        emergency_contact_phone: emergencyPhone ? emergencyPhone.trim() : undefined,
        emergency_contact_relation: emergencyRelation,
        abha_reference: abhaReference ? abhaReference.trim() : undefined,
        consent_obtained: consentObtained
      });

      if (res.success) {
        onSuccess();
      } else {
        const errorText = typeof res.error === "string" 
          ? res.error 
          : (res.error && typeof res.error === "object" ? ((res.error as any).message || (res.error as any).detail || JSON.stringify(res.error)) : "Onboarding failed");
        setErrorMessage(errorText);
      }
    } catch (err: any) {
      const errorText = typeof err?.message === "string" 
        ? err.message 
        : (typeof err === "string" ? err : (err && typeof err === "object" ? (err.message || err.detail || JSON.stringify(err)) : "Onboarding failed"));
      setErrorMessage(errorText);
    } finally {
      setLoading(false);
    }
  };


  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#F8FAFC",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "20px 12px",
        fontFamily: "'Noto Sans', 'Noto Sans Devanagari', sans-serif"
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 480,
          backgroundColor: "#FFFFFF",
          borderRadius: 24,
          boxShadow: "0 12px 40px rgba(0, 0, 0, 0.08)",
          border: "1px solid #E2E8F0",
          overflow: "hidden"
        }}
      >
        {/* Header */}
        <div
          style={{
            background: "linear-gradient(135deg, #1565C0 0%, #1E40AF 100%)",
            color: "#FFFFFF",
            padding: "20px",
            textAlign: "center"
          }}
        >
          <div
            style={{
              width: 50,
              height: 50,
              borderRadius: 16,
              backgroundColor: "#FFFFFF",
              color: "#1565C0",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 10px"
            }}
          >
            <User size={26} />
          </div>
          <h2 id="title-citizen-onboarding" style={{ fontSize: 20, fontWeight: 800, margin: "0 0 4px" }}>
            {t("citizen.onboarding_title", "Complete Citizen Registration")}
          </h2>
          <p style={{ fontSize: 12, opacity: 0.9, margin: 0 }}>
            {t("citizen.onboarding_desc", "Please provide your basic information to set up your rural healthcare profile.")}
          </p>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: "20px", display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Full Name */}
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 4 }}>
              {t("citizen.full_name_label", "Full Name")} *
            </label>
            <input
              type="text"
              id="input-onboarding-fullname"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder={t("citizen.full_name_placeholder", "e.g. Ramesh Patil")}
              style={{
                width: "100%",
                padding: "12px 14px",
                borderRadius: 12,
                border: "2px solid #CBD5E1",
                fontSize: 14,
                fontWeight: 600,
                color: "#0F172A",
                boxSizing: "border-box"
              }}
            />
          </div>

          {/* Age & Gender */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 4 }}>
                {t("citizen.age_label", "Age (Years)")}
              </label>
              <input
                type="number"
                id="input-onboarding-age"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                placeholder="30"
                min={1}
                max={120}
                style={{
                  width: "100%",
                  padding: "12px 14px",
                  borderRadius: 12,
                  border: "2px solid #CBD5E1",
                  fontSize: 14,
                  fontWeight: 600,
                  color: "#0F172A",
                  boxSizing: "border-box"
                }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 4 }}>
                {t("citizen.gender_label", "Gender")}
              </label>
              <select
                id="select-onboarding-gender"
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                style={{
                  width: "100%",
                  padding: "12px 14px",
                  borderRadius: 12,
                  border: "2px solid #CBD5E1",
                  fontSize: 14,
                  fontWeight: 600,
                  color: "#0F172A",
                  boxSizing: "border-box",
                  backgroundColor: "#FFFFFF"
                }}
              >
                <option value="FEMALE">{t("citizen.female", "Female")}</option>
                <option value="MALE">{t("citizen.male", "Male")}</option>
                <option value="OTHER">{t("citizen.other", "Other")}</option>
              </select>
            </div>
          </div>

          {/* Village & Pincode */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 4 }}>
                {t("citizen.village_label", "Village")}
              </label>
              <input
                type="text"
                id="input-onboarding-village"
                value={village}
                onChange={(e) => setVillage(e.target.value)}
                style={{
                  width: "100%",
                  padding: "12px 14px",
                  borderRadius: 12,
                  border: "2px solid #CBD5E1",
                  fontSize: 14,
                  fontWeight: 600,
                  color: "#0F172A",
                  boxSizing: "border-box"
                }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 4 }}>
                {t("citizen.pincode_label", "PIN Code")}
              </label>
              <input
                type="text"
                id="input-onboarding-pincode"
                value={pincode}
                onChange={(e) => setPincode(e.target.value)}
                style={{
                  width: "100%",
                  padding: "12px 14px",
                  borderRadius: 12,
                  border: "2px solid #CBD5E1",
                  fontSize: 14,
                  fontWeight: 600,
                  color: "#0F172A",
                  boxSizing: "border-box"
                }}
              />
            </div>
          </div>

          {/* Optional ABHA */}
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 2 }}>
              {t("citizen.abha_optional_label", "ABHA Number (Optional)")}
            </label>
            <p style={{ fontSize: 11, color: "#64748B", margin: "0 0 4px" }}>
              {t("citizen.abha_optional_hint", "ABHA is optional and not required for registration or scheme eligibility.")}
            </p>
            <input
              type="text"
              id="input-onboarding-abha"
              value={abhaReference}
              onChange={(e) => setAbhaReference(e.target.value)}
              placeholder="91-XXXX-XXXX-XXXX"
              style={{
                width: "100%",
                padding: "12px 14px",
                borderRadius: 12,
                border: "2px solid #CBD5E1",
                fontSize: 14,
                fontWeight: 600,
                color: "#0F172A",
                boxSizing: "border-box"
              }}
            />
          </div>

          {/* Emergency Contact */}
          <div style={{ backgroundColor: "#F8FAFC", padding: 12, borderRadius: 14, border: "1px solid #E2E8F0" }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: "#334155", marginBottom: 8 }}>
              {t("citizen.emergency_contact", "Emergency Contact (Optional)")}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <input
                type="text"
                id="input-onboarding-emergency-name"
                placeholder={t("common.name", "Contact Name")}
                value={emergencyName}
                onChange={(e) => setEmergencyName(e.target.value)}
                style={{ padding: "10px", borderRadius: 10, border: "1px solid #CBD5E1", fontSize: 13 }}
              />
              <input
                type="tel"
                id="input-onboarding-emergency-phone"
                placeholder={t("common.phone", "Phone")}
                value={emergencyPhone}
                onChange={(e) => setEmergencyPhone(e.target.value)}
                style={{ padding: "10px", borderRadius: 10, border: "1px solid #CBD5E1", fontSize: 13 }}
              />
            </div>
          </div>

          {/* Consent Checkbox */}
          <label style={{ display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer", marginTop: 4 }}>
            <input
              type="checkbox"
              id="checkbox-onboarding-consent"
              checked={consentObtained}
              onChange={(e) => setConsentObtained(e.target.checked)}
              style={{ width: 18, height: 18, marginTop: 2 }}
            />
            <span style={{ fontSize: 12, color: "#475569", lineHeight: 1.4, fontWeight: 600 }}>
              {t("citizen.privacy_consent_checkbox", "I acknowledge and give explicit consent for storing my health records securely under DPDP Act.")}
            </span>
          </label>

          {errorMessage && (
            <div
              style={{
                padding: "10px 14px",
                backgroundColor: "#FEF2F2",
                borderRadius: 12,
                border: "1px solid #FCA5A5",
                color: "#B91C1C",
                fontSize: 12,
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: 6
              }}
            >
              <AlertCircle size={16} />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            id="btn-onboarding-submit"
            disabled={loading || !fullName.trim()}
            style={{
              minHeight: 48,
              width: "100%",
              padding: "14px",
              borderRadius: 16,
              backgroundColor: "#2563EB",
              color: "#FFFFFF",
              border: "none",
              fontSize: 16,
              fontWeight: 800,
              cursor: loading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              boxShadow: "0 4px 14px rgba(37, 99, 235, 0.25)"
            }}
          >
            {loading ? <Loader2 size={20} className="animate-spin" /> : <Check size={20} />}
            <span>{t("citizen.complete_registration", "Complete Registration & Enter Home")}</span>
          </button>
        </form>
      </div>
    </div>
  );
};
