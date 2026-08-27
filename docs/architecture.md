# CAUSE Architecture

## Request Flow

```text
React dashboard
    |
    | same-origin /api/v1 requests
    v
FastAPI routes
    |
    v
Application services
    |
    +--> Causal pipeline --> deterministic analysis result
    +--> Narrative service --> optional LLM or offline template
    +--> Decision service --> decision repository
```

## Backend Ownership

- `api`: HTTP methods, request validation, and response schemas.
- `domain`: stable business concepts and thresholds.
- `causal`: anomaly detection, evidence retrieval, hypothesis evaluation, confidence, conflicts, and recommendations.
- `infrastructure`: files, persistence, and external LLM adapters.
- `services`: application workflows that coordinate the lower layers.

`cause/` remains the compatibility package for the original validated engine. The public application boundary is `backend.app.causal.pipeline.CausalPipeline`, which allows the implementation to be decomposed further without changing the frontend API.

## Frontend Ownership

- `src/api`: all HTTP communication.
- `src/features`: feature-specific UI and state.
- `src/components`: reusable UI pieces.
- `src/pages`: route-level compositions.
- `src/router`: client-side routing when multiple pages are introduced.

The API client uses relative URLs in production. Vite proxies those same URLs during development. This keeps React Router and backend requests on one URL contract.

## Production Serving

The frontend build is written to `frontend/dist`. FastAPI mounts `/assets` and returns `index.html` for non-API paths. Therefore the deployed app needs only one process and one port:

```text
http://localhost:8000/       React application
http://localhost:8000/api/   FastAPI API
http://localhost:8000/docs   OpenAPI documentation
```
