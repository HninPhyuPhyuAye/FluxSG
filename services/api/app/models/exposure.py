from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.transport import BusArrivalBoard


class ExposureComponents(BaseModel):
    model_config = ConfigDict(frozen=True)

    psi: float = Field(ge=0, le=55)
    pm25_spike: float = Field(ge=0, le=30)
    outdoor_wait: float = Field(ge=0, le=15)


class StopExposureAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: list[str]
    assessed_at: datetime
    air_observed_at: datetime
    region: str
    region_distance_km: float = Field(ge=0)
    psi_24h: int = Field(ge=0)
    pm25_1h: int = Field(ge=0)
    next_bus_minutes: int | None = Field(default=None, ge=0)
    services_reported: int = Field(ge=0)
    score: int = Field(ge=0, le=100)
    band: str
    components: ExposureComponents
    explanation: list[str]
    guidance: str
    guidance_url: str
    disclaimer: str


class CommuteIntelligence(BaseModel):
    model_config = ConfigDict(frozen=True)

    arrivals: BusArrivalBoard
    exposure: StopExposureAssessment
