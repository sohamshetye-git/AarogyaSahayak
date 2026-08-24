# Requirements Document: Aarogya Sahayak Platform

## Introduction

Aarogya Sahayak is an AI-powered, voice-first rural healthcare coordination platform designed for India's rural healthcare ecosystem. The platform connects rural citizens, ASHA workers, Primary Health Centre (PHC) doctors, and district health officers through a unified case workflow. It addresses critical barriers including low literacy, regional language diversity, unstable connectivity, and overburdened healthcare infrastructure.

The system enables citizens to report health concerns via voice in their regional language, routes cases through deterministic safety checks and AI-assisted triage, facilitates human-in-the-loop verification by ASHA workers, enables PHC doctor consultations, and provides anonymized analytics to district administrators. The platform prioritizes safety, human oversight, and PII protection while maintaining accessibility for users with varying literacy levels.

## Glossary

- **Citizen_Mobile_App**: React Native mobile application for rural citizens to report health concerns via voice
- **Healthcare_Portal**: React web application shared by ASHA workers, PHC doctors, and district administrators
- **Backend_API**: FastAPI Python backend handling business logic, data persistence, and AI orchestration
- **BHASHINI**: Government of India's multilingual translation and speech services (ASR, translation, TTS)
- **Triage_Engine**: AI-powered component that assesses health concern urgency and routing
- **Verifier_Agent**: AI agent that validates and grounds AI outputs against trusted sources
- **Case**: A single health concern reported by a citizen, tracked through the entire workflow
- **ASHA_Worker**: Accredited Social Health Activist - community health worker
- **PHC**: Primary Health Centre - first-level healthcare facility
- **Field_Visit**: In-person assessment by ASHA worker at citizen's location
- **Vital_Signs**: Measurable clinical parameters (blood pressure, temperature, pulse, etc.)
- **Clinical_RAG**: Retrieval-Augmented Generation using Milvus vector database for clinical knowledge
- **Scheme_Graph**: Neo4j graph database containing government health schemes and eligibility
- **Offline_Mode**: Device-local operation without internet connectivity
- **Sync_Queue**: Queue of offline-created records awaiting upload when connectivity returns
- **PII**: Personally Identifiable Information (name, phone, address, Aadhaar, etc.)
- **RBAC**: Role-Based Access Control
- **Audit_Log**: Immutable record of all actions performed in the system
- **District_Admin**: Health officer monitoring aggregated health metrics for a district
- **n8n**: Workflow automation platform for notifications and integrations
- **ABDM**: Ayushman Bharat Digital Mission - India's health records framework
- **Lyzr_Agent**: AI agent framework used for orchestrating multi-step reasoning
- **TFLite_Model**: TensorFlow Lite model for offline triage inference
- **Deterministic_Rules**: Hard-coded safety checks that execute before AI processing
- **Source_Label**: Citation indicating which knowledge source generated specific information
- **Consent**: Explicit citizen approval for data collection, storage, and sharing
- **Care_Plan**: Doctor-created treatment and follow-up instructions
- **Referral**: Case escalation from ASHA worker to PHC doctor
- **Cluster_Alert**: Notification about geographic concentration of similar health concerns
- **SQLite_Cache**: Local database on citizen mobile device for offline operation
- **IndexedDB_Cache**: Browser-based local storage for ASHA worker offline operation
- **Monorepo**: Single repository containing multiple related packages and applications
- **JWT_Token**: JSON Web Token for authenticated API access
- **Session_Timeout**: Maximum duration of inactive authenticated session

## Requirements

### Requirement 1: Citizen Voice Health Concern Reporting

**User Story:** As a rural citizen with low literacy, I want to report health concerns using voice in my regional language, so that I can access healthcare guidance without needing to read or write.

#### Acceptance Criteria

1. THE Citizen_Mobile_App SHALL support voice recording in Hindi, Marathi, and English
2. WHEN a citizen records a voice message, THE Citizen_Mobile_App SHALL display a visual recording indicator
3. WHEN voice recording completes, THE Citizen_Mobile_App SHALL send audio to BHASHINI for transcription
4. WHEN BHASHINI returns a transcript, THE Citizen_Mobile_App SHALL display the text to the citizen for confirmation
5. THE Citizen_Mobile_App SHALL provide a replay button to listen to the original recording
6. WHEN the citizen confirms the transcript, THE Citizen_Mobile_App SHALL save the health concern locally
7. WHERE network connectivity is unavailable, THE Citizen_Mobile_App SHALL store the health concern in SQLite_Cache for later sync
8. WHEN network connectivity returns, THE Citizen_Mobile_App SHALL automatically sync pending health concerns from SQLite_Cache to Backend_API
9. THE Citizen_Mobile_App SHALL limit voice recordings to 180 seconds maximum duration
10. WHEN a health concern is successfully submitted, THE Citizen_Mobile_App SHALL return a unique Case identifier to the citizen

