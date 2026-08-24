import React, { useState } from "react";
import type { Screen } from "../types";
import { SearchIcon, FilterIcon, PhoneIcon, ChevronRightIcon, AddIcon } from "../components/Icons";
import { CaseStatusBadge } from "../components/StatusBadge";

interface PeopleScreenProps {
  onNavigate: (screen: Screen) => void;
}

const citizens = [
  {
    id: "1",
    name: "Sunita Devi",
    age: 28,
    village: "Kalyanpur",
    category: "Maternal health",
    nextAction: "Today – urgent follow-up",
    status: "acknowledged" as const,
    initials: "SD",
    color: "var(--urgent)",
    bg: "var(--urgent-bg)",
  },
  {
    id: "2",
    name: "Ramesh Patil",
    age: 56,
    village: "Kalyanpur",
    category: "Chronic care – hypertension",
    nextAction: "Today, 2:00 PM",
    status: "visit-planned" as const,
    initials: "RP",
    color: "var(--primary)",
    bg: "var(--primary-light)",
  },
  {
    id: "3",
    name: "Meena Jadhav",
    age: 34,
    village: "Sonpur",
    category: "Child health – vaccination",
    nextAction: "Today, 3:30 PM",
    status: "new" as const,
    initials: "MJ",
    color: "var(--teal)",
    bg: "var(--teal-light)",
  },
  {
    id: "4",
    name: "Anita Sharma",
    age: 42,
    village: "Kalyanpur",
    category: "Chronic care – diabetes",
    nextAction: "Tomorrow",
    status: "followup-required" as const,
    initials: "AS",
    color: "var(--followup)",
    bg: "var(--followup-bg)",
  },
  {
    id: "5",
    name: "Kavita Patel",
    age: 26,
    village: "Rampur",
    category: "Maternal health",
    nextAction: "Next week",
    status: "completed" as const,
    initials: "KP",
    color: "var(--success)",
    bg: "var(--success-bg)",
  },
];

const filters = ["All", "Village", "Maternal health", "Child health", "Chronic care", "Follow-up due"];

export default function PeopleScreen({ onNavigate }: PeopleScreenProps) {
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("All");

  const filtered = citizens.filter((c) => {
    const q = search.toLowerCase();
    return (
      !q ||
      c.name.toLowerCase().includes(q) ||
      c.village.toLowerCase().includes(q) ||
      c.category.toLowerCase().includes(q)
    );
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
          placeholder="Search name, phone, ABHA or village"
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
          aria-label="Search citizens"
        />
      </div>

      {/* Filters */}
      <div
        style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 4, marginBottom: 16 }}
        className="scrollbar-hide"
      >
        {filters.map((f) => (
          <button
            key={f}
            onClick={() => setActiveFilter(f)}
            style={{
              height: 34,
              padding: "0 14px",
              borderRadius: 20,
              border: activeFilter === f ? "none" : "1.5px solid var(--border)",
              backgroundColor: activeFilter === f ? "var(--primary)" : "var(--surface)",
              color: activeFilter === f ? "white" : "var(--text-secondary)",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Count */}
      <div style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12, fontWeight: 500 }}>
        {filtered.length} people
      </div>

      {/* Citizens list */}
      {filtered.map((c) => (
        <div
          key={c.id}
          style={{
            backgroundColor: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 14,
            padding: "14px",
            marginBottom: 10,
          }}
        >
          <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 10 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: "50%",
                backgroundColor: c.bg,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                fontSize: 15,
                color: c.color,
                flexShrink: 0,
              }}
              aria-hidden="true"
            >
              {c.initials}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 15, color: "var(--text-primary)" }}>
                {c.name}, {c.age}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                {c.village} · {c.category}
              </div>
            </div>
            <CaseStatusBadge status={c.status} size="sm" />
          </div>

          <div
            style={{
              padding: "8px 10px",
              backgroundColor: "var(--bg)",
              borderRadius: 8,
              fontSize: 13,
              color: "var(--text-secondary)",
              marginBottom: 10,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-disabled)" }}>Next action:</span>
            <span style={{ fontWeight: 500, color: "var(--text-primary)" }}>{c.nextAction}</span>
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => onNavigate("citizen-case")}
              style={{
                flex: 1,
                height: 38,
                backgroundColor: "var(--primary-light)",
                color: "var(--primary)",
                border: "none",
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
              }}
            >
              View
              <ChevronRightIcon size={14} />
            </button>
            <button
              style={{
                width: 38,
                height: 38,
                backgroundColor: "var(--teal-light)",
                color: "var(--teal)",
                border: "none",
                borderRadius: 8,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              aria-label={`Call ${c.name}`}
            >
              <PhoneIcon size={16} />
            </button>
            <button
              onClick={() => onNavigate("field-visit")}
              style={{
                height: 38,
                padding: "0 12px",
                backgroundColor: "var(--bg)",
                color: "var(--text-secondary)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Start visit
            </button>
          </div>
        </div>
      ))}

      {/* Add person FAB */}
      <button
        style={{
          position: "fixed",
          bottom: 88,
          right: 16,
          width: 56,
          height: 56,
          borderRadius: "50%",
          backgroundColor: "var(--primary)",
          color: "white",
          border: "none",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 4px 16px rgba(21,101,192,0.35)",
        }}
        aria-label="Add new person"
      >
        <AddIcon size={24} />
      </button>
    </div>
  );
}
