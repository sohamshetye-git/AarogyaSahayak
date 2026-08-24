import React, { useState } from "react";
import type { Screen } from "../types";
import {
  HomeIcon,
  TasksIcon,
  PeopleIcon,
  MoreIcon,
  NotificationIcon,
  SearchIcon,
  HospitalIcon,
  DocumentIcon,
  SchemeIcon,
  CloudOffIcon,
  HelpIcon,
  LanguageIcon,
  LogoutIcon,
  VisitIcon,
  ReportIcon,
} from "./Icons";
import { OnlineStatus } from "./StatusBadge";

interface LayoutProps {
  children: React.ReactNode;
  currentScreen: Screen;
  onNavigate: (screen: Screen) => void;
  pageTitle?: string;
  onBack?: () => void;
  isOnline?: boolean;
  lastSync?: string;
  workerName?: string;
  village?: string;
}

type NavItem = { key: Screen; label: string; Icon: React.FC<{ size?: number; className?: string }> };

const bottomNavItems: NavItem[] = [
  { key: "dashboard", label: "Home", Icon: HomeIcon },
  { key: "tasks", label: "Tasks", Icon: TasksIcon },
  { key: "field-visit", label: "Visit", Icon: VisitIcon },
  { key: "people", label: "People", Icon: PeopleIcon },
  { key: "notifications", label: "More", Icon: MoreIcon },
];

const sidebarItems: NavItem[] = [
  { key: "dashboard", label: "Home", Icon: HomeIcon },
  { key: "tasks", label: "Tasks", Icon: TasksIcon },
  { key: "field-visit", label: "Start visit", Icon: VisitIcon },
  { key: "people", label: "People", Icon: PeopleIcon },
  { key: "schemes", label: "Schemes", Icon: SchemeIcon },
  { key: "offline", label: "Offline data", Icon: CloudOffIcon },
  { key: "notifications", label: "Notifications", Icon: NotificationIcon },
];

export function MobileLayout({
  children,
  currentScreen,
  onNavigate,
  pageTitle,
  onBack,
  isOnline = true,
  lastSync,
}: LayoutProps) {
  const showBottomNav = !["login", "field-visit", "citizen-case"].includes(currentScreen);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100dvh", backgroundColor: "var(--bg)", overflow: "hidden" }}>
      {/* Top App Bar */}
      {currentScreen !== "login" && (
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
          {onBack ? (
            <button
              onClick={onBack}
              style={{
                width: 40,
                height: 40,
                borderRadius: "50%",
                border: "none",
                background: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--text-primary)",
                flexShrink: 0,
              }}
              aria-label="Go back"
            >
              ←
            </button>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 8,
                  backgroundColor: "var(--primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <HospitalIcon size={16} className="" style={{ color: "white" }} />
              </div>
            </div>
          )}
          <span
            style={{
              flex: 1,
              fontWeight: 600,
              fontSize: 17,
              color: "var(--text-primary)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {pageTitle || "Aarogya Sahayak"}
          </span>
          <button
            onClick={() => onNavigate("notifications")}
            style={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              border: "none",
              background: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-secondary)",
              position: "relative",
            }}
            aria-label="Notifications"
          >
            <NotificationIcon size={22} />
            <span
              style={{
                position: "absolute",
                top: 8,
                right: 8,
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: "var(--urgent)",
                border: "2px solid white",
              }}
              aria-label="New notifications"
            />
          </button>
        </header>
      )}

      {/* Offline Banner */}
      {!isOnline && currentScreen !== "login" && (
        <div
          style={{
            backgroundColor: "var(--offline-bg)",
            color: "var(--offline)",
            padding: "8px 16px",
            fontSize: 13,
            fontWeight: 500,
            display: "flex",
            alignItems: "center",
            gap: 8,
            flexShrink: 0,
          }}
          role="alert"
        >
          <CloudOffIcon size={16} />
          <span>You are offline. Your information is safe on this device.</span>
          {lastSync && <span style={{ marginLeft: "auto", fontSize: 12, opacity: 0.8 }}>Synced {lastSync}</span>}
        </div>
      )}

      {/* Content */}
      <main style={{ flex: 1, overflow: "auto" }} id="main-content">
        {children}
      </main>

      {/* Bottom Navigation */}
      {showBottomNav && (
        <nav
          style={{
            height: 68,
            backgroundColor: "var(--surface)",
            borderTop: "1px solid var(--divider)",
            display: "flex",
            alignItems: "center",
            flexShrink: 0,
            zIndex: 10,
          }}
          aria-label="Main navigation"
        >
          {bottomNavItems.map(({ key, label, Icon }) => {
            const active = currentScreen === key;
            return (
              <button
                key={key}
                onClick={() => onNavigate(key)}
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 3,
                  height: "100%",
                  border: "none",
                  background: "none",
                  cursor: "pointer",
                  color: active ? "var(--primary)" : "var(--text-secondary)",
                  padding: 0,
                  minWidth: 48,
                }}
                aria-label={label}
                aria-current={active ? "page" : undefined}
              >
                <Icon size={active ? 24 : 22} />
                <span style={{ fontSize: 10, fontWeight: active ? 600 : 400, lineHeight: "14px" }}>
                  {label}
                </span>
              </button>
            );
          })}
        </nav>
      )}
    </div>
  );
}

