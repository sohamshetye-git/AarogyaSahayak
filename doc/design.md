# Design Document: Aarogya Sahayak Platform

## Overview

Aarogya Sahayak is a distributed, AI-powered rural healthcare coordination platform that bridges the gap between rural citizens, community health workers (ASHA), primary health centers (PHC), and district administrators. The platform addresses India's rural healthcare challenges through a voice-first, offline-capable, multilingual system that prioritizes safety, human oversight, and citizen privacy.

### Core Design Principles

1. **Safety-First Architecture**: Deterministic emergency detection runs before any AI processing, ensuring life-threatening conditions receive immediate attention
2. **Human-in-the-Loop**: AI provides assistance and suggestions, but humans (ASHA workers and doctors) make all critical decisions
3. **Offline-First Design**: Core functionality works without connectivity, with intelligent sync when connectivity returns
4. **Privacy by Design**: PII is masked before external AI calls, consent is explicit, and data retention is time-bounded
5. **Voice-First Experience**: Audio interfaces remove literacy barriers for rural citizens
6. **Multilingual Support**: Hindi, Marathi, and English throughout the system using BHASHINI government services

### System Context

The platform operates within India's three-tier rural healthcare structure:

```
┌─────────────────┐
│ Rural Citizen   │  Voice reporting in regional language
│ (Mobile App)    │  Offline-capable SQLite cache
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ ASHA Worker     │  Field visits, vital signs, referrals
│ (Web Portal)    │  Offline-capable IndexedDB cache
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ PHC Doctor      │  Consultations, diagnoses, care plans
│ (Web Portal)    │  AI-assisted clinical knowledge
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ District Admin  │  Analytics, cluster detection, resource allocation
│ (Web Portal)    │  Anonymized aggregate metrics
└─────────────────┘
```

### Key Workflows

**Primary Workflow: Citizen Health Concern Journey**

1. **Citizen Reporting**: Rural citizen records voice message in Hindi/Marathi describing health concern
2. **Emergency Detection**: Deterministic rules check for emergency keywords (chest pain, bleeding, suicide)
3. **AI Triage**: Non-emergency cases processed by Lyzr agents with Milvus clinical RAG
4. **ASHA Assignment**: Case routed to geographic ASHA worker with priority level
5. **Field Visit**: ASHA conducts in-person assessment, records vital signs and observations
6. **PHC Referral**: ASHA refers case to PHC doctor with complete context
7. **Consultation**: Doctor reviews, diagnoses, creates care plan, identifies applicable schemes
8. **Citizen Notification**: Citizen receives care plan and PDF report in their language
9. **Follow-up**: System tracks follow-up appointments and case resolution

**Secondary Workflows**:
- **Cluster Detection**: Background analysis identifies geographic disease clusters
- **Offline Sync**: Mobile and web apps queue changes locally and sync when connected
- **Scheme Discovery**: Neo4j graph matches diagnoses to government health schemes
- **Audit Trail**: Every action logged immutably for compliance

## Architecture

### High-Level System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SERVICES                             │
├──────────────────────────────────────────────────────────────────────┤
│ BHASHINI (ASR/TTS)  │  Gemini (LLM)  │  n8n (Notifications)          │
│ Tavily (Search)     │  ABDM (Stub)   │  SMS/WhatsApp Gateway         │
└──────────────────────────────────────────────────────────────────────┘
                                  ↑
                                  │ HTTPS/REST
                                  │
┌─────────────────────────────────┴─────────────────────────────────────┐
│                          CLIENT APPLICATIONS                           │
├───────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐         ┌──────────────────────────────────┐  │
│  │ Citizen Mobile   │         │    Healthcare Portal             │  │
│  │                  │         │                                  │  │
│  │ React Native     │         │ React + Vite                     │  │
│  │ + Expo           │         │                                  │  │
│  │                  │         │ ┌──────┬──────┬──────┬────────┐ │  │
│  │ SQLite Cache     │         │ │ ASHA │Doctor│Admin │        │ │  │
│  │ TFLite Model     │         │ │ View │ View │ View │        │ │  │
│  │ Voice Recording  │         │ └──────┴──────┴──────┘        │ │  │
│  │                  │         │                                  │  │
│  │                  │         │ IndexedDB Cache                  │  │
│  └──────────────────┘         └──────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
                                  ↑
                                  │ REST API + JWT Auth
                                  │
