import React, { useState, useEffect } from "react";
import { apiClient } from "@aarogya/api-client";
import { UserRole } from "@aarogya/shared-types";
import {
  PeopleIcon,
  UserPlusIcon,
  StethoscopeIcon,
  HospitalIcon,
  ShieldCheckIcon,
  WarningIcon,
  CheckIcon,
  ChevronLeftIcon,
  ActivityIcon
} from "../../components/Icons";

export function StaffManagementScreen() {
  const [summary, setSummary] = useState({
    total: 0,
    active: 0,
    suspended: 0,
    asha_workers: 0,
    phc_doctors: 0
  });
  const [staffList, setStaffList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [facilityFilter, setFacilityFilter] = useState("");
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const limit = 15;

  // Facilities and villages for select options
  const [facilities, setFacilities] = useState<any[]>([]);
  const [villages, setVillages] = useState<any[]>([]);

  // Modals state
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [showSuspendModal, setShowSuspendModal] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const [showCredentialsModal, setShowCredentialsModal] = useState(false);

  const [selectedStaff, setSelectedStaff] = useState<any>(null);
  const [createdCredentials, setCreatedCredentials] = useState<any>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Form states for Add Staff
  const [addForm, setAddForm] = useState({
    name: "",
    role: "ASHA_WORKER",
    phone: "",
    email: "",
    employee_id: "",
    preferred_language: "mr-IN",
    district: "District 04",
    assigned_facility_id: "",
    village_name: "Kalyanpur",
    coverage_area: "",
    medical_registration_number: "",
    specialization: ""
  });

  // Edit form state
  const [editForm, setEditForm] = useState({
    name: "",
    phone: "",
    email: "",
    preferred_language: "mr-IN",
    village_name: "",
    coverage_area: "",
    specialization: "",
    medical_registration_number: ""
  });

  // Transfer form state
  const [transferForm, setTransferForm] = useState({
    facility_id: "",
    village_name: "",
    coverage_area: "",
    reason: ""
  });

  // Suspend reason
  const [suspendReason, setSuspendReason] = useState("");

  const loadStaff = async () => {
    setLoading(true);
    try {
      const res = await apiClient.getAdminStaffList({
        search: search || undefined,
        role: roleFilter || undefined,
        status: statusFilter || undefined,
        facility_id: facilityFilter || undefined,
        page,
        limit
      });
      if (res) {
        setSummary(res.summary || summary);
        setStaffList(res.staff || []);
        setTotalItems(res.total || 0);
      }
    } catch (err) {
      console.error("Failed to load staff list", err);
    } finally {
      setLoading(false);
    }
  };

  const loadOptions = async () => {
    try {
      const opts = await apiClient.getPatientRegistrationOptions().catch(() => null);
      if (opts) {
        setFacilities(opts.facilities || []);
        setVillages(opts.villages || []);
        if (opts.facilities?.length > 0 && !addForm.assigned_facility_id) {
          setAddForm(prev => ({ ...prev, assigned_facility_id: opts.facilities[0].id }));
        }
      }
    } catch (e) {
      console.error("Failed to load options", e);
    }
  };

  useEffect(() => {
    loadOptions();
  }, []);

  useEffect(() => {
    loadStaff();
  }, [search, roleFilter, statusFilter, facilityFilter, page]);

  // Handle Add Staff Submit
  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    setActionLoading(true);

    try {
      const payload: any = {
        name: addForm.name.trim(),
        role: addForm.role,
        phone: addForm.phone.trim(),
        email: addForm.email.trim() || undefined,
        employee_id: addForm.employee_id.trim() || undefined,
        preferred_language: addForm.preferred_language,
        district: addForm.district,
        assigned_facility_id: addForm.assigned_facility_id || undefined
      };

      if (addForm.role === "ASHA_WORKER") {
        payload.village_name = addForm.village_name;
        payload.coverage_area = addForm.coverage_area;
      } else {
        payload.medical_registration_number = addForm.medical_registration_number.trim() || undefined;
        payload.specialization = addForm.specialization.trim() || undefined;
      }

      const res = await apiClient.createStaff(payload);
      setShowAddModal(false);
      setCreatedCredentials(res);
      setShowCredentialsModal(true);
      
      // Reset form
      setAddForm({
        name: "",
        role: "ASHA_WORKER",
        phone: "",
        email: "",
        employee_id: "",
        preferred_language: "mr-IN",
        district: "District 04",
        assigned_facility_id: facilities[0]?.id || "",
        village_name: "Kalyanpur",
        coverage_area: "",
        medical_registration_number: "",
        specialization: ""
      });

      loadStaff();
    } catch (err: any) {
      setModalError(err?.message || err?.detail?.message || "Failed to create staff member. Check duplicate employee/registration ID.");
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Edit Submit
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStaff) return;
    setModalError(null);
    setActionLoading(true);

    try {
      await apiClient.updateStaff(selectedStaff.id, {
        name: editForm.name.trim(),
        phone: editForm.phone.trim(),
        email: editForm.email.trim() || undefined,
        preferred_language: editForm.preferred_language,
        village_name: editForm.village_name || undefined,
        coverage_area: editForm.coverage_area || undefined,
        specialization: editForm.specialization || undefined,
        medical_registration_number: editForm.medical_registration_number || undefined
      });
      setShowEditModal(false);
      loadStaff();
    } catch (err: any) {
      setModalError(err?.message || "Failed to update staff record.");
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Transfer Submit
  const handleTransferSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStaff) return;
    setModalError(null);
    setActionLoading(true);

    try {
      await apiClient.transferStaff(selectedStaff.id, {
        facility_id: transferForm.facility_id || undefined,
        village_name: transferForm.village_name || undefined,
        coverage_area: transferForm.coverage_area || undefined,
        reason: transferForm.reason || undefined
      });
      setShowTransferModal(false);
      loadStaff();
    } catch (err: any) {
      setModalError(err?.message || "Failed to transfer staff.");
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Suspend
  const handleSuspend = async () => {
    if (!selectedStaff) return;
    setActionLoading(true);
    setModalError(null);
    try {
      await apiClient.suspendStaff(selectedStaff.id, suspendReason);
      setShowSuspendModal(false);
      setSuspendReason("");
      loadStaff();
    } catch (err: any) {
      setModalError(err?.message || "Failed to suspend staff.");
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Reactivate
  const handleReactivate = async (staff: any) => {
    setActionLoading(true);
    try {
      await apiClient.reactivateStaff(staff.id);
      loadStaff();
    } catch (err: any) {
      alert(err?.message || "Failed to reactivate staff.");
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Reset Password
  const handleResetPassword = async () => {
    if (!selectedStaff) return;
    setActionLoading(true);
    setModalError(null);
    try {
      const res = await apiClient.resetStaffPassword(selectedStaff.id);
      setShowResetModal(false);
      setCreatedCredentials(res);
      setShowCredentialsModal(true);
      loadStaff();
    } catch (err: any) {
      setModalError(err?.message || "Failed to reset password.");
    } finally {
      setActionLoading(false);
    }
  };

  const openEdit = (staff: any) => {
    setSelectedStaff(staff);
    setEditForm({
      name: staff.name || "",
      phone: staff.phone || "",
      email: staff.email || "",
      preferred_language: staff.preferred_language || "mr-IN",
      village_name: staff.village_name || "",
      coverage_area: staff.coverage_area || "",
      specialization: staff.specialization || "",
      medical_registration_number: staff.medical_registration_number || ""
    });
    setModalError(null);
    setShowEditModal(true);
  };

  const openTransfer = (staff: any) => {
    setSelectedStaff(staff);
    setTransferForm({
      facility_id: staff.assigned_facility_id || facilities[0]?.id || "",
      village_name: staff.village_name || "",
      coverage_area: staff.coverage_area || "",
      reason: ""
    });
    setModalError(null);
    setShowTransferModal(true);
  };

  const openSuspend = (staff: any) => {
    setSelectedStaff(staff);
    setSuspendReason("");
    setModalError(null);
    setShowSuspendModal(true);
  };

  const openReset = (staff: any) => {
    setSelectedStaff(staff);
    setModalError(null);
    setShowResetModal(true);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert("Copied to clipboard!");
  };

  const printCredentials = () => {
    window.print();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Top Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: "var(--text-primary)" }}>
            District Staff Management
          </h1>
          <p style={{ margin: "4px 0 0", fontSize: 13.5, color: "var(--text-secondary)" }}>
            Authorize, create, and oversee active ASHA workers and PHC medical officers in District 04.
          </p>
        </div>
        <button
          data-testid="btn-add-staff-modal"
          onClick={() => {
            setModalError(null);
            setShowAddModal(true);
          }}
          style={{
            height: 42,
            padding: "0 18px",
            backgroundColor: "var(--primary)",
            color: "#FFFFFF",
            border: "none",
            borderRadius: 8,
            fontSize: 14,
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: 8,
            cursor: "pointer",
            boxShadow: "0 2px 6px rgba(21, 101, 192, 0.25)"
          }}
        >
          <UserPlusIcon size={18} color="#FFFFFF" />
          <span>Add Staff Member</span>
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16 }}>
        <div style={{ backgroundColor: "var(--surface)", padding: 18, borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 500 }}>Total Registered Staff</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "var(--text-primary)", marginTop: 4 }}>
            {summary.total}
          </div>
        </div>

        <div style={{ backgroundColor: "var(--surface)", padding: 18, borderRadius: 12, border: "1px solid #BBF7D0" }}>
          <div style={{ fontSize: 13, color: "#166534", fontWeight: 600 }}>Active Personnel</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#166534", marginTop: 4 }}>
            {summary.active}
          </div>
        </div>

        <div style={{ backgroundColor: "var(--surface)", padding: 18, borderRadius: 12, border: "1px solid #FED7AA" }}>
          <div style={{ fontSize: 13, color: "#C2410C", fontWeight: 600 }}>Suspended Accounts</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#C2410C", marginTop: 4 }}>
            {summary.suspended}
          </div>
        </div>

        <div style={{ backgroundColor: "var(--surface)", padding: 18, borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 13, color: "var(--primary)", fontWeight: 600 }}>ASHA Workers</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "var(--primary)", marginTop: 4 }}>
            {summary.asha_workers}
          </div>
        </div>

        <div style={{ backgroundColor: "var(--surface)", padding: 18, borderRadius: 12, border: "1px solid var(--border)" }}>
          <div style={{ fontSize: 13, color: "var(--teal)", fontWeight: 600 }}>PHC Medical Officers</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "var(--teal)", marginTop: 4 }}>
            {summary.phc_doctors}
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div style={{
        backgroundColor: "var(--surface)",
        padding: "16px 20px",
        borderRadius: 12,
        border: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 12
      }}>
        <div style={{ flex: "1 1 240px" }}>
          <input
            type="text"
            data-testid="input-staff-search"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search by name, Staff ID, or phone..."
            style={{
              width: "100%",
              height: 40,
              padding: "0 12px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              fontSize: 13.5,
              backgroundColor: "var(--neutral-bg)",
              boxSizing: "border-box"
            }}
          />
        </div>

        <select
          data-testid="select-role-filter"
          value={roleFilter}
          onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
          style={{
            height: 40,
            padding: "0 10px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            fontSize: 13,
            backgroundColor: "var(--surface)",
            cursor: "pointer"
          }}
        >
          <option value="">All Roles</option>
          <option value="ASHA_WORKER">ASHA Worker</option>
          <option value="PHC_DOCTOR">PHC Doctor</option>
        </select>

        <select
          data-testid="select-status-filter"
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          style={{
            height: 40,
            padding: "0 10px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            fontSize: 13,
            backgroundColor: "var(--surface)",
            cursor: "pointer"
          }}
        >
          <option value="">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="SUSPENDED">Suspended</option>
        </select>

        <select
          data-testid="select-facility-filter"
          value={facilityFilter}
          onChange={(e) => { setFacilityFilter(e.target.value); setPage(1); }}
          style={{
            height: 40,
            padding: "0 10px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            fontSize: 13,
            backgroundColor: "var(--surface)",
            cursor: "pointer"
          }}
        >
          <option value="">All Assigned Facilities</option>
          {facilities.map(f => (
            <option key={f.id} value={f.id}>{f.name}</option>
          ))}
        </select>
      </div>

      {/* Staff Table */}
      <div style={{
        backgroundColor: "var(--surface)",
        borderRadius: 12,
        border: "1px solid var(--border)",
        overflow: "hidden"
      }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 13.5 }}>
            <thead>
              <tr style={{ backgroundColor: "var(--neutral-bg)", borderBottom: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                <th style={{ padding: "14px 16px", fontWeight: 600 }}>Staff Name &amp; ID</th>
                <th style={{ padding: "14px 16px", fontWeight: 600 }}>Role</th>
                <th style={{ padding: "14px 16px", fontWeight: 600 }}>Assigned PHC / Facility</th>
                <th style={{ padding: "14px 16px", fontWeight: 600 }}>Village / Coverage</th>
                <th style={{ padding: "14px 16px", fontWeight: 600 }}>Masked Phone</th>
                <th style={{ padding: "14px 16px", fontWeight: 600 }}>Status</th>
                <th style={{ padding: "14px 16px", fontWeight: 600 }}>Last Login</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
                    Loading staff directory...
                  </td>
                </tr>
              ) : staffList.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
                    No staff members found matching the selected criteria.
                  </td>
                </tr>
              ) : (
                staffList.map((staff) => {
                  const isSuspended = staff.account_status === "SUSPENDED";
                  const isAsha = staff.role === "ASHA_WORKER";
                  return (
                    <tr
                      key={staff.id}
                      data-testid={`row-staff-${staff.staff_id}`}
                      style={{
                        borderBottom: "1px solid var(--divider)",
                        backgroundColor: isSuspended ? "#FFF7ED" : "transparent"
                      }}
                    >
                      {/* Name & ID */}
                      <td style={{ padding: "14px 16px" }}>
                        <div style={{ fontWeight: 700, color: "var(--text-primary)" }}>{staff.name}</div>
                        <div style={{ fontSize: 12, color: "var(--primary)", fontFamily: "monospace", marginTop: 2 }}>
                          {staff.staff_id}
                        </div>
                        {staff.employee_id && (
                          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                            Emp: {staff.employee_id}
                          </div>
                        )}
                      </td>

                      {/* Role */}
                      <td style={{ padding: "14px 16px" }}>
                        <span style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "4px 10px",
                          borderRadius: 6,
                          fontSize: 12,
                          fontWeight: 700,
                          backgroundColor: isAsha ? "var(--primary-light)" : "#E0F2FE",
                          color: isAsha ? "var(--primary-dark)" : "#0369A1"
                        }}>
                          {isAsha ? <PeopleIcon size={14} /> : <StethoscopeIcon size={14} />}
                          {isAsha ? "ASHA Worker" : "PHC Doctor"}
                        </span>
                        {staff.specialization && (
                          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
                            {staff.specialization}
                          </div>
                        )}
                      </td>

                      {/* Facility */}
                      <td style={{ padding: "14px 16px" }}>
                        <div style={{ fontWeight: 500, color: "var(--text-primary)" }}>
                          {staff.assigned_facility_name || "Primary Health Centre"}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                          {staff.district_name || "District 04"}
                        </div>
                      </td>

                      {/* Village / Coverage */}
                      <td style={{ padding: "14px 16px" }}>
                        <div>{staff.village_name || "Kalyanpur"}</div>
                        {staff.coverage_area && (
                          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                            Area: {staff.coverage_area}
                          </div>
                        )}
                      </td>

                      {/* Masked Phone */}
                      <td style={{ padding: "14px 16px", color: "var(--text-secondary)", fontFamily: "monospace" }}>
                        {staff.phone_masked || "XXXX-XXXX"}
                      </td>

                      {/* Status */}
                      <td style={{ padding: "14px 16px" }}>
                        <span style={{
                          padding: "3px 8px",
                          borderRadius: 6,
                          fontSize: 11,
                          fontWeight: 700,
                          backgroundColor: isSuspended ? "#FEE2E2" : "#DCFCE7",
                          color: isSuspended ? "#991B1B" : "#166534"
                        }}>
                          {isSuspended ? "SUSPENDED" : "ACTIVE"}
                        </span>
                        {staff.must_change_password && (
                          <div style={{ fontSize: 10, color: "#D97706", fontWeight: 600, marginTop: 4 }}>
                            PWD RESET REQ
                          </div>
                        )}
                      </td>

                      {/* Last Login */}
                      <td style={{ padding: "14px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                        {staff.last_login_at
                          ? new Date(staff.last_login_at).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })
                          : "Never"}
                      </td>

                      {/* Actions */}
                      <td style={{ padding: "14px 16px", textAlign: "right" }}>
                        <div style={{ display: "inline-flex", gap: 6 }}>
                          <button
                            data-testid={`btn-edit-${staff.staff_id}`}
                            onClick={() => openEdit(staff)}
                            style={{
                              padding: "4px 8px",
                              fontSize: 12,
                              borderRadius: 6,
                              border: "1px solid var(--border)",
                              backgroundColor: "var(--surface)",
                              cursor: "pointer",
                              fontWeight: 600
                            }}
                          >
                            Edit
                          </button>

                          <button
                            data-testid={`btn-transfer-${staff.staff_id}`}
                            onClick={() => openTransfer(staff)}
                            style={{
                              padding: "4px 8px",
                              fontSize: 12,
                              borderRadius: 6,
                              border: "1px solid var(--border)",
                              backgroundColor: "var(--surface)",
                              cursor: "pointer",
                              fontWeight: 600
                            }}
                          >
                            Transfer
                          </button>

                          <button
                            data-testid={`btn-reset-pwd-${staff.staff_id}`}
                            onClick={() => openReset(staff)}
                            style={{
                              padding: "4px 8px",
                              fontSize: 12,
                              borderRadius: 6,
                              border: "1px solid #FED7AA",
                              backgroundColor: "#FFFBEB",
                              color: "#B45309",
                              cursor: "pointer",
                              fontWeight: 600
                            }}
                          >
                            Reset PWD
                          </button>

                          {isSuspended ? (
                            <button
                              data-testid={`btn-reactivate-${staff.staff_id}`}
                              onClick={() => handleReactivate(staff)}
                              style={{
                                padding: "4px 8px",
                                fontSize: 12,
                                borderRadius: 6,
                                border: "1px solid #BBF7D0",
                                backgroundColor: "#F0FDF4",
                                color: "#166534",
                                cursor: "pointer",
                                fontWeight: 600
                              }}
                            >
                              Reactivate
                            </button>
                          ) : (
                            <button
                              data-testid={`btn-suspend-${staff.staff_id}`}
                              onClick={() => openSuspend(staff)}
                              style={{
                                padding: "4px 8px",
                                fontSize: 12,
                                borderRadius: 6,
                                border: "1px solid #FECACA",
                                backgroundColor: "#FEF2F2",
                                color: "#991B1B",
                                cursor: "pointer",
                                fontWeight: 600
                              }}
                            >
                              Suspend
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div style={{
          padding: "12px 20px",
          borderTop: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: 13,
          color: "var(--text-secondary)"
        }}>
          <div>
            Showing <strong>{staffList.length}</strong> of <strong>{totalItems}</strong> staff members
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              disabled={page <= 1}
              onClick={() => setPage(p => p - 1)}
              style={{
                padding: "4px 10px",
                borderRadius: 6,
                border: "1px solid var(--border)",
                backgroundColor: "var(--surface)",
                cursor: page <= 1 ? "not-allowed" : "pointer"
              }}
            >
              Previous
            </button>
            <span style={{ display: "flex", alignItems: "center", padding: "0 6px" }}>Page {page}</span>
            <button
              disabled={page * limit >= totalItems}
              onClick={() => setPage(p => p + 1)}
              style={{
                padding: "4px 10px",
                borderRadius: 6,
                border: "1px solid var(--border)",
                backgroundColor: "var(--surface)",
                cursor: page * limit >= totalItems ? "not-allowed" : "pointer"
              }}
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* --- ADD STAFF MODAL --- */}
      {showAddModal && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0,0,0,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 100,
          padding: 16
        }}>
          <div style={{
            backgroundColor: "#FFFFFF",
            borderRadius: 16,
            width: "100%",
            maxWidth: 580,
            maxHeight: "90vh",
            overflowY: "auto",
            padding: 28,
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
          }}>
            <h2 style={{ margin: "0 0 4px", fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
              Create New Staff Member
            </h2>
            <p style={{ margin: "0 0 16px", fontSize: 13, color: "var(--text-secondary)" }}>
              Generates a collision-safe Staff ID and a one-time temporary password.
            </p>

            {modalError && (
              <div style={{
                backgroundColor: "#FDECEC",
                border: "1px solid #F5C6CB",
                borderRadius: 8,
                padding: "10px 14px",
                marginBottom: 16,
                fontSize: 13,
                color: "#C62828"
              }}>
                {modalError}
              </div>
            )}

            <form onSubmit={handleAddSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
                    Role *
                  </label>
                  <select
                    data-testid="input-new-staff-role"
                    value={addForm.role}
                    onChange={(e) => setAddForm({ ...addForm, role: e.target.value })}
                    style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px" }}
                  >
                    <option value="ASHA_WORKER">ASHA Worker</option>
                    <option value="PHC_DOCTOR">PHC Doctor</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
                    Full Legal Name *
                  </label>
                  <input
                    type="text"
                    data-testid="input-new-staff-name"
                    required
                    value={addForm.name}
                    onChange={(e) => setAddForm({ ...addForm, name: e.target.value })}
                    placeholder="e.g. Rekha Bai Patel"
                    style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px", boxSizing: "border-box" }}
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
                    Phone Number *
                  </label>
                  <input
                    type="tel"
                    data-testid="input-new-staff-phone"
                    required
                    value={addForm.phone}
                    onChange={(e) => setAddForm({ ...addForm, phone: e.target.value })}
                    placeholder="10-digit mobile"
                    style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px", boxSizing: "border-box" }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
                    Email (Optional)
                  </label>
                  <input
                    type="email"
                    data-testid="input-new-staff-email"
                    value={addForm.email}
                    onChange={(e) => setAddForm({ ...addForm, email: e.target.value })}
                    placeholder="staff@arogya.gov.in"
                    style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px", boxSizing: "border-box" }}
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
                    Employee ID (Unique)
                  </label>
                  <input
                    type="text"
                    data-testid="input-new-staff-emp-id"
                    value={addForm.employee_id}
                    onChange={(e) => setAddForm({ ...addForm, employee_id: e.target.value })}
                    placeholder="e.g. EMP-2026-904"
                    style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px", boxSizing: "border-box" }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
                    Assigned PHC / Facility *
                  </label>
                  <select
                    data-testid="input-new-staff-facility"
                    value={addForm.assigned_facility_id}
                    onChange={(e) => setAddForm({ ...addForm, assigned_facility_id: e.target.value })}
                    style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px" }}
                  >
                    {facilities.map(f => (
                      <option key={f.id} value={f.id}>{f.name} ({f.facility_type})</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Conditional Fields */}
              {addForm.role === "ASHA_WORKER" ? (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
                      Assigned Village
                    </label>
                    <select
                      data-testid="input-new-staff-village"
                      value={addForm.village_name}
                      onChange={(e) => setAddForm({ ...addForm, village_name: e.target.value })}
                      style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px" }}
                    >
                      {villages.map(v => (
                        <option key={v.id || v.name} value={v.name}>{v.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
                      Coverage Area
                    </label>
                    <input
                      type="text"
                      data-testid="input-new-staff-coverage"
                      value={addForm.coverage_area}
                      onChange={(e) => setAddForm({ ...addForm, coverage_area: e.target.value })}
                      placeholder="e.g. Ward 1-3 / North Sector"
                      style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px", boxSizing: "border-box" }}
                    />
                  </div>
                </div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
                      Medical Reg Number *
                    </label>
                    <input
                      type="text"
                      data-testid="input-new-staff-reg-no"
                      required
                      value={addForm.medical_registration_number}
                      onChange={(e) => setAddForm({ ...addForm, medical_registration_number: e.target.value })}
                      placeholder="e.g. MMC-2024-99124"
                      style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px", boxSizing: "border-box" }}
                    />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
                      Specialization
                    </label>
                    <input
                      type="text"
                      data-testid="input-new-staff-specialization"
                      value={addForm.specialization}
                      onChange={(e) => setAddForm({ ...addForm, specialization: e.target.value })}
                      placeholder="e.g. General Medicine / MBBS"
                      style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px", boxSizing: "border-box" }}
                    />
                  </div>
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 14 }}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  style={{
                    padding: "8px 16px",
                    borderRadius: 6,
                    border: "1px solid var(--border)",
                    backgroundColor: "var(--surface)",
                    cursor: "pointer"
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  data-testid="btn-submit-add-staff"
                  disabled={actionLoading}
                  style={{
                    padding: "8px 18px",
                    borderRadius: 6,
                    border: "none",
                    backgroundColor: "var(--primary)",
                    color: "#FFFFFF",
                    fontWeight: 600,
                    cursor: actionLoading ? "not-allowed" : "pointer"
                  }}
                >
                  {actionLoading ? "Creating Staff..." : "Create Staff & Generate ID"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- CREDENTIALS POPUP MODAL --- */}
      {showCredentialsModal && createdCredentials && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0,0,0,0.6)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 110,
          padding: 16
        }}>
          <div style={{
            backgroundColor: "#FFFFFF",
            borderRadius: 16,
            width: "100%",
            maxWidth: 480,
            padding: 28,
            boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)"
          }}>
            <div style={{ textAlign: "center", marginBottom: 20 }}>
              <div style={{
                width: 44,
                height: 44,
                borderRadius: "50%",
                backgroundColor: "#DCFCE7",
                color: "#166534",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: 10
              }}>
                <CheckIcon size={22} color="#166534" />
              </div>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
                Staff Credentials Generated
              </h2>
              <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-secondary)" }}>
                Account created for <strong>{createdCredentials.name}</strong> ({createdCredentials.role})
              </p>
            </div>

            {/* Critical Notice */}
            <div style={{
              backgroundColor: "#FFFBEB",
              border: "1px solid #FDE68A",
              borderRadius: 8,
              padding: "12px 14px",
              marginBottom: 18,
              fontSize: 12.5,
              color: "#92400E",
              display: "flex",
              gap: 8,
              alignItems: "flex-start"
            }}>
              <WarningIcon size={16} color="#D97706" />
              <span>
                <strong>Save these credentials now.</strong> The temporary password will not be shown again.
              </span>
            </div>

            {/* Credential Box */}
            <div style={{
              backgroundColor: "var(--neutral-bg)",
              borderRadius: 8,
              border: "1px solid var(--border)",
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 12,
              marginBottom: 20
            }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase" }}>
                  Staff ID / Username
                </div>
                <div data-testid="credential-staff-id" style={{ fontSize: 16, fontWeight: 800, color: "var(--primary)", fontFamily: "monospace", marginTop: 2 }}>
                  {createdCredentials.staff_id}
                </div>
              </div>

              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase" }}>
                  One-Time Temporary Password
                </div>
                <div data-testid="credential-temp-password" style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)", fontFamily: "monospace", marginTop: 2 }}>
                  {createdCredentials.temporary_password}
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <button
                data-testid="btn-copy-credentials"
                onClick={() => copyToClipboard(`Staff ID: ${createdCredentials.staff_id}\nTemporary Password: ${createdCredentials.temporary_password}`)}
                style={{
                  flex: 1,
                  height: 40,
                  borderRadius: 6,
                  border: "1px solid var(--primary)",
                  backgroundColor: "var(--primary-light)",
                  color: "var(--primary-dark)",
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: "pointer"
                }}
              >
                Copy Credentials
              </button>
              <button
                data-testid="btn-print-credentials"
                onClick={printCredentials}
                style={{
                  flex: 1,
                  height: 40,
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                  backgroundColor: "var(--surface)",
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: "pointer"
                }}
              >
                Print Slip
              </button>
            </div>

            <button
              data-testid="btn-close-credentials-modal"
              onClick={() => {
                setShowCredentialsModal(false);
                setCreatedCredentials(null);
              }}
              style={{
                width: "100%",
                height: 40,
                marginTop: 10,
                borderRadius: 6,
                border: "none",
                backgroundColor: "var(--primary)",
                color: "#FFFFFF",
                fontWeight: 600,
                fontSize: 13,
                cursor: "pointer"
              }}
            >
              Done
            </button>
          </div>
        </div>
      )}

      {/* --- EDIT MODAL --- */}
      {showEditModal && selectedStaff && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0,0,0,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 100,
          padding: 16
        }}>
          <div style={{
            backgroundColor: "#FFFFFF",
            borderRadius: 16,
            width: "100%",
            maxWidth: 520,
            padding: 24,
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
          }}>
            <h2 style={{ margin: "0 0 4px", fontSize: 18, fontWeight: 700 }}>
              Edit Staff Profile: {selectedStaff.staff_id}
            </h2>
            <p style={{ margin: "0 0 16px", fontSize: 13, color: "var(--text-secondary)" }}>
              Update contact info and coverage for {selectedStaff.name}.
            </p>

            {modalError && (
              <div style={{ backgroundColor: "#FDECEC", color: "#C62828", padding: 10, borderRadius: 6, marginBottom: 12, fontSize: 13 }}>
                {modalError}
              </div>
            )}

            <form onSubmit={handleEditSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>Full Name</label>
                <input
                  type="text"
                  required
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px", boxSizing: "border-box" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>Phone Number</label>
                <input
                  type="tel"
                  required
                  value={editForm.phone}
                  onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                  style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px", boxSizing: "border-box" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>Email</label>
                <input
                  type="email"
                  value={editForm.email}
                  onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                  style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px", boxSizing: "border-box" }}
                />
              </div>

              {selectedStaff.role === "ASHA_WORKER" ? (
                <div>
                  <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>Coverage Area</label>
                  <input
                    type="text"
                    value={editForm.coverage_area}
                    onChange={(e) => setEditForm({ ...editForm, coverage_area: e.target.value })}
                    style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px", boxSizing: "border-box" }}
                  />
                </div>
              ) : (
                <div>
                  <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>Specialization</label>
                  <input
                    type="text"
                    value={editForm.specialization}
                    onChange={(e) => setEditForm({ ...editForm, specialization: e.target.value })}
                    style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px", boxSizing: "border-box" }}
                  />
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 14 }}>
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  style={{ padding: "8px 18px", borderRadius: 6, border: "none", backgroundColor: "var(--primary)", color: "#FFFFFF", fontWeight: 600, cursor: "pointer" }}
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- TRANSFER MODAL --- */}
      {showTransferModal && selectedStaff && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0,0,0,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 100,
          padding: 16
        }}>
          <div style={{
            backgroundColor: "#FFFFFF",
            borderRadius: 16,
            width: "100%",
            maxWidth: 480,
            padding: 24,
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
          }}>
            <h2 style={{ margin: "0 0 4px", fontSize: 18, fontWeight: 700 }}>
              Transfer Assignment: {selectedStaff.staff_id}
            </h2>
            <p style={{ margin: "0 0 16px", fontSize: 13, color: "var(--text-secondary)" }}>
              Reassign staff to a new PHC or coverage village. Past clinical history remains attributed to this staff member.
            </p>

            {modalError && (
              <div style={{ backgroundColor: "#FDECEC", color: "#C62828", padding: 10, borderRadius: 6, marginBottom: 12, fontSize: 13 }}>
                {modalError}
              </div>
            )}

            <form onSubmit={handleTransferSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>Target PHC / Facility</label>
                <select
                  value={transferForm.facility_id}
                  onChange={(e) => setTransferForm({ ...transferForm, facility_id: e.target.value })}
                  style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px" }}
                >
                  {facilities.map(f => (
                    <option key={f.id} value={f.id}>{f.name} ({f.facility_type})</option>
                  ))}
                </select>
              </div>

              {selectedStaff.role === "ASHA_WORKER" && (
                <div>
                  <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>New Assigned Village</label>
                  <select
                    value={transferForm.village_name}
                    onChange={(e) => setTransferForm({ ...transferForm, village_name: e.target.value })}
                    style={{ width: "100%", height: 38, borderRadius: 6, border: "1px solid var(--border)", padding: "0 8px" }}
                  >
                    {villages.map(v => (
                      <option key={v.id || v.name} value={v.name}>{v.name}</option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>Transfer Reason</label>
                <textarea
                  rows={2}
                  value={transferForm.reason}
                  onChange={(e) => setTransferForm({ ...transferForm, reason: e.target.value })}
                  placeholder="Administrative relocation / coverage rebalance"
                  style={{ width: "100%", borderRadius: 6, border: "1px solid var(--border)", padding: 8, boxSizing: "border-box", fontSize: 13 }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 14 }}>
                <button
                  type="button"
                  onClick={() => setShowTransferModal(false)}
                  style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  style={{ padding: "8px 18px", borderRadius: 6, border: "none", backgroundColor: "var(--primary)", color: "#FFFFFF", fontWeight: 600, cursor: "pointer" }}
                >
                  Confirm Transfer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- SUSPEND MODAL --- */}
      {showSuspendModal && selectedStaff && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0,0,0,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 100,
          padding: 16
        }}>
          <div style={{
            backgroundColor: "#FFFFFF",
            borderRadius: 16,
            width: "100%",
            maxWidth: 440,
            padding: 24,
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
          }}>
            <h2 style={{ margin: "0 0 6px", fontSize: 18, fontWeight: 700, color: "#991B1B" }}>
              Suspend Staff Account?
            </h2>
            <p style={{ margin: "0 0 14px", fontSize: 13, color: "var(--text-secondary)" }}>
              Suspension immediately revokes login access and token validation for <strong>{selectedStaff.name}</strong> ({selectedStaff.staff_id}). Historical medical records will remain intact.
            </p>

            {modalError && (
              <div style={{ backgroundColor: "#FDECEC", color: "#C62828", padding: 10, borderRadius: 6, marginBottom: 12, fontSize: 13 }}>
                {modalError}
              </div>
            )}

            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 4 }}>
                Suspension Reason (Optional)
              </label>
              <textarea
                rows={2}
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
                placeholder="Reason for administrative suspension"
                style={{ width: "100%", borderRadius: 6, border: "1px solid var(--border)", padding: 8, boxSizing: "border-box", fontSize: 13 }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                type="button"
                onClick={() => setShowSuspendModal(false)}
                style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSuspend}
                disabled={actionLoading}
                style={{ padding: "8px 18px", borderRadius: 6, border: "none", backgroundColor: "#DC2626", color: "#FFFFFF", fontWeight: 600, cursor: "pointer" }}
              >
                Suspend Account
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- RESET PASSWORD MODAL --- */}
      {showResetModal && selectedStaff && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0,0,0,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 100,
          padding: 16
        }}>
          <div style={{
            backgroundColor: "#FFFFFF",
            borderRadius: 16,
            width: "100%",
            maxWidth: 440,
            padding: 24,
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
          }}>
            <h2 style={{ margin: "0 0 6px", fontSize: 18, fontWeight: 700 }}>
              Reset Staff Password
            </h2>
            <p style={{ margin: "0 0 16px", fontSize: 13, color: "var(--text-secondary)" }}>
              Generate a new temporary password for <strong>{selectedStaff.name}</strong> ({selectedStaff.staff_id}). The staff member will be forced to change it upon next sign-in.
            </p>

            {modalError && (
              <div style={{ backgroundColor: "#FDECEC", color: "#C62828", padding: 10, borderRadius: 6, marginBottom: 12, fontSize: 13 }}>
                {modalError}
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                type="button"
                onClick={() => setShowResetModal(false)}
                style={{ padding: "8px 16px", borderRadius: 6, border: "1px solid var(--border)", backgroundColor: "var(--surface)", cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleResetPassword}
                disabled={actionLoading}
                style={{ padding: "8px 18px", borderRadius: 6, border: "none", backgroundColor: "var(--primary)", color: "#FFFFFF", fontWeight: 600, cursor: "pointer" }}
              >
                Generate New Password
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
