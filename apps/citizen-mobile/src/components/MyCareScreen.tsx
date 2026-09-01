import React, { useState, useEffect } from "react";
import { Phone, Calendar, Clock, ChevronRight, CheckCircle2, Circle, UserCheck, Stethoscope, Navigation } from "lucide-react";
import { useLanguage } from "@aarogya/i18n";
import { apiClient } from "@aarogya/api-client";

interface MyCareScreenProps {
  onOpenDoctor: () => void;
  onOpenAsha: () => void;
  onViewServiceRequest?: (requestId: string) => void;
}

export const MyCareScreen: React.FC<MyCareScreenProps> = ({ onOpenDoctor, onOpenAsha, onViewServiceRequest }) => {
  const { t } = useLanguage();
  const [cases, setCases] = useState<any[]>([]);
  const [serviceRequests, setServiceRequests] = useState<any[]>([]);
  const [selectedCase, setSelectedCase] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchCareData = async () => {
    try {
      const res = await apiClient.request<any>("/citizen/cases");
      const list = res?.data || res || [];
      setCases(list);
      if (list.length > 0) {
        setSelectedCase(list[0]);
        const tlRes = await apiClient.getCitizenTimeline(list[0].id);
        setTimeline(tlRes?.data || tlRes || []);
      }

      // Fetch citizen service requests
      const srRes = await apiClient.getCitizenServiceRequests();
      const srList = srRes?.data || srRes || [];
      setServiceRequests(Array.isArray(srList) ? srList : []);
    } catch (err) {
      console.error("Failed to load care data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCareData();

    const interval = setInterval(() => {
      apiClient.getCitizenServiceRequests().then(srRes => {
        const srList = srRes?.data || srRes || [];
        if (Array.isArray(srList)) setServiceRequests(srList);
      }).catch(() => {});
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  const steps = [
    { title: t("status.NEW", "Concern received"), done: true },
    { title: t("status.ASHA_ASSIGNED", "ASHA assigned"), done: true },
    { title: t("navigation.field_visits", "Home visit"), done: selectedCase?.status !== "NEW" },
    { title: t("status.REFERRED_TO_PHC", "PHC referral"), done: ["REFERRED_TO_PHC", "DOCTOR_ACKNOWLEDGED", "COMPLETED"].includes(selectedCase?.status) },
    { title: t("navigation.consultations", "Doctor review"), done: ["DOCTOR_ACKNOWLEDGED", "COMPLETED"].includes(selectedCase?.status) }
  ];

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 id="title-my-care-screen" style={{ fontSize: 20, fontWeight: 800, color: "#0F172A", margin: 0 }}>
            {t("citizen.active_care", "My Care")}
          </h2>
          <div style={{ fontSize: 12, color: "#64748B" }}>
            {t("citizen.active_care_progress", "Track your active health concerns")}
          </div>
        </div>
        {selectedCase && (
          <span style={{ fontSize: 11, fontWeight: 700, padding: "4px 10px", borderRadius: 12, backgroundColor: "#DCFCE7", color: "#166534" }}>
            {t("case.case_reference", "Case")}: {selectedCase.reference || "AC-20240826"}
          </span>
        )}
      </div>

      {/* Active Service Requests & Care Handoffs */}
      {serviceRequests.length > 0 && (
        <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0" }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: "#1E293B", marginBottom: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>{t("citizen.active_care", "Active Care Requests")}</span>
            <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 10, backgroundColor: "#EFF6FF", color: "#1D4ED8" }}>
              {serviceRequests.length} {t("common.active", "Active")}
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {serviceRequests.map((sr) => {
              const isDoc = sr.assigned_role === "PHC_DOCTOR";
              const isWaiting = sr.status === "WAITING_FOR_DOCTOR" || sr.status === "PENDING" || sr.status === "ASSIGNMENT_PENDING";
              return (
                <div
                  key={sr.id}
                  onClick={() => onViewServiceRequest && onViewServiceRequest(sr.id)}
                  style={{
                    padding: 12,
                    borderRadius: 14,
                    border: "1px solid #E2E8F0",
                    backgroundColor: "#F8FAFC",
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                    cursor: onViewServiceRequest ? "pointer" : "default"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 11, fontWeight: 800, color: isDoc ? "#1E40AF" : "#047857" }}>
                      {isDoc ? `🩺 ${t("citizen.speak_to_doctor")}` : `🏡 ${t("citizen.call_asha")}`}
                    </span>
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: 8,
                        backgroundColor: isWaiting ? "#FEF3C7" : "#DCFCE7",
                        color: isWaiting ? "#92400E" : "#166534"
                      }}
                    >
                      {t(`status.${sr.status}`, sr.status.replace(/_/g, " "))}
                    </span>
                  </div>

                  <div style={{ fontSize: 13, fontWeight: 700, color: "#1E293B" }}>
                    {sr.chief_concern ? (sr.chief_concern === "General health checkup / care guidance" ? t("concerns.GENERAL_HEALTH_GUIDANCE", sr.chief_concern) : t(`concerns.${sr.chief_concern.toUpperCase().replace(/[\s\/\-]+/g, "_")}`, sr.chief_concern)) : t("citizen.quick_actions", "Care request submitted")}
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11, color: "#64748B", marginTop: 2 }}>
                    <span>{t("citizen.reference", "Ref")}: {sr.request_reference}</span>
                    <span style={{ color: "#2563EB", fontWeight: 700 }}>{t("common.view_details", "View Details")} →</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {selectedCase ? (
        <>
          {/* Status Stepper */}
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0", boxShadow: "0 4px 12px rgba(0,0,0,0.04)" }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: "#1E293B", marginBottom: 12 }}>
              {selectedCase.primary_concern === "General health checkup / care guidance" ? t("concerns.GENERAL_HEALTH_GUIDANCE", selectedCase.primary_concern) : t(`concerns.${selectedCase.primary_concern?.toUpperCase().replace(/[\s\/\-]+/g, "_")}`, selectedCase.primary_concern)}
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
              {steps.map((step, idx) => (
                <div key={idx} style={{ display: "flex", flexDirection: "column", alignItems: "center", position: "relative", flex: 1 }}>
                  {step.done ? (
                    <CheckCircle2 size={22} color="#166534" />
                  ) : (
                    <Circle size={22} color="#CBD5E1" />
                  )}
                  <span style={{ fontSize: 9, fontWeight: 700, color: step.done ? "#166534" : "#94A3B8", marginTop: 4, textAlign: "center" }}>
                    {step.title}
                  </span>
                </div>
              ))}
            </div>

            {/* What should I do next? */}
            <div style={{ backgroundColor: "#FEF3C7", padding: 12, borderRadius: 14, border: "1px solid #FDE68A", display: "flex", alignItems: "flex-start", gap: 10 }}>
              <Calendar size={20} color="#D97706" style={{ marginTop: 2 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 800, color: "#92400E" }}>{t("common.next_care_action", "What should I do next?")}</div>
                <div style={{ fontSize: 13, color: "#78350F", marginTop: 2, fontWeight: 600 }}>
                  {selectedCase.citizen_guidance_text ? (selectedCase.citizen_guidance_text.includes("calm") || selectedCase.citizen_guidance_text.includes("monitor") ? t("common.monitor_symptoms_guidance", "Please stay calm and monitor your symptoms.") : selectedCase.citizen_guidance_text) : t("common.monitor_symptoms_guidance", "Please stay calm and monitor your symptoms.")}
                </div>
              </div>
            </div>
          </div>

          {/* Referred Target Facility Card */}
          <div style={{ backgroundColor: "#F0FDF4", borderRadius: 20, padding: 16, border: "1px solid #BBF7D0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <span style={{ fontSize: 10, fontWeight: 800, padding: "2px 8px", borderRadius: 6, backgroundColor: "#DCFCE7", color: "#166534" }}>
                  🏥 {t("citizen.find_health_center_card", "Health Centre")}
                </span>
                <div style={{ fontSize: 15, fontWeight: 800, color: "#166534", marginTop: 6 }}>
                  {t("facilities.kalyanpur_phc", "Kalyanpur Primary Health Centre (PHC)")}
                </div>
                <div style={{ fontSize: 12, color: "#15803D", marginTop: 2 }}>
                  📍 Main Market Road • 2.8 km away • {t("facility.emergency_open_24_7", "24x7 Emergency Services Available")}
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
              <button
                onClick={() => {
                  window.open("https://www.google.com/maps/dir/?api=1&destination=18.5300,73.8700&destination_place_id=Kalyanpur+PHC", "_blank");
                }}
                style={{
                  flex: 1,
                  padding: "10px",
                  borderRadius: 12,
                  backgroundColor: "#2563EB",
                  color: "#FFFFFF",
                  border: "none",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6
                }}
              >
                <Navigation size={15} /> {t("facility.get_directions", "Get Directions")}
              </button>

              <button
                onClick={() => window.open("tel:+912162234567", "_self")}
                style={{
                  flex: 1,
                  padding: "10px",
                  borderRadius: 12,
                  backgroundColor: "#FFFFFF",
                  color: "#166534",
                  border: "1px solid #86EFAC",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6
                }}
              >
                <Phone size={15} /> {t("facility.call_facility", "Call Centre")}
              </button>
            </div>
          </div>

          {/* Care Team */}
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0" }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", marginBottom: 12 }}>
              {t("citizen.care_team", "Your Care Team")}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: 10, borderRadius: 14, backgroundColor: "#F8FAFC" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ width: 40, height: 40, borderRadius: "50%", backgroundColor: "#DCFCE7", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <UserCheck size={20} color="#166534" />
                  </div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#0F172A" }}>Sita Patel ({t("roles.ASHA_WORKER")})</div>
                    <div style={{ fontSize: 11, color: "#64748B" }}>Kalyanpur Village</div>
                  </div>
                </div>
                <button onClick={onOpenAsha} style={{ padding: "6px 12px", borderRadius: 20, backgroundColor: "#FFFFFF", border: "1px solid #CBD5E1", color: "#166534", fontSize: 12, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
                  <Phone size={14} /> {t("common.speak", "Call")}
                </button>
              </div>

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: 10, borderRadius: 14, backgroundColor: "#F8FAFC" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ width: 40, height: 40, borderRadius: "50%", backgroundColor: "#DBEAFE", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Stethoscope size={20} color="#1E40AF" />
                  </div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#0F172A" }}>Dr. Abhinav Sharma</div>
                    <div style={{ fontSize: 11, color: "#64748B" }}>{t("roles.PHC_DOCTOR")}, Kalyanpur PHC</div>
                  </div>
                </div>
                <button onClick={onOpenDoctor} style={{ padding: "6px 12px", borderRadius: 20, backgroundColor: "#2563EB", color: "#FFFFFF", border: "none", fontSize: 12, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 4 }}>
                  <Phone size={14} /> {t("navigation.consultations", "Consult")}
                </button>
              </div>
            </div>
          </div>

          {/* Citizen-Safe Timeline */}
          <div style={{ backgroundColor: "#FFFFFF", borderRadius: 20, padding: 16, border: "1px solid #E2E8F0" }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: "#1E293B", marginBottom: 12 }}>
              {t("case.timeline", "Care Timeline")}
            </div>

            {timeline.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {timeline.map((evt: any) => (
                  <div key={evt.id} style={{ display: "flex", gap: 12, borderLeft: "2px solid #2563EB", paddingLeft: 12, position: "relative" }}>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 800, color: "#0F172A" }}>{evt.title}</div>
                      <div style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>{evt.description}</div>
                      <div style={{ fontSize: 10, color: "#94A3B8", marginTop: 4 }}>{new Date(evt.timestamp).toLocaleString()}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 13, color: "#64748B" }}>{t("emptyState.no_cases", "Timeline updates will appear here in real-time.")}</div>
            )}
          </div>
        </>
      ) : (
        <div style={{ textAlign: "center", padding: 32, color: "#64748B" }}>
          {t("emptyState.no_cases", "No active care cases found.")}
        </div>
      )}
    </div>
  );
};

