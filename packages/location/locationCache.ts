import { LocationData } from "./locationTypes";

const CACHE_VERSION = "v1";
const FRESHNESS_THRESHOLD_MS = 15 * 60 * 1000; // 15 minutes freshness

interface CacheWrapper {
  schema_version: string;
  user_id?: string | null;
  role?: string | null;
  cached_at: string;
  data: LocationData;
}

function buildCacheKey(userId?: string | null, role?: string | null): string {
  const r = (role || "anonymous").toLowerCase().replace(/[^a-z0-9_]/g, "_");
  const u = (userId || "guest").toLowerCase().replace(/[^a-z0-9_]/g, "_");
  return `aarogya:location:${r}:${u}`;
}

export function getCachedLocation(userId?: string | null, role?: string | null): LocationData | null {
  try {
    if (typeof window === "undefined" || typeof localStorage === "undefined") return null;
    const key = buildCacheKey(userId, role);
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const wrapper = JSON.parse(raw) as CacheWrapper;
    if (wrapper.schema_version !== CACHE_VERSION) {
      localStorage.removeItem(key);
      return null;
    }
    return wrapper.data;
  } catch (e) {
    console.warn("Could not read scoped cached location:", e);
    return null;
  }
}

export function setCachedLocation(loc: LocationData, userId?: string | null, role?: string | null): void {
  try {
    if (typeof window === "undefined" || typeof localStorage === "undefined") return;
    const key = buildCacheKey(userId, role);
    const wrapper: CacheWrapper = {
      schema_version: CACHE_VERSION,
      user_id: userId || null,
      role: role || null,
      cached_at: new Date().toISOString(),
      data: loc
    };
    localStorage.setItem(key, JSON.stringify(wrapper));
  } catch (e) {
    console.warn("Could not set scoped cached location:", e);
  }
}

export function clearCachedLocation(userId?: string | null, role?: string | null): void {
  try {
    if (typeof window === "undefined" || typeof localStorage === "undefined") return;
    const key = buildCacheKey(userId, role);
    localStorage.removeItem(key);
  } catch (e) {
    console.warn("Could not clear scoped cached location:", e);
  }
}

export function clearAllTemporaryLocations(): void {
  try {
    if (typeof window === "undefined" || typeof localStorage === "undefined") return;
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith("aarogya:location:")) {
        keysToRemove.push(k);
      }
    }
    keysToRemove.forEach((k) => localStorage.removeItem(k));
  } catch (e) {
    console.warn("Could not clear temporary location keys:", e);
  }
}

export function isLocationFresh(loc: LocationData | null, maxAgeMs = FRESHNESS_THRESHOLD_MS): boolean {
  if (!loc || !loc.captured_at) return false;
  try {
    const capturedTime = new Date(loc.captured_at).getTime();
    const now = Date.now();
    return now - capturedTime < maxAgeMs;
  } catch {
    return false;
  }
}

export function getCacheAgeSeconds(loc: LocationData | null): number | null {
  if (!loc || !loc.captured_at) return null;
  try {
    const diff = Date.now() - new Date(loc.captured_at).getTime();
    return Math.max(0, Math.floor(diff / 1000));
  } catch {
    return null;
  }
}
