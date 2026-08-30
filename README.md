# CAUSE — BusinessIntelligence.ai

**From KPI Monitoring to Decision Intelligence**

CAUSE is a hybrid enterprise intelligence platform for investigating material business KPI movements. It sits on top of existing BI/data systems and moves the user from **what changed → why it changed → how confident are we → what should we do next**.

The system combines deterministic analytics, statistical evidence, structured and unstructured data, evidence retrieval, root-cause hypothesis testing, confidence scoring, contradiction handling, persona-aware narration and human feedback. The LLM is deliberately **not** the source of quantitative truth.

> **Core loop:** Detect → Explain → Challenge → Recommend → Act → Learn

## Why CAUSE?

Traditional BI is excellent at surfacing a signal such as:

> **Revenue in Region X ↓ 8%**

The investigation that follows is often fragmented across SQL queries, operational logs, CRM records, inventory data, support tickets and stakeholder conversations.

CAUSE adds an intelligence layer that:

1. Detects and prioritises material KPI movements.
2. Investigates recent structured events through a low-cost Fast Path.
3. Expands to a Deep Path when multi-source contextual evidence is required.
4. Tests competing root-cause hypotheses against empirical evidence.
5. Exposes supporting and contradictory evidence.
6. Produces an auditable confidence score and can abstain when evidence is insufficient.
7. Converts a validated driver into an operational recommendation and monitoring plan.
8. Captures human decisions for feedback and future calibration.

## Product Workflow

```text
PERSONA / ACCESS
      ↓
DASHBOARD / SIGNAL QUEUE
      ↓
ANOMALY + MATERIALITY DETECTION
      ↓
INVESTIGATION PREVIEW
      ↓
FAST PATH OR DEEP PATH
      ↓
MULTI-SOURCE EVIDENCE
      ↓
COMPETING RCA HYPOTHESES
      ↓
EVIDENCE + CONTRADICTION CHECK
      ↓
CONFIDENCE / ABSTENTION
      ↓
PERSONA-SPECIFIC EXPLANATION
      ↓
RECOMMENDATION + MONITORING PLAN
      ↓
HUMAN APPROVAL / REJECTION / IGNORE
      ↓
FEEDBACK + CALIBRATION LOOP
```

## Architecture

### 1. Data sources

The prototype connects telemetry representing different enterprise sources and grains:

- **Sales / POS:** revenue, units sold, realised price, region/category performance.
- **Campaigns / marketing:** campaign spend and promotional effectiveness.
- **Inventory / ERP:** stock-out events and operational exposure.
- **CRM / support / business evidence:** contextual records for deeper investigation.
- **Change log:** pricing, promotion, inventory and operational events.

Demo telemetry is stored locally under `cause/data/`.

### 2. KPI semantic layer

The KPI registry defines:

- KPI formula
- Business meaning
- Data grain
- Source
- Baseline method
- Materiality rule
- Connected drivers
- Persona/access entitlement

This prevents the investigation engine from reasoning about an ambiguous KPI definition.

### 3. Detection and materiality

The deterministic engine compares current KPI behaviour with historical baselines. The current prototype includes parameters such as:

```text
Z_THRESHOLD = 1.5
PCT_THRESHOLD = 0.10
MIN_BASELINE_WEEKS = 3
```

The relevant KPI registry rule is then applied to determine whether the movement is material enough to investigate.

### 4. Fast Path

The system checks obvious structured changes first:

```text
KPI movement
   ↓
Recent Change Log
   ↓
Pricing / Promotion / Inventory / Operational event
   ↓
Direct match → explain quickly
```

This avoids unnecessary retrieval or LLM calls when a reliable recent event already explains the signal.

### 5. Deep Path

If the Fast Path does not provide sufficient evidence, CAUSE expands the investigation:

```text
Structured telemetry + contextual evidence
                ↓
          Evidence retrieval
                ↓
       Candidate root causes
                ↓
 Evidence scoring + contradiction audit
                ↓
          Ranked hypotheses
```

