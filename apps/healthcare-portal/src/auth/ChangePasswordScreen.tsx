import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { apiClient } from "@aarogya/api-client";
import { ShieldCheckIcon, WarningIcon, CheckIcon } from "../components/Icons";

export function ChangePasswordScreen() {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 6) {
      setError("New password must be at least 6 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("New password and confirm password do not match.");
      return;
    }

    if (newPassword === oldPassword) {
      setError("New password must be different from your current temporary password.");
      return;
    }

    setIsLoading(true);
    try {
      await apiClient.changePassword(oldPassword, newPassword);
      
      // Update local auth context to clear must_change_password
      updateUser({ must_change_password: false });

      // Redirect to assigned workspace
      const roleStr = String(user?.role || "").toUpperCase();
      if (roleStr === "PHC_DOCTOR" || roleStr.includes("DOCTOR")) {
        navigate("/doctor/dashboard", { replace: true });
      } else if (roleStr === "DISTRICT_ADMIN" || roleStr.includes("ADMIN")) {
        navigate("/admin/dashboard", { replace: true });
      } else {
        navigate("/asha/dashboard", { replace: true });
      }
    } catch (err: any) {
      const msg = err?.message || err?.detail || "Failed to change password. Please verify current password.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      width: "100vw",
      minHeight: "100vh",
      background: "linear-gradient(180deg, #F0F4F9 0%, #E8EEF5 100%)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "24px 16px",
      boxSizing: "border-box",
      fontFamily: "'Noto Sans', -apple-system, BlinkMacSystemFont, sans-serif"
    }}>
      <div style={{
        width: "100%",
        maxWidth: 480,
        backgroundColor: "#FFFFFF",
        borderRadius: 20,
        boxShadow: "0 10px 30px rgba(13, 71, 161, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04)",
        border: "1px solid #E2E8F0",
        padding: "36px 32px",
        boxSizing: "border-box"
      }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            backgroundColor: "#1565C0",
            color: "#FFFFFF",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 12,
            boxShadow: "0 4px 12px rgba(21, 101, 192, 0.25)"
          }}>
            <ShieldCheckIcon size={24} color="#FFFFFF" />
          </div>
          <h1 style={{ margin: "0 0 6px 0", fontSize: 20, fontWeight: 700, color: "#0D2B45" }}>
            Mandatory Password Change
          </h1>
          <p style={{ margin: 0, fontSize: 13, color: "#5A6A80", lineHeight: 1.5 }}>
            Welcome, <strong>{user?.name || "Staff Member"}</strong>! Because you are signing in with a temporary password, you must set a new secure password before accessing your workspace.
          </p>
        </div>

        {/* Notice Box */}
        <div style={{
          backgroundColor: "#FFFBEB",
          border: "1px solid #FDE68A",
          borderRadius: 8,
          padding: "12px 14px",
          marginBottom: 20,
          fontSize: 12.5,
          color: "#92400E",
          display: "flex",
          gap: 10,
          alignItems: "flex-start"
        }}>
          <WarningIcon size={16} color="#D97706" />
          <div>
            <strong>Staff ID:</strong> {user?.staff_id || user?.identifier || "Assigned ID"}<br />
            Please create a private password that you will use for future sign-ins.
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div style={{
            backgroundColor: "#FDECEC",
            border: "1px solid #F5C6CB",
            borderRadius: 8,
            padding: "10px 14px",
            marginBottom: 18,
            fontSize: 13,
            color: "#C62828",
            display: "flex",
            gap: 8,
            alignItems: "center"
          }}>
            <WarningIcon size={16} color="#C62828" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
              Current Temporary Password
            </label>
            <input
              type={showPassword ? "text" : "password"}
              data-testid="input-old-password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
              placeholder="Enter temporary password"
              style={{
                width: "100%",
                height: 44,
                padding: "0 12px",
                borderRadius: 8,
                border: "1px solid #CBD5E1",
                fontSize: 14,
                boxSizing: "border-box"
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
              New Password
            </label>
            <input
              type={showPassword ? "text" : "password"}
              data-testid="input-new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={6}
              placeholder="At least 6 characters"
              style={{
                width: "100%",
                height: 44,
                padding: "0 12px",
                borderRadius: 8,
                border: "1px solid #CBD5E1",
                fontSize: 14,
                boxSizing: "border-box"
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
              Confirm New Password
            </label>
            <input
              type={showPassword ? "text" : "password"}
              data-testid="input-confirm-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={6}
              placeholder="Re-type new password"
              style={{
                width: "100%",
                height: 44,
                padding: "0 12px",
                borderRadius: 8,
                border: "1px solid #CBD5E1",
                fontSize: 14,
                boxSizing: "border-box"
              }}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 4 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#475569", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={showPassword}
                onChange={(e) => setShowPassword(e.target.checked)}
              />
              Show passwords
            </label>
          </div>

          <button
            type="submit"
            data-testid="btn-submit-change-password"
            disabled={isLoading}
            style={{
              height: 48,
              backgroundColor: "#1565C0",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 10,
              fontSize: 15,
              fontWeight: 600,
              cursor: isLoading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              marginTop: 10,
              boxShadow: "0 2px 6px rgba(21, 101, 192, 0.25)"
            }}
          >
            {isLoading ? "Updating Password..." : "Set New Password & Continue"}
          </button>
        </form>
      </div>
    </div>
  );
}
