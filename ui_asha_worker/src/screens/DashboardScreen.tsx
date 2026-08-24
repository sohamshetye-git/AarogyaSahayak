import React from "react";
import type { Screen } from "../types";
import {
  WarningIcon,
  PhoneIcon,
  CalendarIcon,
  SyncIcon,
  CheckCircleIcon,
  ClockIcon,
  ChevronRightIcon,
} from "../components/Icons";
import { PriorityBadge } from "../components/StatusBadge";

interface DashboardScreenProps {
  onNavigate: (screen: Screen) => void;
  isOnline?: boolean;
  lastSync?: string;
}

function SummaryCard({
  count,
  label,
  color,
  bg,
  icon: Icon,
  onClick,
}: {
  count: number | string;
  label: string;
  color: string;
  bg: string;
  icon: React.FC<{ size?: number }>;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        minWidth: 0,
        backgroundColor: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 14,
        padding: "16px 14px",
        cursor: "pointer",
        textAlign: "left",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        transition: "border-color 150ms",
      }}
      onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.borderColor = color)}
      onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.borderColor = "var(--border)")}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 10,
          backgroundColor: bg,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color,
        }}
      >
        <Icon size={20} />
      </div>
      <div>
        <div style={{ fontSize: 26, fontWeight: 700, color: "var(--text-primary)", lineHeight: "32px" }}>
          {count}
        </div>
        <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 500, lineHeight: "16px" }}>
          {label}
        </div>
      </div>
    </button>
  );
}

function UrgentAlertCard({ onViewCase }: { onViewCase: () => void }) {
  return (
    <div
      style={{
        backgroundColor: "var(--surface)",
        border: "1.5px solid var(--urgent)",
        borderRadius: 16,
        overflow: "hidden",
      }}
    >
      {/* Header strip */}
      <div
        style={{
          backgroundColor: "var(--urgent-bg)",
          padding: "10px 16px",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <WarningIcon size={16} style={{ color: "var(--urgent)" }} />
        <PriorityBadge priority="urgent" size="sm" />
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--urgent)", fontWeight: 500 }}>
          12 minutes ago
        </span>
      </div>

      <div style={{ padding: "16px 16px 14px" }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 12 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              backgroundColor: "var(--urgent-bg)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: 16,
              color: "var(--urgent)",
              flexShrink: 0,
            }}
          >
            S
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 16, color: "var(--text-primary)", lineHeight: "22px" }}>
              Sunita Devi, 28
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              Approx. 7 months pregnant · Kalyanpur
            </div>
          </div>
        </div>

        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Warning signs detected
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {["Blurred vision", "Severe headache", "BP 150/100"].map((sign) => (
              <span
                key={sign}
                style={{
                  padding: "4px 10px",
                  backgroundColor: "var(--urgent-bg)",
                  color: "var(--urgent)",
                  borderRadius: 6,
                  fontSize: 13,
                  fontWeight: 500,
                }}
              >
                {sign}
              </span>
            ))}
          </div>
        </div>

        <div
          style={{
            padding: "10px 12px",
            backgroundColor: "var(--info-bg)",
            borderRadius: 8,
            fontSize: 13,
            color: "var(--info)",
            fontStyle: "italic",
            marginBottom: 14,
            lineHeight: "18px",
          }}
        >
          AI-assisted summary – please verify.
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={onViewCase}
            style={{
              flex: 1,
              height: 44,
              backgroundColor: "var(--urgent)",
              color: "white",
              border: "none",
              borderRadius: 10,
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
            }}
          >
            View case
            <ChevronRightIcon size={16} />
          </button>
          <button
            style={{
              height: 44,
              padding: "0 16px",
              backgroundColor: "transparent",
              color: "var(--text-primary)",
              border: "1.5px solid var(--border)",
              borderRadius: 10,
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            Acknowledge
          </button>
        </div>
      </div>
    </div>
  );
}

