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

### Resource Details Declared in `render.yaml`:

| Resource | Type | Region | Plan | Key Settings |
| :--- | :--- | :--- | :--- | :--- |
| `aarogya-sahayak-db` | PostgreSQL 16 | Singapore | Starter | `databaseName: aarogya_db`, `user: aarogya_user` |
| `aarogya-sahayak-backend` | Web Service (Python 3) | Singapore | Starter | `preDeployCommand: alembic upgrade head`<br>`startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT`<br>`healthCheckPath: /health` |

### Environment Variables Configured on Render:

#### Automatic / Managed Variables:
* `DATABASE_URL`: Injected securely via Render Database reference (`fromDatabase: aarogya-sahayak-db.connectionString`).
* `JWT_SECRET`: Auto-generated 64-character secret (`generateValue: true`).
* `JWT_REFRESH_SECRET`: Auto-generated 64-character secret (`generateValue: true`).

#### Staging vs. Production Variables:

| Variable | Staging Value | Production Value | Purpose |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `staging` | `production` | Controls security and validation guards |
| `OTP_MODE` | `MOCK` | `TWILIO` / `MSG91` | OTP delivery mechanism (see Section 4) |
| `INTEGRATION_MODE` | `mock` | `live` | AI & external services integration mode |
| `GEMINI_MODE` | `mock` or `live` | `live` | Gemini reasoning engine mode |
| `SARVAM_MODE` | `mock` or `live` | `live` | Sarvam Indic TTS engine mode |
| `TAVILY_MODE` | `mock` or `live` | `live` | Tavily web search mode |

#### Optional Secret API Keys (Enter manually in Render Dashboard if using live modes):
* `GEMINI_API_KEY`: API key from Google AI Studio.
* `SARVAM_API_KEY`: API key from Sarvam AI for TTS/speech synthesis.
* `TAVILY_API_KEY`: API key from Tavily for search.
* `GOOGLE_MAPS_SERVER_KEY`: Server key for geocoding & distance calculation.
* `OTP_SMS_PROVIDER_API_KEY`: SMS gateway API key (required in production).

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

## 4. Staging Authentication & Safe Demo OTP Mechanism

### Staging Configuration:
* `ENVIRONMENT=staging`
* `OTP_MODE=MOCK`
* **Demo OTP Behavior:** In `staging`, `development`, and `test` environments with `OTP_MODE=MOCK`, OTP generation returns deterministic code `123456` and supplies `mock_code` in the OTP challenge response to allow end-to-end testing without external SMS credits.

### Production Guardrails:
* If `ENVIRONMENT=production` and `OTP_MODE=MOCK`, the backend startup validation (`validate_production_settings()`) raises a fatal `RuntimeError`, strictly preventing production deployment with mock authentication.
* In production, real SMS dispatch adapters (e.g. Twilio, MSG91) are used via `OTP_SMS_PROVIDER_API_KEY`.
* *Note:* Sarvam AI is an Indic TTS/Speech provider, not an SMS gateway; `OTP_MODE=SARVAM` is not used.

---

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
