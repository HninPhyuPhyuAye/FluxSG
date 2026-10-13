from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.clients.lta import LtaDataMallClient, LtaNotFoundError, LtaSourceError
from app.core.config import Settings, get_settings
from app.models.transport import (
    BusArrivalBoard,
    BusRouteResult,
    BusStopSearchResult,
    TransportNetworkSummary,
)

router = APIRouter(prefix="/api/v1/transport", tags=["transport"])

SettingsDependency = Annotated[Settings, Depends(get_settings)]


@lru_cache
def create_lta_client(
    account_key: str,
    base_url: str,
    timeout_seconds: float,
    cache_ttl_seconds: int,
) -> LtaDataMallClient:
    return LtaDataMallClient(
        account_key=account_key,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        cache_ttl_seconds=cache_ttl_seconds,
    )


def get_lta_client(settings: SettingsDependency) -> LtaDataMallClient:
    if not settings.lta_account_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LTA DataMall integration is not configured",
        )
    return create_lta_client(
        settings.lta_account_key,
        settings.lta_base_url,
        settings.source_timeout_seconds,
        settings.lta_cache_ttl_seconds,
    )


ClientDependency = Annotated[LtaDataMallClient, Depends(get_lta_client)]


def source_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Live LTA transport data is temporarily unavailable",
    )


@router.get("/network", response_model=TransportNetworkSummary)
async def network_summary(client: ClientDependency) -> TransportNetworkSummary:
    try:
        return await client.fetch_network_summary()
    except LtaSourceError as exc:
        raise source_error() from exc


@router.get("/stops", response_model=BusStopSearchResult)
async def search_stops(
    client: ClientDependency,
    query: Annotated[str, Query(min_length=2, max_length=80)],
    limit: Annotated[int, Query(ge=1, le=25)] = 10,
) -> BusStopSearchResult:
    try:
        return await client.search_stops(query, limit)
    except LtaSourceError as exc:
        raise source_error() from exc


@router.get("/arrivals/{bus_stop_code}", response_model=BusArrivalBoard)
async def arrivals(
    client: ClientDependency,
    bus_stop_code: Annotated[str, Path(pattern=r"^\d{5}$")],
    service_no: Annotated[str | None, Query(max_length=6)] = None,
) -> BusArrivalBoard:
    try:
        return await client.fetch_arrivals(bus_stop_code, service_no)
    except LtaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LtaSourceError as exc:
        raise source_error() from exc


@router.get("/routes/{service_no}", response_model=BusRouteResult)
async def route(
    client: ClientDependency,
    service_no: Annotated[str, Path(min_length=1, max_length=6, pattern=r"^[A-Za-z0-9]+$")],
) -> BusRouteResult:
    try:
        return await client.fetch_route(service_no)
    except LtaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LtaSourceError as exc:
        raise source_error() from exc