┌─────────────────────────────────┴─────────────────────────────────────┐
│                          BACKEND API LAYER                             │
├───────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                     FastAPI Application                        │  │
│  │                                                                │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │  │
│  │  │  Auth    │  │  Cases   │  │  Users   │  │  Analytics   │  │  │
│  │  │  Router  │  │  Router  │  │  Router  │  │  Router      │  │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │  │
│  │       │             │             │               │           │  │
│  │       └─────────────┴─────────────┴───────────────┘           │  │
│  │                           │                                    │  │
│  │  ┌────────────────────────┴──────────────────────────────┐   │  │
│  │  │               Service Layer                           │   │  │
│  │  │                                                        │   │  │
│  │  │  • EmergencyDetectionService (Deterministic Rules)    │   │  │
│  │  │  • TriageService (Lyzr Agents + Milvus RAG)          │   │  │
│  │  │  • PIIMaskingService                                  │   │  │
│  │  │  • BhashiniService (ASR, TTS, Translation)           │   │  │
│  │  │  • NotificationService (n8n Integration)             │   │  │
│  │  │  • ClusterDetectionService                           │   │  │
│  │  │  • SchemeDiscoveryService (Neo4j)                    │   │  │
│  │  │  • ReportGenerationService (WeasyPrint)              │   │  │
│  │  │  • AuditLoggingService                               │   │  │
│  │  │                                                        │   │  │
│  │  └────────────────────────┬──────────────────────────────┘   │  │
│  │                           │                                    │  │
│  │  ┌────────────────────────┴──────────────────────────────┐   │  │
│  │  │             Repository Layer                          │   │  │
│  │  │                                                        │   │  │
│  │  │  • UserRepository          • CaseRepository           │   │  │
│  │  │  • VisitRepository         • ConsultationRepository   │   │  │
│  │  │  • AuditLogRepository      • ConsentRepository        │   │  │
│  │  │                                                        │   │  │
│  │  └────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
                                  ↑
                                  │
┌─────────────────────────────────┴─────────────────────────────────────┐
│                         DATA STORAGE LAYER                             │
├───────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │ PostgreSQL  │  │   Milvus    │  │   Neo4j     │  │   Object   │  │
│  │             │  │             │  │             │  │   Storage  │  │
│  │ • Cases     │  │ • Clinical  │  │ • Schemes   │  │            │  │
│  │ • Users     │  │   Knowledge │  │ • Elig.     │  │ • PDFs     │  │
│  │ • Visits    │  │   Vectors   │  │   Rules     │  │ • Audio    │  │
│  │ • Consults  │  │             │  │ • Benefit   │  │ • Images   │  │
│  │ • Audit Log │  │             │  │   Graph     │  │            │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

**Case Creation Flow with Safety Checks**:

```
Citizen App                Backend API                    AI Services
     │                          │                              │
     │ POST /cases/create       │                              │
     │ {audio, metadata}        │                              │
     ├─────────────────────────>│                              │
     │                          │                              │
     │                          │ 1. Deterministic Rules       │
     │                          │    (Emergency Detection)     │
     │                          │    < 500ms                   │
     │                          │                              │
     │                          │ IF EMERGENCY:               │
     │                          │   - Mark priority           │
     │                          │   - Notify ASHA            │
     │                          │   - Skip AI                │
     │                          │                              │
     │                          │ IF NOT EMERGENCY:           │
     │                          │                              │
     │                          │ 2. PII Masking              │
     │                          │                              │
     │                          │ 3. Lyzr Agent Triage        │
     │                          ├────────────────────────────>│
     │                          │                              │
     │                          │    Milvus Clinical RAG      │
     │                          │<─────────────────────────────│
     │                          │    (Similarity Search)      │
     │                          │                              │
     │                          │    Gemini LLM               │
     │                          │<─────────────────────────────│
     │                          │    (Reasoning + Synthesis)  │
     │                          │                              │
     │                          │ 4. Verifier Agent            │
     │                          │    (Grounds AI Output)       │
     │                          │                              │
     │                          │ 5. Audit Logging            │
     │                          │                              │
     │<─────────────────────────┤                              │
     │ {case_id, priority,      │                              │
     │  triage_notes, sources}  │                              │
     │                          │                              │
```

### AI Agent Orchestration

The platform uses Lyzr agent framework for multi-step AI reasoning:

```
┌──────────────────────────────────────────────────────────────┐
│                    Lyzr Agent Workflow                        │
└──────────────────────────────────────────────────────────────┘
                              │
                              ↓
                    ┌─────────────────┐
                    │  Router Agent   │
                    │                 │
                    │ Determines task │
                    │ type and routes │
                    └────────┬────────┘
                             │
            ┌────────────────┴────────────────┐
            │                                 │
            ↓                                 ↓
   ┌────────────────┐              ┌────────────────┐
   │ Clinical Agent │              │ Scheme Agent   │
   │                │              │                │
   │ • Queries      │              │ • Queries Neo4j│
   │   Milvus RAG   │              │ • Matches ICD  │
   │ • Assesses     │              │   codes        │
   │   symptoms     │              │ • Returns      │
   │ • Assigns      │              │   eligible     │
   │   priority     │              │   schemes      │
   │ • Suggests     │              │                │
   │   next steps   │              │                │
   └────────┬───────┘              └────────┬───────┘
            │                               │
            └───────────────┬───────────────┘
                            │
                            ↓
                  ┌─────────────────┐
                  │ Verifier Agent  │
                  │                 │
                  │ • Validates     │
                  │   claims        │
                  │ • Checks        │
                  │   sources       │
                  │ • Removes       │
                  │   unsupported   │
                  │   content       │
                  │ • Adds citation │
                  │   labels        │
                  └─────────────────┘
```

