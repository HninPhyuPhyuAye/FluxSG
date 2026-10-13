from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FluxSG API"
    environment: str = "development"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    data_gov_weather_url: str = (
        "https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast"
    )
    data_gov_psi_url: str = "https://api-open.data.gov.sg/v2/real-time/api/psi"
    data_gov_pm25_url: str = "https://api-open.data.gov.sg/v2/real-time/api/pm25"
    lta_account_key: str | None = None
    lta_base_url: str = "https://datamall2.mytransport.sg/ltaodataservice"
    lta_cache_ttl_seconds: int = 21_600
    source_timeout_seconds: float = 8.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

