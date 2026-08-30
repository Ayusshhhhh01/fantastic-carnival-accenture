from datetime import datetime, timezone
from backend.app.infrastructure.repositories.decision_repository import DecisionRepository
from .analysis_service import AnalysisService


class DecisionService:
    def __init__(self, analysis: AnalysisService, repository: DecisionRepository):
        self.analysis = analysis
        self.repository = repository

    def record(self, alert_id: str, decision: str, persona: str, feedback: str) -> dict[str, str]:
        result = self.analysis.get_alert(alert_id)
        alert = result["alert"]
        row = {
            "alert_id": alert_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": alert["category"],
            "region": alert["region"],
            "route": result["route"],
            "persona": persona,
            "decision": decision,
            "feedback": feedback
        }
        self.repository.append(row)
        return {"alert_id": alert_id, "decision": decision, "feedback": feedback}

    def reset_demo(self) -> dict[str, str]:
        self.repository.clear()
        self.analysis._dashboard = None
        return {"status": "ok", "message": "Demo decision state cleared successfully"}