## Components and Interfaces

### 1. Citizen Mobile Application

**Technology Stack**: React Native + Expo, TypeScript, SQLite, TensorFlow Lite

**Key Components**:


```
CitizenApp/
├── screens/
│   ├── OnboardingScreen          # Language selection, consent
│   ├── HomeScreen                # Active cases, create new case
│   ├── VoiceRecordingScreen      # Audio recording UI
│   ├── CaseDetailScreen          # Status, care plan, PDF
│   └── SettingsScreen            # Profile, language, consent
├── components/
│   ├── VoiceRecorder             # Audio capture, waveform visualization
│   ├── AudioPlayer               # Playback with translation
│   ├── CaseStatusCard            # Visual status indicator
│   ├── LanguageSelector          # Hindi/Marathi/English
│   └── ConsentForm               # Scrollable, audio-enabled
├── services/
│   ├── OfflineSyncService        # SQLite queue management
│   ├── TFLiteTriageService       # Offline ML inference
│   ├── AudioService              # Recording, compression, playback
│   ├── APIClient                 # HTTP client with retry logic
│   └── NotificationService       # Push notification handling
├── storage/
│   ├── SQLiteDatabase            # Cases, audio files, sync queue
│   └── SecureStorage             # JWT tokens, user credentials
└── utils/
    ├── NetworkMonitor            # Connectivity detection
    └── LanguageProvider          # i18n context
```

**Interface: Citizen Mobile → Backend API**

```typescript
// POST /api/v1/cases
interface CreateCaseRequest {
  audio_base64: string;           // Compressed audio (max 1MB/min)
  language: 'hi' | 'mr' | 'en';
  duration_seconds: number;
  recorded_at: string;            // ISO 8601 timestamp
  device_metadata: {
    os: string;
    app_version: string;
    device_id: string;
  };
  offline_created: boolean;       // True if syncing from SQLite
  idempotency_key: string;        // UUID for offline sync
}

interface CreateCaseResponse {
  case_id: string;
  priority: 'EMERGENCY' | 'URGENT' | 'ROUTINE' | 'INFORMATIONAL';
  transcript: string;
  triage_notes: string;
  estimated_response_time_hours: number;
  assigned_asha_worker?: {
    name: string;
    phone: string;
  };
}

// GET /api/v1/cases/{case_id}
interface CaseDetailResponse {
  case_id: string;
  status: CaseStatus;
  priority: Priority;
  created_at: string;
  transcript: string;
  timeline: CaseTimelineEvent[];
  care_plan?: CarePlan;
  consultation_pdf_url?: string;
  next_follow_up?: string;
}

type CaseStatus = 
  | 'SUBMITTED'
  | 'ACKNOWLEDGED'
  | 'FIELD_VISIT_SCHEDULED'
  | 'FIELD_VISIT_COMPLETED'
  | 'UNDER_DOCTOR_REVIEW'
  | 'CONSULTATION_COMPLETED'
  | 'RESOLVED';
```

**Offline Sync Strategy**:

1. **Queue Management**: SQLite table `sync_queue` with columns: `id`, `operation_type`, `payload_json`, `created_at`, `retry_count`, `status`
2. **Conflict Resolution**: Last-write-wins for client updates, server timestamp is authoritative
3. **Idempotency**: Every offline-created case includes UUID idempotency key
4. **Retry Logic**: Exponential backoff (1s, 2s, 4s, 8s, 16s max) for failed syncs
5. **Background Sync**: Uses Expo TaskManager for background execution when app is closed

### 2. Healthcare Portal

**Technology Stack**: React + Vite, TypeScript, React Query, IndexedDB, Recharts

**Key Components**:

```
HealthcarePortal/
├── features/
│   ├── auth/
│   │   ├── LoginForm              # Username/password
│   │   ├── RoleBasedRoute         # RBAC enforcement
│   │   └── SessionManager         # Token refresh, timeout
│   ├── asha/
│   │   ├── TaskDashboard          # Prioritized case list
│   │   ├── FieldVisitForm         # Vital signs, observations
│   │   ├── ReferralForm           # PHC referral creation
│   │   └── CaseMap                # Geographic case visualization
│   ├── doctor/
│   │   ├── ReferralQueue          # Cases from ASHA
│   │   ├── ConsultationForm       # Diagnosis, care plan
│   │   ├── SchemeRecommendations  # Neo4j scheme matches
│   │   ├── ClinicalKnowledge      # RAG-sourced info panel
│   │   └── PrescriptionBuilder    # Medication entry
│   └── admin/
│       ├── AnalyticsDashboard     # Aggregate metrics
│       ├── ClusterAlertPanel      # Geographic clusters
│       ├── WorkloadMonitor        # ASHA/PHC capacity
│       └── DataExport             # CSV download
├── components/
│   ├── CaseCard                   # Reusable case display
│   ├── PriorityBadge              # Color-coded urgency
│   ├── SourceCitation             # AI source references
│   ├── AudioPlayer                # BHASHINI audio playback
│   └── NotificationToast          # Real-time alerts
├── services/
│   ├── APIClient                  # Typed Axios client
│   ├── OfflineStorage             # IndexedDB wrapper
│   ├── AuthService                # JWT management
│   └── NotificationService        # SSE/WebSocket
├── hooks/
│   ├── useCases                   # React Query cases
│   ├── useAuth                    # Auth context
│   ├── useOfflineSync             # IndexedDB sync
│   └── useNotifications           # SSE subscription
└── utils/
    ├── validators                 # Form validation
    └── formatters                 # Date, number formatting
```

