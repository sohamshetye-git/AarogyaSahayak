import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge } from "../../components/StatusBadge";
import {
  Phone, Video, MessageSquare, Clock, CheckCircle, AlertTriangle,
  User, Check, X, ArrowRight, Play, RefreshCw, Filter, FileText
} from "lucide-react";
import { useRealtime } from "../../hooks/useRealtime";
import { useLanguage } from "../../context/LanguageContext";

export function DirectCitizenRequestsScreen() {
  const { t } = useLanguage();
  const navigate = useNavigate();

  const [requests, setRequests] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<string>("ALL");
  const [isProcessing, setIsProcessing] = useState<string | null>(null);

  // Complete Consultation Modal State
  const [selectedReq, setSelectedReq] = useState<any>(null);
  const [showCompleteModal, setShowCompleteModal] = useState(false);
  const [diagnosis, setDiagnosis] = useState("");
  const [guidance, setGuidance] = useState("");
  const [assignAsha, setAssignAsha] = useState(false);
  const [ashaInstructions, setAshaInstructions] = useState("");

  const fetchRequests = async () => {
    try {
      const res = await apiClient.getDoctorDirectRequests({ status: activeFilter });
      setRequests(res?.data || res || []);
      const sum = await apiClient.getDoctorDirectRequestsSummary();
      setSummary(sum?.data || sum);
    } catch (err) {
      console.error("Failed to load direct requests", err);
    } finally {
      setLoading(false);
    }
  };

  useRealtime((event) => {
    if (
      [
        "DOCTOR_REQUEST_CREATED",
        "DOCTOR_REQUEST_ACCEPTED",
        "CONSULTATION_STARTED",
        "CONSULTATION_COMPLETED"
      ].includes(event)
    ) {
      fetchRequests();
    }
  });

  useEffect(() => {
    fetchRequests();
    const interval = setInterval(fetchRequests, 10000);
    return () => clearInterval(interval);
  }, [activeFilter]);

  const handleAccept = async (e: React.MouseEvent, reqId: string) => {
    e.stopPropagation();
    setIsProcessing(reqId);
    try {
      await apiClient.acceptDoctorDirectRequest(reqId);
      await fetchRequests();
    } catch (err) {
      console.error("Failed to accept request", err);
    } finally {
      setIsProcessing(null);
    }
  };

  const handleStart = async (e: React.MouseEvent, reqId: string) => {
    e.stopPropagation();
    setIsProcessing(reqId);
    try {
      await apiClient.startDoctorDirectConsultation(reqId);
      await fetchRequests();
    } catch (err) {
      console.error("Failed to start consultation", err);
    } finally {
      setIsProcessing(null);
    }
  };

  const handleOpenCompleteModal = (e: React.MouseEvent, req: any) => {
    e.stopPropagation();
    setSelectedReq(req);
    setShowCompleteModal(true);
  };

  const handleSubmitComplete = async () => {
    if (!selectedReq) return;
    setIsProcessing(selectedReq.id);
    try {
      await apiClient.completeDoctorDirectConsultation(selectedReq.id, {
        provisional_diagnosis: diagnosis,
        clinical_summary: `${diagnosis} diagnosed during teleconsultation.`,
        patient_guidance: guidance,
        disposition: assignAsha ? "FOLLOW_UP_REQUIRED" : "COMPLETED",
        prescriptions: [
          {
            medicine_name: "Paracetamol 500mg",
            formulation: "Tablet",
            dosage: "1 tablet",
            frequency: "1-0-1",
            duration_days: 3,
            instructions: "Take after meals"
          },
          {
            medicine_name: "Cetirizine 10mg",
            formulation: "Tablet",
            dosage: "1 tablet",
            frequency: "0-0-1",
            duration_days: 3,
            instructions: "Take at bedtime"
          }
        ],
        investigation_orders: [],
        assign_asha_followup: assignAsha,
        asha_task_type: "POST_CONSULTATION_CHECK",
        asha_due_days: 3,
        asha_instructions: ashaInstructions,
        asha_escalation_conditions: "Escalate if high fever or breathing difficulty occurs."
      });
      setShowCompleteModal(false);
      await fetchRequests();
    } catch (err) {
      console.error("Failed to complete consultation", err);
    } finally {
      setIsProcessing(null);
    }
  };

  return (
    <div className="p-6 bg-slate-50 min-h-screen">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-3">
            <span>{t("navigation.direct_requests", "Direct Citizen Teleconsultation Requests")}</span>
            <span className="text-xs font-bold px-3 py-1 bg-blue-100 text-blue-800 rounded-full">
              {t("common.live", "Live Queue")}
            </span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time direct consultation requests from citizens & household members in Kalyanpur PHC catchment area.
          </p>
        </div>

        <button
          onClick={fetchRequests}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 shadow-sm"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          <span>{t("common.refresh", "Refresh")}</span>
        </button>
      </div>

      {/* Metric Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {[
          { id: "ALL", label: "Total Requests", count: summary?.total || 0, color: "text-slate-900", bg: "bg-white" },
          { id: "NEW", label: "New / Waiting", count: summary?.new || 0, color: "text-blue-600", bg: "bg-blue-50/50" },
          { id: "URGENT", label: "Urgent Triage", count: summary?.urgent || 0, color: "text-red-600", bg: "bg-red-50/50" },
          { id: "ACCEPTED", label: "Accepted", count: summary?.accepted || 0, color: "text-emerald-600", bg: "bg-emerald-50/50" },
          { id: "IN_CONSULTATION", label: "In Consultation", count: summary?.in_consultation || 0, color: "text-purple-600", bg: "bg-purple-50/50" },
          { id: "COMPLETED", label: "Completed", count: summary?.completed || 0, color: "text-slate-600", bg: "bg-slate-100/50" },
        ].map((m) => (
          <button
            key={m.id}
            onClick={() => setActiveFilter(m.id)}
            className={`p-4 rounded-2xl border text-left transition-all ${
              activeFilter === m.id
                ? "border-blue-600 ring-2 ring-blue-500/20 bg-white shadow-md"
                : "border-slate-200 bg-white hover:border-slate-300"
            }`}
          >
            <div className="text-xs font-bold text-slate-500">{m.label}</div>
            <div className={`text-2xl font-black mt-1 ${m.color}`}>{m.count}</div>
          </button>
        ))}
      </div>

      {/* Requests Queue List */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="text-sm font-bold text-slate-700">
            Queue: {requests.length} request(s)
          </div>
        </div>

        {requests.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <User size={48} className="mx-auto mb-3 opacity-40" />
            <div className="text-base font-bold text-slate-600">No requests in this queue</div>
            <div className="text-xs mt-1">Direct teleconsultation requests from citizens will appear here in real time.</div>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {requests.map((req) => {
              const isUrgent = req.priority === "EMERGENCY" || req.priority === "URGENT";
              return (
                <div
                  key={req.id}
                  className="p-5 hover:bg-slate-50/80 transition-colors flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
                >
                  {/* Patient & Request Meta */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs font-mono font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                        {req.request_reference || req.public_reference || req.id}
                      </span>
                      <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                        req.priority === "EMERGENCY" ? "bg-red-100 text-red-800" :
                        req.priority === "HIGH" || req.priority === "URGENT" ? "bg-orange-100 text-orange-800" :
                        "bg-blue-100 text-blue-800"
                      }`}>
                        {req.priority}
                      </span>
                      <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700">
                        {req.requested_channel || req.mode || "CALLBACK"}
                      </span>
                      <span className="text-xs font-semibold text-slate-400">
                        Village: {req.village_name || "Kalyanpur"}
                      </span>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-base font-extrabold text-slate-900">
                        {req.beneficiary_name || req.citizen_name || req.patient?.name}
                        <span className="text-sm font-normal text-slate-500 ml-1.5">
                          ({req.beneficiary_relationship || req.patient?.relationship || "Self"} • {req.village_name || "Kalyanpur"})
                        </span>
                      </div>

                      {req.patient_profile_id || req.patient_id || req.citizen_id ? (
                        <Link
                          to={`/doctor/patients/${req.patient_profile_id || req.patient_id || req.citizen_id}?returnTo=/doctor/direct-requests`}
                          className="text-xs font-bold text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center gap-1 bg-blue-50/60 hover:bg-blue-100/80 px-2 py-1 rounded-lg border border-blue-200/60 transition-colors"
                          title="Open complete longitudinal patient record"
                        >
                          <span>{t("patient.view_details", "View Patient Record")}</span>
                          <ArrowRight size={12} />
                        </Link>
                      ) : (
                        <span
                          className="text-xs font-medium text-slate-400 inline-flex items-center gap-1 bg-slate-100 px-2 py-1 rounded-lg cursor-not-allowed"
                          title="Patient profile relationship unavailable"
                        >
                          <span>Record unavailable</span>
                        </span>
                      )}
                    </div>

                    <div className="text-sm text-slate-700 mt-1 font-medium">
                      "{req.chief_complaint || req.chief_concern || "Care Handoff Request"}"
                    </div>

                    {req.citizen_summary && (
                      <div className="text-xs text-slate-500 mt-1 italic">
                        Confirmed summary: {req.citizen_summary}
                      </div>
                    )}
                  </div>

                  {/* Status & Actions */}
                  <div className="flex items-center gap-2 flex-wrap self-end md:self-center">
                    {req.citizen_phone && (
                      <a
                        href={`tel:${req.citizen_phone}`}
                        className="px-3 py-1.5 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-xl text-xs font-bold flex items-center gap-1 border border-emerald-200"
                      >
                        <Phone size={13} />
                        <span>Call ({req.citizen_phone})</span>
                      </a>
                    )}

                    <span className="text-xs font-bold px-3 py-1 rounded-full bg-slate-100 text-slate-700">
                      Status: {req.status}
                    </span>

                    {(req.status === "WAITING_FOR_DOCTOR" || req.status === "SUBMITTED" || req.status === "NEW") && (
                      <button
                        onClick={(e) => handleAccept(e, req.id)}
                        disabled={isProcessing === req.id}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm"
                      >
                        <Check size={14} /> Accept Request
                      </button>
                    )}

                    {req.status === "DOCTOR_ACCEPTED" && (
                      <button
                        onClick={(e) => handleStart(e, req.id)}
                        disabled={isProcessing === req.id}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm"
                      >
                        <Phone size={14} /> Start Consultation
                      </button>
                    )}

                    {req.status === "IN_CONSULTATION" && (
                      <button
                        onClick={(e) => handleOpenCompleteModal(e, req)}
                        className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm"
                      >
                        <FileText size={14} /> Complete & Prescribe
                      </button>
                    )}

                    {req.status === "COMPLETED" && (
                      <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200 flex items-center gap-1">
                        <CheckCircle size={14} /> Completed
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Complete Consultation Modal */}
      {showCompleteModal && selectedReq && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h3 className="text-lg font-black text-slate-900">Complete Consultation</h3>
                <p className="text-xs text-slate-500">Patient: {selectedReq.patient?.name} ({selectedReq.public_reference})</p>
              </div>
              <button onClick={() => setShowCompleteModal(false)} className="p-1 hover:bg-slate-100 rounded-lg">
                <X size={20} className="text-slate-400" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-700">Provisional Diagnosis</label>
                <input
                  type="text"
                  value={diagnosis}
                  onChange={(e) => setDiagnosis(e.target.value)}
                  className="w-full mt-1 p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700">Patient Guidance / Care Plan</label>
                <textarea
                  rows={3}
                  value={guidance}
                  onChange={(e) => setGuidance(e.target.value)}
                  className="w-full mt-1 p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* ASHA Follow-up Assignment Directive */}
              <div className="p-4 bg-blue-50/60 rounded-2xl border border-blue-100">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={assignAsha}
                    onChange={(e) => setAssignAsha(e.target.checked)}
                    className="w-4 h-4 rounded text-blue-600"
                  />
                  <span className="text-xs font-bold text-blue-900">Assign ASHA Home Follow-up Directive (3 Days)</span>
                </label>

                {assignAsha && (
                  <div className="mt-3">
                    <label className="text-[11px] font-semibold text-blue-800">ASHA Instructions</label>
                    <input
                      type="text"
                      value={ashaInstructions}
                      onChange={(e) => setAshaInstructions(e.target.value)}
                      className="w-full mt-1 p-2 bg-white border border-blue-200 rounded-xl text-xs outline-none"
                    />
                  </div>
                )}
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setShowCompleteModal(false)}
                className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitComplete}
                disabled={isProcessing === selectedReq.id}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-xs shadow-lg shadow-blue-500/20 flex items-center gap-2"
              >
                <Check size={16} /> Sign & Complete Consultation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
