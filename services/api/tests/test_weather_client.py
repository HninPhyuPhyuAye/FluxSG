import json

import httpx
import pytest

from app.clients.weather import WeatherClient, WeatherSourceError

VALID_PAYLOAD = {
    "code": 0,
    "data": {
        "area_metadata": [
            {
                "name": "City",
                "label_location": {"latitude": 1.292, "longitude": 103.844},
            },
            {
                "name": "Bedok",
                "label_location": {"latitude": 1.321, "longitude": 103.924},
            },
        ],
        "items": [
            {
                "update_timestamp": "2026-10-12T20:00:00+08:00",
                "valid_period": {
                    "start": "2026-10-12T20:00:00+08:00",
                    "end": "2026-10-12T22:00:00+08:00",
                },
                "forecasts": [
                    {"area": "City", "forecast": "Light Rain"},
                    {"area": "Bedok", "forecast": "Cloudy"},
                ],
            }
        ],
    },
}


@pytest.mark.asyncio
async def test_normalises_weather_and_reports_quality(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(self: httpx.AsyncClient, *args: object, **kwargs: object) -> httpx.Response:
        request = httpx.Request("GET", "https://example.test/weather")
        return httpx.Response(200, json=VALID_PAYLOAD, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    outlook = await WeatherClient("https://example.test/weather").fetch()

    assert outlook.source == "data.gov.sg / NEA"
    assert outlook.quality.status == "healthy"
    assert outlook.quality.completeness_percent == 100
    assert [item.area for item in outlook.forecasts] == ["City", "Bedok"]


@pytest.mark.asyncio
async def test_rejects_malformed_source_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(self: httpx.AsyncClient, *args: object, **kwargs: object) -> httpx.Response:
        request = httpx.Request("GET", "https://example.test/weather")
        return httpx.Response(200, content=json.dumps({"unexpected": True}), request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(WeatherSourceError):
        await WeatherClient("https://example.test/weather").fetch()

