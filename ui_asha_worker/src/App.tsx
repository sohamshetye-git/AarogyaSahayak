import React, { useState } from "react";
import type { Screen } from "./types";
import { MobileLayout, DesktopLayout } from "./components/Layout";
import LoginScreen from "./screens/LoginScreen";
import DashboardScreen from "./screens/DashboardScreen";
import TasksScreen from "./screens/TasksScreen";
import CitizenCaseScreen from "./screens/CitizenCaseScreen";
import FieldVisitScreen from "./screens/FieldVisitScreen";
import PeopleScreen from "./screens/PeopleScreen";
import SchemesScreen from "./screens/SchemesScreen";
import NotificationsScreen from "./screens/NotificationsScreen";
import OfflineScreen from "./screens/OfflineScreen";
import ReferralScreen from "./screens/ReferralScreen";

const PAGE_TITLES: Partial<Record<Screen, string>> = {
  dashboard: "Home",
  tasks: "Tasks",
  "field-visit": "Field visit",
  people: "People",
  schemes: "Health schemes",
  notifications: "Notifications",
  offline: "Offline data",
  "citizen-case": "Case details",
  referral: "Refer to facility",
};

function useResponsive() {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 900);
  React.useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 900);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);
  return isMobile;
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("login");
  const [history, setHistory] = useState<Screen[]>([]);
  const [isOnline] = useState(true);
  const isMobile = useResponsive();

  const navigate = (next: Screen) => {
    setHistory((h) => [...h, screen]);
    setScreen(next);
  };

  const goBack = () => {
    const prev = history[history.length - 1];
    if (prev) {
      setHistory((h) => h.slice(0, -1));
      setScreen(prev);
    } else {
      setScreen("dashboard");
    }
  };

  const showBack = history.length > 0 && !["dashboard", "tasks", "people", "schemes", "notifications", "offline", "login"].includes(screen);

  const contentProps = {
    currentScreen: screen,
    onNavigate: navigate,
    isOnline,
    lastSync: "10:42 AM",
    pageTitle: PAGE_TITLES[screen],
    onBack: showBack ? goBack : undefined,
  };

  const renderScreen = () => {
    switch (screen) {
      case "login":
        return <LoginScreen onLogin={() => { setHistory([]); setScreen("dashboard"); }} />;
      case "dashboard":
        return <DashboardScreen onNavigate={navigate} isOnline={isOnline} />;
      case "tasks":
        return <TasksScreen onNavigate={navigate} />;
      case "citizen-case":
        return <CitizenCaseScreen onNavigate={navigate} onBack={goBack} />;
      case "field-visit":
        return <FieldVisitScreen onNavigate={navigate} onBack={goBack} />;
      case "people":
        return <PeopleScreen onNavigate={navigate} />;
      case "schemes":
        return <SchemesScreen />;
      case "notifications":
        return <NotificationsScreen onNavigate={navigate} />;
      case "offline":
        return <OfflineScreen />;
      case "referral":
        return <ReferralScreen onNavigate={navigate} onBack={goBack} />;
      default:
        return <DashboardScreen onNavigate={navigate} isOnline={isOnline} />;
    }
  };

  if (screen === "login") {
    return <LoginScreen onLogin={() => { setHistory([]); setScreen("dashboard"); }} />;
  }

  if (isMobile) {
    return (
      <MobileLayout {...contentProps}>
        {renderScreen()}
      </MobileLayout>
    );
  }

  return (
    <DesktopLayout {...contentProps} workerName="Sita Devi" village="Kalyanpur Village">
      <div style={{ maxWidth: 960, padding: "24px 32px" }}>
        {renderScreen()}
      </div>
    </DesktopLayout>
  );
}
