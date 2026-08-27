# CAUSE: Causal Intelligence Platform

CAUSE is a retail anomaly-diagnosis application. It detects material telemetry changes, tests competing causes against evidence, assigns confidence, and produces an auditable recommendation.

The supported application is a React frontend served by a FastAPI backend.

## Quick Start: Single Port

This is the normal way to run the application. It serves both React and FastAPI from `http://localhost:8000`.

### 1. Install backend dependencies

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Build the frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run build
cd ..
```

### 3. Start the application

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Open the dashboard at [http://localhost:8000/](http://localhost:8000/).

Useful checks:

- Dashboard: [http://localhost:8000/](http://localhost:8000/)
- API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)
- Dashboard JSON: [http://localhost:8000/api/v1/dashboard](http://localhost:8000/api/v1/dashboard)

FastAPI also returns the React shell for client-side routes, so direct links work after deployment.

## Frontend Development Mode

Use this mode when actively changing React code. It uses two local processes and enables Vite hot reload.

Terminal 1, backend:

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

Terminal 2, frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open [http://localhost:5173/](http://localhost:5173/). Vite proxies `/api` and `/health` to port `8000`, so the frontend still uses the same API paths as production.

## Docker

Docker builds the React application and packages it with FastAPI. Only port `8000` is exposed.

```powershell
docker compose up --build
```

Open [http://localhost:8000/](http://localhost:8000/).

## LLM Behavior

The causal recommendation is deterministic and does not require an API key. The pipeline computes:

1. Anomalies from sales and campaign telemetry
2. Evidence from inventory, campaigns, sales, and the change log
3. Supply, demand, pricing, and operational hypotheses
4. Confidence and contradiction checks
5. A recommendation and monitoring plan

The LLM is optional. When `OPENAI_API_KEY` is configured, it narrates the verified result and audits the narrative. Without a key, CAUSE uses a deterministic offline template. Recommendations continue to work in both modes.

Optional environment variables:

```text
OPENAI_API_KEY=your-key
CAUSE_LLM_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

Never commit `.env`; it is ignored by Git. The application remains fully usable without these variables.

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Service health |
| `GET` | `/api/v1/dashboard` | All analyzed alerts and KPI metadata |
| `GET` | `/api/v1/alerts/{alert_id}` | One complete causal analysis |
| `POST` | `/api/v1/analyses/refresh` | Re-run the deterministic pipeline |
| `GET` | `/api/v1/alerts/{alert_id}/narrative?persona=CXO` | Generate an audited narrative |
| `POST` | `/api/v1/alerts/{alert_id}/decisions` | Persist an approve/reject/ignore decision |

## Repository Structure

```text
backend/app/api/             FastAPI routes and transport schemas
backend/app/domain/          Domain enums, models, and business rules
backend/app/causal/          Pipeline stages and hypothesis modules
backend/app/infrastructure/  Data, repository, and LLM adapters
backend/app/services/        Application use cases
backend/tests/               Unit and API integration tests
frontend/src/api/            Frontend-to-backend client boundary
frontend/src/features/       Feature-owned React code
frontend/src/components/     Shared React components
frontend/src/pages/          Page compositions
frontend/src/router/         Future client-side route definitions
data/                        Raw, processed, and generated data boundaries
scripts/                     Repeatable utilities
cause/                       Deterministic engine and demo data generator
```

## Data and Decisions

The demo telemetry is stored under `cause/data/`. Run the generator when you need to recreate it:

```powershell
.\venv\Scripts\python.exe scripts\generate_demo_data.py
```

Analyst decisions are appended to `cause/data/decisions.csv` for the demo and ignored by Git. A production deployment should replace the CSV repository with a transactional database adapter.

## Validation

Run the deterministic and backend tests:

```powershell
.\venv\Scripts\python.exe -m pytest backend/tests scenario_test.py -q
```

Compile the backend:

```powershell
.\venv\Scripts\python.exe -m compileall -q backend cause scripts
```

Build the frontend:

```powershell
cd frontend
npm.cmd run build
```
