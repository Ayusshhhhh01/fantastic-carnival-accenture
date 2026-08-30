from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.schemas.alert import AnalysisResponse, DashboardResponse, InvestigationResponse
from backend.app.dependencies import get_analysis_service
from backend.app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/api/v1", tags=["alerts"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    persona: str = Query("Category Manager", pattern="^(Category Manager|CXO)$"),
    service: AnalysisService = Depends(get_analysis_service)
) -> DashboardResponse:
    return DashboardResponse.model_validate(service.dashboard(persona=persona))


@router.get("/alerts/{alert_id}", response_model=AnalysisResponse)
def alert(alert_id: str, service: AnalysisService = Depends(get_analysis_service)) -> AnalysisResponse:
    try:
        return AnalysisResponse.model_validate(service.get_alert(alert_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found") from exc


@router.get("/alerts/{alert_id}/investigate", response_model=InvestigationResponse)
def investigate(alert_id: str, persona: str = Query("Category Manager", pattern="^(Category Manager|CXO)$"), service: AnalysisService = Depends(get_analysis_service)) -> InvestigationResponse:
    """Investigate an alert with path tracking (fast/slow)."""
    try:
        return InvestigationResponse.model_validate(service.investigate_alert(alert_id, persona))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found") from exc
