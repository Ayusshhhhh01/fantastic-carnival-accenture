from typing import Any

from pydantic import BaseModel, Field


class HypothesisResponse(BaseModel):
    name: str
    supported: bool
    score: float = 0.0
    confidence_pct: int | None = None
    verdict: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)