**Interface: Healthcare Portal → Backend API**

```typescript
// POST /api/v1/visits
interface CreateFieldVisitRequest {
  case_id: string;
  vital_signs: {
    blood_pressure_systolic: number;    // 60-250
    blood_pressure_diastolic: number;   // 40-180
    temperature_celsius: number;        // 35-42
    pulse_rate_bpm: number;             // 30-200
    respiratory_rate_bpm: number;       // 8-40
  };
  observations: string;                 // Text notes
  symptom_photos: string[];             // Base64 images
  referral_needed: boolean;
  urgency_notes?: string;
  recorded_at: string;
}

// POST /api/v1/consultations
interface CreateConsultationRequest {
  case_id: string;
  diagnosis_icd10_codes: string[];      // ['A09', 'R50.9']
  diagnosis_text: string;
  care_plan: {
    treatment_instructions: string;
    lifestyle_recommendations: string;
    follow_up_days?: number;
    warning_signs: string;
  };
  prescriptions: Array<{
    medication_name: string;
    dosage: string;
    frequency: string;
    duration_days: number;
    instructions: string;
  }>;
  recommended_schemes: string[];        // Scheme IDs from Neo4j
  additional_notes?: string;
}

// GET /api/v1/schemes/search
interface SchemeSearchRequest {
  diagnosis_icd10_codes: string[];
  patient_age: number;
  patient_gender: 'M' | 'F' | 'O';
  income_level?: 'BPL' | 'APL';
  state: string;
}

interface SchemeSearchResponse {
  schemes: Array<{
    scheme_id: string;
    scheme_name: string;
    scheme_name_hi: string;
    scheme_name_mr: string;
    coverage_amount_inr: number;
    eligibility_criteria: string[];
    application_process: string;
    source_url: string;
  }>;
}
```

**Role-Based Access Control**:

```typescript
enum UserRole {
  CITIZEN = 'CITIZEN',
  ASHA = 'ASHA',
  DOCTOR = 'DOCTOR',
  ADMIN = 'ADMIN'
}

const permissions = {
  CITIZEN: [
    'cases:create',
    'cases:read_own',
    'care_plans:read_own'
  ],
  ASHA: [
    'cases:read_assigned',
    'cases:acknowledge',
    'visits:create',
    'referrals:create'
  ],
  DOCTOR: [
    'cases:read_referred',
    'consultations:create',
    'prescriptions:create',
    'schemes:search'
  ],
  ADMIN: [
    'analytics:read',
    'cases:read_all_anonymized',
    'clusters:read',
    'audit_logs:read'
  ]
};
```

### 3. Backend API

**Technology Stack**: FastAPI, Python 3.11+, SQLAlchemy, Alembic, Pydantic

**Layered Architecture**:

```
backend/
├── api/
│   ├── v1/
│   │   ├── routers/
│   │   │   ├── auth.py            # Login, refresh, logout
│   │   │   ├── cases.py           # Case CRUD, list, search
│   │   │   ├── visits.py          # Field visit operations
│   │   │   ├── consultations.py   # Doctor consultations
│   │   │   ├── users.py           # User management
│   │   │   ├── analytics.py       # Aggregate metrics
│   │   │   ├── schemes.py         # Scheme search
│   │   │   └── health.py          # Health check, metrics
│   │   └── dependencies.py        # Auth, DB session
├── services/
│   ├── emergency_detection.py     # Deterministic rules
│   ├── triage_service.py          # Lyzr agent orchestration
│   ├── pii_masking.py             # PII redaction
│   ├── bhashini_client.py         # ASR, TTS, translation
│   ├── notification_service.py    # n8n webhook triggers
│   ├── cluster_detection.py       # Geographic analysis
│   ├── scheme_discovery.py        # Neo4j queries
│   ├── report_generation.py       # WeasyPrint PDF
│   ├── audit_logging.py           # Immutable audit log
│   └── ai/
│       ├── lyzr_agents.py         # Router, Clinical, Scheme, Verifier
│       ├── milvus_rag.py          # Vector similarity search
│       └── tflite_export.py       # Offline model creation
├── repositories/
│   ├── user_repository.py
│   ├── case_repository.py
│   ├── visit_repository.py
│   ├── consultation_repository.py
│   ├── audit_log_repository.py
│   └── consent_repository.py
├── models/
│   ├── user.py                    # SQLAlchemy ORM models
│   ├── case.py
│   ├── visit.py
│   ├── consultation.py
│   ├── audit_log.py
│   └── consent.py
├── schemas/
│   ├── case.py                    # Pydantic request/response schemas
│   ├── visit.py
│   ├── consultation.py
│   └── user.py
├── core/
│   ├── config.py                  # Environment configuration
│   ├── security.py                # JWT, bcrypt, RBAC
│   ├── database.py                # SQLAlchemy engine
│   └── exceptions.py              # Custom exception classes
├── migrations/                    # Alembic database migrations
└── tests/
    ├── unit/                      # Unit tests (>80% coverage)
    ├── integration/               # API endpoint tests
    ├── property_based/            # Hypothesis tests
    └── e2e/                       # Full workflow tests
```

