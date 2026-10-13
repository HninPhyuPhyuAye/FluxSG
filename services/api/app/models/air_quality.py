from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.weather import QualitySummary


class RegionAirQuality(BaseModel):
    model_config = ConfigDict(frozen=True)

    region: str
    latitude: float
    longitude: float
    psi_24h: int = Field(ge=0)
    pm25_24h: int = Field(ge=0)
    pm25_1h: int = Field(ge=0)
    level: str


class HealthGuidance(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: str
    general_population: str
    sensitive_groups: str
    source_url: str
    disclaimer: str


class AirQualitySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    source_urls: list[str]
    observed_at: datetime
    updated_at: datetime
    ingested_at: datetime
    national_psi: int = Field(ge=0)
    national_level: str
    haze_alert: bool
    regions: list[RegionAirQuality]
    guidance: HealthGuidance
    quality: QualitySummary
