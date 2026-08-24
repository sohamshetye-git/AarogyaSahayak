import React, { useState } from "react";
import type { Screen } from "../types";
import {
  CheckIcon,
  MicIcon,
  StopIcon,
  WarningIcon,
  LockIcon,
  QrIcon,
  SearchIcon,
  ChevronRightIcon,
  CheckCircleIcon,
  InfoIcon,
  EditIcon,
} from "../components/Icons";

interface FieldVisitScreenProps {
  onNavigate: (screen: Screen) => void;
  onBack: () => void;
}

type Step = 1 | 2 | 3 | 4 | 5 | 6 | 7;

const STEPS = [
  "Confirm citizen",
  "Consent",
  "Reason & symptoms",
  "Vitals",
  "AI review",
  "ASHA review",
  "Submit",
];

const SYMPTOM_OPTIONS = [
  "Fever", "Cough", "Difficulty breathing", "Dizziness",
  "Headache", "Blurred vision", "Chest pain", "Swelling",
  "Bleeding", "Weakness", "Abdominal pain", "Vomiting",
];

const VITALS = [
  { id: "temp", label: "Temperature", unit: "°C", placeholder: "36.5", normal: "36–37.5" },
  { id: "systolic", label: "Systolic BP", unit: "mmHg", placeholder: "120", normal: "90–140" },
  { id: "diastolic", label: "Diastolic BP", unit: "mmHg", placeholder: "80", normal: "60–90" },
  { id: "spo2", label: "SpO₂", unit: "%", placeholder: "98", normal: "95–100" },
  { id: "pulse", label: "Pulse", unit: "bpm", placeholder: "72", normal: "60–100" },
  { id: "rr", label: "Respiratory rate", unit: "/min", placeholder: "16", normal: "12–20" },
  { id: "glucose", label: "Blood glucose", unit: "mg/dL", placeholder: "—", normal: "70–140" },
];

function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div
      style={{
        padding: "10px 16px",
        backgroundColor: "var(--surface)",
        borderBottom: "1px solid var(--divider)",
        display: "flex",
        alignItems: "center",
        gap: 12,
        flexShrink: 0,
      }}
    >
      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
        Step {current} of {total}
      </span>
      <div style={{ flex: 1, height: 6, backgroundColor: "var(--border)", borderRadius: 3 }}>
        <div
          style={{
            height: "100%",
            width: `${(current / total) * 100}%`,
            backgroundColor: "var(--primary)",
            borderRadius: 3,
            transition: "width 250ms ease",
          }}
        />
      </div>
      <span style={{ fontSize: 13, color: "var(--primary)", fontWeight: 600, whiteSpace: "nowrap" }}>
        {STEPS[current - 1]}
      </span>
    </div>
  );
}

