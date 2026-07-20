# FinSight AI — Production Deployment Guide
> Step-by-step instructions to deploy backend (Railway), task queue (Upstash Redis), database/storage (Supabase), and frontend (Vercel).

---

## Architecture Blueprint

```
┌────────────────────────────────────────────────────────┐
│               Vercel Frontend (React/Vite)              │
└──────────────────────────┬─────────────────────────────┘
                           │ API Requests
                           ▼
┌────────────────────────────────────────────────────────┐
│           Railway Backend Web Service (FastAPI)        │
└──────────────┬───────────────────────────┬─────────────┘
               │ Dispatch Celery Tasks     │ DB Read/Write
               ▼                           ▼
┌─────────────────────────────┐ ┌────────────────────────┐
│ Upstash Redis (Task Broker) │ │ Supabase (Postgres DB) │
└──────────────┬──────────────┘ └───────────▲────────────┘
               │ Pull Tasks                 │ Update Status &
               ▼                            │ Upload .docx
┌───────────────────────────────────────────┴────────────┐
│         Railway Celery Worker Service (Worker)         │
└────────────────────────────────────────────────────────┘
```

---

## Step 1: Database & Storage Setup (Supabase)

1. **Get Connection Credentials**:
   - Navigate to **Supabase Dashboard** → **Project Settings** → **Database**.
   - Copy your PostgreSQL connection string: `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`.
   - Go to **Project Settings** → **API**. Copy the `URL`, `anon public key`, and `service_role secret key`.

2. **Run Alembic Migrations**:
   In your local backend terminal with `.env` configured to point to your Supabase `DATABASE_URL`:
   ```bash
   cd backend
   alembic upgrade head
   ```
   *This creates `users`, `reports`, `watchlists`, and `cached_data` tables.*

3. **Create Storage Bucket**:
   - Go to **Supabase Dashboard** → **Storage**.
   - Click **New Bucket**. Name it `reports`.
   - Toggle **Public bucket** to ON.
   - Click **Save**.

---

## Step 2: Task Queue Setup (Upstash Redis)

1. **Create Redis Database**:
   - Go to [Upstash Console](https://console.upstash.com/) → **Redis** → **Create Database**.
   - Select region closest to your Railway deployment (e.g. `ap-south-1` or `us-east-1`).
   - Enable **TLS/SSL**.

2. **Copy Connection String**:
   - Copy the `rediss://...` string under **Celery / Redis Client**. Example:
     `rediss://default:PASSWORD@xxxx.upstash.io:6379`

---

## Step 3: Backend Deployment (Railway)

1. **Create Railway Project**:
   - Go to [Railway Dashboard](https://railway.app/) → **New Project** → **Deploy from GitHub repo**.
   - Connect your `valor0506/finsight-ai` repository.

2. **Configure Web Service**:
   - In Railway Service Settings:
     - **Build Command**: `pip install -r backend/requirements.txt`
     - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
     - Or specify **Root Directory**: `backend` (if root directory is set to `backend`, Start Command is `uvicorn main:app --host 0.0.0.0 --port $PORT`).

3. **Configure Celery Worker Service**:
   - In Railway, click **+ New Service** → **GitHub Repo** (same repo).
   - Set **Root Directory**: `backend`.
   - Set **Start Command**: `celery -A tasks.celery_app.celery_app worker --loglevel=info --concurrency=2`

4. **Environment Variables (Add to both Web & Worker services)**:
   ```env
   ENVIRONMENT=production
   FRONTEND_URL=https://your-app.vercel.app
   SECRET_KEY=your_secure_random_jwt_secret_key
   OPENROUTER_API_KEY=sk-or-v1-...
   FINNHUB_API_KEY=...
   GROWW_API_KEY=...
   GROWW_TOTP_SECRET=...
   FRED_API_KEY=...
   NEWS_API_KEY=...
   DATABASE_URL=postgresql://postgres:pass@db.xxxx.supabase.co:5432/postgres
   SUPABASE_URL=https://xxxx.supabase.co
   SUPABASE_ANON_KEY=...
   SUPABASE_SERVICE_KEY=...
   REDIS_URL=rediss://default:pass@xxxx.upstash.io:6379
   ```

5. **Generate Railway Domain**:
   - In Web Service Settings → **Networking** → **Generate Domain**.
   - Copy the public URL (e.g., `https://finsight-backend-production.up.railway.app`).

---

## Step 4: Frontend Deployment (Vercel)

1. **Import Project to Vercel**:
   - Go to [Vercel Dashboard](https://vercel.com/) → **Add New Project**.
   - Import `valor0506/finsight-ai`.
   - Set **Framework Preset**: `Vite`.
   - Set **Root Directory**: `frontend`.

2. **Set Environment Variable**:
   - Key: `VITE_API_URL`
   - Value: `https://finsight-backend-production.up.railway.app` (your Railway Web Service URL).

3. **Deploy**:
   - Click **Deploy**.
   - Vercel will build Vite assets and host your frontend. The included `frontend/vercel.json` ensures SPA routes like `/dashboard`, `/generate`, and `/reports/:id` work smoothly on refresh.

---

## Post-Deployment Checklist

- [ ] Test `/health` endpoint on Railway backend (`https://your-railway-url.up.railway.app/health`).
- [ ] Test frontend signup & login.
- [ ] Submit a test report request on the frontend (`/generate`) and verify Celery processes the background task.
- [ ] Check Supabase `reports` bucket to ensure `.docx` is uploaded and downloadable.