### Requirement 2: Emergency Safety Detection

**User Story:** As a healthcare safety officer, I want emergency symptoms detected immediately before AI processing, so that life-threatening conditions receive immediate attention without AI delay.

#### Acceptance Criteria

1. WHEN a Case is created, THE Backend_API SHALL execute Deterministic_Rules before any AI processing
2. THE Deterministic_Rules SHALL check for emergency keywords in Hindi, Marathi, and English
3. IF emergency keywords are detected (chest pain, difficulty breathing, severe bleeding, unconsciousness, suicide ideation), THEN THE Backend_API SHALL mark the Case as "EMERGENCY" priority
4. WHEN a Case is marked "EMERGENCY", THE Backend_API SHALL bypass Triage_Engine processing
5. WHEN a Case is marked "EMERGENCY", THE Backend_API SHALL immediately notify the nearest ASHA_Worker within 60 seconds
6. THE Backend_API SHALL log all Deterministic_Rules executions to Audit_Log
7. THE Deterministic_Rules SHALL execute within 500 milliseconds of Case creation
8. THE Backend_API SHALL not allow Deterministic_Rules to be bypassed or disabled by any user role

### Requirement 3: AI-Assisted Triage

**User Story:** As an ASHA worker, I want AI to assess health concern urgency, so that I can prioritize which citizens need immediate attention.

#### Acceptance Criteria

1. WHEN a Case is not marked "EMERGENCY" by Deterministic_Rules, THE Triage_Engine SHALL assess the health concern
2. THE Triage_Engine SHALL query Clinical_RAG with the citizen's health concern transcript
3. THE Triage_Engine SHALL assign one of four priority levels: EMERGENCY, URGENT, ROUTINE, INFORMATIONAL
4. WHEN Clinical_RAG returns relevant medical information, THE Triage_Engine SHALL include Source_Label references
5. THE Triage_Engine SHALL complete assessment within 5 seconds of invocation
6. THE Triage_Engine SHALL send output to Verifier_Agent before storing in database
7. WHEN Verifier_Agent detects unsafe or unsupported claims, THE Triage_Engine SHALL remove those claims and mark the Case for human review
8. THE Triage_Engine SHALL not provide diagnosis, prescription, or treatment recommendations
9. THE Triage_Engine SHALL log all inputs and outputs to Audit_Log
10. WHERE Triage_Engine processing fails, THE Backend_API SHALL default the Case to "URGENT" priority

### Requirement 4: PII Protection in AI Processing

**User Story:** As a privacy officer, I want personally identifiable information masked before external AI processing, so that citizen privacy is protected when using cloud AI services.

#### Acceptance Criteria

1. WHEN the Backend_API sends data to external AI services (Gemini, Lyzr), THE Backend_API SHALL mask all PII fields
2. THE Backend_API SHALL replace citizen names with anonymized identifiers (e.g., "CITIZEN_001")
3. THE Backend_API SHALL remove phone numbers, addresses, Aadhaar numbers, and geolocation coordinates
4. THE Backend_API SHALL retain only age, gender, and health concern text for AI processing
5. THE Backend_API SHALL log all PII masking operations to Audit_Log
6. THE Backend_API SHALL not transmit unmasked PII to any external service
7. WHEN AI processing completes, THE Backend_API SHALL re-associate results with original Case using internal identifiers

### Requirement 5: ASHA Worker Task Management

**User Story:** As an ASHA worker, I want to see prioritized cases assigned to my area, so that I can efficiently manage my daily workload and respond to urgent cases first.

#### Acceptance Criteria

1. WHEN an ASHA_Worker logs into Healthcare_Portal, THE Healthcare_Portal SHALL display cases assigned to their geographic area
2. THE Healthcare_Portal SHALL sort cases by priority (EMERGENCY, URGENT, ROUTINE, INFORMATIONAL)
3. THE Healthcare_Portal SHALL display case age (hours since creation) for each case
4. WHEN a new EMERGENCY case is created in the ASHA_Worker's area, THE Healthcare_Portal SHALL display a visual alert within 60 seconds
5. THE Healthcare_Portal SHALL allow the ASHA_Worker to acknowledge a case
6. WHEN an ASHA_Worker acknowledges a case, THE Backend_API SHALL update the case status to "ACKNOWLEDGED"
7. THE Healthcare_Portal SHALL display citizen contact information only after case acknowledgment
8. THE Healthcare_Portal SHALL provide filtering by case status, priority, and date range
9. THE Healthcare_Portal SHALL display total pending, acknowledged, and completed case counts
10. WHERE network connectivity is unavailable, THE Healthcare_Portal SHALL cache the current case list in IndexedDB_Cache and display a connectivity warning

### Requirement 6: ASHA Field Visit Recording

**User Story:** As an ASHA worker, I want to record field visit observations and vital signs, so that I can document citizen health status for doctor review.