function Step1ConfirmCitizen({ onNext }: { onNext: () => void }) {
  const [confirmed, setConfirmed] = useState(false);

  return (
    <div style={{ padding: "20px 16px" }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
        Confirm citizen
      </h2>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 24px", lineHeight: "20px" }}>
        Verify the citizen's identity before beginning this visit.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 24 }}>
        {[
          { icon: QrIcon, label: "Scan ABHA QR code" },
          { icon: SearchIcon, label: "Search by phone number" },
          { icon: SearchIcon, label: "Search by name" },
          { icon: EditIcon, label: "Enter patient ID" },
        ].map(({ icon: Icon, label }) => (
          <button
            key={label}
            onClick={() => setConfirmed(true)}
            style={{
              width: "100%",
              height: 52,
              backgroundColor: "var(--surface)",
              color: "var(--text-primary)",
              border: "1.5px solid var(--border)",
              borderRadius: 12,
              fontSize: 15,
              fontWeight: 500,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "0 16px",
              transition: "border-color 150ms",
            }}
          >
            <Icon size={20} style={{ color: "var(--primary)" }} />
            {label}
          </button>
        ))}
      </div>

      {confirmed && (
        <div
          style={{
            backgroundColor: "var(--primary-light)",
            border: "1.5px solid var(--primary)",
            borderRadius: 14,
            padding: "14px 14px",
            marginBottom: 20,
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--primary)", marginBottom: 8, textTransform: "uppercase" }}>
            Citizen found
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "50%",
                backgroundColor: "var(--primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "white",
                fontWeight: 700,
                fontSize: 18,
              }}
            >
              S
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 16, color: "var(--text-primary)" }}>Sunita Devi</div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Age 28 · Kalyanpur · ···4821</div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            <button
              onClick={onNext}
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
              }}
            >
              Confirm citizen
            </button>
            <button
              onClick={() => setConfirmed(false)}
              style={{
                height: 44,
                padding: "0 16px",
                backgroundColor: "transparent",
                color: "var(--text-secondary)",
                border: "1.5px solid var(--border)",
                borderRadius: 10,
                fontSize: 14,
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Choose another
            </button>
          </div>
        </div>
      )}

      <button
        onClick={onNext}
        style={{
          width: "100%",
          border: "none",
          background: "none",
          color: "var(--text-disabled)",
          fontSize: 14,
          cursor: "pointer",
          padding: "8px 0",
        }}
      >
        Continue without ABHA
      </button>
    </div>
  );
}

function Step2Consent({ onNext }: { onNext: () => void }) {
  const [consent, setConsent] = useState<string | null>(null);

  return (
    <div style={{ padding: "20px 16px" }}>
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            backgroundColor: "var(--info-bg)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 12px",
            color: "var(--primary)",
          }}
        >
          <LockIcon size={28} />
        </div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
          Ask for consent
        </h2>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0, lineHeight: "20px" }}>
          Explain that information from this visit will be recorded to support healthcare and referral.
        </p>
      </div>

      <div
        style={{
          backgroundColor: "var(--info-bg)",
          borderRadius: 10,
          padding: "12px 14px",
          marginBottom: 20,
          fontSize: 13,
          color: "var(--info)",
          lineHeight: "19px",
          fontStyle: "italic",
        }}
      >
        "Aapki jaankari aapki health support ke liye record ki jaayegi."
        <br />
        <span style={{ color: "var(--text-secondary)" }}>
          "Your information will be recorded to support your healthcare."
        </span>
      </div>

      <div style={{ marginBottom: 8, fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
        Has the citizen agreed?
      </div>

      {[
        { key: "yes", label: "Consent given", desc: "Citizen agreed to proceed", color: "var(--success)" },
        { key: "no", label: "Consent not given", desc: "Citizen did not agree", color: "var(--urgent)" },
        { key: "emergency", label: "Emergency minimum-data recording", desc: "Urgent situation – record minimum required information", color: "var(--high)" },
      ].map(({ key, label, desc, color }) => (
        <button
          key={key}
          onClick={() => setConsent(key)}
          style={{
            width: "100%",
            padding: "14px 16px",
            backgroundColor: consent === key ? `${color}10` : "var(--surface)",
            border: `1.5px solid ${consent === key ? color : "var(--border)"}`,
            borderRadius: 12,
            cursor: "pointer",
            textAlign: "left",
            marginBottom: 8,
            transition: "border-color 150ms",
          }}
        >
          <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)", marginBottom: 2 }}>
            {label}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{desc}</div>
        </button>
      ))}

      <div style={{ marginTop: 20, display: "flex", gap: 8 }}>
        <button
          onClick={onNext}
          disabled={!consent}
          style={{
            flex: 1,
            height: 52,
            backgroundColor: consent ? "var(--primary)" : "var(--text-disabled)",
            color: "white",
            border: "none",
            borderRadius: 12,
            fontSize: 16,
            fontWeight: 600,
            cursor: consent ? "pointer" : "not-allowed",
          }}
        >
          Continue
        </button>
      </div>
    </div>
  );
}

