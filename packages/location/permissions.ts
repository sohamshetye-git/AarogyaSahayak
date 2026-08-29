/**
 * Runtime location permission handler for Web and Capacitor
 */

export type PermissionStateResult = "prompt" | "granted" | "denied" | "unavailable";

export async function checkLocationPermission(): Promise<PermissionStateResult> {
  // 1. Check if Capacitor Geolocation is available
  const capacitor = (window as any)?.Capacitor;
  if (capacitor?.isNativePlatform?.() && capacitor?.Plugins?.Geolocation) {
    try {
      const status = await capacitor.Plugins.Geolocation.checkPermissions();
      if (status.location === "granted") return "granted";
      if (status.location === "denied") return "denied";
      return "prompt";
    } catch (e) {
      console.warn("Capacitor permission check error:", e);
    }
  }

  // 2. Web Permissions API fallback
  if (typeof navigator !== "undefined" && navigator.permissions?.query) {
    try {
      const result = await navigator.permissions.query({ name: "geolocation" as PermissionName });
      return result.state as PermissionStateResult;
    } catch {
      // Some browsers throw on querying geolocation
    }
  }

  if (typeof navigator === "undefined" || !navigator.geolocation) {
    return "unavailable";
  }

  return "prompt";
}

export async function requestNativeOrWebPermission(): Promise<PermissionStateResult> {
  const capacitor = (window as any)?.Capacitor;
  if (capacitor?.isNativePlatform?.() && capacitor?.Plugins?.Geolocation) {
    try {
      const status = await capacitor.Plugins.Geolocation.requestPermissions();
      if (status.location === "granted") return "granted";
      if (status.location === "denied") return "denied";
      return "prompt";
    } catch (e) {
      console.warn("Capacitor permission request error:", e);
    }
  }

  return checkLocationPermission();
}
