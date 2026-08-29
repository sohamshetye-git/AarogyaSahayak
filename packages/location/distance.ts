/**
 * Haversine distance calculations and rural travel time estimation
 */

export function calculateDistanceKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  if (
    !isFinite(lat1) ||
    !isFinite(lon1) ||
    !isFinite(lat2) ||
    !isFinite(lon2)
  ) {
    return 0;
  }

  const R = 6371; // Earth radius in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c * 10) / 10;
}

export function estimateTravelTimeMinutes(
  distanceKm: number,
  mode: "ROAD" | "WALKING" = "ROAD"
): { minutes: number; formatted: string } {
  const avgSpeedKmh = mode === "ROAD" ? 25 : 4; // rural roads ~25km/h, walking ~4km/h
  const mins = Math.max(5, Math.round((distanceKm / avgSpeedKmh) * 60));

  if (mins < 60) {
    return { minutes: mins, formatted: `~${mins} mins` };
  }
  const hrs = Math.floor(mins / 60);
  const remMins = mins % 60;
  return {
    minutes: mins,
    formatted: remMins > 0 ? `~${hrs}h ${remMins}m` : `~${hrs}h`
  };
}

export function formatDistance(distanceKm: number): string {
  if (distanceKm < 1) {
    return `${Math.round(distanceKm * 1000)} m`;
  }
  return `${distanceKm.toFixed(1)} km`;
}
