from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.clients.forecast import ForecastClient, ForecastSourceError
from app.core.config import Settings, get_settings
from app.models.forecast import ForecastManifest

router = APIRouter(prefix="/api/v1/forecast", tags=["forecast"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_forecast_client(settings: SettingsDependency) -> ForecastClient:
    return ForecastClient(
        settings.forecast_manifest_url,
        timeout_seconds=settings.source_timeout_seconds,
    )


@router.get("/psi", response_model=ForecastManifest)
async def regional_psi_forecast(
    client: Annotated[ForecastClient, Depends(get_forecast_client)],
) -> ForecastManifest:
    try:
        return await client.fetch()
    except ForecastSourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The guarded PSI forecast is temporarily unavailable",
        ) from exc
