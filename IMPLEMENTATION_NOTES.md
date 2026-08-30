# CAUSE — Final Canonical Implementation & System Architecture

This document describes the canonical end-to-end architecture and multi-stage investigation flow for the **CAUSE (Causal Intelligence Platform)**.

---

## 🎯 Final Product Workflow

```
LOGIN / PERSONA SELECTION
        ↓
DASHBOARD / SIGNAL QUEUE
        ↓
INVESTIGATION PREVIEW MODAL
        ↓
DIAGNOSE
        ↓
FULL-SCREEN INVESTIGATION
        ↓
FAST PATH OR DEEP PATH
        ↓
ROOT CAUSE / EVIDENCE / RECOMMENDATION
        ↓
APPROVE / REJECT / IGNORE
        ↓
RETURN TO DASHBOARD
        ↓
APPROVED ALERT DISAPPEARS FROM ACTIVE QUEUE
```

---

## 🚀 Key Modules & Capabilities

### 1. Persona Selection (`/`)
- **Heading**: `"Select your perspective"`
- **Subtitle**: `"Choose how you want to investigate business signals."`
- **Supported Personas**:
  - **Category Manager**: Operational category intelligence (SKU, regional & supply-demand signals).
  - **CXO Suite**: Enterprise portfolio intelligence (portfolio-level impact & strategic risk with automated SKU redaction).
- **Layout**: Horizontally aligned persona cards, equal dimensions, keyboard accessible, zero vertical scroll on desktop viewport.

### 2. Dashboard Workspace (`/dashboard`)
- **Primary Framing**: `"Find the reason behind the signal."`
- **Objective Signal Display**: No visible severity labels or subjective assumptions (`HIGH`/`MEDIUM`/`LOW` badges eliminated). Presents KPI, Category, Region, Baseline, Current, Variance, and Impact objectively.
- **Header Status**: Connected real-time telemetry status badge (`Telemetry connected`).

### 3. Investigation Preview Modal
- **Dimensions**: Centered desktop pop-up modal (`width: min(700px, calc(100vw - 32px))`).
- **Features**:
  - Horizontal 3-column equal summary grid (`BASELINE`, `CURRENT`, `NET VARIANCE`).
  - Telemetry Trend Preview (`KPIChart`) relying strictly on backend `historical_series`. Shows `"Historical telemetry unavailable"` if telemetry is pending (no fake frontend trend generation).
  - Clear **"Diagnose"** CTA button to launch full-screen investigation, alongside **"Remove Signal"** and close controls (Esc key supported).

### 4. Full-Screen Investigation (`/investigate/:alertId`)
- **Automated Triage Scan**:
  - **Path 1 (Direct Event Match)**: Scans operational change logs for pricing/promo/inventory/IT events. If match found $\rightarrow$ Fast Path.
  - **Path 2 (Deep Causal Research)**: Retrieves multi-source telemetry evidence $\rightarrow$ evaluates 4 canonical hypotheses $\rightarrow$ scores Weighted Evidence Confidence $\rightarrow$ checks cross-regional contradiction.
- **Fast Path UI**:
  - Verified event details (Type, Date, Description, Category/Region match).
  - Recommended action directive, monitoring plan, and evidence citations. Skips candidate hypotheses.
- **Deep Path UI (Resolved)**:
  - Primary Root Cause spotlight (leading candidate at verified confidence score).
  - Supporting & contrary reasoning breakdown.
  - **4 Canonical Hypotheses** (Supply-side stock-out, Demand-side campaign shift, Pricing change, Operational disruption).
  - **Collapsed by default**: All hypothesis cards start collapsed; user explicitly clicks `"Expand"` to inspect verdict and detailed breakdown.
- **Conflict Path UI (Unresolved Conflict)**:
  - Displays `"Conflicting evidence"` and signal contradiction details (Signal A vs Signal B).
  - Withholds automated diagnosis and explicitly directs manual audit.
- **Abstain Path UI (Diagnostic Abstention)**:
  - Displays `"Insufficient evidence to diagnose"` and missing data gaps.
  - Withholds recommendation. ZERO LLM calls made.

### 5. Recommendation & AI Executive Summary
- Grounded in deterministic Causal Engine: Driver, Lever, Action (strongest visual element), Estimated Impact, Owner, Confidence, Monitoring Plan.
- **AI Summary**: Clean narrative brief with trust indicator (`LLM · Narration only`) and expandable technical insight breakdown.

### 6. Evidence & Trust / Audit Ledger
- **Title**: `"EVIDENCE & TRUST"`
- Multi-Source Evidence Retrieval summary (4 telemetry sources checked, Evidence verified, Deterministic analysis).
- Expandable `"View technical audit"` detailed ledger (Step, Engine, Latency, Cost, LLM usage, Provenance notes).

### 7. Decision Persistence & Active Queue Removal
- Actions: `[ Approve & Execute ]`, `[ Reject Action ]`, `[ Ignore Signal ]`.
- If `Reject`: Reason selector (`Wrong cause`, `Missing evidence`, `Wrong impact`, `Wrong recommendation`, `Other`).
- **Approve Action**: Persists decision to backend `decisions.csv`, marks alert as handled in frontend state, shows `"Decision recorded"` confirmation, and IMMEDIATELY removes alert from active dashboard queue.

---

## 🧪 Verification Commands

```bash
# Run Python backend unit & integration tests (16 tests)
pytest backend/tests

# Run full scenario validation script
python scenario_test.py

# Build frontend production bundle
cd frontend && npm run build && cd ..

# Start FastAPI full-stack server
python -m uvicorn backend.app.main:app --port 8000
```
