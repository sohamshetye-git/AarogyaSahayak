import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { UserRole } from "@aarogya/shared-types";
import {
  HomeIcon,
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

interface LayoutProps {
  children: React.ReactNode;
  pageTitle?: string;
  onBack?: () => void;
}

export function AppLayout({ children, pageTitle, onBack }: LayoutProps) {
  const { user, logout, checkPendingOfflineData, logoutWithChoice } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 900);
  const [isOnline] = useState(true);
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [pendingStats, setPendingStats] = useState({ pendingCount: 0, draftsCount: 0 });
  const [isSyncingLogout, setIsSyncingLogout] = useState(false);

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

  // Role-specific navigation items
  let navItems: { path: string; label: string; Icon: React.FC<any> }[] = [];

  if (role === UserRole.ASHA_WORKER) {
    navItems = [
      { path: "/asha/dashboard", label: "Home", Icon: HomeIcon },
      { path: "/asha/tasks", label: "Tasks", Icon: TasksIcon },
      { path: "/asha/followups", label: "Follow-ups", Icon: StethoscopeIcon },
      { path: "/asha/visit", label: "Field Visit", Icon: VisitIcon },
      { path: "/asha/people", label: "People", Icon: PeopleIcon },
      { path: "/asha/schemes", label: "Schemes", Icon: SchemeIcon },
      { path: "/asha/offline", label: "Offline", Icon: CloudOffIcon },
      { path: "/asha/notifications", label: "Alerts", Icon: NotificationIcon },
    ];
  } else if (role === UserRole.PHC_DOCTOR) {
    navItems = [
      { path: "/doctor/dashboard", label: "Dashboard", Icon: HomeIcon },
      { path: "/doctor/referrals", label: "Referral Queue", Icon: StethoscopeIcon },
      { path: "/doctor/consultation", label: "Consultation", Icon: ActivityIcon },
      { path: "/doctor/patients", label: "Patients", Icon: PeopleIcon },
      { path: "/doctor/prescriptions", label: "Prescriptions", Icon: PillIcon },
      { path: "/doctor/reports", label: "Reports", Icon: ShieldCheckIcon },
    ];
  } else if (role === UserRole.DISTRICT_ADMIN) {
    navItems = [
      { path: "/admin/dashboard", label: "Overview", Icon: HomeIcon },
      { path: "/admin/alerts", label: "Cluster Alerts", Icon: ActivityIcon },
      { path: "/admin/referrals", label: "Referral Trends", Icon: TrendingUpIcon },
      { path: "/admin/schemes", label: "Scheme Analytics", Icon: SchemeIcon },
      { path: "/admin/system-health", label: "System Health", Icon: ShieldCheckIcon },
    ];
  }

  const roleLabel = 
    role === UserRole.ASHA_WORKER ? "ASHA Worker" :
    role === UserRole.PHC_DOCTOR ? "PHC Medical Officer" : "District Health Officer";

  const handleLogout = () => {
    logout();
    navigate("/login");
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
              {pageTitle || "Aarogya Sahayak"}
            </h1>
            <p style={{ margin: 0, fontSize: 11, color: "var(--text-secondary)" }}>
              {user?.name || "Staff"} · {roleLabel}
            </p>
          </div>
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
              Aarogya Sahayak
            </div>
            <div style={{ fontSize: 12, color: "var(--primary)", fontWeight: 600 }}>
              {roleLabel}
            </div>
          </div>
        </div>

        {/* User Card */}
        <div style={{ padding: "16px 24px", backgroundColor: "var(--primary-light)", margin: "16px", borderRadius: 10 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--primary-dark)" }}>
            {user?.name || "Staff Member"}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
            {user?.facility_name || "Kalyanpur Health Center"}
          </div>
          <div style={{ marginTop: 8 }}>
            <OnlineStatusBadge isOnline={isOnline} />
          </div>
        </div>

        {/* Nav Links */}
        <nav style={{ flex: 1, padding: "8px 16px", display: "flex", flexDirection: "column", gap: 4 }}>
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  display: "flex",
                  alignItems: "center",
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
                <item.Icon size={20} color={isActive ? "var(--primary)" : "var(--text-secondary)"} />
                <span>{item.label}</span>
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
            <span>Sign Out</span>
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
              {pageTitle || "Dashboard"}
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              Official National Health Mission Integration
            </div>
            <div style={{ width: 1, height: 24, backgroundColor: "var(--divider)" }} />
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
              {new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
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
