from typing import Any

from backend.app.config import get_settings
from backend.app.causal.pipeline import CausalPipeline
from backend.app.infrastructure.repositories.alert_repository import AlertRepository
from backend.app.infrastructure.repositories.decision_repository import DecisionRepository
from backend.app.infrastructure.llm.client import narrate, self_verify
from cause.engine import redact_for_cxo


class AnalysisService:
    def __init__(self, pipeline: CausalPipeline | None = None, decisions: DecisionRepository | None = None):
        self.pipeline = pipeline or CausalPipeline()
        self.alerts = AlertRepository()
        self.decisions = decisions or DecisionRepository(get_settings().decisions_path)
        self._dashboard: dict[str, Any] | None = None

    def dashboard(self, refresh: bool = False) -> dict[str, Any]:
        if self._dashboard is None or refresh:
            self._dashboard = self.pipeline.execute()
        
        # Always dynamically re-read decisions.csv on every dashboard call
        handled_ids = self.decisions.get_handled_alert_ids()
        if self._dashboard and "alerts" in self._dashboard:
            filtered_alerts = [a for a in self._dashboard["alerts"] if str(a.get("alert", {}).get("id")) not in handled_ids]
            res = dict(self._dashboard)
            res["alerts"] = filtered_alerts
            return res

        return self._dashboard

    def get_alert(self, alert_id: str) -> dict[str, Any]:
        raw_dash = self.pipeline.execute()
        result = self.alerts.find(raw_dash, alert_id)
        if result is None:
            raise KeyError(alert_id)
        return result

    def investigate_alert(self, alert_id: str, persona: str) -> dict[str, Any]:
        """Investigate alert and determine path type (FAST/SLOW/ABSTAIN)."""
        raw_result = self.get_alert(alert_id)
        result = redact_for_cxo(dict(raw_result)) if persona == "CXO" else dict(raw_result)
        route = result.get("route", "ABSTAIN")
        
        if route == "ABSTAIN":
            path_type = "ABSTAIN"
            path_success = False
            narrative = None  # ZERO LLM calls on ABSTAIN
        elif route == "FAST_PATH":
            path_type = "FAST"
            path_success = True
            text, engine = narrate(result, persona)
            clean, removed, audit = self_verify(text, result)
            narrative = {
                "text": " ".join(clean.split()).strip(),
                "engine": engine,
                "removed_claims": removed,
                "audit": audit
            }
        else:  # RESOLVED or UNRESOLVED_CONFLICT (both are Path 2: SLOW)
            path_type = "SLOW"
            path_success = (route == "RESOLVED")
            text, engine = narrate(result, persona)
            clean, removed, audit = self_verify(text, result)
            narrative = {
                "text": " ".join(clean.split()).strip(),
                "engine": engine,
                "removed_claims": removed,
                "audit": audit
            }
        
        # Sort hypotheses by confidence/score (ranking exactly 4 hypotheses)
        hypotheses = result.get("hypotheses", [])
        hypotheses_sorted = sorted(hypotheses, key=lambda h: (h.get("confidence_pct", 0) or h.get("score", 0)), reverse=True)
        
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
            "narrative": narrative,
            "ledger_rows": self.dashboard().get("ledger_rows", [])
        }
