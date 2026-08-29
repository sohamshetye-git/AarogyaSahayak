# Aarogya Sahayak Credential Setup Manual

## 1. External AI & Verification Providers

| Environment Variable | Description | Required / Optional | Configured Status | Verification Target |
|:---|:---|:---:|:---:|:---|
| `GEMINI_API_KEY` | Google Gemini API Key | Required | `MOCK` (Blocked by Credentials) | Synthetic Pydantic synthesis and non-diagnostic formatting |
| `LYZR_API_KEY` | Lyzr Agents API Key | Optional | `MOCK` (Falls back to Local) | Coordinates Intake $\rightarrow$ Evidence $\rightarrow$ Scheme agents |
| `BHASHINI_API_KEY` | MeitY BHASHINI API Key | Optional | `MOCK` | Simulated voice intake in Hindi and Marathi |
| `TAVILY_API_KEY` | Tavily Official Search API Key | Optional | `MOCK` | Verifies official government health announcements |

## 2. Self-Generated Secrets (Backend Safety)

| Environment Variable | Description | Configured Status | Security Strategy |
|:---|:---|:---:|:---|
| `JWT_SECRET` | Authentication tokens signature key | `CONFIGURED` | Generated via `openssl rand -hex 32` |
| `N8N_WEBHOOK_SECRET` | HMAC signature payload validator key | `CONFIGURED` | Generated via SHA-256 for follow-up notifications |
| `N8N_ENCRYPTION_KEY` | Database encryption key for local n8n | `CONFIGURED` | Pinned inside docker volumes; never regenerated |

## 3. Database & Local Service Credentials

| Environment Variable | Service Name | Username | Password / Token | Health status |
|:---|:---|:---|:---|:---:|
| `DATABASE_URL` | PostgreSQL | `postgres` | `postgres` | `HEALTHY` |
| `NEO4J_PASSWORD` | Neo4j Graph Database | `neo4j` | `aarogya_password` | `HEALTHY` (Local Service Verified) |
| `MILVUS_URI` | Milvus Vector Database | N/A | None (Development Mode) | `HEALTHY` (Local Service Verified) |

---
**Zero-Secret Invariant**: No raw keys or secrets are committed to git repositories, logs, or frontend code bundles.