function Step3Symptoms({ onNext }: { onNext: () => void }) {
  const [selected, setSelected] = useState<Set<string>>(new Set(["Blurred vision", "Severe headache (use Headache)", "Swelling"]));
  const [recording, setRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);

  const toggle = (s: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };

  return (
    <div style={{ padding: "20px 16px" }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
        Reason and symptoms
      </h2>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px" }}>
        Select all that apply. You can also record voice notes.
      </p>

      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          Reason for visit
        </div>
        <div
          style={{
            padding: "12px 14px",
            backgroundColor: "var(--urgent-bg)",
            border: "1.5px solid var(--urgent)",
            borderRadius: 10,
            fontSize: 14,
            fontWeight: 600,
            color: "var(--urgent)",
          }}
        >
          Citizen-generated alert – urgent
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          Symptoms ({selected.size} selected)
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {SYMPTOM_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => toggle(s)}
              style={{
                padding: "8px 14px",
                borderRadius: 20,
                border: `1.5px solid ${selected.has(s) ? "var(--primary)" : "var(--border)"}`,
                backgroundColor: selected.has(s) ? "var(--primary-light)" : "var(--surface)",
                color: selected.has(s) ? "var(--primary)" : "var(--text-secondary)",
                fontSize: 14,
                fontWeight: selected.has(s) ? 600 : 400,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
                transition: "all 150ms",
              }}
              aria-pressed={selected.has(s)}
            >
              {selected.has(s) && <CheckIcon size={14} />}
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Voice recording */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 14,
          padding: "14px",
          marginBottom: 20,
        }}
      >
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 10 }}>
          Voice-assisted notes
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => setRecording(!recording)}
            style={{
              flex: 1,
              height: 48,
              backgroundColor: recording ? "var(--urgent)" : "var(--primary)",
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
            aria-label={recording ? "Stop recording" : "Start recording"}
          >
            {recording ? <StopIcon size={18} /> : <MicIcon size={18} />}
            {recording ? `Recording ${Math.floor(recordingTime / 60)}:${String(recordingTime % 60).padStart(2, "0")}` : "Record voice notes"}
          </button>
        </div>
        {recording && (
          <div
            style={{
              marginTop: 10,
              padding: "8px 12px",
              backgroundColor: "var(--urgent-bg)",
              borderRadius: 8,
              fontSize: 12,
              color: "var(--urgent)",
              fontWeight: 500,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <div style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "var(--urgent)", animation: "pulse 1s infinite" }} />
            Recording… Citizen consent acknowledged
          </div>
        )}
      </div>

      <button
        onClick={onNext}
        style={{
          width: "100%",
          height: 52,
          backgroundColor: "var(--primary)",
          color: "white",
          border: "none",
          borderRadius: 12,
          fontSize: 16,
          fontWeight: 600,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
        }}
      >
        Continue
        <ChevronRightIcon size={18} />
      </button>
    </div>
  );
}

