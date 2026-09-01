import {
  LocationData,
  LocationDiagnostic,
  LocationReactiveState,
  LocationSource,
  LocationState,
  ReverseGeocodeResult
} from "./locationTypes";
import {
  getCachedLocation,
  setCachedLocation,
  clearCachedLocation,
  isLocationFresh,
  getCacheAgeSeconds
} from "./locationCache";
import {
  checkLocationPermission,
  requestNativeOrWebPermission
} from "./permissions";

type LocationListener = (state: LocationState) => void;

class LocationServiceClass {
  private currentUserId: string | null = null;
  private currentUserRole: string | null = null;

  private state: LocationState = {
    currentLocation: null,
    cachedLocation: null,
    reactiveState: "IDLE",
    errorMessage: null,
    permissionStatus: "prompt",
    isFresh: false,
    lastUpdated: null,
    diagnostic: null
  };

  private listeners: Set<LocationListener> = new Set();
  private reverseGeocodeProvider: ((lat: number, lng: number, accuracy?: number | null, captured_at?: string | null) => Promise<ReverseGeocodeResult | null>) | null = null;

  constructor() {
    this.init();
  }

  public setUserContext(userId: string | null, role: string | null) {
    this.currentUserId = userId;
    this.currentUserRole = role;

    // Load scoped cache for this user/role
    const cached = getCachedLocation(this.currentUserId, this.currentUserRole);
    this.state.cachedLocation = cached;
    this.state.currentLocation = null; // Do NOT automatically assume cached data is current GPS
    this.state.isFresh = false;
    this.state.lastUpdated = cached?.captured_at || null;
    this.updateDiagnostic(cached, true);
    this.notify();
  }

  private async init() {
    const perm = await checkLocationPermission();
    this.state.permissionStatus = perm;
    const cached = getCachedLocation(this.currentUserId, this.currentUserRole);
    if (cached) {
      this.state.cachedLocation = cached;
      this.state.isFresh = isLocationFresh(cached);
      this.state.lastUpdated = cached.captured_at;
      this.updateDiagnostic(cached, true);
    }
    this.notify();
  }

  public setReverseGeocodeProvider(provider: (lat: number, lng: number, accuracy?: number | null, captured_at?: string | null) => Promise<ReverseGeocodeResult | null>) {
    this.reverseGeocodeProvider = provider;
  }

  public getState(): LocationState {
    return { ...this.state };
  }

  public subscribeToLocationState(listener: LocationListener): () => void {
    this.listeners.add(listener);
    listener(this.getState());
    return () => {
      this.listeners.delete(listener);
    };
  }

  private updateState(partial: Partial<LocationState>) {
    this.state = { ...this.state, ...partial };
    this.notify();
  }

  private updateDiagnostic(loc: LocationData | null, isCached: boolean, resolvedAt?: string | null) {
    if (!loc) {
      this.state.diagnostic = null;
      return;
    }
    const diagnostic: LocationDiagnostic = {
      source: loc.source,
      latitude: loc.latitude,
      longitude: loc.longitude,
      accuracy_meters: loc.accuracy_meters,
      captured_at: loc.captured_at,
      resolved_at: resolvedAt || loc.captured_at,
      is_cached: isCached,
      cache_age_seconds: getCacheAgeSeconds(loc),
      permission_state: this.state.permissionStatus,
      provider: loc.provider || "Browser Geolocation API"
    };
    this.state.diagnostic = diagnostic;
  }

  private notify() {
    const currentState = this.getState();
    this.listeners.forEach((fn) => fn(currentState));
  }

