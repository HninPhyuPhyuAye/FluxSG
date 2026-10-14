from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.clients.forecast import ForecastClient, ForecastSourceError


def manifest(*, expires_at: datetime, available: bool = True) -> dict[str, object]:
    observed = expires_at - timedelta(hours=3)
    return {
        "schema_version": 1,
        "forecast_type": "regional 24-hour PSI one hour ahead",
        "source": "data.gov.sg / National Environment Agency",
        "source_url": "https://example.test/psi",
        "generated_at": observed.isoformat(),
        "observed_at": observed.isoformat(),
        "forecast_for": (observed + timedelta(hours=1)).isoformat(),
        "expires_at": expires_at.isoformat(),
        "available": available,
        "status": "available" if available else "withheld",
        "reason": "Guardrail decision",
        "checks": {"source_fresh": True},
        "freshness_hours": 0.5,
        "model": {
            "name": "histogram gradient boosting",
            "version": "psi-hgb-v1",
            "trained_through": observed.isoformat(),
            "age_hours": 1,
            "test_mae": 0.58,
            "persistence_mae": 0.60,
            "interval_coverage": 0.89,
            "backtest_wins": 3,
            "backtest_folds": 4,
        },
        "drift": {"status": "healthy"},
        "forecasts": [
            {
                "region": "central",
                "observed_psi_24h": 45,
                "predicted_psi_24h": 46,
                "lower_90": 44.8,
                "upper_90": 47.2,
                "predicted_band": "Good",
            }
        ],
        "disclaimer": "Experimental estimate, not official guidance.",
    }


@pytest.mark.asyncio
async def test_fetches_valid_forecast_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = manifest(expires_at=datetime.now(UTC) + timedelta(hours=2))

    async def fake_get(self: httpx.AsyncClient, *args: object, **kwargs: object) -> httpx.Response:
        request = httpx.Request("GET", "https://example.test/forecast.json")
        return httpx.Response(200, json=payload, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    result = await ForecastClient("https://example.test/forecast.json").fetch()

    assert result.available is True
    assert result.forecasts[0].region == "central"


@pytest.mark.asyncio
async def test_withholds_expired_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = manifest(expires_at=datetime.now(UTC) - timedelta(minutes=1))

    async def fake_get(self: httpx.AsyncClient, *args: object, **kwargs: object) -> httpx.Response:
        request = httpx.Request("GET", "https://example.test/forecast.json")
        return httpx.Response(200, json=payload, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    result = await ForecastClient("https://example.test/forecast.json").fetch()

    assert result.available is False
    assert result.status == "withheld"
    assert result.checks["source_fresh"] is False


@pytest.mark.asyncio
async def test_rejects_invalid_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(self: httpx.AsyncClient, *args: object, **kwargs: object) -> httpx.Response:
        request = httpx.Request("GET", "https://example.test/forecast.json")
        return httpx.Response(200, json={"unexpected": True}, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(ForecastSourceError):
        await ForecastClient("https://example.test/forecast.json").fetch()
