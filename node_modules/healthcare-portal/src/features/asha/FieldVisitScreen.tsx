import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import {
  CheckIcon,
  WarningIcon,
  ChevronRightIcon,
  ChevronLeftIcon,
  CheckCircleIcon,
  HospitalIcon,
  StethoscopeIcon,
} from "../../components/Icons";
import { ashaSyncService } from "../../services/AshaSyncService";
import { connectivityService } from "../../services/ConnectivityService";
import { db } from "../../db/offlineDb";
import { VoiceInputModal } from "../../components/VoiceInputModal";

const STEPS = [
  "1. Confirm Citizen",
  "2. Consent",
  "3. Symptoms",
  "4. Vitals Check",
  "5. Protocol Review",
  "6. ASHA Decision",
  "7. Submit & Refer",
];

export function AshaFieldVisitScreen() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const caseIdParam = searchParams.get("caseId") || "case-canonical-001";

  const [step, setStep] = useState(1);
  const [caseDetails, setCaseDetails] = useState<any>(null);
  const [systolic, setSystolic] = useState(150);
  const [diastolic, setDiastolic] = useState(100);
  const [spo2, setSpo2] = useState(97);
  const [pulse, setPulse] = useState(88);
  const [temp, setTemp] = useState(37.0);
  const [notes, setNotes] = useState("Field visit conducted at home. Patient reports continuous headache and blurred vision for 2 days. Elevated BP 150/100.");
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successReferral, setSuccessReferral] = useState<any>(null);
  const [isOfflineSave, setIsOfflineSave] = useState(false);

  useEffect(() => {
    const loadCase = async () => {
      try {
        const res = await apiClient.getAshaCase(caseIdParam);
        setCaseDetails(res);
        // Cache for offline
        await db.cachedCases.put({
          id: res.id,
          reference: res.reference,
          priority: res.priority,
          status: res.status,
          primary_concern: res.primary_concern,
          citizen_name: res.citizen_name,
          citizen_age: res.citizen_age,
          citizen_phone: res.citizen_phone,
          village_name: res.village_name,
          is_pregnant: res.is_pregnant,
          gestational_weeks: res.gestational_weeks,
          safety_rule_triggered: res.safety_rule_triggered,
          safety_rule_reason: res.safety_rule_reason,
          symptoms: res.symptoms || [],
          vitals: res.vitals || [],
          created_at: res.created_at
        });
      } catch (err) {
        console.error("Failed to load case online, trying offline...", err);
        const cached = await db.cachedCases.get(caseIdParam);
        if (cached) {
          setCaseDetails(cached);
        }
      }
    };
    loadCase();
  }, [caseIdParam]);

  const hasHighBP = systolic >= 140 || diastolic >= 90;
  const isPregnant = caseDetails?.is_pregnant ?? true;

  const handleSubmitVisit = async () => {
    if (isSubmitting) return; // Prevent duplicate clicks
    setIsSubmitting(true);
    
    const visitPayload = {
      case_id: caseDetails?.id || caseIdParam,
      consent_obtained: true,
      symptoms: ["blurred vision", "severe headache", "swollen feet"],
      vitals: {
        systolic_bp: systolic,
        diastolic_bp: diastolic,
        spo2: spo2,
        pulse: pulse,
        temperature_c: temp,
      },
      notes: notes,
      next_action: "REFER_TO_PHC",
      refer_to_facility_id: "PHC-09",
    };

    try {
      if (connectivityService.isOffline()) {
        // Queue the visit creation action
        await ashaSyncService.queueAction('CREATE_VISIT', visitPayload.case_id, visitPayload);
        
        // Save visit draft locally
        await db.visitDrafts.put({
          id: `draft_${Date.now()}`,
          caseId: visitPayload.case_id,
          data: visitPayload,
          savedAt: new Date().toISOString()
        });

        setIsOfflineSave(true);
        setSuccessReferral({ offline: true, reference: caseDetails?.reference || "CASE-2026-001" });
      } else {
        const res = await apiClient.submitFieldVisit(visitPayload);
        setSuccessReferral(res);
      }
    } catch (err) {
      console.error("Failed to submit visit", err);
      // If we failed due to a network error, queue it
      await ashaSyncService.queueAction('CREATE_VISIT', visitPayload.case_id, visitPayload);
      setIsOfflineSave(true);
      setSuccessReferral({ offline: true, reference: caseDetails?.reference || "CASE-2026-001" });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (successReferral) {
    return (
      <div
        style={{
          backgroundColor: "var(--surface)",
          padding: 40,
          borderRadius: 16,
          border: "1px solid var(--border)",
          textAlign: "center",
          maxWidth: 600,
          margin: "40px auto",
        }}
      >
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: "50%",
            backgroundColor: isOfflineSave ? "var(--warning-bg, #FFF3E0)" : "var(--success-bg)",
            color: isOfflineSave ? "var(--warning, #F57C00)" : "var(--success)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 20px",
          }}
        >
          {isOfflineSave ? <WarningIcon size={36} color="var(--warning, #F57C00)" /> : <CheckCircleIcon size={36} color="var(--success)" />}
        </div>
        <h2 style={{ margin: "0 0 8px", fontSize: 22, fontWeight: 700, color: "var(--text-primary)" }}>
          {isOfflineSave ? "Saved Offline" : "Field Visit & PHC Referral Submitted!"}
        </h2>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 24, lineHeight: "22px" }}>
          {isOfflineSave ? (
            <>
              Case <strong>{caseDetails?.reference || successReferral.reference}</strong> has been saved locally because you are offline.<br/>
              It will automatically sync when connection is restored.
            </>
          ) : (
            <>
              Case <strong>{caseDetails?.reference || successReferral.reference}</strong> has been successfully referred to{" "}
              <strong>Kalyanpur Primary Health Center (Dr. Abhinav Sharma)</strong> with Urgent priority flag.
            </>
          )}
        </p>

        <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
          <button
            onClick={() => navigate("/asha/dashboard")}
            style={{
              padding: "12px 24px",
              backgroundColor: "var(--primary)",
              color: "#FFF",
              borderRadius: 8,
              border: "none",
              fontSize: 14,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Progress Stepper Bar */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          padding: "16px 20px",
          borderRadius: 12,
          border: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: 13, fontWeight: 600 }}>
          <span style={{ color: "var(--primary)" }}>Step {step} of {STEPS.length}: {STEPS[step - 1]}</span>
          <span style={{ color: "var(--text-secondary)" }}>Patient: {caseDetails?.citizen_name || "Sunita Devi"}</span>
        </div>
        <div style={{ height: 6, backgroundColor: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
          <div
            style={{
              height: "100%",
              width: `${(step / STEPS.length) * 100}%`,
              backgroundColor: "var(--primary)",
              transition: "width 200ms ease",
            }}
          />
        </div>
      </div>

      {/* Step Content Container */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          padding: 32,
          borderRadius: 16,
          border: "1px solid var(--border)",
          boxShadow: "0 2px 12px rgba(0,0,0,0.03)",
        }}
      >
        {/* Step 1: Confirm Citizen */}
        {step === 1 && (
          <div>
            <h2 style={{ margin: "0 0 8px", fontSize: 20, fontWeight: 700 }}>Confirm Citizen Identity</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 24 }}>
              Verify identity in-person using ABHA ID, name, or phone number before proceeding.
            </p>
            <div style={{ padding: 18, backgroundColor: "var(--primary-light)", borderRadius: 10, border: "1px solid #BBDEFB", marginBottom: 20 }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: "var(--primary-dark)" }}>
                {caseDetails?.citizen_name || "Sunita Devi"}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
                Age: {caseDetails?.citizen_age || 28} · Phone: {caseDetails?.citizen_phone || "9876543210"} · ABHA: 12-3456-7890-1234
              </div>
              <div style={{ fontSize: 13, color: "#C2185B", fontWeight: 700, marginTop: 4 }}>
                Status: Pregnant ({caseDetails?.gestational_weeks || 28} weeks / ~7 months)
              </div>
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
              <input type="checkbox" defaultChecked style={{ width: 18, height: 18 }} />
              <span>I have verified the citizen's physical identity at their residence.</span>
            </label>
          </div>
        )}

        {/* Step 2: Consent */}
        {step === 2 && (
          <div>
            <h2 style={{ margin: "0 0 8px", fontSize: 20, fontWeight: 700 }}>Citizen Consent</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 24 }}>
              Explain the assessment and seek explicit consent for recording vitals and sharing with the PHC doctor.
            </p>
            <div style={{ padding: 16, backgroundColor: "var(--neutral-bg)", borderRadius: 8, fontSize: 14, lineHeight: "22px", marginBottom: 20 }}>
              "Do you consent to having your vital signs measured and shared with Dr. Abhinav Sharma at Kalyanpur PHC for your care plan?"
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14, fontWeight: 600, color: "var(--success)" }}>
              <input type="checkbox" defaultChecked style={{ width: 18, height: 18 }} />
              <span>Explicit verbal and informed consent obtained from the citizen.</span>
            </label>
          </div>
        )}

        {/* Step 3: Symptoms */}
        {step === 3 && (
          <div>
            <h2 style={{ margin: "0 0 8px", fontSize: 20, fontWeight: 700 }}>Verify Presenting Symptoms</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 20 }}>
              Check all symptoms confirmed during this field visit:
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {["Blurred vision / अंधारी", "Severe headache / तीव्र डोकेदुखी", "Swollen feet (Pedal edema) / पायावर सूज", "Dizziness", "Abdominal pain", "Fever"].map((sym, i) => (
                <label
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "12px 14px",
                    borderRadius: 8,
                    border: i < 3 ? "2px solid var(--primary)" : "1px solid var(--border)",
                    backgroundColor: i < 3 ? "var(--primary-light)" : "var(--surface)",
                    fontSize: 14,
                    fontWeight: 600,
                  }}
                >
                  <input type="checkbox" defaultChecked={i < 3} style={{ width: 16, height: 16 }} />
                  <span>{sym}</span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Step 4: Vitals Check */}
        {step === 4 && (
          <div>
            <h2 style={{ margin: "0 0 8px", fontSize: 20, fontWeight: 700 }}>Record Vital Signs</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 20 }}>
              Measure and enter current vitals. High BP thresholds will trigger deterministic warnings.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                  Systolic BP (mmHg)
                </label>
                <input
                  type="number"
                  value={systolic}
                  onChange={(e) => setSystolic(Number(e.target.value))}
                  style={{ width: "100%", height: 48, padding: "0 12px", borderRadius: 8, border: "2px solid var(--primary)", fontSize: 18, fontWeight: 700 }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                  Diastolic BP (mmHg)
                </label>
                <input
                  type="number"
                  value={diastolic}
                  onChange={(e) => setDiastolic(Number(e.target.value))}
                  style={{ width: "100%", height: 48, padding: "0 12px", borderRadius: 8, border: "2px solid var(--primary)", fontSize: 18, fontWeight: 700 }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                  SpO₂ (%)
                </label>
                <input
                  type="number"
                  value={spo2}
                  onChange={(e) => setSpo2(Number(e.target.value))}
                  style={{ width: "100%", height: 48, padding: "0 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 18, fontWeight: 700 }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                  Pulse (bpm)
                </label>
                <input
                  type="number"
                  value={pulse}
                  onChange={(e) => setPulse(Number(e.target.value))}
                  style={{ width: "100%", height: 48, padding: "0 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 18, fontWeight: 700 }}
                />
              </div>
            </div>

            {hasHighBP && isPregnant && (
              <div
                style={{
                  padding: 16,
                  backgroundColor: "var(--urgent-bg)",
                  borderRadius: 10,
                  border: "1px solid #F5C6CB",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  color: "var(--urgent)",
                }}
              >
                <WarningIcon size={24} color="var(--urgent)" />
                <div style={{ fontSize: 14, fontWeight: 700 }}>
                  ALERT: BP {systolic}/{diastolic} in pregnancy (28w) with neurological symptoms: Pregnancy-related warning signs detected. Urgent professional evaluation is recommended.
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 5: Protocol Review */}
        {step === 5 && (
          <div>
            <h2 style={{ margin: "0 0 8px", fontSize: 20, fontWeight: 700 }}>Approved Clinical Guidelines</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 20 }}>
              AI-assisted protocol summary retrieved from MoHFW & ICMR maternal care guidelines:
            </p>
            <div style={{ padding: 18, backgroundColor: "#F0F7FF", borderRadius: 10, border: "1px solid #BEE3F8", fontSize: 14, lineHeight: "24px" }}>
              <div style={{ fontWeight: 700, color: "var(--primary)", marginBottom: 6 }}>
                ICMR Standard Treatment Workflow (Obstetrics):
              </div>
              <div>• Patient demonstrates Stage 2 Gestational Hypertension with cerebral symptoms.</div>
              <div>• Immediate referral to Kalyanpur PHC for medical officer evaluation & baseline lab investigations.</div>
              <div>• Advise left lateral rest and avoid physical exertion.</div>
              <div style={{ marginTop: 10, fontSize: 12, color: "var(--text-secondary)", fontStyle: "italic" }}>
                AI-assisted summary – human review required. Source ID: ICMR-STW-OBS-01.
              </div>
            </div>
          </div>
        )}

        {/* Step 6: ASHA Decision */}
        {step === 6 && (
          <div>
            <h2 style={{ margin: "0 0 8px", fontSize: 20, fontWeight: 700 }}>ASHA Assessment & Action</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 20 }}>
              Enter field visit notes and select facility referral:
            </p>
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <label style={{ fontSize: 13, fontWeight: 600 }}>
                  Field Visit Notes
                </label>
                <button
                  type="button"
                  onClick={() => setShowVoiceModal(true)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "4px 10px",
                    backgroundColor: "var(--primary-light)",
                    color: "var(--primary-dark)",
                    border: "1px solid var(--primary)",
                    borderRadius: 6,
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  🎙 Speak Notes (मराठी / Voice)
                </button>
              </div>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                style={{ width: "100%", padding: 12, borderRadius: 8, border: "1px solid var(--border)", fontSize: 14 }}
              />
            </div>

            <VoiceInputModal
              isOpen={showVoiceModal}
              onClose={() => setShowVoiceModal(false)}
              preferredLanguage="mr-IN"
              fieldLabel="Field Visit Clinical Notes"
              onConfirmText={(text) => setNotes(prev => prev ? `${prev} ${text}` : text)}
            />

            <div style={{ padding: 16, backgroundColor: "var(--primary-light)", borderRadius: 10, border: "1px solid #BBDEFB" }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: "var(--primary-dark)" }}>
                Target Healthcare Facility:
              </div>
              <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", marginTop: 4 }}>
                🏥 Kalyanpur Primary Health Center (PHC-09) · 2.5 km away
              </div>
            </div>
          </div>
        )}

        {/* Step 7: Submit & Refer */}
        {step === 7 && (
          <div>
            <h2 style={{ margin: "0 0 8px", fontSize: 20, fontWeight: 700 }}>Confirm and Transmit to PHC Doctor</h2>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 20 }}>
              Review the complete referral packet before instant transmission to Dr. Abhinav Sharma:
            </p>

            <div style={{ backgroundColor: "var(--neutral-bg)", padding: 16, borderRadius: 8, fontSize: 14, lineHeight: "24px", marginBottom: 20 }}>
              <div><strong>Patient:</strong> {caseDetails?.citizen_name || "Sunita Devi"} (28y, 28w pregnant)</div>
              <div><strong>Recorded BP:</strong> <span style={{ color: "var(--urgent)", fontWeight: 700 }}>{systolic}/{diastolic} mmHg</span></div>
              <div><strong>Symptoms:</strong> Blurred vision, severe headache, pedal edema</div>
              <div><strong>Urgency:</strong> <span style={{ color: "var(--urgent)", fontWeight: 700 }}>URGENT</span></div>
              <div><strong>Facility:</strong> Kalyanpur Primary Health Center</div>
            </div>

            <button
              onClick={handleSubmitVisit}
              disabled={isSubmitting}
              style={{
                width: "100%",
                height: 50,
                backgroundColor: "var(--urgent)",
                color: "#FFF",
                borderRadius: 8,
                border: "none",
                fontSize: 16,
                fontWeight: 700,
                cursor: isSubmitting ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 10,
              }}
            >
              <HospitalIcon size={20} color="#FFF" />
              <span>{isSubmitting ? "Transmitting to Doctor..." : "Submit Urgent PHC Referral"}</span>
            </button>
          </div>
        )}

        {/* Navigation Buttons */}
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 28, paddingTop: 20, borderTop: "1px solid var(--divider)" }}>
          {step > 1 ? (
            <button
              onClick={() => setStep((s) => s - 1)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "10px 18px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                backgroundColor: "var(--surface)",
                fontSize: 14,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <ChevronLeftIcon size={18} color="var(--text-primary)" />
              <span>Back</span>
            </button>
          ) : <div />}

          {step < STEPS.length && (
            <button
              onClick={() => setStep((s) => s + 1)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "10px 24px",
                borderRadius: 8,
                border: "none",
                backgroundColor: "var(--primary)",
                color: "#FFF",
                fontSize: 14,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              <span>Next Step</span>
              <ChevronRightIcon size={18} color="#FFF" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
