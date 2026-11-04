from datetime import time
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_mode: str = "local"
    auth_mode: str = "demo_local"
    app_timezone: Literal["America/Lima"] = "America/Lima"
    database_url: SecretStr = SecretStr(
        "postgresql://aquaclean:aquaclean_local_only@db:5432/aquaclean"
    )
    gemini_api_key: SecretStr = SecretStr("")
    gemini_chat_model: str = "gemini-3.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"
    embedding_dimension: int = 768
    llm_timeout_seconds: int = 60
    max_model_calls: int = 10
    max_context_chars: int = 60000
    max_pending_runs: int = 20
    runtime_database_password: SecretStr = SecretStr("aquaclean_local_only")
    max_clarifications: int = 2
    wait_hours: int = 24
    max_upload_mb: int = 10
    max_attachments: int = 5
    max_pdf_pages: int = 20
    max_audio_seconds: int = 120
    slot_capacity: int = 8
    max_bags: int = 40
    max_pickup_days: int = 30
    max_reprocesses: int = 1
    max_quality_evidence_requests: int = 1
    max_incident_clarifications: int = 1
    pilot_morning_dispatch: time = time(10, 30)
    pilot_afternoon_dispatch: time = time(16, 0)
    media_root: Path = Path("data/media")
    static_root: Path = Path("web/dist")

    @property
    def ai_available(self) -> bool:
        return bool(self.gemini_api_key.get_secret_value())

    @property
    def policy_version(self) -> str:
        from aquaclean.domain.entities import digest

        return (
            "pilot-1:"
            + digest(
                {
                    key: getattr(self, key)
                    for key in [
                        "max_bags",
                        "max_pickup_days",
                        "max_reprocesses",
                        "max_clarifications",
                        "max_quality_evidence_requests",
                        "max_incident_clarifications",
                        "pilot_morning_dispatch",
                        "pilot_afternoon_dispatch",
                    ]
                }
            )[:12]
        )
