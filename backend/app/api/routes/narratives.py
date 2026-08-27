from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.schemas.narrative import NarrativeResponse
from backend.app.dependencies import get_narrative_service
from backend.app.services.narrative_service import NarrativeService

router = APIRouter(prefix="/api/v1/alerts", tags=["narratives"])


@router.get("/{alert_id}/narrative", response_model=NarrativeResponse)
def narrative(
    alert_id: str,
    persona: str = Query("Category Manager", pattern="^(Category Manager|CXO)$"),
    service: NarrativeService = Depends(get_narrative_service),
) -> NarrativeResponse:
    try:
        return NarrativeResponse.model_validate(service.create(alert_id, persona))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found") from exc
