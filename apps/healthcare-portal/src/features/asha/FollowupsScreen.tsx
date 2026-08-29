import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge } from "../../components/StatusBadge";
import { SearchIcon, ActivityIcon, WarningIcon, CheckCircleIcon } from "../../components/Icons";
import { ashaSyncService } from "../../services/AshaSyncService";
import { useLanguage } from "@aarogya/i18n";

interface FollowUpItem {
  id: string;
  follow_up_id?: string;
  case_id: string;
  case_reference: string;
  citizen_id: string;
  citizen_name: string;
  citizen_phone?: string;
  age?: number;
  gender?: string;
  is_pregnant?: boolean;
  village_name: string;
  task_type: string;
  instructions: string;
  priority: string;
  due_at: string;
  source: string;
  doctor_name?: string;
  facility_name?: string;
  status: string;
  result?: string;
  sync_status?: string;
  completed_at?: string;
  scheduled_reason?: string;
}

export function AshaFollowupsScreen() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { t } = useLanguage();

  const initialFilter = searchParams.get("filter") || "ALL";
  const initialSearch = searchParams.get("q") || "";

  const [followups, setFollowups] = useState<FollowUpItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<string>(initialFilter);
  const [search, setSearch] = useState<string>(initialSearch);
  const [pendingSyncCount, setPendingSyncCount] = useState(0);

  const loadFollowups = async () => {
    try {
      const res = await apiClient.getAshaFollowups();
      const items = res?.data || res || [];
      setFollowups(Array.isArray(items) ? items : []);

      // Check Dexie offline sync queue for follow-ups
      try {
        const queue = await ashaSyncService.getQueue();
        const fupSyncs = queue.filter(
          (item: any) =>
            item.action_type === "UPDATE_FOLLOWUP" ||
            item.action_type === "CREATE_FOLLOWUP" ||
            item.action_type === "RESCHEDULE_FOLLOWUP" ||
            item.action_type === "ESCALATE_FOLLOWUP"
        );
        setPendingSyncCount(fupSyncs.length);
      } catch (dexieErr) {
        console.warn("Could not check offline queue", dexieErr);
      }
    } catch (err) {
      console.error("Failed to load followups", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFollowups();
    const interval = setInterval(loadFollowups, 6000);
    return () => clearInterval(interval);
  }, []);

  const now = new Date();
  const todayDateStr = now.toISOString().split("T")[0];

  // Helper for computing dynamic states
  const getFollowupCategory = (f: FollowUpItem) => {
    const isPending = f.status === "PENDING" || f.status === "IN_PROGRESS" || f.status === "SCHEDULED";
    const dueDateStr = f.due_at ? new Date(f.due_at).toISOString().split("T")[0] : "";
    const isOverdue = isPending && Boolean(f.due_at) && (new Date(f.due_at).getTime() < now.getTime() || dueDateStr < todayDateStr);
    const isToday = isPending && dueDateStr === todayDateStr && !isOverdue;
    const isUpcoming = isPending && Boolean(f.due_at) && dueDateStr > todayDateStr;
    const isAsha = f.source === "ASHA_SCHEDULED" || f.source === "ASHA";
    const isDoctor = f.source === "DOCTOR_DIRECTIVE" || f.source === "DOCTOR" || f.source === "DOCTOR_ASSIGNED";
    const isEscalated = f.status === "ESCALATED";
    const isCompleted = f.status === "COMPLETED";

    return { isPending, isOverdue, isToday, isUpcoming, isAsha, isDoctor, isEscalated, isCompleted };
  };

  // Filter tabs definition
  const filterTabs = [
    { id: "ALL", label: t("followups.filter_all", "All") },
    { id: "OVERDUE", label: `⏱ ${t("followups.filter_overdue", "Overdue")}` },
    { id: "DUE_TODAY", label: `📅 ${t("followups.filter_due_today", "Due Today")}` },
    { id: "ASHA_SCHEDULED", label: `🏠 ${t("followups.filter_asha", "ASHA Scheduled")}` },
    { id: "DOCTOR_DIRECTIVES", label: `👩‍⚕️ ${t("followups.filter_doctor", "Doctor Directives")}` },
    { id: "UPCOMING", label: `📋 ${t("followups.filter_upcoming", "Upcoming")}` },
    { id: "ESCALATED", label: `⚠️ ${t("followups.filter_escalated", "Escalated")}` },
    { id: "COMPLETED", label: `✓ ${t("followups.filter_completed", "Completed")}` },
    { id: "PENDING_SYNC", label: `🔄 ${t("followups.filter_pending_sync", "Pending Sync")}${pendingSyncCount > 0 ? ` (${pendingSyncCount})` : ""}` },
  ];

  const filteredFollowups = followups.filter((f) => {
    const cat = getFollowupCategory(f);

    if (activeTab === "OVERDUE" && !cat.isOverdue) return false;
    if (activeTab === "DUE_TODAY" && !cat.isToday) return false;
    if (activeTab === "ASHA_SCHEDULED" && !cat.isAsha) return false;
    if (activeTab === "DOCTOR_DIRECTIVES" && !cat.isDoctor) return false;
    if (activeTab === "UPCOMING" && !cat.isUpcoming) return false;
    if (activeTab === "ESCALATED" && !cat.isEscalated) return false;
    if (activeTab === "COMPLETED" && !cat.isCompleted) return false;
    if (activeTab === "PENDING_SYNC" && f.sync_status !== "PENDING_SYNC" && f.sync_status !== "QUEUED") {
      if (pendingSyncCount === 0) return false;
    }

    if (search.trim()) {
      const s = search.toLowerCase().trim();
      const nameMatch = f.citizen_name?.toLowerCase().includes(s);
      const caseMatch = f.case_reference?.toLowerCase().includes(s);
      const villageMatch = f.village_name?.toLowerCase().includes(s);
      const reasonMatch = (f.instructions || f.scheduled_reason || f.task_type)?.toLowerCase().includes(s);
      const docMatch = f.doctor_name?.toLowerCase().includes(s);
      if (!nameMatch && !caseMatch && !villageMatch && !reasonMatch && !docMatch) {
        return false;
      }
    }
    return true;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Top Header */}
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h2 style={{ margin: "0 0 8px", fontSize: 22, fontWeight: 700 }}>
              {t("followups.title", "Follow-ups")}
            </h2>
            <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
              {t("followups.subtitle", "Conduct home checkups, record follow-up vitals, verify medication adherence, and escalate high-risk cases to PHC Medical Officers.")}
            </p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            {pendingSyncCount > 0 && (
              <span
                style={{
                  padding: "6px 12px",
                  borderRadius: 20,
                  backgroundColor: "#FEF3C7",
                  color: "#92400E",
                  fontSize: 12,
                  fontWeight: 700,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                🔄 {pendingSyncCount} offline update(s) pending sync
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <div
          style={{
            flex: 1,
            minWidth: 280,
            display: "flex",
            alignItems: "center",
            gap: 10,
            backgroundColor: "var(--surface)",
            padding: "0 14px",
            height: 44,
            borderRadius: 8,
            border: "1px solid var(--border)",
          }}
        >
          <SearchIcon size={18} color="var(--text-secondary)" />
          <input
            id="followup-search-input"
            type="text"
            placeholder={t("followups.search_placeholder", "Search citizen name, case ref, village, doctor...")}
            value={search}
            onChange={(e) => {
              const val = e.target.value;
              setSearch(val);
              setSearchParams({ filter: activeTab, ...(val ? { q: val } : {}) });
            }}
            style={{ border: "none", outline: "none", width: "100%", fontSize: 14, backgroundColor: "transparent" }}
          />
        </div>

        <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 4, maxWidth: "100%" }}>
          {filterTabs.map((tab) => {
            const isSelected = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`filter-tab-${tab.id.toLowerCase()}`}
                onClick={() => {
                  setActiveTab(tab.id);
                  setSearchParams({ filter: tab.id, ...(search ? { q: search } : {}) });
                }}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  border: isSelected ? "2px solid var(--primary)" : "1px solid var(--border)",
                  backgroundColor: isSelected ? "var(--primary-light)" : "var(--surface)",
                  color: isSelected ? "var(--primary-dark)" : "var(--text-primary)",
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  minHeight: 40,
                  transition: "all 0.15s ease-in-out",
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Follow-up List */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: 40, color: "var(--text-secondary)" }}>
            {t("common.loading", "Loading follow-ups...")}
          </div>
        ) : filteredFollowups.length === 0 ? (
          <div style={{ textAlign: "center", padding: 40, backgroundColor: "var(--surface)", borderRadius: 12, border: "1px solid var(--border)" }}>
            <p style={{ margin: "0 0 8px", fontSize: 16, fontWeight: 600 }}>
              {t("followups.no_items", "No follow-up assignments found")}
            </p>
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>
              {t("followups.no_items_desc", "There are no follow-up tasks matching the current filter and search criteria.")}
            </p>
          </div>
        ) : (
          filteredFollowups.map((fup) => {
            const cat = getFollowupCategory(fup);
            const isDoctor = cat.isDoctor;
            const targetId = fup.follow_up_id || fup.id;
            const canonicalCaseId = fup.case_id;

            // Clean doctor name display
            const rawDoc = fup.doctor_name || "";
            const cleanDoc = rawDoc.startsWith("Dr.") ? rawDoc : rawDoc ? `Dr. ${rawDoc}` : "";

            return (
              <div
                key={targetId}
                data-testid={`followup-card-${targetId}`}
                style={{
                  backgroundColor: "var(--surface)",
                  padding: 20,
                  borderRadius: 12,
                  border: cat.isEscalated
                    ? "1px solid #FECACA"
                    : cat.isCompleted
                    ? "1px solid #C6F6D5"
                    : cat.isOverdue
                    ? "1px solid #FED7AA"
                    : "1px solid var(--border)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
                      <span style={{ fontSize: 16, fontWeight: 700 }}>{fup.citizen_name}</span>
                      {fup.age && <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>({fup.age}y {fup.gender || ""})</span>}
                      {fup.is_pregnant && (
                        <span style={{ padding: "2px 8px", borderRadius: 12, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                          🤰 Pregnant
                        </span>
                      )}
                      <PriorityBadge priority={fup.priority} size="sm" />

                      {/* Source Badge */}
                      <span
                        style={{
                          padding: "3px 8px",
                          borderRadius: 6,
                          fontSize: 11,
                          fontWeight: 700,
                          backgroundColor: isDoctor ? "#EEF2FF" : "#F0FDF4",
                          color: isDoctor ? "#4338CA" : "#15803D",
                          border: isDoctor ? "1px solid #C7D2FE" : "1px solid #BBF7D0",
                        }}
                      >
                        {isDoctor ? "👩‍⚕️ Doctor Directive" : "🏠 ASHA Scheduled"}
                      </span>

                      {/* Status Tag */}
                      <span
                        style={{
                          padding: "3px 8px",
                          borderRadius: 6,
                          fontSize: 11,
                          fontWeight: 700,
                          backgroundColor:
                            cat.isEscalated ? "#FEE2E2" :
                            cat.isCompleted ? "#DEF7EC" :
                            cat.isOverdue ? "#FEE2E2" :
                            cat.isToday ? "#FEF3C7" :
                            "#F3F4F6",
                          color:
                            cat.isEscalated ? "#991B1B" :
                            cat.isCompleted ? "#03543F" :
                            cat.isOverdue ? "#991B1B" :
                            cat.isToday ? "#92400E" :
                            "#374151",
                        }}
                      >
                        {cat.isEscalated ? "⚠️ ESCALATED" :
                         cat.isCompleted ? "✓ COMPLETED" :
                         cat.isOverdue ? "⏱ OVERDUE" :
                         cat.isToday ? "📅 DUE TODAY" :
                         fup.status}
                      </span>
                    </div>

                    <div style={{ fontSize: 13, color: "var(--text-secondary)", display: "flex", gap: 12, flexWrap: "wrap" }}>
                      <span>Case: <strong>{fup.case_reference}</strong></span>
                      <span>Village: <strong>{fup.village_name}</strong></span>
                      <span>Due: <strong>{fup.due_at ? new Date(fup.due_at).toLocaleDateString() : "Not set"}</strong></span>
                      {cleanDoc && <span>Doctor: <strong>{cleanDoc}</strong></span>}
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                    <button
                      id={`btn-view-timeline-${targetId}`}
                      onClick={() => navigate(`/asha/cases/${encodeURIComponent(canonicalCaseId)}?tab=timeline&returnTo=${encodeURIComponent(`/asha/followups?filter=${activeTab}${search ? `&q=${encodeURIComponent(search)}` : ""}`)}`)}
                      style={{
                        padding: "10px 16px",
                        backgroundColor: "var(--neutral-bg)",
                        color: "var(--text-primary)",
                        border: "1px solid var(--border)",
                        borderRadius: 8,
                        fontSize: 13,
                        fontWeight: 700,
                        cursor: "pointer",
                        minHeight: 44,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      <span>🕒 {t("followups.view_timeline", "View Timeline")}</span>
                    </button>
                    {!cat.isCompleted && (
                      <button
                        id={`btn-open-followup-${targetId}`}
                        onClick={() => navigate(`/asha/followups/${encodeURIComponent(targetId)}`)}
                        style={{
                          padding: "10px 18px",
                          backgroundColor: "var(--primary)",
                          color: "#FFF",
                          border: "none",
                          borderRadius: 8,
                          fontSize: 13,
                          fontWeight: 700,
                          cursor: "pointer",
                          minHeight: 44,
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          boxShadow: "0 2px 6px rgba(37,99,235,0.2)",
                        }}
                      >
                        <span>→ {t("followups.open_followup", "Open Follow-up")}</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Instructions / Context */}
                <div style={{ padding: 12, backgroundColor: "var(--neutral-bg)", borderRadius: 8, fontSize: 13, color: "var(--text-primary)" }}>
                  <strong>Directive & Instructions:</strong> {fup.instructions || fup.scheduled_reason || "Verify general recovery, adherence and vital signs."}
                </div>

                {/* Result or Completed Note */}
                {fup.result && (
                  <div style={{ fontSize: 12, color: "var(--success)", fontWeight: 600 }}>
                    Outcome: {fup.result} {fup.completed_at && `(Completed on ${new Date(fup.completed_at).toLocaleDateString()})`}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}