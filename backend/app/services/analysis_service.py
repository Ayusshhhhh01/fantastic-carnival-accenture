from typing import Any

from backend.app.causal.pipeline import CausalPipeline
from backend.app.infrastructure.repositories.alert_repository import AlertRepository


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
