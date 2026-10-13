import httpx
import pytest

from app.core.config import Settings, get_settings
from app.main import app


@pytest.mark.asyncio
async def test_health() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "fluxsg-api"


@pytest.mark.asyncio
async def test_prometheus_metrics_are_exposed() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/health")
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert "fluxsg_http_requests_total" in response.text
    assert "fluxsg_http_request_duration_seconds" in response.text


@pytest.mark.asyncio
async def test_lta_is_safe_when_key_is_missing() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(lta_account_key=None)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/integrations/lta")
            transport_response = await client.get("/api/v1/transport/network")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "source": "LTA DataMall",
        "configured": False,
        "state": "awaiting_credentials",
        "next_step": "Add LTA_ACCOUNT_KEY to the local environment",
    }
    assert transport_response.status_code == 503
    assert transport_response.json()["detail"] == "LTA DataMall integration is not configured"


@pytest.mark.asyncio
async def test_pipeline_status_is_safe_when_storage_is_not_configured() -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(database_url=None)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/pipeline/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "state": "not_configured",
        "latest_runs": [],
    }


def test_cors_origins_accept_compose_environment_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")

    settings = Settings()

    assert settings.cors_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
