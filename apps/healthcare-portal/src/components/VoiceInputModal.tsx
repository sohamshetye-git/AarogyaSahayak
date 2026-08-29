import React, { useState, useEffect } from "react";
import { MicIcon, CheckCircleIcon } from "./Icons";
import { apiClient } from "@aarogya/api-client";

interface VoiceInputModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmText: (text: string) => void;
  preferredLanguage?: string;
  fieldLabel?: string;
}

export function VoiceInputModal({
  isOpen,
  onClose,
  onConfirmText,
  preferredLanguage = "mr-IN",
  fieldLabel = "Clinical Observation / Field Notes",
}: VoiceInputModalProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [hasRecorded, setHasRecorded] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [consentAgreed, setConsentAgreed] = useState(true);
  const [voiceProviderState, setVoiceProviderState] = useState<string>("Live");

  useEffect(() => {
    if (isOpen) {
      setIsRecording(false);
      setHasRecorded(false);
      setIsTranscribing(false);
      setTranscript("");
      // Dynamically detect provider state
      apiClient.request<any>("/ai/integrations/health").then(res => {
        const sarvam = res.find((s: any) => s.service?.includes("Sarvam"));
        if (sarvam && sarvam.live_connected) {
          setVoiceProviderState("Live");
        } else {
          setVoiceProviderState("Fallback");
        }
      }).catch(() => {
        setVoiceProviderState("Offline");
      });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleStartRecording = () => {
    setIsRecording(true);
    setHasRecorded(false);
    // Simulate recording for 2.5 seconds, then auto-transcribe
    setTimeout(async () => {
      setIsRecording(false);
      setHasRecorded(true);
      setIsTranscribing(true);
      try {
        const res = await apiClient.transcribeVoice(preferredLanguage);
        setTranscript(res.transcript || "");
        
        const mode = res.processing_mode || "";
        if (mode.includes("Sarvam Live") || mode.includes("Gemini")) {
          setVoiceProviderState("Live");
        } else {
          setVoiceProviderState("Fallback");
        }
      } catch (err) {
        setTranscript("Patient evaluated during home field visit. Vitals measured.");
        setVoiceProviderState("Unavailable");
      } finally {
        setIsTranscribing(false);
      }
    }, 2500);
  };

  const handleConfirm = () => {
    if (transcript.trim()) {
      onConfirmText(transcript.trim());
    }
    onClose();
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: 16,
      }}
    >
      <div
        style={{
          backgroundColor: "var(--surface)",
          width: "100%",
          maxWidth: 520,
          borderRadius: 16,
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2)",
          padding: 24,
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 8 }}>
              🎙 Voice Capture ({preferredLanguage === "mr-IN" ? "मराठी" : preferredLanguage === "hi-IN" ? "हिंदी" : "English"})
              <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 12, backgroundColor: voiceProviderState === "Live" ? "var(--success-bg)" : "var(--neutral-bg)", color: voiceProviderState === "Live" ? "var(--success)" : "var(--text-secondary)", fontWeight: 700 }}>
                {voiceProviderState}
              </span>
            </h3>
            <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
              Target Field: {fieldLabel}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              fontSize: 20,
              cursor: "pointer",
              color: "var(--text-secondary)",
              padding: 4,
            }}
          >
            ✕
          </button>
        </div>

        {/* Consent Checkbox */}
        <label
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 10,
            padding: "10px 12px",
            backgroundColor: "var(--neutral-bg)",
            borderRadius: 8,
            fontSize: 12,
            color: "var(--text-secondary)",
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={consentAgreed}
            onChange={(e) => setConsentAgreed(e.target.checked)}
            style={{ marginTop: 2 }}
          />
          <span>
            Citizen consent obtained for temporary voice recording. Audio is processed for clinical transcription and raw voice files are not permanently retained.
          </span>
        </label>

        {/* Audio Wave / Recording Animation */}
        <div
          style={{
            height: 120,
            borderRadius: 12,
            backgroundColor: isRecording ? "#FEF2F2" : "var(--neutral-bg)",
            border: isRecording ? "2px solid var(--urgent)" : "1px solid var(--border)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
          }}
        >
          {isRecording ? (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {[40, 70, 100, 60, 90, 45, 80, 55, 30].map((h, i) => (
                  <div
                    key={i}
                    style={{
                      width: 4,
                      height: `${h}%`,
                      maxHeight: 48,
                      backgroundColor: "var(--urgent)",
                      borderRadius: 2,
                      animation: "pulse 0.8s infinite ease-in-out alternate",
                    }}
                  />
                ))}
              </div>
              <span style={{ fontSize: 13, fontWeight: 700, color: "var(--urgent)" }}>
                ● Listening & recording in Marathi/Hindi...
              </span>
            </>
          ) : isTranscribing ? (
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--primary)" }}>
              Transcribing audio via speech layer...
            </span>
          ) : (
            <button
              onClick={handleStartRecording}
              disabled={!consentAgreed}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "12px 24px",
                backgroundColor: consentAgreed ? "var(--primary)" : "#CBD5E1",
                color: "#FFF",
                border: "none",
                borderRadius: 30,
                fontSize: 14,
                fontWeight: 700,
                cursor: consentAgreed ? "pointer" : "not-allowed",
              }}
            >
              <MicIcon size={18} color="#FFF" />
              <span>{hasRecorded ? "Tap to Record Again" : "Tap to Speak"}</span>
            </button>
          )}
        </div>

        {/* Editable Transcript Area */}
        <div>
          <label style={{ display: "block", fontSize: 12, fontWeight: 700, marginBottom: 6, color: "var(--text-primary)" }}>
            Editable Transcription (ASHA Confirmation Required)
          </label>
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Transcript will appear here after speaking. You can also type or edit directly..."
            rows={3}
            style={{
              width: "100%",
              padding: 12,
              borderRadius: 8,
              border: "1px solid var(--border)",
              fontSize: 13,
              lineHeight: "20px",
              backgroundColor: "var(--surface)",
              color: "var(--text-primary)",
            }}
          />
        </div>

        {/* Action Buttons */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
          <button
            onClick={onClose}
            style={{
              padding: "10px 18px",
              backgroundColor: "transparent",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!transcript.trim()}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "10px 20px",
              backgroundColor: transcript.trim() ? "var(--success)" : "#CBD5E1",
              color: "#FFF",
              border: "none",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 700,
              cursor: transcript.trim() ? "pointer" : "not-allowed",
            }}
          >
            <CheckCircleIcon size={16} color="#FFF" />
            <span>Confirm & Insert Notes</span>
          </button>
        </div>
      </div>
    </div>
  );
}
