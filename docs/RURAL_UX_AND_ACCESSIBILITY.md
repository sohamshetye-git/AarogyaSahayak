# Aarogya Sahayak — Rural UX, Voice Interface & Accessibility Guidelines

## 1. Rural Healthcare Design Principles
Frontline ASHA workers operate under demanding field conditions: outdoors under bright sunlight, handling affordable low-end Android smartphones, often with intermittent internet connectivity.

### 1.1 Touch Targets & Mobile Ergonomics
* **Minimum 48×48 px Touch Targets**: All interactive elements (buttons, filter chips, checkboxes, tab triggers) adhere strictly to WCAG 2.1 AAA 48×48 px touch boundary requirements to facilitate one-handed thumb use in the field.
* **16px Input Font Size**: All text and number input fields specify minimum `16px` font size to prevent automatic zooming on iOS and mobile WebKit browsers.
* **High-Contrast Colour Palette**:
  * Primary Teal/Blue: `#0D9488` / `#0284C7`
  * Urgent Red: `#DC2626` on `#FEF2F2`
  * Success Green: `#16A34A` on `#F0FDF4`
  * Warning Amber: `#D97706` on `#FFFBEB`
* **Single-Column Mobile Stack**: On mobile viewports (360px to 420px), all dashboards, cards, and wizards transition into a fluid single-column stack.

---

## 2. Multilingual Voice Intake Architecture
* **Supported Rural Languages**:
  * Marathi (`mr-IN`) — Default for Maharashtra rural PHCs
  * Hindi (`hi-IN`)
  * Indian English (`en-IN`)
* **Voice Recording Flow**:
  1. ASHA taps `🎙 Speak Notes` button.
  2. Audio is captured via browser `MediaRecorder` / Web Speech API or streamed to Whisper fallback.
  3. Spoken text is rendered in real time into Marathi/Hindi script with confirmation before insertion.
  4. Non-English voice transcripts are preserved alongside translated clinical observations.

---

## 3. Accessibility & Low-Literacy Support
* **Descriptive Iconography**: Every status badge and navigation item pairs unambiguous icons with high-contrast text labels.
* **Non-Diagnostic Plain Language**: Clinical red flag warnings use clear, plain language descriptions avoiding medical jargon.
* **Auditory Feedback & Clear Confirmation**: Critical actions (acknowledgments, referral transmissions) display unambiguous confirmation modals and status badges.