#### Acceptance Criteria

1. WHEN an ASHA_Worker opens a case, THE Healthcare_Portal SHALL provide a "Start Field Visit" button
2. WHEN the ASHA_Worker starts a field visit, THE Healthcare_Portal SHALL display forms for Vital_Signs entry
3. THE Healthcare_Portal SHALL accept blood pressure (systolic/diastolic), temperature, pulse rate, and respiratory rate
4. THE Healthcare_Portal SHALL validate Vital_Signs within medically plausible ranges (BP 60-250/40-180, temp 35-42°C, pulse 30-200, respiration 8-40)
5. THE Healthcare_Portal SHALL allow the ASHA_Worker to record text observations
6. THE Healthcare_Portal SHALL allow the ASHA_Worker to capture photos of visible symptoms
7. WHERE network connectivity is unavailable, THE Healthcare_Portal SHALL save field visit data to IndexedDB_Cache
8. WHEN the ASHA_Worker saves field visit data, THE Backend_API SHALL timestamp the record with device time and server time
9. THE Healthcare_Portal SHALL allow the ASHA_Worker to mark a case for PHC referral after field visit
10. WHEN an ASHA_Worker completes a field visit, THE Backend_API SHALL update case status to "FIELD_VISIT_COMPLETED"

### Requirement 7: PHC Doctor Referral Management

**User Story:** As a PHC doctor, I want to see cases referred by ASHA workers with complete context, so that I can efficiently review and prioritize consultations.

#### Acceptance Criteria

1. WHEN a PHC doctor logs into Healthcare_Portal, THE Healthcare_Portal SHALL display all cases referred to their PHC
2. THE Healthcare_Portal SHALL display citizen health concern transcript, Triage_Engine assessment, ASHA field visit notes, and Vital_Signs
3. THE Healthcare_Portal SHALL display Source_Label references for all AI-generated content
4. THE Healthcare_Portal SHALL sort referrals by priority and referral age
5. THE Healthcare_Portal SHALL allow the doctor to acknowledge a referral
6. WHEN a doctor acknowledges a referral, THE Backend_API SHALL update case status to "UNDER_DOCTOR_REVIEW"
7. THE Healthcare_Portal SHALL display notification when an EMERGENCY referral is created
8. THE Healthcare_Portal SHALL provide filtering by priority, status, and date range
9. THE Healthcare_Portal SHALL display doctor's current workload (pending, in-review, completed counts)
10. THE Healthcare_Portal SHALL allow the doctor to request additional information from ASHA_Worker

### Requirement 8: Doctor Consultation and Diagnosis

**User Story:** As a PHC doctor, I want to document consultations and diagnoses with treatment plans, so that citizens receive appropriate care guidance.

#### Acceptance Criteria

1. WHEN a doctor reviews a case, THE Healthcare_Portal SHALL provide forms for consultation notes, diagnosis, and Care_Plan
2. THE Healthcare_Portal SHALL allow the doctor to enter ICD-10 diagnosis codes
3. THE Healthcare_Portal SHALL allow the doctor to create a Care_Plan with treatment instructions
4. THE Healthcare_Portal SHALL allow the doctor to prescribe medications with dosage and duration
5. THE Healthcare_Portal SHALL query Scheme_Graph to identify applicable government health schemes based on diagnosis and citizen demographics
6. WHEN applicable schemes are found, THE Healthcare_Portal SHALL display scheme names and eligibility criteria to the doctor
7. THE Healthcare_Portal SHALL allow the doctor to schedule follow-up visits
8. WHEN the doctor saves consultation data, THE Backend_API SHALL update case status to "CONSULTATION_COMPLETED"
9. THE Backend_API SHALL generate a PDF report of the consultation using WeasyPrint
10. THE Backend_API SHALL make the consultation report available to the citizen via Citizen_Mobile_App

### Requirement 9: Citizen Case Status Tracking

**User Story:** As a rural citizen, I want to check my case status and receive updates, so that I stay informed about my healthcare journey.

#### Acceptance Criteria

1. WHEN a citizen opens Citizen_Mobile_App, THE Citizen_Mobile_App SHALL display all their active cases
2. THE Citizen_Mobile_App SHALL display case status (Submitted, Acknowledged, Field Visit Scheduled, Under Doctor Review, Consultation Completed)
3. THE Citizen_Mobile_App SHALL display status updates in the citizen's preferred language using BHASHINI
4. WHEN case status changes, THE Citizen_Mobile_App SHALL display a notification
5. THE Citizen_Mobile_App SHALL allow the citizen to view their Care_Plan in text and audio format
6. THE Citizen_Mobile_App SHALL allow the citizen to download their consultation PDF report
7. THE Citizen_Mobile_App SHALL display next scheduled follow-up date and time
8. THE Citizen_Mobile_App SHALL allow the citizen to mark a case as resolved
9. WHERE network connectivity is unavailable, THE Citizen_Mobile_App SHALL display last cached case status with a "last updated" timestamp
10. THE Citizen_Mobile_App SHALL automatically refresh case status when network connectivity returns

