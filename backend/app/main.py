from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import alerts, analyses, decisions, health, narratives
from backend.app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.api_title, version=settings.api_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(alerts.router)
app.include_router(analyses.router)
app.include_router(narratives.router)
app.include_router(decisions.router)


# In production the API and React UI share one origin. Vite still serves the
# UI separately during development for hot module reloading.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if (FRONTEND_DIST / "assets").is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str = "") -> FileResponse:
    """Return the React shell for direct links and client-side routes."""
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(
            status_code=404,
            detail="Frontend build not found. Run 'npm.cmd run build' in frontend.",
        )
    return FileResponse(index)
