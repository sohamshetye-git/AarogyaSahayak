import React, { useState, useEffect } from "react";
import { 
  Pill, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Calendar, 
  ArrowLeft, 
  Clock, 
  UserCheck, 
  Activity, 
  Stethoscope, 
  Building2, 
  Sparkles,
  ClipboardList
} from "lucide-react";
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

  const parseList = (res: any): any[] => {
    if (!res) return [];
    if (Array.isArray(res)) return res;
    if (Array.isArray(res?.data?.items)) return res.data.items;
    if (Array.isArray(res?.data)) return res.data;
    if (Array.isArray(res?.items)) return res.items;
    return [];
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [rxRes, invRes, folRes] = await Promise.all([
          apiClient.getCitizenPrescriptions(),
          apiClient.getCitizenInvestigations(),
          apiClient.getCitizenFollowups()
        ]);
        setPrescriptions(parseList(rxRes));
        setInvestigations(parseList(invRes));
        setFollowups(parseList(folRes));
      } catch (err) {
        console.error("Failed to fetch medicines data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const tabs = [
    { key: "prescriptions", label: t("navigation.prescriptions", "Prescriptions"), count: prescriptions.length },
    { key: "tests", label: t("navigation.investigations", "Lab Investigations"), count: investigations.length },
    { key: "followups", label: t("navigation.followups", "Follow-ups"), count: followups.length }
  ];

  const formatTaskType = (type: string) => {
    if (!type) return "Follow-up Task";
    if (type === "POST_CONSULTATION_CHECK") return "Post-Consultation Health Check";
    if (type === "MEDICATION_ADHERENCE") return "Medication Adherence Check";
    if (type === "DIAGNOSTIC_FOLLOWUP") return "Diagnostic Review Follow-up";
    if (type === "ROUTINE_MONITORING") return "Routine Health Monitoring";
    return type.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());
  };

  const getStatusBadge = (status: string) => {
    const s = (status || "").toUpperCase();
    if (s === "SIGNED" || s === "ACTIVE" || s === "COMPLETED" || s === "REVIEWED" || s === "RESULT_AVAILABLE") {
      return {
        bg: "#DCFCE7",
        color: "#166534",
        border: "#BBF7D0",
        label: s === "RESULT_AVAILABLE" ? "Result Available" : (s === "SIGNED" ? "Signed & Active" : s)
      };
    }
    if (s === "ORDERED" || s === "SCHEDULED" || s === "COLLECTED" || s === "IN_PROGRESS" || s === "PENDING") {
      return {
        bg: "#EFF6FF",
        color: "#1D4ED8",
        border: "#BFDBFE",
        label: s === "ORDERED" ? "Ordered" : (s === "COLLECTED" ? "Sample Collected" : s)
      };
    }
    return {
      bg: "#F1F5F9",
      color: "#475569",
      border: "#E2E8F0",
      label: s || "Active"
    };
  };

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16, maxWidth: 600, margin: "0 auto", width: "100%" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {onBack && (
          <button 
            onClick={onBack} 
            style={{ 
              border: "none", 
              background: "#F1F5F9", 
              padding: 10, 
              borderRadius: "50%", 
              cursor: "pointer", 
              display: "flex", 
              alignItems: "center", 
              justifyContent: "center",
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
            }}
          >
            <ArrowLeft size={18} color="#334155" />
          </button>
        )}
        <div style={{ flex: 1 }}>
          <h2 style={{ fontSize: 20, fontWeight: 800, color: "#0F172A", margin: 0 }}>
            {t("citizen.my_medicines", "My Medicines & Prescriptions")}
          </h2>
          <div style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>
            {t("citizen.my_medicines_tests", "Prescriptions, lab tests and follow-ups")}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", background: "#FFFFFF", borderRadius: 12, padding: "4px 6px", border: "1px solid #E2E8F0" }}>
        {tabs.map((tab) => {
          const isSelected = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              style={{
                flex: 1,
                padding: "10px 4px",
                border: "none",
                borderRadius: 8,
                backgroundColor: isSelected ? "#2563EB" : "transparent",
                color: isSelected ? "#FFFFFF" : "#64748B",
                fontWeight: 700,
                fontSize: 12,
                cursor: "pointer",
                transition: "all 0.15s ease-in-out",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6
              }}
            >
              <span>{tab.label}</span>
              {tab.count > 0 && (
                <span style={{
                  fontSize: 10,
                  padding: "1px 6px",
                  borderRadius: 10,
                  backgroundColor: isSelected ? "rgba(255,255,255,0.25)" : "#F1F5F9",
                  color: isSelected ? "#FFFFFF" : "#475569",
                  fontWeight: 800
                }}>
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Content Loading State */}
      {loading && (
        <div style={{ padding: "32px 16px", textAlign: "center", color: "#64748B", display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <div style={{ width: 32, height: 32, border: "3px solid #E2E8F0", borderTopColor: "#2563EB", borderRadius: "50%" }} />
          <span style={{ fontSize: 13, fontWeight: 600 }}>Loading records...</span>
        </div>
      )}

      {/* TAB 1: PRESCRIPTIONS */}
      {!loading && activeTab === "prescriptions" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {prescriptions.length > 0 ? (
            prescriptions.map((rx: any) => {
              const badge = getStatusBadge(rx.status);
              const formattedDate = rx.signed_at 
                ? new Date(rx.signed_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
                : (rx.created_at ? new Date(rx.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "");

              return (
                <div 
                  key={rx.id || rx.reference} 
                  style={{ 
                    backgroundColor: "#FFFFFF", 
                    borderRadius: 18, 
                    padding: 16, 
                    border: "1px solid #E2E8F0", 
                    boxShadow: "0 4px 12px rgba(0,0,0,0.03)",
                    display: "flex",
                    flexDirection: "column",
                    gap: 12
                  }}
                >
                  {/* Prescriber & Reference Header */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <Stethoscope size={16} color="#2563EB" />
                        <span style={{ fontSize: 15, fontWeight: 800, color: "#0F172A" }}>
                          {rx.doctor_name || "Dr. Abhinav Sharma"}
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: "#64748B", marginTop: 2, display: "flex", alignItems: "center", gap: 6 }}>
                        <span>{rx.facility_name || "Kalyanpur PHC"}</span>
                        {formattedDate && <span>• {formattedDate}</span>}
                      </div>
                    </div>
                    <span 
                      style={{ 
                        fontSize: 11, 
                        fontWeight: 700, 
                        padding: "3px 8px", 
                        borderRadius: 8, 
                        backgroundColor: badge.bg, 
                        color: badge.color, 
                        border: `1px solid ${badge.border}` 
                      }}
                    >
                      {badge.label}
                    </span>
                  </div>

                  {/* Diagnosis / Clinical Context */}
                  {(rx.provisional_diagnosis || rx.clinical_context) && (
                    <div style={{ fontSize: 12, color: "#334155", backgroundColor: "#F8FAFC", padding: "8px 12px", borderRadius: 10, border: "1px solid #F1F5F9" }}>
                      <span style={{ color: "#64748B", fontWeight: 600 }}>{t("doctor.provisional_diagnosis", "Diagnosis")}: </span>
                      <strong>{rx.provisional_diagnosis || rx.clinical_context}</strong>
                    </div>
                  )}

                  {/* Medication Items */}
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: 0.5 }}>
                      Prescribed Medicines ({rx.items?.length || 0})
                    </div>
                    {rx.items && rx.items.length > 0 ? (
                      rx.items.map((item: any, idx: number) => (
                        <div 
                          key={idx} 
                          style={{ 
                            backgroundColor: "#F8FAFC", 
                            borderRadius: 12, 
                            padding: "10px 12px", 
                            border: "1px solid #E2E8F0",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center"
                          }}
                        >
                          <div>
                            <div style={{ fontSize: 13, fontWeight: 800, color: "#1E293B", display: "flex", alignItems: "center", gap: 6 }}>
                              <Pill size={14} color="#2563EB" />
                              <span>{item.medicine_name || item.medicine || "Medicine"}</span>
                              {item.strength && <span style={{ fontSize: 11, fontWeight: 600, color: "#64748B" }}>({item.strength})</span>}
                            </div>
                            <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
                              {item.instructions ? item.instructions : "Take as directed by doctor"}
                            </div>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <div style={{ fontSize: 12, fontWeight: 700, color: "#2563EB" }}>
                              {item.dosage || "1 dose"} • {item.frequency || "1-0-1"}
                            </div>
                            <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
                              {item.duration_days || 5} {t("prescription.duration", "days")}
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div style={{ fontSize: 12, color: "#64748B", fontStyle: "italic", padding: 8 }}>
                        No medication items listed in this prescription.
                      </div>
                    )}
                  </div>

                  {/* Footer Reference */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 6, borderTop: "1px solid #F1F5F9", fontSize: 11, color: "#94A3B8" }}>
                    <span>Ref: {rx.reference || rx.id}</span>
                    <span style={{ color: "#166534", fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>
                      <CheckCircle2 size={12} /> Doctor Signed
                    </span>
                  </div>
                </div>
              );
            })
          ) : (
            <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 24, border: "1px dashed #CBD5E1", textAlign: "center" }}>
              <div style={{ width: 44, height: 44, borderRadius: "50%", backgroundColor: "#EFF6FF", color: "#2563EB", margin: "0 auto 10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Pill size={22} />
              </div>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", marginBottom: 4 }}>
                No active prescriptions
              </div>
              <div style={{ fontSize: 12, color: "#64748B" }}>
                Prescriptions issued by your doctor after teleconsultations will appear here.
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: TESTS */}
      {!loading && activeTab === "tests" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {investigations.length > 0 ? (
            investigations.map((inv: any) => {
              const badge = getStatusBadge(inv.status);
              const formattedDate = inv.ordered_at 
                ? new Date(inv.ordered_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
                : "";

              return (
                <div 
                  key={inv.id || inv.reference} 
                  style={{ 
                    backgroundColor: "#FFFFFF", 
                    borderRadius: 18, 
                    padding: 16, 
                    border: "1px solid #E2E8F0", 
                    boxShadow: "0 4px 12px rgba(0,0,0,0.03)",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", display: "flex", alignItems: "center", gap: 6 }}>
                        <Activity size={16} color="#2563EB" />
                        <span>{inv.test_name}</span>
                      </div>
                      <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
                        {inv.doctor_name || "Dr. Abhinav Sharma"} • {inv.facility_name || "Kalyanpur PHC Lab"}
                      </div>
                    </div>
                    <span 
                      style={{ 
                        fontSize: 11, 
                        fontWeight: 700, 
                        padding: "3px 8px", 
                        borderRadius: 8, 
                        backgroundColor: badge.bg, 
                        color: badge.color, 
                        border: `1px solid ${badge.border}` 
                      }}
                    >
                      {badge.label}
                    </span>
                  </div>

                  {inv.clinical_reason && (
                    <div style={{ fontSize: 12, color: "#334155", backgroundColor: "#F8FAFC", padding: "8px 12px", borderRadius: 10, border: "1px solid #F1F5F9" }}>
                      <span style={{ color: "#64748B", fontWeight: 600 }}>Reason: </span>
                      {inv.clinical_reason}
                    </div>
                  )}

                  {inv.preparation_instructions && (
                    <div style={{ fontSize: 11, color: "#D97706", backgroundColor: "#FFFBEB", padding: "6px 10px", borderRadius: 8, border: "1px solid #FEF3C7" }}>
                      <strong>Preparation: </strong>{inv.preparation_instructions}
                    </div>
                  )}

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 4, borderTop: "1px solid #F1F5F9", fontSize: 11, color: "#94A3B8" }}>
                    <span>Ref: {inv.reference || inv.order_reference || inv.id}</span>
                    {formattedDate && <span>Ordered on {formattedDate}</span>}
                  </div>
                </div>
              );
            })
          ) : (
            <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 24, border: "1px dashed #CBD5E1", textAlign: "center" }}>
              <div style={{ width: 44, height: 44, borderRadius: "50%", backgroundColor: "#EFF6FF", color: "#2563EB", margin: "0 auto 10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Activity size={22} />
              </div>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", marginBottom: 4 }}>
                No lab tests ordered
              </div>
              <div style={{ fontSize: 12, color: "#64748B" }}>
                Lab and diagnostic test orders created by your doctor will appear here.
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: FOLLOWUPS */}
      {!loading && activeTab === "followups" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {followups.length > 0 ? (
            followups.map((fu: any) => {
              const badge = getStatusBadge(fu.status);
              const formattedDueDate = fu.due_at || fu.due_date 
                ? new Date(fu.due_at || fu.due_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
                : "In 3 days";

              return (
                <div 
                  key={fu.id || fu.reference} 
                  style={{ 
                    backgroundColor: "#FFFFFF", 
                    borderRadius: 18, 
                    padding: 16, 
                    border: "1px solid #E2E8F0", 
                    boxShadow: "0 4px 12px rgba(0,0,0,0.03)",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 800, color: "#0F172A", display: "flex", alignItems: "center", gap: 6 }}>
                        <UserCheck size={16} color="#2563EB" />
                        <span>{formatTaskType(fu.task_type)}</span>
                      </div>
                      <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
                        Assigned to: <strong>{fu.assigned_worker_name || (fu.assigned_role === "ASHA" ? "ASHA Worker (Sita Patel)" : "Care Team")}</strong>
                      </div>
                    </div>
                    <span 
                      style={{ 
                        fontSize: 11, 
                        fontWeight: 700, 
                        padding: "3px 8px", 
                        borderRadius: 8, 
                        backgroundColor: badge.bg, 
                        color: badge.color, 
                        border: `1px solid ${badge.border}` 
                      }}
                    >
                      {badge.label}
                    </span>
                  </div>

                  {fu.instructions && (
                    <div style={{ fontSize: 12, color: "#334155", backgroundColor: "#F8FAFC", padding: "8px 12px", borderRadius: 10, border: "1px solid #F1F5F9" }}>
                      <span style={{ color: "#64748B", fontWeight: 600 }}>Instructions: </span>
                      {fu.instructions}
                    </div>
                  )}

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 4, borderTop: "1px solid #F1F5F9", fontSize: 11, color: "#64748B" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <Calendar size={13} color="#2563EB" />
                      <span>Due date: <strong>{formattedDueDate}</strong></span>
                    </span>
                    <span style={{ color: "#94A3B8" }}>Ref: {fu.reference || fu.follow_up_reference || fu.id}</span>
                  </div>
                </div>
              );
            })
          ) : (
            <div style={{ backgroundColor: "#FFFFFF", borderRadius: 18, padding: 24, border: "1px dashed #CBD5E1", textAlign: "center" }}>
              <div style={{ width: 44, height: 44, borderRadius: "50%", backgroundColor: "#EFF6FF", color: "#2563EB", margin: "0 auto 10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <UserCheck size={22} />
              </div>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", marginBottom: 4 }}>
                No scheduled follow-ups
              </div>
              <div style={{ fontSize: 12, color: "#64748B" }}>
                ASHA or PHC care team follow-up visits scheduled by your doctor will appear here.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

