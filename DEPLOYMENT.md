# FinSight AI — Production Deployment Guide
> Step-by-step instructions to deploy backend & Celery worker (Render Free Tier), task queue (Upstash Redis), database/storage (Supabase), and frontend (Vercel).

---

## Architecture Blueprint

```
┌────────────────────────────────────────────────────────┐
│               Vercel Frontend (React/Vite)              │
│               https://finsight.vercel.app              │
└──────────────────────────┬─────────────────────────────┘
                           │ API Requests
                           ▼
┌────────────────────────────────────────────────────────┐
│          Render Web Service (FastAPI + Celery)         │
│          Runs start.sh: uvicorn (port 10000)           │
│          + celery worker (concurrency 1)               │
└──────────────┬───────────────────────────┬─────────────┘
               │ Dispatch Celery Tasks     │ DB Read/Write
               ▼                           ▼
┌─────────────────────────────┐ ┌────────────────────────┐
│ Upstash Redis (Task Broker) │ │ Supabase (Postgres DB) │
└─────────────────────────────┘ └───────────▲────────────┘
                                            │ Update Status &
                                            │ Upload .docx
```

---

## Step 1: Database & Storage Setup (Supabase)

1. **Create Supabase Project**:
   - Go to [Supabase](https://supabase.com/) and create a free project.
   - Region: Select nearest region (e.g., `South Asia (Mumbai)` or `US East`).

2. **Get Connection Credentials**:
   - Navigate to **Project Settings** → **Database**.
   - Under **Connection String** → **URI**, copy:
     ```
     postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
     ```
   - Go to **Project Settings** → **API**. Copy:
     - `Project URL` (e.g., `https://xxxx.supabase.co`)
     - `anon` `public` key
     - `service_role` `secret` key

3. **Create Storage Bucket for Reports**:
   - Go to **Storage** → **New Bucket**.
   - Bucket name: `reports`
   - Toggle **Public bucket** to **ON**.
   - Click **Save**.

4. **Initialize Tables**:
   - On the first backend startup on Render, FinSight's FastAPI app automatically executes table creation (`users`, `reports`, `watchlists`, `cached_data`).
   - *(Optional local migration)*: You can also run locally:
     ```bash
     cd backend
     alembic upgrade head
     ```

---

## Step 2: Redis Task Broker Setup (Upstash Redis)

1. **Create Free Redis Instance**:
   - Go to [Upstash Console](https://console.upstash.com/) → **Redis** → **Create Database**.
   - Database Name: `finsight-redis`
   - Region: Closest to your database/backend.
   - **TLS (SSL)**: Enabled by default.

2. **Copy Connection String**:
   - In the database details, scroll to **Connect to your database**.
   - Select the **Celery** or **redis-py** tab.
   - Copy the connection URL starting with `rediss://`:
     ```
     rediss://default:[PASSWORD]@[ENDPOINT].upstash.io:6379
     ```

---

## Step 3: Backend Deployment (Render Free Tier)

You can deploy on Render in either of two ways:

### Option A: Render Blueprint (Easiest — 1-Click via `render.yaml`)
1. Push your latest code to your GitHub repo (`origin/main`).
2. Go to [Render Dashboard](https://dashboard.render.com/) → **New +** → **Blueprint**.
3. Connect your `valor0506/finsight-ai` repository.
4. Render will detect `render.yaml`.
5. Enter the required environment variables when prompted and click **Apply**.

---

### Option B: Manual Web Service Setup (Step-by-Step)
1. Go to [Render Dashboard](https://dashboard.render.com/) → **New +** → **Web Service**.
2. Select **Build and deploy from a Git repository** and connect `valor0506/finsight-ai`.
3. Fill in the service configuration:
   - **Name**: `finsight-backend`
   - **Region**: Oregon (or nearest)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `bash start.sh`
   - **Instance Type**: `Free`

4. Scroll down to **Environment Variables** and add:

   | Key | Value | Description |
   |---|---|---|
   | `ENVIRONMENT` | `production` | Production mode |
   | `PYTHON_VERSION` | `3.11.9` | Stable Python runtime |
   | `SECRET_KEY` | *(generate a random string or click generate)* | JWT signing key |
   | `DATABASE_URL` | `postgresql://postgres:...` | Supabase Postgres URL |
   | `SUPABASE_URL` | `https://xxxx.supabase.co` | Supabase API URL |
   | `SUPABASE_ANON_KEY` | `eyJhbGci...` | Supabase anon key |
   | `SUPABASE_SERVICE_KEY` | `eyJhbGci...` | Supabase service_role key |
   | `REDIS_URL` | `rediss://default:...@...upstash.io:6379` | Upstash Redis TLS URL |
   | `OPENROUTER_API_KEY` | `sk-or-v1-...` | OpenRouter LLM API key |
   | `FINNHUB_API_KEY` | *(your finnhub key)* | US market data |
   | `FRED_API_KEY` | *(your fred key)* | Macro interest rate/inflation |
   | `NEWS_API_KEY` | *(your news api key)* | Global market news |
   | `GROWW_API_KEY` | *(optional/your key)* | Indian stock data |
   | `GROWW_TOTP_SECRET` | *(optional/your key)* | Indian stock TOTP |
   | `FRONTEND_URL` | `https://your-app.vercel.app` | Vercel domain (can update after Step 4) |

5. Under **Advanced Settings**:
   - **Health Check Path**: `/health`
   - **Auto-Deploy**: `Yes`

6. Click **Create Web Service**.
7. Wait 2-3 minutes for the build to finish. Once live, copy your backend URL:
   `https://finsight-backend-xxxx.onrender.com`

---

## Step 4: Frontend Deployment (Vercel)

1. Go to [Vercel Dashboard](https://vercel.com/) → **Add New** → **Project**.
2. Import `valor0506/finsight-ai`.
3. Configure project:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click edit and select `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand **Environment Variables**:
   - Name: `VITE_API_URL`
   - Value: `https://finsight-backend-xxxx.onrender.com` *(your Render backend URL, NO trailing slash)*
5. Click **Deploy**.
6. Once deployed, copy your frontend production URL (e.g. `https://finsight-ai.vercel.app`).
7. **Back in Render**: Update the `FRONTEND_URL` environment variable to match your Vercel URL.

---

## Post-Deployment Verification

1. **Verify Backend Health**:
   Visit: `https://finsight-backend-xxxx.onrender.com/health`
   Expected response:
   ```json
   {"status":"healthy","timestamp":"2026-10-07T..."}
   ```
2. **Verify Frontend UI**:
   Open your Vercel URL, navigate through pages.
3. **Register / Login**:
   Create a test account on the registration page.
4. **Generate Report**:
   Submit an equity (`RELIANCE.NS` or `AAPL`) or commodity (`GOLD`) report.
   - Celery worker receives the job via Upstash Redis.
   - OpenRouter generates the multi-section financial analysis.
   - Supabase storage saves the formatted `.docx`.
   - Download the generated file from the dashboard.
