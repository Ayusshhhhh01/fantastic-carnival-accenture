# Implementation Notes: Enhanced User Flow

## Overview
This document describes the new multi-page investigation flow for the CAUSE platform, including login page, investigation detail page, and responsive design enhancements.

## New Features Implemented

### 1. Login Page
**File**: `frontend/src/pages/LoginPage.jsx`

- **Purpose**: Initial entry point where users select their role (CXO or Category Manager)
- **Personas Supported**:
  - **CXO Suite**: Enterprise-wide portfolio view
  - **Category Manager**: Electronics, Apparel & Home portfolios
- **UX Features**:
  - Card-based persona selection with hover effects
  - Visual feedback for active selection
  - Smooth navigation to dashboard with selected persona
  - Highly responsive design for mobile devices

**Route**: `/` (default entry)

### 2. Investigation Detail Page
**File**: `frontend/src/pages/InvestigationDetailPage.jsx`

- **Purpose**: Comprehensive root cause analysis and recommendation view
- **Two-Path Investigation Flow**:

#### Fast Path (Successful Analysis)
- Route indicators: `RESOLVED` or `FAST_PATH`
- Shows single primary hypothesis with high confidence
- Displays:
  - KPI trend chart
  - Verified root cause
  - Recommended action with monitoring plan
  - Supporting evidence
  - Narrative brief with audit trail

#### Slow Path (Unresolved/Conflicting Analysis)
- Route indicator: `UNRESOLVED_CONFLICT`
- Shows top 5 hypotheses ranked by confidence score
- Each hypothesis is expandable to reveal:
  - Detailed verdict
  - Supporting evidence
  - RCA details
  - Estimated impact

#### Abstain Path (Insufficient Data)
- Route indicator: `ABSTAIN`
- Shows diagnostic abstention reason
- Lists required data for better diagnosis

**Features**:
- KPI trend visualization with recharts
- Confidence scoring display
- Evidence retrieval summary
- Expandable hypothesis details
- Approve/Reject decision buttons with backend persistence
- Back navigation to dashboard
- Responsive design for all screen sizes

**Route**: `/investigate/:alertId?persona={persona}`

### 3. Enhanced Dashboard
**File**: `frontend/src/App.jsx` (DashboardPage component)

- **Improvements**:
  - "Investigate" button now navigates to detailed investigation page
  - Changed from inline decision in drawer to dedicated investigation page
  - Maintains existing alert card layout
  - Quick preview drawer still available for initial inspection

### 4. KPI Chart Component
**File**: `frontend/src/components/KPIChart.jsx`

- **Features**:
  - Line chart showing KPI trend over time
  - Comparison with expected baseline
  - Variance percentage display
  - Responsive sizing
  - Color-coded for negative/positive impacts

### 5. API Enhancements

#### New Endpoint: Investigate Alert
```
GET /api/v1/alerts/{alert_id}/investigate?persona={persona}
```

**Request Parameters**:
- `alert_id` (path): Alert identifier
- `persona` (query): "Category Manager" or "CXO"

**Response** (`InvestigationResponse`):
- `alert_id`: Alert identifier
- `alert`: Alert details
- `route`: RESOLVED | FAST_PATH | UNRESOLVED_CONFLICT | ABSTAIN
- `path_type`: FAST | SLOW | ABSTAIN
- `path_success`: Boolean indicating if investigation succeeded
- `hypotheses`: List sorted by confidence (descending)
- `confidence`: Confidence metrics
- `recommendation`: Recommended action
- `narrative`: Generated narrative brief with audit trail
- `rag_evidence`: Supporting evidence records

**Backend Changes**:
- Updated `AnalysisService.investigate_alert()` method
- Sorts hypotheses by confidence score for slow path
- Generates narrative and audit trail
- Determines path type based on route

### 6. Styling Updates

#### New CSS Classes for Login Page
- `.login-shell`: Main container
- `.login-topbar`: Header with logo
- `.personas-grid`: Grid of persona cards
- `.persona-card`: Individual persona selection card
- `.primary-button`: Call-to-action button
- `.login-container`: Centered content container

#### New CSS Classes for Investigation Page
- `.investigation-shell`: Main container
- `.investigation-header`: Top navigation with back button
- `.path-badge`: Visual indicator for path type (FAST/SLOW/ABSTAIN)
- `.chart-container`: KPI chart wrapper
- `.hypothesis-card`: Individual hypothesis card (primary or expandable)
- `.hypothesis-detail`: Expanded hypothesis details
- `.recommendation-card`: Recommendation display
- `.evidence-list`: Supporting evidence

