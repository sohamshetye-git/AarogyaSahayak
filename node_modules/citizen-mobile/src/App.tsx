import React, { useState, useEffect } from "react";
import { apiClient } from "@aarogya/api-client";

const LANGUAGES = [
  { code: "mr-IN", label: "मराठी (Marathi)", prompt: "माईक दाबा आणि तुमची तब्येत कशी आहे ते सांगा..." },
  { code: "hi-IN", label: "हिंदी (Hindi)", prompt: "माइक दबाएं और बताएं कि आपको क्या तकलीफ है..." },
  { code: "kn-IN", label: "ಕನ್ನಡ (Kannada)", prompt: "ಮೈಕ್ ಒತ್ತಿ ಮತ್ತು ನಿಮ್ಮ ಆರೋಗ್ಯದ ಬಗ್ಗೆ ತಿಳಿಸಿ..." },
  { code: "ta-IN", label: "தமிழ் (Tamil)", prompt: "மைக் அழுத்தி உங்கள் உடல்நிலை பற்றி பேசுங்கள்..." },
  { code: "te-IN", label: "తెలుగు (Telugu)", prompt: "మైక్ నొక్కి మీ ఆరోగ్య సమస్యను చెప్పండి..." },
  { code: "en-IN", label: "English", prompt: "Tap the mic and speak your health symptoms..." },
];

const PRESETS = [
  {
    title: "Scenario 1: Sunita Devi (Maternal Red Flag)",
    lang: "mr-IN",
    spoken: "मला खूप डोकेदुखी होत आहे आणि डोळ्यांसमोर अंधारी येत आहे. पायावर पण सूज आली आहे.",
    symptoms: ["blurred vision", "severe headache", "swollen feet"],
    is_pregnant: true,
    weeks: 28,
  },
  {
    title: "Scenario 2: Ramesh (Severe Chest Pain)",
    lang: "hi-IN",
    spoken: "मुझे सीने में बहुत तेज दर्द हो रहा है और सांस लेने में तकलीफ हो रही है।",
    symptoms: ["severe chest pain", "shortness of breath", "cold sweats"],
    is_pregnant: false,
  },
  {
    title: "Scenario 3: Anil (Mild Routine Cold)",
    lang: "en-IN",
    spoken: "I have a mild runny nose and slight throat irritation since yesterday.",
    symptoms: ["mild runny nose", "throat irritation"],
    is_pregnant: false,
  },
];

