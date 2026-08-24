import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@aarogya/api-client";
import { PriorityBadge, StatusBadge } from "../../components/StatusBadge";
import { ChevronRightIcon, SearchIcon, StethoscopeIcon } from "../../components/Icons";

export function DoctorReferralQueueScreen() {
  const navigate = useNavigate();
  const [referrals, setReferrals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiClient.getDoctorReferrals();
        setReferrals(res);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <h2 style={{ margin: "0 0 8px", fontSize: 18, fontWeight: 700 }}>PHC Incoming Referral Queue</h2>
        <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
          Patients referred by village ASHA workers requiring medical evaluation and care planning.
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: 40 }}>Loading queue...</div>
        ) : (
          referrals.map((r) => (
            <div
              key={r.id}
              onClick={() => navigate(`/doctor/consultation?caseId=${r.case_id}`)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "18px 20px",
                borderRadius: 10,
                border: r.urgency === "URGENT" ? "1px solid #F5C6CB" : "1px solid var(--border)",
                backgroundColor: r.urgency === "URGENT" ? "var(--urgent-bg)" : "var(--surface)",
                cursor: "pointer",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 16, fontWeight: 700 }}>{r.citizen_name}</span>
                  {r.is_pregnant && (
                    <span style={{ padding: "2px 8px", borderRadius: 10, backgroundColor: "#FCE4EC", color: "#C2185B", fontSize: 11, fontWeight: 700 }}>
                      Pregnant
                    </span>
                  )}
                  <PriorityBadge priority={r.urgency} size="sm" />
                  <StatusBadge status={r.status} />
                </div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
                  Case: {r.case_reference} · Referring ASHA: {r.referring_asha_name || "Sita Patel"}
                </div>
                <div style={{ fontSize: 13, color: "var(--text-primary)", fontWeight: 500, marginTop: 4 }}>
                  Reason: {r.reason}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--primary)", fontWeight: 700, fontSize: 13 }}>
                <span>Consult</span>
                <ChevronRightIcon size={18} color="var(--primary)" />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export function DoctorPatientsScreen() {
  const [patients, setPatients] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiClient.request<any[]>("/doctor/patients");
        setPatients(res);
      } catch (err) {
        console.error(err);
      }
    };
    load();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ backgroundColor: "var(--surface)", padding: 24, borderRadius: 12, border: "1px solid var(--border)" }}>
        <h2 style={{ margin: "0 0 8px", fontSize: 18, fontWeight: 700 }}>Registered PHC Patients</h2>
        <p style={{ margin: 0, fontSize: 14, color: "var(--text-secondary)" }}>
          Longitudinal health records and active care plans in Kalyanpur block.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
        {patients.map((p) => (
          <div key={p.id} style={{ backgroundColor: "var(--surface)", padding: 20, borderRadius: 12, border: "1px solid var(--border)" }}>
            <div style={{ fontSize: 16, fontWeight: 700 }}>{p.name}</div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
              Age: {p.age} · Gender: {p.gender} · Village: {p.village}
            </div>
            {p.is_pregnant && (
              <div style={{ fontSize: 12, color: "#C2185B", fontWeight: 700, marginTop: 6 }}>
                Maternal Record (High Priority Track)
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
