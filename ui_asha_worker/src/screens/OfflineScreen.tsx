import React, { useState } from "react";
import { SyncIcon, CheckCircleIcon, WarningIcon, CloudOffIcon, InfoIcon } from "../components/Icons";

const QUEUE = [
  {
    id: "1",
    citizen: "Sunita Devi",
    task: "Urgent field visit",
    status: "waiting" as const,
    time: "Today, 9:00 AM",
  },
  {
    id: "2",
    citizen: "Ramesh Patil",
    task: "Blood-pressure follow-up",
    status: "synced" as const,
    time: "Yesterday, 4:00 PM",
  },
  {
    id: "3",
    citizen: "Meena Jadhav",
    task: "Vaccination visit",
    status: "conflict" as const,
    time: "Yesterday, 2:30 PM",
  },
  {
    id: "4",
    citizen: "Anita Sharma",
    task: "Scheme document checklist",
    status: "failed" as const,
    time: "2 days ago",
  },
];

const STATUS_CONFIG = {
  waiting: {
    label: "Waiting to sync",
    color: "var(--followup)",
    bg: "var(--followup-bg)",
    Icon: SyncIcon,
  },
  synced: {
    label: "Synchronized",
    color: "var(--success)",
    bg: "var(--success-bg)",
    Icon: CheckCircleIcon,
  },
  conflict: {
    label: "Needs attention",
    color: "var(--urgent)",
    bg: "var(--urgent-bg)",
    Icon: WarningIcon,
  },
  failed: {
    label: "Sync failed safely",
    color: "var(--high)",
    bg: "var(--high-bg)",
    Icon: InfoIcon,
  },
};

