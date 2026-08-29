from typing import Any, Literal

from pydantic import BaseModel


class DashboardResponse(BaseModel):
    alerts: list[dict[str, Any]]
    ledger_rows: list[dict[str, Any]]
    kpi_registry: dict[str, Any]
    cur_week: str


class AnalysisResponse(BaseModel):
    alert: dict[str, Any]
    route: str
    hypotheses: list[dict[str, Any]]
    confidence: dict[str, Any]
    conflict: dict[str, Any]
    recommendation: dict[str, Any]
    fast_path: dict[str, Any] | None = None
    abstention: dict[str, Any] | None = None
    rag_evidence: list[dict[str, Any]] = []


class InvestigationResponse(BaseModel):
    """Response for investigation endpoint - includes path status."""
    alert_id: str
    alert: dict[str, Any]
    route: str
    path_type: Literal["FAST", "SLOW", "ABSTAIN"]
    path_success: bool
    hypotheses: list[dict[str, Any]]
    confidence: dict[str, Any]
    conflict: dict[str, Any] | None = None
    recommendation: dict[str, Any] | None = None
    fast_path: dict[str, Any] | None = None
    abstention: dict[str, Any] | None = None
    rag_evidence: list[dict[str, Any]] = []
    persona: str
    narrative: dict[str, Any] | None = None
    ledger_rows: list[dict[str, Any]] = []
