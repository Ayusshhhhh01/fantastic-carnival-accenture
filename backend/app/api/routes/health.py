from fastapi import APIRouter

from backend.app.api.schemas.health import HealthResponse
from backend.app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", version=settings.api_version)
