import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import { SearchIcon, ChevronRightIcon, VisitIcon } from "../../components/Icons";

const FILTERS = [
  { id: "ALL", label: "All Tasks" },
  { id: "CITIZEN_REQUESTS", label: "💬 Citizen Requests" },
  { id: "URGENT", label: "🚨 Urgent" },
  { id: "HIGH", label: "⚠️ High" },
  { id: "ROUTINE", label: "📋 Routine" },
  { id: "NEW", label: "✨ New" },
  { id: "ASHA_ACKNOWLEDGED", label: "✓ Acknowledged" },
  { id: "CITIZEN_CONTACTED", label: "📞 Contacted" },
  { id: "VISIT_REQUIRED", label: "🏠 Visit Required" },
  { id: "REFERRED_TO_PHC", label: "🏥 Referred" },
  { id: "UNREACHABLE", label: "🚫 Unreachable" },
  { id: "FOLLOW_UP_REQUIRED", label: "🔄 Follow-up Due" },
];

export function AshaTasksScreen() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialPriority = searchParams.get("priority");
  const initialStatus = searchParams.get("status");
  const initialSource = searchParams.get("source");

  const [tasks, setTasks] = useState<any[]>([]);
  const [filter, setFilter] = useState<string>(
    initialSource === "CITIZEN_REQUEST"
      ? "CITIZEN_REQUESTS"
      : initialPriority
      ? initialPriority
      : initialStatus
      ? initialStatus
      : "ALL"
  );
  const [search, setSearch] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("PRIORITY");
  const [loading, setLoading] = useState(true);
  const [navigatingId, setNavigatingId] = useState<string | null>(null);

  useEffect(() => {
    const loadTasks = async () => {
      try {
        const [casesRes, citizenReqsRes] = await Promise.all([
          apiClient.getAshaTasks(),
          apiClient.getAshaCitizenRequests().catch(() => ({ data: [] }))
        ]);

        const rawCitizenReqs = (citizenReqsRes?.data || citizenReqsRes || []).map((r: any) => ({
          id: r.id,
          request_id: r.id,
          case_id: r.case_id || r.id,
          is_citizen_request: true,
          citizen_name: r.citizen_name,
          citizen_age: r.age || r.citizen_age,
          citizen_phone: r.citizen_phone,
          village_name: r.village || r.village_name || "Kalyanpur",
          priority: r.priority || "ROUTINE",
          status: r.status,
          primary_concern: r.chief_concern || "Citizen Assistance Request",
          created_at: r.submitted_at || r.created_at,
          case_reference: r.request_reference || r.case_reference
        }));

        const combined = [...(Array.isArray(casesRes) ? casesRes : []), ...rawCitizenReqs];
        setTasks(combined);
      } catch (err) {
        console.error("Failed to load tasks", err);
      } finally {
        setLoading(false);
      }
    };
    loadTasks();
  }, []);

  const handleReviewClick = (task: any, e: React.MouseEvent) => {
    e.stopPropagation();
    if (navigatingId) return;
    setNavigatingId(task.id);
    if (task.is_citizen_request) {
      const targetId = task.request_id || task.id;
      navigate(`/asha/citizen-requests/${targetId}`);
    } else {
      navigate(`/asha/cases/${task.case_id || task.id}`);
    }
  };

  const filteredTasks = tasks
    .filter((t) => {
      if (filter === "CITIZEN_REQUESTS" && !t.is_citizen_request) return false;
      if (filter === "URGENT" && t.priority !== "URGENT") return false;
      if (filter === "HIGH" && t.priority !== "HIGH") return false;
      if (filter === "ROUTINE" && t.priority !== "ROUTINE") return false;
      if (filter === "NEW" && t.status !== "NEW" && t.status !== "SUBMITTED" && t.status !== "ASSIGNMENT_PENDING") return false;
      if (filter === "ASHA_ACKNOWLEDGED" && t.status !== "ASHA_ACKNOWLEDGED") return false;
      if (filter === "CITIZEN_CONTACTED" && t.status !== "CITIZEN_CONTACTED") return false;
      if (
        filter === "VISIT_REQUIRED" &&
        !["NEW", "SUBMITTED", "ASHA_ACKNOWLEDGED", "CITIZEN_CONTACTED", "VISIT_SCHEDULED"].includes(t.status)
      )
        return false;
      if (filter === "REFERRED_TO_PHC" && t.status !== "REFERRED_TO_PHC") return false;
      if (filter === "UNREACHABLE" && t.status !== "UNREACHABLE") return false;
      if (filter === "FOLLOW_UP_REQUIRED" && t.status !== "FOLLOW_UP_REQUIRED") return false;

      if (search) {
        const s = search.toLowerCase();
        const matchName = t.citizen_name?.toLowerCase().includes(s);
        const matchRef = t.case_reference?.toLowerCase().includes(s);
        const matchVillage = t.village_name?.toLowerCase().includes(s);
        const matchPhone = t.citizen_phone?.includes(s);
        const matchConcern = t.primary_concern?.toLowerCase().includes(s);
        if (!matchName && !matchRef && !matchVillage && !matchPhone && !matchConcern) {
          return false;
        }
      }
      return true;
    })
    .sort((a, b) => {
      if (sortBy === "PRIORITY") {
        const pOrder: Record<string, number> = { URGENT: 3, HIGH: 2, ROUTINE: 1 };
        return (pOrder[b.priority] || 0) - (pOrder[a.priority] || 0);
      }
      if (sortBy === "NEWEST") {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
      if (sortBy === "OLDEST") {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      }
      return 0;
    });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Top Search & Controls Bar */}
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <div
          style={{
            flex: 1,
            minWidth: 260,
            display: "flex",
            alignItems: "center",
            gap: 10,
            backgroundColor: "var(--surface)",
            padding: "0 14px",
            height: 44,
            borderRadius: 8,
            border: "1px solid var(--border)",
          }}
        >
          <SearchIcon size={18} color="var(--text-secondary)" />
          <input
            type="text"
            placeholder="Search by citizen name, case reference, village or phone ending..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              border: "none",
              outline: "none",
              width: "100%",
              fontSize: 14,
              backgroundColor: "transparent",
            }}
          />
        </div>

        {/* Sort Selector */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)" }}>
            Sort:
          </span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            style={{
              height: 44,
              padding: "0 12px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              backgroundColor: "var(--surface)",
              color: "var(--text-primary)",
              fontWeight: 600,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            <option value="PRIORITY">Priority (Urgent First)</option>
            <option value="NEWEST">Newest Assigned</option>
            <option value="OLDEST">Oldest Assigned</option>
          </select>
        </div>
      </div>

      {/* Filter Tabs Pills (Scrollable horizontally) */}
      <div
        style={{
          display: "flex",
          gap: 8,
          overflowX: "auto",
          paddingBottom: 4,
          scrollbarWidth: "thin",
        }}
      >
        {FILTERS.map((f) => {
          const isSelected = filter === f.id;
          return (
            <button
              key={f.id}
              onClick={() => {
                setFilter(f.id);
                setSearchParams({ filter: f.id });
              }}
              style={{
                padding: "8px 14px",
                borderRadius: 8,
                border: isSelected ? "2px solid var(--primary)" : "1px solid var(--border)",
                backgroundColor: isSelected ? "var(--primary-light)" : "var(--surface)",
                color: isSelected ? "var(--primary-dark)" : "var(--text-primary)",
                fontWeight: 600,
                fontSize: 13,
                cursor: "pointer",
                whiteSpace: "nowrap",
                minHeight: 40,
              }}
            >
              {f.label}
            </button>
          );
        })}
      </div>

      {/* Task List */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: 40, color: "var(--text-secondary)" }}>
            Loading tasks...
          </div>
        ) : filteredTasks.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: 40,
              backgroundColor: "var(--surface)",
              borderRadius: 12,
              border: "1px solid var(--border)",
            }}
          >
            <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 4 }}>
              No matching tasks found
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              Try adjusting your filter or search query.
            </div>
          </div>
        ) : (
          filteredTasks.map((task) => (
            <div
              key={task.id}
              onClick={() => {
                if (task.is_citizen_request && task.request_id) {
                  navigate(`/asha/citizen-requests/${task.request_id}`);
                } else {
                  navigate(`/asha/cases/${task.case_id}`);
                }
              }}
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
                  <span style={{ fontSize: 16, fontWeight: 700 }}>{task.citizen_name}</span>
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
                  disabled={navigatingId === task.id}
                  onClick={(e) => handleReviewClick(task, e)}
                  style={{
                    padding: "8px 14px",
                    borderRadius: 6,
                    border: "none",
                    backgroundColor: navigatingId === task.id ? "var(--text-secondary)" : "var(--primary)",
                    color: "#FFF",
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: navigatingId === task.id ? "not-allowed" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    minHeight: 38,
                    opacity: navigatingId === task.id ? 0.7 : 1,
                  }}
                >
                  <span>{navigatingId === task.id ? "Opening..." : "Review"}</span>
                  <ChevronRightIcon size={14} color="#FFF" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
