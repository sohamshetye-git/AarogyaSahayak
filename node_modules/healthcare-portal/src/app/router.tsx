import React from "react";
import { Routes, Route, Navigate, Outlet } from "react-router-dom";
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
import { AshaPeopleScreen, AshaSchemesScreen, AshaOfflineScreen, AshaNotificationsScreen } from "../features/asha/SecondaryScreens";

// Doctor Feature Screens
import { DoctorDashboardScreen } from "../features/doctor/DoctorDashboardScreen";
import { DoctorConsultationScreen } from "../features/doctor/DoctorConsultationScreen";
import { DoctorReferralQueueScreen, DoctorPatientsScreen } from "../features/doctor/SecondaryScreens";

// Admin Feature Screens
import { AdminDashboardScreen } from "../features/admin/AdminDashboardScreen";
import { AdminReferralAnalyticsScreen, AdminSchemeAnalyticsScreen, AdminSystemHealthScreen } from "../features/admin/SecondaryScreens";

// Role Protected Wrapper
function ProtectedRoute({ allowedRoles }: { allowedRoles?: UserRole[] }) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div style={{ padding: 40, textAlign: "center" }}>Authenticating session...</div>;
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role as UserRole) && user.role !== UserRole.SYSTEM_ADMIN) {
    if (user.role === UserRole.ASHA_WORKER) return <Navigate to="/asha/dashboard" replace />;
    if (user.role === UserRole.PHC_DOCTOR) return <Navigate to="/doctor/dashboard" replace />;
    if (user.role === UserRole.DISTRICT_ADMIN) return <Navigate to="/admin/dashboard" replace />;
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
    if (user.role === UserRole.PHC_DOCTOR) return "/doctor/dashboard";
    if (user.role === UserRole.DISTRICT_ADMIN) return "/admin/dashboard";
    return "/asha/dashboard";
  };

  return (
    <Routes>
      <Route path="/login" element={<LoginScreen />} />

      {/* ASHA Routes */}
      <Route element={<ProtectedRoute allowedRoles={[UserRole.ASHA_WORKER]} />}>
        <Route path="/asha/dashboard" element={<AshaDashboardScreen />} />
        <Route path="/asha/tasks" element={<AshaTasksScreen />} />
        <Route path="/asha/followups" element={<AshaFollowupsScreen />} />
        <Route path="/asha/cases/:caseId" element={<AshaCitizenCaseScreen />} />
        <Route path="/asha/visit" element={<AshaFieldVisitScreen />} />
        <Route path="/asha/people" element={<AshaPeopleScreen />} />
        <Route path="/asha/schemes" element={<AshaSchemesScreen />} />
        <Route path="/asha/offline" element={<AshaOfflineScreen />} />
        <Route path="/asha/notifications" element={<AshaNotificationsScreen />} />
      </Route>

      {/* Doctor Routes */}
      <Route element={<ProtectedRoute allowedRoles={[UserRole.PHC_DOCTOR]} />}>
        <Route path="/doctor/dashboard" element={<DoctorDashboardScreen />} />
        <Route path="/doctor/referrals" element={<DoctorReferralQueueScreen />} />
        <Route path="/doctor/consultation" element={<DoctorConsultationScreen />} />
        <Route path="/doctor/patients" element={<DoctorPatientsScreen />} />
        <Route path="/doctor/prescriptions" element={<DoctorReferralQueueScreen />} />
        <Route path="/doctor/reports" element={<DoctorPatientsScreen />} />
      </Route>

      {/* District Admin Routes */}
      <Route element={<ProtectedRoute allowedRoles={[UserRole.DISTRICT_ADMIN]} />}>
        <Route path="/admin/dashboard" element={<AdminDashboardScreen />} />
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