export function App() {
  const [selectedLang, setSelectedLang] = useState(LANGUAGES[0]);
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState(PRESETS[0].spoken);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedCase, setSubmittedCase] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"intake" | "history">("intake");
  const [casesHistory, setCasesHistory] = useState<any[]>([]);

  const fetchCases = async () => {
    try {
      const res = await apiClient.request<any[]>("/citizen/cases");
      setCasesHistory(res);
    } catch (err) {
      console.error("Failed to load cases history", err);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  const handleStartRecording = () => {
    setIsRecording(true);
    // Simulate live voice input in demo
    setTimeout(() => {
      setIsRecording(false);
    }, 2500);
  };

  const handleApplyPreset = (preset: typeof PRESETS[0]) => {
    const langObj = LANGUAGES.find((l) => l.code === preset.lang) || LANGUAGES[0];
    setSelectedLang(langObj);
    setTranscript(preset.spoken);
  };

  const handleSubmitCase = async () => {
    setIsSubmitting(true);
    try {
      const activePreset = PRESETS.find((p) => p.spoken === transcript) || PRESETS[0];

      const res = await apiClient.createCitizenCase({
        preferred_language: selectedLang.code,
        spoken_transcript: transcript,
        symptoms: activePreset.symptoms,
        is_pregnant: activePreset.is_pregnant,
        gestational_weeks: activePreset.weeks,
        vitals: activePreset.is_pregnant
          ? { systolic_bp: 150, diastolic_bp: 100, spo2: 97, pulse: 88 }
          : undefined,
      });

      setSubmittedCase(res);
      await fetchCases();
    } catch (err) {
      console.error("Failed to submit citizen intake", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#F4F7FB",
        fontFamily: "'Noto Sans', 'Noto Sans Devanagari', sans-serif",
        display: "flex",
        justifyContent: "center",
        padding: "16px 12px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 480,
          backgroundColor: "#FFFFFF",
          borderRadius: 20,
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.08)",
          border: "1px solid #E2E8F0",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          minHeight: 700,
        }}
      >
        {/* Header Bar */}
        <header
          style={{
            padding: "16px 20px",
            backgroundColor: "#1565C0",
            color: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: "50%",
                backgroundColor: "#FFFFFF",
                color: "#1565C0",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 800,
                fontSize: 16,
              }}
            >
              AS
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 700 }}>आरोग्य सहायक</div>
              <div style={{ fontSize: 11, opacity: 0.9 }}>Voice Health Assistance</div>
            </div>
          </div>

          <a
            href="tel:108"
            style={{
              padding: "6px 12px",
              backgroundColor: "#C62828",
              color: "#FFFFFF",
              borderRadius: 20,
              fontSize: 12,
              fontWeight: 700,
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            🚨 108 Emergency
          </a>
        </header>

        {/* Tab Navigation */}
        <div style={{ display: "flex", borderBottom: "1px solid #E2E8F0" }}>
          <button
            onClick={() => setActiveTab("intake")}
            style={{
              flex: 1,
              padding: "12px",
              border: "none",
              borderBottom: activeTab === "intake" ? "3px solid #1565C0" : "none",
              backgroundColor: activeTab === "intake" ? "#F0F7FF" : "#FFFFFF",
              color: activeTab === "intake" ? "#1565C0" : "#64748B",
              fontWeight: 700,
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            🎙️ Speak Concern
          </button>
          <button
            onClick={() => setActiveTab("history")}
            style={{
              flex: 1,
              padding: "12px",
              border: "none",
              borderBottom: activeTab === "history" ? "3px solid #1565C0" : "none",
              backgroundColor: activeTab === "history" ? "#F0F7FF" : "#FFFFFF",
              color: activeTab === "history" ? "#1565C0" : "#64748B",
              fontWeight: 700,
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            📋 My Cases ({casesHistory.length})
          </button>
        </div>

        {/* Body Content */}
        <div style={{ padding: 20, flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
          {activeTab === "intake" ? (
            <>
              {/* Language Selection */}
              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#475569", marginBottom: 6 }}>
                  Select Language / भाषा निवडा:
                </label>
                <select
                  value={selectedLang.code}
                  onChange={(e) => {
                    const l = LANGUAGES.find((item) => item.code === e.target.value);
                    if (l) setSelectedLang(l);
                  }}
                  style={{
                    width: "100%",
                    height: 42,
                    borderRadius: 8,
                    border: "1px solid #CBD5E1",
                    padding: "0 12px",
                    fontSize: 14,
                    fontWeight: 600,
                    backgroundColor: "#F8FAFC",
                  }}
                >
                  {LANGUAGES.map((l) => (
                    <option key={l.code} value={l.code}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Quick Demo Preset Selector */}
              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#475569", marginBottom: 6 }}>
                  ⚡ Quick Demo Voice Samples:
                </label>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {PRESETS.map((p, i) => (
                    <button
                      key={i}
                      onClick={() => handleApplyPreset(p)}
                      style={{
                        padding: "8px 12px",
                        textAlign: "left",
                        borderRadius: 6,
                        border: transcript === p.spoken ? "2px solid #1565C0" : "1px solid #E2E8F0",
                        backgroundColor: transcript === p.spoken ? "#EFF6FF" : "#FFFFFF",
                        fontSize: 12,
                        fontWeight: 600,
                        cursor: "pointer",
                        color: transcript === p.spoken ? "#1565C0" : "#334155",
                      }}
                    >
                      {p.title}
                    </button>
                  ))}
                </div>
              </div>

              {/* Large Voice Recording Area */}
              <div
                style={{
                  padding: "24px 16px",
                  borderRadius: 16,
                  backgroundColor: isRecording ? "#FEF2F2" : "#F8FAFC",
                  border: isRecording ? "2px solid #EF4444" : "1px solid #E2E8F0",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 14,
                  textAlign: "center",
                }}
              >
                <button
                  onClick={handleStartRecording}
                  style={{
                    width: 76,
                    height: 76,
                    borderRadius: "50%",
                    backgroundColor: isRecording ? "#EF4444" : "#1565C0",
                    border: "none",
                    color: "#FFFFFF",
                    fontSize: 32,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    boxShadow: isRecording
                      ? "0 0 0 8px rgba(239, 68, 68, 0.3)"
                      : "0 4px 14px rgba(21, 101, 192, 0.3)",
                    transition: "all 200ms ease",
                  }}
                >
                  🎙️
                </button>

                <div style={{ fontSize: 13, fontWeight: 700, color: isRecording ? "#DC2626" : "#334155" }}>
                  {isRecording ? "Listening & Transcribing (BHASHINI ASR)..." : selectedLang.prompt}
                </div>
              </div>

              {/* Spoken Transcript Input & Review */}
              <div>
                <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#475569", marginBottom: 6 }}>
                  Spoken Transcript (Recognized):
                </label>
                <textarea
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  rows={3}
                  style={{
                    width: "100%",
                    padding: 12,
                    borderRadius: 8,
                    border: "1px solid #CBD5E1",
                    fontSize: 14,
                    lineHeight: "20px",
                    backgroundColor: "#FFFFFF",
                  }}
                />
              </div>

              {/* Submit / Dispatch Button */}
              <button
                onClick={handleSubmitCase}
                disabled={isSubmitting || !transcript.trim()}
                style={{
                  width: "100%",
                  height: 48,
                  backgroundColor: "#1565C0",
                  color: "#FFFFFF",
                  borderRadius: 10,
                  border: "none",
                  fontSize: 15,
                  fontWeight: 700,
                  cursor: isSubmitting ? "not-allowed" : "pointer",
                }}
              >
                {isSubmitting ? "Connecting to Kalyanpur Health Center..." : "Submit Concern to Local ASHA Worker"}
              </button>

              {/* Result Confirmation Card */}
              {submittedCase && (
                <div
                  style={{
                    padding: 18,
                    borderRadius: 12,
                    backgroundColor: submittedCase.priority === "URGENT" ? "#FEF2F2" : "#F0FDF4",
                    border: submittedCase.priority === "URGENT" ? "1px solid #FECACA" : "1px solid #BBF7D0",
                    display: "flex",
                    flexDirection: "column",
                    gap: 10,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontSize: 14, fontWeight: 800, color: submittedCase.priority === "URGENT" ? "#DC2626" : "#166534" }}>
                      {submittedCase.priority === "URGENT" ? "🚨 Urgent Case Assigned" : "✓ Case Registered"}
                    </span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: "#64748B" }}>
                      {submittedCase.case_reference}
                    </span>
                  </div>

                  <div style={{ fontSize: 13, color: "#1E293B", lineHeight: "20px" }}>
                    {submittedCase.reassurance_message}
                  </div>

                  <div style={{ fontSize: 12, color: "#475569", borderTop: "1px solid rgba(0,0,0,0.06)", paddingTop: 8 }}>
                    <strong>Assigned Worker:</strong> Sita Patel (ASHA Kalyanpur) · <strong>Action:</strong> Home Visit & PHC Consultation
                  </div>
                </div>
              )}
            </>
          ) : (
            /* Cases History Tab */
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {casesHistory.length === 0 ? (
                <div style={{ textAlign: "center", padding: 40, color: "#64748B" }}>No past cases found.</div>
              ) : (
                casesHistory.map((c) => (
                  <div
                    key={c.id}
                    style={{
                      padding: 16,
                      borderRadius: 10,
                      border: "1px solid #E2E8F0",
                      backgroundColor: "#F8FAFC",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 14, fontWeight: 700 }}>{c.case_reference}</span>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: 10,
                          backgroundColor: c.priority === "URGENT" ? "#FEE2E2" : "#DCFCE7",
                          color: c.priority === "URGENT" ? "#DC2626" : "#166534",
                        }}
                      >
                        {c.priority}
                      </span>
                    </div>
                    <div style={{ fontSize: 13, color: "#475569" }}>{c.primary_concern}</div>
                    <div style={{ fontSize: 12, color: "#1565C0", fontWeight: 600, marginTop: 6 }}>
                      Status: {c.status.replace(/_/g, " ")}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