### Requirement 10: District Analytics Dashboard

**User Story:** As a district health administrator, I want to view anonymized health metrics and trends, so that I can allocate resources and identify emerging health concerns.

#### Acceptance Criteria

1. WHEN a District_Admin logs into Healthcare_Portal, THE Healthcare_Portal SHALL display anonymized aggregate metrics
2. THE Healthcare_Portal SHALL display total cases by priority level for the current month
3. THE Healthcare_Portal SHALL display average case resolution time (creation to consultation completion)
4. THE Healthcare_Portal SHALL display top 10 diagnosis categories by frequency
5. THE Healthcare_Portal SHALL display PHC facility workload distribution
6. THE Healthcare_Portal SHALL display ASHA_Worker caseload distribution
7. THE Healthcare_Portal SHALL not display individual citizen names, phone numbers, or addresses
8. THE Healthcare_Portal SHALL allow filtering by date range, PHC facility, and health concern category
9. THE Healthcare_Portal SHALL display metrics within 3 seconds of page load
10. THE Healthcare_Portal SHALL allow export of anonymized data in CSV format

### Requirement 11: Geographic Cluster Detection

**User Story:** As a district health administrator, I want alerts about geographic clusters of similar health concerns, so that I can detect potential disease outbreaks early.

#### Acceptance Criteria

1. WHEN the Backend_API detects 5 or more cases with similar symptoms within a 5-kilometer radius within 7 days, THE Backend_API SHALL create a Cluster_Alert
2. THE Backend_API SHALL analyze symptom similarity using Clinical_RAG vector embeddings
3. THE Backend_API SHALL calculate geographic clustering using citizen location coordinates
4. WHEN a Cluster_Alert is created, THE Backend_API SHALL notify District_Admin within 15 minutes
5. THE Healthcare_Portal SHALL display Cluster_Alert details (affected area, symptom pattern, case count, time period)
6. THE Healthcare_Portal SHALL not display individual citizen identities in Cluster_Alert
7. THE Backend_API SHALL execute cluster detection analysis once every 6 hours
8. THE District_Admin SHALL be able to acknowledge and dismiss Cluster_Alert notifications
9. THE Backend_API SHALL log all Cluster_Alert creations to Audit_Log
10. THE Healthcare_Portal SHALL display Cluster_Alert history for the past 90 days

### Requirement 12: Offline Triage for Citizens

**User Story:** As a rural citizen in an area with poor connectivity, I want to receive basic health guidance offline, so that I can get help even without internet access.

#### Acceptance Criteria

1. WHEN Citizen_Mobile_App installs, THE Citizen_Mobile_App SHALL download TFLite_Model to device storage
2. WHERE network connectivity is unavailable and a citizen creates a health concern, THE Citizen_Mobile_App SHALL execute TFLite_Model for basic triage
3. THE TFLite_Model SHALL classify health concerns into EMERGENCY, URGENT, or ROUTINE priority
4. WHEN TFLite_Model detects EMERGENCY priority, THE Citizen_Mobile_App SHALL display immediate advice to contact emergency services
5. THE Citizen_Mobile_App SHALL store offline triage results in SQLite_Cache
6. WHEN network connectivity returns, THE Citizen_Mobile_App SHALL sync offline cases to Backend_API
7. WHEN Backend_API receives an offline-created case, THE Backend_API SHALL re-run Triage_Engine with full Clinical_RAG and update if priority changes
8. THE TFLite_Model SHALL execute within 2 seconds on device
9. THE Citizen_Mobile_App SHALL display a clear indicator when operating in offline mode
10. THE Citizen_Mobile_App SHALL update TFLite_Model weekly when network connectivity is available

### Requirement 13: User Authentication and Authorization

**User Story:** As a system administrator, I want secure role-based authentication, so that users only access features appropriate for their role.

#### Acceptance Criteria

1. THE Healthcare_Portal SHALL require username and password login for ASHA_Worker, PHC doctor, and District_Admin users
2. THE Citizen_Mobile_App SHALL require phone number OTP authentication for citizens
3. WHEN a user logs in, THE Backend_API SHALL return a JWT_Token valid for 8 hours
4. THE Backend_API SHALL implement RBAC with four roles: CITIZEN, ASHA, DOCTOR, ADMIN
5. THE Backend_API SHALL verify JWT_Token and role permissions for every API request
6. THE Backend_API SHALL return 401 Unauthorized for invalid or expired JWT_Token
7. THE Backend_API SHALL return 403 Forbidden when a user attempts to access resources outside their role permissions
8. THE Healthcare_Portal SHALL automatically log out users after Session_Timeout of 30 minutes of inactivity
9. THE Backend_API SHALL hash passwords using bcrypt with salt rounds of 12
10. THE Backend_API SHALL log all authentication attempts (success and failure) to Audit_Log

