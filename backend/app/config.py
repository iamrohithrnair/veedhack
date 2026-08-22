from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env.local", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    openai_api_key: str | None = None
    tavily_api_key: str | None = None
    pioneer_api_key: str | None = None
    fal_key: str | None = None
    pioneer_model_id: str | None = None

    database_path: Path = BACKEND_DIR / "charismate.db"
    pioneer_base_url: str = "https://api.pioneer.ai"
    openai_model: str = "gpt-5.6-sol"
    openai_tts_model: str = "tts-1"
    openai_tts_voice: str = "onyx"
    fal_image_model: str = "fal-ai/nano-banana"
    fal_animate_model: str = "fal-ai/wan/v2.2-14b/animate"
    fal_lipsync_model: str = "veed/lipsync/v2"
    pipeline_timeout_seconds: float = Field(default=900, gt=0)
    cors_origins: str = "http://localhost:3000"

    def require(self, name: str) -> str:
        value = getattr(self, name, None)
        if not value:
            raise RuntimeError(f"{name.upper()} is required for this pipeline stage")
        return str(value)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
