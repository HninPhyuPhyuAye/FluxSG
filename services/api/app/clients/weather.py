from datetime import UTC, datetime

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models.weather import AreaForecast, QualitySummary, WeatherOutlook


class SourceLocation(BaseModel):
    latitude: float
    longitude: float


class SourceArea(BaseModel):
    name: str
    label_location: SourceLocation


class SourcePeriod(BaseModel):
    start: datetime
    end: datetime


class SourceForecast(BaseModel):
    area: str
    forecast: str


class SourceItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    update_timestamp: datetime
    valid_period: SourcePeriod
    forecasts: list[SourceForecast] = Field(default_factory=list)


class SourceData(BaseModel):
    area_metadata: list[SourceArea]
    items: list[SourceItem]


class SourceResponse(BaseModel):
    code: int
    data: SourceData


class WeatherSourceError(RuntimeError):
    """Raised when the upstream weather source cannot provide trusted data."""


class WeatherClient:
    def __init__(self, url: str, timeout_seconds: float = 8.0) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds

    async def fetch(self) -> WeatherOutlook:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(self.url, headers={"User-Agent": "FluxSG/0.1"})
                response.raise_for_status()
            payload = SourceResponse.model_validate(response.json())
        except (httpx.HTTPError, ValueError, ValidationError) as exc:
            raise WeatherSourceError("The weather source returned an invalid response") from exc

        if payload.code != 0 or not payload.data.items:
            raise WeatherSourceError("The weather source reported no current forecast")

        item = payload.data.items[0]
        locations = {area.name: area.label_location for area in payload.data.area_metadata}
        forecasts: list[AreaForecast] = []
        issues: list[str] = []

        for forecast in item.forecasts:
            location = locations.get(forecast.area)
            if location is None:
                issues.append(f"Missing coordinates for {forecast.area}")
                continue
            if not forecast.forecast.strip():
                issues.append(f"Missing forecast for {forecast.area}")
                continue
            forecasts.append(
                AreaForecast(
                    area=forecast.area,
                    forecast=forecast.forecast.strip(),
                    latitude=location.latitude,
                    longitude=location.longitude,
                )
            )

        received = len(item.forecasts)
        valid = len(forecasts)
        completeness = round((valid / received * 100) if received else 0, 1)
        quality_status = "healthy" if received > 0 and completeness == 100 else "degraded"

        return WeatherOutlook(
            source="data.gov.sg / NEA",
            source_url=self.url,
            source_updated_at=item.update_timestamp,
            ingested_at=datetime.now(UTC),
            valid_from=item.valid_period.start,
            valid_to=item.valid_period.end,
            forecasts=forecasts,
            quality=QualitySummary(
                status=quality_status,
                received_records=received,
                valid_records=valid,
                completeness_percent=completeness,
                issues=issues,
            ),
        )
