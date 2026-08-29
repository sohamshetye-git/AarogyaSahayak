import enIN from "./locales/en-IN.json";
import hiIN from "./locales/hi-IN.json";
import mrIN from "./locales/mr-IN.json";

function getDeepKeys(obj: Record<string, any>, prefix = ""): string[] {
  return Object.keys(obj).reduce((res: string[], el: string) => {
    const name = prefix ? `${prefix}.${el}` : el;
    if (typeof obj[el] === "object" && obj[el] !== null && !Array.isArray(obj[el])) {
      return [...res, ...getDeepKeys(obj[el], name)];
    }
    return [...res, name];
  }, []);
}

export function validateLocaleParity(): {
  valid: boolean;
  totalKeys: number;
  missingInHi: string[];
  missingInMr: string[];
  extraInHi: string[];
  extraInMr: string[];
} {
  const enKeys = new Set(getDeepKeys(enIN));
  const hiKeys = new Set(getDeepKeys(hiIN));
  const mrKeys = new Set(getDeepKeys(mrIN));

  const missingInHi = [...enKeys].filter((k) => !hiKeys.has(k));
  const missingInMr = [...enKeys].filter((k) => !mrKeys.has(k));
  const extraInHi = [...hiKeys].filter((k) => !enKeys.has(k));
  const extraInMr = [...mrKeys].filter((k) => !enKeys.has(k));

  return {
    valid: missingInHi.length === 0 && missingInMr.length === 0,
    totalKeys: enKeys.size,
    missingInHi,
    missingInMr,
    extraInHi,
    extraInMr,
  };
}
