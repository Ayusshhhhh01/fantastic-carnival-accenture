from typing import Any

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
