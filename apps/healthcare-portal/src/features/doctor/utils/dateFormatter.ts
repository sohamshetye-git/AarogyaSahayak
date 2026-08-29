export function formatIndiaDateTime(dateStr?: string | null): string {
  if (!dateStr || dateStr === "null" || dateStr === "undefined") {
    return "Date unavailable";
  }
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) {
    return "Date unavailable";
  }
  return d.toLocaleString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true
  });
}
