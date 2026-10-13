from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.clients.lta import LtaDataMallClient


def bus_stop(code: str = "01012", description: str = "Hotel Grand Pacific") -> dict:
    return {
        "BusStopCode": code,
        "RoadName": "Victoria St",
        "Description": description,
        "Latitude": 1.29685,
        "Longitude": 103.853,
    }


def bus_service(service_no: str = "10", direction: int = 1) -> dict:
    return {
        "ServiceNo": service_no,
        "Operator": "SBST",
        "Direction": direction,
    }


def route_stop(sequence: int = 1) -> dict:
    return {
        "ServiceNo": "10",
        "Operator": "SBST",
        "Direction": 1,
        "StopSequence": sequence,
        "BusStopCode": "01012",
        "Distance": float(sequence - 1),
        "WD_FirstBus": "0600",
        "WD_LastBus": "2330",
        "SAT_FirstBus": "0600",
        "SAT_LastBus": "2330",
        "SUN_FirstBus": "0630",
        "SUN_LastBus": "2300",
    }


@pytest.mark.asyncio
async def test_network_summary_and_stop_search_are_normalised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["AccountKey"] == "test-key"
        if request.url.path.endswith("/BusStops"):
            return httpx.Response(
                200,
                json={"value": [bus_stop(), bus_stop("02049", "Raffles Hotel")]},
            )
        if request.url.path.endswith("/BusServices"):
            return httpx.Response(
                200,
                json={"value": [bus_service(), bus_service(direction=2)]},
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    client = LtaDataMallClient(
        account_key="test-key",
        base_url="https://example.test/ltaodataservice",
        transport=httpx.MockTransport(handler),
    )

    summary = await client.fetch_network_summary()
    search = await client.search_stops("raffles", limit=5)

    assert summary.bus_stop_count == 2
    assert summary.service_count == 1
    assert summary.route_pattern_count == 2
    assert summary.operator_counts == {"SBST": 2}
    assert summary.quality.completeness_percent == 100
    assert [stop.code for stop in search.stops] == ["02049"]


@pytest.mark.asyncio
async def test_live_arrivals_include_minutes_load_and_accessibility() -> None:
    eta = datetime.now(UTC) + timedelta(minutes=8)

    def estimate(arrival: str, load: str = "SEA") -> dict:
        return {
            "EstimatedArrival": arrival,
            "Monitored": 1,
            "Latitude": "1.30",
            "Longitude": "103.85",
            "VisitNumber": "1",
            "Load": load,
            "Feature": "WAB",
            "Type": "DD",
        }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/BusStops"):
            return httpx.Response(200, json={"value": [bus_stop()]})
        if request.url.path.endswith("/v3/BusArrival"):
            return httpx.Response(
                200,
                json={
                    "BusStopCode": "01012",
                    "Services": [
                        {
                            "ServiceNo": "10",
                            "Operator": "SBST",
                            "NextBus": estimate(eta.isoformat()),
                            "NextBus2": estimate(""),
                            "NextBus3": estimate(""),
                        }
                    ],
                },
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    client = LtaDataMallClient(
        account_key="test-key",
        base_url="https://example.test/ltaodataservice",
        transport=httpx.MockTransport(handler),
    )

    board = await client.fetch_arrivals("01012")

    assert board.bus_stop.description == "Hotel Grand Pacific"
    assert board.services[0].service_no == "10"
    assert board.services[0].arrivals[0].minutes in {7, 8}
    assert board.services[0].arrivals[0].load_label == "Seats available"
    assert board.services[0].arrivals[0].wheelchair_accessible is True
    assert board.services[0].arrivals[0].vehicle_type == "Double deck"


@pytest.mark.asyncio
async def test_route_adapter_filters_and_orders_the_requested_service() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/BusRoutes"):
            return httpx.Response(
                200,
                json={"value": [route_stop(2), route_stop(1)]},
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    client = LtaDataMallClient(
        account_key="test-key",
        base_url="https://example.test/ltaodataservice",
        transport=httpx.MockTransport(handler),
    )

    route = await client.fetch_route("10")

    assert route.service_no == "10"
    assert [stop.stop_sequence for stop in route.stops] == [1, 2]
    assert route.stops[0].weekday_first_bus == "0600"
