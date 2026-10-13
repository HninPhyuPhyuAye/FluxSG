import asyncio
from datetime import UTC, datetime

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models.air_quality import AirQualitySnapshot, HealthGuidance, RegionAirQuality
from app.models.weather import QualitySummary


class SourceLocation(BaseModel):
    latitude: float
    longitude: float


class SourceRegion(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    label_location: SourceLocation = Field(alias="labelLocation")


class SourceReadings(BaseModel):
    psi_twenty_four_hourly: dict[str, int] | None = None
    pm25_twenty_four_hourly: dict[str, int] | None = None
    pm25_one_hourly: dict[str, int] | None = None


class SourceItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    updated_timestamp: datetime = Field(alias="updatedTimestamp")
    timestamp: datetime
    readings: SourceReadings


class SourceData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    region_metadata: list[SourceRegion] = Field(alias="regionMetadata")
    items: list[SourceItem]


class SourceResponse(BaseModel):
    code: int
    data: SourceData


class AirQualitySourceError(RuntimeError):
    """Raised when official air-quality data is unavailable or malformed."""


def psi_level(value: int) -> str:
    if value <= 50:
        return "Good"
    if value <= 100:
        return "Moderate"
    if value <= 200:
        return "Unhealthy"
    if value <= 300:
        return "Very Unhealthy"
    return "Hazardous"


GUIDANCE: dict[str, tuple[str, str]] = {
    "Good": (
        "Normal activities can continue.",
        "Normal activities can continue.",
    ),
    "Moderate": (
        "Normal activities can generally continue.",
        "People unusually sensitive to air pollution can reduce prolonged or "
        "strenuous outdoor activity.",
    ),
    "Unhealthy": (
        "Reduce prolonged or strenuous outdoor activity.",
        "Children, older adults, pregnant people, and people with heart or lung "
        "conditions should minimise prolonged or strenuous outdoor activity.",
    ),
    "Very Unhealthy": (
        "Avoid prolonged or strenuous outdoor activity.",
        "Avoid outdoor activity where possible and follow official health advice.",
    ),
    "Hazardous": (
        "Minimise outdoor activity and follow official emergency health advice.",
        "Remain indoors where possible and follow official emergency health advice.",
    ),
}


class AirQualityClient:
    def __init__(self, psi_url: str, pm25_url: str, timeout_seconds: float = 8.0) -> None:
        self.psi_url = psi_url
        self.pm25_url = pm25_url
        self.timeout_seconds = timeout_seconds

    async def fetch(self) -> AirQualitySnapshot:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                psi_response, pm25_response = await asyncio.gather(
                    client.get(self.psi_url, headers={"User-Agent": "FluxSG/0.1"}),
                    client.get(self.pm25_url, headers={"User-Agent": "FluxSG/0.1"}),
                )
                psi_response.raise_for_status()
                pm25_response.raise_for_status()
            psi_payload = SourceResponse.model_validate(psi_response.json())
            pm25_payload = SourceResponse.model_validate(pm25_response.json())
        except (httpx.HTTPError, ValueError, ValidationError) as exc:
            raise AirQualitySourceError("Air-quality sources returned invalid data") from exc

        if psi_payload.code != 0 or pm25_payload.code != 0:
            raise AirQualitySourceError("Air-quality sources reported an error")
        if not psi_payload.data.items or not pm25_payload.data.items:
            raise AirQualitySourceError("Air-quality sources returned no current readings")

        psi_item = psi_payload.data.items[0]
        pm25_item = pm25_payload.data.items[0]
        psi_values = psi_item.readings.psi_twenty_four_hourly or {}
        pm25_24h_values = psi_item.readings.pm25_twenty_four_hourly or {}
        pm25_1h_values = pm25_item.readings.pm25_one_hourly or {}
        locations = {
            region.name: region.label_location for region in psi_payload.data.region_metadata
        }
        expected_regions = sorted(locations)
        regions: list[RegionAirQuality] = []
        issues: list[str] = []

        for region in expected_regions:
            missing = [
                metric
                for metric, values in (
                    ("PSI 24h", psi_values),
                    ("PM2.5 24h", pm25_24h_values),
                    ("PM2.5 1h", pm25_1h_values),
                )
                if region not in values
            ]
            if missing:
                issues.append(f"{region}: missing {', '.join(missing)}")
                continue
            psi = psi_values[region]
            regions.append(
                RegionAirQuality(
                    region=region,
                    latitude=locations[region].latitude,
                    longitude=locations[region].longitude,
                    psi_24h=psi,
                    pm25_24h=pm25_24h_values[region],
                    pm25_1h=pm25_1h_values[region],
                    level=psi_level(psi),
                )
            )

        if not regions:
            raise AirQualitySourceError("No complete regional air-quality readings were found")

        national_psi = max(region.psi_24h for region in regions)
        level = psi_level(national_psi)
        general, sensitive = GUIDANCE[level]
        completeness = round(len(regions) / len(expected_regions) * 100, 1)

        return AirQualitySnapshot(
            source="data.gov.sg / NEA",
            source_urls=[self.psi_url, self.pm25_url],
            observed_at=max(psi_item.timestamp, pm25_item.timestamp),
            updated_at=max(psi_item.updated_timestamp, pm25_item.updated_timestamp),
            ingested_at=datetime.now(UTC),
            national_psi=national_psi,
            national_level=level,
            haze_alert=national_psi > 100,
            regions=sorted(regions, key=lambda item: item.psi_24h, reverse=True),
            guidance=HealthGuidance(
                level=level,
                general_population=general,
                sensitive_groups=sensitive,
                source_url="https://www.haze.gov.sg/",
                disclaimer=(
                    "General information only. Follow current NEA, MOH, school, "
                    "workplace, and medical advice."
                ),
            ),
            quality=QualitySummary(
                status="healthy" if completeness == 100 else "degraded",
                received_records=len(expected_regions),
                valid_records=len(regions),
                completeness_percent=completeness,
                issues=issues,
            ),
        )