### Requirement 14: Citizen Consent Management

**User Story:** As a rural citizen, I want to understand and control how my health data is used, so that I can make informed decisions about my privacy.

#### Acceptance Criteria

1. WHEN a citizen first uses Citizen_Mobile_App, THE Citizen_Mobile_App SHALL display a Consent form in their preferred language
2. THE Consent form SHALL explain data collection, storage, sharing with ASHA_Worker and PHC doctor, and retention policies
3. THE Citizen_Mobile_App SHALL provide audio playback of the Consent text using BHASHINI TTS
4. THE Citizen_Mobile_App SHALL require explicit consent acceptance before allowing health concern creation
5. THE Backend_API SHALL record consent acceptance with timestamp in database
6. THE Citizen_Mobile_App SHALL allow citizens to review and withdraw consent at any time
7. WHEN a citizen withdraws consent, THE Backend_API SHALL anonymize all their historical cases within 24 hours
8. THE Backend_API SHALL not process new health concerns from citizens who have withdrawn consent
9. THE Backend_API SHALL log all consent actions (acceptance, withdrawal) to Audit_Log
10. THE Citizen_Mobile_App SHALL display current consent status on user profile screen

### Requirement 15: Audit Logging and Compliance

**User Story:** As a compliance officer, I want comprehensive audit logs of all system actions, so that I can investigate incidents and ensure regulatory compliance.

#### Acceptance Criteria

1. THE Backend_API SHALL log every Case creation, status change, and access to Audit_Log
2. THE Backend_API SHALL log every user authentication, authorization failure, and consent action to Audit_Log
3. THE Audit_Log SHALL record timestamp, user ID, user role, action type, resource ID, and IP address
4. THE Audit_Log SHALL record all AI agent invocations with inputs and outputs
5. THE Backend_API SHALL make Audit_Log records immutable (append-only)
6. THE Backend_API SHALL retain Audit_Log records for 7 years
7. THE Backend_API SHALL not allow any user role to delete or modify Audit_Log records
8. THE Healthcare_Portal SHALL provide audit log search for District_Admin by date range, user, and action type
9. THE Backend_API SHALL write Audit_Log entries synchronously before returning API responses
10. WHERE Audit_Log write fails, THE Backend_API SHALL return 500 Internal Server Error and not complete the action

### Requirement 16: Notification Workflow Integration

**User Story:** As an ASHA worker, I want to receive SMS and WhatsApp notifications for urgent cases, so that I can respond quickly even when not actively using the portal.

#### Acceptance Criteria

1. WHEN a Case is marked EMERGENCY, THE Backend_API SHALL trigger an n8n workflow within 60 seconds
2. THE n8n workflow SHALL send SMS to the assigned ASHA_Worker with Case ID and citizen contact
3. THE n8n workflow SHALL send WhatsApp message to the assigned ASHA_Worker with Case summary
4. WHEN an ASHA_Worker refers a case to PHC, THE Backend_API SHALL trigger n8n workflow to notify the PHC doctor
5. WHEN a PHC doctor completes a consultation, THE Backend_API SHALL trigger n8n workflow to notify the citizen
6. THE n8n workflow SHALL support Hindi, Marathi, and English message templates
7. THE Backend_API SHALL log all notification delivery attempts to Audit_Log
8. THE Backend_API SHALL retry failed notification deliveries up to 3 times with exponential backoff
9. THE Backend_API SHALL not block API responses waiting for notification delivery
10. THE Healthcare_Portal SHALL display notification delivery status (sent, delivered, failed) for each Case

### Requirement 17: Clinical Knowledge Retrieval

**User Story:** As a PHC doctor, I want AI-suggested clinical information with sources, so that I can make informed decisions with confidence in the information accuracy.

#### Acceptance Criteria

1. WHEN the Triage_Engine or doctor requests clinical information, THE Clinical_RAG SHALL search Milvus vector database
2. THE Clinical_RAG SHALL return top 5 most relevant medical knowledge chunks
3. THE Clinical_RAG SHALL include Source_Label with each knowledge chunk (document name, page number, publication date)
4. THE Clinical_RAG SHALL not generate unsupported medical claims
5. WHEN Verifier_Agent detects hallucinated content, THE Verifier_Agent SHALL remove that content and log the occurrence
6. THE Clinical_RAG SHALL respond within 3 seconds for 95% of queries
7. THE Backend_API SHALL log all Clinical_RAG queries and responses to Audit_Log
8. THE Healthcare_Portal SHALL display Source_Label references as clickable citations
9. THE Clinical_RAG SHALL support queries in Hindi, Marathi, and English
10. THE Backend_API SHALL not cache Clinical_RAG responses for more than 24 hours

### Requirement 18: Government Scheme Discovery

