from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.api.routes.air_quality import get_air_quality_client
from app.api.routes.transport import get_lta_client
from app.main import app
from app.models.air_quality import AirQualitySnapshot, HealthGuidance, RegionAirQuality
from app.models.transport import (
    ArrivalEstimate,
    BusArrivalBoard,
    BusServiceArrival,
    BusStop,
)
from app.models.weather import QualitySummary
from app.services.exposure import assess_stop_exposure, exposure_band, nearest_region


def quality() -> QualitySummary:
    return QualitySummary(
        status="healthy",
        received_records=1,
        valid_records=1,
        completeness_percent=100,
        issues=[],
    )


def air_snapshot() -> AirQualitySnapshot:
    observed = datetime(2026, 10, 14, 9, tzinfo=UTC)
    return AirQualitySnapshot(
        source="data.gov.sg / NEA",
        source_urls=["https://example.test/psi"],
        observed_at=observed,
        updated_at=observed,
        ingested_at=observed,
        national_psi=170,
        national_level="Unhealthy",
        haze_alert=True,
        regions=[
            RegionAirQuality(
                region="west",
                latitude=1.35735,
                longitude=103.7,
                psi_24h=170,
                pm25_24h=120,
                pm25_1h=200,
                level="Unhealthy",
            ),
            RegionAirQuality(
                region="east",
                latitude=1.35735,
                longitude=103.94,
                psi_24h=120,
                pm25_24h=70,
                pm25_1h=100,
                level="Unhealthy",
            ),
        ],
        guidance=HealthGuidance(
            level="Unhealthy",
            general_population="Reduce prolonged or strenuous outdoor activity.",
            sensitive_groups="Follow official advice.",
            source_url="https://www.haze.gov.sg/",
            disclaimer="General information only.",
        ),
        quality=quality(),
    )


def arrival_board(*, with_arrival: bool = True) -> BusArrivalBoard:
    now = datetime(2026, 10, 14, 9, tzinfo=UTC)
    estimates = (
        [
            ArrivalEstimate(
                estimated_arrival=now + timedelta(minutes=12),
                minutes=12,
                display="12 min",
                load="SEA",
                load_label="Seats available",
                wheelchair_accessible=True,
                monitored=True,
                vehicle_type="Double deck",
            )
        ]
        if with_arrival
        else []
    )
    return BusArrivalBoard(
        source="LTA DataMall",
        source_url="https://example.test/arrivals",
        fetched_at=now,
        bus_stop=BusStop(
            code="01012",
            road_name="Test Road",
            description="Test Stop",
            latitude=1.35,
            longitude=103.71,
        ),
        services=[BusServiceArrival(service_no="10", operator="SBST", arrivals=estimates)],
        quality=quality(),
    )


def test_selects_the_nearest_official_region() -> None:
    region, region_distance = nearest_region(arrival_board().bus_stop, air_snapshot().regions)

    assert region.region == "west"
    assert region_distance < 2


def test_builds_an_explainable_bounded_score() -> None:
    assessment = assess_stop_exposure(
        arrival_board(),
        air_snapshot(),
        now=datetime(2026, 10, 14, 9, 5, tzinfo=UTC),
    )

    assert assessment.region == "west"
    assert assessment.next_bus_minutes == 12
    assert assessment.score == 61
    assert assessment.band == "High"
    assert assessment.components.psi == pytest.approx(31.2)
    assert assessment.components.pm25_spike == 24
    assert assessment.components.outdoor_wait == 6
    assert len(assessment.explanation) == 3


def test_no_arrival_is_disclosed_instead_of_inventing_a_wait() -> None:
    assessment = assess_stop_exposure(arrival_board(with_arrival=False), air_snapshot())

    assert assessment.next_bus_minutes is None
    assert assessment.components.outdoor_wait == 0
    assert "No live arrival estimate" in assessment.explanation[-1]


@pytest.mark.parametrize(
    ("score", "band"),
    [(0, "Low"), (24, "Low"), (25, "Elevated"), (50, "High"), (75, "Very high")],
)
def test_score_bands(score: int, band: str) -> None:
    assert exposure_band(score) == band


@pytest.mark.asyncio
async def test_commute_endpoint_joins_arrivals_and_air_quality() -> None:
    class FakeLtaClient:
        async def fetch_arrivals(self, bus_stop_code: str) -> BusArrivalBoard:
            assert bus_stop_code == "01012"
            return arrival_board()

    class FakeAirClient:
        async def fetch(self) -> AirQualitySnapshot:
            return air_snapshot()

    app.dependency_overrides[get_lta_client] = lambda: FakeLtaClient()
    app.dependency_overrides[get_air_quality_client] = lambda: FakeAirClient()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/commute/stops/01012")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["arrivals"]["bus_stop"]["code"] == "01012"
    assert payload["exposure"]["region"] == "west"
    assert payload["exposure"]["score"] == 61
