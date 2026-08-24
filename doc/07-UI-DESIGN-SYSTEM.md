# UI Design System

## 1. Principles

- Citizen: voice-first, minimal, one primary action.
- ASHA: task-first, field-ready, offline-aware.
- Doctor: clinical review-first, desktop/tablet optimized.
- Admin: aggregate insight-first, privacy-preserving.
- Never expose technical AI terminology to end users.
- Never communicate status with color alone.

## 2. Color tokens

```text
primary #1565C0
primary_dark #0D47A1
primary_light #E3F2FD
secondary #00897B
background #F6F8FB
surface #FFFFFF
text_primary #17202A
text_secondary #5F6B76
border #D9E0E7
urgent #C62828
urgent_bg #FDECEC
warning #D65A00
warning_bg #FFF3E8
success #2E7D32
success_bg #EAF5EB
offline #8A5200
offline_bg #FFF4E5
```

## 3. Typography

Font: Noto Sans; use the matching Noto Sans Indian-script font.

```text
Desktop page title 28/36 semibold
Desktop section 22/30 semibold
Card title 18/26 semibold
Body 16/24 regular
Secondary 14/20 regular
Caption 12/16 regular
Button 16/20 semibold
Important vital 28/36 bold

Mobile page title 24/32 semibold
Mobile section 20/28 semibold
Mobile card 17/24 semibold
Mobile body 16/24 regular
```

No important medical text below 14 px. Support dynamic type.

## 4. Spacing and shape

- 8-point system: 4, 8, 12, 16, 24, 32, 40, 48.
- Mobile padding 16; tablet 24; desktop 32.
- Button/input height 48-56.
- Touch target minimum 48x48.
- Card radius 12-16; button radius 12.
- Prefer borders to heavy shadows.

## 5. Responsive layouts

### Citizen mobile

Frames: 360x800, 390x844, 412x915. One column, fixed bottom navigation, microphone 96-112px. Use three primary destinations: Home, My Updates, Help.

### Portal desktop

Frame 1440x1024. Sidebar 240, top bar 64, 12-column grid, max content 1200.

### Portal tablet

768x1024. Collapsible sidebar 80, padding 24, two-column cards.

### Portal mobile

390x844. App bar 56, bottom nav 68-72, stacked cards, bottom sheets, sticky action.

## 6. Shared components

```text
Button: primary, secondary, tertiary, danger, emergency
Input: text, numeric, search, select, textarea, date/time
Navigation: sidebar, top bar, bottom nav, tabs, stepper
Cards: summary, task, citizen, referral, vital, scheme, facility
Badges: priority, case status, source, sync
Banners: allergy, urgent, warning, offline, consent
Workflow: timeline, verification row, report preview, follow-up
States: loading, empty, error, offline, permission denied, conflict
```

Every component includes default, hover/focus where applicable, pressed, loading, disabled, error, success, and offline/read-only variants.

## 7. Citizen screens

Language, Home, Listening, Transcript Confirmation, Follow-up Question, Processing, Normal Guidance, High Risk, Uncertain, Offline Urgent Check, Scheme Result, Facility Finder, My Updates, Update Details, Help/Privacy.

Use tap-to-start/tap-to-stop consistently. Risk checking happens before ordinary response generation.

## 8. ASHA screens

Login, Dashboard, Tasks, Case Details, Contact Outcome, Plan Visit, Identify Citizen, Consent, Visit Wizard, AI Extraction Review, Vitals, Urgent Warning, Review/Decision, Referral, Report Preview, Follow-ups, People, Offline Queue.

Mobile navigation: Home, Tasks, Visit, People, More.

## 9. Doctor screens

Login, Dashboard, Referral Queue, Case Review, ASHA Summary, Vitals Timeline, Consultation, Assessment, Orders, Prescription, Care Plan, Higher Referral, Follow-ups, Patient Record, Reports.

Doctor case desktop layout: main clinical content 8 columns plus sticky action summary 4 columns.

## 10. Admin screens

Overview, Possible Cluster Alerts, Geography/Blocks, Scheme Analytics, Referral Analytics, Facility Load, Workforce Support, Reports, System Health.

Admin visualizations must be aggregate and must not reveal individual identities.

## 11. Required microcopy

Use:

```text
AI-assisted summary - please verify.
Potentially relevant scheme.
Urgent professional evaluation is recommended.
You are offline. Your information is safe.
We need more information.
```

Avoid:

```text
AI diagnosis
Execute escalation
API error
Confidence 83%
Patient critical
```

## 12. Accessibility

- WCAG 2.2 AA contrast target.
- Keyboard and screen-reader support.
- Visible focus indicators.
- Icon + label + color for status.
- No autoplay of sensitive audio.
- Reduced motion.
- One question per screen for citizen follow-ups.
- Clear field errors next to labels.