**Core Services Design**:

#### EmergencyDetectionService

```python
class EmergencyDetectionService:
    """
    Deterministic rule-based emergency detection.
    Executes before any AI processing to catch life-threatening conditions.
    """
    
    EMERGENCY_KEYWORDS = {
        'hi': [
            'छाती में दर्द', 'सांस लेने में तकलीफ', 
            'खून बह रहा है', 'बेहोश', 'आत्महत्या'
        ],
        'mr': [
            'छातीत वेदना', 'श्वास घेण्यात त्रास',
            'रक्तस्त्राव', 'बेशुद्ध', 'आत्महत्या'
        ],
        'en': [
            'chest pain', 'difficulty breathing', 'severe bleeding',
            'unconscious', 'suicide', 'cannot breathe'
        ]
    }
    
    def detect_emergency(
        self, 
        transcript: str, 
        language: str
    ) -> tuple[bool, list[str]]:
        """
        Returns (is_emergency, matched_keywords).
        Must execute in < 500ms.
        """
        keywords = self.EMERGENCY_KEYWORDS.get(language, [])
        transcript_lower = transcript.lower()
        
        matched = [
            kw for kw in keywords 
            if kw.lower() in transcript_lower
        ]
        
        return (len(matched) > 0, matched)
```

#### PIIMaskingService

```python
class PIIMaskingService:
    """
    Masks PII before sending data to external AI services.
    Implements requirement 4: PII Protection in AI Processing.
    """
    
    PII_PATTERNS = {
        'phone': r'\b\d{10}\b',
        'aadhaar': r'\b\d{4}\s?\d{4}\s?\d{4}\b',
        'pincode': r'\b\d{6}\b'
    }
    
    def mask_for_ai(self, case_data: dict) -> dict:
        """
        Returns a sanitized copy with PII removed/masked.
        Preserves: age, gender, health concern text (with names masked).
        """
        masked = {
            'age': case_data['age'],
            'gender': case_data['gender'],
            'transcript': self._mask_names(case_data['transcript']),
            'case_id_internal': case_data['case_id']
        }
        
        # Remove coordinates, phone, address, aadhaar
        return masked
    
    def _mask_names(self, text: str) -> str:
        """Replace person names with CITIZEN_001, CITIZEN_002."""
        # Use spaCy NER for Hindi/Marathi/English
        # Replace PERSON entities with anonymized IDs
        pass
```

#### TriageService (Lyzr Agent Orchestration)

```python
class TriageService:
    """
    Orchestrates AI-assisted triage using Lyzr agents.
    """
    
    def __init__(
        self,
        lyzr_client: LyzrClient,
        milvus_rag: MilvusRAGService,
        verifier: VerifierAgent,
        audit_logger: AuditLoggingService
    ):
        self.lyzr = lyzr_client
        self.rag = milvus_rag
        self.verifier = verifier
        self.audit = audit_logger
    
    async def triage_case(
        self,
        case_id: str,
        masked_data: dict
    ) -> TriageResult:
        """
        Execute multi-agent triage workflow:
        1. Router agent determines task
        2. Clinical agent queries Milvus RAG
        3. Verifier agent grounds output
        4. Return prioritized assessment
        """
        
        # Step 1: Router agent
        task = await self.lyzr.router_agent.classify(
            masked_data['transcript']
        )
        
        # Step 2: Clinical agent with RAG
        rag_results = await self.rag.search_clinical_knowledge(
            query=masked_data['transcript'],
            top_k=5
        )
        
        clinical_assessment = await self.lyzr.clinical_agent.assess(
            transcript=masked_data['transcript'],
            context=rag_results
        )
        
        # Step 3: Verifier agent
        verified = await self.verifier.verify_claims(
            assessment=clinical_assessment,
            sources=rag_results
        )
        
        # Step 4: Audit logging
        await self.audit.log_triage(
            case_id=case_id,
            inputs=masked_data,
            outputs=verified
        )
        
        return TriageResult(
            priority=verified.priority,
            notes=verified.notes,
            sources=verified.source_labels,
            next_steps=verified.recommendations
        )
```

### 4. AI and Knowledge Services

#### Milvus Clinical RAG

**Schema Design**:

