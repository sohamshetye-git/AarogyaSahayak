import React, { useEffect, useRef, useState } from "react";
import { MapPin, Navigation, Compass, AlertCircle, RefreshCw, ZoomIn, ZoomOut, CheckCircle2 } from "lucide-react";
import { loadGoogleMapsScript } from "../services/googleMapsLoader";
import { FacilitySearchResultItem } from "@aarogya/shared-types";

interface GoogleMapViewProps {
  userLocation: { latitude: number; longitude: number; source?: string } | null;
  facilities: FacilitySearchResultItem[];
  selectedFacilityId: string | null;
  onSelectFacility: (facility: FacilitySearchResultItem) => void;
  onSearchArea?: (lat: number, lng: number) => void;
  searchRadiusMeters?: number;
}

export const GoogleMapView: React.FC<GoogleMapViewProps> = ({
  userLocation,
  facilities,
  selectedFacilityId,
  onSelectFacility,
  onSearchArea,
  searchRadiusMeters = 10000
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const userMarkerRef = useRef<any>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [hasGoogleSDK, setHasGoogleSDK] = useState(false);
  const [mapMoved, setMapMoved] = useState(false);
  const [centerCoords, setCenterCoords] = useState<{ lat: number; lng: number } | null>(null);

  const defaultCenter = userLocation
    ? { lat: userLocation.latitude, lng: userLocation.longitude }
    : { lat: 18.5204, lng: 73.8567 };

  useEffect(() => {
    loadGoogleMapsScript().then(() => {
      const g = (window as any).google;
      if (g && g.maps) {
        setHasGoogleSDK(true);
      } else {
        setHasGoogleSDK(false);
      }
      setMapLoaded(true);
    });
  }, []);

  // Initialize Native Google Map
  useEffect(() => {
    if (!hasGoogleSDK || !mapContainerRef.current || mapInstanceRef.current) return;

    const g = (window as any).google;
    const map = new g.maps.Map(mapContainerRef.current, {
      center: defaultCenter,
      zoom: 12,
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: false,
      zoomControl: false,
      styles: [
        { featureType: "poi.medical", stylers: [{ visibility: "on" }, { color: "#2563EB" }] },
        { featureType: "poi.business", stylers: [{ visibility: "off" }] }
      ]
    });

    mapInstanceRef.current = map;

    map.addListener("dragend", () => {
      const c = map.getCenter();
      if (c) {
        setCenterCoords({ lat: c.lat(), lng: c.lng() });
        setMapMoved(true);
      }
    });
  }, [hasGoogleSDK]);

  // Update Markers & Bounds
  useEffect(() => {
    if (!hasGoogleSDK || !mapInstanceRef.current) return;
    const g = (window as any).google;
    const map = mapInstanceRef.current;

    // Clear old facility markers
    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];

    // User location marker
    if (userMarkerRef.current) {
      userMarkerRef.current.setMap(null);
    }

    if (userLocation) {
      userMarkerRef.current = new g.maps.Marker({
        position: { lat: userLocation.latitude, lng: userLocation.longitude },
        map: map,
        title: "Your Location",
        icon: {
          path: g.maps.SymbolPath.CIRCLE,
          scale: 8,
          fillColor: "#2563EB",
          fillOpacity: 1,
          strokeColor: "#FFFFFF",
          strokeWeight: 3
        },
        zIndex: 999
      });
    }

    const bounds = new g.maps.LatLngBounds();
    if (userLocation) {
      bounds.extend({ lat: userLocation.latitude, lng: userLocation.longitude });
    }

    facilities.forEach((fac, idx) => {
      const isSelected = fac.id === selectedFacilityId || fac.result_id === selectedFacilityId;
      const isGovt = fac.ownership === "GOVERNMENT" || fac.verification_status === "PROJECT_VERIFIED";
      const isEmergency = fac.emergency_capability || fac.is_24x7_emergency;

      const markerColor = isSelected ? "#2563EB" : isEmergency ? "#DC2626" : isGovt ? "#16A34A" : "#D97706";

      // Numbered SVG pin icon
      const markerSvg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="34" height="42" viewBox="0 0 34 42">
          <path d="M17 0 C7.6 0 0 7.6 0 17 C0 27.5 17 42 17 42 C17 42 34 27.5 34 17 C34 7.6 26.4 0 17 0 Z" fill="${markerColor}" stroke="#FFFFFF" stroke-width="2"/>
          <circle cx="17" cy="16" r="10" fill="#FFFFFF"/>
          <text x="17" y="20" font-size="11" font-family="Arial, sans-serif" font-weight="bold" fill="${markerColor}" text-anchor="middle">${idx + 1}</text>
        </svg>
      `;

      const marker = new g.maps.Marker({
        position: { lat: fac.latitude, lng: fac.longitude },
        map: map,
        title: fac.display_name,
        icon: {
          url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(markerSvg)}`,
          scaledSize: new g.maps.Size(isSelected ? 38 : 32, isSelected ? 46 : 40),
          anchor: new g.maps.Point(17, 42)
        },
        zIndex: isSelected ? 100 : idx + 1
      });

      marker.addListener("click", () => {
        onSelectFacility(fac);
        map.panTo({ lat: fac.latitude, lng: fac.longitude });
      });

      markersRef.current.push(marker);
      bounds.extend({ lat: fac.latitude, lng: fac.longitude });
    });

    if (facilities.length > 0) {
      map.fitBounds(bounds, { top: 40, bottom: 40, left: 40, right: 40 });
    }
  }, [hasGoogleSDK, facilities, userLocation, selectedFacilityId]);

  // Pan to selected facility if changed from outside
  useEffect(() => {
    if (!hasGoogleSDK || !mapInstanceRef.current || !selectedFacilityId) return;
    const selected = facilities.find((f) => f.id === selectedFacilityId || f.result_id === selectedFacilityId);
    if (selected) {
      mapInstanceRef.current.panTo({ lat: selected.latitude, lng: selected.longitude });
    }
  }, [selectedFacilityId]);

  const handleZoomIn = () => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setZoom(mapInstanceRef.current.getZoom() + 1);
    }
  };

  const handleZoomOut = () => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setZoom(mapInstanceRef.current.getZoom() - 1);
    }
  };

  const handleRecenter = () => {
    if (mapInstanceRef.current && userLocation) {
      mapInstanceRef.current.panTo({ lat: userLocation.latitude, lng: userLocation.longitude });
      mapInstanceRef.current.setZoom(13);
      setMapMoved(false);
    }
  };

  const handleSearchThisAreaClick = () => {
    if (centerCoords && onSearchArea) {
      onSearchArea(centerCoords.lat, centerCoords.lng);
      setMapMoved(false);
    }
  };

  return (
    <div style={{ position: "relative", width: "100%", height: 320, borderRadius: 20, overflow: "hidden", border: "1.5px solid #CBD5E1", boxShadow: "0 4px 14px rgba(0,0,0,0.06)", backgroundColor: "#E2E8F0" }}>
      {/* Real Google Map Canvas or Fallback */}
      {hasGoogleSDK ? (
        <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />
      ) : (
        /* Fallback Interactive SVG Map when browser key is pending or network is restricted */
        <div style={{ width: "100%", height: "100%", position: "relative", backgroundColor: "#EEF2F6", display: "flex", flexDirection: "column", justifyContent: "space-between", padding: 14 }}>
          {/* Top Info Banner */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", backgroundColor: "rgba(255,255,255,0.9)", padding: "6px 12px", borderRadius: 12, backdropFilter: "blur(4px)", border: "1px solid #CBD5E1", zIndex: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#1E293B", display: "flex", alignItems: "center", gap: 4 }}>
              <Compass size={14} color="#2563EB" />
              <span>Interactive Facility Radar ({facilities.length} centres)</span>
            </div>
            <div style={{ fontSize: 10, color: "#64748B" }}>
              Radius: ~{Math.round(searchRadiusMeters / 1000)} km
            </div>
          </div>

          {/* SVG Map Projection */}
          <svg style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", zIndex: 1 }}>
            {/* Grid Pattern */}
            <defs>
              <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
                <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#E2E8F0" strokeWidth="1" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />

            {/* Concentric Search Circles */}
            <circle cx="50%" cy="50%" r="50" fill="none" stroke="#BFDBFE" strokeWidth="1.5" strokeDasharray="4 3" />
            <circle cx="50%" cy="50%" r="100" fill="none" stroke="#BFDBFE" strokeWidth="1" strokeDasharray="4 3" />

            {/* User Center Pulse */}
            <circle cx="50%" cy="50%" r="12" fill="rgba(37, 99, 235, 0.2)" />
            <circle cx="50%" cy="50%" r="6" fill="#2563EB" stroke="#FFFFFF" strokeWidth="2" />

            {/* Projected Facility Markers */}
            {facilities.map((fac, idx) => {
              const isSelected = fac.id === selectedFacilityId || fac.result_id === selectedFacilityId;
              const angle = (idx * (360 / Math.max(facilities.length, 1)) - 60) * (Math.PI / 180);
              const distRadius = Math.min(120, Math.max(35, (fac.distance_km || 2) * 14));
              const cx = 50 + Math.cos(angle) * (distRadius / 3.2);
              const cy = 50 + Math.sin(angle) * (distRadius / 3.2);
              const isGovt = fac.ownership === "GOVERNMENT" || fac.verification_status === "PROJECT_VERIFIED";
              const isEmergency = fac.emergency_capability || fac.is_24x7_emergency;
              const color = isSelected ? "#2563EB" : isEmergency ? "#DC2626" : isGovt ? "#16A34A" : "#D97706";

              return (
                <g key={fac.id || idx} onClick={() => onSelectFacility(fac)} style={{ cursor: "pointer" }}>
                  <circle cx={`${cx}%`} cy={`${cy}%`} r={isSelected ? 14 : 11} fill={color} stroke="#FFFFFF" strokeWidth="2" />
                  <text x={`${cx}%`} y={`${cy + 1.2}%`} fontSize={isSelected ? "11" : "10"} fontWeight="bold" fill="#FFFFFF" textAnchor="middle">
                    {idx + 1}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Bottom Hint */}
          <div style={{ alignSelf: "center", backgroundColor: "rgba(255,255,255,0.9)", padding: "4px 10px", borderRadius: 10, fontSize: 10, color: "#64748B", border: "1px solid #CBD5E1", zIndex: 10 }}>
            Tap numbered pin to focus facility details below
          </div>
        </div>
      )}

      {/* Floating "Search this area" Button */}
      {mapMoved && (
        <button
          onClick={handleSearchThisAreaClick}
          style={{
            position: "absolute",
            top: 12,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 20,
            backgroundColor: "#2563EB",
            color: "#FFFFFF",
            padding: "8px 16px",
            borderRadius: 20,
            border: "none",
            fontSize: 12,
            fontWeight: 800,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
            boxShadow: "0 4px 12px rgba(37,99,235,0.4)"
          }}
        >
          <RefreshCw size={14} /> Search this area
        </button>
      )}

      {/* Floating Map Controls (Recenter, Zoom) */}
      <div style={{ position: "absolute", right: 12, bottom: 12, display: "flex", flexDirection: "column", gap: 6, zIndex: 20 }}>
        {userLocation && (
          <button
            onClick={handleRecenter}
            title="Recenter on my location"
            style={{ width: 36, height: 36, borderRadius: "50%", backgroundColor: "#FFFFFF", border: "1px solid #CBD5E1", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "#2563EB", boxShadow: "0 2px 8px rgba(0,0,0,0.12)" }}
          >
            <Navigation size={18} />
          </button>
        )}
        <button
          onClick={handleZoomIn}
          title="Zoom In"
          style={{ width: 36, height: 36, borderRadius: "50%", backgroundColor: "#FFFFFF", border: "1px solid #CBD5E1", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "#334155", boxShadow: "0 2px 8px rgba(0,0,0,0.12)" }}
        >
          <ZoomIn size={18} />
        </button>
        <button
          onClick={handleZoomOut}
          title="Zoom Out"
          style={{ width: 36, height: 36, borderRadius: "50%", backgroundColor: "#FFFFFF", border: "1px solid #CBD5E1", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "#334155", boxShadow: "0 2px 8px rgba(0,0,0,0.12)" }}
        >
          <ZoomOut size={18} />
        </button>
      </div>

      {/* Legend Tag in Bottom Left */}
      <div style={{ position: "absolute", left: 10, bottom: 10, backgroundColor: "rgba(255,255,255,0.92)", padding: "4px 8px", borderRadius: 8, fontSize: 10, fontWeight: 700, color: "#334155", display: "flex", gap: 8, alignItems: "center", border: "1px solid #E2E8F0", zIndex: 15 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "#16A34A" }} /> Verified Govt
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 3 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "#D97706" }} /> Google Discovered
        </span>
      </div>
    </div>
  );
};
