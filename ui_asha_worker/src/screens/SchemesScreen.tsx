import React, { useState } from "react";
import { SearchIcon, MicIcon, SchemeIcon, ChevronRightIcon, CheckIcon, InfoIcon } from "../components/Icons";

const CATEGORIES = [
  { key: "pregnancy", label: "Pregnancy & mother care", count: 5 },
  { key: "treatment", label: "Treatment support", count: 8 },
  { key: "child", label: "Child health", count: 4 },
  { key: "senior", label: "Senior citizen health", count: 3 },
  { key: "disability", label: "Disability support", count: 2 },
  { key: "insurance", label: "Health insurance", count: 6 },
];

const SCHEMES = [
  {
    name: "Janani Suraksha Yojana",
    shortName: "JSY",
    category: "pregnancy",
    status: "potentially-relevant",
    why: "Citizen is pregnant and below poverty line – this scheme supports institutional delivery.",
    eligibility: ["Pregnant women · BPL", "Age 19+ for first 2 children", "Institutional delivery required"],
    documents: ["Identity proof (Aadhaar)", "Pregnancy health card", "BPL card or income certificate", "Bank account details"],
    steps: ["Register at local ANM", "Receive JSY card", "Deliver at empanelled facility", "Receive benefit post-delivery"],
    source: "nhm.gov.in",
    lastVerified: "July 2025",
    color: "var(--teal)",
    bg: "var(--teal-light)",
  },
  {
    name: "Pradhan Mantri Matru Vandana Yojana",
    shortName: "PMMVY",
    category: "pregnancy",
    status: "potentially-relevant",
    why: "First pregnancy support scheme – citizen is pregnant for the first time.",
    eligibility: ["Pregnant and lactating women", "First living child only", "Registered in local AWC"],
    documents: ["MCP card", "Bank account (joint or individual)", "Aadhaar card"],
    steps: ["Apply at AWC/health centre", "Submit required documents", "Receive ₹5,000 in 3 instalments"],
    source: "pmmvy.nic.in",
    lastVerified: "June 2025",
    color: "var(--primary)",
    bg: "var(--primary-light)",
  },
  {
    name: "Ayushman Bharat – PMJAY",
    shortName: "PMJAY",
    category: "insurance",
    status: "check-eligibility",
    why: "Provides up to ₹5 lakh health cover per family per year.",
    eligibility: ["SECC database listed families", "No existing government health insurance"],
    documents: ["Aadhaar card", "Ration card or SECC letter"],
    steps: ["Check eligibility on mera.pmjay.gov.in", "Obtain e-card from nearest CSC", "Use at empanelled hospitals"],
    source: "pmjay.gov.in",
    lastVerified: "August 2025",
    color: "var(--high)",
    bg: "var(--high-bg)",
  },
];

