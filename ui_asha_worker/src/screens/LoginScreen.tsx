import React, { useState } from "react";
import { LockIcon, HospitalIcon, HelpIcon, LanguageIcon } from "../components/Icons";

interface LoginScreenProps {
  onLogin: () => void;
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [workerId, setWorkerId] = useState("");
  const [pin, setPin] = useState("");
  const [showPin, setShowPin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!workerId.trim() || pin.length < 4) {
      setError("Please enter your worker ID and 4-digit PIN.");
      return;
    }
    setError("");
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      onLogin();
    }, 1200);
  };

  return (
    <div
      style={{
        minHeight: "100dvh",
        backgroundColor: "var(--bg)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Mobile: single column; Desktop: split layout */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "stretch",
          maxWidth: "100%",
        }}
      >
        {/* Left panel – visible on desktop */}
        <div
          className="login-left-panel"
          style={{
            flex: "0 0 480px",
            backgroundColor: "var(--primary)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: 48,
          }}
        >
          <div style={{ maxWidth: 360, textAlign: "center" }}>
            <div
              style={{
                width: 72,
                height: 72,
                borderRadius: 20,
                backgroundColor: "rgba(255,255,255,0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 24px",
              }}
            >
              <HospitalIcon size={40} />
            </div>
            <h1
              style={{
                color: "white",
                fontSize: 28,
                fontWeight: 700,
                margin: "0 0 8px",
                lineHeight: "36px",
              }}
            >
              Aarogya Sahayak
            </h1>
            <p style={{ color: "rgba(255,255,255,0.8)", fontSize: 16, margin: "0 0 40px" }}>
              ASHA Copilot
            </p>

            {/* Feature highlights */}
            {[
              "View and manage assigned health cases",
              "Conduct field visits with voice assistance",
              "Refer citizens to PHC facilities",
              "Works offline during field visits",
            ].map((text, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  marginBottom: 16,
                  textAlign: "left",
                }}
              >
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    backgroundColor: "rgba(255,255,255,0.6)",
                    flexShrink: 0,
                    marginTop: 7,
                  }}
                />
                <span style={{ color: "rgba(255,255,255,0.85)", fontSize: 15, lineHeight: "22px" }}>
                  {text}
                </span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: "auto", paddingTop: 32 }}>
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 12, textAlign: "center" }}>
              National Health Mission · Government of India
            </p>
          </div>
        </div>

        {/* Right panel – login form */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "32px 24px",
            minWidth: 0,
          }}
        >
          {/* Mobile logo */}
          <div
            className="login-mobile-logo"
            style={{ marginBottom: 32, textAlign: "center" }}
          >
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 16,
                backgroundColor: "var(--primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 12px",
              }}
            >
              <HospitalIcon size={30} />
            </div>
            <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}>
              Aarogya Sahayak
            </div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>ASHA Copilot</div>
          </div>

          <div style={{ width: "100%", maxWidth: 400 }}>
            <div style={{ marginBottom: 32 }}>
              <h2 style={{ fontSize: 24, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 8px" }}>
                Welcome back
              </h2>
              <p style={{ fontSize: 15, color: "var(--text-secondary)", margin: 0, lineHeight: "22px" }}>
                Sign in to view your assigned health tasks.
              </p>
            </div>

            <form onSubmit={handleSubmit}>
              {/* Worker ID */}
              <div style={{ marginBottom: 20 }}>
                <label
                  htmlFor="worker-id"
                  style={{
                    display: "block",
                    fontSize: 14,
                    fontWeight: 600,
                    color: "var(--text-primary)",
                    marginBottom: 8,
                  }}
                >
                  Mobile number or Worker ID
                </label>
                <input
                  id="worker-id"
                  type="text"
                  value={workerId}
                  onChange={(e) => setWorkerId(e.target.value)}
                  placeholder="Enter mobile number or worker ID"
                  autoComplete="username"
                  style={{
                    width: "100%",
                    height: 52,
                    padding: "0 16px",
                    border: "1.5px solid var(--border)",
                    borderRadius: 12,
                    fontSize: 16,
                    color: "var(--text-primary)",
                    backgroundColor: "var(--surface)",
                    outline: "none",
                    boxSizing: "border-box",
                    transition: "border-color 150ms",
                  }}
                  onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
                  onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                />
              </div>

              {/* PIN */}
              <div style={{ marginBottom: 12 }}>
                <label
                  htmlFor="pin"
                  style={{
                    display: "block",
                    fontSize: 14,
                    fontWeight: 600,
                    color: "var(--text-primary)",
                    marginBottom: 8,
                  }}
                >
                  4-digit PIN
                </label>
                <div style={{ position: "relative" }}>
                  <input
                    id="pin"
                    type={showPin ? "text" : "password"}
                    value={pin}
                    onChange={(e) => setPin(e.target.value.slice(0, 4))}
                    placeholder="••••"
                    autoComplete="current-password"
                    inputMode="numeric"
                    maxLength={4}
                    style={{
                      width: "100%",
                      height: 52,
                      padding: "0 48px 0 16px",
                      border: "1.5px solid var(--border)",
                      borderRadius: 12,
                      fontSize: 20,
                      color: "var(--text-primary)",
                      backgroundColor: "var(--surface)",
                      outline: "none",
                      boxSizing: "border-box",
                      letterSpacing: showPin ? 2 : 6,
                      transition: "border-color 150ms",
                    }}
                    onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
                    onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPin(!showPin)}
                    style={{
                      position: "absolute",
                      right: 12,
                      top: "50%",
                      transform: "translateY(-50%)",
                      border: "none",
                      background: "none",
                      cursor: "pointer",
                      color: "var(--text-disabled)",
                      fontSize: 13,
                      fontWeight: 500,
                      padding: "4px 8px",
                    }}
                    aria-label={showPin ? "Hide PIN" : "Show PIN"}
                  >
                    {showPin ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              <button
                type="button"
                onClick={() => {}}
                style={{
                  border: "none",
                  background: "none",
                  color: "var(--primary)",
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer",
                  padding: 0,
                  marginBottom: 24,
                }}
              >
                Forgot PIN?
              </button>

              {error && (
                <div
                  style={{
                    padding: "10px 14px",
                    backgroundColor: "var(--urgent-bg)",
                    border: "1px solid var(--urgent)",
                    borderRadius: 10,
                    color: "var(--urgent)",
                    fontSize: 14,
                    marginBottom: 16,
                  }}
                  role="alert"
                >
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: "100%",
                  height: 52,
                  backgroundColor: loading ? "var(--text-disabled)" : "var(--primary)",
                  color: "white",
                  border: "none",
                  borderRadius: 12,
                  fontSize: 16,
                  fontWeight: 600,
                  cursor: loading ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  transition: "background-color 150ms",
                  marginBottom: 16,
                }}
              >
                {loading ? (
                  <>
                    <div
                      style={{
                        width: 18,
                        height: 18,
                        border: "2px solid rgba(255,255,255,0.4)",
                        borderTopColor: "white",
                        borderRadius: "50%",
                        animation: "spin 0.8s linear infinite",
                      }}
                    />
                    Signing in…
                  </>
                ) : (
                  <>
                    <LockIcon size={18} />
                    Sign in
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={() => {}}
                style={{
                  width: "100%",
                  height: 48,
                  backgroundColor: "transparent",
                  color: "var(--text-secondary)",
                  border: "1.5px solid var(--border)",
                  borderRadius: 12,
                  fontSize: 15,
                  fontWeight: 500,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                }}
              >
                <LanguageIcon size={18} />
                Change language
              </button>
            </form>

            {/* Trust indicators */}
            <div
              style={{
                marginTop: 32,
                padding: "12px 16px",
                backgroundColor: "var(--success-bg)",
                borderRadius: 10,
                display: "flex",
                alignItems: "center",
                gap: 10,
              }}
            >
              <LockIcon size={16} style={{ color: "var(--success)", flexShrink: 0 }} />
              <p style={{ fontSize: 12, color: "var(--success)", margin: 0, lineHeight: "18px", fontWeight: 500 }}>
                Secure login · Your data is encrypted and protected
              </p>
            </div>

            <div
              style={{
                marginTop: 24,
                textAlign: "center",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 16,
                flexWrap: "wrap",
              }}
            >
              <button
                type="button"
                onClick={() => {}}
                style={{
                  border: "none",
                  background: "none",
                  color: "var(--text-disabled)",
                  fontSize: 12,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                <HelpIcon size={14} />
                Need help? Contact support
              </button>
              <button
                type="button"
                onClick={() => {}}
                style={{
                  border: "none",
                  background: "none",
                  color: "var(--text-disabled)",
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                Privacy policy
              </button>
            </div>

            <p style={{ textAlign: "center", fontSize: 11, color: "var(--text-disabled)", marginTop: 16 }}>
              Version 1.2.0 · NHM India
            </p>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @media (max-width: 768px) {
          .login-left-panel { display: none !important; }
          .login-mobile-logo { display: block !important; }
        }
        @media (min-width: 769px) {
          .login-mobile-logo { display: none !important; }
        }
      `}</style>
    </div>
  );
}
