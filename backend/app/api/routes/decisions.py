from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.schemas.decision import DecisionRequest, DecisionResponse
from backend.app.dependencies import get_decision_service
from backend.app.services.decision_service import DecisionService

router = APIRouter(prefix="/api/v1", tags=["decisions"])


@router.post("/alerts/{alert_id}/decisions", response_model=DecisionResponse)
def decision(
    alert_id: str,
    request: DecisionRequest,
    service: DecisionService = Depends(get_decision_service),
) -> DecisionResponse:
    try:
        return DecisionResponse.model_validate(
            service.record(alert_id, request.decision, request.persona, request.feedback)
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found") from exc


@router.post("/reset-demo")
def reset_demo(
    service: DecisionService = Depends(get_decision_service),
) -> dict[str, str]:
    return service.reset_demo()
