from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd

# Handled decisions mean the alert has been acted upon / dismissed and is no longer active on Home
HANDLED_DECISIONS = {"approved", "approve", "dismissed", "dismiss", "removed", "remove", "ignored", "ignore"}


class DecisionRepository:
    def __init__(self, path: Path):
        self.path = path
        self._lock = Lock()

    def append(self, row: dict[str, Any]) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Ensure alert_id and decision are normalized strings
            if "alert_id" in row and row["alert_id"] is not None:
                row["alert_id"] = str(row["alert_id"]).strip()
            if "decision" in row and row["decision"] is not None:
                row["decision"] = str(row["decision"]).strip().lower()
            pd.DataFrame([row]).to_csv(self.path, mode="a", header=not self.path.exists(), index=False)

    def get_handled_alert_ids(self) -> set[str]:
        with self._lock:
            if not self.path.exists():
                return set()
            try:
                df = pd.read_csv(self.path)
                if df.empty or "alert_id" not in df.columns or "decision" not in df.columns:
                    return set()

                valid_rows = df.dropna(subset=["alert_id", "decision"]).copy()
                valid_rows["alert_id"] = valid_rows["alert_id"].astype(str).str.strip()
                valid_rows["decision"] = valid_rows["decision"].astype(str).str.strip().str.lower()

                if valid_rows.empty:
                    return set()

                # Preserve insertion order or timestamp order to get the latest effective decision
                if "timestamp" in valid_rows.columns:
                    valid_rows = valid_rows.sort_values(by="timestamp", ascending=True)

                effective_decisions: dict[str, str] = {}
                for _, row in valid_rows.iterrows():
                    effective_decisions[row["alert_id"]] = row["decision"]

                # Return alert IDs whose latest effective decision is a closing action
                return {
                    alert_id for alert_id, dec in effective_decisions.items()
                    if dec in HANDLED_DECISIONS
                }
            except Exception:
                return set()

    def clear(self) -> None:
        with self._lock:
            if self.path.exists():
                try:
                    self.path.unlink()
                except Exception:
                    pass
