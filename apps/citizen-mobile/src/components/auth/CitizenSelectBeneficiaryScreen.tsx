import React from "react";
import { useLanguage } from "@aarogya/i18n";
import { User, Users, Check, ArrowRight, Plus } from "lucide-react";
import { useCitizenAuth } from "../../context/CitizenAuthContext";
import { BeneficiaryOption } from "@aarogya/shared-types";

interface CitizenSelectBeneficiaryScreenProps {
  onContinue: () => void;
}

export const CitizenSelectBeneficiaryScreen: React.FC<CitizenSelectBeneficiaryScreenProps> = ({
  onContinue
}) => {
  const { t } = useLanguage();
  const { authorizedBeneficiaries, activeBeneficiary, selectBeneficiary } = useCitizenAuth();

  const handleSelect = (beneficiary: BeneficiaryOption) => {
    selectBeneficiary(beneficiary);
    onContinue();
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
          maxWidth: 440,
          backgroundColor: "#FFFFFF",
          borderRadius: 24,
          boxShadow: "0 12px 40px rgba(0, 0, 0, 0.08)",
          border: "1px solid #E2E8F0",
          overflow: "hidden",
          padding: "24px 20px"
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 20 }}>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: 16,
              backgroundColor: "#EFF6FF",
              color: "#2563EB",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 12px"
            }}
          >
            <Users size={28} />
          </div>
          <h2 style={{ fontSize: 20, fontWeight: 800, color: "#0F172A", margin: "0 0 4px" }}>
            {t("citizen.select_beneficiary_title", "Who is this care for?")}
          </h2>
          <p style={{ fontSize: 13, color: "#64748B", margin: 0 }}>
            {t("citizen.select_beneficiary_desc", "Select yourself or a family member to personalize your care experience.")}
          </p>
        </div>

        {/* Beneficiary Options */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
          {authorizedBeneficiaries.map((b) => {
            const isSelected = activeBeneficiary?.beneficiaryId === b.beneficiaryId;
            return (
              <button
                key={b.beneficiaryId}
                type="button"
                onClick={() => handleSelect(b)}
                id={`btn-select-beneficiary-${b.beneficiaryId}`}
                style={{
                  minHeight: 48,
                  padding: "14px 16px",
                  borderRadius: 16,
                  border: isSelected ? "2px solid #2563EB" : "2px solid #E2E8F0",
                  backgroundColor: isSelected ? "#EFF6FF" : "#FFFFFF",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  cursor: "pointer",
                  textAlign: "left"
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 12,
                      backgroundColor: isSelected ? "#2563EB" : "#F1F5F9",
                      color: isSelected ? "#FFFFFF" : "#475569",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center"
                    }}
                  >
                    <User size={20} />
                  </div>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>
                      {b.displayName}
                    </div>
                    <div style={{ fontSize: 12, color: "#64748B", fontWeight: 600 }}>
                      {b.relationship} {b.age ? `• ${b.age} yrs` : ""} {b.gender ? `• ${b.gender}` : ""}
                    </div>
                  </div>
                </div>

                {isSelected && (
                  <div
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: "50%",
                      backgroundColor: "#2563EB",
                      color: "#FFFFFF",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center"
                    }}
                  >
                    <Check size={16} strokeWidth={3} />
                  </div>
                )}
              </button>
            );
          })}
        </div>

        {/* Continue Button */}
        <button
          type="button"
          onClick={onContinue}
          id="btn-beneficiary-continue-home"
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
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            boxShadow: "0 4px 14px rgba(37, 99, 235, 0.25)"
          }}
        >
          <span>{t("common.continue", "Continue")}</span>
          <ArrowRight size={20} />
        </button>
      </div>
    </div>
  );
};
