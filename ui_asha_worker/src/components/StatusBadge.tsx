import React from "react";
import { WarningIcon, ClockIcon, CheckCircleIcon, InfoIcon } from "./Icons";
import type { Priority, CaseStatus } from "../types";

interface PriorityBadgeProps {
  priority: Priority;
  size?: "sm" | "md";
}

const priorityConfig = {
  urgent: {
    label: "Urgent",
    color: "var(--urgent)",
    bg: "var(--urgent-bg)",
    Icon: WarningIcon,
  },
  high: {
    label: "High priority",
    color: "var(--high)",
    bg: "var(--high-bg)",
    Icon: WarningIcon,
  },
  followup: {
    label: "Follow-up",
    color: "var(--followup)",
    bg: "var(--followup-bg)",
    Icon: ClockIcon,
  },
  routine: {
    label: "Routine",
    color: "var(--neutral)",
    bg: "var(--neutral-bg)",
    Icon: InfoIcon,
  },
};

export function PriorityBadge({ priority, size = "md" }: PriorityBadgeProps) {
  const cfg = priorityConfig[priority];
  const px = size === "sm" ? "8px" : "10px";
  const py = size === "sm" ? "3px" : "5px";
  const fontSize = size === "sm" ? "11px" : "13px";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        padding: `${py} ${px}`,
        borderRadius: "6px",
        backgroundColor: cfg.bg,
        color: cfg.color,
        fontSize,
        fontWeight: 600,
        lineHeight: "18px",
        whiteSpace: "nowrap",
      }}
      aria-label={`Priority: ${cfg.label}`}
    >
      <cfg.Icon size={size === "sm" ? 12 : 14} />
      {cfg.label}
    </span>
  );
}

interface CaseStatusBadgeProps {
  status: CaseStatus;
  size?: "sm" | "md";
}

const statusConfig: Record<CaseStatus, { label: string; color: string; bg: string }> = {
  new: { label: "New", color: "var(--info)", bg: "var(--info-bg)" },
  acknowledged: { label: "Acknowledged", color: "var(--teal)", bg: "var(--teal-light)" },
  contacted: { label: "Contacted", color: "var(--teal)", bg: "var(--teal-light)" },
  "visit-planned": { label: "Visit planned", color: "var(--primary)", bg: "var(--primary-light)" },
  "visit-in-progress": { label: "Visit in progress", color: "var(--primary)", bg: "var(--primary-light)" },
  "asha-reviewed": { label: "ASHA reviewed", color: "var(--teal)", bg: "var(--teal-light)" },
  referred: { label: "Referred", color: "var(--high)", bg: "var(--high-bg)" },
  "doctor-acknowledged": { label: "Doctor acknowledged", color: "var(--success)", bg: "var(--success-bg)" },
  "followup-required": { label: "Follow-up required", color: "var(--followup)", bg: "var(--followup-bg)" },
  completed: { label: "Completed", color: "var(--success)", bg: "var(--success-bg)" },
};

export function CaseStatusBadge({ status, size = "md" }: CaseStatusBadgeProps) {
  const cfg = statusConfig[status];
  const px = size === "sm" ? "8px" : "10px";
  const py = size === "sm" ? "3px" : "5px";
  const fontSize = size === "sm" ? "11px" : "13px";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: `${py} ${px}`,
        borderRadius: "6px",
        backgroundColor: cfg.bg,
        color: cfg.color,
        fontSize,
        fontWeight: 600,
        lineHeight: "18px",
        whiteSpace: "nowrap",
      }}
    >
      {cfg.label}
    </span>
  );
}

interface OnlineStatusProps {
  online: boolean;
  lastSync?: string;
}

export function OnlineStatus({ online, lastSync }: OnlineStatusProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        padding: "4px 10px",
        borderRadius: "20px",
        backgroundColor: online ? "var(--success-bg)" : "var(--offline-bg)",
        color: online ? "var(--success)" : "var(--offline)",
        fontSize: "12px",
        fontWeight: 600,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: "currentColor",
          flexShrink: 0,
        }}
        aria-hidden="true"
      />
      {online ? "Online" : lastSync ? `Offline · Synced ${lastSync}` : "Offline"}
    </div>
  );
}