function Step4Vitals({ onNext }: { onNext: () => void }) {
  const [vitals, setVitals] = useState<Record<string, string>>({
    systolic: "150",
    diastolic: "100",
  });
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({});

  const isOutOfRange = (id: string, value: string) => {
    if (!value || value === "—") return false;
    const v = parseFloat(value);
    if (id === "systolic") return v > 140 || v < 90;
    if (id === "diastolic") return v > 90 || v < 60;
    if (id === "temp") return v > 37.5 || v < 36;
    if (id === "spo2") return v < 95;
    if (id === "pulse") return v > 100 || v < 60;
    return false;
  };

  return (
    <div style={{ padding: "20px 16px" }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
        Record vital signs
      </h2>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px" }}>
        Enter readings from your measurements. Units are shown beside each field.
      </p>

      {VITALS.map(({ id, label, unit, placeholder, normal }) => {
        const val = vitals[id] || "";
        const outOfRange = isOutOfRange(id, val);
        const isConfirmed = confirmed[id];

        return (
          <div key={id} style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 6 }}>
              <label
                htmlFor={`vital-${id}`}
                style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}
              >
                {label}
              </label>
              <span style={{ fontSize: 12, color: "var(--text-disabled)" }}>Normal: {normal}</span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <div style={{ position: "relative", flex: 1 }}>
                <input
                  id={`vital-${id}`}
                  type="number"
                  value={val}
                  onChange={(e) => {
                    setVitals((v) => ({ ...v, [id]: e.target.value }));
                    setConfirmed((c) => ({ ...c, [id]: false }));
                  }}
                  placeholder={placeholder}
                  inputMode="decimal"
                  style={{
                    width: "100%",
                    height: 52,
                    paddingLeft: 16,
                    paddingRight: 56,
                    border: `1.5px solid ${outOfRange && !isConfirmed ? "var(--urgent)" : "var(--border)"}`,
                    borderRadius: 12,
                    fontSize: 18,
                    fontWeight: 600,
                    color: "var(--text-primary)",
                    backgroundColor: outOfRange && !isConfirmed ? "var(--urgent-bg)" : "var(--surface)",
                    outline: "none",
                    boxSizing: "border-box",
                    transition: "border-color 150ms",
                  }}
                />
                <span
                  style={{
                    position: "absolute",
                    right: 14,
                    top: "50%",
                    transform: "translateY(-50%)",
                    fontSize: 13,
                    color: "var(--text-disabled)",
                    fontWeight: 500,
                  }}
                >
                  {unit}
                </span>
              </div>
              {val && (
                <button
                  onClick={() => setConfirmed((c) => ({ ...c, [id]: true }))}
                  style={{
                    width: 48,
                    height: 52,
                    borderRadius: 12,
                    border: "none",
                    backgroundColor: isConfirmed ? "var(--success-bg)" : "var(--neutral-bg)",
                    color: isConfirmed ? "var(--success)" : "var(--text-disabled)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                  aria-label={`Confirm ${label}`}
                >
                  <CheckIcon size={20} />
                </button>
              )}
            </div>
            {outOfRange && !isConfirmed && val && (
              <div
                style={{
                  marginTop: 6,
                  padding: "8px 12px",
                  backgroundColor: "var(--urgent-bg)",
                  borderRadius: 8,
                  fontSize: 12,
                  color: "var(--urgent)",
                  fontWeight: 500,
                }}
                role="alert"
              >
                This reading is outside the expected range. Please check and confirm it.
              </div>
            )}
          </div>
        );
      })}

      {(vitals.systolic === "150" || vitals.diastolic === "100") && (
        <div
          style={{
            margin: "16px 0",
            padding: "14px",
            backgroundColor: "var(--urgent-bg)",
            border: "1.5px solid var(--urgent)",
            borderRadius: 12,
            display: "flex",
            gap: 10,
          }}
          role="alert"
        >
          <WarningIcon size={20} style={{ color: "var(--urgent)", flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: "var(--urgent)", marginBottom: 4 }}>
              Urgent warning signs detected
            </div>
            <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: "18px" }}>
              This combination of symptoms and vital signs needs immediate professional evaluation.
            </div>
          </div>
        </div>
      )}

      <button
        onClick={onNext}
        style={{
          width: "100%",
          height: 52,
          backgroundColor: "var(--primary)",
          color: "white",
          border: "none",
          borderRadius: 12,
          fontSize: 16,
          fontWeight: 600,
          cursor: "pointer",
          marginTop: 8,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
        }}
      >
        Continue
        <ChevronRightIcon size={18} />
      </button>
    </div>
  );
}