  public async getCurrentLocation(forceRefresh = false): Promise<LocationData | null> {
    if (!forceRefresh && this.state.currentLocation && isLocationFresh(this.state.currentLocation)) {
      return this.state.currentLocation;
    }

    if (typeof navigator === "undefined" || !navigator.geolocation) {
      this.updateState({
        reactiveState: "UNAVAILABLE",
        errorMessage: "Geolocation is not supported on this device/browser.",
        permissionStatus: "unavailable"
      });
      return null;
    }

    this.updateState({
      reactiveState: "REQUESTING_PERMISSION",
      errorMessage: null
    });

    await requestNativeOrWebPermission();

    this.updateState({
      reactiveState: "LOCATING"
    });

    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          const accuracy = position.coords.accuracy;
          const altitude = position.coords.altitude;

          // Reject impossible or malformed coordinates
          if (!isFinite(lat) || !isFinite(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180 || accuracy < 0) {
            this.updateState({
              reactiveState: "ERROR",
              errorMessage: "Invalid coordinates received from GPS sensor."
            });
            resolve(null);
            return;
          }

          const capturedAt = new Date().toISOString();
          const baseLoc: LocationData = {
            latitude: lat,
            longitude: lng,
            accuracy_meters: accuracy,
            altitude_meters: altitude,
            captured_at: capturedAt,
            source: "DEVICE_GPS",
            formatted_address: null,
            village: null,
            pincode: null,
            block: null,
            district: null,
            state: null,
            place_id: null,
            is_confirmed: false,
            provider: "Browser Geolocation Sensor"
          };

          // Accuracy evaluation rules:
          // ≤100m: Ready
          // 101–500m: Low accuracy
          // >500m: Very low accuracy
          let reactiveState: LocationReactiveState = "READY";
          let accuracyWarning: string | null = null;
          if (accuracy > 500) {
            reactiveState = "VERY_LOW_ACCURACY";
            accuracyWarning = `GPS accuracy is very low (±${Math.round(accuracy)}m). Please confirm or enter your village.`;
          } else if (accuracy > 100) {
            reactiveState = "LOW_ACCURACY";
            accuracyWarning = `GPS accuracy is low (±${Math.round(accuracy)}m).`;
          }

          this.updateState({
            reactiveState: "RESOLVING_ADDRESS"
          });

          let finalLoc = baseLoc;
          let resolvedTime: string | null = null;
          let addressResolved = false;

          if (this.reverseGeocodeProvider) {
            try {
              const geo = await this.reverseGeocodeProvider(lat, lng, accuracy, capturedAt);
              resolvedTime = geo?.resolved_at || new Date().toISOString();
              if (geo && geo.formatted_address && !geo.formatted_address.includes("Address unavailable")) {
                addressResolved = true;
                finalLoc = {
                  ...baseLoc,
                  formatted_address: geo.formatted_address,
                  village: geo.village || geo.locality || null,
                  pincode: geo.postal_code || geo.pincode || null,
                  block: geo.block || null,
                  district: geo.district || null,
                  state: geo.state || null,
                  place_id: geo.place_id || null,
                  provider: geo.provider || geo.source || "Google Reverse Geocoding"
                };
              } else {
                finalLoc = {
                  ...baseLoc,
                  formatted_address: `GPS (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
                  provider: "Device GPS Sensor"
                };
                if (reactiveState === "READY") {
                  reactiveState = "REVERSE_GEOCODE_FAILED";
                }
              }
            } catch (err) {
              console.warn("Reverse geocoding error:", err);
              finalLoc = {
                ...baseLoc,
                formatted_address: `GPS (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
                provider: "Device GPS Sensor"
              };
              if (reactiveState === "READY") {
                reactiveState = "REVERSE_GEOCODE_FAILED";
              }
            }
          } else {
            finalLoc = {
              ...baseLoc,
              formatted_address: `GPS (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
              provider: "Device GPS Sensor"
            };
          }

          setCachedLocation(finalLoc, this.currentUserId, this.currentUserRole);
          this.updateDiagnostic(finalLoc, false, resolvedTime);

          this.updateState({
            currentLocation: finalLoc,
            cachedLocation: finalLoc,
            reactiveState,
            permissionStatus: "granted",
            isFresh: true,
            lastUpdated: capturedAt,
            errorMessage: accuracyWarning
          });

          resolve(finalLoc);
        },
        (err) => {
          let reactiveState: LocationReactiveState = "ERROR";
          let message = "Failed to obtain current GPS location.";
          let permStatus = this.state.permissionStatus;

          if (err.code === err.PERMISSION_DENIED) {
            reactiveState = "PERMISSION_DENIED";
            permStatus = "denied";
            message = "Location permission denied. Enter your village/PIN or select on map.";
          } else if (err.code === err.TIMEOUT) {
            reactiveState = "TIMEOUT";
            message = "Location request timed out. Please try again or enter your village/PIN.";
          } else if (err.code === err.POSITION_UNAVAILABLE) {
            reactiveState = "UNAVAILABLE";
            message = "Location sensor is unavailable on this device.";
          }

          this.updateState({
            reactiveState,
            permissionStatus: permStatus,
            errorMessage: message
          });
          resolve(null);
        },
        {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 0 // Always fresh position request
        }
      );
    });
  }

  public async refreshCurrentLocation(): Promise<LocationData | null> {
    return this.getCurrentLocation(true);
  }

  public useLastKnownLocation(): LocationData | null {
    const cached = getCachedLocation(this.currentUserId, this.currentUserRole);
    if (!cached) return null;

    const lastKnownLoc: LocationData = {
      ...cached,
      source: "LAST_KNOWN"
    };

    this.updateDiagnostic(lastKnownLoc, true);

    this.updateState({
      currentLocation: lastKnownLoc,
      reactiveState: "READY",
      isFresh: false,
      lastUpdated: lastKnownLoc.captured_at,
      errorMessage: null
    });

    return lastKnownLoc;
  }

  public selectManualLocation(data: {
    village?: string | null;
    pincode?: string | null;
    block?: string | null;
    district?: string | null;
    state?: string | null;
    latitude?: number;
    longitude?: number;
    formatted_address?: string | null;
    source?: LocationSource;
  }): LocationData {
    const capturedAt = new Date().toISOString();
    const loc: LocationData = {
      latitude: data.latitude ?? 18.5204,
      longitude: data.longitude ?? 73.8567,
      accuracy_meters: null,
      altitude_meters: null,
      captured_at: capturedAt,
      source: data.source || (data.village ? "MANUAL_VILLAGE" : "MANUAL_PINCODE"),
      formatted_address: data.formatted_address || (data.village ? `${data.village}, ${data.pincode || ""}`.trim() : data.pincode || "Manual location"),
      village: data.village || null,
      pincode: data.pincode || null,
      block: data.block || null,
      district: data.district || null,
      state: data.state || null,
      place_id: null,
      is_confirmed: true,
      provider: "Manual User Selection"
    };

    setCachedLocation(loc, this.currentUserId, this.currentUserRole);
    this.updateDiagnostic(loc, false, capturedAt);

    this.updateState({
      currentLocation: loc,
      cachedLocation: loc,
      reactiveState: "READY",
      isFresh: true,
      lastUpdated: loc.captured_at,
      errorMessage: null
    });

    return loc;
  }

  public clearTemporaryLocation() {
    clearCachedLocation(this.currentUserId, this.currentUserRole);
    this.updateState({
      currentLocation: null,
      cachedLocation: null,
      reactiveState: "IDLE",
      isFresh: false,
      lastUpdated: null,
      errorMessage: null,
      diagnostic: null
    });
  }
}

export const LocationService = new LocationServiceClass();
