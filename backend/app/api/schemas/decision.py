from typing import Literal

from pydantic import BaseModel, Field


class DecisionRequest(BaseModel):
    decision: Literal["approved", "rejected", "ignored"]
    persona: str = Field(min_length=1)
    feedback: str = ""
    hypothesis_type: str | None = None


class DecisionResponse(BaseModel):
    alert_id: str
    decision: str
    feedback: str