function SchemeCard({ scheme, onExpand }: { scheme: typeof SCHEMES[0]; onExpand: () => void }) {
  return (
    <div
      style={{
        backgroundColor: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 14,
        padding: "14px",
        marginBottom: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 10 }}>
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 10,
            backgroundColor: scheme.bg,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: scheme.color,
            flexShrink: 0,
            fontWeight: 700,
            fontSize: 11,
          }}
        >
          {scheme.shortName.slice(0, 3)}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)", lineHeight: "21px" }}>
            {scheme.name}
          </div>
          <span
            style={{
              display: "inline-block",
              marginTop: 4,
              padding: "3px 8px",
              backgroundColor: "var(--followup-bg)",
              color: "var(--followup)",
              borderRadius: 5,
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            Potentially relevant
          </span>
        </div>
      </div>

      <div
        style={{
          padding: "10px 12px",
          backgroundColor: "var(--bg)",
          borderRadius: 8,
          fontSize: 13,
          color: "var(--text-primary)",
          lineHeight: "19px",
          marginBottom: 10,
        }}
      >
        <span style={{ fontWeight: 600, color: "var(--text-secondary)" }}>Why it may help: </span>
        {scheme.why}
      </div>

      <div style={{ marginBottom: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-disabled)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.4px" }}>
          Basic eligibility
        </div>
        {scheme.eligibility.map((e, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, fontSize: 13, color: "var(--text-primary)" }}>
            <div style={{ width: 5, height: 5, borderRadius: "50%", backgroundColor: scheme.color, flexShrink: 0 }} />
            {e}
          </div>
        ))}
      </div>

      <div
        style={{
          padding: "8px 10px",
          backgroundColor: "var(--followup-bg)",
          borderRadius: 8,
          fontSize: 12,
          color: "var(--followup)",
          fontWeight: 500,
          marginBottom: 12,
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <InfoIcon size={14} />
        Final eligibility verification pending
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={onExpand}
          style={{
            flex: 1,
            height: 40,
            backgroundColor: "var(--primary)",
            color: "white",
            border: "none",
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
          Check eligibility
          <ChevronRightIcon size={14} />
        </button>
        <button
          style={{
            height: 40,
            padding: "0 12px",
            backgroundColor: "var(--teal-light)",
            color: "var(--teal)",
            border: "none",
            borderRadius: 8,
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Explain to citizen
        </button>
      </div>

      <div style={{ marginTop: 8, fontSize: 11, color: "var(--text-disabled)" }}>
        Source: {scheme.source} · Last verified: {scheme.lastVerified}
      </div>
    </div>
  );
}

export default function SchemesScreen() {
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"schemes" | "assistance">("assistance");
  const [assistanceTasks, setAssistanceTasks] = useState<any[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(false);
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [officialRefInput, setOfficialRefInput] = useState("");
  const [outcomeNotes, setOutcomeNotes] = useState("");
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchAssistanceTasks = async () => {
    setLoadingTasks(true);
    try {
      const res = await fetch("http://localhost:8000/api/asha/scheme-assistance-tasks", {
        headers: { "Authorization": "Bearer mock-token-asha" }
      });
      if (res.ok) {
        const json = await res.json();
        setAssistanceTasks(json?.data || []);
      }
    } catch (err) {
      console.error("Failed to load assistance tasks", err);
    } finally {
      setLoadingTasks(false);
    }
  };

  useEffect(() => {
    fetchAssistanceTasks();
  }, []);

  const handleCompleteAssistance = async (taskId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/asha/scheme-assistance-tasks/${taskId}/outcome`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer mock-token-asha" },
        body: JSON.stringify({
          status: "COMPLETED",
          outcome_summary: outcomeNotes || "ASHA assisted citizen with scheme document verification and portal submission.",
          official_reference_recorded: officialRefInput || "PMMVY-MH-2026-88992"
        })
      });
      if (res.ok) {
        setActionMessage("शासकीय योजना सहाय्य यशस्वीपणे नोंदवले गेले! (Assistance recorded successfully)");
        setSelectedTask(null);
        fetchAssistanceTasks();
        setTimeout(() => setActionMessage(null), 2500);
      }
    } catch (err) {
      console.error("Failed to update task", err);
    }
  };

  const filtered = SCHEMES.filter((s) => {
    const q = search.toLowerCase();
    const matchSearch = !q || s.name.toLowerCase().includes(q) || s.why.toLowerCase().includes(q);
    const matchCategory = !activeCategory || s.category === activeCategory;
    return matchSearch && matchCategory;
  });

  return (
    <div style={{ padding: "16px 16px 24px" }}>
      {actionMessage && (
        <div style={{ backgroundColor: "#166534", color: "#FFFFFF", padding: "12px 16px", borderRadius: 10, marginBottom: 16, fontSize: 13, fontWeight: 700 }}>
          {actionMessage}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button
          onClick={() => setActiveTab("assistance")}
          style={{
            flex: 1,
            padding: "10px",
            borderRadius: 10,
            border: "none",
            backgroundColor: activeTab === "assistance" ? "var(--primary)" : "var(--surface)",
            color: activeTab === "assistance" ? "#FFFFFF" : "var(--text-primary)",
            fontWeight: 700,
            fontSize: 13,
            cursor: "pointer"
          }}
        >
          नागरिक सहाय्य विनंत्या ({assistanceTasks.length})
        </button>
        <button
          onClick={() => setActiveTab("schemes")}
          style={{
            flex: 1,
            padding: "10px",
            borderRadius: 10,
            border: "none",
            backgroundColor: activeTab === "schemes" ? "var(--primary)" : "var(--surface)",
            color: activeTab === "schemes" ? "#FFFFFF" : "var(--text-primary)",
            fontWeight: 700,
            fontSize: 13,
            cursor: "pointer"
          }}
        >
          शासकीय योजना मार्गदर्शिका
        </button>
      </div>

      {activeTab === "assistance" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {assistanceTasks.length === 0 ? (
            <div style={{ textAlign: "center", padding: 40, backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>कोणतीही प्रलंबित योजना विनंती नाही</div>
            </div>
          ) : (
            assistanceTasks.map((task, idx) => (
              <div
                key={idx}
                style={{
                  backgroundColor: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 14,
                  padding: "16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 8
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)" }}>
                      {task.citizen_name} - {task.scheme_name}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                      संदर्भ: {task.request_reference}
                    </div>
                  </div>
                  <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 8px", borderRadius: 6, backgroundColor: task.status === "COMPLETED" ? "#DCFCE7" : "#FEF3C7", color: task.status === "COMPLETED" ? "#166534" : "#92400E" }}>
                    {task.status}
                  </span>
                </div>

                <div style={{ fontSize: 13, color: "var(--text-primary)" }}>
                  <strong>आवश्यक मदत:</strong> {task.notes || "कागदपत्रांची तपासणी व अर्ज मार्गदर्शन."}
                </div>

                {task.status !== "COMPLETED" && (
                  <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 8, backgroundColor: "#F8FAFC", padding: 12, borderRadius: 10 }}>
                    <div style={{ fontSize: 12, fontWeight: 700 }}>आशा कार्यवाही (Record Action):</div>
                    <input
                      type="text"
                      placeholder="अधिकृत अर्ज संदर्भ क्र. (उदा. PMMVY-MH-2026-9812)"
                      value={officialRefInput}
                      onChange={(e) => setOfficialRefInput(e.target.value)}
                      style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
                    />
                    <input
                      type="text"
                      placeholder="तपासणी नोंदी (उदा. सर्व कागदपत्रे तपासली, अर्ज सबमिट केला)"
                      value={outcomeNotes}
                      onChange={(e) => setOutcomeNotes(e.target.value)}
                      style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
                    />
                    <button
                      onClick={() => handleCompleteAssistance(task.id)}
                      style={{
                        backgroundColor: "var(--primary)",
                        color: "#FFFFFF",
                        border: "none",
                        borderRadius: 8,
                        padding: "10px",
                        fontSize: 13,
                        fontWeight: 700,
                        cursor: "pointer"
                      }}
                    >
                      सहाय्य पूर्ण नोंदवा (Complete Assistance)
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      ) : (
        <div>
          {/* Search with voice */}
          <div style={{ position: "relative", marginBottom: 16 }}>
            <SearchIcon
              size={18}
              style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: "var(--text-disabled)" }}
            />
            <input
              type="search"
              placeholder="Ask about a health scheme"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: "100%",
                height: 48,
                paddingLeft: 44,
                paddingRight: 56,
                border: "1.5px solid var(--border)",
                borderRadius: 12,
                fontSize: 15,
                color: "var(--text-primary)",
                backgroundColor: "var(--surface)",
                outline: "none",
                boxSizing: "border-box",
              }}
              aria-label="Search health schemes"
            />
          </div>
          {filtered.map((s, idx) => (
            <SchemeCard key={idx} scheme={s} onExpand={() => {}} />
          ))}
        </div>
      )}
    </div>
  );
}

