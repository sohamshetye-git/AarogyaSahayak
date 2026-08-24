import React, { useState } from "react";
import type { Screen } from "../types";
import { WarningIcon, ClockIcon, CheckCircleIcon, InfoIcon, ChevronRightIcon } from "../components/Icons";

interface NotificationsScreenProps {
  onNavigate: (screen: Screen) => void;
}

const NOTIFICATIONS = [
  {
    id: "1",
    group: "urgent",
    title: "New urgent case assigned",
    body: "Sunita Devi reported pregnancy-related warning signs.",
    time: "12 min ago",
    read: false,
    action: "citizen-case" as Screen,
    Icon: WarningIcon,
    color: "var(--urgent)",
    bg: "var(--urgent-bg)",
  },
  {
    id: "2",
    group: "urgent",
    title: "Referral not yet acknowledged",
    body: "Kalyanpur PHC has not confirmed Meera's referral. Follow up required.",
    time: "2 hours ago",
    read: false,
    action: "tasks" as Screen,
    Icon: WarningIcon,
    color: "var(--urgent)",
    bg: "var(--urgent-bg)",
  },
  {
    id: "3",
    group: "tasks",
    title: "Visit due – Ramesh Patil",
    body: "Blood-pressure follow-up scheduled for today at 2:00 PM.",
    time: "Today",
    read: false,
    action: "tasks" as Screen,
    Icon: ClockIcon,
    color: "var(--high)",
    bg: "var(--high-bg)",
  },
  {
    id: "4",
    group: "tasks",
    title: "Follow-up overdue – Kavita Patel",
    body: "Scheme document follow-up was due yesterday.",
    time: "Yesterday",
    read: true,
    action: "tasks" as Screen,
    Icon: ClockIcon,
    color: "var(--followup)",
    bg: "var(--followup-bg)",
  },
  {
    id: "5",
    group: "updates",
    title: "Doctor reviewed Sunita's case",
    body: "Dr Sharma acknowledged the referral from Kalyanpur PHC.",
    time: "Today, 9:15 AM",
    read: true,
    action: "citizen-case" as Screen,
    Icon: CheckCircleIcon,
    color: "var(--success)",
    bg: "var(--success-bg)",
  },
  {
    id: "6",
    group: "updates",
    title: "Data synchronized",
    body: "3 field visits have been successfully synced.",
    time: "Yesterday, 6:30 PM",
    read: true,
    action: "offline" as Screen,
    Icon: InfoIcon,
    color: "var(--primary)",
    bg: "var(--primary-light)",
  },
];

const GROUP_LABELS = {
  urgent: "Urgent",
  tasks: "Tasks",
  updates: "Updates",
};

export default function NotificationsScreen({ onNavigate }: NotificationsScreenProps) {
  const [notifications, setNotifications] = useState(NOTIFICATIONS);

  const markAllRead = () => {
    setNotifications((n) => n.map((item) => ({ ...item, read: true })));
  };

  const groups = ["urgent", "tasks", "updates"] as const;

  return (
    <div style={{ padding: "16px 16px 24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          {notifications.filter((n) => !n.read).length} unread
        </div>
        <button
          onClick={markAllRead}
          style={{
            border: "none",
            background: "none",
            color: "var(--primary)",
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Mark all read
        </button>
      </div>

      {groups.map((group) => {
        const items = notifications.filter((n) => n.group === group);
        if (items.length === 0) return null;

        return (
          <div key={group} style={{ marginBottom: 24 }}>
            <div
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: "var(--text-disabled)",
                textTransform: "uppercase",
                letterSpacing: "0.6px",
                marginBottom: 10,
              }}
            >
              {GROUP_LABELS[group]}
            </div>
            {items.map(({ id, title, body, time, read, action, Icon, color, bg }) => (
              <button
                key={id}
                onClick={() => {
                  setNotifications((n) => n.map((item) => item.id === id ? { ...item, read: true } : item));
                  onNavigate(action);
                }}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  padding: "12px 12px",
                  backgroundColor: read ? "var(--surface)" : `${bg}`,
                  border: `1px solid ${read ? "var(--border)" : color}20`,
                  borderRadius: 12,
                  marginBottom: 8,
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "background-color 150ms",
                  position: "relative",
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "50%",
                    backgroundColor: read ? "var(--neutral-bg)" : bg,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: read ? "var(--text-disabled)" : color,
                    flexShrink: 0,
                  }}
                >
                  <Icon size={18} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: read ? 400 : 600,
                      color: "var(--text-primary)",
                      marginBottom: 2,
                      lineHeight: "20px",
                    }}
                  >
                    {title}
                  </div>
                  <div
                    style={{
                      fontSize: 13,
                      color: "var(--text-secondary)",
                      lineHeight: "18px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {body}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-disabled)", marginTop: 4 }}>{time}</div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 4, flexShrink: 0 }}>
                  {!read && (
                    <div
                      style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: color }}
                      aria-label="Unread"
                    />
                  )}
                  <ChevronRightIcon size={16} style={{ color: "var(--border-strong)" }} />
                </div>
              </button>
            ))}
          </div>
        );
      })}

      {notifications.every((n) => n.read) && (
        <div
          style={{
            textAlign: "center",
            padding: "32px 16px",
            color: "var(--text-secondary)",
          }}
        >
          <CheckCircleIcon size={40} style={{ color: "var(--success)", marginBottom: 12 }} />
          <div style={{ fontWeight: 600, fontSize: 15 }}>All caught up</div>
          <div style={{ fontSize: 14, marginTop: 4 }}>No new notifications</div>
        </div>
      )}
    </div>
  );
}
