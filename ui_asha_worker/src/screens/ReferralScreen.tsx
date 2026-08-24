import React, { useState } from "react";
import type { Screen } from "../types";
import { HospitalIcon, PhoneIcon, LocationIcon, CheckCircleIcon, ChevronRightIcon, SendIcon } from "../components/Icons";

interface ReferralScreenProps {
  onNavigate: (screen: Screen) => void;
  onBack: () => void;
}

const FACILITIES = [
  {
    id: "1",
    name: "Kalyanpur PHC",
    distance: "2.4 km",
    type: "Government facility",
    phone: "+91 99876 54321",
    hours: "Mon–Sat, 8 AM – 4 PM",
    empanelled: true,
  },
  {
    id: "2",
    name: "District Hospital Nashik",
    distance: "14.8 km",
    type: "Government hospital",
    phone: "+91 99888 11234",
    hours: "24 hours",
    empanelled: true,
  },
];

const URGENCIES = [
  { key: "immediate", label: "Immediate", desc: "Patient needs care now", color: "var(--urgent)" },
  { key: "today", label: "Today", desc: "Within hours", color: "var(--high)" },
  { key: "24h", label: "Within 24 hours", desc: "Tomorrow or today", color: "var(--followup)" },
  { key: "routine", label: "Routine appointment", desc: "Within a week", color: "var(--neutral)" },
];