```python
# Milvus Collection: clinical_knowledge
{
    'chunk_id': 'string (primary key)',
    'embedding': 'float_vector[768]',      # Sentence-BERT multilingual
    'text_hi': 'string',
    'text_mr': 'string',
    'text_en': 'string',
    'source_document': 'string',          # WHO guideline, ICMR protocol
    'source_page': 'int',
    'publication_date': 'datetime',
    'category': 'string',                 # symptom, treatment, prevention
    'metadata': 'json'
}

# Index: HNSW (Hierarchical Navigable Small World)
# Metric: Cosine similarity
# Parameters: M=16, efConstruction=256
```

**RAG Query Flow**:

```python
class MilvusRAGService:
    def __init__(self, milvus_client, embedding_model):
        self.client = milvus_client
        self.model = embedding_model  # sentence-transformers/paraphrase-multilingual
    
    async def search_clinical_knowledge(
        self,
        query: str,
        top_k: int = 5,
        language: str = 'en'
    ) -> list[RAGResult]:
        """
        1. Generate query embedding
        2. Search Milvus with cosine similarity
        3. Return results with source labels
        """
        
        # Embed query
        query_vector = self.model.encode(query)
        
        # Search Milvus
        results = self.client.search(
            collection_name='clinical_knowledge',
            data=[query_vector],
            anns_field='embedding',
            param={'metric_type': 'COSINE', 'top_k': top_k},
            limit=top_k,
            output_fields=['text_en', 'text_hi', 'text_mr', 
                          'source_document', 'source_page']
        )
        
        # Format with source labels
        return [
            RAGResult(
                text=r[f'text_{language}'],
                source=f"{r['source_document']} (p. {r['source_page']})",
                similarity_score=r['distance']
            )
            for r in results[0]
        ]
```

#### Neo4j Scheme Graph

**Graph Schema**:

```cypher
// Node types
(:Scheme {
  scheme_id: string,
  name_en: string,
  name_hi: string,
  name_mr: string,
  coverage_amount: int,
  state: string,
  scheme_type: string  // national, state
})

(:Condition {
  icd10_code: string,
  name_en: string,
  category: string
})

(:Eligibility {
  criteria_type: string,  // age, gender, income, location
  min_value: int,
  max_value: int,
  required_value: string
})

// Relationships
(:Scheme)-[:COVERS]->(:Condition)
(:Scheme)-[:REQUIRES]->(:Eligibility)
(:Condition)-[:PARENT_CONDITION]->(:Condition)  // ICD hierarchy
```

**Scheme Discovery Query**:

```cypher
// Find schemes matching diagnosis and demographics
MATCH (s:Scheme)-[:COVERS]->(c:Condition)
WHERE c.icd10_code IN $icd_codes
  AND (s.state = $patient_state OR s.scheme_type = 'national')

MATCH (s)-[:REQUIRES]->(e:Eligibility)
WHERE 
  (e.criteria_type = 'age' AND $patient_age >= e.min_value AND $patient_age <= e.max_value)
  OR (e.criteria_type = 'gender' AND e.required_value = $patient_gender)
  OR (e.criteria_type = 'income' AND e.required_value = $patient_income_level)

WITH s, COUNT(DISTINCT e) as matched_criteria
RETURN s.scheme_id, s.name_en, s.name_hi, s.name_mr, 
       s.coverage_amount, s.application_process
ORDER BY matched_criteria DESC
LIMIT 10
```

#### TensorFlow Lite Offline Model

**Architecture**:

```
Input: Text embedding (768-dim multilingual BERT)
       ↓
Dense Layer (768 → 256, ReLU)
       ↓
Dropout (0.3)
       ↓
Dense Layer (256 → 64, ReLU)
       ↓
Dense Layer (64 → 3, Softmax)
       ↓
Output: [EMERGENCY, URGENT, ROUTINE] probabilities
```

**Training Data**: Historical cases with human-verified priority labels

**Quantization**: Post-training quantization to INT8 for mobile efficiency

**Model Size**: ~2 MB (deployable over 2G)

**Inference Time**: < 2 seconds on mid-range Android device

## Data Models

### PostgreSQL Schema

#### Users Table

```sql
CREATE TYPE user_role AS ENUM ('CITIZEN', 'ASHA', 'DOCTOR', 'ADMIN');
CREATE TYPE user_status AS ENUM ('ACTIVE', 'INACTIVE', 'SUSPENDED');

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(15) UNIQUE,          -- For citizens
    username VARCHAR(100) UNIQUE,             -- For healthcare workers
    password_hash VARCHAR(255),               -- bcrypt hash
    full_name VARCHAR(255) NOT NULL,
    role user_role NOT NULL,
    status user_status DEFAULT 'ACTIVE',
    preferred_language VARCHAR(2) DEFAULT 'en', -- hi, mr, en
    age INT,
    gender VARCHAR(1),                        -- M, F, O
    state VARCHAR(50),
    district VARCHAR(100),
    block VARCHAR(100),                       -- For ASHA geographic assignment
    phc_facility_id UUID,                     -- For doctors
    abdm_health_id VARCHAR(14),               -- Optional ABDM integration
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);

CREATE INDEX idx_users_phone ON users(phone_number);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_geographic ON users(district, block) WHERE role = 'ASHA';
```

