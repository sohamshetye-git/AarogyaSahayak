import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import { UserRole } from "@aarogya/shared-types";
import { formatDate, SupportedLanguage, SUPPORTED_LANGUAGES } from "@aarogya/i18n";
import {
  HomeIcon,
  UserPlusIcon,
  TasksIcon,
  VisitIcon,
  PeopleIcon,
  HospitalIcon,
  SchemeIcon,
  NotificationIcon,
  StethoscopeIcon,
  PillIcon,
  ActivityIcon,
  TrendingUpIcon,
  ShieldCheckIcon,
  CloudOffIcon,
  LogoutIcon,
  ChevronLeftIcon,
} from "../components/Icons";
import { OnlineStatusBadge } from "../components/StatusBadge";
import { UnsavedOfflineDataModal } from "../components/UnsavedOfflineDataModal";
import { LocationChip } from "../components/LocationChip";
import { connectivityService } from "../services/ConnectivityService";

interface LayoutProps {
  children: React.ReactNode;
  pageTitle?: string;
  onBack?: () => void;
}

export function AppLayout({ children, pageTitle, onBack }: LayoutProps) {
  const { user, logout, checkPendingOfflineData, logoutWithChoice } = useAuth();
  const { currentLanguage, setLanguage, t } = useLanguage();
  const location = useLocation();
  const navigate = useNavigate();
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 900);
  const [isOnline, setIsOnline] = useState(() => !connectivityService.isOffline());
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [pendingStats, setPendingStats] = useState({ pendingCount: 0, draftsCount: 0 });
  const [isSyncingLogout, setIsSyncingLogout] = useState(false);

  useEffect(() => {
    const unsub = connectivityService.subscribe((state) => {
      setIsOnline(state === "ONLINE" || state === "SYNCING");
    });
    return unsub;
  }, []);

  const handleSignOutClick = async () => {
    const stats = await checkPendingOfflineData();
    if (stats.pendingCount > 0 || stats.draftsCount > 0) {
      setPendingStats(stats);
      setShowLogoutModal(true);
    } else {
      await logout();
      navigate("/login");
    }
  };

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 900);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const role = user?.role || UserRole.ASHA_WORKER;

  // Role-specific navigation items translated via i18n
  let navItems: { path: string; label: string; Icon: React.FC<any> }[] = [];

  if (role === UserRole.ASHA_WORKER) {
    navItems = [
      { path: "/asha/dashboard", label: t("navigation.home", "Home"), Icon: HomeIcon },
      { path: "/asha/patients/new", label: t("navigation.add_patient", "Add Patient"), Icon: UserPlusIcon },
      { path: "/asha/tasks", label: t("navigation.tasks", "Tasks"), Icon: TasksIcon },
      { path: "/asha/followups", label: t("navigation.followups", "Follow-ups"), Icon: StethoscopeIcon },
      { path: "/asha/visit", label: t("navigation.field_visits", "Field Visits"), Icon: VisitIcon },
      { path: "/asha/people", label: t("navigation.people", "People"), Icon: PeopleIcon },
      { path: "/asha/schemes", label: t("navigation.schemes", "Schemes"), Icon: SchemeIcon },
      { path: "/asha/offline", label: t("common.offline", "Offline"), Icon: CloudOffIcon },
      { path: "/asha/notifications", label: t("navigation.alerts", "Alerts"), Icon: NotificationIcon },
    ];
  } else if (role === UserRole.PHC_DOCTOR) {
    navItems = [
      { path: "/doctor/dashboard", label: t("navigation.dashboard", "Dashboard"), Icon: HomeIcon },
      { path: "/doctor/direct-requests", label: t("navigation.direct_requests", "Citizen Requests"), Icon: StethoscopeIcon },
      { path: "/doctor/referrals", label: t("navigation.referrals", "Referrals"), Icon: HospitalIcon },
      { path: "/doctor/consultations", label: t("navigation.consultations", "Consultations"), Icon: ActivityIcon },
      { path: "/doctor/followups", label: t("navigation.followups", "ASHA Follow-ups"), Icon: VisitIcon },
      { path: "/doctor/patients", label: t("navigation.patients", "Patients"), Icon: PeopleIcon },
      { path: "/doctor/investigations", label: t("navigation.investigations", "Investigations"), Icon: ShieldCheckIcon },
      { path: "/doctor/prescriptions", label: t("navigation.prescriptions", "Prescriptions"), Icon: PillIcon },
      { path: "/doctor/reports", label: t("navigation.reports", "Reports"), Icon: TrendingUpIcon },
      { path: "/doctor/alerts", label: t("navigation.alerts", "Alerts"), Icon: NotificationIcon },
      { path: "/doctor/system-status", label: t("navigation.system_status", "System Status"), Icon: CloudOffIcon },
    ];
  } else if (role === UserRole.DISTRICT_ADMIN) {
    navItems = [
      { path: "/admin/dashboard", label: t("navigation.dashboard", "Overview"), Icon: HomeIcon },
      { path: "/admin/staff", label: t("navigation.staff_management", "Staff Management"), Icon: UserPlusIcon },
      { path: "/admin/alerts", label: t("navigation.cluster_alerts", "Cluster Alerts"), Icon: ActivityIcon },
      { path: "/admin/referrals", label: t("navigation.referral_trends", "Referral Trends"), Icon: TrendingUpIcon },
      { path: "/admin/schemes", label: t("navigation.scheme_analytics", "Scheme Analytics"), Icon: SchemeIcon },
      { path: "/admin/system-health", label: t("navigation.system_health", "System Health"), Icon: ShieldCheckIcon },
    ];
  }

  const roleLabel = 
    role === UserRole.ASHA_WORKER ? t("common.role_asha", "ASHA Worker") :
    role === UserRole.PHC_DOCTOR ? t("common.role_doctor", "PHC Medical Officer") : t("common.role_admin", "District Health Officer");

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const getTranslatedTitle = () => {
    if (pageTitle) return pageTitle;
    const path = location.pathname;
    if (path.includes("/asha/cases/")) return t("case.timeline", "Patient Case Review");
    if (path.includes("/asha/patients/new")) return t("navigation.add_patient", "Add Patient");
    if (path.includes("/asha/tasks")) return t("navigation.tasks", "Tasks");
    if (path.includes("/asha/followups")) return t("navigation.followups", "Follow-ups");
    if (path.includes("/asha/visit")) return t("navigation.field_visits", "Field Visits");
    if (path.includes("/asha/people")) return t("navigation.people", "People");
    if (path.includes("/asha/schemes")) return t("navigation.schemes", "Schemes");
    if (path.includes("/asha/offline")) return t("common.offline", "Offline");
    if (path.includes("/asha/notifications")) return t("navigation.alerts", "Alerts");
    if (path.includes("/doctor/referrals")) return t("navigation.referrals", "Referral Queue");
    if (path.includes("/doctor/consultation")) return t("doctor.consultation_workspace_title", "Consultation");
    if (path.includes("/doctor/patients")) return t("navigation.patients", "Patients");
    if (path.includes("/doctor/prescriptions")) return t("navigation.prescriptions", "Prescriptions");
    if (path.includes("/doctor/reports")) return t("navigation.reports", "Reports");
    if (path.includes("/admin/staff")) return t("navigation.staff_management", "Staff Management");
    if (path.includes("/admin/alerts")) return t("navigation.cluster_alerts", "Cluster Alerts");
    if (path.includes("/admin/referrals")) return t("navigation.referral_trends", "Referral Trends");
    if (path.includes("/admin/schemes")) return t("navigation.scheme_analytics", "Scheme Analytics");
    if (path.includes("/admin/system-health")) return t("navigation.system_health", "System Health");
    return t("navigation.dashboard", "Dashboard");
  };

  if (isMobile) {
    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100dvh", backgroundColor: "var(--bg)", overflow: "hidden" }}>
        {/* Mobile Top Header */}
        <header
          style={{
            height: 56,
            backgroundColor: "var(--surface)",
            borderBottom: "1px solid var(--divider)",
            display: "flex",
            alignItems: "center",
            padding: "0 16px",
            gap: 12,
            flexShrink: 0,
            zIndex: 10,
          }}
        >
          {onBack && (
            <button
              onClick={onBack}
              style={{
                width: 36,
                height: 36,
                borderRadius: "50%",
                border: "none",
                backgroundColor: "var(--neutral-bg)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
              }}
            >
              <ChevronLeftIcon size={20} color="var(--text-primary)" />
            </button>
          )}
          <div style={{ flex: 1 }}>
            <h1 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
              {getTranslatedTitle()}
            </h1>
            <p style={{ margin: 0, fontSize: 11, color: "var(--text-secondary)" }}>
              {user?.name || "Staff"} · {roleLabel}
            </p>
          </div>
          <select
            id="portal-mobile-language-select"
            value={currentLanguage}
            onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
            style={{
              fontSize: 12,
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid var(--border)",
              backgroundColor: "var(--surface)",
              color: "var(--text-primary)",
              fontWeight: 700,
              cursor: "pointer",
            }}
            title={t("common.language", "Language")}
          >
            {SUPPORTED_LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.name} ({lang.code.split("-")[0]})
              </option>
            ))}
          </select>
          <LocationChip
            userRole={user?.role}
            defaultVillage={user?.village_name || user?.coverage_area || "Assigned Village"}
            defaultFacility={user?.facility_name || "Assigned PHC"}
            isMobile={true}
          />
          <OnlineStatusBadge isOnline={isOnline} />
        </header>

        {/* Scrollable Content */}
        <main style={{ flex: 1, overflowY: "auto", WebkitOverflowScrolling: "touch" }}>
          {children}
        </main>

        {/* Mobile Bottom Navigation */}
        <nav
          style={{
            height: 64,
            backgroundColor: "var(--surface)",
            borderTop: "1px solid var(--divider)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-around",
            flexShrink: 0,
            padding: "0 4px",
            zIndex: 10,
          }}
        >
          {navItems.slice(0, 5).map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  flex: 1,
                  height: "100%",
                  textDecoration: "none",
                  color: isActive ? "var(--primary)" : "var(--text-secondary)",
                  gap: 3,
                }}
              >
                <item.Icon size={22} color={isActive ? "var(--primary)" : "var(--text-secondary)"} />
                <span style={{ fontSize: 11, fontWeight: isActive ? 700 : 500 }}>
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>
      </div>
    );
  }

  // Desktop Layout
  return (
    <div style={{ display: "flex", height: "100vh", backgroundColor: "var(--bg)", overflow: "hidden" }}>
      {/* Sidebar */}
      <aside
        style={{
          width: 260,
          backgroundColor: "var(--surface)",
          borderRight: "1px solid var(--divider)",
          display: "flex",
          flexDirection: "column",
          flexShrink: 0,
        }}
      >
        {/* Brand */}
        <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--divider)", display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              backgroundColor: "var(--primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#FFF",
              fontWeight: 700,
              fontSize: 18,
            }}
          >
            AS
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
              {t("common.app_name", "Aarogya Sahayak")}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 500 }}>
              {t("common.tagline", "AI-Powered Rural Healthcare Platform")}
            </div>
            <div style={{ fontSize: 12, color: "var(--primary)", fontWeight: 600 }}>
              {roleLabel}
            </div>
          </div>
        </div>

        {/* User Profile Card */}
        <div style={{ padding: "14px 16px", backgroundColor: "var(--primary-light)", margin: "12px 16px", borderRadius: 10, display: "flex", flexDirection: "column", gap: 8 }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--primary-dark)" }}>
              {user?.name || (role === UserRole.PHC_DOCTOR ? "PHC Doctor" : role === UserRole.DISTRICT_ADMIN ? "District Health Officer" : "ASHA Worker")}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
              <span style={{ fontWeight: 600 }}>Registered:</span> {role === UserRole.PHC_DOCTOR ? (user?.facility_name || "Primary Health Centre") : (user?.village_name || "Catchment Area")}
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
            <OnlineStatusBadge isOnline={isOnline} />
            <select
              id="portal-desktop-language-select"
              value={currentLanguage}
              onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
              style={{
                fontSize: 11,
                padding: "3px 6px",
                borderRadius: 6,
                border: "1px solid var(--border)",
                backgroundColor: "var(--surface)",
                color: "var(--text-primary)",
                fontWeight: 600,
                cursor: "pointer",
                minHeight: 28
              }}
              title={t("common.language", "Preferred Language")}
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.name} ({lang.code.split("-")[0]})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Nav Links */}
        <nav style={{ flex: 1, padding: "8px 16px", display: "flex", flexDirection: "column", gap: 4, overflowY: "auto" }}>
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            const isAlertItem = item.path === "/doctor/alerts";
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 12,
                  padding: "10px 14px",
                  borderRadius: 8,
                  textDecoration: "none",
                  fontSize: 14,
                  fontWeight: isActive ? 700 : 500,
                  backgroundColor: isActive ? "var(--primary-light)" : "transparent",
                  color: isActive ? "var(--primary-dark)" : "var(--text-primary)",
                  transition: "all 150ms ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <item.Icon size={20} color={isActive ? "var(--primary)" : "var(--text-secondary)"} />
                  <span>{item.label}</span>
                </div>
                {isAlertItem && (
                  <span
                    style={{
                      padding: "2px 8px",
                      borderRadius: 10,
                      backgroundColor: "#DC2626",
                      color: "#FFF",
                      fontSize: 11,
                      fontWeight: 800
                    }}
                  >
                    4
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Logout */}
        <div style={{ padding: "16px", borderTop: "1px solid var(--divider)" }}>
          <button
            onClick={handleSignOutClick}
            style={{
              width: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              padding: "10px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              backgroundColor: "transparent",
              color: "var(--urgent)",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <LogoutIcon size={16} color="var(--urgent)" />
            <span>{t("common.logout", "Sign Out")}</span>
          </button>
        </div>
      </aside>

      <UnsavedOfflineDataModal
        isOpen={showLogoutModal}
        pendingCount={pendingStats.pendingCount}
        draftsCount={pendingStats.draftsCount}
        isSyncing={isSyncingLogout}
        onSyncAndLogout={async () => {
          setIsSyncingLogout(true);
          try {
            await logoutWithChoice('SYNC_AND_LOGOUT');
            setShowLogoutModal(false);
            navigate('/login');
          } finally {
            setIsSyncingLogout(false);
          }
        }}
        onLogoutAndKeepData={async () => {
          await logoutWithChoice('KEEP_DATA');
          setShowLogoutModal(false);
          navigate('/login');
        }}
        onStaySignedIn={() => setShowLogoutModal(false)}
      />

      {/* Main Panel */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Top Header */}
        <header
          style={{
            height: 64,
            backgroundColor: "var(--surface)",
            borderBottom: "1px solid var(--divider)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 32px",
            flexShrink: 0,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {onBack && (
              <button
                onClick={onBack}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  border: "none",
                  backgroundColor: "var(--neutral-bg)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                }}
              >
                <ChevronLeftIcon size={20} color="var(--text-primary)" />
              </button>
            )}
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: "var(--text-primary)" }}>
              {getTranslatedTitle()}
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <LocationChip
              userRole={user?.role}
              defaultVillage={user?.village_name || user?.coverage_area || "Assigned Village"}
              defaultFacility={user?.facility_name || "Assigned PHC"}
            />
            <div style={{ width: 1, height: 24, backgroundColor: "var(--divider)" }} />
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              {t("common.app_name", "Aarogya Sahayak")} — {roleLabel}
            </div>
            <div style={{ width: 1, height: 24, backgroundColor: "var(--divider)" }} />
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
              {formatDate(new Date(), currentLanguage)}
            </div>
          </div>
        </header>

        {/* Scrollable View */}
        <main style={{ flex: 1, overflowY: "auto", padding: "24px 32px" }}>
          <div style={{ maxWidth: 1200, margin: "0 auto" }}>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

