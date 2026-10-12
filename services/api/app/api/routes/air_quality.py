from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.clients.air_quality import AirQualityClient, AirQualitySourceError
from app.core.config import Settings, get_settings
from app.models.air_quality import AirQualitySnapshot

router = APIRouter(prefix="/api/v1/air-quality", tags=["air quality"])

SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_air_quality_client(settings: SettingsDependency) -> AirQualityClient:
    return AirQualityClient(
        psi_url=settings.data_gov_psi_url,
        pm25_url=settings.data_gov_pm25_url,
        timeout_seconds=settings.source_timeout_seconds,
    )


@router.get("/current", response_model=AirQualitySnapshot)
async def current_air_quality(
    client: Annotated[AirQualityClient, Depends(get_air_quality_client)],
) -> AirQualitySnapshot:
    try:
        return await client.fetch()
    except AirQualitySourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live air-quality data is temporarily unavailable",
        ) from exc

