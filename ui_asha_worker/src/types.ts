export type Screen =
  | "login"
  | "dashboard"
  | "tasks"
  | "citizen-case"
  | "field-visit"
  | "people"
  | "schemes"
  | "notifications"
  | "offline"
  | "urgent-alert"
  | "referral"
  | "referral-success"
  | "profile";

export type Priority = "urgent" | "high" | "followup" | "routine";
export type CaseStatus =
  | "new"
  | "acknowledged"
  | "contacted"
  | "visit-planned"
  | "visit-in-progress"
  | "asha-reviewed"
  | "referred"
  | "doctor-acknowledged"
  | "followup-required"
  | "completed";
