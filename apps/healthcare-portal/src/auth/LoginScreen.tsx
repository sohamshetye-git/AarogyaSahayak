import React, { useState } from "react";
import { useAuth } from "./AuthContext";
import {
  ShieldCheckIcon,
  WarningIcon,
  PeopleIcon,
  StethoscopeIcon,
  HospitalIcon,
  CheckIcon,
} from "../components/Icons";

export function LoginScreen() {
  const { login, isLoading } = useAuth();
  const [identifier, setIdentifier] = useState("sita.asha");
  const [password, setPassword] = useState("demo123");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  const handleLogin = async (e?: React.FormEvent, customId?: string) => {
    if (e) e.preventDefault();
    setError(null);
    setErrorCode(null);
    const loginId = customId || identifier;

    try {
      const user = await login(loginId, password);
      
      if (user.must_change_password) {
        window.location.href = "/auth/change-password";
        return;
      }

      const roleStr = String(user.role).toUpperCase();
      let targetPath = "/asha/dashboard";
      if (roleStr === "PHC_DOCTOR" || roleStr.includes("DOCTOR")) {
        targetPath = "/doctor/dashboard";
      } else if (roleStr === "DISTRICT_ADMIN" || roleStr.includes("ADMIN")) {
        targetPath = "/admin/dashboard";
      }

      window.location.href = targetPath;
    } catch (err: any) {
      const code = err?.code || "UNKNOWN";
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
        setError(err?.message || "Invalid login credentials");
      }
    }
  };

  const selectRole = (roleId: string) => {
    setIdentifier(roleId);
  };

  const roles = [
    {
      id: "sita.asha",
      testId: "demo-role-asha",
      title: "ASHA Worker",
      desc: "Field care",
      icon: PeopleIcon,
      gridClass: "role-col-asha",
    },
    {
      id: "dr.sharma",
      testId: "demo-role-doctor",
      title: "PHC Doctor",
      desc: "Clinical care",
      icon: StethoscopeIcon,
      gridClass: "role-col-doctor",
    },
    {
      id: "dho.admin",
      testId: "demo-role-admin",
      title: "District Health Officer",
      desc: "Administration",
      icon: HospitalIcon,
      gridClass: "role-col-admin",
    },
  ];

  return (
    <div className="login-root">
      {/* Dynamic CSS styles */}
      <style>{`
        .login-root {
          width: 100vw;
          min-height: 100vh;
          background: linear-gradient(180deg, #F0F4F9 0%, #E8EEF5 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 32px 16px;
          margin: 0;
          box-sizing: border-box;
          font-family: 'Noto Sans', 'Noto Sans Devanagari', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .login-card {
          width: 100%;
          max-width: 540px;
          margin: 0 auto;
          background: #FFFFFF;
          border-radius: 20px;
          box-shadow: 0 10px 30px rgba(13, 71, 161, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04);
          border: 1px solid #E2E8F0;
          padding: 36px 36px 28px 36px;
          box-sizing: border-box;
        }

        /* Header Area */
        .login-header {
          text-align: center;
          margin-bottom: 20px;
        }

        .logo-badge {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          background: #1565C0;
          color: #FFFFFF;
          font-size: 20px;
          font-weight: 700;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          letter-spacing: -0.5px;
          box-shadow: 0 4px 12px rgba(21, 101, 192, 0.25);
          margin-bottom: 12px;
        }

        .product-title {
          font-size: 22px;
          font-weight: 700;
          color: #0D2B45;
          margin: 0 0 4px 0;
          letter-spacing: -0.3px;
        }

        .product-subtitle {
          font-size: 13.5px;
          font-weight: 500;
          color: #5A6A80;
          margin: 0;
        }

        .header-divider {
          height: 1px;
          background-color: #EDF2F7;
          border: none;
          margin: 20px 0 18px 0;
        }

        .intro-area {
          margin-bottom: 20px;
        }

        .welcome-title {
          font-size: 18px;
          font-weight: 700;
          color: #17202A;
          margin: 0 0 4px 0;
        }

        .welcome-subtext {
          font-size: 13.5px;
          color: #5F6B76;
          margin: 0;
          line-height: 1.45;
        }

        /* Role Selection Section */
        .role-section {
          margin-bottom: 20px;
        }

        .role-section-label {
          font-size: 13px;
          font-weight: 600;
          color: #475569;
          margin-bottom: 10px;
          display: block;
        }

        .role-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }

        .role-col-asha {
          grid-column: 1 / 2;
        }

        .role-col-doctor {
          grid-column: 2 / 3;
        }

        .role-col-admin {
          grid-column: 1 / 3;
        }

        .role-btn {
          width: 100%;
          min-height: 52px;
          padding: 8px 12px;
          border-radius: 12px;
          border: 1px solid #D9E0E7;
          background-color: #FFFFFF;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 10px;
          transition: all 0.18s ease-in-out;
          text-align: left;
          outline: none;
          box-sizing: border-box;
        }

        .role-btn:hover {
          border-color: #1565C0;
          background-color: #F8FBFE;
        }

        .role-btn:focus-visible {
          border-color: #1565C0;
          box-shadow: 0 0 0 3px rgba(21, 101, 192, 0.2);
        }

        .role-btn.selected {
          border: 1.5px solid #1565C0;
          background-color: #EBF3FC;
          box-shadow: 0 2px 6px rgba(21, 101, 192, 0.06);
        }

        .role-icon-container {
          width: 34px;
          height: 34px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          background-color: #F1F5F9;
          color: #475569;
          transition: all 0.18s ease;
        }

        .role-btn.selected .role-icon-container {
          background-color: #1565C0;
          color: #FFFFFF;
        }

        .role-info {
          flex: 1;
          min-width: 0;
        }

        .role-name {
          font-size: 13.5px;
          font-weight: 600;
          color: #1E293B;
          line-height: 1.25;
        }

        .role-btn.selected .role-name {
          color: #0D47A1;
        }

        .role-tagline {
          font-size: 11.5px;
          color: #64748B;
          line-height: 1.25;
          margin-top: 1px;
        }

        .role-radio-check {
          width: 18px;
          height: 18px;
          border-radius: 50%;
          border: 1.5px solid #CBD5E1;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          transition: all 0.18s ease;
          background: #FFFFFF;
        }

        .role-btn.selected .role-radio-check {
          border-color: #1565C0;
          background-color: #1565C0;
          color: #FFFFFF;
        }

        /* Form Controls */
        .form-group {
          margin-bottom: 16px;
        }

        .form-label {
          display: block;
          font-size: 13px;
          font-weight: 600;
          color: #334155;
          margin-bottom: 6px;
        }

        .input-wrapper {
          position: relative;
          display: flex;
          align-items: center;
        }

        .input-icon-lead {
          position: absolute;
          left: 14px;
          color: #64748B;
          pointer-events: none;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .form-input {
          width: 100%;
          height: 48px;
          padding: 0 14px 0 42px;
          border-radius: 10px;
          border: 1px solid #D1D5DB;
          font-size: 14px;
          color: #1E293B;
          background-color: #F8FAFC;
          outline: none;
          transition: border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease;
          box-sizing: border-box;
        }

        .form-input.has-trail {
          padding-right: 44px;
        }

        .form-input:focus {
          border-color: #1565C0;
          background-color: #FFFFFF;
          box-shadow: 0 0 0 3px rgba(21, 101, 192, 0.15);
        }

        .form-input::placeholder {
          color: #94A3B8;
          font-size: 13.5px;
        }

        .password-toggle-btn {
          position: absolute;
          right: 6px;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          padding: 8px;
          cursor: pointer;
          color: #64748B;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .password-toggle-btn:hover {
          color: #1E293B;
        }

        .password-toggle-btn:focus-visible {
          outline: 2px solid #1565C0;
        }

        /* Sign In Button */
        .submit-btn {
          width: 100%;
          height: 50px;
          background-color: #1565C0;
          color: #FFFFFF;
          border-radius: 10px;
          border: 1px solid #0D47A1;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          box-shadow: 0 2px 6px rgba(21, 101, 192, 0.25);
          transition: all 0.15s ease;
          box-sizing: border-box;
          margin-top: 20px;
        }

        .submit-btn:hover:not(:disabled) {
          background-color: #0D47A1;
          box-shadow: 0 4px 12px rgba(21, 101, 192, 0.35);
        }

        .submit-btn:focus-visible {
          outline: none;
          box-shadow: 0 0 0 3px rgba(21, 101, 192, 0.4);
        }

        .submit-btn:disabled {
          opacity: 0.65;
          cursor: not-allowed;
          box-shadow: none;
        }

        .btn-spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: #FFFFFF;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }

        /* Footer */
        .secure-footer {
          margin-top: 22px;
          text-align: center;
          font-size: 12px;
          color: #64748B;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          line-height: 1.4;
        }

        /* Mobile adjustments */
        @media (max-width: 600px) {
          .login-root {
            padding: 16px;
            align-items: center;
          }

          .login-card {
            padding: 24px 20px 20px 20px;
            border-radius: 18px;
          }

          .role-grid {
            grid-template-columns: 1fr;
          }

          .role-col-asha,
          .role-col-doctor,
          .role-col-admin {
            grid-column: 1 / 2;
          }
        }
      `}</style>

      <div className="login-card">
        {/* Header */}
        <div className="login-header">
          <div className="logo-badge">AS</div>
          <h1 className="product-title">Aarogya Sahayak</h1>
          <p className="product-subtitle">Healthcare &amp; Clinical Intelligence Portal</p>
        </div>

        <hr className="header-divider" />

        <div className="intro-area">
          <h2 className="welcome-title">Welcome back</h2>
          <p className="welcome-subtext">Sign in to access your authorized healthcare workspace.</p>
        </div>

        {/* Error Banner */}
        {error && (
          <div
            data-testid="login-error-banner"
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: 10,
              padding: "12px 14px",
              backgroundColor: "var(--urgent-bg, #FDECEC)",
              color: "var(--urgent, #C62828)",
              borderRadius: 8,
              fontSize: 13,
              marginBottom: 18,
              border: "1px solid #F5C6CB",
            }}
          >
            <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
              <span style={{ marginTop: 2, flexShrink: 0, display: "inline-flex" }}>
                <WarningIcon size={16} color="var(--urgent, #C62828)" />
              </span>
              <div>
                <div style={{ fontWeight: 600 }}>{error}</div>
                {errorCode === "BACKEND_UNREACHABLE" && (
                  <div style={{ fontSize: 11, color: "var(--text-secondary, #5F6B76)", marginTop: 3 }}>
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
                fontWeight: 600,
                backgroundColor: "#FFFFFF",
                border: "1px solid var(--urgent, #C62828)",
                color: "var(--urgent, #C62828)",
                borderRadius: 6,
                cursor: "pointer",
                flexShrink: 0,
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Role Selection */}
        <div className="role-section">
          <label className="role-section-label" id="role-select-label">
            Select your role
          </label>
          <div
            role="radiogroup"
            aria-labelledby="role-select-label"
            className="role-grid"
          >
            {roles.map((role) => {
              const isSelected = identifier === role.id;
              const RoleIcon = role.icon;
              return (
                <button
                  key={role.id}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  data-testid={role.testId}
                  onClick={() => selectRole(role.id)}
                  className={`role-btn ${role.gridClass} ${isSelected ? "selected" : ""}`}
                >
                  <div className="role-icon-container">
                    <RoleIcon size={18} />
                  </div>
                  <div className="role-info">
                    <div className="role-name">{role.title}</div>
                    <div className="role-tagline">{role.desc}</div>
                  </div>
                  <div className="role-radio-check" aria-hidden="true">
                    {isSelected && <CheckIcon size={12} color="#FFFFFF" />}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={(e) => handleLogin(e)}>
          <div className="form-group">
            <label htmlFor="input-username" className="form-label">
              Username / Staff ID
            </label>
            <div className="input-wrapper">
              <span className="input-icon-lead">
                <PeopleIcon size={18} />
              </span>
              <input
                id="input-username"
                type="text"
                data-testid="input-username"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="Enter username or staff ID"
                required
                autoComplete="username"
                className="form-input"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="input-password" className="form-label">
              Password
            </label>
            <div className="input-wrapper">
              <span className="input-icon-lead">
                <ShieldCheckIcon size={18} />
              </span>
              <input
                id="input-password"
                type={showPassword ? "text" : "password"}
                data-testid="input-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
                autoComplete="current-password"
                className="form-input has-trail"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="password-toggle-btn"
                aria-label={showPassword ? "Hide password" : "Show password"}
                title={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          <button
            type="submit"
            data-testid="btn-login-submit"
            disabled={isLoading}
            className="submit-btn"
          >
            {isLoading ? (
              <>
                <div className="btn-spinner" aria-hidden="true" />
                <span>Signing in…</span>
              </>
            ) : (
              <>
                <ShieldCheckIcon size={18} color="#FFFFFF" />
                <span>Sign In Securely</span>
              </>
            )}
          </button>
        </form>

        {/* Secure Access Footer */}
        <div className="secure-footer">
          <ShieldCheckIcon size={14} color="#1565C0" />
          <span>Authorized access only • Secure role-based healthcare portal</span>
        </div>
      </div>
    </div>
  );
}

