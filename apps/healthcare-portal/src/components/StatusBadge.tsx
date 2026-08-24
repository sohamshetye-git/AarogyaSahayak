import React from "react";
import { WarningIcon, CheckCircleIcon, ActivityIcon, CloudOffIcon } from "./Icons";

export type PriorityType = "URGENT" | "HIGH" | "FOLLOW_UP" | "ROUTINE" | "INFORMATION";
export type StatusType = 
  | "NEW" 
  | "ASHA_ASSIGNED" 
  | "ASHA_ACKNOWLEDGED" 
  | "CITIZEN_CONTACTED" 
  | "VISIT_SCHEDULED" 
  | "VISIT_IN_PROGRESS" 
  | "ASHA_REVIEWED" 
  | "REFERRED_TO_PHC" 
  | "DOCTOR_ACKNOWLEDGED" 
  | "PATIENT_ARRIVED" 
  | "CONSULTATION_IN_PROGRESS" 
  | "FOLLOW_UP_REQUIRED" 
  | "COMPLETED";

interface PriorityBadgeProps {
  priority: PriorityType | string;
  size?: "sm" | "md";
}

export function PriorityBadge({ priority, size = "md" }: PriorityBadgeProps) {
  const p = (priority || "ROUTINE").toUpperCase();
  
  let bg = "var(--neutral-bg)";
  let color = "var(--text-secondary)";
  let border = "var(--border)";
  let Icon = ActivityIcon;
  let label = p;

  if (p === "URGENT") {
    bg = "var(--urgent-bg)";
    color = "var(--urgent)";
    border = "#F5C6CB";
    Icon = WarningIcon;
    label = "Urgent";
  } else if (p === "HIGH") {
    bg = "var(--high-bg)";
    color = "var(--high)";
    border = "#FFE8D6";
    Icon = WarningIcon;
    label = "High Priority";
  } else if (p === "FOLLOW_UP") {
    bg = "var(--followup-bg)";
    color = "var(--followup)";
    border = "#FFF3CD";
    label = "Follow-up";
  } else if (p === "ROUTINE") {
    bg = "var(--success-bg)";
    color = "var(--success)";
    border = "#D4EDDA";
    Icon = CheckCircleIcon;
    label = "Routine";
  }

  const isSmall = size === "sm";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: isSmall ? 4 : 6,
        padding: isSmall ? "2px 8px" : "4px 10px",
        borderRadius: "9999px",
        backgroundColor: bg,
        color: color,
        border: `1px solid ${border}`,
        fontSize: isSmall ? 12 : 13,
        fontWeight: 600,
        whiteSpace: "nowrap",
      }}
    >
      <Icon size={isSmall ? 12 : 14} color={color} />
      <span>{label}</span>
    </span>
  );
}

export function StatusBadge({ status }: { status: StatusType | string }) {
  const s = (status || "NEW").toUpperCase();
  let bg = "var(--neutral-bg)";
  let color = "var(--text-secondary)";
  let label = s.replace(/_/g, " ").toLowerCase();
  label = label.charAt(0).toUpperCase() + label.slice(1);

  if (s === "NEW") {
    bg = "var(--info-bg)";
    color = "var(--primary)";
    label = "New Case";
  } else if (s === "ASHA_ACKNOWLEDGED" || s === "DOCTOR_ACKNOWLEDGED") {
    bg = "#E8F4FD";
    color = "#0B6BCB";
    label = s === "ASHA_ACKNOWLEDGED" ? "ASHA Acknowledged" : "Doctor Acknowledged";
  } else if (s === "REFERRED_TO_PHC") {
    bg = "#FFF3E8";
    color = "#D65A00";
    label = "Referred to PHC";
  } else if (s === "FOLLOW_UP_REQUIRED") {
    bg = "#FFF8E1";
    color = "#B26A00";
    label = "Follow-up Required";
  } else if (s === "COMPLETED") {
    bg = "var(--success-bg)";
    color = "var(--success)";
    label = "Completed";
  }

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "3px 8px",
        borderRadius: "6px",
        backgroundColor: bg,
        color: color,
        fontSize: 12,
        fontWeight: 600,
        border: "1px solid var(--border)",
      }}
    >
      {label}
    </span>
  );
}

export function OnlineStatusBadge({ isOnline }: { isOnline: boolean }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "2px 8px",
        borderRadius: "12px",
        backgroundColor: isOnline ? "var(--success-bg)" : "var(--offline-bg)",
        color: isOnline ? "var(--success)" : "var(--offline)",
        fontSize: 12,
        fontWeight: 600,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: isOnline ? "var(--success)" : "var(--offline)",
        }}
      />
      {isOnline ? "Online" : "Offline mode"}
    </span>
  );
}