export default function OfflineScreen() {
  const [syncing, setSyncing] = useState(false);
  const [showConflict, setShowConflict] = useState(false);

  const waiting = QUEUE.filter((q) => q.status === "waiting").length;

  const handleSync = () => {
    setSyncing(true);
    setTimeout(() => setSyncing(false), 2000);
  };

  return (
    <div style={{ padding: "16px 16px 24px" }}>
      {/* Summary */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 14,
          padding: "16px",
          marginBottom: 16,
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            backgroundColor: waiting > 0 ? "var(--followup-bg)" : "var(--success-bg)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: waiting > 0 ? "var(--followup)" : "var(--success)",
            flexShrink: 0,
          }}
        >
          {waiting > 0 ? <SyncIcon size={24} /> : <CheckCircleIcon size={24} />}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 16, color: "var(--text-primary)" }}>
            {waiting > 0 ? `${waiting} update${waiting > 1 ? "s" : ""} waiting to sync` : "All data synchronized"}
          </div>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
            Your information is safe on this device
          </div>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing || waiting === 0}
          style={{
            height: 40,
            padding: "0 14px",
            backgroundColor: syncing || waiting === 0 ? "var(--neutral-bg)" : "var(--primary)",
            color: syncing || waiting === 0 ? "var(--text-disabled)" : "white",
            border: "none",
            borderRadius: 8,
            fontSize: 13,
            fontWeight: 600,
            cursor: syncing || waiting === 0 ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
            whiteSpace: "nowrap",
            flexShrink: 0,
          }}
        >
          <SyncIcon size={15} style={{ animation: syncing ? "spin 1s linear infinite" : "none" }} />
          {syncing ? "Syncing…" : "Sync now"}
        </button>
      </div>

      {/* Available offline */}
      <div
        style={{
          backgroundColor: "var(--success-bg)",
          borderRadius: 12,
          padding: "12px 14px",
          marginBottom: 16,
        }}
      >
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--success)", marginBottom: 8 }}>
          Available offline
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {[
            "Assigned downloaded tasks",
            "Cached citizen profiles",
            "Field-visit forms",
            "Vital-sign entry",
            "Safety rules and guidance",
            "Referral drafts",
            "Follow-up notes",
          ].map((item) => (
            <div key={item} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-primary)" }}>
              <CheckCircleIcon size={14} style={{ color: "var(--success)", flexShrink: 0 }} />
              {item}
            </div>
          ))}
        </div>
      </div>

      {/* Unavailable offline */}
      <div
        style={{
          backgroundColor: "var(--offline-bg)",
          borderRadius: 12,
          padding: "12px 14px",
          marginBottom: 20,
        }}
      >
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--offline)", marginBottom: 8 }}>
          Requires internet connection
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {[
            "Live scheme eligibility verification",
            "Current hospital status",
            "Government-record synchronization",
            "Live clinical information",
          ].map((item) => (
            <div key={item} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-primary)" }}>
              <CloudOffIcon size={14} style={{ color: "var(--offline)", flexShrink: 0 }} />
              {item}
            </div>
          ))}
        </div>
      </div>

      {/* Queue */}
      <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", marginBottom: 12 }}>
        Sync queue
      </div>

      {QUEUE.map(({ id, citizen, task, status, time }) => {
        const cfg = STATUS_CONFIG[status];

        return (
          <div
            key={id}
            style={{
              backgroundColor: "var(--surface)",
              border: `1.5px solid ${status === "conflict" ? "var(--urgent)" : "var(--border)"}`,
              borderRadius: 12,
              padding: "12px 14px",
              marginBottom: 10,
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: "50%",
                backgroundColor: cfg.bg,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: cfg.color,
                flexShrink: 0,
              }}
            >
              <cfg.Icon size={18} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)" }}>{citizen}</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {task}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-disabled)", marginTop: 2 }}>{time}</div>
            </div>
            <div style={{ flexShrink: 0 }}>
              <span
                style={{
                  display: "inline-block",
                  padding: "4px 8px",
                  backgroundColor: cfg.bg,
                  color: cfg.color,
                  borderRadius: 6,
                  fontSize: 11,
                  fontWeight: 600,
                  marginBottom: 6,
                  whiteSpace: "nowrap",
                }}
              >
                {cfg.label}
              </span>
              {status === "conflict" && (
                <div>
                  <button
                    onClick={() => setShowConflict(true)}
                    style={{
                      border: "none",
                      background: "none",
                      color: "var(--urgent)",
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: "pointer",
                      padding: 0,
                      display: "block",
                    }}
                  >
                    Resolve
                  </button>
                </div>
              )}
              {status === "failed" && (
                <button
                  style={{
                    border: "none",
                    background: "none",
                    color: "var(--primary)",
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                    padding: 0,
                    display: "block",
                  }}
                >
                  Retry
                </button>
              )}
            </div>
          </div>
        );
      })}

      {/* Conflict dialog */}
      {showConflict && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "flex-end",
            zIndex: 50,
          }}
          onClick={() => setShowConflict(false)}
        >
          <div
            style={{
              backgroundColor: "var(--surface)",
              borderRadius: "20px 20px 0 0",
              padding: "20px 20px 32px",
              width: "100%",
              maxHeight: "70vh",
              overflow: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>
              Data conflict detected
            </div>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: "20px", marginBottom: 20 }}>
              Two versions of Meena Jadhav's vaccination record exist. Your offline visit was recorded before the server record was updated.
            </p>
            <div
              style={{
                backgroundColor: "var(--urgent-bg)",
                padding: "12px 14px",
                borderRadius: 10,
                marginBottom: 20,
                fontSize: 13,
                color: "var(--urgent)",
                lineHeight: "19px",
                fontWeight: 500,
              }}
            >
              Health information will NOT be overwritten automatically. Please review and choose which version to keep.
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => setShowConflict(false)}
                style={{
                  flex: 1,
                  height: 48,
                  backgroundColor: "var(--primary)",
                  color: "white",
                  border: "none",
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Review conflict
              </button>
              <button
                onClick={() => setShowConflict(false)}
                style={{
                  height: 48,
                  padding: "0 16px",
                  backgroundColor: "transparent",
                  color: "var(--text-secondary)",
                  border: "1.5px solid var(--border)",
                  borderRadius: 10,
                  fontSize: 14,
                  cursor: "pointer",
                }}
              >
                Later
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
