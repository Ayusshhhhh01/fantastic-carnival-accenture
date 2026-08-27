from fastapi import APIRouter, Depends, Query

from backend.app.api.schemas.alert import DashboardResponse
from backend.app.dependencies import get_analysis_service
from backend.app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])


@router.post("/refresh", response_model=DashboardResponse)
def refresh(service: AnalysisService = Depends(get_analysis_service)) -> DashboardResponse:
    return DashboardResponse.model_validate(service.dashboard(refresh=True))
