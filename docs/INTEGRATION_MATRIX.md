# Aarogya Sahayak Integration & AI Technology Matrix

| Technology / Adapter | Role in Platform | Current Configured Mode | Health Status | Implementation Status | Real Service Evidence | Limitation & Boundaries |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| **Milvus Clinical RAG** | Vector search over authoritative ICMR & MoHFW guideline passages | `FALLBACK` / `LIVE` | `HEALTHY` | `LOCAL_SERVICE_VERIFIED` | 19 chunks indexed with L2-normalized 384-dim embeddings | Reference only; never auto-prescribes or alters vitals |
| **Neo4j Scheme GraphRAG** | Deterministic graph traversal of government health schemes & eligibility rules | `FALLBACK` / `LIVE` | `HEALTHY` | `LOCAL_SERVICE_VERIFIED` | 3 national/state schemes evaluated via Cypher-equivalent matching | Deterministic graph matching; zero LLM hallucinations |
| **Google Gemini (google-genai)** | Pydantic structured clinical intake & evidence synthesis for doctor review | `FALLBACK` / `LIVE` | `HEALTHY` | `BLOCKED_BY_CREDENTIALS` | Pydantic contracts and safety critic verified | Requires doctor confirmation; diagnosis forbidden |
| **Lyzr Multi-Agent Orchestration** | Coordinates Intake, Evidence, Scheme, and Safety Critic agents | `LOCAL_FALLBACK` | `HEALTHY` | `LOCAL_SERVICE_VERIFIED` | 4-agent execution sequence verified via Pytest | Safety Critic runs last; rejects unauthorized outputs |
| **BHASHINI (MeitY)** | Indian multilingual voice ASR, translation, and TTS (Marathi, Hindi, English) | `MOCK` | `HEALTHY` | `MOCK_VERIFIED` | In-browser speech simulation with consent modal | Mandatory editable confirmation before persistence |
| **Tavily Search** | Verification of official health announcements & scheme portals | `MOCK` | `HEALTHY` | `MOCK_VERIFIED` | Domain whitelist active (`.gov.in`, `nha.gov.in`, `abdm.gov.in`) | Non-official domains blocked; human review required |
| **n8n Automation** | Webhook orchestration for follow-up reminders and escalation alerts | `MOCK` | `HEALTHY` | `MOCK_VERIFIED` | HMAC SHA-256 webhook dispatcher tested | Minimal non-PII payloads; no prescription contents |
| **ABDM Sandbox** | Synthetic ABHA ID validation and consent artifact linking | `MOCK` | `HEALTHY` | `MOCK_VERIFIED` | Synthetic ABHA linking verified (`12-3456-7890-1234`) | Sandbox/Mock only; zero real Aadhaar/OTP data |
| **LiteRT (TensorFlow Lite)** | Offline edge model computing supplemental confidence signals | `MOCK` | `HEALTHY` | `MOCK_VERIFIED` | Tested `LOW/MODERATE/HIGH_MODEL_SIGNAL` | Research model only; deterministic rules override |
| **Swytchcode** | Allow-listed external AI tool execution guardrail | `MOCK` | `HEALTHY` | `ADAPTER_IMPLEMENTED` | Internal allow-listed execution adapter | Blocked from direct PostgreSQL write mutations |