#### Cases Table

```sql
CREATE TYPE case_priority AS ENUM ('EMERGENCY', 'URGENT', 'ROUTINE', 'INFORMATIONAL');
CREATE TYPE case_status AS ENUM (
    'SUBMITTED',
    'ACKNOWLEDGED',
    'FIELD_VISIT_SCHEDULED',
    'FIELD_VISIT_COMPLETED',
    'UNDER_DOCTOR_REVIEW',
    'CONSULTATION_COMPLETED',
    'RESOLVED'
);

CREATE TABLE cases (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id UUID NOT NULL REFERENCES users(user_id),
    priority case_priority NOT NULL,
    status case_status DEFAULT 'SUBMITTED',
    
    -- Audio and transcript
    audio_file_url VARCHAR(500),
    audio_duration_seconds INT,
    transcript TEXT NOT NULL,
    transcript_language VARCHAR(2),
    
    -- Emergency detection
    emergency_detected BOOLEAN DEFAULT FALSE,
    emergency_keywords TEXT[],
    
    -- AI triage (NULL if emergency bypass)
    triage_priority case_priority,
    triage_notes TEXT,
    triage_sources JSONB,                    -- Source labels
    
    -- Assignment
    assigned_asha_id UUID REFERENCES users(user_id),
    assigned_doctor_id UUID REFERENCES users(user_id),
    assigned_at TIMESTAMP,
    acknowledged_at TIMESTAMP,
    
    -- Geographic
    location_lat DECIMAL(10, 8),
    location_lon DECIMAL(11, 8),
    location_accuracy_meters INT,
    
    -- Metadata
    offline_created BOOLEAN DEFAULT FALSE,
    idempotency_key UUID UNIQUE,
    device_metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    
    CONSTRAINT fk_assigned_asha 
        FOREIGN KEY (assigned_asha_id) 
        REFERENCES users(user_id),
    CONSTRAINT fk_assigned_doctor 
        FOREIGN KEY (assigned_doctor_id) 
        REFERENCES users(user_id)
);

CREATE INDEX idx_cases_citizen ON cases(citizen_id);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_priority ON cases(priority);
CREATE INDEX idx_cases_assigned_asha ON cases(assigned_asha_id, status);
CREATE INDEX idx_cases_assigned_doctor ON cases(assigned_doctor_id, status);
CREATE INDEX idx_cases_created ON cases(created_at DESC);
CREATE INDEX idx_cases_geographic ON cases(location_lat, location_lon);
CREATE INDEX idx_cases_idempotency ON cases(idempotency_key);
```

#### Field Visits Table

```sql
CREATE TABLE field_visits (
    visit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(case_id),
    asha_worker_id UUID NOT NULL REFERENCES users(user_id),
    
    -- Vital signs
    bp_systolic INT CHECK (bp_systolic BETWEEN 60 AND 250),
    bp_diastolic INT CHECK (bp_diastolic BETWEEN 40 AND 180),
    temperature_celsius DECIMAL(4, 2) CHECK (temperature_celsius BETWEEN 35 AND 42),
    pulse_rate_bpm INT CHECK (pulse_rate_bpm BETWEEN 30 AND 200),
    respiratory_rate_bpm INT CHECK (respiratory_rate_bpm BETWEEN 8 AND 40),
    
    -- Observations
    observations TEXT NOT NULL,
    symptom_photo_urls TEXT[],
    
    -- Referral decision
    referral_needed BOOLEAN DEFAULT FALSE,
    urgency_notes TEXT,
    
    -- Metadata
    offline_created BOOLEAN DEFAULT FALSE,
    device_timestamp TIMESTAMP,
    server_timestamp TIMESTAMP DEFAULT NOW(),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_visits_case ON field_visits(case_id);
CREATE INDEX idx_visits_asha ON field_visits(asha_worker_id);
```

#### Consultations Table

```sql
CREATE TABLE consultations (
    consultation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(case_id),
    doctor_id UUID NOT NULL REFERENCES users(user_id),
    
    -- Diagnosis
    diagnosis_icd10_codes VARCHAR(10)[],
    diagnosis_text TEXT NOT NULL,
    
    -- Care plan
    treatment_instructions TEXT NOT NULL,
    lifestyle_recommendations TEXT,
    warning_signs TEXT,
    follow_up_days INT,
    next_follow_up_date DATE,
    
    -- Prescriptions (denormalized for simplicity)
    prescriptions JSONB,  -- Array of {medication, dosage, frequency, duration, instructions}
    
    -- Scheme recommendations
    recommended_scheme_ids TEXT[],
    
    -- Report generation
    report_pdf_url VARCHAR(500),
    report_generated_at TIMESTAMP,
    report_expires_at TIMESTAMP,
    
    -- Additional notes
    additional_notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_consultations_case ON consultations(case_id);
CREATE INDEX idx_consultations_doctor ON consultations(doctor_id);
CREATE INDEX idx_consultations_icd10 ON consultations USING GIN(diagnosis_icd10_codes);
```

