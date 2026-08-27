from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_title: str = "CAUSE Causal Intelligence API"
    api_version: str = "1.0.0"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    decisions_path: Path = PROJECT_ROOT / "cause" / "data" / "decisions.csv"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
