import React, { useState } from "react";
import type { Screen, Priority } from "../types";
import { SearchIcon, FilterIcon, CalendarIcon, PhoneIcon, ChevronRightIcon } from "../components/Icons";
import { PriorityBadge, CaseStatusBadge } from "../components/StatusBadge";

interface Task {
  id: string;
  priority: Priority;
  citizen: string;
  age: number;
  village: string;
  task: string;
  due: string;
  status: "not-started" | "in-progress" | "completed";
}

const mockTasks: Task[] = [
  {
    id: "1",
    priority: "urgent",
    citizen: "Sunita Devi",
    age: 28,
    village: "Kalyanpur",
    task: "Maternal health – warning signs",
    due: "Now",
    status: "not-started",
  },
  {
    id: "2",
    priority: "high",
    citizen: "Ramesh Patil",
    age: 56,
    village: "Kalyanpur",
    task: "Blood-pressure follow-up",
    due: "Today, 2:00 PM",
    status: "not-started",
  },
  {
    id: "3",
    priority: "followup",
    citizen: "Meena Jadhav",
    age: 34,
    village: "Sonpur",
    task: "Vaccination visit – BCG",
    due: "Today, 3:30 PM",
    status: "not-started",
  },
  {
    id: "4",
    priority: "routine",
    citizen: "Anita Sharma",
    age: 42,
    village: "Kalyanpur",
    task: "Diabetes follow-up",
    due: "Tomorrow",
    status: "not-started",
  },
  {
    id: "5",
    priority: "followup",
    citizen: "Kavita Patel",
    age: 26,
    village: "Rampur",
    task: "Confirm PHC visit",
    due: "Today, 5:00 PM",
    status: "in-progress",
  },
];

interface TaskCardProps {
  task: Task;
  onStart: () => void;
  onCall: () => void;
}

function TaskCard({ task, onStart, onCall }: TaskCardProps) {
  const urgentBorder = task.priority === "urgent" ? "var(--urgent)" : "var(--border)";

  return (
    <div
      style={{
        backgroundColor: "var(--surface)",
        border: `1.5px solid ${urgentBorder}`,
        borderRadius: 14,
        padding: "14px 14px 12px",
        marginBottom: 10,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 10 }}>
        <PriorityBadge priority={task.priority} size="sm" />
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
          {task.due}
        </span>
      </div>

      <div style={{ marginBottom: 8 }}>
        <div style={{ fontWeight: 600, fontSize: 15, color: "var(--text-primary)", lineHeight: "21px" }}>
          {task.citizen}, {task.age}
        </div>
        <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          {task.village} · {task.task}
        </div>
      </div>

      {task.status !== "not-started" && (
        <div style={{ marginBottom: 8 }}>
          <CaseStatusBadge
            status={task.status === "in-progress" ? "visit-in-progress" : "completed"}
            size="sm"
          />
        </div>
      )}

      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={onStart}
          style={{
            flex: 1,
            height: 40,
            backgroundColor: task.priority === "urgent" ? "var(--urgent)" : "var(--primary)",
            color: "white",
            border: "none",
            borderRadius: 8,
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 6,
          }}
        >
          {task.status === "not-started" ? "Start visit" : "Continue"}
          <ChevronRightIcon size={15} />
        </button>
        <button
          onClick={onCall}
          style={{
            width: 40,
            height: 40,
            backgroundColor: "var(--teal-light)",
            color: "var(--teal)",
            border: "none",
            borderRadius: 8,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          aria-label={`Call ${task.citizen}`}
        >
          <PhoneIcon size={18} />
        </button>
      </div>
    </div>
  );
}

interface TasksScreenProps {
  onNavigate: (screen: Screen) => void;
}

type FilterKey = "all" | "urgent" | "today" | "followup";

const filters: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "urgent", label: "Urgent" },
  { key: "today", label: "Today" },
  { key: "followup", label: "Follow-up" },
];