#### Responsive Breakpoints
- **Desktop** (1024px+): Full grid layouts, side-by-side components
- **Tablet** (768px - 1023px): 2-column grids, stacked recommendations
- **Mobile** (<768px): Single column, stacked cards, simplified navigation

### 7. Frontend Dependencies Added
```json
{
  "react-router-dom": "latest",
  "recharts": "latest"
}
```

## Flow Diagram

```
┌─────────────────┐
│  Login Page (/)  │ ← User selects CXO or Category Manager
└────────┬────────┘
         │
         ↓
┌──────────────────────────┐
│ Dashboard (/dashboard)   │ ← Shows alerts, each with "Investigate" button
└────────┬─────────────────┘
         │
         ↓ (Click Investigate)
┌─────────────────────────────────────────┐
│ Investigation Detail (/investigate/:id) │
│                                         │
│ ┌──────────────────────────────────┐   │
│ │ FAST PATH                        │   │
│ │ (Successful Analysis)            │   │
│ ├──────────────────────────────────┤   │
│ │ - Single RCA                     │   │
│ │ - High confidence                │   │
│ │ - Detailed recommendation        │   │
│ └──────────────────────────────────┘   │
│                                         │
│ ┌──────────────────────────────────┐   │
│ │ SLOW PATH                        │   │
│ │ (Multiple Hypotheses)            │   │
│ ├──────────────────────────────────┤   │
│ │ - Top 5 RCAs                     │   │
│ │ - Ranked by confidence           │   │
│ │ - Expandable details             │   │
│ └──────────────────────────────────┘   │
│                                         │
│ [Approve] [Reject] [Back to Dashboard] │
└─────────────────────────────────────────┘
```

## Key Design Decisions

1. **Routing Strategy**: Used React Router for client-side routing
   - BrowserRouter for modern SPA experience
   - Query parameters for persona persistence
   - Hash-free URLs for SEO compatibility

2. **Path Determination**: Path type determined at investigation time (not at dashboard)
   - Allows lazy loading of investigation details
   - Reduces initial dashboard response time

3. **Hypothesis Sorting**: Hypotheses sorted by confidence score in API response
   - Slow path shows top 5 most confident options
   - Consistent ranking across slow path displays

4. **Chart Data Generation**: Sample data generation in frontend
   - Simulates realistic KPI trend
   - In production, would consume real historical data from backend

5. **Responsive Design**: Mobile-first approach with progressive enhancement
   - Base styles optimized for mobile
   - Breakpoints for tablet and desktop
   - Touch-friendly buttons and spacing

## Testing Checklist

- [ ] Login page displays both personas
- [ ] Persona selection navigates to dashboard with correct persona
- [ ] Dashboard loads alerts for selected persona
- [ ] "Investigate" button opens investigation detail page
- [ ] Fast path displays single RCA with high confidence
- [ ] Slow path displays top 5 hypotheses
- [ ] Slow path hypotheses are expandable
- [ ] Approve/Reject buttons persist decision to backend
- [ ] Back button returns to dashboard
- [ ] Chart renders with correct trend data
- [ ] Responsive design works on mobile (320px+)
- [ ] Responsive design works on tablet (768px)
- [ ] Responsive design works on desktop (1024px+)

## Performance Considerations

1. **Code Splitting**: Consider lazy loading investigation page component
2. **Chart Optimization**: Recharts handles responsive sizing efficiently
3. **API Caching**: Dashboard cache can be reused for investigation data
4. **Bundle Size**: Recharts library (~200KB gzipped) - acceptable for charting capability

## Future Enhancements

1. **Historical Data**: Connect chart to real historical data from backend
2. **Custom Date Range**: Allow users to select time range for chart
3. **Export Reports**: PDF/Excel export of investigation findings
4. **Collaboration**: Add comments/notes on alerts for team discussion
5. **Workflow Status**: Track alert status through workflow (Assigned, In Review, Closed)
6. **Notifications**: Real-time alerts for new anomalies

## Deployment Notes

1. **Frontend Build**:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

2. **Backend Build**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Application**:
   ```bash
   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
   ```

4. **Environment Variables**:
   - Ensure `VITE_API_URL` is set correctly in frontend if API is on different domain
   - Default: relative to current domain (works for single-port deployment)

5. **Docker Deployment**:
   - Dockerfile includes both frontend build and FastAPI server
   - See `docker-compose.yml` for multi-container setup
