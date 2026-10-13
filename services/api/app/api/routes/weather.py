from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.clients.weather import WeatherClient, WeatherSourceError
from app.core.config import Settings, get_settings
from app.models.weather import WeatherOutlook

router = APIRouter(prefix="/api/v1/weather", tags=["weather"])


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_weather_client(settings: SettingsDependency) -> WeatherClient:
    return WeatherClient(
        url=settings.data_gov_weather_url,
        timeout_seconds=settings.source_timeout_seconds,
    )


@router.get("/outlook", response_model=WeatherOutlook)
async def weather_outlook(
    client: Annotated[WeatherClient, Depends(get_weather_client)],
) -> WeatherOutlook:
    try:
        return await client.fetch()
    except WeatherSourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live weather data is temporarily unavailable",
        ) from exc
