import React, { useState } from "react";
import type { Screen } from "../types";
import {
  WarningIcon,
  PhoneIcon,
  CheckCircleIcon,
  EditIcon,
  InfoIcon,
  LockIcon,
  PlayIcon,
  DocumentIcon,
  ChevronRightIcon,
  CheckIcon,
} from "../components/Icons";
import { PriorityBadge, CaseStatusBadge } from "../components/StatusBadge";

interface CitizenCaseScreenProps {
  onNavigate: (screen: Screen) => void;
  onBack: () => void;
}

function TimelineItem({
  label,
  time,
  status,
  role,
}: {
  label: string;
  time?: string;
  status: "completed" | "current" | "pending";
  role?: string;
}) {
  return (
    <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
        <div
          style={{
            width: 24,
            height: 24,
            borderRadius: "50%",
            backgroundColor:
              status === "completed"
                ? "var(--success)"
                : status === "current"
                ? "var(--primary)"
                : "var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: status === "pending" ? "var(--text-disabled)" : "white",
          }}
        >
          {status === "completed" ? (
            <CheckIcon size={14} />
          ) : (
            <div style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "currentColor" }} />
          )}
        </div>
      </div>
      <div style={{ paddingBottom: 16, flex: 1 }}>
        <div
          style={{
            fontSize: 14,
            fontWeight: status === "current" ? 600 : 400,
            color: status === "pending" ? "var(--text-disabled)" : "var(--text-primary)",
            lineHeight: "20px",
          }}
        >
          {label}
        </div>
        {time && (
          <div style={{ fontSize: 12, color: "var(--text-disabled)", marginTop: 2 }}>{time}</div>
        )}
        {role && (
          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{role}</div>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        backgroundColor: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 14,
        padding: "16px",
        marginBottom: 12,
      }}
    >
      <h3
        style={{
          fontSize: 14,
          fontWeight: 700,
          color: "var(--text-secondary)",
          margin: "0 0 12px",
          textTransform: "uppercase",
          letterSpacing: "0.5px",
        }}
      >
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function CitizenCaseScreen({ onNavigate, onBack }: CitizenCaseScreenProps) {
  const [acknowledged, setAcknowledged] = useState(false);
  const [aiConfirmed, setAiConfirmed] = useState<null | boolean>(null);

  return (
    <div style={{ backgroundColor: "var(--bg)", minHeight: "100%" }}>
      {/* Header */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          borderBottom: "1px solid var(--divider)",
          padding: "12px 16px 14px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <div>
            <div style={{ fontSize: 12, color: "var(--text-disabled)", fontWeight: 500 }}>
              Case A102 · Request from 23 August
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", lineHeight: "24px" }}>
              Sunita Devi, 28
            </div>
          </div>
          <div style={{ marginLeft: "auto" }}>
            <PriorityBadge priority="urgent" />
          </div>
        </div>
        <CaseStatusBadge status={acknowledged ? "acknowledged" : "new"} />
      </div>

      <div style={{ padding: "12px 16px 96px" }}>
        {/* Warning card */}
        <div
          style={{
            backgroundColor: "var(--urgent-bg)",
            border: "1.5px solid var(--urgent)",
            borderRadius: 14,
            padding: "14px 14px",
            marginBottom: 12,
            display: "flex",
            gap: 10,
          }}
          role="alert"
        >
          <WarningIcon size={20} style={{ color: "var(--urgent)", flexShrink: 0, marginTop: 1 }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: "var(--urgent)", marginBottom: 4 }}>
              Urgent professional evaluation recommended
            </div>
            <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: "19px", marginBottom: 10 }}>
              Pregnancy-related warning signs were detected.
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {["Blurred vision", "Severe headache", "Swelling in feet", "BP 150/100"].map((sign) => (
                <span
                  key={sign}
                  style={{
                    padding: "4px 10px",
                    backgroundColor: "var(--surface)",
                    color: "var(--urgent)",
                    borderRadius: 6,
                    fontSize: 12,
                    fontWeight: 600,
                    border: "1px solid var(--urgent)",
                  }}
                >
                  {sign}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Patient summary */}
        <Section title="Patient">
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 16px" }}>
            {[
              ["Name", "Sunita Devi"],
              ["Age", "28 years"],
              ["Village", "Kalyanpur"],
              ["Language", "Marathi"],
              ["Pregnancy", "Approx. 7 months"],
              ["ABHA status", "Linked ✓"],
            ].map(([label, value]) => (
              <div key={label}>
                <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-disabled)", textTransform: "uppercase", letterSpacing: "0.4px" }}>
                  {label}
                </div>
                <div style={{ fontSize: 14, color: "var(--text-primary)", fontWeight: 500, marginTop: 2 }}>
                  {value}
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Original message */}
        <Section title="Citizen's message">
          <div
            style={{
              padding: "10px 12px",
              backgroundColor: "var(--info-bg)",
              borderRadius: 8,
              marginBottom: 10,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <LockIcon size={14} style={{ color: "var(--info)", flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: "var(--info)", lineHeight: "17px" }}>
              This message may contain private health information. Use headphones when possible.
            </span>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              style={{
                flex: 1,
                height: 44,
                backgroundColor: "var(--primary)",
                color: "white",
                border: "none",
                borderRadius: 10,
                fontSize: 14,
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
              }}
            >
              <PlayIcon size={16} />
              Listen to message
            </button>
            <button
              style={{
                height: 44,
                padding: "0 14px",
                backgroundColor: "transparent",
                color: "var(--text-secondary)",
                border: "1.5px solid var(--border)",
                borderRadius: 10,
                fontSize: 14,
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
              }}
            >
              <DocumentIcon size={16} />
              Transcript
            </button>
          </div>
        </Section>

        {/* AI Summary */}
        <Section title="AI-assisted summary">
          <div
            style={{
              padding: "10px 12px",
              backgroundColor: "var(--info-bg)",
              borderRadius: 8,
              marginBottom: 12,
              fontSize: 12,
              color: "var(--info)",
              fontWeight: 600,
              fontStyle: "italic",
            }}
          >
            AI-assisted summary – please verify.
          </div>
          <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: "21px", marginBottom: 12 }}>
            Citizen reported blurred vision and severe headache for 2 days with foot swelling. BP measured at 150/100 mmHg. These signs may indicate pregnancy hypertension and warrant urgent evaluation.
          </div>
          <div style={{ fontSize: 12, color: "var(--text-disabled)", marginBottom: 14 }}>
            Source: Approved maternal-health triage guidance · NHM India
          </div>

          {aiConfirmed === null ? (
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => setAiConfirmed(true)}
                style={{
                  flex: 1,
                  height: 40,
                  backgroundColor: "var(--success-bg)",
                  color: "var(--success)",
                  border: "1.5px solid var(--success)",
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                }}
              >
                <CheckIcon size={15} />
                Confirm summary
              </button>
              <button
                onClick={() => setAiConfirmed(false)}
                style={{
                  flex: 1,
                  height: 40,
                  backgroundColor: "var(--neutral-bg)",
                  color: "var(--neutral)",
                  border: "1.5px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                }}
              >
                <EditIcon size={15} />
                Correct information
              </button>
            </div>
          ) : (
            <div
              style={{
                padding: "10px 14px",
                backgroundColor: aiConfirmed ? "var(--success-bg)" : "var(--followup-bg)",
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 600,
                color: aiConfirmed ? "var(--success)" : "var(--followup)",
              }}
            >
              {aiConfirmed ? "✓ Summary confirmed" : "Information marked for correction"}
            </div>
          )}
        </Section>

        {/* Case timeline */}
        <Section title="Case timeline">
          <TimelineItem
            label="Request received from citizen"
            time="Today, 9:00 AM"
            status="completed"
            role="Citizen"
          />
          <TimelineItem
            label="Warning signs identified"
            time="Today, 9:00 AM"
            status="completed"
            role="System"
          />
          <TimelineItem
            label="ASHA worker notified"
            time="Today, 9:01 AM"
            status="completed"
            role="System"
          />
          <TimelineItem
            label="Waiting for acknowledgement"
            status={acknowledged ? "completed" : "current"}
            role="You"
          />
          <TimelineItem label="Contact citizen" status="pending" />
          <TimelineItem label="Home visit" status="pending" />
        </Section>
      </div>

      {/* Sticky action panel */}
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
          boxShadow: "0 -4px 12px rgba(0,0,0,0.06)",
        }}
      >
        {!acknowledged ? (
          <button
            onClick={() => setAcknowledged(true)}
            style={{
              width: "100%",
              height: 52,
              backgroundColor: "var(--urgent)",
              color: "white",
              border: "none",
              borderRadius: 12,
              fontSize: 16,
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
            }}
          >
            <CheckCircleIcon size={20} />
            Acknowledge case
          </button>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => {}}
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
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                }}
              >
                <PhoneIcon size={16} />
                Call citizen
              </button>
              <button
                onClick={() => onNavigate("field-visit")}
                style={{
                  flex: 1,
                  height: 48,
                  backgroundColor: "var(--teal)",
                  color: "white",
                  border: "none",
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                }}
              >
                Plan visit
                <ChevronRightIcon size={16} />
              </button>
            </div>
            <button
              onClick={() => onNavigate("referral")}
              style={{
                width: "100%",
                height: 44,
                backgroundColor: "transparent",
                color: "var(--urgent)",
                border: "1.5px solid var(--urgent)",
                borderRadius: 10,
                fontSize: 14,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Refer to PHC
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
