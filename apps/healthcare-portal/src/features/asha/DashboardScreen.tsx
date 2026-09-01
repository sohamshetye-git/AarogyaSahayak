import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { useLanguage } from "../../context/LanguageContext";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import {
  WarningIcon,
  TasksIcon,
  VisitIcon,
  ChevronRightIcon,
  PeopleIcon,
  StethoscopeIcon,
  CloudOffIcon,
  ActivityIcon,
} from "../../components/Icons";
import { useRealtime } from "../../hooks/useRealtime";
import { db } from "../../db/offlineDb";

export function AshaDashboardScreen() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [pendingSyncCount, setPendingSyncCount] = useState(0);
  const [isAcknowledging, setIsAcknowledging] = useState(false);

  const fetchDashboard = async () => {
    try {
      const res = await apiClient.getAshaDashboard();
      setData(res);
      // Check offline pending actions count from Dexie
      try {
        const count = await db.pendingActions.where("status").notEqual("SYNCED").count();
        setPendingSyncCount(count);
      } catch {
        setPendingSyncCount(0);
      }
    } catch (err) {
      console.error("Failed to load ASHA dashboard", err);
    } finally {
      setLoading(false);
    }
  };

  // Real-time WebSocket connection hook
  useRealtime((event, eventData) => {
    if (
      [
        "DOCTOR_ACKNOWLEDGED",
        "FOLLOW_UP_ASSIGNED",
        "CONSULTATION_COMPLETED",
        "CASE_ASSIGNED",
        "VISIT_COMPLETED",
        "SYNC_COMPLETED",
        "REFERRAL_CREATED",
      ].includes(event)
    ) {
      console.log(`[RealTime] Invalidation event received: ${event}. Refetching dashboard...`);
      fetchDashboard();
    }
  });

  useEffect(() => {
    fetchDashboard();
    
    // Listen for background sync updates
    window.addEventListener("sync_completed", fetchDashboard);
    return () => {
      window.removeEventListener("sync_completed", fetchDashboard);
    };
  }, []);

  const handleAcknowledgeUrgent = async (caseId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (isAcknowledging) return;
    setIsAcknowledging(true);
    try {
      await apiClient.acknowledgeAshaCase(caseId);
      await fetchDashboard();
    } catch (err) {
      console.error("Failed to acknowledge urgent case", err);
    } finally {
      setIsAcknowledging(false);
    }
  };

  if (loading && !data) {
    return (
      <div style={{ padding: "40px 0", textAlign: "center", color: "var(--text-secondary)" }}>
        Loading ASHA tasks...
      </div>
    );
  }

  const urgentTasks =
    data?.recent_tasks?.filter(
      (t: any) => t.priority === "URGENT" && (t.status === "NEW" || t.status === "ASHA_ACKNOWLEDGED")
    ) || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Urgent Warning Banner if Real Unacknowledged Urgent Case Exists */}
      {urgentTasks.length > 0 && (
        <div
          style={{
            backgroundColor: "var(--urgent-bg)",
            border: "1px solid #F5C6CB",
            borderRadius: 12,
            padding: "18px 22px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
            flexWrap: "wrap",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "50%",
                backgroundColor: "var(--urgent)",
                color: "#FFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <WarningIcon size={24} color="#FFF" />
            </div>
            <div
              onClick={() => navigate(`/asha/cases/${urgentTasks[0].case_id}`)}
              style={{ cursor: "pointer" }}
            >
              <div style={{ fontSize: 16, fontWeight: 700, color: "var(--urgent)" }}>
                {urgentTasks.length}{" "}
                {t(
                  urgentTasks.length === 1 ? "asha.urgent_unack_case_single" : "asha.urgent_unack_case_plural",
                  urgentTasks.length === 1 ? "Urgent Unacknowledged Case" : "Urgent Unacknowledged Cases"
                )}
                {": "}
                {urgentTasks.length > 1 ? (
                  <span>
                    <span style={{ fontWeight: 600, color: "var(--urgent)" }}>{t("common.latest", "Latest")}: </span>
                    {urgentTasks[0].citizen_name || t("common.unnamed_citizen", "Citizen")}
                  </span>
                ) : (
                  <span>{urgentTasks[0].citizen_name || t("common.unnamed_citizen", "Citizen")}</span>
                )}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-primary)", marginTop: 2 }}>
                {urgentTasks[0].village_name || t("common.catchment_village", "Village")} · {urgentTasks[0].primary_concern || t("common.urgent_clinical_attention", "Urgent Clinical Attention Needed")}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (urgentTasks[0].citizen_phone) {
                  window.open(`tel:${urgentTasks[0].citizen_phone}`, "_self");
                }
              }}
              style={{
                padding: "9px 14px",
                backgroundColor: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 600,
                color: "var(--text-primary)",
                cursor: "pointer",
                minHeight: 44,
              }}
            >
              📞 {t("asha.call_citizen", "Call Citizen")}
            </button>
            <button
              onClick={(e) => handleAcknowledgeUrgent(urgentTasks[0].case_id, e)}
              disabled={isAcknowledging}
              style={{
                padding: "9px 16px",
                backgroundColor: "var(--teal)",
                color: "#FFF",
                border: "none",
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
                minHeight: 44,
              }}
            >
              {isAcknowledging ? t("common.saved", "Saving...") : `✓ ${t("common.confirm", "Acknowledge")}`}
            </button>
            <Link
              to={`/asha/cases/${urgentTasks[0].case_id}`}
              style={{
                padding: "9px 18px",
                backgroundColor: "var(--urgent)",
                color: "#FFF",
                borderRadius: 8,
                textDecoration: "none",
                fontSize: 13,
                fontWeight: 700,
                whiteSpace: "nowrap",
                display: "inline-flex",
                alignItems: "center",
                minHeight: 44,
              }}
            >
              {t("asha.review_urgent_case", "Review Urgent Case")}
            </Link>
          </div>
        </div>
      )}

      {/* Metric Cards Grid (6 Actionable Cards) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 16,
        }}
      >
        {/* 1. Urgent Unacknowledged Cases */}
        <div
          onClick={() => navigate("/asha/tasks?priority=URGENT")}
          style={{
            backgroundColor: "var(--surface)",
            padding: 18,
            borderRadius: 12,
            border: "1px solid #F5C6CB",
            cursor: "pointer",
            transition: "transform 120ms ease, box-shadow 120ms ease",
          }}
        >
          <div style={{ fontSize: 13, color: "var(--urgent)", fontWeight: 600 }}>
            🚨 {t("asha.urgent_red_flags", "Urgent Red Flags")}
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: "var(--urgent)", marginTop: 4 }}>
            {data?.urgent_count || 0}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
            {t("asha.tap_to_view_urgent", "Tap to view urgent triage")}
          </div>
        </div>

        {/* 2. Today's Field Visits */}
        <div
          onClick={() => navigate("/asha/visit?tab=today")}
          style={{
            backgroundColor: "var(--surface)",
            padding: 18,
            borderRadius: 12,
            border: "1px solid var(--border)",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>
            📅 {t("asha.todays_visits", "Today's Visits")}
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: "var(--primary)", marginTop: 4 }}>
            {data?.pending_visits || 0}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
            {t("asha.tap_to_view_schedule", "Tap to view today's schedule")}
          </div>
        </div>

        {/* 3. Overdue Follow-ups */}
        <div
          onClick={() => navigate("/asha/followups?status=OVERDUE")}
          style={{
            backgroundColor: "var(--surface)",
            padding: 18,
            borderRadius: 12,
            border: "1px solid var(--border)",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>
            ⏱ Overdue Follow-ups
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: "var(--urgent)", marginTop: 4 }}>
            {data?.overdue_followups_count || 0}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
            Needs priority visit
          </div>
        </div>

        {/* 4. Active Doctor Instructions */}
        <div
          onClick={() => navigate("/asha/followups?source=DOCTOR")}
          style={{
            backgroundColor: "var(--surface)",
            padding: 18,
            borderRadius: 12,
            border: "1px solid var(--border)",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>
            👩‍⚕️ Doctor Instructions
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: "var(--teal)", marginTop: 4 }}>
            {data?.doctor_instructions_count || data?.active_followups || 0}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
            Assigned by PHC Medical Officer
          </div>
        </div>

        {/* 5. Total Assigned Citizens */}
        <div
          onClick={() => navigate("/asha/people")}
          style={{
            backgroundColor: "var(--surface)",
            padding: 18,
            borderRadius: 12,
            border: "1px solid var(--border)",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>
            👥 Assigned Citizens
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
            {data?.total_assigned_citizens || data?.total_assigned || 0}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
            Kalyanpur village directory
          </div>
        </div>

        {/* 6. Pending Offline Synchronization */}
        <div
          onClick={() => navigate("/asha/offline")}
          style={{
            backgroundColor: "var(--surface)",
            padding: 18,
            borderRadius: 12,
            border: "1px solid var(--border)",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>
            ☁️ Pending Sync
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: pendingSyncCount > 0 ? "var(--urgent)" : "var(--success)", marginTop: 4 }}>
            {pendingSyncCount}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
            Offline drafts & actions
          </div>
        </div>
      </div>

      {/* Task List Section */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          borderRadius: 12,
          border: "1px solid var(--border)",
          padding: 24,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 20,
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
              Priority Tasks & Field Visits
            </h2>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-secondary)" }}>
              Actionable cases and pending health interventions assigned to your care.
            </p>
          </div>
          <Link
            to="/asha/tasks"
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--primary)",
              textDecoration: "none",
            }}
          >
            View All Tasks →
          </Link>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {data?.recent_tasks?.map((task: any) => (
            <div
              key={task.id}
              onClick={() => navigate(`/asha/cases/${task.case_id}`)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "16px 20px",
                borderRadius: 10,
                border:
                  task.priority === "URGENT"
                    ? "1px solid #F5C6CB"
                    : "1px solid var(--border)",
                backgroundColor:
                  task.priority === "URGENT" ? "var(--urgent-bg)" : "var(--surface)",
                cursor: "pointer",
                transition: "transform 150ms ease, box-shadow 150ms ease",
                flexWrap: "wrap",
                gap: 12,
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 6, flex: 1, minWidth: 260 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                    {task.citizen_name}
                  </span>
                  {task.citizen_age && (
                    <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                      ({task.citizen_age}y)
                    </span>
                  )}
                  {task.is_pregnant && (
                    <span
                      style={{
                        padding: "2px 8px",
                        borderRadius: 12,
                        backgroundColor: "#FCE4EC",
                        color: "#C2185B",
                        fontSize: 11,
                        fontWeight: 700,
                      }}
                    >
                      Pregnant ({task.gestational_weeks ? `${task.gestational_weeks}w` : "7m"})
                    </span>
                  )}
                  <PriorityBadge priority={task.priority} size="sm" />
                  <StatusBadge status={task.status} />
                </div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                  Ref: <strong>{task.case_reference}</strong> · {task.village_name} · {task.primary_concern}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                  Assigned: {new Date(task.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>

              {/* Action Buttons */}
              <div
                style={{ display: "flex", alignItems: "center", gap: 8 }}
                onClick={(e) => e.stopPropagation()}
              >
                {task.citizen_phone && (
                  <button
                    onClick={() => window.open(`tel:${task.citizen_phone}`, "_self")}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 6,
                      border: "1px solid var(--border)",
                      backgroundColor: "var(--surface)",
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: "pointer",
                      minHeight: 38,
                    }}
                    title="Call Citizen"
                  >
                    📞 Call
                  </button>
                )}
                {(task.status === "CITIZEN_CONTACTED" || task.status === "NEW" || task.status === "ASHA_ACKNOWLEDGED") && (
                  <button
                    onClick={() => navigate(`/asha/visit?caseId=${task.case_id}`)}
                    style={{
                      padding: "8px 14px",
                      borderRadius: 6,
                      border: "none",
                      backgroundColor: "var(--teal)",
                      color: "#FFF",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer",
                      minHeight: 38,
                    }}
                  >
                    Visit
                  </button>
                )}
                <button
                  onClick={() => navigate(`/asha/cases/${task.case_id}`)}
                  style={{
                    padding: "8px 14px",
                    borderRadius: 6,
                    border: "none",
                    backgroundColor: "var(--primary)",
                    color: "#FFF",
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    minHeight: 38,
                  }}
                >
                  <span>Review</span>
                  <ChevronRightIcon size={14} color="#FFF" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
