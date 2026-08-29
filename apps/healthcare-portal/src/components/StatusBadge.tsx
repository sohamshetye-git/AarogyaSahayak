import React from "react";
import { useTranslation } from "react-i18next";
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
  | "REFERRED_TO_HIGHER_FACILITY"
  | "COMPLETED"
  | "UNREACHABLE"
  | "DECLINED"
  | "PENDING_SYNC"
  | "WAITING_FOR_DOCTOR"
  | "ORDERED"
  | "COLLECTED"
  | "DISPENSED";

interface PriorityBadgeProps {
  priority: PriorityType | string;
  size?: "sm" | "md";
}

export function PriorityBadge({ priority, size = "md" }: PriorityBadgeProps) {
  const { t } = useTranslation(["priority", "common"]);
  const p = (priority || "ROUTINE").toUpperCase();
  
  let bg = "var(--neutral-bg)";
  let color = "var(--text-secondary)";
  let border = "var(--border)";
  let Icon = ActivityIcon;
  let label = t(`priority.${p}`, p);

  if (p === "URGENT") {
    bg = "var(--urgent-bg)";
    color = "var(--urgent)";
    border = "#F5C6CB";
    Icon = WarningIcon;
    label = t("priority.URGENT", "Urgent");
  } else if (p === "HIGH") {
    bg = "var(--high-bg)";
    color = "var(--high)";
    border = "#FFE8D6";
    Icon = WarningIcon;
    label = t("priority.HIGH", "High Priority");
  } else if (p === "FOLLOW_UP") {
    bg = "var(--followup-bg)";
    color = "var(--followup)";
    border = "#FFF3CD";
    label = t("priority.FOLLOW_UP", "Follow-up");
  } else if (p === "ROUTINE") {
    bg = "var(--success-bg)";
    color = "var(--success)";
    border = "#D4EDDA";
    Icon = CheckCircleIcon;
    label = t("priority.ROUTINE", "Routine");
  } else if (p === "INFORMATION") {
    label = t("priority.INFORMATION", "Information");
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
  const { t } = useTranslation(["status", "common"]);
  const s = (status || "NEW").toUpperCase();
  let bg = "var(--neutral-bg)";
  let color = "var(--text-secondary)";
  let label = t(`status.${s}`, s.replace(/_/g, " "));

  if (s === "NEW") {
    bg = "var(--info-bg)";
    color = "var(--primary)";
    label = t("status.NEW", "New Case");
  } else if (s === "ASHA_ASSIGNED") {
    bg = "#E8F4FD";
    color = "#0B6BCB";
    label = t("status.ASHA_ASSIGNED", "ASHA Assigned");
  } else if (s === "ASHA_ACKNOWLEDGED" || s === "DOCTOR_ACKNOWLEDGED") {
    bg = "#E8F4FD";
    color = "#0B6BCB";
    label = s === "ASHA_ACKNOWLEDGED" ? t("status.ASHA_ACKNOWLEDGED", "ASHA Acknowledged") : t("status.DOCTOR_ACKNOWLEDGED", "Doctor Acknowledged");
  } else if (s === "CITIZEN_CONTACTED") {
    bg = "#E0F2FE";
    color = "#0284C7";
    label = t("status.CITIZEN_CONTACTED", "Citizen Contacted");
  } else if (s === "VISIT_SCHEDULED" || s === "VISIT_IN_PROGRESS") {
    bg = "#FEF3C7";
    color = "#D97706";
    label = s === "VISIT_SCHEDULED" ? t("status.VISIT_SCHEDULED", "Visit Scheduled") : t("status.VISIT_IN_PROGRESS", "Visit in Progress");
  } else if (s === "REFERRED_TO_PHC" || s === "REFERRED_TO_HIGHER_FACILITY") {
    bg = "#FFF3E8";
    color = "#D65A00";
    label = s === "REFERRED_TO_PHC" ? t("status.REFERRED_TO_PHC", "Referred to PHC") : t("status.REFERRED_TO_HIGHER_FACILITY", "Referred to Higher Facility");
  } else if (s === "PATIENT_ARRIVED") {
    bg = "#DEF7EC";
    color = "#03543F";
    label = t("status.PATIENT_ARRIVED", "Patient Arrived");
  } else if (s === "CONSULTATION_IN_PROGRESS" || s === "WAITING_FOR_DOCTOR") {
    bg = "#EFF6FF";
    color = "#1D4ED8";
    label = s === "CONSULTATION_IN_PROGRESS" ? t("status.CONSULTATION_IN_PROGRESS", "In Consultation") : t("status.WAITING_FOR_DOCTOR", "Waiting for Doctor");
  } else if (s === "FOLLOW_UP_REQUIRED") {
    bg = "#FFF8E1";
    color = "#B26A00";
    label = t("status.FOLLOW_UP_REQUIRED", "Follow-up Required");
  } else if (s === "COMPLETED") {
    bg = "var(--success-bg)";
    color = "var(--success)";
    label = t("status.COMPLETED", "Completed");
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
  const { t } = useTranslation(["common"]);
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
      {isOnline ? t("common.online", "Online") : t("common.offline", "Offline mode")}
    </span>
  );
}

