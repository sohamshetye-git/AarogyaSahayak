import React, { useEffect, useState } from "react";
import { LocationService, LocationState, LocationSource } from "@aarogya/location";
import { apiClient } from "@aarogya/api-client";
import { useLanguage } from "../context/LanguageContext";
import { MapPinIcon, ShieldCheckIcon, WarningIcon } from "./Icons";

interface LocationChipProps {
  userRole?: string;
  defaultVillage?: string;
  defaultFacility?: string;
  isMobile?: boolean;
}

export const LocationChip: React.FC<LocationChipProps> = ({
  userRole,
  defaultVillage = "Assigned Village",
  defaultFacility = "Assigned PHC",
  isMobile = false,
}) => {
  const { t, locale } = useLanguage();
  const [locationState, setLocationState] = useState<LocationState>(() => LocationService.getState());
  const [showDrawer, setShowDrawer] = useState(false);
  const [showManualModal, setShowManualModal] = useState(false);
  const [showDiagnosticModal, setShowDiagnosticModal] = useState(false);
  const [manualInput, setManualInput] = useState("");
  const [isLocating, setIsLocating] = useState(false);

  const roleStr = String(userRole || "").toUpperCase();
  const isAdmin = roleStr.includes("ADMIN") || roleStr === "DISTRICT_ADMIN";
  const isDoctor = roleStr.includes("DOCTOR") || roleStr === "PHC_DOCTOR";
  const isAsha = roleStr.includes("ASHA") || roleStr === "ASHA_WORKER";

  useEffect(() => {
    // Canonical POST /api/locations/reverse-geocode provider configuration
    LocationService.setReverseGeocodeProvider(async (lat: number, lng: number, accuracy?: number | null, capturedAt?: string | null) => {
      try {
        const res = await apiClient.reverseGeocodeLocation(lat, lng, locale || "mr-IN", accuracy, capturedAt);
        return res?.data || res;
      } catch (err) {
        console.warn("Reverse geocode provider failed:", err);
        return null;
      }
    });

    const unsubscribe = LocationService.subscribeToLocationState((st) => {
      setLocationState(st);
    });

    return () => unsubscribe();
  }, [locale]);

  const handleRefresh = async (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (isLocating) return;
    setIsLocating(true);
    try {
      await LocationService.refreshCurrentLocation();
    } catch (err) {
      console.warn("Location refresh error:", err);
    } finally {
      setIsLocating(false);
    }
  };

  const handleUseLastKnown = () => {
    LocationService.useLastKnownLocation();
    setShowDrawer(false);
  };

  const handleUseRegistered = () => {
    const registeredName = isDoctor ? defaultFacility : defaultVillage;
    LocationService.selectManualLocation({
      village: registeredName,
      formatted_address: registeredName,
      source: isDoctor ? "ASSIGNED_FACILITY" : "REGISTERED_HOME",
      latitude: 18.5204,
      longitude: 73.8567,
    });
    setShowDrawer(false);
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualInput.trim()) return;

    LocationService.selectManualLocation({
      village: manualInput.trim(),
      formatted_address: manualInput.trim(),
      source: "MANUAL_VILLAGE",
      latitude: 18.5204,
      longitude: 73.8567,
    });
    setShowManualModal(false);
    setShowDrawer(false);
    setManualInput("");
  };

  if (isAdmin) {
    return (
      <div
        id="location-badge-admin"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          padding: "4px 10px",
          backgroundColor: "var(--neutral-bg)",
          borderRadius: 8,
          border: "1px solid var(--border)",
          fontSize: 12,
          color: "var(--text-secondary)",
          fontWeight: 600,
          whiteSpace: "nowrap",
        }}
      >
        <MapPinIcon size={14} color="var(--primary)" />
        <span>Jurisdiction: District 04 · Maharashtra</span>
      </div>
    );
  }

  const loc = locationState.currentLocation;
  const isGps = loc?.source === "DEVICE_GPS";
  const isLastKnown = loc?.source === "LAST_KNOWN" || (!loc && !!locationState.cachedLocation);
  const isManual = loc?.source === "MANUAL_VILLAGE" || loc?.source === "MANUAL_PINCODE" || loc?.source === "MAP_SELECTED";
  const isAssigned = loc?.source === "ASSIGNED_FACILITY" || loc?.source === "REGISTERED_HOME" || !loc;

  const reactiveState = locationState.reactiveState;
  const accuracy = loc?.accuracy_meters;
  const isLowAccuracy = accuracy != null && accuracy > 100;
  const isAddressFailed = reactiveState === "REVERSE_GEOCODE_FAILED";
  const isErrorState = reactiveState === "PERMISSION_DENIED" || reactiveState === "TIMEOUT" || reactiveState === "UNAVAILABLE" || reactiveState === "ERROR";

  // Compute Source Badge Label
  let sourceBadge = t("location.registered_location", "Registered");
  if (isDoctor && (isAssigned || !loc)) {
    sourceBadge = t("location.assigned_phc", "Assigned PHC");
  } else if (isGps) {
    sourceBadge = t("location.current_gps", "Current GPS");
  } else if (isLastKnown) {
    sourceBadge = t("location.last_known", "Last Known");
  } else if (isManual) {
    sourceBadge = t("location.manually_selected", "Manual");
  }

  // Compute Badge Colors
  // Green: GPS and address successfully resolved
  // Amber: GPS acquired but low accuracy or address unresolved
  // Grey: registered / assigned / last-known
  // Red: permission denied, unavailable or error
  let badgeBg = "var(--surface)";
  let badgeBorder = "1px solid var(--border)";
  let iconColor = "var(--primary)";
  let pillBg = "#E2E8F0";
  let pillColor = "#475569";

  if (isErrorState) {
    badgeBg = "#FEF2F2";
    badgeBorder = "1px solid #FECACA";
    iconColor = "#DC2626";
    pillBg = "#FEE2E2";
    pillColor = "#991B1B";
  } else if (isGps) {
    if (isLowAccuracy || isAddressFailed) {
      badgeBg = "#FFFBEB";
      badgeBorder = "1px solid #FCD34D";
      iconColor = "#D97706";
      pillBg = "#FEF3C7";
      pillColor = "#B45309";
    } else {
      badgeBg = "#F0FDF4";
      badgeBorder = "1px solid #86EFAC";
      iconColor = "#16A34A";
      pillBg = "#DCFCE7";
      pillColor = "#15803D";
    }
  } else if (isLastKnown) {
    badgeBg = "#F8FAFC";
    badgeBorder = "1px solid #CBD5E1";
    iconColor = "#64748B";
    pillBg = "#E2E8F0";
    pillColor = "#475569";
  }

  // Address Display Text
  let addressDisplay = isDoctor ? defaultFacility : defaultVillage;
  if (loc?.formatted_address && !loc.formatted_address.includes("Address unavailable")) {
    addressDisplay = loc.formatted_address;
  } else if (loc?.village) {
    addressDisplay = loc.village;
  } else if (isAddressFailed && isGps) {
    addressDisplay = t("location.gps_acquired_no_address", "GPS acquired, address could not be resolved");
  } else if (reactiveState === "PERMISSION_DENIED") {
    addressDisplay = t("location.permission_denied_banner", "Permission denied");
  }

  const registeredLocationName = isDoctor ? defaultFacility : defaultVillage;
  const capturedFormatted = loc?.captured_at
    ? new Date(loc.captured_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <>
      {/* Header Compact Location Chip Indicator */}
      <div
        id="portal-location-chip"
        onClick={() => setShowDrawer(true)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          padding: "5px 12px",
          backgroundColor: badgeBg,
          border: badgeBorder,
          borderRadius: 8,
          fontSize: 12,
          cursor: "pointer",
          maxWidth: isMobile ? 220 : 380,
          transition: "all 120ms ease",
          userSelect: "none",
        }}
        title={t("location.location_management", "Click to manage location")}
      >
        <MapPinIcon size={15} color={iconColor} />

        <div style={{ display: "flex", alignItems: "center", gap: 6, overflow: "hidden", whiteSpace: "nowrap" }}>
          <span
            id="location-source-badge"
            style={{
              padding: "2px 6px",
              borderRadius: 4,
              fontSize: 10,
              fontWeight: 800,
              backgroundColor: pillBg,
              color: pillColor,
              flexShrink: 0,
            }}
          >
            {sourceBadge}
          </span>

          <span
            id="location-address-text"
            style={{
              fontWeight: 600,
              color: "var(--text-primary)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {addressDisplay}
          </span>

          {accuracy != null && isGps && (
            <span
              id="location-accuracy-pill"
              style={{
                fontSize: 11,
                color: isLowAccuracy ? "#D97706" : "var(--text-secondary)",
                flexShrink: 0,
                fontWeight: 600,
              }}
            >
              (±{Math.round(accuracy)}m)
            </span>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: "auto", flexShrink: 0 }}>
          <button
            type="button"
            id="location-chip-refresh-btn"
            onClick={handleRefresh}
            disabled={isLocating}
            style={{
              background: "none",
              border: "none",
              cursor: isLocating ? "not-allowed" : "pointer",
              fontSize: 11,
              fontWeight: 700,
              color: "var(--primary)",
              padding: "2px 4px",
              display: "flex",
              alignItems: "center",
              gap: 2,
            }}
            title={t("location.refresh_location", "Refresh Location")}
          >
            {isLocating ? "⏳" : "🔄"} {t("common.refresh", "Refresh")}
          </button>
        </div>
      </div>

      {/* Location Management Modal */}
      {showDrawer && (
        <div
          id="location-management-modal-backdrop"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: 16,
          }}
          onClick={() => setShowDrawer(false)}
        >
          <div
            id="location-management-modal"
            style={{
              backgroundColor: "var(--surface)",
              borderRadius: 16,
              width: "100%",
              maxWidth: 480,
              maxHeight: "90vh",
              overflowY: "auto",
              padding: 24,
              boxShadow: "0 12px 36px rgba(0,0,0,0.18)",
              border: "1px solid var(--border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <MapPinIcon size={20} color="var(--primary)" />
                <h3 style={{ margin: 0, fontSize: 17, fontWeight: 800, color: "var(--text-primary)" }}>
                  {t("location.location_management", "Location Management")}
                </h3>
              </div>
              <button
                type="button"
                id="location-modal-close-btn"
                onClick={() => setShowDrawer(false)}
                style={{
                  background: "none",
                  border: "none",
                  fontSize: 18,
                  cursor: "pointer",
                  color: "var(--text-secondary)",
                }}
              >
                ✕
              </button>
            </div>

            {/* Active Position Info Card */}
            <div
              id="active-location-card"
              style={{
                backgroundColor: isGps ? (isLowAccuracy || isAddressFailed ? "#FFFBEB" : "#F0FDF4") : "#F8FAFC",
                border: isGps ? (isLowAccuracy || isAddressFailed ? "1.5px solid #FCD34D" : "1.5px solid #86EFAC") : "1.5px solid var(--border)",
                borderRadius: 12,
                padding: 16,
                marginBottom: 16,
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span
                  style={{
                    padding: "2px 8px",
                    borderRadius: 6,
                    fontSize: 11,
                    fontWeight: 800,
                    backgroundColor: pillBg,
                    color: pillColor,
                  }}
                >
                  {sourceBadge}
                </span>
                {capturedFormatted && (
                  <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                    {t("location.captured_at", "Captured: {{time}}", { time: capturedFormatted })}
                  </span>
                )}
              </div>

              <div id="active-location-address-detail" style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                {addressDisplay}
              </div>

              {accuracy != null && isGps && (
                <div style={{ fontSize: 12, color: isLowAccuracy ? "#D97706" : "var(--text-secondary)" }}>
                  <strong>{t("location.accuracy_meters", "Accuracy: ±{{meters}}m", { meters: Math.round(accuracy) })}</strong>
                </div>
              )}

              {/* Accuracy Warning / Improve Guidance */}
              {isLowAccuracy && isGps && (
                <div style={{ marginTop: 4, padding: "8px 10px", backgroundColor: "#FEF3C7", borderRadius: 8, fontSize: 12, color: "#92400E" }}>
                  <div style={{ fontWeight: 700, marginBottom: 2 }}>⚠️ {t("location.low_accuracy_warning", "Low accuracy GPS")}</div>
                  <div style={{ fontSize: 11 }}>
                    {t("location.low_accuracy_guidance", "Step towards an open area or confirm your village.")}
                  </div>
                </div>
              )}

              {/* Reverse Geocode Unresolved Message */}
              {isAddressFailed && isGps && (
                <div style={{ marginTop: 4, padding: "8px 10px", backgroundColor: "#FEF3C7", borderRadius: 8, fontSize: 12, color: "#92400E" }}>
                  <div style={{ fontWeight: 700 }}>⚠️ {t("location.gps_acquired_no_address", "GPS acquired, address could not be resolved")}</div>
                </div>
              )}

              <div style={{ fontSize: 12, color: "var(--text-secondary)", borderTop: "1px solid var(--divider)", paddingTop: 6, marginTop: 4 }}>
                <strong>{isDoctor ? t("location.assigned_facility", "Authorized Facility") : t("location.registered_location", "Registered Location")}:</strong> {registeredLocationName}
              </div>
            </div>

            {/* If GPS failed and cache exists: Offer last known option explicitly */}
            {!loc && locationState.cachedLocation && (
              <div style={{ padding: 12, backgroundColor: "#FEF9C3", border: "1px solid #FDE047", borderRadius: 10, marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#854D0E", marginBottom: 6 }}>
                  {t("location.last_known_location", "Last known location available. Use it?")}
                </div>
                <button
                  type="button"
                  onClick={handleUseLastKnown}
                  style={{
                    padding: "6px 12px",
                    backgroundColor: "#CA8A04",
                    color: "#FFF",
                    border: "none",
                    borderRadius: 6,
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  {t("location.last_known", "Use Last Known Position")}
                </button>
              </div>
            )}

            {/* Action Buttons Grid */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <button
                type="button"
                id="acquire-fresh-gps-btn"
                onClick={handleRefresh}
                disabled={isLocating}
                style={{
                  width: "100%",
                  minHeight: 48,
                  padding: "10px 16px",
                  backgroundColor: "var(--primary)",
                  color: "#FFF",
                  border: "none",
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: isLocating ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                }}
              >
                {isLocating ? `⏳ ${t("location.acquiring_gps", "Acquiring fresh GPS...")}` : `🛰️ ${t("location.acquire_fresh_gps", "Acquire Fresh GPS Location")}`}
              </button>

              <button
                type="button"
                id="use-registered-btn"
                onClick={handleUseRegistered}
                style={{
                  width: "100%",
                  minHeight: 48,
                  padding: "10px 16px",
                  backgroundColor: "var(--surface)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border)",
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                🏛️ {isDoctor ? t("location.use_assigned_phc", "Use Assigned PHC") : t("location.use_registered_location", "Use Registered Location")} ({registeredLocationName})
              </button>

              <button
                type="button"
                id="enter-manual-location-btn"
                onClick={() => setShowManualModal(true)}
                style={{
                  width: "100%",
                  minHeight: 48,
                  padding: "10px 16px",
                  backgroundColor: "var(--surface)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border)",
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                ✏️ {t("location.enter_village_pin_facility", "Enter Village / PIN / Facility Name")}
              </button>

              {/* Developer Diagnostic Toggle */}
              <button
                type="button"
                onClick={() => setShowDiagnosticModal(!showDiagnosticModal)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-secondary)",
                  fontSize: 11,
                  cursor: "pointer",
                  marginTop: 4,
                  textAlign: "center",
                  textDecoration: "underline",
                }}
              >
                {t("location.diagnostic_info", "Location Diagnostics (Dev Panel)")}
              </button>

              {showDiagnosticModal && locationState.diagnostic && (
                <div style={{ backgroundColor: "#F1F5F9", borderRadius: 8, padding: 10, fontSize: 11, color: "#334155" }}>
                  <div><strong>Lat/Lng:</strong> {locationState.diagnostic.latitude.toFixed(6)}, {locationState.diagnostic.longitude.toFixed(6)}</div>
                  <div><strong>Accuracy:</strong> {locationState.diagnostic.accuracy_meters ? `±${Math.round(locationState.diagnostic.accuracy_meters)}m` : "N/A"}</div>
                  <div><strong>Source:</strong> {locationState.diagnostic.source}</div>
                  <div><strong>Provider:</strong> {locationState.diagnostic.provider}</div>
                  <div><strong>Permission:</strong> {locationState.diagnostic.permission_state}</div>
                  <div><strong>Captured:</strong> {locationState.diagnostic.captured_at}</div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Manual Input Dialog */}
      {showManualModal && (
        <div
          id="manual-location-modal"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 10000,
            padding: 16,
          }}
          onClick={() => setShowManualModal(false)}
        >
          <div
            style={{
              backgroundColor: "var(--surface)",
              borderRadius: 14,
              padding: 24,
              width: "100%",
              maxWidth: 400,
              boxShadow: "0 8px 30px rgba(0,0,0,0.18)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: "0 0 8px", fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
              {t("location.select_working_location", "Select Working Location")}
            </h3>
            <p style={{ margin: "0 0 16px", fontSize: 12, color: "var(--text-secondary)" }}>
              {t("location.select_working_location_desc", "Update your temporary working location for this session.")}
            </p>
            <form onSubmit={handleManualSubmit}>
              <input
                type="text"
                id="manual-location-input"
                value={manualInput}
                onChange={(e) => setManualInput(e.target.value)}
                placeholder="e.g. Ganeshpur Village or 411001"
                required
                style={{
                  width: "100%",
                  height: 44,
                  padding: "0 12px",
                  borderRadius: 8,
                  border: "1px solid var(--border)",
                  fontSize: 14,
                  marginBottom: 16,
                  outline: "none",
                }}
              />
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
                <button
                  type="button"
                  onClick={() => setShowManualModal(false)}
                  style={{
                    minHeight: 44,
                    padding: "0 16px",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                    backgroundColor: "transparent",
                    cursor: "pointer",
                    fontWeight: 600,
                  }}
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button
                  type="submit"
                  id="submit-manual-location-btn"
                  style={{
                    minHeight: 44,
                    padding: "0 18px",
                    borderRadius: 8,
                    border: "none",
                    backgroundColor: "var(--primary)",
                    color: "#FFF",
                    cursor: "pointer",
                    fontWeight: 700,
                  }}
                >
                  {t("location.set_location", "Set Location")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
