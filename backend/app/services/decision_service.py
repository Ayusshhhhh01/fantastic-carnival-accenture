from datetime import datetime, timezone
from backend.app.infrastructure.repositories.decision_repository import DecisionRepository
from .analysis_service import AnalysisService


class DecisionService:
    def __init__(self, analysis: AnalysisService, repository: DecisionRepository):
        self.analysis = analysis
        self.repository = repository

    def record(
        self,
        alert_id: str,
        decision: str,
        persona: str,
        feedback: str,
        hypothesis_type: str | None = None
    ) -> dict[str, str]:
        result = self.analysis.get_alert(alert_id)
        alert = result["alert"]

        hyp_type = hypothesis_type
        if not hyp_type:
            hyps = result.get("hypotheses", [])
            top_hyp = next((h for h in hyps if h.get("supported")), hyps[0] if hyps else None)
            if top_hyp and "name" in top_hyp:
                hyp_type = top_hyp["name"].split("-")[0].split(" ")[0].strip()
            else:
                hyp_type = "Supply"

        row = {
            "alert_id": alert_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": alert["category"],
            "region": alert["region"],
            "route": result.get("route", ""),
            "persona": persona,
            "decision": decision,
            "feedback": feedback,
            "hypothesis_type": hyp_type
        }
        self.repository.append(row)
        return {"alert_id": alert_id, "decision": decision, "feedback": feedback}

    def reset_demo(self) -> dict[str, str]:
        self.repository.clear()
        self.analysis._dashboard = None
        return {"status": "ok", "message": "Demo decision state cleared successfully"}