function TodayVisitRow({
  time,
  name,
  task,
  priority,
  onStart,
}: {
  time: string;
  name: string;
  task: string;
  priority: "urgent" | "routine";
  onStart: () => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "12px 0",
        borderBottom: "1px solid var(--divider)",
      }}
    >
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: "var(--text-secondary)",
          minWidth: 56,
          whiteSpace: "nowrap",
        }}
      >
        {time}
      </div>
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: priority === "urgent" ? "var(--urgent)" : "var(--primary)",
          flexShrink: 0,
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)" }}>{name}</div>
        <div style={{ fontSize: 13, color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {task}
        </div>
      </div>
      <button
        onClick={onStart}
        style={{
          height: 36,
          padding: "0 14px",
          backgroundColor: "var(--primary-light)",
          color: "var(--primary)",
          border: "none",
          borderRadius: 8,
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        Start
      </button>
    </div>
  );
}

function RecentUpdateItem({ text, time }: { text: string; time: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        padding: "10px 0",
        borderBottom: "1px solid var(--divider)",
      }}
    >
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: "var(--teal)",
          flexShrink: 0,
          marginTop: 6,
        }}
      />
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: "20px" }}>{text}</div>
        <div style={{ fontSize: 12, color: "var(--text-disabled)", marginTop: 2 }}>{time}</div>
      </div>
    </div>
  );
}

export default function DashboardScreen({ onNavigate, isOnline = true, lastSync }: DashboardScreenProps) {
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div style={{ padding: "16px 16px 24px" }}>
      {/* Greeting */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 2px" }}>
          {greeting}, Sita
        </h2>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 14, color: "var(--text-secondary)" }}>Kalyanpur Village</span>
          {!isOnline && (
            <span style={{ fontSize: 12, color: "var(--offline)", fontWeight: 500 }}>
              · Internet is weak · Last synced {lastSync || "10:42 AM"}
            </span>
          )}
        </div>
      </div>

      {/* Summary Cards – 2×2 on mobile */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 24 }}>
        <SummaryCard
          count={2}
          label="Urgent cases"
          color="var(--urgent)"
          bg="var(--urgent-bg)"
          icon={WarningIcon}
          onClick={() => onNavigate("tasks")}
        />
        <SummaryCard
          count={5}
          label="Visits today"
          color="var(--primary)"
          bg="var(--primary-light)"
          icon={CalendarIcon}
          onClick={() => onNavigate("tasks")}
        />
        <SummaryCard
          count={8}
          label="Follow-ups"
          color="var(--followup)"
          bg="var(--followup-bg)"
          icon={ClockIcon}
          onClick={() => onNavigate("tasks")}
        />
        <SummaryCard
          count={1}
          label="Waiting to sync"
          color={isOnline ? "var(--teal)" : "var(--offline)"}
          bg={isOnline ? "var(--teal-light)" : "var(--offline-bg)"}
          icon={SyncIcon}
          onClick={() => onNavigate("offline")}
        />
      </div>

      {/* Urgent section */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <WarningIcon size={18} style={{ color: "var(--urgent)" }} />
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            Needs attention now
          </h3>
        </div>
        <UrgentAlertCard onViewCase={() => onNavigate("citizen-case")} />
      </div>

      {/* Today's visits */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 16,
          padding: "16px",
          marginBottom: 24,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            Today's visits
          </h3>
          <button
            onClick={() => onNavigate("tasks")}
            style={{
              border: "none",
              background: "none",
              color: "var(--primary)",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              padding: 0,
            }}
          >
            View all
          </button>
        </div>
        <TodayVisitRow
          time="10:00 AM"
          name="Ramesh Patil"
          task="Blood-pressure follow-up"
          priority="routine"
          onStart={() => onNavigate("field-visit")}
        />
        <TodayVisitRow
          time="11:30 AM"
          name="Sunita Devi"
          task="Urgent maternal-health visit"
          priority="urgent"
          onStart={() => onNavigate("citizen-case")}
        />
        <div style={{ borderBottom: "none", paddingBottom: 0 }}>
          <TodayVisitRow
            time="2:00 PM"
            name="Meena Jadhav"
            task="Vaccination visit"
            priority="routine"
            onStart={() => onNavigate("field-visit")}
          />
        </div>
      </div>

      {/* Recent updates */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 16,
          padding: "16px",
        }}
      >
        <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
          Recent updates
        </h3>
        <RecentUpdateItem
          text="Dr Sharma acknowledged Sunita's referral"
          time="Today, 9:15 AM"
        />
        <RecentUpdateItem
          text="Meena's vaccination visit was completed"
          time="Yesterday, 4:30 PM"
        />
        <RecentUpdateItem
          text="One field visit is waiting to sync"
          time="Yesterday, 6:00 PM"
        />
        <button
          onClick={() => onNavigate("notifications")}
          style={{
            width: "100%",
            marginTop: 12,
            padding: "10px",
            backgroundColor: "transparent",
            color: "var(--primary)",
            border: "none",
            borderRadius: 8,
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 4,
          }}
        >
          View all notifications
          <ChevronRightIcon size={16} />
        </button>
      </div>
    </div>
  );
}
