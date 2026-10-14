import math
from datetime import UTC, datetime

from app.models.air_quality import AirQualitySnapshot, RegionAirQuality
from app.models.exposure import ExposureComponents, StopExposureAssessment
from app.models.transport import BusArrivalBoard, BusStop


def distance_km(first_lat: float, first_lon: float, second_lat: float, second_lon: float) -> float:
    """Return great-circle distance between two WGS84 points."""

    radius_km = 6371.0
    first_phi = math.radians(first_lat)
    second_phi = math.radians(second_lat)
    delta_phi = math.radians(second_lat - first_lat)
    delta_lambda = math.radians(second_lon - first_lon)
    haversine = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(first_phi) * math.cos(second_phi) * math.sin(delta_lambda / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


def nearest_region(
    stop: BusStop,
    regions: list[RegionAirQuality],
) -> tuple[RegionAirQuality, float]:
    if not regions:
        raise ValueError("At least one regional air-quality reading is required")
    ranked = [
        (distance_km(stop.latitude, stop.longitude, region.latitude, region.longitude), region)
        for region in regions
    ]
    region_distance, region = min(ranked, key=lambda item: item[0])
    return region, region_distance


def exposure_band(score: int) -> str:
    if score < 25:
        return "Low"
    if score < 50:
        return "Elevated"
    if score < 75:
        return "High"
    return "Very high"


def assess_stop_exposure(
    arrivals: BusArrivalBoard,
    air: AirQualitySnapshot,
    *,
    now: datetime | None = None,
) -> StopExposureAssessment:
    """Combine live wait and regional air signals into a transparent planning score."""

    region, region_distance = nearest_region(arrivals.bus_stop, air.regions)
    observed_waits = [
        estimate.minutes
        for service in arrivals.services
        for estimate in service.arrivals
    ]
    next_bus_minutes = min(observed_waits) if observed_waits else None

    psi_component = round(min(region.psi_24h / 300 * 55, 55), 1)
    pm25_component = round(min(region.pm25_1h / 250 * 30, 30), 1)
    wait_component = round(
        min((next_bus_minutes or 0) / 30 * 15, 15),
        1,
    )
    score = round(psi_component + pm25_component + wait_component)
    explanation = [
        f"{region.region.title()} 24-hour PSI contributes {psi_component:.1f} of 55 points.",
        f"The latest regional PM2.5 1-hour reading contributes {pm25_component:.1f} of 30 points.",
    ]
    if next_bus_minutes is None:
        explanation.append(
            "No live arrival estimate was available, so outdoor waiting adds no points."
        )
    else:
        explanation.append(
            f"The shortest reported wait ({next_bus_minutes} min) contributes "
            f"{wait_component:.1f} of 15 points."
        )

    return StopExposureAssessment(
        source=[air.source, arrivals.source],
        assessed_at=(now or datetime.now(UTC)).astimezone(UTC),
        air_observed_at=air.observed_at,
        region=region.region,
        region_distance_km=round(region_distance, 2),
        psi_24h=region.psi_24h,
        pm25_1h=region.pm25_1h,
        next_bus_minutes=next_bus_minutes,
        services_reported=len(arrivals.services),
        score=score,
        band=exposure_band(score),
        components=ExposureComponents(
            psi=psi_component,
            pm25_spike=pm25_component,
            outdoor_wait=wait_component,
        ),
        explanation=explanation,
        guidance=air.guidance.general_population,
        guidance_url=air.guidance.source_url,
        disclaimer=(
            "Planning signal only, not a personal exposure or medical measurement. "
            "Follow official NEA and haze.gov.sg guidance."
        ),
    )
