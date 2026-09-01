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
    switch (locale) {
      case "mr-IN": return "आत्ताच";
      case "hi-IN": return "अभी";
      case "gu-IN": return "હમણાં જ";
      case "bn-IN": return "এইমাত্র";
      case "kn-IN": return "ಈಗಷ್ಟೇ";
      case "te-IN": return "ఇప్పుడే";
      case "ta-IN": return "இப்போது";
      case "ml-IN": return "ഇപ്പോൾ";
      case "pa-IN": return "ਹੁਣੇ";
      case "od-IN": return "ଏବେ";
      case "en-IN":
      default: return "just now";
    }
  }

  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) {
    switch (locale) {
      case "mr-IN": return `${diffMin} मिनिटांपूर्वी`;
      case "hi-IN": return `${diffMin} मिनट पहले`;
      case "gu-IN": return `${diffMin} મિનિટ પહેલાં`;
      case "bn-IN": return `${diffMin} মিনিট আগে`;
      case "kn-IN": return `${diffMin} ನಿಮಿಷಗಳ ಹಿಂದೆ`;
      case "te-IN": return `${diffMin} నిమిషాల క్రితం`;
      case "ta-IN": return `${diffMin} நிமிடங்களுக்கு முன்பு`;
      case "ml-IN": return `${diffMin} മിനിറ്റ് മുമ്പ്`;
      case "pa-IN": return `${diffMin} ਮਿੰਟ ਪਹਿਲਾਂ`;
      case "od-IN": return `${diffMin} ମିନିଟ୍ ପୂର୍ବରୁ`;
      case "en-IN":
      default: return `${diffMin} min ago`;
    }
  }

  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) {
    switch (locale) {
      case "mr-IN": return `${diffHours} तासांपूर्वी`;
      case "hi-IN": return `${diffHours} घंटे पहले`;
      case "gu-IN": return `${diffHours} કલાક પહેલાં`;
      case "bn-IN": return `${diffHours} ঘন্টা আগে`;
      case "kn-IN": return `${diffHours} ಗಂಟೆಗಳ ಹಿಂದೆ`;
      case "te-IN": return `${diffHours} గంటల క్రితం`;
      case "ta-IN": return `${diffHours} மணி நேரத்திற்கு முன்பு`;
      case "ml-IN": return `${diffHours} മണിക്കൂർ മുമ്പ്`;
      case "pa-IN": return `${diffHours} ਘੰਟੇ ਪਹਿਲਾਂ`;
      case "od-IN": return `${diffHours} ଘଣ୍ଟା ପୂର୍ବରୁ`;
      case "en-IN":
      default: return `${diffHours}h ago`;
    }
  }

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) {
    switch (locale) {
      case "mr-IN": return `${diffDays} दिवसांपूर्वी`;
      case "hi-IN": return `${diffDays} दिन पहले`;
      case "gu-IN": return `${diffDays} દિવસ પહેલાં`;
      case "bn-IN": return `${diffDays} দিন আগে`;
      case "kn-IN": return `${diffDays} ದಿನಗಳ ಹಿಂದೆ`;
      case "te-IN": return `${diffDays} రోజుల క్రితం`;
      case "ta-IN": return `${diffDays} நாட்களுக்கு முன்பு`;
      case "ml-IN": return `${diffDays} ദിവസങ്ങൾക്ക് മുമ്പ്`;
      case "pa-IN": return `${diffDays} ਦਿਨ ਪਹਿਲਾਂ`;
      case "od-IN": return `${diffDays} ଦିନ ପୂର୍ବରୁ`;
      case "en-IN":
      default: return `${diffDays}d ago`;
    }
  }

  return formatDate(d, locale);
}
