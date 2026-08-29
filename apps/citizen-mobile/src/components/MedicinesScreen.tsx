import React, { useState, useEffect } from "react";
import { Pill, FileText, CheckCircle2, AlertCircle, Calendar, ArrowLeft } from "lucide-react";
import { useLanguage } from "@aarogya/i18n";
import { apiClient } from "@aarogya/api-client";

interface MedicinesScreenProps {
  onBack?: () => void;
}

export const MedicinesScreen: React.FC<MedicinesScreenProps> = ({ onBack }) => {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<"prescriptions" | "tests" | "followups">("prescriptions");
  const [prescriptions, setPrescriptions] = useState<any[]>([]);
  const [investigations, setInvestigations] = useState<any[]>([]);
  const [followups, setFollowups] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [rxRes, invRes, folRes] = await Promise.all([
          apiClient.getCitizenPrescriptions(),
          apiClient.getCitizenInvestigations(),
          apiClient.getCitizenFollowups()
        ]);
        setPrescriptions(rxRes?.data || rxRes || []);
        setInvestigations(invRes?.data || invRes || []);
        setFollowups(folRes?.data || folRes || []);
      } catch (err) {
        console.error("Failed to fetch medicines data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const tabs = [
    { key: "prescriptions", label: t("navigation.prescriptions", "Prescriptions") },
    { key: "tests", label: t("navigation.investigations", "Lab Investigations") },
    { key: "followups", label: t("navigation.followups", "Follow-ups") }
  ];

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {onBack && (
          <button onClick={onBack} style={{ border: "none", background: "#F1F5F9", padding: 8, borderRadius: "50%", cursor: "pointer" }}>
            <ArrowLeft size={20} color="#334155" />
          </button>
        )}
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 800, color: "#0F172A", margin: 0 }}>
            {t("citizen.my_medicines", "My Medicines & Prescriptions")}
          </h2>
          <div style={{ fontSize: 12, color: "#64748B" }}>
            {t("citizen.my_medicines_tests", "Prescriptions, lab tests and follow-ups")}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid #E2E8F0" }}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            style={{
              flex: 1,
              padding: "10px",
              border: "none",
              borderBottom: activeTab === tab.key ? "3px solid #2563EB" : "none",
              backgroundColor: activeTab === tab.key ? "#EFF6FF" : "transparent",
              color: activeTab === tab.key ? "#1D4ED8" : "#64748B",
              fontWeight: 700,
              fontSize: 13,
              cursor: "pointer"
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB 1: PRESCRIPTIONS */}
      {activeTab === "prescriptions" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {prescriptions.length > 0 ? (
            prescriptions.map((rx: any) => (
              <div key={rx.id} style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1px solid #E2E8F0", boxShadow: "0 4px 12px rgba(0,0,0,0.04)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>{rx.doctor_name || "Dr. Abhinav Sharma"}</div>
                  <span style={{ fontSize: 11, color: "#64748B" }}>{t("citizen.reference", "Ref")}: {rx.reference}</span>
                </div>

                <div style={{ fontSize: 12, color: "#475569", marginBottom: 12 }}>
                  {t("doctor.provisional_diagnosis", "Diagnosis")}: <strong>{rx.provisional_diagnosis || "General care"}</strong>
                </div>

                <div style={{ backgroundColor: "#F8FAFC", borderRadius: 12, padding: 10, display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
                  {rx.items?.map((item: any, idx: number) => (
                    <div key={idx} style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                      <span style={{ fontWeight: 700, color: "#1E293B" }}>💊 {item.medicine_name}</span>
                      <span style={{ color: "#64748B" }}>{item.dosage} • {item.frequency} ({item.duration_days} {t("prescription.duration", "days")})</span>
                    </div>
                  ))}
                </div>
              </div>
            ))
          ) : (
            <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1px solid #E2E8F0" }}>
              <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", marginBottom: 4 }}>Iron & Folic Acid Tablets (IFA)</div>
              <div style={{ fontSize: 12, color: "#64748B", marginBottom: 10 }}>Dr. Abhinav Sharma • Kalyanpur PHC</div>
              <div style={{ backgroundColor: "#F8FAFC", padding: 10, borderRadius: 10, fontSize: 13, color: "#334155" }}>
                💊 1 tablet daily after food (30 days)
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: TESTS */}
      {activeTab === "tests" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {investigations.length > 0 ? (
            investigations.map((inv: any) => (
              <div key={inv.id} style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1px solid #E2E8F0" }}>
                <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>{inv.test_name}</div>
                <div style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>
                  {t("common.status")}: {t("status." + inv.status, inv.status)} • {inv.ordered_at}
                </div>
              </div>
            ))
          ) : (
            <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1px solid #E2E8F0" }}>
              <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>Hemoglobin (Hb) & Blood Pressure Test</div>
              <div style={{ fontSize: 12, color: "#166534", fontWeight: 700, marginTop: 4 }}>✓ {t("status.COLLECTED", "Collected")} • 11.5 g/dL</div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: FOLLOWUPS */}
      {activeTab === "followups" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 16, border: "1px solid #E2E8F0" }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>3rd ANC Routine Checkup</div>
            <div style={{ fontSize: 12, color: "#64748B", marginTop: 4 }}>Kalyanpur PHC • 25 May 2026</div>
          </div>
        </div>
      )}
    </div>
  );
};