#### Audit Logs Table

```sql
CREATE TYPE audit_action AS ENUM (
    'USER_LOGIN',
    'USER_LOGOUT',
    'AUTH_FAILURE',
    'CASE_CREATE',
    'CASE_UPDATE',
    'CASE_ACCESS',
    'VISIT_CREATE',
    'CONSULTATION_CREATE',
    'CONSENT_ACCEPT',
    'CONSENT_WITHDRAW',
    'AI_TRIAGE',
    'AI_VERIFIER',
    'EMERGENCY_DETECT',
    'NOTIFICATION_SEND',
    'DATA_EXPORT',
    'DATA_DELETE'
);

CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP DEFAULT NOW() NOT NULL,
    
    -- Actor
    user_id UUID REFERENCES users(user_id),
    user_role user_role,
    ip_address INET,
    
    -- Action
    action audit_action NOT NULL,
    resource_type VARCHAR(50),              -- case, visit, consultation
    resource_id UUID,
    
    -- Details
    action_details JSONB,                   -- Flexible storage for specifics
    ai_inputs JSONB,                        -- For AI operations
    ai_outputs JSONB,
    
    -- Compliance
    data_classification VARCHAR(20),        -- PII, PHI, PUBLIC
    retention_until DATE                    -- Based on data type
);

-- Append-only table: No UPDATE or DELETE permissions for any role
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
```

#### Consent Records Table

```sql
CREATE TYPE consent_status AS ENUM ('ACCEPTED', 'WITHDRAWN');

CREATE TABLE consent_records (
    consent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    status consent_status NOT NULL,
    consent_text TEXT NOT NULL,              -- Full text shown to user
    consent_version VARCHAR(10) NOT NULL,    -- v1.0, v1.1, etc.
    language VARCHAR(2) NOT NULL,
    
    -- Timestamps
    accepted_at TIMESTAMP,
    withdrawn_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_consent_user ON consent_records(user_id);
CREATE INDEX idx_consent_status ON consent_records(status);
```

#### Cluster Alerts Table

```sql
CREATE TABLE cluster_alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Cluster details
    symptom_pattern TEXT NOT NULL,
    case_count INT NOT NULL,
    center_lat DECIMAL(10, 8),
    center_lon DECIMAL(11, 8),
    radius_km DECIMAL(5, 2),
    
    -- Time window
    first_case_at TIMESTAMP,
    last_case_at TIMESTAMP,
    
    -- Associated cases
    case_ids UUID[],
    
    -- Admin action
    acknowledged_by UUID REFERENCES users(user_id),
    acknowledged_at TIMESTAMP,
    dismissed_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cluster_acknowledged ON cluster_alerts(acknowledged_at) 
    WHERE acknowledged_at IS NULL;
```

### SQLite Offline Schema (Citizen Mobile)

```sql
-- Simplified schema for offline storage on device

CREATE TABLE offline_cases (
    local_id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT UNIQUE,                    -- NULL until synced
    audio_file_path TEXT,
    transcript TEXT,
    priority TEXT,
    created_at TEXT,
    synced BOOLEAN DEFAULT 0,
    sync_attempts INTEGER DEFAULT 0
);

CREATE TABLE sync_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type TEXT CHECK(operation_type IN ('CREATE_CASE', 'UPDATE_CASE')),
    payload_json TEXT NOT NULL,
    idempotency_key TEXT UNIQUE,
    created_at TEXT,
    retry_count INTEGER DEFAULT 0,
    last_attempt_at TEXT,
    status TEXT CHECK(status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')),
    error_message TEXT
);

CREATE TABLE tflite_predictions (
    local_case_id INTEGER REFERENCES offline_cases(local_id),
    predicted_priority TEXT,
    confidence REAL,
    model_version TEXT,
    predicted_at TEXT
);
```

### IndexedDB Schema (Healthcare Portal)

```typescript
// IndexedDB stores for offline operation in browser

interface OfflineDraft {
  draftId: string;                        // UUID
  caseId: string;
  formType: 'field_visit' | 'consultation';
  formData: Record<string, any>;
  createdAt: string;
  lastModifiedAt: string;
  synced: boolean;
}

interface CachedCase {
  caseId: string;
  caseData: any;                          // Full case object
  cachedAt: string;
  expiresAt: string;
}

const db = {
  name: 'AarogyaSahayakPortal',
  version: 1,
  stores: {
    offline_drafts: {
      keyPath: 'draftId',
      indexes: ['caseId', 'synced']
    },
    cached_cases: {
      keyPath: 'caseId',
      indexes: ['expiresAt']
    },
    sync_queue: {
      keyPath: 'queueId',
      autoIncrement: true,
      indexes: ['status', 'createdAt']
    }
  }
};
```