interface DesktopLayoutProps extends LayoutProps {
  searchQuery?: string;
  onSearchChange?: (q: string) => void;
}

export function DesktopLayout({
  children,
  currentScreen,
  onNavigate,
  pageTitle,
  isOnline = true,
  lastSync,
  workerName = "Sita Devi",
  village = "Kalyanpur Village",
  searchQuery = "",
  onSearchChange,
}: DesktopLayoutProps) {
  const [sidebarExpanded, setSidebarExpanded] = useState(true);

  if (currentScreen === "login") {
    return <>{children}</>;
  }

  return (
    <div style={{ display: "flex", height: "100dvh", backgroundColor: "var(--bg)", overflow: "hidden" }}>
      {/* Sidebar */}
      <aside
        style={{
          width: sidebarExpanded ? 240 : 72,
          backgroundColor: "var(--surface)",
          borderRight: "1px solid var(--divider)",
          display: "flex",
          flexDirection: "column",
          flexShrink: 0,
          transition: "width 200ms ease",
          overflow: "hidden",
          zIndex: 20,
        }}
        aria-label="Sidebar navigation"
      >
        {/* Logo */}
        <div style={{ padding: "20px 16px 16px", borderBottom: "1px solid var(--divider)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                backgroundColor: "var(--primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <HospitalIcon size={20} />
            </div>
            {sidebarExpanded && (
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", lineHeight: "18px" }}>
                  Aarogya Sahayak
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)", fontWeight: 500 }}>
                  ASHA Copilot
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Nav Items */}
        <nav style={{ flex: 1, padding: "12px 8px", overflow: "auto" }}>
          {sidebarItems.map(({ key, label, Icon }) => {
            const active = currentScreen === key;
            return (
              <button
                key={key}
                onClick={() => onNavigate(key)}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: sidebarExpanded ? "10px 12px" : "10px",
                  borderRadius: 10,
                  border: "none",
                  cursor: "pointer",
                  backgroundColor: active ? "var(--primary-light)" : "transparent",
                  color: active ? "var(--primary)" : "var(--text-secondary)",
                  fontWeight: active ? 600 : 400,
                  fontSize: 14,
                  marginBottom: 2,
                  textAlign: "left",
                  justifyContent: sidebarExpanded ? "flex-start" : "center",
                  transition: "background-color 150ms",
                }}
                aria-label={label}
                aria-current={active ? "page" : undefined}
                title={!sidebarExpanded ? label : undefined}
              >
                <Icon size={20} />
                {sidebarExpanded && <span>{label}</span>}
              </button>
            );
          })}
        </nav>

        {/* Bottom section */}
        <div style={{ borderTop: "1px solid var(--divider)", padding: "12px 8px" }}>
          {sidebarExpanded && (
            <div style={{ padding: "8px 12px 12px", display: "flex", alignItems: "center", gap: 10 }}>
              <div
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: "50%",
                  backgroundColor: "var(--primary-light)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: 14,
                  color: "var(--primary)",
                  flexShrink: 0,
                }}
              >
                {workerName.charAt(0)}
              </div>
              <div style={{ overflow: "hidden" }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {workerName}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{village}</div>
              </div>
            </div>
          )}
          <button
            onClick={() => {}}
            style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: sidebarExpanded ? "flex-start" : "center", gap: 12, padding: "8px 12px", borderRadius: 8, border: "none", background: "none", cursor: "pointer", color: "var(--text-secondary)", fontSize: 14 }}
            title="Change language"
          >
            <LanguageIcon size={18} />
            {sidebarExpanded && <span>Language</span>}
          </button>
          <button
            onClick={() => onNavigate("login")}
            style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: sidebarExpanded ? "flex-start" : "center", gap: 12, padding: "8px 12px", borderRadius: 8, border: "none", background: "none", cursor: "pointer", color: "var(--text-secondary)", fontSize: 14 }}
            title="Sign out"
          >
            <LogoutIcon size={18} />
            {sidebarExpanded && <span>Sign out</span>}
          </button>
        </div>
      </aside>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Top App Bar */}
        <header
          style={{
            height: 64,
            backgroundColor: "var(--surface)",
            borderBottom: "1px solid var(--divider)",
            display: "flex",
            alignItems: "center",
            padding: "0 32px",
            gap: 16,
            flexShrink: 0,
          }}
        >
          <button
            onClick={() => setSidebarExpanded(!sidebarExpanded)}
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-secondary)",
              flexShrink: 0,
            }}
            aria-label="Toggle sidebar"
          >
            ☰
          </button>

          <h1 style={{ fontSize: 18, fontWeight: 600, color: "var(--text-primary)", margin: 0, flex: 1 }}>
            {pageTitle || "Dashboard"}
          </h1>

          {/* Search */}
          <div style={{ position: "relative", width: 280 }}>
            <SearchIcon
              size={18}
              style={{
                position: "absolute",
                left: 12,
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--text-disabled)",
              }}
            />
            <input
              type="search"
              placeholder="Search citizen or task"
              value={searchQuery}
              onChange={(e) => onSearchChange?.(e.target.value)}
              style={{
                width: "100%",
                height: 40,
                paddingLeft: 40,
                paddingRight: 12,
                border: "1px solid var(--border)",
                borderRadius: 10,
                fontSize: 14,
                color: "var(--text-primary)",
                backgroundColor: "var(--bg)",
                outline: "none",
              }}
              aria-label="Search citizen or task"
            />
          </div>

          <OnlineStatus online={isOnline} lastSync={lastSync} />

          <button
            onClick={() => onNavigate("notifications")}
            style={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              border: "1px solid var(--border)",
              background: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-secondary)",
              position: "relative",
            }}
            aria-label="Notifications"
          >
            <NotificationIcon size={20} />
            <span
              style={{
                position: "absolute",
                top: 8,
                right: 8,
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: "var(--urgent)",
                border: "2px solid white",
              }}
            />
          </button>

          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              backgroundColor: "var(--primary-light)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: 15,
              color: "var(--primary)",
              cursor: "pointer",
            }}
            aria-label={`Profile: ${workerName}`}
          >
            {workerName.charAt(0)}
          </div>
        </header>

        {/* Offline Banner */}
        {!isOnline && (
          <div
            style={{
              backgroundColor: "var(--offline-bg)",
              color: "var(--offline)",
              padding: "8px 32px",
              fontSize: 13,
              fontWeight: 500,
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexShrink: 0,
            }}
            role="alert"
          >
            <CloudOffIcon size={16} />
            <span>
              You are offline. You can continue field visits. Information will sync when connectivity returns.
            </span>
            {lastSync && (
              <span style={{ marginLeft: "auto", fontSize: 12 }}>Last synced: {lastSync}</span>
            )}
          </div>
        )}

        {/* Content */}
        <main style={{ flex: 1, overflow: "auto" }} id="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
