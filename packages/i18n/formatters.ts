import { SupportedLanguage } from "./config";

/**
 * Formats a Date object or ISO timestamp according to locale conventions.
 */
export function formatDate(
  date: string | Date | number,
  locale: SupportedLanguage = "en-IN",
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return "";
  const d = typeof date === "string" || typeof date === "number" ? new Date(date) : date;
  if (isNaN(d.getTime())) return "";

  const defaultOptions: Intl.DateTimeFormatOptions = {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...options,
  };

  try {
    return new Intl.DateTimeFormat(locale, defaultOptions).format(d);
  } catch {
    return d.toLocaleDateString();
  }
}

/**
 * Formats a time according to locale conventions.
 */
export function formatTime(
  date: string | Date | number,
  locale: SupportedLanguage = "en-IN",
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return "";
  const d = typeof date === "string" || typeof date === "number" ? new Date(date) : date;
  if (isNaN(d.getTime())) return "";

  const defaultOptions: Intl.DateTimeFormatOptions = {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
    ...options,
  };

  try {
    return new Intl.DateTimeFormat(locale, defaultOptions).format(d);
  } catch {
    return d.toLocaleTimeString();
  }
}

/**
 * Formats full datetime according to locale conventions.
 */
export function formatDateTime(
  date: string | Date | number,
  locale: SupportedLanguage = "en-IN"
): string {
  if (!date) return "";
  return `${formatDate(date, locale)} ${formatTime(date, locale)}`;
}

/**
 * Formats currency (INR ₹) with Indian numbering (e.g. ₹5,00,000)
 */
export function formatCurrency(
  amount: number | null | undefined,
  locale: SupportedLanguage = "en-IN"
): string {
  if (amount === null || amount === undefined || isNaN(amount)) return "₹0";
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `₹${amount.toLocaleString("en-IN")}`;
  }
}

/**
 * Formats plain numbers in localized script digits if desired or Indian grouping.
 */
export function formatNumber(
  value: number | null | undefined,
  locale: SupportedLanguage = "en-IN"
): string {
  if (value === null || value === undefined || isNaN(value)) return "0";
  try {
    return new Intl.NumberFormat(locale).format(value);
  } catch {
    return String(value);
  }
}

/**
 * Formats human-friendly relative time (e.g., "5 mins ago", "२ तासांपूर्वी").
 */
export function formatRelativeTime(
  date: string | Date | number,
  locale: SupportedLanguage = "en-IN"
): string {
  if (!date) return "";
  const d = typeof date === "string" || typeof date === "number" ? new Date(date) : date;
  const now = new Date();
  const diffSec = Math.floor((now.getTime() - d.getTime()) / 1000);

  if (diffSec < 60) {
    if (locale === "mr-IN") return "आत्ताच";
    if (locale === "hi-IN") return "अभी";
    return "just now";
  }

  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) {
    if (locale === "mr-IN") return `${diffMin} मिनिटांपूर्वी`;
    if (locale === "hi-IN") return `${diffMin} मिनट पहले`;
    return `${diffMin} min ago`;
  }

  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) {
    if (locale === "mr-IN") return `${diffHours} तासांपूर्वी`;
    if (locale === "hi-IN") return `${diffHours} घंटे पहले`;
    return `${diffHours}h ago`;
  }

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) {
    if (locale === "mr-IN") return `${diffDays} दिवसांपूर्वी`;
    if (locale === "hi-IN") return `${diffDays} दिन पहले`;
    return `${diffDays}d ago`;
  }

  return formatDate(d, locale);
}
