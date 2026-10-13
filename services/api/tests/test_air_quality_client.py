import httpx
import pytest

from app.clients.air_quality import AirQualityClient, AirQualitySourceError, psi_level

REGIONS = [
    {"name": "north", "labelLocation": {"latitude": 1.41803, "longitude": 103.82}},
    {"name": "west", "labelLocation": {"latitude": 1.35735, "longitude": 103.7}},
]

PSI_PAYLOAD = {
    "code": 0,
    "data": {
        "regionMetadata": REGIONS,
        "items": [
            {
                "updatedTimestamp": "2026-10-12T21:45:47+08:00",
                "timestamp": "2026-10-12T21:00:00+08:00",
                "readings": {
                    "psi_twenty_four_hourly": {"north": 123, "west": 161},
                    "pm25_twenty_four_hourly": {"north": 76, "west": 113},
                },
            }
        ],
    },
}

PM25_PAYLOAD = {
    "code": 0,
    "data": {
        "regionMetadata": REGIONS,
        "items": [
            {
                "updatedTimestamp": "2026-10-12T21:45:54+08:00",
                "timestamp": "2026-10-12T21:00:00+08:00",
                "readings": {"pm25_one_hourly": {"north": 107, "west": 171}},
            }
        ],
    },
}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "Good"),
        (50, "Good"),
        (51, "Moderate"),
        (100, "Moderate"),
        (101, "Unhealthy"),
        (200, "Unhealthy"),
        (201, "Very Unhealthy"),
        (300, "Very Unhealthy"),
        (301, "Hazardous"),
    ],
)
def test_psi_level_boundaries(value: int, expected: str) -> None:
    assert psi_level(value) == expected


@pytest.mark.asyncio
async def test_combines_official_psi_and_pm25_feeds(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(
        self: httpx.AsyncClient, url: str, *args: object, **kwargs: object
    ) -> httpx.Response:
        payload = PSI_PAYLOAD if url.endswith("/psi") else PM25_PAYLOAD
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    snapshot = await AirQualityClient(
        "https://example.test/psi", "https://example.test/pm25"
    ).fetch()

    assert snapshot.national_psi == 161
    assert snapshot.national_level == "Unhealthy"
    assert snapshot.haze_alert is True
    assert snapshot.quality.completeness_percent == 100
    assert snapshot.regions[0].region == "west"
    assert snapshot.regions[0].pm25_1h == 171


@pytest.mark.asyncio
async def test_rejects_air_quality_without_complete_regions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incomplete = {
        **PM25_PAYLOAD,
        "data": {
            **PM25_PAYLOAD["data"],
            "items": [
                {
                    **PM25_PAYLOAD["data"]["items"][0],
                    "readings": {"pm25_one_hourly": {}},
                }
            ],
        },
    }

    async def fake_get(
        self: httpx.AsyncClient, url: str, *args: object, **kwargs: object
    ) -> httpx.Response:
        payload = PSI_PAYLOAD if url.endswith("/psi") else incomplete
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(AirQualitySourceError):
        await AirQualityClient("https://example.test/psi", "https://example.test/pm25").fetch()
