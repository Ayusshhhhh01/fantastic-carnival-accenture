from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd


class DecisionRepository:
    def __init__(self, path: Path):
        self.path = path
        self._lock = Lock()

    def append(self, row: dict[str, Any]) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame([row]).to_csv(self.path, mode="a", header=not self.path.exists(), index=False)

    def get_handled_alert_ids(self) -> set[str]:
        with self._lock:
            if not self.path.exists():
                return set()
            try:
                df = pd.read_csv(self.path)
                if "alert_id" in df.columns:
                    return set(df["alert_id"].dropna().astype(str).tolist())
            except Exception:
                pass
            return set()
