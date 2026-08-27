from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.schemas.alert import AnalysisResponse, DashboardResponse
from backend.app.dependencies import get_analysis_service
from backend.app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/v1", tags=["alerts"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(service: AnalysisService = Depends(get_analysis_service)) -> DashboardResponse:
    return DashboardResponse.model_validate(service.dashboard())


@router.get("/alerts/{alert_id}", response_model=AnalysisResponse)
def alert(alert_id: str, service: AnalysisService = Depends(get_analysis_service)) -> AnalysisResponse:
    try:
        return AnalysisResponse.model_validate(service.get_alert(alert_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found") from exc