## Root-Cause Intelligence

The current demo evaluates four hypothesis families:

1. **Supply:** stock-outs and availability constraints
2. **Demand:** campaign/demand changes
3. **Pricing:** price or discount movements
4. **Operational:** delivery, system or operational disruption

The engine evaluates competing hypotheses rather than accepting the first plausible explanation.

## Confidence Scoring

CAUSE uses an interpretable evidence framework built around four factors:

- **W1 — Temporal Correlation:** alignment between the driver event and KPI movement.
- **W2 — Source Reliability:** historical trustworthiness of the evidence source.
- **W3 — Contrary Stats Score:** statistical support versus contrary statistical evidence.
- **W4 — Evidence Density:** amount and independence of evidence supporting the hypothesis.

Conceptually:

```text
Score(c) = W1·T(c) + W2·R(c) + W3·A(c) + W4·D(c)
```

The factors are normalised to `[0,1]`. The weights are intended to be learned/calibrated from validated RCA outcomes rather than treated as permanent hand-picked percentages.

For competing hypotheses, scores can be transformed into a relative distribution and calibrated. The UI converts the final calibrated value into the displayed percentage:

```text
Confidence % = round(clamp(Calibrated Score, 0.0, 1.0) × 100)
```

The system can abstain when confidence is below the configured threshold or evidence is unresolved/contradictory.

### Statistical evidence

For numerical baseline analysis, the engine uses features such as:

```text
Z = (Observed − Historical Mean) / Historical Standard Deviation
```

Z-score is evidence of unusual behaviour; it is **not treated as proof of causality** and is not forced onto text-only evidence.

## Evidence & Contradiction Handling

Investigations are designed to be traceable. Evidence records can include:

- Source
- Timestamp
- Freshness
- KPI/context
- Supporting evidence
- Contrary evidence
- Analytical method
- Contribution/strength
- Lineage

When competing evidence conflicts, the product surfaces the conflict rather than silently choosing a convenient narrative.

When evidence is insufficient, CAUSE can explicitly return an abstention such as:

> **Insufficient evidence to diagnose**

and withhold the recommendation.

## Recommendation Layer

A validated driver is converted into a structured action proposal:

```text
Driver
  → Controllable Lever
  → Action
  → Expected / Estimated Impact
  → Owner
  → Confidence
  → Monitoring Plan
```

The final decision remains with an authorised human user.

## Persona-Specific Intelligence

The prototype supports two principal views:

### Category Manager

Operational detail such as category, region, SKU/volume, pricing and inventory signals.

### CXO

Executive-level aggregation focused on portfolio impact and strategic risk, with sensitive granular data appropriately restricted.

The investigation and narrative layers accept persona context so the same underlying evidence can be communicated at the right level of detail.

## LLM Governance Boundary

The quantitative causal pipeline is deterministic and can run offline without an API key.

**Non-LLM responsibilities:**

- KPI calculation
- Baselines and materiality
- Anomaly detection
- Statistical calculations
- Structured evidence selection
- Contribution analysis
- Hypothesis scoring
- Contradiction checks
- Recommendation rules
- Access/entitlement rules
- Audit and telemetry

**LLM responsibilities:**

- Natural-language narration
- Persona-specific summarisation
- Contextual wording from verified JSON

When enabled, the LLM receives the finished/audited analytical output rather than raw unindexed telemetry. The application labels this boundary as **`LLM · Narration only`**. Without a configured key, a deterministic offline narrative template is used.

Optional environment variables:

```text
OPENAI_API_KEY=your-key
CAUSE_LLM_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

Never commit API keys or `.env` files.

## Decision Stress Test

A key product differentiator is the planned decision-oriented layer:

```text
Leading RCA
   ↓
“What if we intervene on this driver?”
   ↓
Historical / statistical / causal scenario analysis
   ↓
Conservative / expected / optimistic outcomes
   ↓
Compare actions on impact, cost, risk and confidence
   ↓