export default function ReferralScreen({ onNavigate, onBack }: ReferralScreenProps) {
  const [urgency, setUrgency] = useState("immediate");
  const [selectedFacility, setSelectedFacility] = useState("1");
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);

  const handleSend = () => {
    setSending(true);
    setTimeout(() => {
      setSending(false);
      setSubmitted(true);
    }, 1500);
  };

  if (submitted) {
    return (
      <div style={{ padding: "48px 24px", textAlign: "center" }}>
        <div
          style={{
            width: 72,
            height: 72,
            borderRadius: "50%",
            backgroundColor: "var(--success-bg)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 20px",
            color: "var(--success)",
          }}
        >
          <CheckCircleIcon size={40} />
        </div>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
          Referral sent
        </h2>
        <p style={{ fontSize: 15, color: "var(--text-secondary)", margin: "0 0 32px", lineHeight: "22px" }}>
          Kalyanpur PHC has been notified.
        </p>

        {/* Timeline */}
        <div style={{ textAlign: "left", marginBottom: 32 }}>
          {[
            { label: "Referral created", done: true },
            { label: "Doctor notified", done: true },
            { label: "Waiting for doctor acknowledgement", done: false },
          ].map(({ label, done }) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  backgroundColor: done ? "var(--success)" : "var(--border)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "white",
                  flexShrink: 0,
                }}
              >
                {done ? "✓" : "·"}
              </div>
              <span style={{ fontSize: 14, color: done ? "var(--text-primary)" : "var(--text-disabled)", fontWeight: done ? 500 : 400 }}>
                {label}
              </span>
            </div>
          ))}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <button
            onClick={() => {}}
            style={{
              width: "100%",
              height: 48,
              backgroundColor: "var(--primary-light)",
              color: "var(--primary)",
              border: "none",
              borderRadius: 10,
              fontSize: 15,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            View referral report
          </button>
          <button
            onClick={() => {}}
            style={{
              width: "100%",
              height: 48,
              backgroundColor: "var(--teal-light)",
              color: "var(--teal)",
              border: "none",
              borderRadius: 10,
              fontSize: 15,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Inform citizen
          </button>
          <button
            onClick={() => onNavigate("dashboard")}
            style={{
              width: "100%",
              height: 48,
              backgroundColor: "transparent",
              color: "var(--text-secondary)",
              border: "1.5px solid var(--border)",
              borderRadius: 10,
              fontSize: 15,
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Return to dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "16px 16px 100px" }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
        Refer to healthcare facility
      </h2>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px" }}>
        Sunita Devi · Pregnancy-related warning signs
      </p>

      {/* Urgency */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          How urgent is this referral?
        </div>
        {URGENCIES.map(({ key, label, desc, color }) => (
          <button
            key={key}
            onClick={() => setUrgency(key)}
            style={{
              width: "100%",
              padding: "12px 14px",
              marginBottom: 8,
              backgroundColor: urgency === key ? `${color}10` : "var(--surface)",
              border: `1.5px solid ${urgency === key ? color : "var(--border)"}`,
              borderRadius: 12,
              cursor: "pointer",
              textAlign: "left",
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <div
              style={{
                width: 20,
                height: 20,
                borderRadius: "50%",
                border: `2px solid ${urgency === key ? color : "var(--border)"}`,
                backgroundColor: urgency === key ? color : "transparent",
                flexShrink: 0,
              }}
            />
            <div>
              <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)" }}>{label}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{desc}</div>
            </div>
          </button>
        ))}
      </div>

      {/* Facility selection */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          Select facility
        </div>
        {FACILITIES.map((f) => (
          <button
            key={f.id}
            onClick={() => setSelectedFacility(f.id)}
            style={{
              width: "100%",
              padding: "14px 14px",
              marginBottom: 10,
              backgroundColor: selectedFacility === f.id ? "var(--primary-light)" : "var(--surface)",
              border: `1.5px solid ${selectedFacility === f.id ? "var(--primary)" : "var(--border)"}`,
              borderRadius: 14,
              cursor: "pointer",
              textAlign: "left",
            }}
          >
            <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 8 }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  backgroundColor: selectedFacility === f.id ? "var(--primary)" : "var(--neutral-bg)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: selectedFacility === f.id ? "white" : "var(--text-disabled)",
                  flexShrink: 0,
                }}
              >
                <HospitalIcon size={18} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>{f.name}</div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{f.type}</div>
              </div>
              {f.empanelled && (
                <span
                  style={{
                    padding: "3px 8px",
                    backgroundColor: "var(--success-bg)",
                    color: "var(--success)",
                    borderRadius: 5,
                    fontSize: 11,
                    fontWeight: 600,
                    whiteSpace: "nowrap",
                  }}
                >
                  Empanelled
                </span>
              )}
            </div>
            <div style={{ display: "flex", gap: 16, fontSize: 13, color: "var(--text-secondary)" }}>
              <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <LocationIcon size={14} />
                {f.distance}
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <PhoneIcon size={14} />
                {f.phone}
              </span>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-disabled)", marginTop: 4 }}>{f.hours}</div>
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <button
                onClick={(e) => e.stopPropagation()}
                style={{
                  height: 32,
                  padding: "0 12px",
                  backgroundColor: "var(--teal-light)",
                  color: "var(--teal)",
                  border: "none",
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                <PhoneIcon size={12} />
                Call
              </button>
              <button
                onClick={(e) => e.stopPropagation()}
                style={{
                  height: 32,
                  padding: "0 12px",
                  backgroundColor: "var(--primary-light)",
                  color: "var(--primary)",
                  border: "none",
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                <LocationIcon size={12} />
                Directions
              </button>
            </div>
          </button>
        ))}
      </div>

      {/* Referral summary */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: "14px",
          marginBottom: 20,
        }}
      >
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.4px" }}>
          Information included in referral
        </div>
        {["Confirmed symptoms", "Vital signs", "ASHA observations", "Warning signs", "Consent status"].map((item) => (
          <div key={item} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5, fontSize: 13, color: "var(--text-primary)" }}>
            <CheckCircleIcon size={14} style={{ color: "var(--success)", flexShrink: 0 }} />
            {item}
          </div>
        ))}
      </div>

      {/* Sticky footer */}
      <div
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          backgroundColor: "var(--surface)",
          borderTop: "1px solid var(--divider)",
          padding: "12px 16px",
          zIndex: 20,
          display: "flex",
          gap: 8,
        }}
      >
        <button
          onClick={handleSend}
          disabled={sending}
          style={{
            flex: 1,
            height: 52,
            backgroundColor: sending ? "var(--text-disabled)" : "var(--primary)",
            color: "white",
            border: "none",
            borderRadius: 12,
            fontSize: 16,
            fontWeight: 700,
            cursor: sending ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
          }}
        >
          <SendIcon size={18} />
          {sending ? "Sending…" : "Send referral"}
        </button>
        <button
          style={{
            height: 52,
            padding: "0 16px",
            backgroundColor: "transparent",
            color: "var(--text-secondary)",
            border: "1.5px solid var(--border)",
            borderRadius: 12,
            fontSize: 14,
            fontWeight: 500,
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          Save offline
        </button>
      </div>
    </div>
  );
}