function Step5AIReview({ onNext }: { onNext: () => void }) {
  const [rowStatus, setRowStatus] = useState<Record<string, "confirmed" | "needs-verify" | null>>({
    dizziness: "confirmed",
    duration: null,
    bp: "confirmed",
    pregnancy: "confirmed",
    swelling: "confirmed",
  });

  const rows = [
    { id: "dizziness", label: "Symptom", value: "Dizziness" },
    { id: "duration", label: "Duration", value: "2 days" },
    { id: "bp", label: "Blood pressure", value: "150/100" },
    { id: "pregnancy", label: "Pregnancy", value: "Approx. 7 months" },
    { id: "swelling", label: "Swelling", value: "Feet and ankles" },
  ];

  const allConfirmed = rows.every((r) => rowStatus[r.id] === "confirmed");

  return (
    <div style={{ padding: "20px 16px" }}>
      <div
        style={{
          padding: "10px 12px",
          backgroundColor: "var(--info-bg)",
          borderRadius: 8,
          marginBottom: 16,
          fontSize: 12,
          color: "var(--info)",
          fontWeight: 600,
          fontStyle: "italic",
        }}
      >
        AI-assisted summary – please verify.
      </div>

      <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
        Please verify what we understood
      </h2>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: "0 0 20px", lineHeight: "20px" }}>
        Check each item and confirm or correct it.
      </p>

      {rows.map(({ id, label, value }) => {
        const status = rowStatus[id];
        return (
          <div
            key={id}
            style={{
              backgroundColor: "var(--surface)",
              border: `1.5px solid ${
                status === "confirmed"
                  ? "var(--success)"
                  : status === "needs-verify"
                  ? "var(--followup)"
                  : "var(--border)"
              }`,
              borderRadius: 12,
              padding: "12px 14px",
              marginBottom: 10,
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-disabled)", textTransform: "uppercase", letterSpacing: "0.4px" }}>
                {label}
              </div>
              <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", marginTop: 2 }}>
                {value}
              </div>
              {!status && (
                <div style={{ fontSize: 12, color: "var(--followup)", fontWeight: 500, marginTop: 2 }}>
                  This information needs verification.
                </div>
              )}
            </div>
            <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
              <button
                onClick={() => setRowStatus((prev) => ({ ...prev, [id]: "confirmed" }))}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  border: "none",
                  backgroundColor: status === "confirmed" ? "var(--success)" : "var(--success-bg)",
                  color: status === "confirmed" ? "white" : "var(--success)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                aria-label="Confirm"
              >
                <CheckIcon size={16} />
              </button>
              <button
                onClick={() => setRowStatus((prev) => ({ ...prev, [id]: "needs-verify" }))}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  border: "none",
                  backgroundColor: status === "needs-verify" ? "var(--followup)" : "var(--neutral-bg)",
                  color: status === "needs-verify" ? "white" : "var(--neutral)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                aria-label="Mark as needs verification"
              >
                <EditIcon size={16} />
              </button>
            </div>
          </div>
        );
      })}

      <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
        <button
          onClick={onNext}
          style={{
            flex: 1,
            height: 52,
            backgroundColor: "var(--primary)",
            color: "white",
            border: "none",
            borderRadius: 12,
            fontSize: 16,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Confirm information
        </button>
      </div>
      <button
        style={{
          width: "100%",
          marginTop: 10,
          height: 44,
          backgroundColor: "transparent",
          color: "var(--text-secondary)",
          border: "none",
          borderRadius: 10,
          fontSize: 14,
          cursor: "pointer",
        }}
      >
        Mark transcript unclear
      </button>
    </div>
  );
}

function Step6ASHAReview({ onNext }: { onNext: () => void }) {
  const [priority, setPriority] = useState<string | null>(null);

  return (
    <div style={{ padding: "20px 16px" }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 20px" }}>
        Review visit
      </h2>

      {/* Summary sections */}
      {[
        { title: "Confirmed symptoms", value: "Blurred vision, Severe headache, Swelling (feet)" },
        { title: "Vitals", value: "BP 150/100 mmHg · Temp 37.2°C · SpO₂ 97%" },
        { title: "Warning signs", value: "Pregnancy-related hypertension signs" },
      ].map(({ title, value }) => (
        <div
          key={title}
          style={{
            marginBottom: 12,
            padding: "12px 14px",
            backgroundColor: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 10,
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.4px", marginBottom: 4 }}>
            {title}
          </div>
          <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: "20px" }}>{value}</div>
        </div>
      ))}

      <div
        style={{
          padding: "12px 14px",
          backgroundColor: "var(--urgent-bg)",
          border: "1.5px solid var(--urgent)",
          borderRadius: 10,
          marginBottom: 20,
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--urgent)", marginBottom: 4, textTransform: "uppercase" }}>
          Suggested next action
        </div>
        <div style={{ fontSize: 14, color: "var(--text-primary)", fontWeight: 600 }}>
          Refer to PHC – urgent professional evaluation recommended
        </div>
        <div style={{ fontSize: 12, color: "var(--text-disabled)", marginTop: 4, fontStyle: "italic" }}>
          AI-assisted summary – please verify.
        </div>
      </div>

      <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginBottom: 12 }}>
        Do you agree with this priority?
      </div>

      {[
        { key: "yes", label: "Yes – refer to PHC" },
        { key: "change", label: "No, change priority" },
        { key: "advice", label: "Need medical officer's advice" },
      ].map(({ key, label }) => (
        <button
          key={key}
          onClick={() => setPriority(key)}
          style={{
            width: "100%",
            padding: "14px 16px",
            marginBottom: 8,
            backgroundColor: priority === key ? "var(--primary-light)" : "var(--surface)",
            border: `1.5px solid ${priority === key ? "var(--primary)" : "var(--border)"}`,
            borderRadius: 12,
            cursor: "pointer",
            textAlign: "left",
            fontSize: 15,
            fontWeight: 500,
            color: priority === key ? "var(--primary)" : "var(--text-primary)",
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
              border: `2px solid ${priority === key ? "var(--primary)" : "var(--border)"}`,
              backgroundColor: priority === key ? "var(--primary)" : "transparent",
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {priority === key && (
              <div style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "white" }} />
            )}
          </div>
          {label}
        </button>
      ))}

      <button
        onClick={onNext}
        disabled={!priority}
        style={{
          width: "100%",
          height: 52,
          marginTop: 16,
          backgroundColor: priority ? "var(--primary)" : "var(--text-disabled)",
          color: "white",
          border: "none",
          borderRadius: 12,
          fontSize: 16,
          fontWeight: 600,
          cursor: priority ? "pointer" : "not-allowed",
        }}
      >
        Continue to referral
      </button>
    </div>
  );
}

function Step7Submit({ onComplete }: { onComplete: () => void }) {
  const [submitted, setSubmitted] = useState(false);

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
          Visit information saved
        </h2>
        <p style={{ fontSize: 15, color: "var(--text-secondary)", margin: "0 0 32px", lineHeight: "22px" }}>
          The field visit has been recorded and will sync automatically when internet is available.
        </p>
        <button
          onClick={onComplete}
          style={{
            width: "100%",
            height: 52,
            backgroundColor: "var(--primary)",
            color: "white",
            border: "none",
            borderRadius: 12,
            fontSize: 16,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Return to dashboard
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: "20px 16px" }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
        Field-visit summary
      </h2>
      <div
        style={{
          display: "inline-block",
          padding: "4px 10px",
          backgroundColor: "var(--followup-bg)",
          color: "var(--followup)",
          borderRadius: 6,
          fontSize: 12,
          fontWeight: 600,
          marginBottom: 20,
        }}
      >
        Not a final medical diagnosis
      </div>

      {[
        { label: "Patient", value: "Sunita Devi, 28 · Kalyanpur" },
        { label: "Consent", value: "Consent given · Recorded" },
        { label: "Chief concern", value: "Pregnancy-related warning signs" },
        { label: "Confirmed symptoms", value: "Blurred vision, Severe headache, Swelling" },
        { label: "Vitals", value: "BP 150/100 · Temp 37.2°C · SpO₂ 97%" },
        { label: "Warning signs", value: "Pregnancy hypertension signs detected" },
        { label: "ASHA decision", value: "Refer to PHC – urgent" },
      ].map(({ label, value }) => (
        <div
          key={label}
          style={{
            display: "flex",
            gap: 12,
            paddingBottom: 10,
            marginBottom: 10,
            borderBottom: "1px solid var(--divider)",
          }}
        >
          <div style={{ fontSize: 13, color: "var(--text-disabled)", fontWeight: 600, minWidth: 120, flexShrink: 0 }}>
            {label}
          </div>
          <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: "20px" }}>{value}</div>
        </div>
      ))}

      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 24 }}>
        <button
          onClick={() => setSubmitted(true)}
          style={{
            width: "100%",
            height: 52,
            backgroundColor: "var(--primary)",
            color: "white",
            border: "none",
            borderRadius: 12,
            fontSize: 16,
            fontWeight: 700,
            cursor: "pointer",
          }}
        >
          Confirm and send
        </button>
        <button
          style={{
            width: "100%",
            height: 44,
            backgroundColor: "transparent",
            color: "var(--text-secondary)",
            border: "1.5px solid var(--border)",
            borderRadius: 12,
            fontSize: 15,
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          Correct information
        </button>
        <button
          style={{
            width: "100%",
            height: 44,
            backgroundColor: "transparent",
            color: "var(--text-secondary)",
            border: "none",
            borderRadius: 12,
            fontSize: 14,
            cursor: "pointer",
          }}
        >
          Download PDF
        </button>
      </div>
    </div>
  );
}

