from typing import Any, Literal

from pydantic import BaseModel


class NarrativeResponse(BaseModel):
    alert_id: str
    persona: Literal["Category Manager", "CXO"]
    text: str
    engine: str
    removed_claims: list[dict[str, Any]]
    audit: str