**User Story:** As a PHC doctor, I want automatic identification of applicable government health schemes, so that I can help citizens access financial assistance for treatment.

#### Acceptance Criteria

1. WHEN a doctor enters a diagnosis, THE Backend_API SHALL query Scheme_Graph Neo4j database
2. THE Scheme_Graph SHALL match diagnosis ICD-10 codes, citizen age, gender, and income level against scheme eligibility rules
3. THE Scheme_Graph SHALL return all matching government health schemes
4. THE Healthcare_Portal SHALL display scheme names, eligibility criteria, coverage amount, and application process
5. THE Healthcare_Portal SHALL allow the doctor to add scheme recommendations to the Care_Plan
6. THE Scheme_Graph SHALL include national schemes (Ayushman Bharat) and state-specific schemes
7. THE Backend_API SHALL update Scheme_Graph weekly with latest scheme information
8. THE Healthcare_Portal SHALL display scheme information in Hindi, Marathi, and English
9. THE Backend_API SHALL log all scheme queries to Audit_Log
10. WHERE no matching schemes are found, THE Healthcare_Portal SHALL display a message indicating scheme search was performed

### Requirement 19: PDF Report Generation

**User Story:** As a rural citizen, I want a downloadable consultation report, so that I can share it with family or other healthcare providers.

#### Acceptance Criteria

1. WHEN a doctor completes a consultation, THE Backend_API SHALL generate a PDF report using WeasyPrint
2. THE PDF report SHALL include Case ID, citizen name, consultation date, diagnosis, Care_Plan, prescribed medications, and follow-up schedule
3. THE PDF report SHALL include doctor's name and PHC facility name
4. THE PDF report SHALL include Source_Label references for any AI-generated content displayed
5. THE PDF report SHALL be generated in the citizen's preferred language
6. THE Backend_API SHALL store the PDF report in object storage with secure URL
7. THE Citizen_Mobile_App SHALL allow the citizen to download the PDF report
8. THE Backend_API SHALL expire PDF download URLs after 90 days
9. THE Backend_API SHALL generate PDF reports within 10 seconds of consultation completion
10. THE PDF report SHALL be formatted for A4 paper size and readable when printed

### Requirement 20: ABDM Integration Preparation

**User Story:** As a system architect, I want ABDM sandbox integration hooks, so that the platform can eventually integrate with India's national health records system.

#### Acceptance Criteria

1. THE Backend_API SHALL include API endpoints for ABDM Health ID creation (stubbed for MVP)
2. THE Backend_API SHALL include API endpoints for health record consent management (stubbed for MVP)
3. THE Backend_API SHALL store ABDM Health ID when provided by citizens
4. THE Healthcare_Portal SHALL display ABDM Health ID field in citizen profile (optional)
5. THE Backend_API SHALL format consultation records in FHIR-compatible JSON structure
6. THE Backend_API SHALL store FHIR-formatted records in database for future ABDM sync
7. THE Backend_API SHALL not actively sync records to ABDM in MVP (stubbed for future)
8. THE Backend_API SHALL log all ABDM-related operations to Audit_Log
9. THE Backend_API SHALL validate ABDM Health ID format (14-digit number) when provided
10. THE Healthcare_Portal SHALL display a notice that ABDM integration is in development

### Requirement 21: Multi-language Support

**User Story:** As a rural citizen who speaks Marathi, I want the entire application in my language, so that I can use the platform comfortably without language barriers.

#### Acceptance Criteria

1. THE Citizen_Mobile_App SHALL support Hindi, Marathi, and English interface languages
2. THE Citizen_Mobile_App SHALL allow language selection during onboarding and in settings
3. THE Citizen_Mobile_App SHALL persist language preference locally and sync to Backend_API
4. THE Healthcare_Portal SHALL support Hindi, Marathi, and English interface languages
5. THE Backend_API SHALL store all text content (Care_Plan, consultation notes, field visit notes) in the author's language
6. WHEN displaying content to users in different languages, THE Backend_API SHALL translate using BHASHINI
7. THE Citizen_Mobile_App SHALL provide audio playback of all text content using BHASHINI TTS
8. THE Backend_API SHALL support transliteration of citizen names in Devanagari script
9. THE Citizen_Mobile_App SHALL use culturally appropriate icons and visual metaphors
10. THE Healthcare_Portal SHALL display numbers in Indian numbering format (lakhs, crores)

### Requirement 22: Performance Requirements

**User Story:** As a rural citizen with slow 2G connectivity, I want the app to load quickly and work smoothly, so that I can complete tasks without frustration.

#### Acceptance Criteria