export default function FieldVisitScreen({ onNavigate, onBack }: FieldVisitScreenProps) {
  const [step, setStep] = useState<Step>(1);

  const next = () => setStep((s) => Math.min(s + 1, 7) as Step);
  const prev = () => {
    if (step === 1) onBack();
    else setStep((s) => (s - 1) as Step);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", backgroundColor: "var(--bg)" }}>
      {/* Step indicator */}
      <StepIndicator current={step} total={7} />

      {/* Step content */}
      <div style={{ flex: 1, overflow: "auto" }}>
        {step === 1 && <Step1ConfirmCitizen onNext={next} />}
        {step === 2 && <Step2Consent onNext={next} />}
        {step === 3 && <Step3Symptoms onNext={next} />}
        {step === 4 && <Step4Vitals onNext={next} />}
        {step === 5 && <Step5AIReview onNext={next} />}
        {step === 6 && <Step6ASHAReview onNext={next} />}
        {step === 7 && <Step7Submit onComplete={() => onNavigate("dashboard")} />}
      </div>

      {/* Bottom controls */}
      {step < 7 && (
        <div
          style={{
            backgroundColor: "var(--surface)",
            borderTop: "1px solid var(--divider)",
            padding: "10px 16px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexShrink: 0,
          }}
        >
          <button
            onClick={prev}
            style={{
              height: 44,
              padding: "0 16px",
              border: "1.5px solid var(--border)",
              borderRadius: 10,
              backgroundColor: "transparent",
              color: "var(--text-secondary)",
              fontSize: 14,
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            ← Back
          </button>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 12,
              color: "var(--success)",
              fontWeight: 500,
            }}
          >
            <InfoIcon size={14} />
            Saved offline
          </div>
          <button
            onClick={() => {}}
            style={{
              height: 44,
              padding: "0 16px",
              border: "none",
              borderRadius: 10,
              backgroundColor: "transparent",
              color: "var(--text-disabled)",
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            Save & exit
          </button>
        </div>
      )}
    </div>
  );
}
