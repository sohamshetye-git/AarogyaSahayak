import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { apiClient as api } from "@aarogya/api-client";
import { InvestigationCard } from "./components/InvestigationCard";
import { OrderBuilderModal } from "./components/OrderBuilderModal";
import { SampleRecordModal } from "./components/SampleRecordModal";
import { ResultEntryModal } from "./components/ResultEntryModal";
import { RequestRecollectionModal } from "./components/RequestRecollectionModal";
import { useLanguage } from "../../context/LanguageContext";

export const DoctorInvestigationsScreen: React.FC = () => {
  const { t } = useLanguage();
  const [searchParams, setSearchParams] = useSearchParams();


  const currentStatusFilter = searchParams.get("status") || "ALL_ACTIVE";
  const currentCategory = searchParams.get("category") || "";
  const currentPriority = searchParams.get("priority") || "";
  const currentSortBy = searchParams.get("sort_by") || "critical_first";
  const currentSearch = searchParams.get("search") || "";
  const currentPage = parseInt(searchParams.get("page") || "1", 10);

  const [summary, setSummary] = useState<any>({
    total_ordered_today: 0,
    sample_pending: 0,
    sample_collected: 0,
    results_ready: 0,
    urgent_critical_results: 0,
    awaiting_doctor_review: 0,
    reviewed_today: 0,
    recollection_required: 0,
  });

  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastSyncedTime, setLastSyncedTime] = useState<string>(new Date().toLocaleTimeString("en-IN"));

  // Modals
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);
  const [selectedOrderForSample, setSelectedOrderForSample] = useState<any | null>(null);
  const [selectedOrderForResult, setSelectedOrderForResult] = useState<any | null>(null);
  const [selectedOrderForRecollection, setSelectedOrderForRecollection] = useState<any | null>(null);

  // Review modal inline note prompt
  const [reviewingOrder, setReviewingOrder] = useState<any | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [reviewOutcome, setReviewOutcome] = useState("NO_CHANGE");
  const [updateCarePlan, setUpdateCarePlan] = useState(false);
  const [createFollowup, setCreateFollowup] = useState(false);
  const [followupInstructions, setFollowupInstructions] = useState("");
  const [reviewSubmitting, setReviewSubmitting] = useState(false);

  const updateFilters = (updates: Record<string, string | number | null>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, val]) => {
      if (val === null || val === "" || val === undefined) {
        newParams.delete(key);
      } else {
        newParams.set(key, String(val));
      }
    });
    setSearchParams(newParams);
  };

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, listRes] = await Promise.all([
        api.getDoctorInvestigationsSummary().catch(() => null),
        api.getDoctorInvestigations({
          status_filter: currentStatusFilter,
          category: currentCategory || undefined,
          priority: currentPriority || undefined,
          search: currentSearch || undefined,
          sort_by: currentSortBy,
          page: currentPage,
          limit: 50,
        }),
      ]);

      if (sumRes) setSummary(sumRes);

      // Handle direct array or pagination wrapper
      const listData = Array.isArray(listRes) ? listRes : listRes?.items || [];
      setItems(listData);
      setLastSyncedTime(new Date().toLocaleTimeString("en-IN"));
    } catch (err: any) {
      setError(err.message || "Failed to load investigations data.");
    } finally {
      setLoading(false);
    }
  }, [currentStatusFilter, currentCategory, currentPriority, currentSortBy, currentSearch, currentPage]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Modal Submit Actions
  const handleCreateOrder = async (orderData: any) => {
    await api.createInvestigationOrder(orderData);
    fetchData();
  };

  const handleRecordSampleSubmit = async (orderId: string, sampleData: any) => {
    await api.recordSampleCollection(orderId, sampleData);
    fetchData();
  };

  const handleResultEntrySubmit = async (orderId: string, resultData: any) => {
    await api.enterInvestigationResult(orderId, resultData);
    fetchData();
  };

  const handleAcknowledgeCritical = async (order: any) => {
    try {
      const invId = order.investigation_id || order.id;
      await api.acknowledgeInvestigationCritical(invId, { notes: "Doctor acknowledged critical result alert." });
      fetchData();
    } catch (err: any) {
      console.error("Failed to acknowledge critical result:", err);
    }
  };

  const handleRequestRecollection = (order: any) => {
    setSelectedOrderForRecollection(order);
  };

  const handleOpenReviewModal = (order: any) => {
    setReviewingOrder(order);
    setReviewNote("Result reviewed. No acute abnormalities observed.");
    setReviewOutcome("NO_CHANGE");
    setUpdateCarePlan(false);
    setCreateFollowup(false);
    setFollowupInstructions("");
  };

  const handleConfirmReview = async () => {
    if (!reviewingOrder) return;
    setReviewSubmitting(true);
    try {
      await api.reviewInvestigationResult(reviewingOrder.id, {
        review_note: reviewNote,
        outcome: reviewOutcome,
        update_care_plan: updateCarePlan,
        create_followup: createFollowup,
        followup_instructions: followupInstructions || undefined,
      });
      setReviewingOrder(null);
      fetchData();
    } catch (err: any) {
      alert(err.message || "Failed to submit doctor review.");
    } finally {
      setReviewSubmitting(false);
    }
  };

  return (
    <div style={{ padding: "1.5rem", maxWidth: "1400px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Workspace Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.75rem", fontWeight: 800, color: "var(--text-primary, #0f172a)" }}>
            {t("doctor.investigations_workspace_title", "Investigations Workspace")}
          </h1>
          <div style={{ fontSize: "0.85rem", color: "var(--text-secondary, #64748b)", marginTop: "0.2rem" }}>
            Kalyanpur Primary Health Center • {t("doctor.last_synced_at", "Last synced at {{time}}", { time: lastSyncedTime })}
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button
            onClick={fetchData}
            style={{
              padding: "0.5rem 1rem",
              borderRadius: "8px",
              border: "1px solid var(--border, #cbd5e1)",
              background: "var(--card-bg, #ffffff)",
              fontWeight: 600,
              fontSize: "0.85rem",
              cursor: "pointer",
            }}
          >
            ↻ {t("common.refresh", "Refresh")}
          </button>

          <button
            onClick={() => setIsOrderModalOpen(true)}
            style={{
              padding: "0.5rem 1.25rem",
              borderRadius: "8px",
              border: "none",
              background: "#0284c7",
              color: "#ffffff",
              fontWeight: 700,
              fontSize: "0.85rem",
              cursor: "pointer",
              boxShadow: "0 2px 4px rgba(2, 132, 199, 0.2)",
            }}
          >
            {t("doctor.new_investigation_order", "+ New Investigation Order")}
          </button>
        </div>
      </div>

      {/* Dynamic Interactive Metrics Bar */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: "0.75rem",
        }}
      >
        {[
          { label: t("doctor.ordered_today_metric", "Ordered Today"), count: summary.total_ordered_today, status: "ALL_ACTIVE", color: "#0284c7" },
          { label: t("doctor.sample_pending_metric", "Sample Pending"), count: summary.sample_pending, status: "SAMPLE_PENDING", color: "#7c3aed" },
          { label: t("doctor.sample_collected_metric", "Sample Collected"), count: summary.sample_collected, status: "SAMPLE_COLLECTED", color: "#6366f1" },
          { label: t("doctor.results_ready_metric", "Results Ready"), count: summary.results_ready, status: "RESULT_AVAILABLE", color: "#2563eb" },
          { label: t("doctor.urgent_critical_metric", "Urgent/Critical"), count: summary.urgent_critical_results, status: "CRITICAL", color: "#dc2626" },
          { label: t("doctor.awaiting_review_metric", "Awaiting Review"), count: summary.awaiting_doctor_review, status: "REVIEW_REQUIRED", color: "#d97706" },
          { label: t("doctor.reviewed_today_metric", "Reviewed Today"), count: summary.reviewed_today, status: "REVIEWED", color: "#16a34a" },
          { label: t("doctor.recollection_metric", "Recollection"), count: summary.recollection_required, status: "RECOLLECTION_REQUIRED", color: "#ea580c" },
        ].map((m) => {
          const isSelected = currentStatusFilter === m.status;
          return (
            <button
              key={m.label}
              onClick={() => updateFilters({ status: m.status, page: 1 })}
              style={{
                background: isSelected ? m.color : "var(--card-bg, #ffffff)",
                color: isSelected ? "#ffffff" : "var(--text-primary, #0f172a)",
                border: isSelected ? `2px solid ${m.color}` : "1px solid var(--border, #e2e8f0)",
                borderRadius: "10px",
                padding: "0.85rem 0.75rem",
                textAlign: "left",
                cursor: "pointer",
                boxShadow: isSelected ? "0 4px 6px -1px rgba(0,0,0,0.1)" : "0 1px 2px rgba(0,0,0,0.05)",
                transition: "all 0.15s ease",
              }}
            >
              <div style={{ fontSize: "1.4rem", fontWeight: 800, lineHeight: 1 }}>{m.count}</div>
              <div style={{ fontSize: "0.75rem", fontWeight: 600, opacity: isSelected ? 0.95 : 0.7, marginTop: "0.3rem" }}>
                {m.label}
              </div>
            </button>
          );
        })}
      </div>

      {/* Filters & Search Controls */}
      <div
        style={{
          background: "var(--card-bg, #ffffff)",
          padding: "1rem 1.25rem",
          borderRadius: "12px",
          border: "1px solid var(--border, #e2e8f0)",
          display: "flex",
          flexWrap: "wrap",
          gap: "1rem",
          alignItems: "center",
        }}
      >
        {/* Search */}
        <div style={{ flex: "1 1 280px" }}>
          <input
            type="text"
            placeholder="Search patient, reference, test, case, village, ASHA..."
            value={currentSearch}
            onChange={(e) => updateFilters({ search: e.target.value, page: 1 })}
            style={{
              width: "100%",
              padding: "0.55rem 0.85rem",
              borderRadius: "8px",
              border: "1px solid var(--border, #cbd5e1)",
              fontSize: "0.85rem",
            }}
          />
        </div>

        {/* Status Filter */}
        <select
          value={currentStatusFilter}
          onChange={(e) => updateFilters({ status: e.target.value, page: 1 })}
          style={{ padding: "0.55rem 0.85rem", borderRadius: "8px", border: "1px solid var(--border, #cbd5e1)", fontSize: "0.85rem" }}
        >
          <option value="ALL_ACTIVE">All Active</option>
          <option value="ORDERED">Ordered</option>
          <option value="SAMPLE_PENDING">Sample Pending</option>
          <option value="SAMPLE_COLLECTED">Sample Collected</option>
          <option value="IN_PROCESS">In Process</option>
          <option value="RESULT_AVAILABLE">Result Available</option>
          <option value="CRITICAL">Critical Results</option>
          <option value="REVIEW_REQUIRED">Review Required</option>
          <option value="REVIEWED">Reviewed</option>
          <option value="RECOLLECTION_REQUIRED">Recollection Required</option>
          <option value="CANCELLED">Cancelled</option>
        </select>

        {/* Sorting */}
        <select
          value={currentSortBy}
          onChange={(e) => updateFilters({ sort_by: e.target.value })}
          style={{ padding: "0.55rem 0.85rem", borderRadius: "8px", border: "1px solid var(--border, #cbd5e1)", fontSize: "0.85rem" }}
        >
          <option value="critical_first">Critical First</option>
          <option value="result_ready_first">Result Ready First</option>
          <option value="oldest_pending">Oldest Pending</option>
          <option value="newest">Newest Order</option>
          <option value="patient_name">Patient Name</option>
        </select>
      </div>

      {/* Main List Display */}
      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              style={{
                height: "140px",
                background: "var(--card-bg, #ffffff)",
                borderRadius: "12px",
                border: "1px solid #e2e8f0",
                animation: "pulse 1.5s infinite ease-in-out",
              }}
            />
          ))}
        </div>
      ) : error ? (
        <div style={{ padding: "2rem", textAlign: "center", background: "#fef2f2", borderRadius: "12px", border: "1px solid #fca5a5", color: "#991b1b" }}>
          <h3>{t("messages.ERROR", "Error Loading Investigations")}</h3>
          <p>{error}</p>
          <button onClick={fetchData} style={{ padding: "0.5rem 1rem", borderRadius: "6px", background: "#dc2626", color: "#fff", border: "none", cursor: "pointer" }}>
            {t("common.retry", "Retry")}
          </button>
        </div>
      ) : items.length === 0 ? (
        <div style={{ padding: "3rem", textAlign: "center", background: "var(--card-bg, #ffffff)", borderRadius: "12px", border: "1px solid #e2e8f0", color: "#64748b" }}>
          <h3 style={{ margin: "0 0 0.5rem 0", color: "#0f172a" }}>{t("investigation.no_results", "No Investigations Found")}</h3>
          <p>{t("investigation.no_results", "No investigation orders match the selected filters or search query.")}</p>
          <button
            onClick={() => updateFilters({ status: "ALL_ACTIVE", search: null, category: null, priority: null })}
            style={{ padding: "0.5rem 1rem", borderRadius: "6px", border: "1px solid #cbd5e1", background: "none", cursor: "pointer" }}
          >
            {t("common.clear", "Clear Filters")}
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {items.map((item) => (
            <InvestigationCard
              key={item.id}
              item={item}
              onRecordSample={(ord) => setSelectedOrderForSample(ord)}
              onEnterResult={(ord) => setSelectedOrderForResult(ord)}
              onReviewResult={(ord) => handleOpenReviewModal(ord)}
              onAcknowledgeCritical={(ord) => handleAcknowledgeCritical(ord)}
              onRequestRecollection={(ord) => handleRequestRecollection(ord)}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      <OrderBuilderModal isOpen={isOrderModalOpen} onClose={() => setIsOrderModalOpen(false)} onSubmit={handleCreateOrder} />

      <SampleRecordModal
        isOpen={!!selectedOrderForSample}
        order={selectedOrderForSample}
        onClose={() => setSelectedOrderForSample(null)}
        onSubmit={handleRecordSampleSubmit}
      />

      <ResultEntryModal
        isOpen={!!selectedOrderForResult}
        order={selectedOrderForResult}
        onClose={() => setSelectedOrderForResult(null)}
        onSubmit={handleResultEntrySubmit}
      />

      {selectedOrderForRecollection && (
        <RequestRecollectionModal
          order={selectedOrderForRecollection}
          onClose={() => setSelectedOrderForRecollection(null)}
          onSuccess={() => fetchData()}
        />
      )}

      {/* Doctor Review Outcome Modal */}
      {reviewingOrder && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "1rem",
          }}
        >
          <div style={{ background: "#ffffff", borderRadius: "16px", width: "100%", maxWidth: "550px", padding: "1.5rem", boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1)" }}>
            <h2 style={{ margin: "0 0 1rem 0", fontSize: "1.2rem", fontWeight: 700 }}>
              Review Result: {reviewingOrder.test_name} ({reviewingOrder.reference})
            </h2>

            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Select Clinical Outcome *</label>
                <select
                  value={reviewOutcome}
                  onChange={(e) => setReviewOutcome(e.target.value)}
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                >
                  <option value="NO_CHANGE">No immediate change</option>
                  <option value="REPEAT_TEST">Repeat test</option>
                  <option value="UPDATE_CARE_PLAN">Update treatment/care plan</option>
                  <option value="PHC_REVIEW">Schedule PHC review</option>
                  <option value="ASHA_FOLLOW_UP">Assign ASHA follow-up</option>
                  <option value="REFER_HIGHER">Refer higher centre</option>
                  <option value="EMERGENCY_ACTION">Emergency action required</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>Doctor Review Note *</label>
                <textarea
                  rows={3}
                  value={reviewNote}
                  onChange={(e) => setReviewNote(e.target.value)}
                  placeholder="Enter clinical assessment note..."
                  required
                  style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.85rem" }}
                />
              </div>

              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", cursor: "pointer" }}>
                <input type="checkbox" checked={updateCarePlan} onChange={(e) => setUpdateCarePlan(e.target.checked)} />
                Flag Care Plan Updated in Patient Record
              </label>

              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.85rem", cursor: "pointer" }}>
                <input type="checkbox" checked={createFollowup} onChange={(e) => setCreateFollowup(e.target.checked)} />
                Create ASHA Follow-up Task
              </label>

              {createFollowup && (
                <div>
                  <input
                    type="text"
                    placeholder="Enter ASHA follow-up instructions..."
                    value={followupInstructions}
                    onChange={(e) => setFollowupInstructions(e.target.value)}
                    style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.85rem" }}
                  />
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "1rem" }}>
                <button type="button" onClick={() => setReviewingOrder(null)} style={{ padding: "0.5rem 1rem", borderRadius: "6px", border: "1px solid #cbd5e1", background: "none" }}>
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmReview}
                  disabled={reviewSubmitting}
                  style={{ padding: "0.5rem 1.25rem", borderRadius: "6px", border: "none", background: "#0284c7", color: "#ffffff", fontWeight: 600 }}
                >
                  {reviewSubmitting ? "Submitting..." : "Save Review"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
