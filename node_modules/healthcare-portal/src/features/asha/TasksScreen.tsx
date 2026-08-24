import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import { SearchIcon, ChevronRightIcon } from "../../components/Icons";

export function AshaTasksScreen() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<any[]>([]);
  const [filter, setFilter] = useState<string>("ALL");
  const [search, setSearch] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadTasks = async () => {
      try {
        const res = await apiClient.getAshaTasks();
        setTasks(res);
      } catch (err) {
        console.error("Failed to load tasks", err);
      } finally {
        setLoading(false);
      }
    };
    loadTasks();
  }, []);

  const filteredTasks = tasks.filter((t) => {
    if (filter === "URGENT" && t.priority !== "URGENT") return false;
    if (filter === "FOLLOW_UP" && t.status !== "FOLLOW_UP_REQUIRED") return false;
    if (search && !t.citizen_name.toLowerCase().includes(search.toLowerCase()) && !t.case_reference.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    return true;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Search and Filters */}
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
            placeholder="Search citizen or case ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ border: "none", outline: "none", width: "100%", fontSize: 14, backgroundColor: "transparent" }}
          />
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          {["ALL", "URGENT", "FOLLOW_UP"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border: filter === f ? "2px solid var(--primary)" : "1px solid var(--border)",
                backgroundColor: filter === f ? "var(--primary-light)" : "var(--surface)",
                color: filter === f ? "var(--primary-dark)" : "var(--text-primary)",
                fontWeight: 600,
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              {f === "ALL" ? "All Tasks" : f === "URGENT" ? "🚨 Urgent Only" : "Follow-ups"}
            </button>
          ))}
        </div>
      </div>

      {/* Task List */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: 40, color: "var(--text-secondary)" }}>Loading tasks...</div>
        ) : filteredTasks.length === 0 ? (
          <div style={{ textAlign: "center", padding: 40, backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
            No matching tasks found.
          </div>
        ) : (
          filteredTasks.map((task) => (
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
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 16, fontWeight: 700 }}>{task.citizen_name}</span>
                  {task.is_pregnant && (
                    <span style={{ padding: "2px 8px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                      Pregnant
                    </span>
                  )}
                  <PriorityBadge priority={task.priority} size="sm" />
                  <StatusBadge status={task.status} />
                </div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                  {task.case_reference} · {task.village_name} · {task.primary_concern}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--primary)", fontWeight: 600, fontSize: 13 }}>
                <span>Review</span>
                <ChevronRightIcon size={18} color="var(--primary)" />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
