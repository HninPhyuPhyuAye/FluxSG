import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.routes.air_quality import get_air_quality_client
from app.api.routes.transport import get_lta_client
from app.clients.air_quality import AirQualityClient, AirQualitySourceError
from app.clients.lta import LtaDataMallClient, LtaNotFoundError, LtaSourceError
from app.models.exposure import CommuteIntelligence
from app.services.exposure import assess_stop_exposure

router = APIRouter(prefix="/api/v1/commute", tags=["commute intelligence"])


@router.get("/stops/{bus_stop_code}", response_model=CommuteIntelligence)
async def stop_intelligence(
    bus_stop_code: Annotated[str, Path(pattern=r"^\d{5}$")],
    lta: Annotated[LtaDataMallClient, Depends(get_lta_client)],
    air: Annotated[AirQualityClient, Depends(get_air_quality_client)],
) -> CommuteIntelligence:
    try:
        arrivals, air_quality = await asyncio.gather(
            lta.fetch_arrivals(bus_stop_code),
            air.fetch(),
        )
    except LtaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (LtaSourceError, AirQualitySourceError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live commute exposure data is temporarily unavailable",
        ) from exc

    return CommuteIntelligence(
        arrivals=arrivals,
        exposure=assess_stop_exposure(arrivals, air_quality),
    )
