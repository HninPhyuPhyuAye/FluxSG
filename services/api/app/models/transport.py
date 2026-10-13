from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.weather import QualitySummary


class BusStop(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str = Field(pattern=r"^\d{5}$")
    road_name: str
    description: str
    latitude: float
    longitude: float


class TransportNetworkSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    source_url: str
    ingested_at: datetime
    bus_stop_count: int = Field(ge=0)
    service_count: int = Field(ge=0)
    route_pattern_count: int = Field(ge=0)
    operator_counts: dict[str, int]
    quality: QualitySummary


class BusStopSearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    query: str
    ingested_at: datetime
    stops: list[BusStop]
    quality: QualitySummary


class ArrivalEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    estimated_arrival: datetime
    minutes: int = Field(ge=0)
    display: str
    load: str | None
    load_label: str
    wheelchair_accessible: bool
    monitored: bool
    vehicle_type: str


class BusServiceArrival(BaseModel):
    model_config = ConfigDict(frozen=True)

    service_no: str
    operator: str
    arrivals: list[ArrivalEstimate]


class BusArrivalBoard(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    source_url: str
    fetched_at: datetime
    bus_stop: BusStop
    services: list[BusServiceArrival]
    quality: QualitySummary


class BusRouteStop(BaseModel):
    model_config = ConfigDict(frozen=True)

    service_no: str
    operator: str
    direction: int
    stop_sequence: int
    bus_stop_code: str
    distance_km: float
    weekday_first_bus: str
    weekday_last_bus: str
    saturday_first_bus: str
    saturday_last_bus: str
    sunday_first_bus: str
    sunday_last_bus: str


class BusRouteResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    service_no: str
    ingested_at: datetime
    stops: list[BusRouteStop]
    quality: QualitySummary
