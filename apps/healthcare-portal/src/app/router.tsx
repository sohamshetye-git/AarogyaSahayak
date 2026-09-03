import React, { useEffect } from "react";
import { Routes, Route, Navigate, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { UserRole } from "@aarogya/shared-types";
import { LoginScreen } from "../auth/LoginScreen";
import { AppLayout } from "../layouts/Layout";

// ASHA Feature Screens
import { AshaDashboardScreen } from "../features/asha/DashboardScreen";
import { AshaTasksScreen } from "../features/asha/TasksScreen";
import { AshaFollowupsScreen } from "../features/asha/FollowupsScreen";
import { AshaCitizenCaseScreen } from "../features/asha/CitizenCaseScreen";
import { AshaFieldVisitScreen } from "../features/asha/FieldVisitScreen";
import { AddPatientScreen } from "../features/asha/AddPatientScreen";
import { FollowUpDetailScreen } from "../features/asha/FollowUpDetailScreen";
import { AshaCitizenRequestDetailScreen } from "../features/asha/CitizenRequestDetailScreen";
import { AshaPeopleScreen, AshaSchemesScreen, AshaOfflineScreen, AshaNotificationsScreen } from "../features/asha/SecondaryScreens";

// Doctor Feature Screens
import { DoctorDashboardScreen } from "../features/doctor/DoctorDashboardScreen";
import { DirectCitizenRequestsScreen } from "../features/doctor/DirectCitizenRequestsScreen";
import { DoctorConsultationScreen } from "../features/doctor/DoctorConsultationScreen";
import { DoctorConsultationWorkspaceScreen } from "../features/doctor/DoctorConsultationWorkspaceScreen";
import { DoctorReferralQueueScreen } from "../features/doctor/SecondaryScreens";
import { DoctorPatientsScreen } from "../features/doctor/DoctorPatientsScreen";
import { DoctorCaseTimelineScreen } from "../features/doctor/DoctorCaseTimelineScreen";
import { DoctorActivityScreen } from "../features/doctor/DoctorActivityScreen";
import { DoctorFollowupsScreen } from "../features/doctor/DoctorFollowupsScreen";
import { DoctorPatientRecordScreen } from "../features/doctor/DoctorPatientRecordScreen";
import { DoctorFollowUpDetailScreen } from "../features/doctor/DoctorFollowUpDetailScreen";
import { DoctorInvestigationsScreen } from "../features/doctor/DoctorInvestigationsScreen";
import { DoctorInvestigationDetailScreen } from "../features/doctor/DoctorInvestigationDetailScreen";
import { DoctorPrescriptionsScreen } from "../features/doctor/DoctorPrescriptionsScreen";
import { DoctorPrescriptionDetailScreen } from "../features/doctor/DoctorPrescriptionDetailScreen";
import { DoctorReportsScreen } from "../features/doctor/DoctorReportsScreen";
import { DoctorAlertsScreen } from "../features/doctor/DoctorAlertsScreen";
import { DoctorAlertDetailScreen } from "../features/doctor/DoctorAlertDetailScreen";

// Admin Feature Screens
import { AdminDashboardScreen } from "../features/admin/AdminDashboardScreen";
import { StaffManagementScreen } from "../features/admin/StaffManagementScreen";
import { AdminReferralAnalyticsScreen, AdminSchemeAnalyticsScreen, AdminSystemHealthScreen } from "../features/admin/SecondaryScreens";
import { ChangePasswordScreen } from "../auth/ChangePasswordScreen";

// Login wrapper that automatically redirects if authenticated
function PublicLoginRoute() {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated && user) {
      if (user.must_change_password) {
        navigate("/auth/change-password", { replace: true });
        return;
      }
      const uRole = String(user.role).toUpperCase();
      if (uRole === "PHC_DOCTOR" || uRole.includes("DOCTOR")) {
        navigate("/doctor/dashboard", { replace: true });
      } else if (uRole === "DISTRICT_ADMIN" || uRole.includes("ADMIN")) {
        navigate("/admin/dashboard", { replace: true });
      } else {
        navigate("/asha/dashboard", { replace: true });
      }
    }
  }, [isAuthenticated, user, navigate]);

  return <LoginScreen />;
}

// Role Protected Wrapper
function ProtectedRoute({ allowedRoles }: { allowedRoles?: UserRole[] }) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div style={{ padding: 40, textAlign: "center" }}>Authenticating session...</div>;
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (user.must_change_password) {
    return <Navigate to="/auth/change-password" replace />;
  }

  const uRole = String(user.role).toUpperCase();
  if (allowedRoles && !allowedRoles.some(r => String(r).toUpperCase() === uRole) && uRole !== "SYSTEM_ADMIN") {
    if (uRole === "ASHA_WORKER" || uRole.includes("ASHA")) return <Navigate to="/asha/dashboard" replace />;
    if (uRole === "PHC_DOCTOR" || uRole.includes("DOCTOR")) return <Navigate to="/doctor/dashboard" replace />;
    if (uRole === "DISTRICT_ADMIN" || uRole.includes("ADMIN")) return <Navigate to="/admin/dashboard" replace />;
  }

  return (
    <AppLayout>
      <Outlet />
    </AppLayout>
  );
}

