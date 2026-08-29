/**
 * Singleton Google Maps JavaScript API script loader.
 * Loads the Google Maps JS SDK once using VITE_GOOGLE_MAPS_BROWSER_KEY.
 * Prevents multiple script injections, handles offline state and unauthorized errors.
 */

let loadPromise: Promise<void> | null = null;

export function loadGoogleMapsScript(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Window is not available"));
  }

  // Already loaded
  if ((window as any).google && (window as any).google.maps) {
    return Promise.resolve();
  }

  if (loadPromise) {
    return loadPromise;
  }

  const browserKey = ((import.meta as any).env?.VITE_GOOGLE_MAPS_BROWSER_KEY as string) || "";

  loadPromise = new Promise<void>((resolve, reject) => {
    // If no browser key is set, we still resolve gracefully so UI fallback renders
    if (!browserKey || browserKey.trim() === "") {
      console.warn("[GoogleMapsLoader] VITE_GOOGLE_MAPS_BROWSER_KEY is not set. Rendering interactive canvas fallback.");
      resolve();
      return;
    }

    const scriptId = "google-maps-platform-sdk";
    if (document.getElementById(scriptId)) {
      resolve();
      return;
    }

    const script = document.createElement("script");
    script.id = scriptId;
    script.type = "text/javascript";
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(browserKey)}&libraries=places,geometry&v=weekly`;
    script.async = true;
    script.defer = true;

    script.onload = () => {
      console.info("[GoogleMapsLoader] Google Maps JavaScript API loaded successfully.");
      resolve();
    };

    script.onerror = (e) => {
      console.warn("[GoogleMapsLoader] Failed to load Google Maps JavaScript API (offline or blocked).", e);
      // Resolve instead of rejecting so fallback UI renders seamlessly
      resolve();
    };

    document.head.appendChild(script);
  });

  return loadPromise;
}
