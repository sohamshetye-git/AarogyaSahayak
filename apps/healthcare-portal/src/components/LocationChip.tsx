import React, { useEffect, useState, useRef } from "react";
import { LocationService, LocationData, LocationState, LocationSource } from "@aarogya/location";
import { apiClient } from "@aarogya/api-client";
import { MapPinIcon, ShieldCheckIcon, WarningIcon } from "./Icons";

interface LocationChipProps {
  userRole?: string;
  defaultVillage?: string;
  defaultFacility?: string;
  isMobile?: boolean;
}

export const LocationChip: React.FC<LocationChipProps> = ({
  userRole,
  defaultVillage = "Kalyanpur Village",
  defaultFacility = "Kalyanpur PHC",
  isMobile = false,
}) => {
  const [locationState, setLocationState] = useState<LocationState>(() => LocationService.getState());
  const [showDrawer, setShowDrawer] = useState(false);
  const [showManualModal, setShowManualModal] = useState(false);
  const [manualInput, setManualInput] = useState("");
  const [isLocating, setIsLocating] = useState(false);
  const [hasPromptedGps, setHasPromptedGps] = useState(false);
  const [accuracyGuidanceOpen, setAccuracyGuidanceOpen] = useState(false);

  useEffect(() => {
    LocationService.setReverseGeocodeProvider(async (lat: number, lng: number) => {
      try {
        const res = await apiClient.get<any>("/locations/reverse-geocode", { latitude: lat, longitude: lng });
        return res?.data || res;
      } catch (err) {
        console.warn("Reverse geocode failed:", err);
        return null;
      }
    });

    const unsubscribe = LocationService.subscribeToLocationState((st) => {
      setLocationState(st);
    });

    return () => unsubscribe();
  }, []);

  // Post-login lifecycle: request GPS asynchronously without blocking login
  useEffect(() => {
    const roleStr = String(userRole || "").toUpperCase();
    if (roleStr.includes("ADMIN") || roleStr === "DISTRICT_ADMIN") {
      return;
    }

    if (!hasPromptedGps && !locationState.currentLocation) {
      setHasPromptedGps(true);
      LocationService.getCurrentLocation(false).catch((e) => {
        console.warn("Async location request error:", e);
      });
    }
  }, [userRole, hasPromptedGps, locationState.currentLocation]);

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
    const roleStr = String(userRole || "").toUpperCase();
    const registeredName = roleStr.includes("DOCTOR") ? defaultFacility : defaultVillage;
    LocationService.selectManualLocation({
      village: registeredName,
      formatted_address: registeredName,
      source: roleStr.includes("DOCTOR") ? "ASSIGNED_FACILITY" : "REGISTERED_HOME",
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

  const roleStr = String(userRole || "").toUpperCase();
  const isAdmin = roleStr.includes("ADMIN") || roleStr === "DISTRICT_ADMIN";
  const isDoctor = roleStr.includes("DOCTOR") || roleStr === "PHC_DOCTOR";

  if (isAdmin) {
    return (
      <div
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

  let sourceBadge = "Registered";
  if (isGps) sourceBadge = "Current GPS";
  else if (isLastKnown) sourceBadge = "Last Known";
  else if (isManual) sourceBadge = "Manual";

  let addressDisplay = isDoctor ? defaultFacility : defaultVillage;
  if (loc?.formatted_address) {
    addressDisplay = loc.formatted_address;
  } else if (loc?.village) {
    addressDisplay = loc.village;
  }

  const registeredLocationName = isDoctor ? defaultFacility : defaultVillage;
  const accuracy = loc?.accuracy_meters;
  const isLowAccuracy = accuracy != null && accuracy > 100 && accuracy <= 500;
  const isVeryLowAccuracy = accuracy != null && accuracy > 500;

  const capturedFormatted = loc?.captured_at
    ? new Date(loc.captured_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <>
      {/* Header Compact Control */}
      <div
        onClick={() => setShowDrawer(true)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          padding: "4px 12px",
          backgroundColor: isGps ? "#F0FDF4" : isLowAccuracy || isVeryLowAccuracy ? "#FFFBEB" : "var(--surface)",
          border: isGps ? "1px solid #86EFAC" : isLowAccuracy || isVeryLowAccuracy ? "1px solid #FCD34D" : "1px solid var(--border)",
          borderRadius: 8,
          fontSize: 12,
          cursor: "pointer",
          maxWidth: isMobile ? 220 : 380,
          transition: "all 120ms ease",
          userSelect: "none",
        }}
        title="Click to view location details, switch to GPS, or select manual location"
      >
        <MapPinIcon size={15} color={isGps ? "#16A34A" : isLowAccuracy || isVeryLowAccuracy ? "#D97706" : "var(--primary)"} />

        <div style={{ display: "flex", alignItems: "center", gap: 6, overflow: "hidden", whiteSpace: "nowrap" }}>
          <span
            style={{
              padding: "1px 6px",
              borderRadius: 4,
              fontSize: 10,
              fontWeight: 800,
              backgroundColor: isGps ? "#DCFCE7" : isLastKnown ? "#FEF3C7" : "#E2E8F0",
              color: isGps ? "#15803D" : isLastKnown ? "#B45309" : "#475569",
              flexShrink: 0,
            }}
          >
            {sourceBadge}
          </span>

          <span
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
            <span style={{ fontSize: 11, color: isVeryLowAccuracy ? "#DC2626" : isLowAccuracy ? "#D97706" : "var(--text-secondary)", flexShrink: 0 }}>
              (±{Math.round(accuracy)}m)
            </span>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: "auto", flexShrink: 0 }}>
          <button
            type="button"
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
            title="Request fresh high-accuracy position"
          >
            {isLocating ? "⏳" : "🔄"} Refresh
          </button>
        </div>
      </div>

      {/* Location Details Popover / Drawer */}
      {showDrawer && (
        <div
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
                  Location Management
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowDrawer(false)}
                style={{ background: "none", border: "none", fontSize: 18, cursor: "pointer", color: "var(--text-secondary)" }}
              >
                ✕
              </button>
            </div>

            {/* Active Position Info Card */}
            <div
              style={{
                backgroundColor: isGps ? "#F0FDF4" : "#F8FAFC",
                border: isGps ? "1.5px solid #86EFAC" : "1.5px solid var(--border)",
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
                    backgroundColor: isGps ? "#DCFCE7" : "#E2E8F0",
                    color: isGps ? "#15803D" : "#334155",
                  }}
                >
                  {sourceBadge}
                </span>
                {capturedFormatted && (
                  <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                    Captured: {capturedFormatted}
                  </span>
                )}
              </div>

              <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                {addressDisplay}
              </div>

              {accuracy != null && (
                <div style={{ fontSize: 12, color: isVeryLowAccuracy ? "#DC2626" : isLowAccuracy ? "#D97706" : "var(--text-secondary)" }}>
                  <strong>Accuracy:</strong> approximately {Math.round(accuracy)} metres
                </div>
              )}

              {/* Accuracy Warning / Improve Guidance */}
              {(isLowAccuracy || isVeryLowAccuracy) && (
                <div style={{ marginTop: 4, padding: "8px 10px", backgroundColor: "#FEF3C7", borderRadius: 8, fontSize: 12, color: "#92400E" }}>
                  <div style={{ fontWeight: 700, marginBottom: 2 }}>⚠️ GPS accuracy is degraded</div>
                  <div style={{ fontSize: 11 }}>
                    Enable precise location on your device or step towards an open area.
                  </div>
                </div>
              )}

              <div style={{ fontSize: 12, color: "var(--text-secondary)", borderTop: "1px solid var(--divider)", paddingTop: 6, marginTop: 4 }}>
                <strong>Registered Location:</strong> {registeredLocationName}
              </div>
            </div>

            {/* If GPS failed and cache exists: Offer last known option explicitly */}
            {!loc && locationState.cachedLocation && (
              <div style={{ padding: 12, backgroundColor: "#FEF9C3", border: "1px solid #FDE047", borderRadius: 10, marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#854D0E", marginBottom: 6 }}>
                  Current GPS is unavailable. Use last known location?
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
                  Use Last Known Position
                </button>
              </div>
            )}

            {/* Action Buttons Grid */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <button
                type="button"
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
                {isLocating ? "⏳ Acquiring fresh GPS..." : "🛰️ Acquire Fresh GPS Location"}
              </button>

              <button
                type="button"
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
                🏛️ Use Registered ({registeredLocationName})
              </button>

              <button
                type="button"
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
                ✏️ Enter Village / PIN / Facility Name
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manual Input Dialog */}
      {showManualModal && (
        <div
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
              Select Working Location
            </h3>
            <p style={{ margin: "0 0 16px", fontSize: 12, color: "var(--text-secondary)" }}>
              Update your temporary working location for this session. This will not modify your permanent registered jurisdiction.
            </p>
            <form onSubmit={handleManualSubmit}>
              <input
                type="text"
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
                  Cancel
                </button>
                <button
                  type="submit"
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
                  Set Location
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
