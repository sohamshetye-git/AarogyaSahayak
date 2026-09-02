import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { ShieldCheckIcon, WarningIcon } from "../components/Icons";

export function LoginScreen() {
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("sita.asha");
  const [password, setPassword] = useState("demo123");
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  const handleLogin = async (e?: React.FormEvent, customId?: string) => {
    if (e) e.preventDefault();
    setError(null);
    setErrorCode(null);
    const loginId = customId || identifier;

    try {
      const user = await login(loginId, password);
      const roleStr = String(user.role).toUpperCase();

      let targetPath = "/asha/dashboard";
      if (roleStr === "PHC_DOCTOR" || roleStr.includes("DOCTOR")) {
        targetPath = "/doctor/dashboard";
      } else if (roleStr === "DISTRICT_ADMIN" || roleStr.includes("ADMIN")) {
        targetPath = "/admin/dashboard";
      }

      window.location.href = targetPath;
    } catch (err: any) {
      const code = err.code || "UNKNOWN";
      setErrorCode(code);
      if (code === "BACKEND_UNREACHABLE") {
        setError("Backend unreachable. Please verify server status.");
      } else if (code === "TIMEOUT") {
        setError("Request timed out. Please check network connection.");
      } else if (code === "INVALID_CREDENTIALS") {
        setError("Sign-in details incorrect. Please check identifier and password.");
      } else if (code === "SERVER_ERROR") {
        setError("Server error. Please try again in a few moments.");
      } else {
        setError(err.message || "Invalid login credentials");
      }
    }
  };

  const selectDemoRole = (roleId: string) => {
    setIdentifier(roleId);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "var(--bg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 480,
          backgroundColor: "var(--surface)",
          borderRadius: 16,
          boxShadow: "0 4px 24px rgba(0, 0, 0, 0.06)",
          border: "1px solid var(--border)",
          padding: "36px 32px",
        }}
      >
        {/* Header / Logo */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 14,
              backgroundColor: "var(--primary)",
              color: "#FFF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 16px",
              fontSize: 24,
              fontWeight: 700,
            }}
          >
            AS
          </div>
          <h1 style={{ margin: "0 0 6px", fontSize: 24, fontWeight: 700, color: "var(--text-primary)" }}>
            Aarogya Sahayak
          </h1>
          <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
            Unified Healthcare & Clinical Intelligence Portal
          </p>
        </div>

        {error && (
          <div
            data-testid="login-error-banner"
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: 10,
              padding: "12px 16px",
              backgroundColor: "var(--urgent-bg)",
              color: "var(--urgent)",
              borderRadius: 8,
              fontSize: 13,
              marginBottom: 20,
              border: "1px solid #F5C6CB",
            }}
          >
            <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
              <span style={{ marginTop: 2, flexShrink: 0, display: "inline-flex" }}>
                <WarningIcon size={18} color="var(--urgent)" />
              </span>
              <div>
                <div style={{ fontWeight: 700 }}>{error}</div>
                {errorCode === "BACKEND_UNREACHABLE" && (
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
                    If the cloud server was idle, Render free tier may take up to 30 seconds to wake up.
                  </div>
                )}
              </div>
            </div>
            <button
              type="button"
              data-testid="btn-login-retry"
              onClick={() => handleLogin()}
              style={{
                padding: "4px 10px",
                fontSize: 12,
                fontWeight: 700,
                backgroundColor: "var(--surface)",
                border: "1px solid var(--urgent)",
                color: "var(--urgent)",
                borderRadius: 4,
                cursor: "pointer",
                flexShrink: 0,
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Demo Fast-Login Selector */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 10 }}>
            ⚡ Hackathon Demo Accounts (1-Click Login):
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <button
              type="button"
              data-testid="demo-role-asha"
              onClick={() => selectDemoRole("sita.asha")}
              style={{
                padding: "10px",
                borderRadius: 8,
                border: identifier === "sita.asha" ? "2px solid var(--primary)" : "1px solid var(--border)",
                backgroundColor: identifier === "sita.asha" ? "var(--primary-light)" : "var(--surface)",
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              <div style={{ fontSize: 13, fontWeight: 700, color: "var(--primary)" }}>ASHA Worker</div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Sita Patel (Kalyanpur)</div>
            </button>

            <button
              type="button"
              data-testid="demo-role-doctor"
              onClick={() => selectDemoRole("dr.sharma")}
              style={{
                padding: "10px",
                borderRadius: 8,
                border: identifier === "dr.sharma" ? "2px solid var(--primary)" : "1px solid var(--border)",
                backgroundColor: identifier === "dr.sharma" ? "var(--primary-light)" : "var(--surface)",
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              <div style={{ fontSize: 13, fontWeight: 700, color: "var(--primary)" }}>PHC Doctor</div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>Dr. Abhinav Sharma</div>
            </button>

            <button
              type="button"
              data-testid="demo-role-admin"
              onClick={() => selectDemoRole("dho.admin")}
              style={{
                padding: "10px",
                borderRadius: 8,
                border: identifier === "dho.admin" ? "2px solid var(--primary)" : "1px solid var(--border)",
                backgroundColor: identifier === "dho.admin" ? "var(--primary-light)" : "var(--surface)",
                cursor: "pointer",
                textAlign: "left",
                gridColumn: "span 2",
              }}
            >
              <div style={{ fontSize: 13, fontWeight: 700, color: "var(--primary)" }}>District Health Officer (Admin)</div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>District 04 Analytics & Cluster Signals</div>
            </button>
          </div>
        </div>

        {/* Standard Form */}
        <form onSubmit={(e) => handleLogin(e)}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
              Username / Staff ID
            </label>
            <input
              type="text"
              data-testid="input-username"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
              style={{
                width: "100%",
                height: 48,
                padding: "0 14px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                fontSize: 14,
                color: "var(--text-primary)",
                backgroundColor: "#FAFCFE",
                outline: "none",
              }}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
              Password
            </label>
            <input
              type="password"
              data-testid="input-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{
                width: "100%",
                height: 48,
                padding: "0 14px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                fontSize: 14,
                color: "var(--text-primary)",
                backgroundColor: "#FAFCFE",
                outline: "none",
              }}
            />
          </div>

          <button
            type="submit"
            data-testid="btn-login-submit"
            disabled={isLoading}
            style={{
              width: "100%",
              height: 48,
              backgroundColor: "var(--primary)",
              color: "#FFF",
              borderRadius: 8,
              border: "none",
              fontSize: 15,
              fontWeight: 700,
              cursor: isLoading ? "not-allowed" : "pointer",
              opacity: isLoading ? 0.7 : 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
            }}
          >
            <ShieldCheckIcon size={18} color="#FFF" />
            <span>{isLoading ? "Signing in..." : "Sign In to Healthcare Portal"}</span>
          </button>
        </form>

        <div style={{ marginTop: 24, textAlign: "center", fontSize: 12, color: "var(--text-secondary)" }}>
          Authorized healthcare portal. Access is recorded and restricted by role. Designed with ABDM- and DPDP-aligned privacy principles.
        </div>
      </div>
    </div>
  );
}
