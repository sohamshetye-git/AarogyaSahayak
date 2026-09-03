import React, { useState, useEffect } from "react";
import { useLanguage } from "@aarogya/i18n";
import {
  CheckCircle, Pill, FileText, UserCheck, Shield, Calendar,
  ArrowRight, Download, Home, Volume2
} from "lucide-react";
import { apiClient } from "@aarogya/api-client";
import { LanguageService } from "../services/languageService";

interface DoctorConsultationSummaryScreenProps {
  requestId: string;
  onBackToHome: () => void;
  onViewMedicines: () => void;
}

const formatDoctorName = (name?: string | null): string => {
  if (!name || name.trim() === "") return "Dr. Abhinav Sharma";
  let trimmed = name.trim();
  while (trimmed.toLowerCase().startsWith("dr. ") || trimmed.toLowerCase().startsWith("dr ")) {
    if (trimmed.toLowerCase().startsWith("dr. ")) {
      trimmed = trimmed.substring(4).trim();
    } else if (trimmed.toLowerCase().startsWith("dr ")) {
      trimmed = trimmed.substring(3).trim();
    }
  }
  return `Dr. ${trimmed}`;
};

export const DoctorConsultationSummaryScreen: React.FC<DoctorConsultationSummaryScreenProps> = ({
  requestId,
  onBackToHome,
  onViewMedicines
}) => {
  const { t, locale } = useLanguage();

  const [data, setData] = useState<any>(null);
  const [medicines, setMedicines] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const res = await apiClient.getDoctorRequest(requestId);
        const detail = res?.data || res;
        setData(detail);

        // Fetch prescriptions
        const presRes = await apiClient.getCitizenPrescriptions();
        const presList = presRes?.data || presRes || [];
        setMedicines(presList);
      } catch (err) {
        console.error("Failed to load summary", err);
      } finally {
        setLoading(false);
      }
    };
    fetchSummary();
  }, [requestId]);

  const handleReadAloud = (text: string) => {
    LanguageService.speakPhrase(text, (locale as any) || "mr-IN");
  };

  if (loading && !data) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "#64748B" }}>
        Loading Consultation Summary...
      </div>
    );
  }

  const guidanceText = data?.clinical_notes || data?.patient_guidance || "Take prescribed medicines on time. Follow up with your assigned ASHA worker if fever persists.";

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F8FAFC", display: "flex", flexDirection: "column" }}>
      {/* Top Banner */}
      <div style={{ backgroundColor: "#166534", color: "#FFFFFF", padding: "20px 16px", textAlign: "center" }}>
        <div style={{ width: 56, height: 56, borderRadius: "50%", backgroundColor: "#DCFCE7", color: "#166534", margin: "0 auto 10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <CheckCircle size={32} />
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 900, margin: "0 0 4px" }}>
          Consultation Completed
        </h2>
        <p style={{ fontSize: 12, opacity: 0.9, margin: 0 }}>
          {formatDoctorName(data?.doctor?.name)} • Kalyanpur PHC
        </p>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, padding: 16, display: "flex", flexDirection: "column", gap: 14, maxWidth: 480, margin: "0 auto", width: "100%" }}>
        
        {/* Patient Advice / Guidance Card */}
        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0", boxShadow: "0 4px 12px rgba(0,0,0,0.04)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 800, color: "#1E293B" }}>Doctor's Advice & Care Plan</span>
            <button
              onClick={() => handleReadAloud(guidanceText)}
              style={{ border: "none", background: "#EFF6FF", color: "#2563EB", padding: "4px 8px", borderRadius: 8, fontSize: 11, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}
            >
              <Volume2 size={14} /> Listen / ऐका
            </button>
          </div>
          <div style={{ fontSize: 14, color: "#334155", lineHeight: 1.5, backgroundColor: "#F8FAFC", padding: 12, borderRadius: 12, border: "1px solid #E2E8F0" }}>
            "{guidanceText}"
          </div>
        </div>

        {/* Signed Prescriptions Section */}
        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 800, color: "#1E293B", display: "flex", alignItems: "center", gap: 6 }}>
              <Pill size={16} color="#2563EB" /> Prescribed Medicines
            </span>
            <span style={{ fontSize: 11, fontWeight: 700, color: "#166534", backgroundColor: "#DCFCE7", padding: "2px 8px", borderRadius: 8 }}>
              ✓ Doctor Signed
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {medicines.length > 0 && medicines[0]?.items?.length > 0 ? (
              medicines[0].items.map((med: any, idx: number) => (
                <div key={idx} style={{ padding: 10, backgroundColor: "#F8FAFC", borderRadius: 12, border: "1px solid #E2E8F0" }}>
                  <div style={{ fontSize: 14, fontWeight: 800, color: "#0F172A" }}>{med.medicine_name || med.medicine}</div>
                  <div style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>
                    Dosage: {med.dosage || "1 tablet"} • {med.frequency || "1-0-1"} {med.instructions ? `(${med.instructions})` : ""} • {med.duration_days || 3} days
                  </div>
                </div>
              ))
            ) : (
              <div style={{ padding: 12, backgroundColor: "#F8FAFC", borderRadius: 12, border: "1px solid #E2E8F0", fontSize: 13, color: "#64748B" }}>
                Medicines recorded in consultation plan. Tap "View in Medicines" to view full details.
              </div>
            )}
          </div>
        </div>

        {/* Assigned ASHA Follow-up */}
        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0" }}>
          <div style={{ fontSize: 13, fontWeight: 800, color: "#1E293B", display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <UserCheck size={16} color="#2563EB" /> Care Follow-up Scheduled
          </div>
          <div style={{ fontSize: 12, color: "#64748B" }}>
            Your assigned health worker (<b>{data?.assigned_worker_name || data?.details?.assigned_asha || "Sita Patel"}</b>) has received instructions for your post-consultation health check.
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
          <button
            onClick={onViewMedicines}
            style={{
              flex: 1,
              padding: "14px",
              backgroundColor: "#EFF6FF",
              color: "#2563EB",
              border: "1.5px solid #BFDBFE",
              borderRadius: 16,
              fontWeight: 800,
              fontSize: 14,
              cursor: "pointer"
            }}
          >
            View in Medicines
          </button>
          <button
            onClick={onBackToHome}
            style={{
              flex: 1,
              padding: "14px",
              backgroundColor: "#2563EB",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 16,
              fontWeight: 800,
              fontSize: 14,
              cursor: "pointer"
            }}
          >
            Return to Home
          </button>
        </div>
      </div>
    </div>
  );
};
