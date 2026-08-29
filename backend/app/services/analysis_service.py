from typing import Any

from backend.app.causal.pipeline import CausalPipeline
from backend.app.infrastructure.repositories.alert_repository import AlertRepository
from backend.app.infrastructure.llm.client import narrate, self_verify
from cause.engine import redact_for_cxo


class AnalysisService:
    def __init__(self, pipeline: CausalPipeline | None = None):
        self.pipeline = pipeline or CausalPipeline()
        self.alerts = AlertRepository()
        self._dashboard: dict[str, Any] | None = None

    def dashboard(self, refresh: bool = False) -> dict[str, Any]:
        if self._dashboard is None or refresh:
            self._dashboard = self.pipeline.execute()
        return self._dashboard

    def get_alert(self, alert_id: str) -> dict[str, Any]:
        result = self.alerts.find(self.dashboard(), alert_id)
        if result is None:
            raise KeyError(alert_id)
        return result

    def investigate_alert(self, alert_id: str, persona: str) -> dict[str, Any]:
        """Investigate alert and determine path type (FAST/SLOW/ABSTAIN)."""
        result = self.get_alert(alert_id)
        route = result.get("route", "ABSTAIN")
        
        # Determine path type based on route
        if route == "ABSTAIN":
            path_type = "ABSTAIN"
            path_success = False
        elif route in ["RESOLVED", "FAST_PATH"]:
            path_type = "FAST"
            path_success = True
        else:  # UNRESOLVED_CONFLICT
            path_type = "SLOW"
            path_success = False
        
        # Generate narrative for investigation
        payload = redact_for_cxo(dict(result)) if persona == "CXO" else dict(result)
        text, engine = narrate(payload, persona)
        clean, removed, audit = self_verify(text, payload)
        narrative = {
            "text": " ".join(clean.split()).strip(),
            "engine": engine,
            "removed_claims": removed,
            "audit": audit
        }
        
        # Sort hypotheses by confidence for slow path
        hypotheses = result.get("hypotheses", [])
        hypotheses_sorted = sorted(hypotheses, key=lambda h: h.get("confidence_pct", 0) or h.get("score", 0), reverse=True)
        
        return {
            "alert_id": alert_id,
            "alert": result.get("alert"),
            "route": route,
            "path_type": path_type,
            "path_success": path_success,
            "hypotheses": hypotheses_sorted,
            "confidence": result.get("confidence"),
            "conflict": result.get("conflict"),
            "recommendation": result.get("recommendation"),
            "fast_path": result.get("fast_path"),
            "abstention": result.get("abstention"),
            "rag_evidence": result.get("rag_evidence", []),
            "persona": persona,
            "narrative": narrative
        }
