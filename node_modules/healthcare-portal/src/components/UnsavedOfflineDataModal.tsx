import React from "react";
import { WarningIcon } from "./Icons";

interface UnsavedOfflineDataModalProps {
  isOpen: boolean;
  pendingCount: number;
  draftsCount: number;
  onSyncAndLogout: () => void;
  onStaySignedIn: () => void;
  onLogoutAndKeepData: () => void;
  isSyncing?: boolean;
}

export const UnsavedOfflineDataModal: React.FC<UnsavedOfflineDataModalProps> = ({
  isOpen,
  pendingCount,
  draftsCount,
  onSyncAndLogout,
  onStaySignedIn,
  onLogoutAndKeepData,
  isSyncing = false
}) => {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: 16
      }}
    >
      <div
        style={{
          backgroundColor: "var(--surface, #FFFFFF)",
          borderRadius: 16,
          maxWidth: 520,
          width: "100%",
          padding: 28,
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
          border: "1px solid var(--border, #E2E8F0)"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: "50%",
              backgroundColor: "var(--warning-bg, #FFF3E0)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--warning, #F57C00)"
            }}
          >
            <WarningIcon size={28} color="var(--warning, #F57C00)" />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary, #1A202C)" }}>
              Unsaved Offline Data Warning
            </h3>
            <div style={{ fontSize: 13, color: "var(--text-secondary, #718096)", marginTop: 2 }}>
              Some field information has not been synchronized.
            </div>
          </div>
        </div>

        <p style={{ fontSize: 14, color: "var(--text-primary, #2D3748)", lineHeight: "22px", marginBottom: 20 }}>
          You have <strong>{pendingCount} pending field action(s)</strong> and <strong>{draftsCount} visit draft(s)</strong> saved locally on this device.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <button
            onClick={onSyncAndLogout}
            disabled={isSyncing}
            style={{
              padding: "12px 18px",
              backgroundColor: "var(--primary, #0052CC)",
              color: "#FFF",
              borderRadius: 8,
              border: "none",
              fontSize: 14,
              fontWeight: 700,
              cursor: isSyncing ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8
            }}
          >
            {isSyncing ? "Synchronizing..." : "Sync and Log Out"}
          </button>

          <button
            onClick={onLogoutAndKeepData}
            style={{
              padding: "12px 18px",
              backgroundColor: "var(--neutral-bg, #EDF2F7)",
              color: "var(--text-primary, #2D3748)",
              borderRadius: 8,
              border: "1px solid var(--border, #CBD5E0)",
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer"
            }}
          >
            Log Out and Keep Data Safely on This Device
          </button>

          <button
            onClick={onStaySignedIn}
            style={{
              padding: "10px 18px",
              backgroundColor: "transparent",
              color: "var(--text-secondary, #718096)",
              borderRadius: 8,
              border: "none",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer"
            }}
          >
            Stay Signed In
          </button>
        </div>
      </div>
    </div>
  );
};
