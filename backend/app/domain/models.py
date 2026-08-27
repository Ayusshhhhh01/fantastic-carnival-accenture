from typing import Any

from pydantic import BaseModel, Field

from .enums import Decision, Persona, Route


class Alert(BaseModel):
    id: str
    kpi: str
    category: str
    region: str
    week_start: str
    delta_inr: float
    pct_change: float | None = None
    route: Route | None = None


class Hypothesis(BaseModel):
    name: str
    supported: bool
    score: float = 0.0
    confidence_pct: int | None = None
    verdict: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)


class Recommendation(BaseModel):
    driver: str
    lever: str
    action: str
    estimated_impact: float | None = None
    owner: str
    confidence: str
    monitoring_plan: str
    basis: str


class DecisionRecord(BaseModel):
    alert_id: str
    decision: Decision
    persona: Persona
    feedback: str = ""
