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
DEDICATED TRIAGE SCREEN
        ↓
FAST PATH OR DEEP PATH
        ↓
RCA RESULTS (4 COMPETING CAUSES - ALL COLLAPSED)
        ↓
USER CHOOSES EXPAND CAUSE DETAILS
        ↓
RCA DETAIL (EVIDENCE / KPI / CONFIDENCE / CONFLICT)
        ↓
RECOMMENDATION (ACTION DIRECTIVE / EXPECTED IMPACT / MATRIX / LLM NARRATION)
        ↓
APPROVE / REJECT
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

### 4. Dedicated Triage & Investigation Flow (`/investigate/:alertId`)
- **Automated Triage Scan**:
  - **Path 1 (Direct Event Match)**: Scans operational change logs for pricing/promo/inventory/IT events. If match found $\rightarrow$ Fast Path.
  - **Path 2 (Deep Causal Research)**: Retrieves multi-source telemetry evidence $\rightarrow$ evaluates 4 canonical hypotheses $\rightarrow$ scores Weighted Evidence Confidence $\rightarrow$ checks cross-regional contradiction.
- **Fast Path UI**:
  - Verified event details (Type, Date, Description, Category/Region match).
  - Recommended action directive, monitoring plan, and evidence citations.
- **Deep Path UI (Resolved)**:
  - Evaluates **exactly 4 canonical competing causes**:
    1. Supply-side stock-out
    2. Demand-side campaign/demand shift
    3. Pricing change
    4. Operational / channel disruption
  - **All cards collapsed initially**: `selectedCauseIndex` starts as `null`. No pre-emptive root-cause answer is shown before user interaction.
  - User explicitly clicks `"Expand Cause Details"` to inspect RCA Detail (Evidence Provenance, Real KPI Snapshot, Weighted Evidence Confidence, Conflict Audit).
  - **Single Top-Only Navigation**: `[← Back to RCA List]` control positioned exclusively at the top of detail screens.
- **Conflict Path UI (Unresolved Conflict)**:
  - Displays `"Conflicting evidence"` and signal contradiction details (Signal A vs Signal B).
  - Withholds automated diagnosis and explicitly directs manual audit.
- **Abstain Path UI (Diagnostic Abstention)**:
  - Displays `"Insufficient evidence to diagnose"` and missing data gaps.
  - Withholds recommendation. ZERO LLM calls made.

### 5. Recommendation & AI Executive Summary
- Grounded in deterministic Causal Engine: Driver, Lever, Action (strongest visual element), Expected Impact, Owner, Confidence, Monitoring Plan.
- **AI Summary**: Clean narrative brief with trust indicator (`LLM · Narration only`) and expandable technical insight breakdown.

### 6. Evidence & Trust / Audit Ledger
- **Title**: `"EVIDENCE & TRUST"`
- Multi-source evidence retrieval summary across 4 empirical telemetry sources (POS, CRM, ERP, Change Log).
- Technical Audit table with latency, cost, and provenance notes.

### 7. Decision Persistence & Active Queue Removal
- Actions: `[ Approve & Execute ]`, `[ Reject Action ]`.
- If `Reject`: Reason selector (`Wrong cause`, `Missing evidence`, `Wrong impact`, `Wrong recommendation`, `Other`).
- **Approve Action**: Persists decision to backend `decisions.csv` (with hypothesis-specific calibration tag), navigates immediately to dashboard, and removes alert from active dashboard queue.

---

## 🧪 Verification Commands

```bash
# Run Python backend unit & integration tests + scenario test
python -m pytest backend/tests scenario_test.py -q

# Compile backend
python -m compileall -q backend cause scripts

# Build frontend production bundle
cd frontend && npm run build && cd ..

# Start FastAPI full-stack server
python -m uvicorn backend.app.main:app --port 8000
```
