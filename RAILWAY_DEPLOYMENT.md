# Railway Deployment Guide (24/7)

This project can run fully without your local machine by splitting backend runtime into always-on Railway services.

## Target Architecture

- Service 1: `gridguard-api` (FastAPI)
- Service 2: `gridguard-worker` (Celery worker)
- Service 3: `gridguard-beat` (Celery beat scheduler)
- Managed MongoDB: MongoDB Atlas (recommended)
- Managed Redis: Upstash Redis or Railway Redis
- Frontend: Vercel

## Why 3 backend services

- API handles HTTP + WebSocket routes.
- Worker executes background jobs and payout checks.
- Beat schedules recurring pollers and periodic tasks.

If worker and beat are not running, data polling and automated workflows will stop.

## Step 1: Create Railway Project

1. Create a Railway project.
2. Connect this GitHub repository.
3. Create three services from the same repo:
   - `gridguard-api`
   - `gridguard-worker`
   - `gridguard-beat`
4. Set each service root directory to `backend`.

## Step 2: Build Configuration

Use Dockerfile build mode (already supported by `backend/railway.json`).

- Dockerfile path: `backend/Dockerfile`

## Step 3: Start Process (role-based)

All three services can share the same `backend/railway.json` start command:

`bash ./scripts/railway_start.sh`

Set service variables to select runtime role:

- `gridguard-api`: `SERVICE_ROLE=api`
- `gridguard-worker`: `SERVICE_ROLE=worker`
- `gridguard-beat`: `SERVICE_ROLE=beat`

Optional:

- `CELERY_CONCURRENCY=4` on `gridguard-worker`

## Step 4: Environment Variables

Set the same core env vars on all 3 services unless marked API-only.

### Required on API + Worker + Beat

- MONGODB_URL
- MONGODB_DB_NAME
- REDIS_URL
- SECRET_KEY
- ALGORITHM
- ACCESS_TOKEN_EXPIRE_DAYS
- INTERNAL_API_KEY
- INTERNAL_API_BASE_URL
- ADMIN_EMAILS
- GRID_DATA_MODE
- STALE_EVENT_MINUTES
- PAYOUT_PROVIDER
- RAZORPAY_FALLBACK_TO_MOCK
- ENVIRONMENT

### API-only (but safe to set everywhere)

- CORS_ORIGINS
- SENTRY_DSN

### External provider keys (set where needed; safe to set everywhere)

- WAQI_API_TOKEN
- ORS_API_KEY
- TOMTOM_API_KEY
- OPENWEATHER_API_KEY
- SMTP_HOST
- SMTP_PORT
- SMTP_USER
- SMTP_PASSWORD
- EMAIL_FROM
- FIREBASE_SERVER_KEY
- FIREBASE_PROJECT_ID

### Optional Razorpay keys

- RAZORPAY_KEY_ID
- RAZORPAY_KEY_SECRET
- RAZORPAYX_ACCOUNT_NUMBER
- RAZORPAY_WEBHOOK_SECRET

## Step 5: INTERNAL_API_BASE_URL

Set `INTERNAL_API_BASE_URL` to the private service URL in Railway network:

http://gridguard-api.railway.internal

Use the public API URL only for frontend/browser clients.

## Step 6: CORS for Vercel

Set `CORS_ORIGINS` on API service to include your Vercel domains, for example:

https://your-frontend.vercel.app,https://your-preview-domain.vercel.app

## Step 7: Vercel Frontend Environment

In Vercel project settings set:

- NEXT_PUBLIC_API_URL=https://your-api-domain.railway.app
- NEXT_PUBLIC_APP_ENV=production

Optional (recommended for future realtime wiring consistency):

- NEXT_PUBLIC_WS_URL=wss://your-api-domain.railway.app

## Step 8: Health and Smoke Tests

After deploy:

1. Check API health:
   - GET https://your-api-domain.railway.app/health
2. Open admin pages and verify live metrics load.
3. Confirm worker logs show periodic task execution.
4. Confirm beat logs show schedule dispatch.

## Step 9: Production Reliability

- Keep all three services with at least 1 replica.
- Enable Railway restart policy.
- Add alerting for service down and error spikes.
- Use paid plans that do not sleep for true 24/7 behavior.

## Common Failure Modes

- API works but no fresh events: worker/beat service not running.
- Admin pages show request errors: missing/incorrect CORS_ORIGINS or auth env.
- Pollers fail silently: missing provider API keys.
- WebSockets fail from frontend: NEXT_PUBLIC_WS_URL not set to secure wss endpoint.
