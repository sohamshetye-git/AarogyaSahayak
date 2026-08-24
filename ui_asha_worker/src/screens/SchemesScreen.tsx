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

  const filtered = SCHEMES.filter((s) => {
    const q = search.toLowerCase();
    const matchSearch = !q || s.name.toLowerCase().includes(q) || s.why.toLowerCase().includes(q);
    const matchCategory = !activeCategory || s.category === activeCategory;
    return matchSearch && matchCategory;
  });

  return (
    <div style={{ padding: "16px 16px 24px" }}>
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
        <button
          style={{
            position: "absolute",
            right: 10,
            top: "50%",
            transform: "translateY(-50%)",
            width: 36,
            height: 36,
            borderRadius: 8,
            border: "none",
            backgroundColor: "var(--primary-light)",
            color: "var(--primary)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          aria-label="Voice search"
        >
          <MicIcon size={18} />
        </button>
      </div>

      {/* Category filters */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          Categories
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {CATEGORIES.map(({ key, label, count }) => (
            <button
              key={key}
              onClick={() => setActiveCategory(activeCategory === key ? null : key)}
              style={{
                padding: "10px 12px",
                borderRadius: 10,
                border: `1.5px solid ${activeCategory === key ? "var(--primary)" : "var(--border)"}`,
                backgroundColor: activeCategory === key ? "var(--primary-light)" : "var(--surface)",
                color: activeCategory === key ? "var(--primary)" : "var(--text-primary)",
                cursor: "pointer",
                textAlign: "left",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 8,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <SchemeIcon size={14} style={{ color: activeCategory === key ? "var(--primary)" : "var(--text-disabled)" }} />
                <span style={{ fontSize: 12, fontWeight: 600, lineHeight: "16px" }}>{label}</span>
              </div>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: activeCategory === key ? "var(--primary)" : "var(--text-disabled)",
                  backgroundColor: activeCategory === key ? "var(--primary)" : "var(--neutral-bg)",
                  padding: "2px 6px",
                  borderRadius: 10,
                  color: activeCategory === key ? "white" : "var(--text-disabled)",
                }}
              >
                {count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Schemes */}
      {filtered.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px 16px", color: "var(--text-secondary)" }}>
          <SchemeIcon size={40} style={{ color: "var(--border-strong)", marginBottom: 12 }} />
          <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 8 }}>No schemes found</div>
          <div style={{ fontSize: 14 }}>Scheme information is temporarily unavailable.</div>
        </div>
      ) : (
        filtered.map((scheme) => (
          <SchemeCard key={scheme.name} scheme={scheme} onExpand={() => {}} />
        ))
      )}
    </div>
  );
}
