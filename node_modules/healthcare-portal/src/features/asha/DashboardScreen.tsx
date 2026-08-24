import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import { WarningIcon, TasksIcon, VisitIcon, ChevronRightIcon, PeopleIcon } from "../../components/Icons";
import { useRealtime } from "../../hooks/useRealtime";

export function AshaDashboardScreen() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = async () => {
    try {
      const res = await apiClient.getAshaDashboard();
      setData(res);
    } catch (err) {
      console.error("Failed to load ASHA dashboard", err);
    } finally {
      setLoading(false);
    }
  };

  // Real-time WebSocket connection hook
  useRealtime((event, eventData) => {
    if (["DOCTOR_ACKNOWLEDGED", "FOLLOW_UP_ASSIGNED", "CONSULTATION_COMPLETED", "CASE_ASSIGNED", "VISIT_COMPLETED", "SYNC_COMPLETED"].includes(event)) {
      console.log(`[RealTime] Invalidation event received: ${event}. Refetching dashboard...`);
      fetchDashboard();
    }
  });

  useEffect(() => {
    fetchDashboard();
  }, []);

  if (loading && !data) {
    return (
      <div style={{ padding: "40px 0", textAlign: "center", color: "var(--text-secondary)" }}>
        Loading ASHA tasks...
      </div>
    );
  }

  const urgentTasks = data?.recent_tasks?.filter((t: any) => t.priority === "URGENT") || [];
  const otherTasks = data?.recent_tasks?.filter((t: any) => t.priority !== "URGENT") || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Urgent Warning Banner if Urgent Cases Exist */}
      {urgentTasks.length > 0 && (
        <div
          style={{
            backgroundColor: "var(--urgent-bg)",
            border: "1px solid #F5C6CB",
            borderRadius: 12,
            padding: "16px 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
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
            <div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "var(--urgent)" }}>
                {urgentTasks.length} Urgent Case Requiring Attention
              </div>
              <div style={{ fontSize: 13, color: "var(--text-primary)", marginTop: 2 }}>
                Pregnancy warning signs detected in Kalyanpur Village. Please acknowledge and plan field visit.
              </div>
            </div>
          </div>
          <Link
            to={`/asha/cases/${urgentTasks[0].case_id}`}
            style={{
              padding: "10px 18px",
              backgroundColor: "var(--urgent)",
              color: "#FFF",
              borderRadius: 8,
              textDecoration: "none",
              fontSize: 13,
              fontWeight: 700,
              whiteSpace: "nowrap",
            }}
          >
            Review Urgent Case
          </Link>
        </div>
      )}

      {/* Metric Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
        <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>Total Assigned Cases</div>
          <div style={{ fontSize: 28, fontWeight: 700, color: "var(--text-primary)", marginTop: 4 }}>
            {data?.total_assigned || 0}
          </div>
        </div>

        <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid #F5C6CB" }}>
          <div style={{ fontSize: 13, color: "var(--urgent)", fontWeight: 600 }}>Urgent Red Flags</div>
          <div style={{ fontSize: 28, fontWeight: 700, color: "var(--urgent)", marginTop: 4 }}>
            {data?.urgent_count || 0}
          </div>
        </div>

        <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>Pending Field Visits</div>
          <div style={{ fontSize: 28, fontWeight: 700, color: "var(--primary)", marginTop: 4 }}>
            {data?.pending_visits || 0}
          </div>
        </div>

        <div style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>Active Follow-ups</div>
          <div style={{ fontSize: 28, fontWeight: 700, color: "var(--followup)", marginTop: 4 }}>
            {data?.active_followups || 0}
          </div>
        </div>
      </div>

      {/* Task List Section */}
      <div style={{ backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)", padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
            Priority Tasks & Field Visits
          </h2>
          <Link
            to="/asha/tasks"
            style={{ fontSize: 13, fontWeight: 600, color: "var(--primary)", textDecoration: "none" }}
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
                border: task.priority === "URGENT" ? "1px solid #F5C6CB" : "1px solid var(--border)",
                backgroundColor: task.priority === "URGENT" ? "var(--urgent-bg)" : "var(--surface)",
                cursor: "pointer",
                transition: "transform 150ms ease, box-shadow 150ms ease",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                    {task.citizen_name}
                  </span>
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
                  {task.case_reference} · {task.village_name} · {task.primary_concern}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--primary)", fontWeight: 600, fontSize: 13 }}>
                <span>Review</span>
                <ChevronRightIcon size={18} color="var(--primary)" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