1. THE Citizen_Mobile_App SHALL load the home screen within 3 seconds on 2G connectivity
2. THE Citizen_Mobile_App SHALL compress voice recordings to maximum 1 MB per minute
3. THE Backend_API SHALL respond to 95% of API requests within 2 seconds
4. THE Healthcare_Portal SHALL load the dashboard within 2 seconds on 3G connectivity
5. THE Backend_API SHALL support 10,000 concurrent users
6. THE Backend_API SHALL process 1,000 case creations per minute
7. THE Milvus vector database SHALL respond to similarity queries within 500 milliseconds
8. THE Neo4j Scheme_Graph SHALL respond to queries within 300 milliseconds
9. THE Citizen_Mobile_App SHALL use progressive image loading for symptom photos
10. THE Healthcare_Portal SHALL use pagination for case lists exceeding 50 items

### Requirement 23: Reliability and Error Handling

**User Story:** As an ASHA worker, I want the system to handle errors gracefully, so that I don't lose my work when issues occur.

#### Acceptance Criteria

1. WHERE the Backend_API encounters an error, THE Backend_API SHALL return a user-friendly error message in the user's language
2. THE Backend_API SHALL log all errors with stack traces to error monitoring system
3. WHERE database connection fails, THE Backend_API SHALL retry up to 3 times before returning error
4. WHERE BHASHINI service is unavailable, THE Citizen_Mobile_App SHALL queue voice recordings for later transcription
5. WHERE Clinical_RAG is unavailable, THE Triage_Engine SHALL default to rule-based triage without AI
6. THE Healthcare_Portal SHALL auto-save form data every 30 seconds to IndexedDB_Cache
7. WHERE the user's session expires during form entry, THE Healthcare_Portal SHALL restore form data after re-authentication
8. THE Backend_API SHALL implement circuit breaker pattern for external service calls
9. THE Backend_API SHALL achieve 99.5% uptime measured monthly
10. THE Backend_API SHALL recover from failures within 5 minutes

### Requirement 24: Accessibility Requirements

**User Story:** As a visually impaired ASHA worker, I want the portal to work with screen readers, so that I can perform my duties independently.

#### Acceptance Criteria

1. THE Healthcare_Portal SHALL comply with WCAG 2.1 Level AA standards
2. THE Healthcare_Portal SHALL provide alt text for all images and icons
3. THE Healthcare_Portal SHALL support keyboard navigation for all interactive elements
4. THE Healthcare_Portal SHALL use sufficient color contrast ratios (4.5:1 for text, 3:1 for UI components)
5. THE Healthcare_Portal SHALL provide focus indicators for keyboard navigation
6. THE Citizen_Mobile_App SHALL support screen reader announcements for all actions
7. THE Citizen_Mobile_App SHALL provide haptic feedback for button presses
8. THE Healthcare_Portal SHALL not rely on color alone to convey information
9. THE Citizen_Mobile_App SHALL support font size adjustment from 100% to 200%
10. THE Healthcare_Portal SHALL provide skip navigation links for screen reader users

### Requirement 25: Data Retention and Privacy

**User Story:** As a privacy officer, I want clear data retention policies enforced automatically, so that citizen data is not retained longer than necessary.

#### Acceptance Criteria

1. THE Backend_API SHALL retain Case records for 3 years after case closure
2. THE Backend_API SHALL anonymize Case records after 3 years (remove PII, retain clinical data)
3. THE Backend_API SHALL permanently delete Audit_Log records older than 7 years
4. THE Backend_API SHALL delete voice recordings and audio files after 90 days
5. THE Backend_API SHALL delete symptom photos after 1 year
6. THE Backend_API SHALL run data retention cleanup jobs daily at 2:00 AM local time
7. THE Backend_API SHALL log all data deletion operations to Audit_Log before deletion
8. THE Backend_API SHALL not delete cases with active follow-up appointments
9. WHEN a citizen requests data deletion, THE Backend_API SHALL complete deletion within 30 days
10. THE Backend_API SHALL provide data export in JSON format for citizens requesting their data

### Requirement 26: Testing and Quality Assurance

**User Story:** As a quality assurance engineer, I want comprehensive testing infrastructure, so that I can verify system correctness and safety.

#### Acceptance Criteria

1. THE Backend_API SHALL include unit tests with minimum 80% code coverage
2. THE Backend_API SHALL include integration tests for all API endpoints
3. THE Backend_API SHALL include property-based tests for Deterministic_Rules
4. THE Backend_API SHALL include property-based tests for PII masking functions
5. THE Backend_API SHALL include end-to-end tests for critical user journeys (citizen report → ASHA visit → doctor consultation)
6. THE Backend_API SHALL include load tests simulating 10,000 concurrent users
7. THE Citizen_Mobile_App SHALL include unit tests for offline sync logic
8. THE Healthcare_Portal SHALL include accessibility tests using axe-core
9. THE Backend_API SHALL run all tests in CI/CD pipeline before deployment
10. WHERE any test fails, THE CI/CD pipeline SHALL block deployment

### Requirement 27: Deployment and DevOps

**User Story:** As a DevOps engineer, I want containerized deployment with monitoring, so that I can operate the platform reliably in production.

