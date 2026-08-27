from functools import lru_cache

from .config import get_settings
from .infrastructure.repositories.decision_repository import DecisionRepository
from .services.analysis_service import AnalysisService
from .services.decision_service import DecisionService
from .services.narrative_service import NarrativeService


@lru_cache
def get_analysis_service() -> AnalysisService:
    return AnalysisService()


@lru_cache
def get_narrative_service() -> NarrativeService:
    return NarrativeService(get_analysis_service())


@lru_cache
def get_decision_service() -> DecisionService:
    return DecisionService(
        get_analysis_service(),
        DecisionRepository(get_settings().decisions_path),
    )
