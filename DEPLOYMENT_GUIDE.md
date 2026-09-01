# Aarogya Sahayak Deployment Guide (Staging & Production)

This guide documents the unified deployment process for **Aarogya Sahayak** using:
1. **Render Blueprint (`render.yaml`)** for Backend API & Managed PostgreSQL.
2. **Vercel Monorepo Projects** for the Citizen Mobile PWA and Healthcare Portal SPA.

---

## 1. Deployment Architecture

```text
Vercel (Frontend Hosting)
├── Citizen Mobile PWA (apps/citizen-mobile)
│     └── URL: https://aarogya-citizen.vercel.app
└── Healthcare Portal SPA (apps/healthcare-portal)
      └── URL: https://aarogya-portal.vercel.app

Render Singapore (Backend & Database)
├── Managed PostgreSQL 16 (aarogya-sahayak-db)
└── FastAPI Web Service (aarogya-sahayak-backend)
      ├── REST API: https://<backend>.onrender.com/api
      ├── WebSockets: wss://<backend>.onrender.com/api/ws
      └── Health Check: https://<backend>.onrender.com/health
```

---

## 2. Step 1: Deploy Backend & Database via Render Blueprint

All backend infrastructure (FastAPI Web Service + Managed PostgreSQL 16 database) is declared in [render.yaml](file:///c:/Arogya%20Sahayak_AI_antigravity/render.yaml). Do not manually create duplicate database or web service instances in Render.

### Deployment Workflow:

```text
Render Dashboard
→ New
→ Blueprint
→ Connect GitHub repository (sohamshetye-git/AarogyaSahayak)
→ Select render.yaml
→ Review resources (aarogya-sahayak-db & aarogya-sahayak-backend)
→ Enter required secret variables
→ Apply Blueprint
```

### Resource Details Declared in `render.yaml` (Free Staging Tier):

| Resource | Type | Region | Plan | Key Settings |
| :--- | :--- | :--- | :--- | :--- |
| `aarogya-sahayak-db` | PostgreSQL 16 | Singapore | Free (`plan: free`) | `postgresMajorVersion: "16"`, `databaseName: aarogya_db`, `user: aarogya_user` |
| `aarogya-sahayak-backend` | Web Service (Python 3) | Singapore | Free (`plan: free`) | `startCommand: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`<br>`healthCheckPath: /health` |

> [!IMPORTANT]
> **Render Free Tier Staging Characteristics & Constraints:**
> * **No Credit Card / Payment Required**: Both the PostgreSQL database and FastAPI Web Service run on Render's 100% free plan.
> * **Zero Cost**: Blueprint sync and deployment require no billing setup.
> * **Web Service Sleep / Spin-down**: The backend spins down after 15 minutes of inactivity. When a new request arrives, initial wake-up time is ~50-60 seconds.
> * **Database Limits**: Render Free PostgreSQL has a 1 GB storage limit, no automated snapshots/backups, and expires after 30 days.
> * **Purpose**: Strictly for staging validation, hackathon demonstration, and integration testing. Not for production workloads.
> * **Restart-Safe Startup Migration**: Since `preDeployCommand` is not available on Render Free tier, migrations execute safely at start (`alembic upgrade head && uvicorn app.main:app...`), which idempotently skips when the schema is already current.

### Environment Variables Configured on Render:

#### Automatic / Managed Variables:
* `DATABASE_URL`: Injected securely via Render Database reference (`fromDatabase: aarogya-sahayak-db.connectionString`).
* `JWT_SECRET`: Auto-generated 64-character secret (`generateValue: true`).
* `JWT_REFRESH_SECRET`: Auto-generated 64-character secret (`generateValue: true`).

#### Live-Integration Hackathon Demo vs. Staging vs. Production Variables:

| Variable | Free Mock Staging | Live-Integration Demo | Production | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `staging` | `staging` | `production` | Controls environment behavior & security guards |
| `INTEGRATION_MODE` | `mock` | `live` | `live` | Master integration toggle |
| `OTP_MODE` | `MOCK` | `TWILIO` (or `MSG91`) | `TWILIO` / `MSG91` | Real SMS OTP delivery adapter |
| `GEMINI_MODE` | `mock` | `live` | `live` | Google Gemini reasoning engine |
| `SARVAM_MODE` | `mock` | `live` | `live` | Sarvam Indic TTS & Voice engine |
| `TAVILY_MODE` | `mock` | `live` | `live` | Tavily official government search |
| `NEO4J_MODE` | `mock` | `mock` | `live` | Knowledge graph (mocked unless Neo4j URI provided) |
| `MILVUS_MODE` | `mock` | `mock` | `live` | Vector search (in-memory/mocked unless Milvus URI provided) |

### 2.1 Private Credential Checklist for Render Dashboard

When setting up a **Live-Integration Hackathon Demo**, configure these secret environment variables directly in your private Render Dashboard (`sync: false` in `render.yaml` ensures credentials are never stored in git):

| Environment Variable | Provider / Purpose | Where to Obtain | Required in Live Mode? |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini AI Reasoning | [Google AI Studio](https://aistudio.google.com/) | **Yes** (when `GEMINI_MODE=live`) |
| `SARVAM_API_KEY` | Sarvam AI Indic Speech/TTS | [Sarvam AI Dashboard](https://www.sarvam.ai/) | **Yes** (when `SARVAM_MODE=live`) |
| `TAVILY_API_KEY` | Tavily Web Search Verification | [Tavily AI](https://tavily.com/) | **Yes** (when `TAVILY_MODE=live`) |
| `GOOGLE_MAPS_SERVER_KEY` | Google Maps Places & Geocoding | [Google Cloud Console](https://console.cloud.google.com/) | **Recommended** for live facility lookups |
| `TWILIO_ACCOUNT_SID` | Twilio SMS OTP | [Twilio Console](https://console.twilio.com/) | **Yes** (when `OTP_MODE=TWILIO`) |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | [Twilio Console](https://console.twilio.com/) | **Yes** (when `OTP_MODE=TWILIO`) |
| `TWILIO_FROM_NUMBER` | Twilio Outbound Number | [Twilio Phone Numbers](https://console.twilio.com/) | **Yes** (when `OTP_MODE=TWILIO`) |
| `MSG91_AUTH_KEY` | MSG91 Indian SMS Gateway | [MSG91 Dashboard](https://msg91.com/) | **Yes** (when `OTP_MODE=MSG91`) |

> [!NOTE]
> **Architecture & Boundary Distinctions:**
> * **Infrastructure:** 100% Free tier on Render (FastAPI + PostgreSQL 16) and Vercel.
> * **Application Integrations:** Live API calls to Google Gemini, Sarvam AI, Tavily, and Twilio/MSG91.
> * **Database & Healthcare Data:** Synthetic seeded demo patients, doctors, facilities, and cases. No real patient health information (PHI) is ever used.
> * **Graph & Vector Stores:** Milvus and Neo4j remain safely mocked/in-memory unless managed cloud instances are provisioned.

---

## 3. Step 2: Deploy Frontend Applications on Vercel

The repository is a monorepo using npm workspaces with shared packages under `packages/` (`@aarogya/api-client`, `@aarogya/design-tokens`, `@aarogya/i18n`, `@aarogya/location`, `@aarogya/shared-types`).

### Project 1: Citizen Mobile PWA

1. Open **Vercel Dashboard** → **Add New...** → **Project**.
2. Import repository `sohamshetye-git/AarogyaSahayak`.
3. Configure project build settings:
   * **Framework Preset:** `Vite`
   * **Root Directory:** `apps/citizen-mobile`
   * **Include files outside the Root Directory:** **ENABLED (Checked)** *(Mandatory for shared workspace packages)*
   * **Install Command:** `npm install`
   * **Build Command:** `npm run build`
   * **Output Directory:** `dist`
   * **Node.js Version:** `20.x` or `22.x`
4. Add Environment Variables:
   * `VITE_API_BASE_URL`: `https://<your-backend>.onrender.com/api`
   * `VITE_WS_URL`: `wss://<your-backend>.onrender.com`
   * `VITE_APP_ENV`: `staging` (or `production`)
   * `VITE_GOOGLE_MAPS_BROWSER_KEY`: *(Optional)* Google Maps Javascript API browser key.
5. Click **Deploy**.

### Project 2: Healthcare Portal SPA (ASHA / Doctor / Admin)

1. In **Vercel Dashboard**, click **Add New...** → **Project**.
2. Import the same repository.
3. Configure project build settings:
   * **Framework Preset:** `Vite`
   * **Root Directory:** `apps/healthcare-portal`
   * **Include files outside the Root Directory:** **ENABLED (Checked)**
   * **Install Command:** `npm install`
   * **Build Command:** `npm run build`
   * **Output Directory:** `dist`
   * **Node.js Version:** `20.x` or `22.x`
4. Add Environment Variables:
   * `VITE_API_BASE_URL`: `https://<your-backend>.onrender.com/api`
   * `VITE_WS_URL`: `wss://<your-backend>.onrender.com`
   * `VITE_APP_ENV`: `staging` (or `production`)
   * `VITE_GOOGLE_MAPS_BROWSER_KEY`: *(Optional)* Google Maps Javascript API browser key.
5. Click **Deploy**.

---

## 4. Authentication Modes & OTP Providers

### Active Staging Deployment Settings:
```text
Environment: STAGING
Citizen OTP Mode: CONTROLLED DEMO
Demo OTP: 123456
Data: SYNTHETIC/DEMO ONLY
Twilio: CODE INTEGRATED BUT DISABLED FOR THIS DEPLOYMENT
```

> [!NOTE]
> This is intentionally a controlled hackathon demo / staging authentication flow. It is not real SMS delivery or production authentication.
>
> **Twilio Integration Status:**
> Twilio code remains fully implemented and tested in the backend (`TwilioOtpProvider`). To enable live SMS delivery after validating phone numbers and SMS sender routes, set `OTP_MODE=TWILIO` in Render / `.env` and provide `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`.

### Supported OTP Modes:
1. **`OTP_MODE=MOCK` (Controlled Hackathon Demo / Staging / Dev):**
   * Configurable via `DEMO_OTP_CODE` (default: `123456`).
   * No third-party network dispatch or SMS charges incurred.
   * Challenge verification limits (5 attempts), 60-second cooldown, and 5-minute expiry remain strictly active.
   * Strictly blocked when `ENVIRONMENT=production` during startup.
2. **`OTP_MODE=TWILIO` (Live Global SMS):**
   * Dispatches real SMS through Twilio REST API without requiring external SDK installation.
   * Requires `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`.
3. **`OTP_MODE=MSG91` (Live Indian Telecom DLT):**
   * Dispatches real SMS through MSG91 OTP/Flow API for Indian carrier delivery.
   * Requires `MSG91_AUTH_KEY` (and optional `MSG91_TEMPLATE_ID`, `MSG91_SENDER_ID`).

> [!WARNING]
> Sarvam AI is an Indic TTS/Speech provider, **not** an SMS gateway. Do not use `OTP_MODE=SARVAM`.

## 5. WebSocket URL & Realtime Configuration

The frontend clients dynamically resolve WebSocket connections via `VITE_WS_URL`:
- If `VITE_WS_URL=wss://aarogya-backend.onrender.com`, the client connects to:
  ```text
  wss://aarogya-backend.onrender.com/api/ws?ticket=<short_lived_ticket>
  ```
- The path `/api/ws` is appended exactly once by the frontend realtime service.
- Realtime authentication uses single-use, 60-second tickets obtained via `POST /api/realtime/ticket`.

---

## 6. Single-Page Application (SPA) Routing

Both applications contain [vercel.json](file:///c:/Arogya%20Sahayak_AI_antigravity/apps/citizen-mobile/vercel.json) rewrites:
```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```
This ensures direct browser refresh and deep-linking work correctly across all routes:
- Citizen routes: `/`, `/auth`, `/schemes`, `/facilities`, `/consultation`
- Portal routes: `/login`, `/asha`, `/doctor`, `/admin`, `/investigations`, `/followups`

---

## 7. Post-Deployment Verification & Smoke Test Checklist

Once Render and Vercel deployments are live:

1. **Backend Health Check:**
   - Visit `https://<your-backend>.onrender.com/health`.
   - Verify HTTP 200 response:
     ```json
     {
       "status": "HEALTHY",
       "service": "aarogya-sahayak-backend",
       "version": "1.0.0"
     }
     ```

2. **Citizen Mobile Verification:**
   - Open Citizen Mobile URL on mobile and desktop viewports.
   - Verify language selection screen displays all 11 Indian languages.
   - Select Hindi/Marathi and proceed to Login.
   - Enter mobile number `9876543210` and verify OTP using `123456`.
   - Verify Home Screen, Government Schemes catalog, and Facility Finder.

3. **Healthcare Portal Verification:**
   - Open Healthcare Portal URL.
   - Sign in as Doctor (`dr.sharma` / `demo123`) and verify Referral & Direct Request queues.
   - Sign in as ASHA Worker (`sita.asha` / `demo123`) and verify Task List & Offline sync.

4. **WebSockets Live Test:**
   - Submit a Citizen Teleconsultation Request.
   - Verify real-time notification on Doctor Dashboard and establish bidirectional chat over `wss://`.

---

## 8. Rollback & Disaster Recovery Procedures

* **Backend Rollback:** In Render Dashboard → `aarogya-sahayak-backend` → **Deploys** → select previous healthy build → click **Rollback**.
* **Database Rollback:** Render Starter PostgreSQL creates automated daily snapshots. Manual backup restore can be performed via:
  ```bash
  pg_restore -h <render-host> -U aarogya_user -d aarogya_db -c backup.dump
  ```
* **Frontend Rollback:** In Vercel Dashboard → select project → **Deployments** → locate previous deployment → click **Promote to Production**.
