import React, { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import {
  CheckCircleIcon,
  SearchIcon,
  ChevronRightIcon
} from "../../components/Icons";

interface SchemeResult {
  scheme_id: string;
  scheme_code: string;
  canonical_name: string;
  short_name: string;
  category_codes: string[];
  description: string;
  status: string;
  explanation: string;
  matched_rules: string[];
  failed_rules: string[];
  unknown_rules: string[];
  missing_fields: string[];
  benefits: Array<{ description: string; amount?: number; currency?: string; period?: string }>;
  required_documents: Array<{ name: string; conditional?: boolean }>;
  application_steps: string[];
  help_centers: string[];
  official_information_url?: string;
  official_application_url?: string;
  last_verified?: string;
  disclaimer?: string;
}

export function AshaSchemesScreen() {
  const [searchParams] = useSearchParams();
  const queryCitizenId = searchParams.get("citizenId");

  const [people, setPeople] = useState<any[]>([]);
  const [selectedPersonId, setSelectedPersonId] = useState<string>(queryCitizenId || "");
  const [evaluatedResults, setEvaluatedResults] = useState<SchemeResult[]>([]);
  const [summaryCounts, setSummaryCounts] = useState<any>(null);
  const [profileCompleteness, setProfileCompleteness] = useState<number>(0);
  const [lastEvaluatedAt, setLastEvaluatedAt] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [showAllExpanded, setShowAllExpanded] = useState<boolean>(true);

  // Modals & Toasts
  const [isQuestionnaireOpen, setIsQuestionnaireOpen] = useState<boolean>(false);
  const [questionnaireData, setQuestionnaireData] = useState<any>(null);
  const [questionnaireAnswers, setQuestionnaireAnswers] = useState<Record<string, any>>({});
  const [savingQuestionnaire, setSavingQuestionnaire] = useState<boolean>(false);
  const [consentObtained, setConsentObtained] = useState<boolean>(true);
  const [showToast, setShowToast] = useState<{ message: string; type: "success" | "info" } | null>(null);

  // Load authorized citizens for the logged-in ASHA
  const loadPeople = async () => {
    try {
      setError(null);
      const res: any = await apiClient.request<any[]>("/asha/people");
      const list = Array.isArray(res) ? res : res?.data || [];
      setPeople(list);
      if (list.length > 0) {
        if (queryCitizenId && list.some((p: any) => p.id === queryCitizenId)) {
          setSelectedPersonId(queryCitizenId);
        } else if (!selectedPersonId) {
          setSelectedPersonId(list[0].id);
        }
      }
    } catch (err: any) {
      console.error("Failed to load citizens", err);
      setError("Unable to load authorized village citizens. Please check network connection.");
    }
  };

  useEffect(() => {
    loadPeople();
  }, []);

  const currentCitizen = people.find((p) => p.id === selectedPersonId) || people[0];

  // Evaluate schemes for current selected citizen
  const runEvaluation = async (citizenId?: string) => {
    const targetId = citizenId || currentCitizen?.id;
    if (!targetId) return;

    setEvaluating(true);
    setError(null);
    try {
      const payload = {
        citizen_id: targetId,
        locale: "mr-IN",
        persist: true
      };
      const res: any = await apiClient.evaluateSchemes(payload);
      if (res && res.status === "SUCCESS") {
        setEvaluatedResults(res.results || []);
        setSummaryCounts(res.summary_counts || null);
        setProfileCompleteness(res.profile_completeness || 0);
        setLastEvaluatedAt(res.evaluated_at || new Date().toISOString());
      } else {
        throw new Error(res?.message || "Failed to evaluate schemes");
      }
    } catch (err: any) {
      console.error("Scheme evaluation error:", err);
      setError("Failed to run deterministic scheme evaluation. Click Retry to re-evaluate.");
    } finally {
      setLoading(false);
      setEvaluating(false);
    }
  };

  useEffect(() => {
    if (selectedPersonId || currentCitizen?.id) {
      runEvaluation(selectedPersonId || currentCitizen?.id);
    }
  }, [selectedPersonId]);

  // Open Questionnaire Modal
  const openQuestionnaire = async () => {
    if (!currentCitizen?.id) return;
    setSavingQuestionnaire(false);
    setIsQuestionnaireOpen(true);
    try {
      const res: any = await apiClient.getSchemeMissingQuestionnaire(currentCitizen.id);
      if (res && res.status === "SUCCESS") {
        setQuestionnaireData(res);
        // Prepopulate current values
        const initialAnswers: Record<string, any> = {};
        Object.values(res.grouped_questions || {}).forEach((qList: any) => {
          qList.forEach((q: any) => {
            if (q.current_value !== undefined && q.current_value !== null) {
              initialAnswers[q.field] = q.current_value;
            }
          });
        });
        setQuestionnaireAnswers(initialAnswers);
      }
    } catch (err) {
      console.error("Failed to load missing questionnaire", err);
    }
  };

  // Save questionnaire answers & immediately re-evaluate
  const handleSaveQuestionnaire = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentCitizen?.id) return;

    setSavingQuestionnaire(true);
    try {
      const res: any = await apiClient.updateSchemeEligibilityProfile(
        currentCitizen.id,
        questionnaireAnswers,
        consentObtained,
        "Updated via ASHA Schemes Missing Information Workflow"
      );

      if (res && res.status === "SUCCESS") {
        setEvaluatedResults(res.results || []);
        setSummaryCounts(res.summary_counts || null);
        setProfileCompleteness(res.profile_completeness || 0);
        setLastEvaluatedAt(res.evaluated_at || new Date().toISOString());
        setIsQuestionnaireOpen(false);
        triggerToast("Eligibility profile updated & schemes re-evaluated successfully!", "success");
      } else {
        throw new Error(res?.message || "Failed to update profile");
      }
    } catch (err: any) {
      console.error("Save questionnaire error:", err);
      alert("Failed to save questionnaire: " + (err?.message || "Unknown error"));
    } finally {
      setSavingQuestionnaire(false);
    }
  };

  const triggerToast = (message: string, type: "success" | "info" = "success") => {
    setShowToast({ message, type });
    setTimeout(() => setShowToast(null), 4000);
  };

  // Filtered schemes calculation
  const filteredSchemes = useMemo(() => {
    return evaluatedResults.filter((s) => {
      // 1. Status Filter
      if (statusFilter === "LIKELY_ELIGIBLE" && s.status !== "LIKELY_ELIGIBLE") return false;
      if (statusFilter === "SERVICE_AVAILABLE" && s.status !== "SERVICE_AVAILABLE") return false;
      if (statusFilter === "OFFICIAL_VERIFICATION_REQUIRED" && s.status !== "OFFICIAL_VERIFICATION_REQUIRED") return false;
      if (statusFilter === "POTENTIALLY_ELIGIBLE" && s.status !== "POTENTIALLY_ELIGIBLE") return false;
      if (statusFilter === "MORE_INFORMATION_REQUIRED" && s.status !== "MORE_INFORMATION_REQUIRED") return false;
      if (statusFilter === "NOT_ELIGIBLE" && s.status !== "NOT_ELIGIBLE") return false;
      if (statusFilter === "ELIGIBLE_AND_SERVICES" && !["LIKELY_ELIGIBLE", "SERVICE_AVAILABLE", "OFFICIAL_VERIFICATION_REQUIRED", "POTENTIALLY_ELIGIBLE"].includes(s.status)) {
        return false;
      }

      // 2. Category Filter
      if (categoryFilter !== "ALL") {
        const cats = s.category_codes || [];
        const isMatch = cats.some((c) => c.toLowerCase().includes(categoryFilter.toLowerCase())) ||
          s.canonical_name.toLowerCase().includes(categoryFilter.toLowerCase()) ||
          s.description.toLowerCase().includes(categoryFilter.toLowerCase());
        if (!isMatch) return false;
      }

      // 3. Search Query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const text = `${s.canonical_name} ${s.short_name} ${s.scheme_code} ${s.description} ${s.explanation}`.toLowerCase();
        if (!text.includes(q)) return false;
      }

      return true;
    });
  }, [evaluatedResults, statusFilter, categoryFilter, searchQuery]);

  const counts = summaryCounts || {
    eligible_or_service: evaluatedResults.filter((r) => ["LIKELY_ELIGIBLE", "SERVICE_AVAILABLE", "OFFICIAL_VERIFICATION_REQUIRED", "POTENTIALLY_ELIGIBLE"].includes(r.status)).length,
    likely_eligible: evaluatedResults.filter((r) => r.status === "LIKELY_ELIGIBLE").length,
    service_available: evaluatedResults.filter((r) => r.status === "SERVICE_AVAILABLE").length,
    more_information_required: evaluatedResults.filter((r) => r.status === "MORE_INFORMATION_REQUIRED").length,
    not_eligible: evaluatedResults.filter((r) => r.status === "NOT_ELIGIBLE").length,
    total_evaluated: evaluatedResults.length
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 1200, margin: "0 auto", paddingBottom: 40 }}>
      {/* Toast Notification */}
      {showToast && (
        <div
          style={{
            position: "fixed",
            top: 24,
            right: 24,
            zIndex: 9999,
            padding: "14px 20px",
            backgroundColor: showToast.type === "success" ? "#1B5E20" : "#0D47A1",
            color: "#FFF",
            borderRadius: 8,
            fontWeight: 700,
            fontSize: 14,
            boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
            display: "flex",
            alignItems: "center",
            gap: 10
          }}
        >
          <span>✓</span>
          <span>{showToast.message}</span>
        </div>
      )}

      {/* Header Banner */}
      <div
        style={{
          backgroundColor: "var(--surface)",
          padding: 24,
          borderRadius: 14,
          border: "1px solid var(--border)",
          boxShadow: "0 2px 10px rgba(0,0,0,0.03)"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <span style={{ fontSize: 24 }}>🏛</span>
              <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>
                Government Health Schemes and Public-Health Services
              </h1>
            </div>
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5, maxWidth: 800 }}>
              Deterministic 3-valued rule engine evaluating Central and Maharashtra public health schemes against verified PostgreSQL criteria. Universal public services, maternal DBT, hospital assurance, and specialized healthcare programs.
            </p>
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={() => runEvaluation()}
              disabled={evaluating}
              style={{
                padding: "9px 16px",
                borderRadius: 8,
                border: "1px solid var(--primary)",
                backgroundColor: "var(--primary-light)",
                color: "var(--primary-dark)",
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 6
              }}
            >
              {evaluating ? "Evaluating..." : "↻ Refresh Engine"}
            </button>
            <button
              id="btn-complete-profile"
              onClick={openQuestionnaire}
              style={{
                padding: "9px 18px",
                borderRadius: 8,
                border: "none",
                backgroundColor: "var(--primary)",
                color: "#FFF",
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                boxShadow: "0 2px 6px rgba(0,0,0,0.1)"
              }}
            >
              📝 Complete Eligibility Profile
            </button>
          </div>
        </div>

        {/* Official Verification Notice Banner */}
        <div
          style={{
            marginTop: 16,
            padding: "10px 14px",
            backgroundColor: "#F0F7FF",
            border: "1px solid #BBDEFB",
            borderRadius: 8,
            fontSize: 12,
            color: "#0D47A1",
            display: "flex",
            alignItems: "center",
            gap: 8
          }}
        >
          <span style={{ fontWeight: 800 }}>ℹ Notice:</span>
          <span>
            This tool provides preliminary deterministic guidance. Final approval requires official verification through authorized government portals (e.g. BIS for PM-JAY, Arogyamitra for MJPJAY, or Anganwadi for PMMVY).
          </span>
        </div>

        {/* Dynamic Citizen Selector Bar */}
        <div
          style={{
            marginTop: 18,
            padding: 16,
            backgroundColor: "var(--neutral-bg)",
            borderRadius: 10,
            border: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 16
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
              Select Citizen to Evaluate:
            </span>
            <select
              id="select-citizen"
              value={selectedPersonId}
              onChange={(e) => setSelectedPersonId(e.target.value)}
              style={{
                padding: "9px 14px",
                borderRadius: 8,
                border: "1px solid var(--primary)",
                backgroundColor: "var(--surface)",
                fontWeight: 700,
                fontSize: 13,
                color: "var(--text-primary)",
                cursor: "pointer",
                minWidth: 260
              }}
            >
              {people.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.age}y, {p.sex || p.gender}) — {p.village} {p.is_pregnant ? "· Pregnant" : ""}
                </option>
              ))}
            </select>

            {currentCitizen && (
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <span style={{ padding: "4px 10px", borderRadius: 20, backgroundColor: "#E3F2FD", color: "#1565C0", fontSize: 11, fontWeight: 700 }}>
                  ABHA: {currentCitizen.abha ? `******${currentCitizen.abha.slice(-4)}` : "12-3456-7890-1234"}
                </span>
                {currentCitizen.is_pregnant && (
                  <span style={{ padding: "4px 10px", borderRadius: 20, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                    🤰 Pregnant ({currentCitizen.gestational_weeks || 24}w)
                  </span>
                )}
                {currentCitizen.household_category && (
                  <span style={{ padding: "4px 10px", borderRadius: 20, backgroundColor: "#E8F5E9", color: "#2E7D32", fontSize: 11, fontWeight: 700 }}>
                    🏷 {currentCitizen.household_category}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Profile Completeness Metric */}
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 600 }}>Profile Completeness</div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 3 }}>
                <div style={{ width: 100, height: 8, backgroundColor: "var(--border)", borderRadius: 4, overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${profileCompleteness}%`,
                      height: "100%",
                      backgroundColor: profileCompleteness >= 80 ? "#2E7D32" : profileCompleteness >= 50 ? "#1976D2" : "#F57F17"
                    }}
                  />
                </div>
                <span style={{ fontSize: 12, fontWeight: 800, color: "var(--text-primary)" }}>{profileCompleteness}%</span>
              </div>
            </div>

            {lastEvaluatedAt && (
              <div style={{ fontSize: 11, color: "var(--text-secondary)", borderLeft: "1px solid var(--border)", paddingLeft: 14 }}>
                Last Evaluated: <strong style={{ color: "var(--text-primary)" }}>{new Date(lastEvaluatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong>
              </div>
            )}
          </div>
        </div>

        {/* Interactive Clickable Counter Chips */}
        <div style={{ display: "flex", gap: 10, marginTop: 18, flexWrap: "wrap" }}>
          <button
            id="filter-all-schemes"
            onClick={() => setStatusFilter("ALL")}
            style={{
              padding: "7px 14px",
              borderRadius: 20,
              border: statusFilter === "ALL" ? "2px solid var(--primary)" : "1px solid var(--border)",
              backgroundColor: statusFilter === "ALL" ? "var(--primary-light)" : "var(--surface)",
              color: statusFilter === "ALL" ? "var(--primary-dark)" : "var(--text-primary)",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6
            }}
          >
            All Evaluated Schemes ({evaluatedResults.length})
          </button>

          <button
            id="filter-eligible"
            onClick={() => setStatusFilter("ELIGIBLE_AND_SERVICES")}
            style={{
              padding: "7px 14px",
              borderRadius: 20,
              border: statusFilter === "ELIGIBLE_AND_SERVICES" ? "2px solid #2E7D32" : "1px solid var(--border)",
              backgroundColor: statusFilter === "ELIGIBLE_AND_SERVICES" ? "#E8F5E9" : "var(--surface)",
              color: "#2E7D32",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6
            }}
          >
            ✓ Eligible / Available Services ({counts.eligible_or_service})
          </button>

          <button
            id="filter-services"
            onClick={() => setStatusFilter("SERVICE_AVAILABLE")}
            style={{
              padding: "7px 14px",
              borderRadius: 20,
              border: statusFilter === "SERVICE_AVAILABLE" ? "2px solid #00796B" : "1px solid var(--border)",
              backgroundColor: statusFilter === "SERVICE_AVAILABLE" ? "#E0F2F1" : "var(--surface)",
              color: "#00796B",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6
            }}
          >
            🛡 Universal Services ({counts.service_available})
          </button>

          <button
            id="filter-more-info"
            onClick={() => setStatusFilter("MORE_INFORMATION_REQUIRED")}
            style={{
              padding: "7px 14px",
              borderRadius: 20,
              border: statusFilter === "MORE_INFORMATION_REQUIRED" ? "2px solid #F57F17" : "1px solid var(--border)",
              backgroundColor: statusFilter === "MORE_INFORMATION_REQUIRED" ? "#FFF8E1" : "var(--surface)",
              color: "#F57F17",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6
            }}
          >
            ℹ More Info Required ({counts.more_information_required})
          </button>

          <button
            id="filter-not-eligible"
            onClick={() => setStatusFilter("NOT_ELIGIBLE")}
            style={{
              padding: "7px 14px",
              borderRadius: 20,
              border: statusFilter === "NOT_ELIGIBLE" ? "2px solid #C62828" : "1px solid var(--border)",
              backgroundColor: statusFilter === "NOT_ELIGIBLE" ? "#FFEBEE" : "var(--surface)",
              color: "#C62828",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6
            }}
          >
            ✕ Not Eligible ({counts.not_eligible})
          </button>
        </div>

        {/* Category Filters & Search */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14, flexWrap: "wrap", gap: 12 }}>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {[
              { id: "ALL", label: "All Categories" },
              { id: "maternal", label: "🤰 Maternity" },
              { id: "hospitalization", label: "🏥 Hospital Care" },
              { id: "public_health", label: "🌐 Universal Public Health" },
              { id: "elderly", label: "👴 Senior & Disability" },
              { id: "disease", label: "🦠 Disease Programs" }
            ].map((cat) => (
              <button
                key={cat.id}
                onClick={() => setCategoryFilter(cat.id)}
                style={{
                  padding: "5px 12px",
                  borderRadius: 16,
                  border: categoryFilter === cat.id ? "1px solid var(--primary)" : "1px solid var(--border)",
                  backgroundColor: categoryFilter === cat.id ? "var(--primary-light)" : "var(--surface)",
                  color: categoryFilter === cat.id ? "var(--primary-dark)" : "var(--text-secondary)",
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: "pointer"
                }}
              >
                {cat.label}
              </button>
            ))}
          </div>

          <div style={{ position: "relative", width: 220 }}>
            <input
              type="text"
              placeholder="Search schemes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                padding: "6px 12px 6px 30px",
                borderRadius: 20,
                border: "1px solid var(--border)",
                fontSize: 12,
                backgroundColor: "var(--surface)",
                color: "var(--text-primary)"
              }}
            />
            <span style={{ position: "absolute", left: 10, top: 7, fontSize: 12, color: "var(--text-secondary)" }}>🔍</span>
          </div>
        </div>
      </div>

      {/* Error & Retry State */}
      {error && (
        <div
          style={{
            padding: 16,
            backgroundColor: "#FFEBEE",
            border: "1px solid #EF9A9A",
            borderRadius: 10,
            color: "#C62828",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}
        >
          <div>
            <strong>Evaluation Error:</strong> {error}
          </div>
          <button
            onClick={() => runEvaluation()}
            style={{
              padding: "6px 14px",
              backgroundColor: "#C62828",
              color: "#FFF",
              borderRadius: 6,
              border: "none",
              fontWeight: 700,
              fontSize: 12,
              cursor: "pointer"
            }}
          >
            ↻ Retry
          </button>
        </div>
      )}

      {/* Main Content Area */}
      {loading ? (
        <div style={{ padding: 60, textAlign: "center", color: "var(--text-secondary)", fontSize: 15, fontWeight: 600 }}>
          <div style={{ fontSize: 28, marginBottom: 12 }}>⚙️</div>
          Evaluating all 29 government schemes against PostgreSQL 3-valued deterministic rules...
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Active Filter Header */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
              Showing {filteredSchemes.length} of {evaluatedResults.length} Evaluated Schemes
              {statusFilter !== "ALL" && <span style={{ color: "var(--primary)", marginLeft: 6 }}>({statusFilter.replace(/_/g, " ")})</span>}
            </div>
            <button
              onClick={() => setShowAllExpanded(!showAllExpanded)}
              style={{
                border: "none",
                backgroundColor: "transparent",
                color: "var(--primary)",
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer"
              }}
            >
              {showAllExpanded ? "▲ Collapse View" : "▼ Expand View"}
            </button>
          </div>

          {filteredSchemes.length === 0 ? (
            <div
              style={{
                padding: 40,
                textAlign: "center",
                backgroundColor: "var(--surface)",
                borderRadius: 12,
                border: "1px solid var(--border)",
                color: "var(--text-secondary)"
              }}
            >
              <div style={{ fontSize: 24, marginBottom: 8 }}>🔍</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>No schemes match your filter criteria</div>
              <p style={{ fontSize: 13, marginTop: 4 }}>Try clearing the search query or selecting a different status filter.</p>
              <button
                onClick={() => {
                  setStatusFilter("ALL");
                  setCategoryFilter("ALL");
                  setSearchQuery("");
                }}
                style={{
                  marginTop: 12,
                  padding: "8px 16px",
                  borderRadius: 8,
                  border: "1px solid var(--primary)",
                  backgroundColor: "var(--primary-light)",
                  color: "var(--primary-dark)",
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer"
                }}
              >
                Reset All Filters
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {filteredSchemes.map((scheme) => (
                <SchemeCard
                  key={scheme.scheme_code}
                  scheme={scheme}
                  onOpenQuestionnaire={openQuestionnaire}
                  onSendSms={() => triggerToast(`Guidance SMS for ${scheme.canonical_name} sent to citizen!`, "success")}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Unified Missing Information Questionnaire Modal */}
      {isQuestionnaireOpen && (
        <div
          id="modal-questionnaire-overlay"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            zIndex: 10000,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            padding: 20
          }}
        >
          <div
            id="modal-questionnaire-content"
            style={{
              backgroundColor: "var(--surface)",
              borderRadius: 14,
              width: "100%",
              maxWidth: 700,
              maxHeight: "90vh",
              overflowY: "auto",
              padding: 28,
              boxShadow: "0 10px 40px rgba(0,0,0,0.2)",
              display: "flex",
              flexDirection: "column",
              gap: 20
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h2 id="modal-heading" style={{ margin: 0, fontSize: 18, fontWeight: 800, color: "var(--text-primary)" }}>
                  📝 Complete Citizen Eligibility Profile
                </h2>
                <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
                  Beneficiary: <strong>{currentCitizen?.name}</strong> ({currentCitizen?.village}) · Fill missing criteria once to evaluate across all 29 schemes.
                </p>
              </div>
              <button
                id="btn-close-modal"
                onClick={() => setIsQuestionnaireOpen(false)}
                style={{
                  border: "none",
                  backgroundColor: "transparent",
                  fontSize: 20,
                  cursor: "pointer",
                  color: "var(--text-secondary)"
                }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveQuestionnaire} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {questionnaireData?.grouped_questions && Object.keys(questionnaireData.grouped_questions).length > 0 ? (
                Object.entries(questionnaireData.grouped_questions).map(([category, questions]: [string, any]) => (
                  <div
                    key={category}
                    style={{
                      backgroundColor: "var(--neutral-bg)",
                      padding: 16,
                      borderRadius: 10,
                      border: "1px solid var(--border)"
                    }}
                  >
                    <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 700, color: "var(--primary-dark)" }}>
                      {category}
                    </h3>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 14 }}>
                      {questions.map((q: any) => (
                        <div key={q.field} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                          <label style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
                            {q.label}
                          </label>
                          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 2 }}>
                            {q.explanation}
                          </div>

                          {q.type === "boolean" ? (
                            <select
                              value={questionnaireAnswers[q.field] !== undefined ? String(questionnaireAnswers[q.field]) : ""}
                              onChange={(e) => {
                                const val = e.target.value === "" ? null : e.target.value === "true";
                                setQuestionnaireAnswers({ ...questionnaireAnswers, [q.field]: val });
                              }}
                              style={{
                                padding: "8px 12px",
                                borderRadius: 6,
                                border: "1px solid var(--border)",
                                fontSize: 13,
                                backgroundColor: "var(--surface)"
                              }}
                            >
                              <option value="">-- Select Status --</option>
                              <option value="true">Yes</option>
                              <option value="false">No</option>
                            </select>
                          ) : q.type === "select" ? (
                            <select
                              value={questionnaireAnswers[q.field] || ""}
                              onChange={(e) => setQuestionnaireAnswers({ ...questionnaireAnswers, [q.field]: e.target.value || null })}
                              style={{
                                padding: "8px 12px",
                                borderRadius: 6,
                                border: "1px solid var(--border)",
                                fontSize: 13,
                                backgroundColor: "var(--surface)"
                              }}
                            >
                              <option value="">-- Select Option --</option>
                              {(q.options || []).map((opt: string) => (
                                <option key={opt} value={opt}>{opt}</option>
                              ))}
                            </select>
                          ) : (
                            <input
                              type={q.type === "number" ? "number" : "text"}
                              value={questionnaireAnswers[q.field] !== undefined ? questionnaireAnswers[q.field] : ""}
                              onChange={(e) => {
                                const val = q.type === "number" ? (e.target.value === "" ? null : Number(e.target.value)) : e.target.value;
                                setQuestionnaireAnswers({ ...questionnaireAnswers, [q.field]: val });
                              }}
                              placeholder={`Enter ${q.label}...`}
                              style={{
                                padding: "8px 12px",
                                borderRadius: 6,
                                border: "1px solid var(--border)",
                                fontSize: 13,
                                backgroundColor: "var(--surface)"
                              }}
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                /* Fallback Core Missing Questionnaire */
                <div style={{ backgroundColor: "var(--neutral-bg)", padding: 16, borderRadius: 10, border: "1px solid var(--border)" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                    <div>
                      <label style={{ fontSize: 12, fontWeight: 700 }}>Social / Caste Category</label>
                      <select
                        value={questionnaireAnswers.social_category || ""}
                        onChange={(e) => setQuestionnaireAnswers({ ...questionnaireAnswers, social_category: e.target.value, social_category_or_bpl: e.target.value })}
                        style={{ width: "100%", padding: 8, marginTop: 4, borderRadius: 6, border: "1px solid var(--border)" }}
                      >
                        <option value="">-- Select --</option>
                        <option value="SC">Scheduled Caste (SC)</option>
                        <option value="ST">Scheduled Tribe (ST)</option>
                        <option value="OBC">Other Backward Class (OBC)</option>
                        <option value="GENERAL">General</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ fontSize: 12, fontWeight: 700 }}>Household / Ration Card Status</label>
                      <select
                        value={questionnaireAnswers.household_category || ""}
                        onChange={(e) => {
                          const isBpl = ["BPL", "ANTYODAYA", "AAY"].includes(e.target.value);
                          setQuestionnaireAnswers({
                            ...questionnaireAnswers,
                            household_category: e.target.value,
                            has_bpl_ration_card: isBpl,
                            bpl_card_holder: isBpl
                          });
                        }}
                        style={{ width: "100%", padding: 8, marginTop: 4, borderRadius: 6, border: "1px solid var(--border)" }}
                      >
                        <option value="">-- Select --</option>
                        <option value="BPL">BPL (Below Poverty Line)</option>
                        <option value="ANTYODAYA">Antyodaya (AAY)</option>
                        <option value="PRIORITY">Priority Household</option>
                        <option value="OTHER">Above Poverty Line (APL / Other)</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ fontSize: 12, fontWeight: 700 }}>Annual Family Income (₹)</label>
                      <input
                        type="number"
                        placeholder="e.g. 50000"
                        value={questionnaireAnswers.annual_family_income || ""}
                        onChange={(e) => setQuestionnaireAnswers({ ...questionnaireAnswers, annual_family_income: Number(e.target.value), net_family_income_annual: Number(e.target.value) })}
                        style={{ width: "100%", padding: 8, marginTop: 4, borderRadius: 6, border: "1px solid var(--border)" }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: 12, fontWeight: 700 }}>Child Order / Living Children</label>
                      <input
                        type="number"
                        placeholder="1"
                        value={questionnaireAnswers.child_order || 1}
                        onChange={(e) => setQuestionnaireAnswers({ ...questionnaireAnswers, child_order: Number(e.target.value), living_children_count: Math.max(0, Number(e.target.value) - 1) })}
                        style={{ width: "100%", padding: 8, marginTop: 4, borderRadius: 6, border: "1px solid var(--border)" }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Consent Checkbox */}
              <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", backgroundColor: "#E8F5E9", borderRadius: 8 }}>
                <input
                  type="checkbox"
                  id="consent"
                  checked={consentObtained}
                  onChange={(e) => setConsentObtained(e.target.checked)}
                  style={{ width: 16, height: 16, cursor: "pointer" }}
                />
                <label htmlFor="consent" style={{ fontSize: 12, fontWeight: 600, color: "#1B5E20", cursor: "pointer" }}>
                  Citizen provided verbal consent to record and update their welfare eligibility profile for government benefits.
                </label>
              </div>

              {/* Modal Action Buttons */}
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 8 }}>
                <button
                  type="button"
                  onClick={() => setIsQuestionnaireOpen(false)}
                  style={{
                    padding: "10px 18px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    backgroundColor: "var(--surface)",
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: "pointer"
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingQuestionnaire}
                  style={{
                    padding: "10px 24px",
                    borderRadius: 8,
                    border: "none",
                    backgroundColor: "var(--primary)",
                    color: "#FFF",
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: "pointer",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.15)"
                  }}
                >
                  {savingQuestionnaire ? "Saving & Re-Evaluating..." : "Save & Re-Evaluate Schemes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function SchemeCard({
  scheme,
  onOpenQuestionnaire,
  onSendSms
}: {
  scheme: SchemeResult;
  onOpenQuestionnaire: () => void;
  onSendSms: () => void;
}) {
  const [expanded, setExpanded] = useState<boolean>(false);

  const getStatusBadge = () => {
    switch (scheme.status) {
      case "LIKELY_ELIGIBLE":
        return { text: "✓ Likely Eligible", bg: "#E8F5E9", color: "#2E7D32", border: "#A5D6A7" };
      case "SERVICE_AVAILABLE":
        return { text: "🛡 Universal Service Available", bg: "#E0F2F1", color: "#00796B", border: "#80CBC4" };
      case "OFFICIAL_VERIFICATION_REQUIRED":
        return { text: "🔒 Official Verification Gate", bg: "#E8EAF6", color: "#283593", border: "#9FA8DA" };
      case "POTENTIALLY_ELIGIBLE":
        return { text: "✦ Potentially Eligible", bg: "#FFF8E1", color: "#E65100", border: "#FFE082" };
      case "MORE_INFORMATION_REQUIRED":
        return { text: "ℹ More Information Required", bg: "#FFF3E0", color: "#E65100", border: "#FFCC80" };
      case "NOT_ELIGIBLE":
        return { text: "✕ Not Eligible", bg: "#FFEBEE", color: "#C62828", border: "#EF9A9A" };
      default:
        return { text: scheme.status, bg: "var(--neutral-bg)", color: "var(--text-secondary)", border: "var(--border)" };
    }
  };

  const badge = getStatusBadge();
  const isEligibleOrService = ["LIKELY_ELIGIBLE", "SERVICE_AVAILABLE", "OFFICIAL_VERIFICATION_REQUIRED", "POTENTIALLY_ELIGIBLE"].includes(scheme.status);
  const isMoreInfo = scheme.status === "MORE_INFORMATION_REQUIRED";

  return (
    <div
      style={{
        backgroundColor: "var(--surface)",
        borderRadius: 12,
        border: `1px solid ${badge.border}`,
        padding: 20,
        boxShadow: "0 2px 8px rgba(0,0,0,0.02)",
        transition: "box-shadow 0.2s ease"
      }}
    >
      {/* Top Card Row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: "var(--primary-dark)" }}>
              {scheme.canonical_name || scheme.short_name}
            </h3>
            <span style={{ fontSize: 11, padding: "2px 8px", backgroundColor: "var(--neutral-bg)", borderRadius: 4, color: "var(--text-secondary)", fontWeight: 600 }}>
              {scheme.scheme_code}
            </span>
          </div>
          {scheme.description && (
            <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.4 }}>
              {scheme.description}
            </p>
          )}
        </div>

        <span
          style={{
            padding: "5px 12px",
            borderRadius: 20,
            backgroundColor: badge.bg,
            color: badge.color,
            fontSize: 12,
            fontWeight: 800,
            border: `1px solid ${badge.border}`
          }}
        >
          {badge.text}
        </span>
      </div>

      {/* Explanation Banner */}
      <div
        style={{
          marginTop: 12,
          padding: "10px 12px",
          backgroundColor: "var(--neutral-bg)",
          borderRadius: 8,
          fontSize: 12,
          color: "var(--text-primary)",
          lineHeight: 1.5,
          fontWeight: 500
        }}
      >
        <strong>Eligibility Reason:</strong> {scheme.explanation}
      </div>

      {/* Benefits Summary Pill */}
      {scheme.benefits && scheme.benefits.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-secondary)" }}>Financial Entitlement:</span>
          {scheme.benefits.map((b, idx) => (
            <span
              key={idx}
              style={{
                padding: "3px 10px",
                borderRadius: 6,
                backgroundColor: "#E8F5E9",
                color: "#1B5E20",
                fontSize: 12,
                fontWeight: 700
              }}
            >
              {b.amount ? `₹${b.amount.toLocaleString()} ` : ""}{b.description}
            </span>
          ))}
        </div>
      )}

      {/* Matched Criteria Chips */}
      {scheme.matched_rules && scheme.matched_rules.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "#2E7D32" }}>Matched Criteria:</span>
          {scheme.matched_rules.map((m, idx) => (
            <span
              key={idx}
              style={{
                padding: "2px 8px",
                borderRadius: 4,
                backgroundColor: "#E8F5E9",
                color: "#2E7D32",
                fontSize: 11,
                fontWeight: 600
              }}
            >
              ✓ {m}
            </span>
          ))}
        </div>
      )}

      {/* Failed Rules Chips (if not eligible) */}
      {scheme.failed_rules && scheme.failed_rules.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "#C62828" }}>Unmatched Criteria:</span>
          {scheme.failed_rules.map((f, idx) => (
            <span
              key={idx}
              style={{
                padding: "2px 8px",
                borderRadius: 4,
                backgroundColor: "#FFEBEE",
                color: "#C62828",
                fontSize: 11,
                fontWeight: 600
              }}
            >
              ✕ {f}
            </span>
          ))}
        </div>
      )}

      {/* Missing Information Tag & Action */}
      {isMoreInfo && scheme.missing_fields && scheme.missing_fields.length > 0 && (
        <div
          style={{
            marginTop: 10,
            padding: "10px 12px",
            backgroundColor: "#FFF8E1",
            border: "1px solid #FFE082",
            borderRadius: 8,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 8
          }}
        >
          <div style={{ fontSize: 12, color: "#E65100", fontWeight: 700 }}>
            Missing facts needed: <span style={{ fontWeight: 500 }}>{scheme.missing_fields.join(", ")}</span>
          </div>
          <button
            onClick={onOpenQuestionnaire}
            style={{
              padding: "5px 12px",
              backgroundColor: "#E65100",
              color: "#FFF",
              borderRadius: 6,
              border: "none",
              fontSize: 11,
              fontWeight: 700,
              cursor: "pointer"
            }}
          >
            + Provide Missing Facts
          </button>
        </div>
      )}

      {/* Expanded Accordion: Documents, Application Steps, Help Centres */}
      {expanded && (
        <div
          style={{
            marginTop: 16,
            paddingTop: 14,
            borderTop: "1px solid var(--border)",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 16
          }}
        >
          {/* Required Documents */}
          <div>
            <h4 style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
              📄 Required Documents
            </h4>
            {scheme.required_documents && scheme.required_documents.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                {scheme.required_documents.map((doc, idx) => (
                  <li key={idx}>
                    {doc.name} {doc.conditional ? "(if applicable)" : ""}
                  </li>
                ))}
              </ul>
            ) : (
              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Aadhaar / Standard identity documents</span>
            )}
          </div>

          {/* Application Steps */}
          <div>
            <h4 style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
              📋 Application & Access Steps
            </h4>
            {scheme.application_steps && scheme.application_steps.length > 0 ? (
              <ol style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                {scheme.application_steps.map((step, idx) => (
                  <li key={idx}>{step}</li>
                ))}
              </ol>
            ) : (
              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Visit local PHC / Sub-Centre or contact ASHA worker.</span>
            )}
          </div>

          {/* Help Centres & Official Verification */}
          <div>
            <h4 style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
              🏥 Assistance Help Centres
            </h4>
            {scheme.help_centers && scheme.help_centers.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6 }}>
                {scheme.help_centers.map((hc, idx) => (
                  <li key={idx}>{hc}</li>
                ))}
              </ul>
            ) : (
              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Primary Health Centre / Anganwadi Centre</span>
            )}
          </div>
        </div>
      )}

      {/* Action Buttons Footer */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14, flexWrap: "wrap", gap: 10 }}>
        <div style={{ display: "flex", gap: 10 }}>
          {isEligibleOrService && (
            <button
              onClick={onSendSms}
              style={{
                padding: "7px 14px",
                backgroundColor: "var(--primary)",
                color: "#FFF",
                borderRadius: 6,
                border: "none",
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 6
              }}
            >
              📱 Send Scheme Guidance SMS
            </button>
          )}

          {scheme.official_application_url ? (
            <a
              href={scheme.official_application_url}
              target="_blank"
              rel="noreferrer"
              style={{
                padding: "7px 12px",
                backgroundColor: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                color: "var(--primary-dark)",
                fontSize: 12,
                fontWeight: 700,
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: 4
              }}
            >
              Check Official Portal ↗
            </a>
          ) : scheme.official_information_url ? (
            <a
              href={scheme.official_information_url}
              target="_blank"
              rel="noreferrer"
              style={{
                padding: "7px 12px",
                backgroundColor: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                color: "var(--text-primary)",
                fontSize: 12,
                fontWeight: 600,
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: 4
              }}
            >
              Official Guidelines ↗
            </a>
          ) : null}
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            border: "none",
            backgroundColor: "transparent",
            color: "var(--primary)",
            fontSize: 12,
            fontWeight: 700,
            cursor: "pointer"
          }}
        >
          {expanded ? "▲ Less Details" : "▼ Documents & Application Steps"}
        </button>
      </div>
    </div>
  );
}
