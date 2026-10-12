from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AreaForecast(BaseModel):
    model_config = ConfigDict(frozen=True)

    area: str
    forecast: str
    latitude: float
    longitude: float


class QualitySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    received_records: int = Field(ge=0)
    valid_records: int = Field(ge=0)
    completeness_percent: float = Field(ge=0, le=100)
    issues: list[str]


class WeatherOutlook(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    source_url: str
    source_updated_at: datetime
    ingested_at: datetime
    valid_from: datetime
    valid_to: datetime
    forecasts: list[AreaForecast]
    quality: QualitySummary


class IntegrationStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    configured: bool
    state: str
    next_step: str

