from typing import Any


class AlertRepository:
    def find(self, dashboard: dict[str, Any], alert_id: str) -> dict[str, Any] | None:
        return next(
            (item for item in dashboard.get("alerts", []) if item["alert"]["id"] == alert_id),
            None,
        )
