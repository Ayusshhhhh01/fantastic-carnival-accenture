from cause.engine import redact_for_cxo
from backend.app.infrastructure.llm.client import narrate, self_verify
from .analysis_service import AnalysisService


class NarrativeService:
    def __init__(self, analysis: AnalysisService):
        self.analysis = analysis

    def create(self, alert_id: str, persona: str) -> dict:
        result = self.analysis.get_alert(alert_id)
        if result.get("route") == "ABSTAIN":
            return {
                "alert_id": alert_id,
                "persona": persona,
                "text": "Insufficient evidence — CAUSE abstained from generating a definitive explanation.",
                "engine": "NONE (Abstained)",
                "removed_claims": [],
                "audit": "Abstained (No LLM call)"
            }
        payload = redact_for_cxo(dict(result)) if persona == "CXO" else dict(result)
        text, engine = narrate(payload, persona)
        clean, removed, audit = self_verify(text, payload)
        return {"alert_id": alert_id, "persona": persona, "text": " ".join(clean.split()).strip(), "engine": engine, "removed_claims": removed, "audit": audit}