export default function TasksScreen({ onNavigate }: TasksScreenProps) {
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterKey>("all");

  const filtered = mockTasks.filter((t) => {
    const matchSearch =
      !search ||
      t.citizen.toLowerCase().includes(search.toLowerCase()) ||
      t.task.toLowerCase().includes(search.toLowerCase());

    const matchFilter =
      activeFilter === "all" ||
      (activeFilter === "urgent" && t.priority === "urgent") ||
      (activeFilter === "today" && t.due.startsWith("Today")) ||
      (activeFilter === "followup" && t.priority === "followup");

    return matchSearch && matchFilter;
  });

  return (
    <div style={{ padding: "16px 16px 24px" }}>
      {/* Search */}
      <div style={{ position: "relative", marginBottom: 12 }}>
        <SearchIcon
          size={18}
          style={{
            position: "absolute",
            left: 14,
            top: "50%",
            transform: "translateY(-50%)",
            color: "var(--text-disabled)",
          }}
        />
        <input
          type="search"
          placeholder="Search citizen or task"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            width: "100%",
            height: 48,
            paddingLeft: 44,
            paddingRight: 14,
            border: "1.5px solid var(--border)",
            borderRadius: 12,
            fontSize: 15,
            color: "var(--text-primary)",
            backgroundColor: "var(--surface)",
            outline: "none",
            boxSizing: "border-box",
          }}
          aria-label="Search citizen or task"
        />
      </div>

      {/* Filter tabs */}
      <div
        style={{
          display: "flex",
          gap: 8,
          marginBottom: 16,
          overflowX: "auto",
          paddingBottom: 4,
        }}
        className="scrollbar-hide"
        role="tablist"
        aria-label="Task filters"
      >
        {filters.map(({ key, label }) => (
          <button
            key={key}
            role="tab"
            aria-selected={activeFilter === key}
            onClick={() => setActiveFilter(key)}
            style={{
              height: 36,
              padding: "0 16px",
              borderRadius: 20,
              border: activeFilter === key ? "none" : "1.5px solid var(--border)",
              backgroundColor: activeFilter === key ? "var(--primary)" : "var(--surface)",
              color: activeFilter === key ? "white" : "var(--text-secondary)",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              whiteSpace: "nowrap",
              transition: "all 150ms",
            }}
          >
            {label}
            {key === "urgent" && (
              <span
                style={{
                  marginLeft: 6,
                  backgroundColor: activeFilter === key ? "rgba(255,255,255,0.3)" : "var(--urgent-bg)",
                  color: activeFilter === key ? "white" : "var(--urgent)",
                  borderRadius: 10,
                  padding: "1px 6px",
                  fontSize: 11,
                  fontWeight: 700,
                }}
              >
                2
              </span>
            )}
          </button>
        ))}
        <button
          style={{
            height: 36,
            padding: "0 14px",
            borderRadius: 20,
            border: "1.5px solid var(--border)",
            backgroundColor: "var(--surface)",
            color: "var(--text-secondary)",
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
            whiteSpace: "nowrap",
            display: "flex",
            alignItems: "center",
            gap: 6,
            flexShrink: 0,
          }}
          aria-label="More filters"
        >
          <FilterIcon size={14} />
          Filter
        </button>
      </div>

      {/* Results count */}
      <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12, fontWeight: 500 }}>
        {filtered.length} task{filtered.length !== 1 ? "s" : ""}
      </div>

      {/* Task list */}
      {filtered.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "48px 16px",
            color: "var(--text-secondary)",
          }}
        >
          <CalendarIcon size={40} style={{ color: "var(--border-strong)", marginBottom: 12 }} />
          <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 8 }}>No tasks found</div>
          <div style={{ fontSize: 14, lineHeight: "20px" }}>
            Try a different search or filter.
          </div>
        </div>
      ) : (
        filtered.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            onStart={() => onNavigate(task.priority === "urgent" ? "citizen-case" : "field-visit")}
            onCall={() => {}}
          />
        ))
      )}
    </div>
  );
}
