from typing import Any

from cause.engine import run


class CausalPipeline:
    """Stable application boundary for deterministic CAUSE analysis."""

    def execute(self) -> dict[str, Any]:
        return run()
