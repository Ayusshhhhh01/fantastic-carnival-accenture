# CAUSE: Causal Intelligence Platform

CAUSE is an enterprise causal intelligence and anomaly diagnosis application for retail. It detects material telemetry changes, tests competing causes against empirical evidence, assigns weighted confidence, and produces an auditable operational recommendation.

The application consists of a React frontend served by a FastAPI backend.

## Quick Start: Single Port

This is the standard way to run the application. It serves both the React production build and FastAPI endpoints from `http://localhost:8000`.

### 1. Install backend dependencies

```powershell
python -m pip install -r requirements.txt
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
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Open the application in your browser:

- Application: [http://localhost:8000/](http://localhost:8000/)
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Service Health: [http://localhost:8000/health](http://localhost:8000/health)
- Active Dashboard JSON: [http://localhost:8000/api/v1/dashboard](http://localhost:8000/api/v1/dashboard)

## Frontend Development Mode

Use this mode when actively changing React code. It uses Vite hot module replacement (HMR).

Terminal 1 (Backend):

```powershell
python -m uvicorn backend.app.main:app --reload --port 8000
```

Terminal 2 (Frontend):

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open [http://localhost:5173/](http://localhost:5173/). Vite proxies `/api` and `/health` to port `8000`.

## Docker

Package React and FastAPI into a single container:

```powershell
docker compose up --build
```

Open [http://localhost:8000/](http://localhost:8000/).

## LLM Governance & Safety Boundary

The causal analysis pipeline is 100% deterministic and operates offline without an API key.

The deterministic pipeline computes:

1. Primary anomaly detection (Revenue & Marketing Spend)
2. Multi-source evidence retrieval (POS, CRM, ERP, Change Log)
3. Falsification of 4 competing hypotheses (Supply, Demand, Pricing, Operational)
4. Weighted Evidence Confidence scoring and hypothesis-specific feedback calibration
5. Cross-regional conflict audit & diagnostic abstention rules
6. 7-part operational recommendation

The LLM is strictly constrained to copy narration (`LLM · Narration only`). When `OPENAI_API_KEY` is configured, it generates executive summary text from verified JSON. Without a key, CAUSE uses a deterministic offline template.

Optional environment variables:

```text
OPENAI_API_KEY=your-key
CAUSE_LLM_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Service health status |
| `GET` | `/api/v1/dashboard` | Active signal queue (excluding handled alerts) & KPI registry |
| `GET` | `/api/v1/alerts/{alert_id}` | Complete causal analysis object for a specific alert |
| `GET` | `/api/v1/alerts/{alert_id}/investigate?persona=...` | Persona-scoped investigation analysis (with Fast/Deep path resolution) |
| `POST` | `/api/v1/alerts/{alert_id}/decisions` | Persist an approve/reject/ignore decision with hypothesis calibration tag |
| `POST` | `/api/v1/analyses/refresh` | Re-run deterministic analysis pipeline across telemetry data |
| `GET` | `/api/v1/alerts/{alert_id}/narrative?persona=...` | Fetch persona-customized LLM narration brief |
| `POST` | `/api/v1/reset-demo` | Clear persisted decision CSV and reset active dashboard signal queue |

## Repository Structure

```text
backend/app/api/             FastAPI routes and transport schemas
backend/app/domain/          Domain enums, models, and business rules
backend/app/causal/          Pipeline stages and hypothesis modules
backend/app/infrastructure/  Data, repository, and LLM adapters
backend/app/services/        Application use cases
backend/tests/               Unit and API integration tests
frontend/src/                React source code (components, pages, styles)
data/                        Telemetry CSV datasets
cause/                       Deterministic engine, data generator, and decision persistence
```

## Validation Commands

Run backend pytest and scenario validation:

```powershell
python -m pytest backend/tests scenario_test.py -q
```

Compile backend source code:

```powershell
python -m compileall -q backend cause scripts
```

Build frontend production bundle:

```powershell
cd frontend
npm.cmd run build
```
