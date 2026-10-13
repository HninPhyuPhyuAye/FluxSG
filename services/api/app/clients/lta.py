import asyncio
import math
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.models.transport import (
    ArrivalEstimate,
    BusArrivalBoard,
    BusRouteResult,
    BusRouteStop,
    BusServiceArrival,
    BusStop,
    BusStopSearchResult,
    TransportNetworkSummary,
)
from app.models.weather import QualitySummary


class SourceBusStop(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    bus_stop_code: str = Field(alias="BusStopCode", pattern=r"^\d{5}$")
    road_name: str = Field(alias="RoadName")
    description: str = Field(alias="Description")
    latitude: float = Field(alias="Latitude")
    longitude: float = Field(alias="Longitude")


class SourceBusService(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    service_no: str = Field(alias="ServiceNo")
    operator: str = Field(alias="Operator")
    direction: int = Field(alias="Direction")


class SourceBusRoute(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    service_no: str = Field(alias="ServiceNo")
    operator: str = Field(alias="Operator")
    direction: int = Field(alias="Direction")
    stop_sequence: int = Field(alias="StopSequence")
    bus_stop_code: str = Field(alias="BusStopCode")
    distance: float = Field(alias="Distance")
    weekday_first_bus: str = Field(alias="WD_FirstBus")
    weekday_last_bus: str = Field(alias="WD_LastBus")
    saturday_first_bus: str = Field(alias="SAT_FirstBus")
    saturday_last_bus: str = Field(alias="SAT_LastBus")
    sunday_first_bus: str = Field(alias="SUN_FirstBus")
    sunday_last_bus: str = Field(alias="SUN_LastBus")


class SourceArrivalEstimate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    estimated_arrival: str = Field(default="", alias="EstimatedArrival")
    monitored: int | str = Field(default=0, alias="Monitored")
    load: str = Field(default="", alias="Load")
    feature: str = Field(default="", alias="Feature")
    vehicle_type: str = Field(default="", alias="Type")


class SourceBusArrival(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    service_no: str = Field(alias="ServiceNo")
    operator: str = Field(alias="Operator")
    next_bus: SourceArrivalEstimate = Field(alias="NextBus")
    next_bus_2: SourceArrivalEstimate = Field(alias="NextBus2")
    next_bus_3: SourceArrivalEstimate = Field(alias="NextBus3")


@dataclass(frozen=True)
class DatasetResult[RecordT: BaseModel]:
    records: list[RecordT]
    raw_records: list[Any]
    rejected_records: list[Any]
    received: int
    issues: list[str]
    ingested_at: datetime


class LtaSourceError(RuntimeError):
    """Raised when LTA DataMall cannot provide a trusted response."""


class LtaNotFoundError(RuntimeError):
    """Raised when the requested LTA entity does not exist."""


LOAD_LABELS = {
    "SEA": "Seats available",
    "SDA": "Standing available",
    "LSD": "Limited standing",
}

VEHICLE_TYPES = {
    "SD": "Single deck",
    "DD": "Double deck",
    "BD": "Bendy",
}


class LtaDataMallClient:
    page_size = 500

    def __init__(
        self,
        account_key: str,
        base_url: str,
        timeout_seconds: float = 8.0,
        cache_ttl_seconds: int = 21_600,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.account_key = account_key
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self.transport = transport
        self._stops_cache: tuple[float, DatasetResult[SourceBusStop]] | None = None
        self._services_cache: tuple[float, DatasetResult[SourceBusService]] | None = None
        self._routes_cache: tuple[float, DatasetResult[SourceBusRoute]] | None = None
        self._stops_lock = asyncio.Lock()
        self._services_lock = asyncio.Lock()
        self._routes_lock = asyncio.Lock()

    @property
    def headers(self) -> dict[str, str]:
        return {
            "AccountKey": self.account_key,
            "Accept": "application/json",
            "User-Agent": "FluxSG/0.2",
        }

    async def _request(self, path: str, params: dict[str, str | int]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.get(path, params=params, headers=self.headers)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise LtaSourceError("LTA DataMall returned an invalid response") from exc
        if not isinstance(payload, dict):
            raise LtaSourceError("LTA DataMall response was not an object")
        return payload

    async def _fetch_all[RecordT: BaseModel](
        self,
        path: str,
        model: type[RecordT],
        *,
        max_pages: int,
    ) -> DatasetResult[RecordT]:
        records: list[RecordT] = []
        all_raw_records: list[Any] = []
        rejected_records: list[Any] = []
        issues: list[str] = []
        received = 0
        for page in range(max_pages):
            payload = await self._request(path, {"$skip": page * self.page_size})
            page_records = payload.get("value")
            if not isinstance(page_records, list):
                raise LtaSourceError(f"LTA {path} response did not contain a record list")
            received += len(page_records)
            for index, raw_record in enumerate(page_records):
                all_raw_records.append(raw_record)
                try:
                    records.append(model.model_validate(raw_record))
                except ValidationError:
                    rejected_records.append(raw_record)
                    if len(issues) < 20:
                        issues.append(f"{path} page {page + 1}, row {index + 1}: invalid record")
            if len(page_records) < self.page_size:
                return DatasetResult(
                    records=records,
                    raw_records=all_raw_records,
                    rejected_records=rejected_records,
                    received=received,
                    issues=issues,
                    ingested_at=datetime.now(UTC),
                )
        raise LtaSourceError(f"LTA {path} exceeded the safe pagination limit")

    def _fresh(self, cached_at: float) -> bool:
        return time.monotonic() - cached_at < self.cache_ttl_seconds

    async def _load_stops(self) -> DatasetResult[SourceBusStop]:
        if self._stops_cache and self._fresh(self._stops_cache[0]):
            return self._stops_cache[1]
        async with self._stops_lock:
            if self._stops_cache and self._fresh(self._stops_cache[0]):
                return self._stops_cache[1]
            result = await self._fetch_all("BusStops", SourceBusStop, max_pages=20)
            self._stops_cache = (time.monotonic(), result)
            return result

    async def _load_services(self) -> DatasetResult[SourceBusService]:
        if self._services_cache and self._fresh(self._services_cache[0]):
            return self._services_cache[1]
        async with self._services_lock:
            if self._services_cache and self._fresh(self._services_cache[0]):
                return self._services_cache[1]
            result = await self._fetch_all("BusServices", SourceBusService, max_pages=10)
            self._services_cache = (time.monotonic(), result)
            return result

    async def _load_routes(self) -> DatasetResult[SourceBusRoute]:
        if self._routes_cache and self._fresh(self._routes_cache[0]):
            return self._routes_cache[1]
        async with self._routes_lock:
            if self._routes_cache and self._fresh(self._routes_cache[0]):
                return self._routes_cache[1]
            result = await self._fetch_all("BusRoutes", SourceBusRoute, max_pages=100)
            self._routes_cache = (time.monotonic(), result)
            return result

    async def fetch_network_snapshot(self) -> dict[str, Any]:
        """Return validated source records for immutable scheduled storage."""

        stops, services, routes = await asyncio.gather(
            self._load_stops(),
            self._load_services(),
            self._load_routes(),
        )
        datasets = {
            "bus_stops": stops,
            "bus_services": services,
            "bus_routes": routes,
        }
        received = sum(result.received for result in datasets.values())
        valid = sum(len(result.records) for result in datasets.values())
        rejected = sum(len(result.rejected_records) for result in datasets.values())
        completeness = round((valid / received * 100) if received else 0, 1)
        return {
            "source": "LTA DataMall",
            "source_url": self.base_url,
            "ingested_at": max(result.ingested_at for result in datasets.values()).isoformat(),
            "datasets": {
                name: {
                    "received_records": result.received,
                    "valid_records": len(result.records),
                    "rejected_records": result.rejected_records,
                    "records": result.raw_records,
                    "issues": result.issues,
                }
                for name, result in datasets.items()
            },
            "quality": {
                "status": "healthy" if received > 0 and rejected == 0 else "degraded",
                "received_records": received,
                "valid_records": valid,
                "rejected_records": rejected,
                "completeness_percent": completeness,
            },
        }

    @staticmethod
    def _stop(record: SourceBusStop) -> BusStop:
        return BusStop(
            code=record.bus_stop_code,
            road_name=record.road_name.strip(),
            description=record.description.strip(),
            latitude=record.latitude,
            longitude=record.longitude,
        )

    @staticmethod
    def _quality(result: DatasetResult[Any]) -> QualitySummary:
        valid = len(result.records)
        completeness = round((valid / result.received * 100) if result.received else 0, 1)
        return QualitySummary(
            status="healthy" if result.received > 0 and completeness == 100 else "degraded",
            received_records=result.received,
            valid_records=valid,
            completeness_percent=completeness,
            issues=result.issues,
        )

    async def fetch_network_summary(self) -> TransportNetworkSummary:
        stops, services = await asyncio.gather(self._load_stops(), self._load_services())
        unique_services = {record.service_no for record in services.records}
        operator_counts = Counter(record.operator for record in services.records)
        received = stops.received + services.received
        valid = len(stops.records) + len(services.records)
        issues = [*stops.issues, *services.issues]
        completeness = round((valid / received * 100) if received else 0, 1)
        return TransportNetworkSummary(
            source="LTA DataMall",
            source_url=self.base_url,
            ingested_at=max(stops.ingested_at, services.ingested_at),
            bus_stop_count=len(stops.records),
            service_count=len(unique_services),
            route_pattern_count=len(services.records),
            operator_counts=dict(sorted(operator_counts.items())),
            quality=QualitySummary(
                status="healthy" if received > 0 and completeness == 100 else "degraded",
                received_records=received,
                valid_records=valid,
                completeness_percent=completeness,
                issues=issues,
            ),
        )

    async def search_stops(self, query: str, limit: int) -> BusStopSearchResult:
        result = await self._load_stops()
        needle = query.casefold().strip()

        def score(stop: SourceBusStop) -> tuple[int, str, str]:
            code = stop.bus_stop_code.casefold()
            description = stop.description.casefold()
            road = stop.road_name.casefold()
            if code == needle:
                rank = 0
            elif code.startswith(needle):
                rank = 1
            elif description.startswith(needle) or road.startswith(needle):
                rank = 2
            else:
                rank = 3
            return rank, description, code

        matches = [
            stop
            for stop in result.records
            if needle in stop.bus_stop_code.casefold()
            or needle in stop.description.casefold()
            or needle in stop.road_name.casefold()
        ]
        matches.sort(key=score)
        return BusStopSearchResult(
            source="LTA DataMall",
            query=query,
            ingested_at=result.ingested_at,
            stops=[self._stop(stop) for stop in matches[:limit]],
            quality=self._quality(result),
        )

    async def _fetch_stop(self, bus_stop_code: str) -> BusStop:
        payload = await self._request("BusStops", {"BusStopCode": bus_stop_code})
        raw_records = payload.get("value")
        if not isinstance(raw_records, list) or not raw_records:
            raise LtaNotFoundError(f"Bus stop {bus_stop_code} was not found")
        try:
            return self._stop(SourceBusStop.model_validate(raw_records[0]))
        except ValidationError as exc:
            raise LtaSourceError("LTA returned invalid bus-stop metadata") from exc

    async def fetch_arrivals(
        self,
        bus_stop_code: str,
        service_no: str | None = None,
    ) -> BusArrivalBoard:
        params: dict[str, str | int] = {"BusStopCode": bus_stop_code}
        if service_no:
            params["ServiceNo"] = service_no
        stop, payload = await asyncio.gather(
            self._fetch_stop(bus_stop_code),
            self._request("v3/BusArrival", params),
        )
        raw_services = payload.get("Services")
        if not isinstance(raw_services, list):
            raise LtaSourceError("LTA BusArrival response did not contain services")

        fetched_at = datetime.now(UTC)
        services: list[BusServiceArrival] = []
        issues: list[str] = []
        for index, raw_service in enumerate(raw_services):
            try:
                source = SourceBusArrival.model_validate(raw_service)
            except ValidationError:
                issues.append(f"Service row {index + 1}: invalid arrival record")
                continue
            estimates: list[ArrivalEstimate] = []
            for estimate in (source.next_bus, source.next_bus_2, source.next_bus_3):
                if not estimate.estimated_arrival:
                    continue
                try:
                    eta = datetime.fromisoformat(estimate.estimated_arrival)
                except ValueError:
                    issues.append(f"Service {source.service_no}: invalid arrival timestamp")
                    continue
                minutes = max(0, math.floor((eta - fetched_at).total_seconds() / 60))
                estimates.append(
                    ArrivalEstimate(
                        estimated_arrival=eta,
                        minutes=minutes,
                        display="Arr" if minutes == 0 else f"{minutes} min",
                        load=estimate.load or None,
                        load_label=LOAD_LABELS.get(estimate.load, "Load unavailable"),
                        wheelchair_accessible=estimate.feature == "WAB",
                        monitored=str(estimate.monitored) == "1",
                        vehicle_type=VEHICLE_TYPES.get(
                            estimate.vehicle_type,
                            "Vehicle type unavailable",
                        ),
                    )
                )
            services.append(
                BusServiceArrival(
                    service_no=source.service_no,
                    operator=source.operator,
                    arrivals=estimates,
                )
            )

        valid_services = len(services)
        completeness = round(
            (valid_services / len(raw_services) * 100) if raw_services else 100,
            1,
        )
        return BusArrivalBoard(
            source="LTA DataMall",
            source_url=f"{self.base_url}v3/BusArrival",
            fetched_at=fetched_at,
            bus_stop=stop,
            services=services,
            quality=QualitySummary(
                status="healthy" if not issues else "degraded",
                received_records=len(raw_services),
                valid_records=valid_services,
                completeness_percent=completeness,
                issues=issues,
            ),
        )

    async def fetch_route(self, service_no: str) -> BusRouteResult:
        result = await self._load_routes()
        matching = [
            route
            for route in result.records
            if route.service_no.casefold() == service_no.casefold()
        ]
        if not matching:
            raise LtaNotFoundError(f"Bus service {service_no} was not found")
        matching.sort(key=lambda route: (route.direction, route.stop_sequence))
        return BusRouteResult(
            source="LTA DataMall",
            service_no=matching[0].service_no,
            ingested_at=result.ingested_at,
            stops=[
                BusRouteStop(
                    service_no=route.service_no,
                    operator=route.operator,
                    direction=route.direction,
                    stop_sequence=route.stop_sequence,
                    bus_stop_code=route.bus_stop_code,
                    distance_km=route.distance,
                    weekday_first_bus=route.weekday_first_bus,
                    weekday_last_bus=route.weekday_last_bus,
                    saturday_first_bus=route.saturday_first_bus,
                    saturday_last_bus=route.saturday_last_bus,
                    sunday_first_bus=route.sunday_first_bus,
                    sunday_last_bus=route.sunday_last_bus,
                )
                for route in matching
            ],
            quality=self._quality(result),
        )