#### Acceptance Criteria

1. THE Backend_API SHALL be packaged as a Docker container
2. THE Backend_API SHALL include health check endpoint returning 200 OK when healthy
3. THE Backend_API SHALL export Prometheus metrics for monitoring
4. THE Backend_API SHALL include structured JSON logging
5. THE Backend_API SHALL support environment-based configuration (development, staging, production)
6. THE Backend_API SHALL include database migration scripts using Alembic
7. THE Backend_API SHALL support zero-downtime rolling deployments
8. THE Backend_API SHALL include backup scripts for PostgreSQL database
9. THE Backend_API SHALL support horizontal scaling with multiple container instances
10. THE Backend_API SHALL include disaster recovery documentation

### Requirement 28: Monorepo Structure and Shared Packages

**User Story:** As a developer, I want a well-organized monorepo with shared packages, so that I can maintain consistency across applications and reduce code duplication.

#### Acceptance Criteria

1. THE Monorepo SHALL include separate directories for citizen-mobile, healthcare-portal, and backend applications
2. THE Monorepo SHALL include a shared-types package with TypeScript interfaces for API contracts
3. THE Monorepo SHALL include a design-tokens package with colors, spacing, and typography values
4. THE Monorepo SHALL include an api-client package with typed HTTP client functions
5. THE Monorepo SHALL use a workspace manager (npm workspaces or Yarn workspaces)
6. THE Monorepo SHALL include a root-level Docker Compose file for local development
7. THE Monorepo SHALL include a root-level README with setup instructions
8. THE Monorepo SHALL use consistent linting and formatting rules across all packages
9. THE Monorepo SHALL support running tests for all packages from the root level
10. THE Monorepo SHALL include CI/CD configuration for automated testing and deployment

### Requirement 29: Local Development Environment

**User Story:** As a developer, I want to run the entire platform locally, so that I can develop and test features without cloud dependencies.

#### Acceptance Criteria

1. THE Monorepo SHALL include Docker Compose configuration for all services (PostgreSQL, Milvus, Neo4j, Backend_API)
2. THE Docker Compose configuration SHALL start all services with a single command
3. THE Docker Compose configuration SHALL include seed data for testing (sample users, cases, schemes)
4. THE Docker Compose configuration SHALL mount source code for hot reload during development
5. THE Docker Compose configuration SHALL expose ports for direct database access
6. THE Monorepo SHALL include scripts to initialize Clinical_RAG with sample medical documents
7. THE Monorepo SHALL include scripts to initialize Scheme_Graph with sample government schemes
8. THE Monorepo SHALL mock BHASHINI services for local development
9. THE Monorepo SHALL mock n8n notification services for local development
10. THE Monorepo SHALL include documentation for troubleshooting common local development issues

### Requirement 30: Parser and Serializer Requirements

**User Story:** As a developer, I want robust parsing and serialization of data formats, so that data integrity is maintained across system boundaries.

#### Acceptance Criteria

1. WHEN the Backend_API receives FHIR JSON from ABDM, THE FHIR_Parser SHALL parse it into internal Case data model
2. WHEN the FHIR_Parser encounters invalid JSON, THE FHIR_Parser SHALL return a descriptive error with line number and field name
3. THE FHIR_Pretty_Printer SHALL format Case data into valid FHIR JSON
4. FOR ALL valid Case objects, parsing then printing then parsing SHALL produce an equivalent object (round-trip property)
5. WHEN the Backend_API receives ICD-10 codes, THE ICD_Parser SHALL validate code format and version
6. WHEN the ICD_Parser encounters an invalid code, THE ICD_Parser SHALL return an error with suggested valid codes
7. THE Backend_API SHALL include property-based tests for FHIR_Parser round-trip behavior
8. THE Backend_API SHALL include property-based tests for ICD_Parser validation logic
9. WHEN the Backend_API serializes data to JSON for external APIs, THE JSON_Serializer SHALL escape special characters properly
10. THE Backend_API SHALL include unit tests verifying FHIR_Pretty_Printer output validates against FHIR schema

---

## Summary

This requirements document defines 30 comprehensive requirements covering all aspects of the Aarogya Sahayak platform:

- **User Roles**: Citizen voice reporting, ASHA worker task management, PHC doctor consultations, district administrator analytics
- **Safety**: Emergency detection, AI verification, human-in-loop oversight
- **Privacy**: PII masking, consent management, audit logging, data retention
- **Accessibility**: Voice-first interface, multilingual support, offline operation, WCAG compliance
- **AI Integration**: Triage engine, clinical RAG, scheme discovery, verifier agents
- **Technical Infrastructure**: Authentication, notification workflows, PDF generation, ABDM preparation
- **Quality**: Performance benchmarks, reliability requirements, testing standards, deployment practices

All requirements follow EARS patterns and INCOSE quality rules for clarity, testability, and completeness.
