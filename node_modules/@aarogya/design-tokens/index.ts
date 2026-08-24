/**
 * Aarogya Sahayak - Canonical Design Tokens
 * Strictly adhering to WCAG 2.2 AA and rural healthcare clarity requirements
 */

export const colors = {
  primary: "#1565C0",
  primaryDark: "#0D47A1",
  primaryLight: "#E3F2FD",
  secondaryTeal: "#00897B",
  secondaryTealLight: "#E0F2F1",
  
  background: "#F6F8FB",
  surface: "#FFFFFF",
  
  textPrimary: "#17202A",
  textSecondary: "#5F6B76",
  textDisabled: "#8A949E",
  textInverse: "#FFFFFF",
  
  border: "#D9E0E7",
  borderStrong: "#B8C2CC",
  divider: "#E8EDF2",
  
  urgent: "#C62828",
  urgentBg: "#FDECEC",
  
  warning: "#D65A00",
  warningBg: "#FFF3E8",
  
  followup: "#B26A00",
  followupBg: "#FFF8E1",
  
  success: "#2E7D32",
  successBg: "#EAF5EB",
  
  offline: "#8A5200",
  offlineBg: "#FFF4E5",
  
  info: "#1565C0",
  infoBg: "#E3F2FD",
} as const;

export const typography = {
  fontFamily: "'Noto Sans', -apple-system, BlinkMacSystemFont, sans-serif",
  fontFamilyIndic: "'Noto Sans Devanagari', 'Noto Sans', sans-serif",
  sizes: {
    desktopPageTitle: { fontSize: "28px", lineHeight: "36px", fontWeight: 600 },
    mobilePageTitle: { fontSize: "24px", lineHeight: "32px", fontWeight: 600 },
    sectionTitle: { fontSize: "20px", lineHeight: "28px", fontWeight: 600 },
    cardTitle: { fontSize: "17px", lineHeight: "24px", fontWeight: 600 },
    body: { fontSize: "16px", lineHeight: "24px", fontWeight: 400 },
    secondary: { fontSize: "14px", lineHeight: "20px", fontWeight: 400 },
    caption: { fontSize: "12px", lineHeight: "16px", fontWeight: 400 },
    button: { fontSize: "16px", lineHeight: "20px", fontWeight: 600 },
    vitalDisplay: { fontSize: "28px", lineHeight: "36px", fontWeight: 700 },
  },
} as const;

export const spacing = {
  touchTargetMin: "48px",
  radiusCard: "12px",
  radiusButton: "12px",
  radiusBadge: "8px",
} as const;