Recommend when evidence supports the decision
```

The goal is to move beyond explaining **why** a KPI moved toward helping the business evaluate **what happens if we act**.

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Service health |
| `GET` | `/api/v1/dashboard` | Active signal queue and KPI registry |
| `GET` | `/api/v1/alerts/{alert_id}` | Complete causal analysis object |
| `GET` | `/api/v1/alerts/{alert_id}/investigate?persona=...` | Persona-scoped Fast/Deep investigation |
| `POST` | `/api/v1/analyses/refresh` | Re-run deterministic analysis |
| `GET` | `/api/v1/alerts/{alert_id}/narrative?persona=...` | Persona-specific narrative |
| `POST` | `/api/v1/alerts/{alert_id}/decisions` | Persist human decision and calibration feedback |
| `POST` | `/api/v1/reset-demo` | Reset demo decision state |
| `GET` | `/docs` | Interactive FastAPI documentation |

## Repository Structure

```text
backend/app/api/             FastAPI routes and transport schemas
backend/app/domain/          Domain models, enums and business rules
backend/app/causal/          Causal pipeline and hypothesis modules
backend/app/infrastructure/  Data, repository and LLM adapters
backend/app/services/        Application use cases
backend/tests/               Unit and API integration tests
frontend/src/                React application source
frontend/src/features/       Feature-level UI code
frontend/src/components/     Shared UI components
frontend/src/pages/          Page compositions
cause/                       Deterministic engine and scoring logic
cause/data/                  Demo telemetry / persisted decision data
data/                        Supporting datasets
scripts/                     Repeatable utilities
```

## Run Locally

### Backend dependencies

```powershell
python -m pip install -r requirements.txt
```

### Frontend build

```powershell
cd frontend
npm.cmd install
npm.cmd run build
cd ..
```

### Start full application

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Open:

- Application: `http://localhost:8000/`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Dashboard JSON: `http://localhost:8000/api/v1/dashboard`

### Frontend development mode

Terminal 1:

```powershell
python -m uvicorn backend.app.main:app --reload --port 8000
```

Terminal 2:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173/`.

### Docker

```powershell
docker compose up --build
```

## Demo Data

Generate the controlled demo telemetry with:

```powershell
python scripts/generate_demo_data.py
```

## Validation

Run tests and scenario validation:

```powershell
python -m pytest backend/tests scenario_test.py -q
```

Compile Python source:

```powershell
python -m compileall -q backend cause scripts
```

Build the frontend:

```powershell
cd frontend
npm.cmd run build
```

## Prototype Scenarios

The application is designed to demonstrate:

- Material KPI movement detection
- Recent-event Fast Path
- Deep multi-source investigation
- Multi-factor driver/contribution analysis
- Competing root-cause hypotheses
- Supporting and contradictory evidence
- Confidence scoring
- Low-confidence abstention
- Persona-specific narratives
- Action recommendation and monitoring
- Human approve/reject/ignore workflow
- Feedback and calibration loop
- Runtime/model telemetry

## Round 2 Alignment

The prototype is structured around the BusinessIntelligence.ai Round 2 requirements:

- 3–5 connected KPIs
- 2–3 heterogeneous data sources
- KPI semantic contracts
- Multi-factor KPI movement
- Structured + unstructured investigation
- Driver/contribution analysis
- Evidence retrieval and lineage
- Root-cause ranking
- Confidence and contradiction handling
- Persona-specific narratives
- Action recommendations
- Low-confidence abstention
- Sparse-history handling
- Role-based access/entitlements
- Human feedback and calibration
- Explicit LLM vs non-LLM separation
- Runtime latency, model-call, token and cost telemetry

The repository contains a competition-grade prototype and controlled demo data; production deployment would require enterprise-specific connectors, security infrastructure, governance controls and scale testing.

## Disclaimer

This is a competition prototype. Demo telemetry and scenario values are synthetic/controlled for demonstration and should not be interpreted as real enterprise performance data.

## License

No separate open-source license is currently declared for this repository.