export function AppRouter() {
  const { isAuthenticated, user } = useAuth();

  const getDefaultRedirect = () => {
    if (!isAuthenticated || !user) return "/login";
    const uRole = String(user.role).toUpperCase();
    if (uRole === "PHC_DOCTOR" || uRole.includes("DOCTOR")) return "/doctor/dashboard";
    if (uRole === "DISTRICT_ADMIN" || uRole.includes("ADMIN")) return "/admin/dashboard";
    return "/asha/dashboard";
  };

  return (
    <Routes>
      <Route path="/login" element={<PublicLoginRoute />} />
      <Route path="/auth/change-password" element={<ChangePasswordScreen />} />

      {/* ASHA Routes */}
      <Route element={<ProtectedRoute allowedRoles={[UserRole.ASHA_WORKER]} />}>
        <Route path="/asha/dashboard" element={<AshaDashboardScreen />} />
        <Route path="/asha/patients/new" element={<AddPatientScreen />} />
        <Route path="/asha/add-patient" element={<AddPatientScreen />} />
        <Route path="/asha/tasks" element={<AshaTasksScreen />} />
        <Route path="/asha/followups" element={<AshaFollowupsScreen />} />
        <Route path="/asha/followups/:id" element={<FollowUpDetailScreen />} />
        <Route path="/asha/citizen-requests/:requestId" element={<AshaCitizenRequestDetailScreen />} />
        <Route path="/asha/cases/:caseId" element={<AshaCitizenCaseScreen />} />
        <Route path="/asha/visit" element={<AshaFieldVisitScreen />} />
        <Route path="/asha/visits" element={<AshaFieldVisitScreen />} />
        <Route path="/asha/people" element={<AshaPeopleScreen />} />
        <Route path="/asha/schemes" element={<AshaSchemesScreen />} />
        <Route path="/asha/offline" element={<AshaOfflineScreen />} />
        <Route path="/asha/notifications" element={<AshaNotificationsScreen />} />
      </Route>

      {/* Doctor Routes */}
      <Route element={<ProtectedRoute allowedRoles={[UserRole.PHC_DOCTOR]} />}>
        <Route path="/doctor/dashboard" element={<DoctorDashboardScreen />} />
        <Route path="/doctor/direct-requests" element={<DirectCitizenRequestsScreen />} />
        <Route path="/doctor/referrals" element={<DoctorReferralQueueScreen />} />
        <Route path="/doctor/consultation" element={<DoctorConsultationWorkspaceScreen />} />
        <Route path="/doctor/consultations" element={<DoctorConsultationWorkspaceScreen />} />
        <Route path="/doctor/consultations/:consultationId" element={<DoctorConsultationScreen />} />
        <Route path="/doctor/referrals/:referralId" element={<DoctorConsultationScreen />} />
        <Route path="/doctor/cases/:caseId/timeline" element={<DoctorCaseTimelineScreen />} />
        <Route path="/doctor/followups" element={<DoctorFollowupsScreen />} />
        <Route path="/doctor/followups/:followUpId" element={<DoctorFollowUpDetailScreen />} />
        <Route path="/doctor/patients" element={<DoctorPatientsScreen />} />
        <Route path="/doctor/patients/:citizenId" element={<DoctorPatientRecordScreen />} />
        <Route path="/doctor/patients/:patientProfileId" element={<DoctorPatientRecordScreen />} />
        <Route path="/doctor/investigations" element={<DoctorInvestigationsScreen />} />
        <Route path="/doctor/investigations/:investigationId" element={<DoctorInvestigationDetailScreen />} />
        <Route path="/doctor/prescriptions" element={<DoctorPrescriptionsScreen />} />
        <Route path="/doctor/prescriptions/:prescriptionId" element={<DoctorPrescriptionDetailScreen />} />
        <Route path="/doctor/reports" element={<DoctorReportsScreen />} />
        <Route path="/doctor/reports/:reportType" element={<DoctorReportsScreen />} />
        <Route path="/doctor/alerts" element={<DoctorAlertsScreen />} />
        <Route path="/doctor/alerts/:alertId" element={<DoctorAlertDetailScreen />} />
        <Route path="/doctor/system-status" element={<DoctorPatientsScreen />} />
        <Route path="/doctor/activity" element={<DoctorActivityScreen />} />
      </Route>

      {/* District Admin Routes */}
      <Route element={<ProtectedRoute allowedRoles={[UserRole.DISTRICT_ADMIN]} />}>
        <Route path="/admin/dashboard" element={<AdminDashboardScreen />} />
        <Route path="/admin/staff" element={<StaffManagementScreen />} />
        <Route path="/admin/alerts" element={<AdminDashboardScreen />} />
        <Route path="/admin/referrals" element={<AdminReferralAnalyticsScreen />} />
        <Route path="/admin/schemes" element={<AdminSchemeAnalyticsScreen />} />
        <Route path="/admin/system-health" element={<AdminSystemHealthScreen />} />
      </Route>

      {/* Default Catch-all */}
      <Route path="*" element={<Navigate to={getDefaultRedirect()} replace />} />
    </Routes>
  );
}
